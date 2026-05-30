package server

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	billingservice "github.com/flamegreat-1/etradie/src/billing/service"
	billingstore "github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/pipeline"
	"github.com/flamegreat-1/etradie/src/gateway/internal/settingsstore"
	"github.com/flamegreat-1/etradie/src/gateway/internal/symbolstore"
)

// APIHandler serves the dashboard-facing REST API for gateway operations.
// These endpoints expose the same logic as the gRPC server but over HTTP
// so the browser-based dashboard can call them directly.
type APIHandler struct {
	orchestrator  *pipeline.Orchestrator
	symbolStore   *symbolstore.Store
	settingsStore *settingsstore.Store
	scheduler     *pipeline.Scheduler
	redis         *infra.RedisClient
	engine        *infra.EngineHTTPClient
	transport     *alertredis.Transport
	cfg           *config.Config
	authCfg       *auth.Config
	log           zerolog.Logger

	// Quota pre-flight stores. Nil-tolerant so a future build that
	// disables the metering layer entirely (METERING_ENABLED=false)
	// still starts; the pre-flight degrades to a no-op in that case
	// and the deep Reserve path inside the orchestrator catches the
	// breach (or doesn't, when metering is off).
	quotaPolicyStore *billingstore.QuotaPolicyStore
	usageStore       *billingstore.UsageStore

	// Per-tier token-bucket rate limiters for POST /api/v1/cycle/run.
	// One bucket pool per tier so a Pro Managed user's burst budget is
	// not shared with a BYOK user's; the limiter is keyed by user_id
	// from the JWT, so two devices on the same account share one bucket
	// (correct behaviour: it is one user, one cost centre).
	cycleLimitFree       *billingservice.TokenBucketRateLimiter
	cycleLimitProByok    *billingservice.TokenBucketRateLimiter
	cycleLimitProManaged *billingservice.TokenBucketRateLimiter
}

// NewAPIHandler creates the dashboard REST API handler. authCfg
// supplies the per-tier rate-limit knobs configured via
// AUTH_TIER_*_CYCLE_RPM / _CYCLE_BURST.
func NewAPIHandler(
	cfg *config.Config,
	authCfg *auth.Config,
	orchestrator *pipeline.Orchestrator,
	symbolStore *symbolstore.Store,
	settingsStore *settingsstore.Store,
	scheduler *pipeline.Scheduler,
	redis *infra.RedisClient,
	engine *infra.EngineHTTPClient,
	transport *alertredis.Transport,
	quotaPolicyStore *billingstore.QuotaPolicyStore,
	usageStore *billingstore.UsageStore,
) *APIHandler {
	makeLimiter := func(rpm, burst int) *billingservice.TokenBucketRateLimiter {
		return billingservice.NewTokenBucketRateLimiter(billingservice.RateLimiterConfig{
			MaxKeys:    16384,
			RatePerSec: float64(rpm) / 60.0,
			Burst:      float64(burst),
		})
	}
	return &APIHandler{
		orchestrator:         orchestrator,
		symbolStore:          symbolStore,
		settingsStore:        settingsStore,
		scheduler:            scheduler,
		redis:                redis,
		engine:               engine,
		transport:            transport,
		cfg:                  cfg,
		authCfg:              authCfg,
		quotaPolicyStore:     quotaPolicyStore,
		usageStore:           usageStore,
		log:                  observability.Logger("api_handler"),
		cycleLimitFree:       makeLimiter(authCfg.TierFreeCycleRPM, authCfg.TierFreeCycleBurst),
		cycleLimitProByok:    makeLimiter(authCfg.TierProByokCycleRPM, authCfg.TierProByokCycleBurst),
		cycleLimitProManaged: makeLimiter(authCfg.TierProManagedCycleRPM, authCfg.TierProManagedCycleBurst),
	}
}

// cycleLimiterForClaims returns the right token bucket for the user's
// tier. Admins share the managed bucket because their LLM calls run on
// the platform key (see engine.dependencies._load_active_llm_connection).
func (h *APIHandler) cycleLimiterForClaims(claims *auth.Claims) *billingservice.TokenBucketRateLimiter {
	if claims == nil {
		return h.cycleLimitFree
	}
	if claims.Role == auth.RoleAdmin {
		return h.cycleLimitProManaged
	}
	switch strings.ToLower(strings.TrimSpace(claims.Tier)) {
	case "pro_managed":
		return h.cycleLimitProManaged
	case "pro_byok":
		return h.cycleLimitProByok
	default:
		return h.cycleLimitFree
	}
}

