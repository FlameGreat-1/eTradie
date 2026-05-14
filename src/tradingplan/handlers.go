package tradingplan

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"net/http"
	"runtime/debug"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/tradingsystem"
)

const (
	internalAuthHeader   = "X-Internal-Auth"
	internalUserIDHeader = "X-User-Id"
)

// EngineDispatcher is the minimal interface the handler needs to fire
// the asynchronous engine LLM call. Defined here (and implemented in
// main / container) so the package does not depend on the infra
// package and unit tests can substitute a fake dispatcher.
//
// Dispatch MUST return quickly: it kicks off the generation and
// returns. The engine eventually posts the finished plan back to
// /internal/trading-plan/callback. A non-nil error from Dispatch is
// treated as a hard failure and the row is flipped to status='failed'.
type EngineDispatcher interface {
	Dispatch(ctx context.Context, req GenerationRequest) error
}

// SystemReader is the minimal projection of the tradingsystem store
// the handler needs. Declared here so tests can stub it without
// pulling in a real Postgres pool.
type SystemReader interface {
	Get(ctx context.Context, userID string) (*tradingsystem.Record, error)
}

// BalanceProvider returns the user's active broker balance. The
// implementation lives in the container and proxies to the engine.
// Returning (0, BalanceSourceFallback, nil) is the documented
// no-broker / no-balance fallback path — not an error.
type BalanceProvider interface {
	GetBalance(ctx context.Context, userID string) (amount float64, currency string, source BalanceSource, err error)
}

// Handler serves the trading-plan REST API.
type Handler struct {
	store          *Store
	sysReader      SystemReader
	dispatcher     EngineDispatcher
	balance        BalanceProvider
	internalSecret string
	log            zerolog.Logger

	generateLimiter *userRateLimiter
	editLimiter     *userRateLimiter
	resetLimiter    *userRateLimiter
}

// NewHandler builds a Handler. internalSecret is the same value the
// engine sends in X-Internal-Auth; pass an empty string only in
// tests. A deployed gateway with an empty secret refuses every
// internal call (safe by default).
//
// Either of sysReader, dispatcher, balance may be nil to disable the
// generation surface (the GET/PUT/RESET endpoints still work). This
// lets the gateway boot cleanly in environments where the engine is
// not reachable and yields a 503 on /generate instead of crashing.
func NewHandler(
	store *Store,
	sysReader SystemReader,
	dispatcher EngineDispatcher,
	balance BalanceProvider,
	internalSecret string,
	log zerolog.Logger,
) *Handler {
	return &Handler{
		store:           store,
		sysReader:       sysReader,
		dispatcher:      dispatcher,
		balance:         balance,
		internalSecret:  strings.TrimSpace(internalSecret),
		log:             log,
		generateLimiter: newUserRateLimiter(5, time.Hour),
		editLimiter:     newUserRateLimiter(30, time.Minute),
		resetLimiter:    newUserRateLimiter(10, time.Minute),
	}
}

// Close releases background goroutines owned by the rate limiters.
func (h *Handler) Close() {
	h.generateLimiter.Close()
	h.editLimiter.Close()
	h.resetLimiter.Close()
}

// RegisterRoutes mounts the public REST surface.
func (h *Handler) RegisterRoutes(
	mux *http.ServeMux,
	authMiddleware func(http.Handler) http.Handler,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	wrap := func(handler http.HandlerFunc) http.Handler {
		return authMiddleware(csrfMiddleware(h.withPanicRecovery(handler)))
	}

	mux.Handle("/api/v1/trading-plan", wrap(h.handlePlan))
	mux.Handle("/api/v1/trading-plan/status", wrap(h.handleStatus))
	mux.Handle("/api/v1/trading-plan/generate", wrap(h.handleGenerate))
	mux.Handle("/api/v1/trading-plan/reset", wrap(h.handleReset))
}

// RegisterInternalRoutes mounts the engine-callable surface.
func (h *Handler) RegisterInternalRoutes(mux *http.ServeMux) {
	mux.Handle("/internal/trading-plan/callback", h.withPanicRecovery(h.handleInternalCallback))
	mux.Handle("/internal/trading-plan/fail", h.withPanicRecovery(h.handleInternalFail))
}

