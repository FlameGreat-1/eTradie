package server

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/prometheus/client_golang/prometheus/testutil"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
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
	log           zerolog.Logger
}

// NewAPIHandler creates the dashboard REST API handler.
func NewAPIHandler(
	cfg *config.Config,
	orchestrator *pipeline.Orchestrator,
	symbolStore *symbolstore.Store,
	settingsStore *settingsstore.Store,
	scheduler *pipeline.Scheduler,
	redis *infra.RedisClient,
	engine *infra.EngineHTTPClient,
	transport *alertredis.Transport,
) *APIHandler {
	return &APIHandler{
		orchestrator:  orchestrator,
		symbolStore:   symbolStore,
		settingsStore: settingsStore,
		scheduler:     scheduler,
		redis:         redis,
		engine:        engine,
		transport:     transport,
		cfg:           cfg,
		log:           observability.Logger("api_handler"),
	}
}

// RegisterRoutes mounts all dashboard API routes on the given mux.
func (h *APIHandler) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/api/v1/cycle/run", h.withPanicRecovery(h.handleRunCycle))
	mux.HandleFunc("/api/v1/symbols", h.withPanicRecovery(h.handleSymbols))
	mux.HandleFunc("/api/v1/symbols/reset", h.withPanicRecovery(h.handleResetSymbols))
	mux.HandleFunc("/api/v1/config", h.withPanicRecovery(h.handleGetConfig))
	mux.HandleFunc("/api/v1/config/interval", h.withPanicRecovery(h.handleSetInterval))
	mux.HandleFunc("/api/v1/health", h.withPanicRecovery(h.handleDetailedHealth))
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

	var req runCycleRequest
	if r.Body != nil && r.ContentLength > 0 {
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeJSONError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
			return
		}
	}

	symbols := req.Symbols
	if len(symbols) == 0 {
		symbols = h.symbolStore.GetActiveSymbols(r.Context())
	}

	h.log.Info().
		Strs("symbols", symbols).
		Str("trace_id", req.TraceID).
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
	symbols := h.symbolStore.GetActiveSymbols(r.Context())
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

	oldSymbols := h.symbolStore.GetActiveSymbols(r.Context())
	ok := h.symbolStore.SetActiveSymbols(r.Context(), req.Symbols)
	active := h.symbolStore.GetActiveSymbols(r.Context())

	if ok {
		h.transport.Publish(r.Context(),
			alert.NewEvent(alert.SourceGateway, alert.TypeSymbolsChanged, alert.SeverityInfo,
				fmt.Sprintf("Active symbols changed: %s", strings.Join(active, ", "))).
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

// ---------------------------------------------------------------------------
// POST /api/v1/symbols/reset
// ---------------------------------------------------------------------------

func (h *APIHandler) handleResetSymbols(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	oldSymbols := h.symbolStore.GetActiveSymbols(r.Context())
	ok := h.symbolStore.ResetToDefaults(r.Context())
	active := h.symbolStore.GetActiveSymbols(r.Context())

	if ok {
		h.transport.Publish(r.Context(),
			alert.NewEvent(alert.SourceGateway, alert.TypeSymbolsChanged, alert.SeverityInfo,
				fmt.Sprintf("Symbols reset to defaults: %s", strings.Join(active, ", "))).
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

	activeSymbols := h.symbolStore.GetActiveSymbols(r.Context())

	source := "gateway_config"
	persisted := h.settingsStore.Load(r.Context())
	if persisted.CycleIntervalSeconds > 0 {
		source = "redis"
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"enabled":                 h.cfg.Enabled,
		"cycle_interval_seconds":  h.scheduler.CurrentIntervalSeconds(),
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

	oldInterval := h.scheduler.CurrentIntervalSeconds()

	h.scheduler.UpdateInterval(time.Duration(req.IntervalSeconds) * time.Second)

	if err := h.settingsStore.SetCycleInterval(r.Context(), req.IntervalSeconds); err != nil {
		h.log.Warn().Err(err).Int("interval", req.IntervalSeconds).Msg("set_cycle_interval_persist_failed_using_in_memory")
	}

	h.log.Info().
		Int("old_interval_seconds", oldInterval).
		Int("new_interval_seconds", req.IntervalSeconds).
		Msg("cycle_interval_updated_via_dashboard_rest")

	h.transport.Publish(r.Context(),
		alert.NewEvent(alert.SourceGateway, alert.TypeIntervalChanged, alert.SeverityInfo,
			fmt.Sprintf("Cycle interval changed from %ds to %ds", oldInterval, req.IntervalSeconds)).
			WithDetails(map[string]interface{}{
				"old_interval_seconds": oldInterval,
				"new_interval_seconds": req.IntervalSeconds,
			}),
	)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success":                  true,
		"current_interval_seconds": req.IntervalSeconds,
		"message":                  fmt.Sprintf("Cycle interval updated to %d seconds. Takes effect immediately.", req.IntervalSeconds),
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

	activeCycles := int(testutil.ToFloat64(observability.GatewayActiveCycles))

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