// RegisterProtectedRoutes mounts all dashboard API routes on the given mux,
// wrapping each with the provided auth middleware so that a valid JWT
// Bearer token is required for access.
//
// csrfMiddleware is applied AFTER auth so an unauthenticated request is
// rejected with 401 (not 403); RequireCSRF itself short-circuits safe
// methods (GET, HEAD, OPTIONS) and only gates POST/PUT/PATCH/DELETE, so
// wrapping multi-method endpoints (e.g. /api/v1/symbols which serves
// GET + PUT) is correct by construction.
func (h *APIHandler) RegisterProtectedRoutes(
	mux *http.ServeMux,
	authMiddleware func(http.Handler) http.Handler,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	wrap := func(handler http.HandlerFunc) http.Handler {
		return authMiddleware(csrfMiddleware(h.withPanicRecovery(handler)))
	}

	mux.Handle("/api/v1/cycle/run", wrap(h.handleRunCycle))
	mux.Handle("/api/v1/symbols", wrap(h.handleSymbols))
	mux.Handle("/api/v1/symbols/reset", wrap(h.handleResetSymbols))
	mux.Handle("/api/v1/config", wrap(h.handleGetConfig))
	mux.Handle("/api/v1/config/interval", wrap(h.handleSetInterval))
	mux.Handle("/api/v1/health", wrap(h.handleDetailedHealth))
}

// ---------------------------------------------------------------------------
// POST /api/v1/cycle/run
// ---------------------------------------------------------------------------

type runCycleRequest struct {
	Symbols []string `json:"symbols"`
	TraceID string   `json:"trace_id"`
}

func (h *APIHandler) handleRunCycle(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	claims := auth.ClaimsFromContext(r.Context())
	if claims == nil {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	// Per-user token bucket gated by the authenticated tier. Keyed by
	// JWT subject so two tabs / devices on the same account share one
	// bucket (correct: one user, one cost centre).
	limiter := h.cycleLimiterForClaims(claims)
	if !limiter.Allow(claims.UserID) {
		rpm, _ := h.authCfg.CycleRateLimitForTier(claims.Tier)
		if claims.Role == auth.RoleAdmin {
			rpm = h.authCfg.TierProManagedCycleRPM
		}
		retryAfter := 60 / max(rpm, 1)
		w.Header().Set("Retry-After", fmt.Sprintf("%d", retryAfter))
		h.log.Info().
			Str("user_id", claims.UserID).
			Str("tier", claims.Tier).
			Int("rpm", rpm).
			Msg("cycle_run_rate_limited")
		writeJSONError(w, http.StatusTooManyRequests, "too many cycle requests; please slow down")
		return
	}

	var req runCycleRequest
	if r.Body != nil && r.ContentLength > 0 {
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeJSONError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
			return
		}
	}

	userID := claims.UserID
	symbols := req.Symbols
	if len(symbols) == 0 {
		symbols = h.symbolStore.GetActiveSymbols(r.Context(), userID)
	}

	// ------------------------------------------------------------------
	// LLM quota pre-flight (Audit ref: ADMIN-QUOTA-7).
	//
	// Skip the cycle entirely when the user is on the platform key and
	// has already exhausted a cap. Saves the TA + Macro + RAG cost AND
	// surfaces a typed event so the SPA opens the dedicated quota modal
	// instead of a generic CYCLE_FAILED.
	//
	// Nil-tolerance: when METERING_ENABLED=false the stores can be nil;
	// the pre-flight is a no-op in that case (the metering layer is
	// disabled, so there is no quota to check).
	// ------------------------------------------------------------------
	if h.quotaPolicyStore != nil && h.usageStore != nil {
		if blocked, body, retryAfter := h.preflightLLMQuota(r, claims); blocked {
			w.Header().Set("Retry-After", strconv.Itoa(retryAfter))
			writeJSON(w, http.StatusTooManyRequests, body)
			return
		}
	}

	h.log.Info().
		Strs("symbols", symbols).
		Str("trace_id", req.TraceID).
		Str("user_id", userID).
		Str("tier", claims.Tier).
		Msg("dashboard_run_cycle_triggered")

	outputs := h.orchestrator.RunCycle(r.Context(), symbols, req.TraceID)

	results := make([]map[string]interface{}, 0, len(outputs))
	for _, out := range outputs {
		entry := map[string]interface{}{
			"cycle_status":  string(out.CycleStatus),
			"cycle_outcome": string(out.CycleOutcome),
			"phase_reached": string(out.PhaseReached),
			"symbol":        out.Symbol,
			"duration_ms":   out.DurationMs,
			"trace_id":      out.TraceID,
			"error":         out.Error,
			"error_stage":   out.ErrorStage,
		}
		if out.ProcessorOutput != nil {
			entry["processor_output"] = out.ProcessorOutput
		}
		if out.GuardResult != nil {
			entry["guard_result"] = out.GuardResult
		}
		if out.ExecutionResult != nil {
			entry["execution_result"] = out.ExecutionResult
		}
		results = append(results, entry)
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{"outputs": results})
}