func (h *Handler) withPanicRecovery(next http.HandlerFunc) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				h.log.Error().
					Interface("panic", rec).
					Str("path", r.URL.Path).
					Str("method", r.Method).
					Bytes("stack", debug.Stack()).
					Msg("trading_plan_panic_recovered")
				writeError(w, http.StatusInternalServerError, "internal server error")
			}
		}()
		next(w, r)
	})
}

// ---------------------------------------------------------------------------
// GET / PUT /api/v1/trading-plan
// ---------------------------------------------------------------------------

func (h *Handler) handlePlan(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.getPlan(w, r)
	case http.MethodPut:
		h.putPlan(w, r)
	default:
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (h *Handler) getPlan(w http.ResponseWriter, r *http.Request) {
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	rec, err := h.store.Get(r.Context(), userID)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			TradingPlanFetchTotal.WithLabelValues(outcomeEmpty).Inc()
			writeJSON(w, http.StatusOK, map[string]interface{}{
				"status":   string(StatusNone),
				"version":  0,
				"plan":     nil,
				"has_plan": false,
			})
			return
		}
		TradingPlanFetchTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_get_failed")
		writeError(w, http.StatusInternalServerError, "failed to load trading plan")
		return
	}
	if rec.Plan != nil {
		TradingPlanFetchTotal.WithLabelValues(outcomeHit).Inc()
	} else {
		TradingPlanFetchTotal.WithLabelValues(outcomeEmpty).Inc()
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":     string(rec.Status),
		"version":    rec.Version,
		"plan":       rec.Plan,
		"has_plan":   rec.Plan != nil,
		"last_error": rec.LastError,
		"created_at": rec.CreatedAt,
		"updated_at": rec.UpdatedAt,
	})
}

// putPlan handles in-app manual edits. Does NOT trigger an LLM call;
// it persists whatever shape the SPA sends after the user changes a
// cell, adds a journal row, or rewrites an objective.
func (h *Handler) putPlan(w http.ResponseWriter, r *http.Request) {
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	if !h.editLimiter.Allow(userID) {
		TradingPlanRateLimitedTotal.WithLabelValues(endpointEdit).Inc()
		w.Header().Set("Retry-After", "60")
		writeError(w, http.StatusTooManyRequests, "too many edit requests; try again shortly")
		return
	}

	// 256 KB is generous: a fully-populated 200-row journal sits at ~80 KB.
	r.Body = http.MaxBytesReader(w, r.Body, 256*1024)

	var p Plan
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&p); err != nil {
		TradingPlanEditTotal.WithLabelValues(outcomeValidationError).Inc()
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	if err := Validate(&p); err != nil {
		var verr *ValidationError
		if errors.As(err, &verr) {
			TradingPlanEditTotal.WithLabelValues(outcomeValidationError).Inc()
			writeJSON(w, http.StatusUnprocessableEntity, map[string]interface{}{
				"error":  verr.Message,
				"fields": verr.Fields,
			})
			return
		}
		TradingPlanEditTotal.WithLabelValues(outcomeValidationError).Inc()
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	rec, err := h.store.UpdatePlanContent(r.Context(), userID, &p)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			TradingPlanEditTotal.WithLabelValues(outcomeValidationError).Inc()
			writeError(w, http.StatusNotFound, "no trading plan to edit; generate one first")
			return
		}
		TradingPlanEditTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_edit_failed")
		writeError(w, http.StatusInternalServerError, "failed to save trading plan")
		return
	}

	TradingPlanEditTotal.WithLabelValues(outcomeSuccess).Inc()
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":     string(rec.Status),
		"version":    rec.Version,
		"plan":       rec.Plan,
		"has_plan":   true,
		"created_at": rec.CreatedAt,
		"updated_at": rec.UpdatedAt,
	})
}

// ---------------------------------------------------------------------------
// GET /api/v1/trading-plan/status
// ---------------------------------------------------------------------------

