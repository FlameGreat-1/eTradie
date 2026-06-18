package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
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

// userRateLimiter is a per-user sliding-window rate limiter keyed on the
// authenticated user_id, matching the pattern used by the gateway's
// tradingplan / tradingsystem / performancereview packages. Safe for
// concurrent use; a background goroutine reaps stale windows every 5
// minutes. Close() terminates that goroutine on shutdown.
type userRateLimiter struct {
	mu       sync.Mutex
	windows  map[string]*rlWindow
	limit    int
	interval time.Duration
	done     chan struct{}
}

type rlWindow struct {
	count   int
	resetAt time.Time
}

func newUserRateLimiter(limit int, interval time.Duration) *userRateLimiter {
	rl := &userRateLimiter{
		windows:  make(map[string]*rlWindow),
		limit:    limit,
		interval: interval,
		done:     make(chan struct{}),
	}
	go rl.cleanup()
	return rl
}

// Allow reports whether user_id is within budget. An empty user_id
// (cannot occur behind RequireAuth) is allowed so a missing identity
// never wedges a legitimate request behind a phantom budget.
func (rl *userRateLimiter) Allow(userID string) bool {
	if userID == "" {
		return true
	}
	rl.mu.Lock()
	defer rl.mu.Unlock()
	now := time.Now()
	w, exists := rl.windows[userID]
	if !exists || now.After(w.resetAt) {
		rl.windows[userID] = &rlWindow{count: 1, resetAt: now.Add(rl.interval)}
		return true
	}
	if w.count >= rl.limit {
		return false
	}
	w.count++
	return true
}

func (rl *userRateLimiter) Close() {
	select {
	case <-rl.done:
	default:
		close(rl.done)
	}
}

func (rl *userRateLimiter) cleanup() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()
	for {
		select {
		case <-rl.done:
			return
		case <-ticker.C:
			rl.mu.Lock()
			now := time.Now()
			for uid, w := range rl.windows {
				if now.After(w.resetAt) {
					delete(rl.windows, uid)
				}
			}
			rl.mu.Unlock()
		}
	}
}

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

	// settingsLimiter and cancelLimiter are per-user abuse caps on the
	// two mutating dashboard routes. Closed in Shutdown().
	settingsLimiter *userRateLimiter
	cancelLimiter   *userRateLimiter
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
		state:           sm,
		broker:          bp,
		settings:        ss,
		auditLog:        al,
		transport:       transport,
		log:             observability.Logger("http_server"),
		settingsLimiter: newUserRateLimiter(30, time.Minute),
		cancelLimiter:   newUserRateLimiter(30, time.Minute),
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

	// No CORS middleware by design. Under the Option B architecture the
	// SPA talks ONLY to the gateway origin; execution is reached
	// exclusively via the gateway reverse proxy (server-to-server),
	// never directly by a browser, so no browser reads a CORS header
	// from this service. CORS is emitted once at the gateway edge and
	// the gateway proxy strips any upstream Access-Control-* so the
	// gateway is the single CORS authority. Re-adding CORS here would
	// reintroduce the duplicated `Access-Control-Allow-Credentials:
	// true,true` the browser rejects. Do NOT add it back.
	s.server = &http.Server{
		Addr:              fmt.Sprintf(":%d", port),
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	return s
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

// Shutdown gracefully stops the HTTP server and reaps the rate-limiter
// background goroutines.
func (s *HTTPServer) Shutdown(ctx context.Context) error {
	s.log.Info().Msg("http_api_server_shutting_down")
	s.settingsLimiter.Close()
	s.cancelLimiter.Close()
	return s.server.Shutdown(ctx)
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
	userID := auth.UserIDFromContext(r.Context())
	if !s.settingsLimiter.Allow(userID) {
		observability.RateLimitedTotal.WithLabelValues("settings").Inc()
		w.Header().Set("Retry-After", "60")
		writeJSON(w, http.StatusTooManyRequests, map[string]string{"error": "too many requests; please slow down"})
		return
	}

	var req store.Settings
	if err := auth.DecodeJSONStrict(w, r, &req, 0); err != nil {
		status, msg := auth.DecodeJSONError(err)
		writeJSON(w, status, map[string]string{"error": msg})
		return
	}

	req.ExecutionMode = strings.ToUpper(req.ExecutionMode)
	if err := s.settings.SaveAll(r.Context(), userID, &req); err != nil {
		s.log.Error().Err(err).Msg("put_settings_failed")
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "failed to save settings"})
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

	cancelUserID := auth.UserIDFromContext(r.Context())
	if !s.cancelLimiter.Allow(cancelUserID) {
		observability.RateLimitedTotal.WithLabelValues("orders_cancel").Inc()
		w.Header().Set("Retry-After", "60")
		writeJSON(w, http.StatusTooManyRequests, map[string]string{"error": "too many requests; please slow down"})
		return
	}

	var req struct {
		OrderID string `json:"order_id"`
		Symbol  string `json:"symbol"`
		Reason  string `json:"reason"`
	}
	if err := auth.DecodeJSONStrict(w, r, &req, 0); err != nil {
		status, msg := auth.DecodeJSONError(err)
		writeJSON(w, status, map[string]string{"error": msg})
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
			"error":   "could not cancel the order; it may already be filled or cancelled",
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

	// Object-level authorization (TIER 4 ownership verification / TIER 2
	// tenant isolation). RequireAuth has populated the claims; a
	// non-admin caller may replay ONLY their own audit trail. An admin
	// (operator running executionctl) may replay any user's. Without
	// this gate any valid token could read another tenant's execution
	// audit log via a forged user_id query parameter.
	claims := auth.ClaimsFromContext(r.Context())
	if claims == nil || claims.UserID == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	if claims.UserID != userID && claims.Role != auth.RoleAdmin {
		s.log.Warn().
			Str("caller_user_id", claims.UserID).
			Str("requested_user_id", userID).
			Msg("audit_replay_cross_tenant_denied")
		writeJSON(w, http.StatusForbidden, map[string]string{"error": "cannot replay another user's audit log"})
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