// preflightLLMQuota runs the shared LLMQuotaPreflight helper and, on
// block, emits the user-scoped LLM_QUOTA_EXCEEDED event AND returns
// the structured 429 body. The helper itself owns tier resolution,
// policy load, enforced-gate, and the read-only usage check; the only
// site-specific logic kept here is the source="preflight" tag and the
// HTTP-shaped log line.
//
// Failure posture (delegated to the helper):
//   * Policy lookup error -> not blocked (helper returns Blocked=false
//     and the error; we log + return so the caller proceeds).
//   * Usage lookup error -> same.
//   * Block dimension hit -> blocked.
func (h *APIHandler) preflightLLMQuota(
	r *http.Request,
	claims *auth.Claims,
) (bool, map[string]interface{}, int) {
	outcome, err := billingstore.LLMQuotaPreflight(
		r.Context(),
		h.quotaPolicyStore,
		h.usageStore,
		billingstore.LLMQuotaPreflightCaller{
			UserID: claims.UserID,
			Role:   string(claims.Role),
			Tier:   claims.Tier,
		},
	)
	if err != nil {
		h.log.Warn().
			Err(err).
			Str("user_id", claims.UserID).
			Str("tier", outcome.Tier).
			Msg("cycle_preflight_failed")
		return false, nil, 0
	}
	if !outcome.Blocked {
		return false, nil, 0
	}

	resetsAt := outcome.ResetsAt.UTC().Format(time.RFC3339)

	// Emit a user-scoped LLM_QUOTA_EXCEEDED event so any other SPA tab
	// the user has open also opens the quota modal in lock-step.
	h.transport.Publish(r.Context(),
		alert.NewEvent(
			alert.SourceGateway,
			alert.TypeLLMQuotaExceeded,
			alert.SeverityWarning,
			"Your AI usage limit for this window has been reached.",
		).
			WithUserID(claims.UserID).
			WithDetails(map[string]interface{}{
				"dimension":   outcome.Dimension,
				"limit":       outcome.Limit,
				"used":        outcome.Used,
				"requested":   outcome.Requested,
				"resets_at":   resetsAt,
				"retry_after": outcome.RetryAfter,
				"is_admin":    outcome.IsAdmin,
				"source":      "preflight",
			}),
	)

	h.log.Info().
		Str("user_id", claims.UserID).
		Str("tier", outcome.Tier).
		Str("dimension", outcome.Dimension).
		Int64("limit", outcome.Limit).
		Int64("used", outcome.Used).
		Bool("is_admin", outcome.IsAdmin).
		Msg("cycle_preflight_quota_blocked")

	return true, map[string]interface{}{
		// Single canonical key (Audit ref: ADMIN-QUOTA-AUDIT-V2-9).
		"error_code":  "llm_quota_exceeded",
		"message":     "Your AI usage limit for this window has been reached.",
		"dimension":   outcome.Dimension,
		"limit":       outcome.Limit,
		"used":        outcome.Used,
		"requested":   outcome.Requested,
		"resets_at":   resetsAt,
		"retry_after": outcome.RetryAfter,
		"is_admin":    outcome.IsAdmin,
	}, outcome.RetryAfter
}