func (h *Handler) handleStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	view, err := h.store.GetStatus(r.Context(), userID)
	if err != nil {
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_status_failed")
		writeError(w, http.StatusInternalServerError, "failed to load status")
		return
	}
	writeJSON(w, http.StatusOK, view)
}

// ---------------------------------------------------------------------------
// POST /api/v1/trading-plan/generate
//
// Reads the user's Trading System + broker balance, marks the row as
// 'generating', and dispatches the LLM call. The engine posts the
// completed plan back via /internal/trading-plan/callback.
//
// Optional body:
//   { "fallback_balance": 10000, "fallback_currency": "USD" }
// fallback_balance is used ONLY when the broker reports 0 / is
// unavailable. The currency, if omitted, defaults to USD.
// ---------------------------------------------------------------------------

type generateRequest struct {
	FallbackBalance  float64 `json:"fallback_balance"`
	FallbackCurrency string  `json:"fallback_currency"`
}

func (h *Handler) handleGenerate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	if h.dispatcher == nil || h.sysReader == nil {
		writeError(w, http.StatusServiceUnavailable,
			"trading plan generation is temporarily disabled")
		return
	}
	if !h.generateLimiter.Allow(userID) {
		TradingPlanGenerateTotal.WithLabelValues(outcomeThrottled).Inc()
		TradingPlanRateLimitedTotal.WithLabelValues(endpointGenerate).Inc()
		w.Header().Set("Retry-After", "3600")
		writeError(w, http.StatusTooManyRequests,
			"too many plan generations; try again later")
		return
	}

	start := time.Now()
	defer func() {
		TradingPlanGenerateDuration.Observe(time.Since(start).Seconds())
	}()

	// Body is optional. Treat any decode failure (incl. empty body)
	// as zero-value fallback hints rather than rejecting the request.
	var body generateRequest
	if r.ContentLength > 0 {
		r.Body = http.MaxBytesReader(w, r.Body, 4*1024)
		dec := json.NewDecoder(r.Body)
		dec.DisallowUnknownFields()
		_ = dec.Decode(&body)
	}

	sysRec, err := h.sysReader.Get(r.Context(), userID)
	if err != nil {
		if errors.Is(err, tradingsystem.ErrNotFound) || sysRec == nil {
			TradingPlanGenerateTotal.WithLabelValues(outcomeValidationError).Inc()
			writeError(w, http.StatusPreconditionFailed,
				"build your trading system before generating a plan")
			return
		}
		TradingPlanGenerateTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_sys_read_failed")
		writeError(w, http.StatusInternalServerError, "failed to load trading system")
		return
	}
	if sysRec.Status != tradingsystem.StatusActive || sysRec.Profile == nil {
		TradingPlanGenerateTotal.WithLabelValues(outcomeValidationError).Inc()
		writeError(w, http.StatusPreconditionFailed,
			"trading system must be active before generating a plan")
		return
	}

	profileJSON, err := json.Marshal(sysRec.Profile)
	if err != nil {
		TradingPlanGenerateTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_profile_marshal_failed")
		writeError(w, http.StatusInternalServerError, "failed to serialise trading system")
		return
	}

	// Resolve balance.  A nil BalanceProvider or a 0 result triggers
	// the fallback path, with fallback_balance from the request body
	// (or 10_000 if the body did not specify one).
	var (
		balance     float64
		balanceCcy  string
		balanceSrc  BalanceSource
		balanceErr  error
		fallbackUsd = 10000.0
	)
	if body.FallbackBalance > 0 {
		fallbackUsd = body.FallbackBalance
	}
	fallbackCcy := strings.TrimSpace(strings.ToUpper(body.FallbackCurrency))
	if fallbackCcy == "" {
		fallbackCcy = "USD"
	}
	if h.balance != nil {
		balance, balanceCcy, balanceSrc, balanceErr = h.balance.GetBalance(r.Context(), userID)
		if balanceErr != nil {
			h.log.Warn().Err(balanceErr).Str("user_id", userID).Msg("trading_plan_balance_lookup_failed")
		}
	}
	if balance <= 0 || balanceCcy == "" || balanceSrc == "" {
		balance = fallbackUsd
		balanceCcy = fallbackCcy
		balanceSrc = BalanceSourceFallback
	}
	TradingPlanBalanceSourceTotal.WithLabelValues(string(balanceSrc)).Inc()

	if err := h.store.MarkGenerating(r.Context(), userID); err != nil {
		TradingPlanGenerateTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_mark_generating_failed")
		writeError(w, http.StatusInternalServerError, "failed to record generation state")
		return
	}

	req := GenerationRequest{
		UserID:          userID,
		Balance:         balance,
		BalanceCurrency: balanceCcy,
		BalanceSource:   balanceSrc,
		ProfileVersion:  sysRec.Version,
		ProfileJSON:     profileJSON,
	}

	// Dispatch with a generous timeout independent of the user's
	// request context so a slow client (or a flaky network on the
	// browser side) cannot cancel an LLM call mid-flight.
	dispatchCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	go func() {
		defer cancel()
		if err := h.dispatcher.Dispatch(dispatchCtx, req); err != nil {
			h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_dispatch_failed")
			// Use a fresh context with a 5-second timeout because the
			// dispatch context is about to be cancelled.
			failCtx, failCancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer failCancel()
			msg := "failed to start plan generation"
			if markErr := h.store.MarkFailed(failCtx, userID, msg); markErr != nil {
				h.log.Error().Err(markErr).Str("user_id", userID).Msg("trading_plan_mark_failed_after_dispatch")
			}
		}
	}()

	TradingPlanGenerateTotal.WithLabelValues(outcomeQueued).Inc()
	h.log.Info().
		Str("user_id", userID).
		Int("profile_version", sysRec.Version).
		Float64("balance", balance).
		Str("balance_source", string(balanceSrc)).
		Msg("trading_plan_generation_dispatched")

	writeJSON(w, http.StatusAccepted, map[string]interface{}{
		"status":  string(StatusGenerating),
		"message": "plan generation in progress",
	})
}

