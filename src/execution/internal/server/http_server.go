package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/execution/internal/audit"
	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
	"github.com/flamegreat-1/etradie/src/execution/internal/state"
	"github.com/flamegreat-1/etradie/src/execution/internal/store"
)

// HTTPServer serves the dashboard-facing REST API and WebSocket notifications.
//
// Middleware chain for every protected route:
//
//	authMw -> csrfMw -> handler
//
// authMw populates the request context with the verified user claims;
// csrfMw enforces signed double-submit CSRF on POST/PUT/PATCH/DELETE
// and short-circuits safe methods. The WS upgrade is GET so it never
// hits the CSRF gate even when wrapped, but we keep WS outside the
// chain for clarity.
type HTTPServer struct {
	server          *http.Server
	state           *state.Manager
	broker          broker.Port
	settings        *store.SettingsStore
	auditLog        *audit.Logger
	transport       *alertredis.Transport
	log             zerolog.Logger
	symbolMetaCache sync.Map // symbol -> symbolMeta (cached forever)
}

// symbolMeta holds broker-sourced instrument metadata for the frontend.
type symbolMeta struct {
	Point  float64 `json:"point"`
	Digits int32   `json:"digits"`
}

// NewHTTPServer creates the execution HTTP API server.
func NewHTTPServer(
	port int,
	sm *state.Manager,
	bp broker.Port,
	ss *store.SettingsStore,
	al *audit.Logger,
	transport *alertredis.Transport,
	tokenService *auth.TokenService,
	authCfg *auth.Config,
) *HTTPServer {
	s := &HTTPServer{
		state:     sm,
		broker:    bp,
		settings:  ss,
		auditLog:  al,
		transport: transport,
		log:       observability.Logger("http_server"),
	}

	mux := http.NewServeMux()
	authMw := auth.RequireAuth(tokenService)
	csrfMw := auth.RequireCSRF(authCfg)

	wrap := func(h http.HandlerFunc) http.Handler {
		return authMw(csrfMw(http.HandlerFunc(h)))
	}

	// Dashboard REST API (all protected). RequireCSRF short-circuits
	// safe methods so wrapping GET-only routes is uniform and free.
	mux.Handle("/api/v1/settings", wrap(s.handleSettings))
	mux.Handle("/api/v1/state", wrap(s.handleState))
	mux.Handle("/api/v1/orders/cancel", wrap(s.handleCancelOrder))
	mux.Handle("/api/v1/account", wrap(s.handleAccount))

	// Section 7 Step B: audit replay endpoint.
	// Protected by service-token auth (same RequireAuth middleware).
	// CSRF is NOT applied because this is a GET-only operator endpoint
	// called by executionctl, not by the browser dashboard.
	mux.Handle("/internal/audit/replay", authMw(http.HandlerFunc(s.handleAuditReplay)))

	// WebSocket notifications (auth only; the WS handshake is GET and
	// the dashboard's WS client never POSTs, so CSRF is N/A here).
	mux.Handle("/ws/notifications", authMw(http.HandlerFunc(alert.WebSocketHandler(transport.LocalHub()))))

	// Ops endpoints (public).
	mux.HandleFunc("/health", s.handleHealth)
	mux.Handle("/metrics", promhttp.Handler())

	s.server = &http.Server{
		Addr:         fmt.Sprintf(":%d", port),
		Handler:      corsMiddleware(loadAllowedOrigins(), authCfg.CSRFHeader)(mux),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	return s
}

// loadAllowedOrigins reads the credentialed-CORS allow-list from env.
// Precedence:
//  1. EXECUTION_ALLOWED_ORIGINS (service-specific override)
//  2. ALLOWED_ORIGINS           (shared with engine + management)
func loadAllowedOrigins() map[string]bool {
	raw := strings.TrimSpace(os.Getenv("EXECUTION_ALLOWED_ORIGINS"))
	if raw == "" {
		raw = strings.TrimSpace(os.Getenv("ALLOWED_ORIGINS"))
	}
	if raw == "" {
		return map[string]bool{}
	}
	out := map[string]bool{}
	for _, part := range strings.Split(raw, ",") {
		if p := strings.TrimSpace(part); p != "" {
			out[p] = true
		}
	}
	return out
}

// Start begins serving HTTP. Blocks until the server stops.
func (s *HTTPServer) Start() error {
	s.log.Info().Str("addr", s.server.Addr).Msg("http_api_server_starting")
	err := s.server.ListenAndServe()
	if err == http.ErrServerClosed {
		return nil
	}
	return err
}

// Shutdown gracefully stops the HTTP server.
func (s *HTTPServer) Shutdown(ctx context.Context) error {
	s.log.Info().Msg("http_api_server_shutting_down")
	return s.server.Shutdown(ctx)
}

// corsMiddleware emits credentialed-CORS headers backed by an explicit
// allow-list. The Allow-Headers list includes the configured CSRF
// header name so renaming AUTH_CSRF_HEADER does not break preflights.
func corsMiddleware(allowed map[string]bool, csrfHeaderName string) func(http.Handler) http.Handler {
	csrfHeaderName = strings.TrimSpace(csrfHeaderName)
	if csrfHeaderName == "" {
		csrfHeaderName = "X-CSRF-Token"
	}
	allowHeaders := strings.Join([]string{
		"Content-Type",
		"Authorization",
		"X-Trace-ID",
		"X-Requested-With",
		csrfHeaderName,
	}, ", ")
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if origin != "" && allowed[origin] {
				w.Header().Set("Access-Control-Allow-Origin", origin)
				w.Header().Set("Access-Control-Allow-Credentials", "true")
				w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
				w.Header().Set("Access-Control-Allow-Headers", allowHeaders)
				w.Header().Set("Access-Control-Max-Age", "86400")
				w.Header().Add("Vary", "Origin")
			}

			if r.Method == http.MethodOptions {
				w.WriteHeader(http.StatusNoContent)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

// GET /api/v1/settings - Read all settings.
// PUT /api/v1/settings - Update settings.
func (s *HTTPServer) handleSettings(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		s.getSettings(w, r)
	case http.MethodPut:
		s.putSettings(w, r)
	default:
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

func (s *HTTPServer) getSettings(w http.ResponseWriter, r *http.Request) {
	userID := auth.UserIDFromContext(r.Context())
	defaults := store.Settings{
		ExecutionMode:       "AUTO",
		MaxConcurrentTrades: 3,
		DailyLossLimitPct:   3.0,
		WeeklyDrawdownPct:   5.0,
	}

	settings, err := s.settings.LoadAll(r.Context(), userID, defaults)
	if err != nil {
		s.log.Error().Err(err).Msg("get_settings_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "failed to load settings"})
		return
	}

	writeJSON(w, http.StatusOK, settings)
}

func (s *HTTPServer) putSettings(w http.ResponseWriter, r *http.Request) {
	var req store.Settings
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid JSON: " + err.Error()})
		return
	}

	req.ExecutionMode = strings.ToUpper(req.ExecutionMode)

	userID := auth.UserIDFromContext(r.Context())
	if err := s.settings.SaveAll(r.Context(), userID, &req); err != nil {
		s.log.Error().Err(err).Msg("put_settings_failed")
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	s.transport.Publish(r.Context(),
		alert.NewEvent(alert.SourceExecution, alert.TypeSettingsUpdated, alert.SeverityInfo,
			fmt.Sprintf("Settings updated: mode=%s, max_trades=%d", req.ExecutionMode, req.MaxConcurrentTrades)).
			WithUserID(userID).
			WithDetails(map[string]interface{}{
				"execution_mode":        req.ExecutionMode,
				"max_concurrent_trades": req.MaxConcurrentTrades,
				"daily_loss_limit_pct":  req.DailyLossLimitPct,
				"weekly_drawdown_pct":   req.WeeklyDrawdownPct,
			}),
	)

	writeJSON(w, http.StatusOK, req)
}

// GET /api/v1/state - Execution state.
func (s *HTTPServer) handleState(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	userID := auth.UserIDFromContext(r.Context())
	if err := s.state.Refresh(r.Context(), userID); err != nil {
		s.log.Error().Err(err).Msg("state_refresh_failed")
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "broker state refresh failed"})
		return
	}

	positions := s.state.Positions(userID)
	pending := s.state.PendingOrders(userID)
	account := s.state.Account(userID)

	var balance, equity float64
	if account != nil {
		balance = account.Balance
		equity = account.Equity
	}

	posMap := make(map[string]interface{}, len(positions))
	for _, p := range positions {
		posMap[p.Symbol] = p
	}

	meta := make(map[string]symbolMeta, len(positions))
	for _, p := range positions {
		if _, exists := meta[p.Symbol]; exists {
			continue
		}
		if cached, ok := s.symbolMetaCache.Load(p.Symbol); ok {
			meta[p.Symbol] = cached.(symbolMeta)
			continue
		}
		info, err := s.broker.GetInstrumentInfo(r.Context(), p.Symbol)
		if err != nil {
			s.log.Warn().Err(err).Str("symbol", p.Symbol).Msg("symbol_meta_fetch_failed")
			continue
		}
		sm := symbolMeta{Point: info.PipSize, Digits: info.Digits}
		s.symbolMetaCache.Store(p.Symbol, sm)
		meta[p.Symbol] = sm
	}

	resp := map[string]interface{}{
		"open_position_count": len(positions),
		"pending_order_count": len(pending),
		"daily_realized_pnl":  s.state.DailyPnL(userID),
		"weekly_realized_pnl": s.state.WeeklyPnL(userID),
		"account_balance":     balance,
		"account_equity":      equity,
		"open_positions":      posMap,
		"pending_orders":      pending,
		"symbol_meta":         meta,
	}

	writeJSON(w, http.StatusOK, resp)
}

// POST /api/v1/orders/cancel - Cancel a pending order.
func (s *HTTPServer) handleCancelOrder(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		OrderID string `json:"order_id"`
		Symbol  string `json:"symbol"`
		Reason  string `json:"reason"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid JSON: " + err.Error()})
		return
	}

	if req.OrderID == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "order_id is required"})
		return
	}
	if req.Reason == "" {
		req.Reason = "MANUAL"
	}

	userID := auth.UserIDFromContext(r.Context())
	if err := s.state.Refresh(r.Context(), userID); err != nil {
		s.log.Error().Err(err).Msg("cancel_order_state_refresh_failed")
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "broker state refresh failed"})
		return
	}

	ownsOrder := false
	for _, po := range s.state.PendingOrders(userID) {
		if po.OrderID == req.OrderID {
			ownsOrder = true
			break
		}
	}
	if !ownsOrder {
		writeJSON(w, http.StatusForbidden, map[string]interface{}{
			"success": false,
			"status":  "FORBIDDEN",
			"error":   "order not found in your pending orders",
		})
		return
	}

	if err := s.broker.CancelOrder(r.Context(), req.OrderID); err != nil {
		s.log.Error().Err(err).Str("order_id", req.OrderID).Msg("cancel_order_failed")
		writeJSON(w, http.StatusNotFound, map[string]interface{}{
			"success": false,
			"status":  "NOT_FOUND",
			"error":   err.Error(),
		})
		return
	}

	s.auditLog.LogOrderCancelled(r.Context(), req.OrderID, req.Symbol, req.Reason, "")

	s.transport.Publish(r.Context(),
		alert.NewEvent(alert.SourceExecution, alert.TypeOrderCancelled, alert.SeverityInfo,
			fmt.Sprintf("Order %s cancelled: %s", req.OrderID, req.Reason)).
			WithUserID(userID).
			WithSymbol(req.Symbol).
			WithDetails(map[string]interface{}{
				"order_id": req.OrderID,
				"reason":   req.Reason,
			}),
	)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"success": true,
		"status":  "CANCELLED",
	})
}

// GET /api/v1/account - Live broker account info.
func (s *HTTPServer) handleAccount(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	account, err := s.broker.GetAccountInfo(r.Context())
	if err != nil {
		s.log.Error().Err(err).Msg("get_account_failed")
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "broker unavailable"})
		return
	}

	writeJSON(w, http.StatusOK, account)
}

func (s *HTTPServer) handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}

// GET /internal/audit/replay
//
// Returns a chronologically-ordered JSON array of audit log events
// for the requested user within the given time window.
//
// Query parameters:
//
//	user_id  (required) - the user whose audit log to replay.
//	since    (required) - RFC3339 start timestamp (inclusive).
//	until    (optional) - RFC3339 end timestamp (inclusive).
//	                      Defaults to now. Maximum window: 7 days.
//
// Authentication: service-token (RequireAuth middleware). The caller
// must present a valid JWT in the Authorization header. The endpoint
// is NOT CSRF-protected because it is GET-only and is called by
// executionctl, not by the browser dashboard.
//
// Response:
//
//	200 OK  - JSON array of AuditLogRow objects.
//	400     - missing/invalid parameters.
//	401     - missing or invalid token.
//	500     - DB error.
//
// Audit ref: CHECKLIST Section 7 'Replay capability (audit + debugging)'.
func (s *HTTPServer) handleAuditReplay(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}

	q := r.URL.Query()
	userID := strings.TrimSpace(q.Get("user_id"))
	if userID == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "user_id is required"})
		return
	}

	sinceStr := strings.TrimSpace(q.Get("since"))
	if sinceStr == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "since is required (RFC3339)"})
		return
	}
	since, err := time.Parse(time.RFC3339, sinceStr)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "since must be RFC3339: " + err.Error()})
		return
	}

	until := time.Now().UTC()
	if untilStr := strings.TrimSpace(q.Get("until")); untilStr != "" {
		until, err = time.Parse(time.RFC3339, untilStr)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "until must be RFC3339: " + err.Error()})
			return
		}
	}

	// Enforce maximum window of 7 days to prevent unbounded queries.
	const maxWindow = 7 * 24 * time.Hour
	if until.Sub(since) > maxWindow {
		writeJSON(w, http.StatusBadRequest, map[string]string{
			"error": "time window exceeds maximum of 7 days",
		})
		return
	}
	if until.Before(since) {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "until must be after since"})
		return
	}

	rows, err := s.auditLog.QueryAuditLog(r.Context(), userID, since, until)
	if err != nil {
		s.log.Error().Err(err).Str("user_id", userID).Msg("audit_replay_query_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "audit query failed"})
		return
	}

	writeJSON(w, http.StatusOK, rows)
}

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}