// ---------------------------------------------------------------------------
// GET  /api/v1/symbols
// PUT  /api/v1/symbols
// ---------------------------------------------------------------------------

type setSymbolsRequest struct {
	Symbols []string `json:"symbols"`
}

func (h *APIHandler) handleSymbols(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.getSymbols(w, r)
	case http.MethodPut:
		h.setSymbols(w, r)
	default:
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (h *APIHandler) getSymbols(w http.ResponseWriter, r *http.Request) {
	userID := auth.UserIDFromContext(r.Context())
	symbols := h.symbolStore.GetActiveSymbols(r.Context(), userID)

	claims := auth.ClaimsFromContext(r.Context())
	if claims != nil && claims.Role != "admin" && claims.Tier == "free" && len(symbols) > 1 {
		symbols = symbols[:1]
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"symbols": symbols,
		"source":  "redis",
	})
}

func (h *APIHandler) setSymbols(w http.ResponseWriter, r *http.Request) {
	var req setSymbolsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSONError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	if len(req.Symbols) == 0 {
		writeJSONError(w, http.StatusBadRequest, "symbols array must not be empty")
		return
	}

	claims := auth.ClaimsFromContext(r.Context())
	if claims != nil && claims.Role != "admin" && claims.Tier == "free" && len(req.Symbols) > 1 {
		h.transport.Publish(r.Context(),
			alert.NewEvent(alert.SourceGateway, alert.TypeSymbolsChanged, alert.SeverityWarning,
				"Free tier is restricted to 1 active symbol. Upgrade to Pro for unlimited tracking.").
				WithUserID(claims.UserID).
				WithDetails(map[string]interface{}{
					"attempted_symbols": len(req.Symbols),
				}),
		)
		writeTierRequired(w,
			"Free tier is restricted to 1 active symbol. Upgrade to Pro for unlimited tracking.",
			"pro_byok",
			"unlimited_symbols",
		)
		return
	}

	if claims != nil && claims.Role != "admin" {
		if err := h.validateAgainstBrokerCatalog(r.Context(), req.Symbols); err != nil {
			writeJSONError(w, err.status, err.message)
			return
		}
	}

	userID := claims.UserID
	oldSymbols := h.symbolStore.GetActiveSymbols(r.Context(), userID)
	ok := h.symbolStore.SetActiveSymbols(r.Context(), userID, req.Symbols)
	active := h.symbolStore.GetActiveSymbols(r.Context(), userID)

	if ok {
		h.transport.Publish(r.Context(),
			alert.NewEvent(alert.SourceGateway, alert.TypeSymbolsChanged, alert.SeverityInfo,
				fmt.Sprintf("Active symbols changed: %s", strings.Join(active, ", "))).
				WithUserID(userID).
				WithDetails(map[string]interface{}{
					"old_symbols": oldSymbols,
					"new_symbols": active,
				}),
		)
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success":        ok,
		"active_symbols": active,
	})
}

type validationError struct {
	status  int
	message string
}

// validateAgainstBrokerCatalog rejects any submitted symbol that is
// not published by the user's currently connected broker. The
// catalog comes from the engine's /api/broker/symbols endpoint,
// which is populated lazily by BrokerSyncService and reflects the
// broker-actual names (e.g. EURUSDm on Exness) the EA returns from
// GET_ALL_SYMBOLS. Admins bypass this check so platform operators
// can seed defaults without a connected broker.
func (h *APIHandler) validateAgainstBrokerCatalog(ctx context.Context, requested []string) *validationError {
	catalog, err := h.engine.GetJSON(ctx, "/api/broker/symbols")
	if err != nil {
		h.log.Error().Err(err).Msg("symbols_catalog_fetch_failed")
		return &validationError{
			status:  http.StatusBadGateway,
			message: "could not verify symbols against broker catalogue; try again in a moment",
		}
	}
	rawList, _ := catalog["symbols"].([]interface{})
	known := make(map[string]struct{}, len(rawList))
	for _, entry := range rawList {
		obj, ok := entry.(map[string]interface{})
		if !ok {
			continue
		}
		name, ok := obj["name"].(string)
		if !ok || strings.TrimSpace(name) == "" {
			continue
		}
		known[strings.TrimSpace(name)] = struct{}{}
	}
	if len(known) == 0 {
		return &validationError{
			status:  http.StatusFailedDependency,
			message: "broker catalogue is empty; connect a broker before configuring symbols",
		}
	}
	unknown := make([]string, 0)
	for _, sym := range requested {
		trimmed := strings.TrimSpace(sym)
		if trimmed == "" {
			continue
		}
		if _, ok := known[trimmed]; !ok {
			unknown = append(unknown, trimmed)
		}
	}
	if len(unknown) > 0 {
		return &validationError{
			status:  http.StatusBadRequest,
			message: "symbols not published by your broker: " + strings.Join(unknown, ", "),
		}
	}
	return nil
}