// ---------------------------------------------------------------------------
// POST /api/v1/trading-plan/reset
// ---------------------------------------------------------------------------

func (h *Handler) handleReset(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	if !h.resetLimiter.Allow(userID) {
		TradingPlanRateLimitedTotal.WithLabelValues(endpointReset).Inc()
		w.Header().Set("Retry-After", "60")
		writeError(w, http.StatusTooManyRequests, "too many reset requests; try again shortly")
		return
	}
	if err := h.store.Reset(r.Context(), userID); err != nil {
		TradingPlanResetTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_reset_failed")
		writeError(w, http.StatusInternalServerError, "failed to reset")
		return
	}
	TradingPlanResetTotal.WithLabelValues(outcomeSuccess).Inc()
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":   string(StatusNone),
		"version":  0,
		"has_plan": false,
	})
}

// ---------------------------------------------------------------------------
// Internal: POST /internal/trading-plan/callback
//
// Body shape:
//   { "user_id": "...", "plan": { ...Plan... } }
//
// Authenticated via constant-time HMAC against the shared secret.
// ---------------------------------------------------------------------------

type internalCallbackBody struct {
	UserID string `json:"user_id"`
	Plan   *Plan  `json:"plan"`
}

func (h *Handler) handleInternalCallback(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.verifyInternalSecret(r) {
		TradingPlanCallbackTotal.WithLabelValues(outcomeUnauthorized).Inc()
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	// 512 KB ceiling because the LLM response (with a freshly seeded
	// 65-row journal) is comfortably under 50 KB. The headroom
	// absorbs verbose narrative bullets without risking memory abuse.
	r.Body = http.MaxBytesReader(w, r.Body, 512*1024)

	var body internalCallbackBody
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&body); err != nil {
		TradingPlanCallbackTotal.WithLabelValues(outcomeValidationError).Inc()
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	userID := strings.TrimSpace(body.UserID)
	if userID == "" {
		userID = strings.TrimSpace(r.Header.Get(internalUserIDHeader))
	}
	if userID == "" {
		TradingPlanCallbackTotal.WithLabelValues(outcomeValidationError).Inc()
		writeError(w, http.StatusBadRequest, "user_id is required")
		return
	}
	if body.Plan == nil {
		TradingPlanCallbackTotal.WithLabelValues(outcomeValidationError).Inc()
		writeError(w, http.StatusBadRequest, "plan is required")
		return
	}

	if err := Validate(body.Plan); err != nil {
		TradingPlanCallbackTotal.WithLabelValues(outcomeValidationError).Inc()
		var verr *ValidationError
		if errors.As(err, &verr) {
			h.log.Warn().
				Str("user_id", userID).
				Interface("fields", verr.Fields).
				Msg("trading_plan_callback_validation_failed")
			writeJSON(w, http.StatusUnprocessableEntity, map[string]interface{}{
				"error":  verr.Message,
				"fields": verr.Fields,
			})
			return
		}
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	rec, err := h.store.Save(r.Context(), userID, body.Plan)
	if err != nil {
		TradingPlanCallbackTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_callback_save_failed")
		writeError(w, http.StatusInternalServerError, "failed to persist trading plan")
		return
	}

	// Track end-to-end LLM call duration: callback time minus the
	// row's last update (which the dispatch path stamps as it flips
	// the row to 'generating').
	if !rec.UpdatedAt.IsZero() && !rec.CreatedAt.IsZero() {
		TradingPlanLLMCallDuration.Observe(time.Since(rec.CreatedAt).Seconds())
	}

	TradingPlanCallbackTotal.WithLabelValues(outcomeSuccess).Inc()
	h.log.Info().
		Str("user_id", userID).
		Int("version", rec.Version).
		Float64("balance", body.Plan.BalanceUsed).
		Str("balance_source", body.Plan.BalanceSourceKind).
		Msg("trading_plan_callback_persisted")

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"persisted": true,
		"version":   rec.Version,
	})
}

