package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/alert"
	"github.com/flamegreat/etradie/src/alert/alertredis"
	"github.com/flamegreat/etradie/src/execution/internal/audit"
	"github.com/flamegreat/etradie/src/execution/internal/broker"
	"github.com/flamegreat/etradie/src/execution/internal/observability"
	"github.com/flamegreat/etradie/src/execution/internal/state"
	"github.com/flamegreat/etradie/src/execution/internal/store"
)

// HTTPServer serves the dashboard-facing REST API and WebSocket notifications.
type HTTPServer struct {
	server   *http.Server
	state    *state.Manager
	broker   broker.Port
	settings *store.SettingsStore
	auditLog *audit.Logger
	transport *alertredis.Transport
	log       zerolog.Logger
}

// NewHTTPServer creates the execution HTTP API server.
func NewHTTPServer(
	port int,
	sm *state.Manager,
	bp broker.Port,
	ss *store.SettingsStore,
	al *audit.Logger,
	transport *alertredis.Transport,
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

	// Dashboard REST API.
	mux.HandleFunc("/api/v1/settings", s.handleSettings)
	mux.HandleFunc("/api/v1/state", s.handleState)
	mux.HandleFunc("/api/v1/orders/cancel", s.handleCancelOrder)
	mux.HandleFunc("/api/v1/account", s.handleAccount)

	// WebSocket notifications (delegates to local hub via transport).
	mux.HandleFunc("/ws/notifications", alert.WebSocketHandler(transport.LocalHub()))

	// Ops endpoints.
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
// In production, the allowed origin should be restricted to the
// dashboard domain via a reverse proxy (nginx, Traefik, etc.).
// This middleware ensures development and direct-access scenarios work.
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
	defaults := store.Settings{
		ExecutionMode:       "LIMIT",
		MaxConcurrentTrades: 3,
		DailyLossLimitPct:   3.0,
		WeeklyDrawdownPct:   5.0,
	}

	settings, err := s.settings.LoadAll(r.Context(), defaults)
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

	if err := s.settings.SaveAll(r.Context(), &req); err != nil {
		s.log.Error().Err(err).Msg("put_settings_failed")
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	// Publish settings change to all connected dashboards via Redis.
	s.transport.Publish(r.Context(),
		alert.NewEvent(alert.SourceExecution, alert.TypeSettingsUpdated, alert.SeverityInfo,
			fmt.Sprintf("Settings updated: mode=%s, max_trades=%d", req.ExecutionMode, req.MaxConcurrentTrades)).
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

	if err := s.state.Refresh(r.Context()); err != nil {
		s.log.Error().Err(err).Msg("state_refresh_failed")
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "broker state refresh failed"})
		return
	}

	positions := s.state.Positions()
	pending := s.state.PendingOrders()
	account := s.state.Account()

	var balance, equity float64
	if account != nil {
		balance = account.Balance
		equity = account.Equity
	}

	resp := map[string]interface{}{
		"open_position_count": len(positions),
		"pending_order_count": len(pending),
		"daily_realized_pnl":  s.state.DailyPnL(),
		"weekly_realized_pnl": s.state.WeeklyPnL(),
		"account_balance":     balance,
		"account_equity":      equity,
		"open_positions":      positions,
		"pending_orders":      pending,
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