// ---------------------------------------------------------------------------
// POST /api/v1/symbols/reset
// ---------------------------------------------------------------------------

func (h *APIHandler) handleResetSymbols(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	userID := auth.UserIDFromContext(r.Context())
	oldSymbols := h.symbolStore.GetActiveSymbols(r.Context(), userID)
	ok := h.symbolStore.ResetToDefaults(r.Context(), userID)
	active := h.symbolStore.GetActiveSymbols(r.Context(), userID)

	// Free-tier defense-in-depth: ResetToDefaults writes the full default list
	// (typically 8 symbols). For a Free non-admin user, persist only the first
	// symbol so the stored state matches the 1-symbol policy. Without this,
	// the scheduler truncates at execution time but the persisted state stays
	// wrong, and any future read path that doesn't truncate inherits the bypass.
	claims := auth.ClaimsFromContext(r.Context())
	if ok && claims != nil && claims.Role != "admin" && claims.Tier == "free" && len(active) > 1 {
		if h.symbolStore.SetActiveSymbols(r.Context(), userID, active[:1]) {
			active = h.symbolStore.GetActiveSymbols(r.Context(), userID)
		}
	}

	if ok {
		h.transport.Publish(r.Context(),
			alert.NewEvent(alert.SourceGateway, alert.TypeSymbolsChanged, alert.SeverityInfo,
				fmt.Sprintf("Symbols reset to defaults: %s", strings.Join(active, ", "))).
				WithUserID(userID).
				WithDetails(map[string]interface{}{
					"old_symbols": oldSymbols,
					"new_symbols": active,
					"source":      "reset_to_defaults",
				}),
		)
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success":        ok,
		"active_symbols": active,
	})
}

// ---------------------------------------------------------------------------
// GET /api/v1/config
// ---------------------------------------------------------------------------

func (h *APIHandler) handleGetConfig(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	userID := auth.UserIDFromContext(r.Context())
	activeSymbols := h.symbolStore.GetActiveSymbols(r.Context(), userID)

	// Read this user's interval (from Redis or config default).
	userInterval := h.scheduler.CurrentIntervalForUser(r.Context(), userID)

	source := "gateway_config"
	persisted := h.settingsStore.Load(r.Context(), userID)
	if persisted.CycleIntervalSeconds > 0 {
		source = "redis"
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"enabled":                 h.cfg.Enabled,
		"cycle_interval_seconds":  userInterval,
		"cycle_timeout_seconds":   h.cfg.CycleTimeoutSeconds,
		"max_concurrent_symbols":  h.cfg.MaxConcurrentSymbols,
		"ta_cache_ttl_seconds":    h.cfg.TACacheTTLSeconds,
		"macro_cache_ttl_seconds": h.cfg.MacroCacheTTLSeconds,
		"max_cycle_retries":       h.cfg.MaxCycleRetries,
		"default_symbols":         h.cfg.DefaultSymbols,
		"active_symbols":          activeSymbols,
		"active_symbols_source":   source,
		"execution_enabled":       h.cfg.ExecutionEnabled,
	})
}

// ---------------------------------------------------------------------------
// PUT /api/v1/config/interval
// ---------------------------------------------------------------------------

type setIntervalRequest struct {
	IntervalSeconds int `json:"interval_seconds"`
}

