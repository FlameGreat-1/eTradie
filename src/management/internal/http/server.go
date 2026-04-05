package http

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/management/internal/analytics"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/monitoring"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
)

// Server serves the dashboard-facing REST API for Trade Management.
type Server struct {
	server  *http.Server
	monitor *monitoring.Manager
	journal *journal.Repository
	metrics *analytics.Metrics
	log     zerolog.Logger
}

// NewServer creates the management HTTP API server.
// All /api/v1/* routes require a valid JWT Bearer token.
func NewServer(
	port int,
	monitor *monitoring.Manager,
	journal *journal.Repository,
	metrics *analytics.Metrics,
	tokenService *auth.TokenService,
) *Server {
	s := &Server{
		monitor: monitor,
		journal: journal,
		metrics: metrics,
		log:     observability.Logger("http_server"),
	}

	mux := http.NewServeMux()
	authMw := auth.RequireAuth(tokenService)

	// Dashboard REST API (all protected by auth middleware).
	mux.Handle("/api/v1/management/trades", authMw(http.HandlerFunc(s.handleGetTrades)))
	mux.Handle("/api/v1/management/journal", authMw(http.HandlerFunc(s.handleGetJournal)))
	mux.Handle("/api/v1/management/metrics", authMw(http.HandlerFunc(s.handleGetMetrics)))

	// Ops endpoints (public, no auth required).
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
func (s *Server) Start() error {
	s.log.Info().Str("addr", s.server.Addr).Msg("http_api_server_starting")
	err := s.server.ListenAndServe()
	if err == http.ErrServerClosed {
		return nil
	}
	return err
}

// Shutdown gracefully stops the HTTP server.
func (s *Server) Shutdown(ctx context.Context) error {
	s.log.Info().Msg("http_api_server_shutting_down")
	return s.server.Shutdown(ctx)
}

// corsMiddleware adds CORS headers for dashboard cross-origin requests.
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

// GET /api/v1/management/trades - Return active managed trades for the authenticated user.
func (s *Server) handleGetTrades(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}

	trades := s.monitor.GetAllTrades()
	result := make([]map[string]interface{}, 0, len(trades))

	for _, t := range trades {
		t.RLock()
		// Only return trades owned by the authenticated user.
		if t.UserID != userID {
			t.RUnlock()
			continue
		}
		result = append(result, map[string]interface{}{
			"trade_id":           t.TradeID,
			"symbol":             t.Symbol,
			"direction":          string(t.Direction),
			"entry_price":        t.EntryPrice,
			"current_price":      t.CurrentPrice,
			"stop_loss":          t.StopLoss,
			"tp1_price":          t.TP1Price,
			"tp2_price":          t.TP2Price,
			"tp3_price":          t.TP3Price,
			"total_lot_size":     t.TotalLotSize,
			"remaining_lot_size": t.RemainingLotSize,
			"unrealized_pnl":     t.UnrealizedPnL,
			"realized_pnl":       t.RealizedPnL,
			"trading_style":      string(t.TradingStyle),
			"status":             string(t.Status),
			"breakeven_set":      t.BreakevenSet,
			"tp1_hit":            t.TP1Hit,
			"tp2_hit":            t.TP2Hit,
			"broker_order_id":    t.BrokerOrderID,
			"analysis_id":        t.AnalysisID,
			"opened_at":          t.OpenedAt.Format(time.RFC3339),
		})
		t.RUnlock()
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{"trades": result})
}

// GET /api/v1/management/journal - Return closed trade history for the authenticated user.
func (s *Server) handleGetJournal(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}

	q := r.URL.Query()
	limitQuery := q.Get("limit")
	offsetQuery := q.Get("offset")
	symbolFilter := q.Get("symbol")
	styleFilter := q.Get("style")

	limit := 50
	offset := 0
	var err error

	if limitQuery != "" {
		limit, err = strconv.Atoi(limitQuery)
		if err != nil || limit <= 0 {
			limit = 50
		}
	}
	if offsetQuery != "" {
		offset, err = strconv.Atoi(offsetQuery)
		if err != nil || offset < 0 {
			offset = 0
		}
	}

	trades, total, err := s.journal.GetClosedTrades(r.Context(), userID, limit, offset, symbolFilter, styleFilter)
	if err != nil {
		s.log.Error().Err(err).Msg("failed_to_get_journal")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "failed to retrieve journal"})
		return
	}

	entries := make([]map[string]interface{}, 0, len(trades))
	for _, t := range trades {
		mapped := map[string]interface{}{
			"trade_id":            t.TradeID,
			"symbol":              t.Symbol,
			"direction":           t.Direction,
			"entry_price":         t.EntryPrice,
			"exit_price":          t.ExitPrice,
			"stop_loss":           t.StopLoss,
			"lot_size":            t.TotalLotSize,
			"gross_pnl":           t.GrossPnL,
			"r_multiple":          t.RMultiple,
			"confluence_score":    t.ConfluenceScore,
			"grade":               t.Grade,
			"setup_type":          t.SetupType,
			"trading_style":       t.TradingStyle,
			"outcome":             t.Outcome,
			"duration_minutes":    t.DurationMinutes,
			"sl_adjustment_count": t.SLAdjustments,
			"partial_close_count": t.PartialCloses,
			"analysis_id":         t.AnalysisID,
			"opened_at":           t.OpenedAt.Format(time.RFC3339),
		}
		if t.ClosedAt != nil {
			mapped["closed_at"] = t.ClosedAt.Format(time.RFC3339)
		}
		entries = append(entries, mapped)
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"entries":     entries,
		"total_count": total,
	})
}

// GET /api/v1/management/metrics - Return real-time analytics for the authenticated user.
func (s *Server) handleGetMetrics(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}

	period := r.URL.Query().Get("period")
	if period == "" {
		period = "ALL_TIME"
	}

	summary, err := s.metrics.Calculate(r.Context(), userID, period)
	if err != nil {
		s.log.Error().Err(err).Msg("failed_to_calculate_metrics")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "failed to calculate metrics"})
		return
	}

	writeJSON(w, http.StatusOK, summary)
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}
