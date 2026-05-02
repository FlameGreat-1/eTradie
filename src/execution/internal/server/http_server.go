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

// HTTPServer serves the dashboard-facing REST API and WebSocket notifications.
type HTTPServer struct {
	server         *http.Server
	state          *state.Manager
	broker         broker.Port
	settings       *store.SettingsStore
	auditLog       *audit.Logger
	transport      *alertredis.Transport
	log            zerolog.Logger
	symbolMetaCache sync.Map // symbol -> symbolMeta (cached forever; digits/point never change)
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

	// Dashboard REST API (all protected).
	mux.Handle("/api/v1/settings", authMw(http.HandlerFunc(s.handleSettings)))
	mux.Handle("/api/v1/state", authMw(http.HandlerFunc(s.handleState)))
	mux.Handle("/api/v1/orders/cancel", authMw(http.HandlerFunc(s.handleCancelOrder)))
	mux.Handle("/api/v1/account", authMw(http.HandlerFunc(s.handleAccount)))

	// WebSocket notifications (protected).
	mux.Handle("/ws/notifications", authMw(http.HandlerFunc(alert.WebSocketHandler(transport.LocalHub()))))

	// Ops endpoints (public).
	mux.HandleFunc("/health", s.handleHealth)
	mux.Handle("/metrics", promhttp.Handler())

	s.server = &http.Server{
		Addr:         fmt.Sprintf(":%d", port),
		Handler:      corsMiddleware(mux),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
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

// Shutdown gracefully stops the HTTP server.
func (s *HTTPServer) Shutdown(ctx context.Context) error {
	s.log.Info().Msg("http_api_server_shutting_down")
	return s.server.Shutdown(ctx)
}

// corsMiddleware adds CORS headers for dashboard cross-origin requests.
// Allowed origins are enforced at the API Gateway / Reverse Proxy layer (Nginx/Traefik).
// This middleware ensures internal routing and dashboard scenarios work smoothly.
func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		if origin != "" {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
			w.Header().Set("Access-Control-Max-Age", "86400")
		}

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}

		next.ServeHTTP(w, r)
	})
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

	// Publish settings change to the user's connected dashboards via Redis.
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

	// Convert positions slice to a map keyed by symbol. The dashboard
	// iterates open_positions with Object.entries() expecting
	// {symbol: positionData} pairs. A flat array would produce
	// ["0", data] entries whose keys never match the active symbol.
	posMap := make(map[string]interface{}, len(positions))
	for _, p := range positions {
		posMap[p.Symbol] = p
	}

	// Build symbol_meta from broker. Cached in-memory; digits/point
	// are immutable properties of a symbol and never change at runtime.
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

	// Ownership verification: ensure the order belongs to this user.
	// Refresh state to get the user's current pending orders from their
	// own broker account, then verify the order_id is in that list.
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

	// Write audit log (same as gRPC CancelPendingOrder).
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

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}