func (h *APIHandler) handleSetInterval(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	var req setIntervalRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSONError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	if req.IntervalSeconds < 60 {
		writeJSONError(w, http.StatusBadRequest, fmt.Sprintf("interval_seconds must be >= 60, got %d", req.IntervalSeconds))
		return
	}
	if req.IntervalSeconds > 86400 {
		writeJSONError(w, http.StatusBadRequest, fmt.Sprintf("interval_seconds must be <= 86400 (24h), got %d", req.IntervalSeconds))
		return
	}

	// Free tier users do not get automated scheduling — block interval changes.
	claims := auth.ClaimsFromContext(r.Context())
	if claims != nil && claims.Role != "admin" && claims.Tier == "free" {
		writeTierRequired(w,
			"Automated scheduling is not available on the Free tier. Upgrade to Pro to configure cycle intervals.",
			"pro_byok",
			"automated_scheduling",
		)
		return
	}

	userID := auth.UserIDFromContext(r.Context())
	oldInterval := h.scheduler.CurrentIntervalForUser(r.Context(), userID)

	// Persist and update this user's interval only. Other users are unaffected.
	h.scheduler.UpdateUserInterval(r.Context(), userID, time.Duration(req.IntervalSeconds)*time.Second)

	h.log.Info().
		Str("user_id", userID).
		Int("old_interval_seconds", oldInterval).
		Int("new_interval_seconds", req.IntervalSeconds).
		Msg("cycle_interval_updated_via_dashboard_rest")

	h.transport.Publish(r.Context(),
		alert.NewEvent(alert.SourceGateway, alert.TypeIntervalChanged, alert.SeverityInfo,
			fmt.Sprintf("Cycle interval changed from %ds to %ds", oldInterval, req.IntervalSeconds)).
			WithUserID(userID).
			WithDetails(map[string]interface{}{
				"old_interval_seconds": oldInterval,
				"new_interval_seconds": req.IntervalSeconds,
			}),
	)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success":                  true,
		"current_interval_seconds": req.IntervalSeconds,
		"message":                  fmt.Sprintf("Cycle interval updated to %d seconds. Your scheduler goroutine will pick up the change within 5 minutes.", req.IntervalSeconds),
	})
}

// ---------------------------------------------------------------------------
// GET /api/v1/health
// ---------------------------------------------------------------------------

func (h *APIHandler) handleDetailedHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	ctx := r.Context()
	redisOK := h.redis.HealthCheck(ctx)
	engineOK := h.engine.HealthCheck(ctx)

	healthStatus := "ok"
	if !redisOK || !engineOK {
		healthStatus = "degraded"
	}

	activeCycles := int(observability.ReadGaugeValue(observability.GatewayActiveCycles))

	statusCode := http.StatusOK
	if healthStatus == "degraded" {
		statusCode = http.StatusServiceUnavailable
	}

	writeJSON(w, statusCode, map[string]interface{}{
		"status":           healthStatus,
		"redis_connected":  redisOK,
		"engine_connected": engineOK,
		"active_cycles":    activeCycles,
	})
}

// ---------------------------------------------------------------------------
// Shared utilities
// ---------------------------------------------------------------------------

// withPanicRecovery wraps an HTTP handler with panic recovery.
func (h *APIHandler) withPanicRecovery(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				observability.LogPanicRecovery(h.log, rec, r.URL.Path)
				writeJSONError(w, http.StatusInternalServerError, "internal server error")
			}
		}()
		next(w, r)
	}
}

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func writeJSONError(w http.ResponseWriter, status int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": message})
}

// writeTierRequired writes a structured 403 response the SPA can
// match exactly to decide whether to surface the "Upgrade Required"
// modal. PRACTICE.md #2: a 403 from any non-tier-gated endpoint
// (CSRF mismatch, expired cookie race, server bug) must NOT trigger
// an upgrade prompt; the SPA distinguishes by `error_code` rather
// than guessing from the URL prefix.
//
// requiredTier is the smallest paid tier that unlocks the feature
// (currently "pro_byok" or "pro_managed"). featureKey is a short,
// stable identifier the SPA can use to deep-link the upsell to the
// right tier card; it is not localised text.
func writeTierRequired(w http.ResponseWriter, message, requiredTier, featureKey string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusForbidden)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"error":         message,
		"error_code":    "tier_required",
		"required_tier": requiredTier,
		"feature":       featureKey,
	})
}