// internalFailBody is the engine's structured-failure callback.
//
// The message field is forwarded verbatim to the SPA, so the engine
// must scrub stack traces and internal IDs before posting.
type internalFailBody struct {
	UserID  string `json:"user_id"`
	Message string `json:"message"`
}

func (h *Handler) handleInternalFail(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.verifyInternalSecret(r) {
		TradingPlanCallbackTotal.WithLabelValues(outcomeUnauthorized).Inc()
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 4*1024)
	var body internalFailBody
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	userID := strings.TrimSpace(body.UserID)
	if userID == "" {
		userID = strings.TrimSpace(r.Header.Get(internalUserIDHeader))
	}
	if userID == "" {
		writeError(w, http.StatusBadRequest, "user_id is required")
		return
	}
	message := strings.TrimSpace(body.Message)
	if message == "" {
		message = "plan generation failed; please try again"
	}
	if err := h.store.MarkFailed(r.Context(), userID, message); err != nil {
		TradingPlanCallbackTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("trading_plan_mark_failed_callback")
		writeError(w, http.StatusInternalServerError, "failed to record failure state")
		return
	}
	h.log.Warn().Str("user_id", userID).Str("message", message).Msg("trading_plan_marked_failed")
	writeJSON(w, http.StatusOK, map[string]interface{}{"recorded": true})
}

// verifyInternalSecret performs a constant-time comparison of the
// X-Internal-Auth header against the configured shared secret. Uses
// the same SHA-256 pre-hash dance as tradingsystem so the secret
// length is never leaked via timing.
func (h *Handler) verifyInternalSecret(r *http.Request) bool {
	if h.internalSecret == "" {
		return false
	}
	provided := strings.TrimSpace(r.Header.Get(internalAuthHeader))
	if provided == "" {
		return false
	}
	want := sha256.Sum256([]byte(h.internalSecret))
	got := sha256.Sum256([]byte(provided))
	return hmac.Equal(want[:], got[:])
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func writeJSON(w http.ResponseWriter, status int, body interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
