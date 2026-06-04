package http

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"strings"
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
//
// Middleware chain for every protected route:
//
//	authMw -> csrfMw -> handler
//
// All current /api/v1/management/* endpoints are GET, so RequireCSRF
// short-circuits without doing any work. The wrap is uniform so the
// next mutating route added to this server is automatically protected.
//
// Internal routes (/internal/*) are guarded by a separate constant-
// time HMAC against the same engine shared secret the gateway uses.
// No cookie auth on the internal surface — the engine cannot hold a
// user JWT in background workers.
type Server struct {
	server         *http.Server
	monitor        *monitoring.Manager
	journal        *journal.Repository
	metrics        *analytics.Metrics
	aggregator     *analytics.PerformanceAggregator
	internalSecret string
	log            zerolog.Logger
}

// NewServer creates the management HTTP API server.
// All /api/v1/* routes require a valid JWT and pass the CSRF gate.
//
// aggregator and engineInternalSecret are optional: when either is
// empty the /internal/performance-review/aggregate route is mounted
// but refuses every request with 401 (safe default for dev).
func NewServer(
	port int,
	monitor *monitoring.Manager,
	journal *journal.Repository,
	metrics *analytics.Metrics,
	aggregator *analytics.PerformanceAggregator,
	engineInternalSecret string,
	tokenService *auth.TokenService,
	authCfg *auth.Config,
) *Server {
	s := &Server{
		monitor:        monitor,
		journal:        journal,
		metrics:        metrics,
		aggregator:     aggregator,
		internalSecret: strings.TrimSpace(engineInternalSecret),
		log:            observability.Logger("http_server"),
	}

	mux := http.NewServeMux()
	authMw := auth.RequireAuth(tokenService)
	csrfMw := auth.RequireCSRF(authCfg)

	wrap := func(h http.HandlerFunc) http.Handler {
		return authMw(csrfMw(http.HandlerFunc(h)))
	}

	mux.Handle("/api/v1/management/trades", wrap(s.handleGetTrades))
	mux.Handle("/api/v1/management/journal", wrap(s.handleGetJournal))
	mux.Handle("/api/v1/management/metrics", wrap(s.handleGetMetrics))
	mux.Handle("/api/v1/management/pnl-calendar", wrap(s.handleGetPnLCalendar))

	// Internal (shared-secret) surface for the engine's performance
	// review generator. No cookie auth here — the engine cannot hold
	// a user JWT in background workers; verifyInternal does the HMAC
	// gate per-request.
	mux.HandleFunc("/internal/performance-review/aggregate", s.handlePerfReviewAggregate)

	// Ops endpoints (public, no auth required).
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
//  1. MANAGEMENT_ALLOWED_ORIGINS (service-specific override)
//  2. ALLOWED_ORIGINS            (shared with engine + execution)
func loadAllowedOrigins() map[string]bool {
	raw := strings.TrimSpace(os.Getenv("MANAGEMENT_ALLOWED_ORIGINS"))
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

// corsMiddleware emits credentialed-CORS headers backed by an explicit
// allow-list. The Allow-Headers list is built from the configured CSRF
// header name so AUTH_CSRF_HEADER changes don't silently break the
// preflight.
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
			"swap":               t.Swap,
			"commission":         t.Commission,
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

// verifyInternal performs a constant-time comparison of the
// X-Internal-Auth header against the configured engine shared
// secret. Same SHA-256 pre-hash dance the gateway uses so the
// secret length is never leaked via timing.
func (s *Server) verifyInternal(r *http.Request) bool {
	if s.internalSecret == "" {
		return false
	}
	provided := strings.TrimSpace(r.Header.Get("X-Internal-Auth"))
	if provided == "" {
		return false
	}
	want := sha256.Sum256([]byte(s.internalSecret))
	got := sha256.Sum256([]byte(provided))
	return hmac.Equal(want[:], got[:])
}

// perfReviewAggregateBody is the engine's POST body.
//
// The user_id is taken from the body (the engine's per-user dispatch
// already knows whose review this is); we do NOT trust
// X-User-Id alone because the body is the contract and is signed by
// the shared secret on every call.
type perfReviewAggregateBody struct {
	UserID      string `json:"user_id"`
	Period      string `json:"period"`
	PeriodStart string `json:"period_start"`
	PeriodEnd   string `json:"period_end"`
	JournalMode string `json:"journal_mode"`
}

// POST /internal/performance-review/aggregate
//
// Returns the deterministic per-window bundle the engine generator
// feeds to the LLM. Idempotent; safe to retry.
func (s *Server) handlePerfReviewAggregate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method not allowed"})
		return
	}
	if !s.verifyInternal(r) {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}
	if s.aggregator == nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"error": "aggregator not configured"})
		return
	}

	r.Body = http.MaxBytesReader(w, r.Body, 4*1024)
	var body perfReviewAggregateBody
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&body); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid JSON: " + err.Error()})
		return
	}

	userID := strings.TrimSpace(body.UserID)
	if userID == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "user_id is required"})
		return
	}
	period := strings.ToLower(strings.TrimSpace(body.Period))
	if period != "weekly" && period != "monthly" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "period must be 'weekly' or 'monthly'"})
		return
	}
	periodStart, err := time.Parse(time.RFC3339, body.PeriodStart)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "period_start must be RFC3339"})
		return
	}
	periodEnd, err := time.Parse(time.RFC3339, body.PeriodEnd)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "period_end must be RFC3339"})
		return
	}

	journalMode := strings.ToLower(strings.TrimSpace(body.JournalMode))
	if journalMode == "" {
		journalMode = "system"
	}
	if journalMode != "system" && journalMode != "manual" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "journal_mode must be 'system' or 'manual'"})
		return
	}

	bundle, err := s.aggregator.Aggregate(r.Context(), userID, period, periodStart, periodEnd, journalMode)
	if err != nil {
		s.log.Error().Err(err).Str("user_id", userID).Str("period", period).Str("journal_mode", journalMode).Msg("perf_review_aggregate_failed")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "failed to aggregate performance data"})
		return
	}
	writeJSON(w, http.StatusOK, bundle)
}

// GET /api/v1/management/pnl-calendar - Daily PnL aggregation and streaks.
func (s *Server) handleGetPnLCalendar(w http.ResponseWriter, r *http.Request) {
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

	year, err := strconv.Atoi(q.Get("year"))
	if err != nil || year < 2000 || year > 2100 {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid year parameter"})
		return
	}

	month, err := strconv.Atoi(q.Get("month"))
	if err != nil || month < 1 || month > 12 {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid month parameter"})
		return
	}

	tz := q.Get("tz")
	if tz == "" {
		tz = "UTC"
	}

	dailyPnL, err := s.journal.GetDailyPnL(r.Context(), userID, year, month, tz)
	if err != nil {
		s.log.Error().Err(err).Msg("failed_to_get_daily_pnl")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "failed to retrieve PnL data"})
		return
	}

	streaks, err := s.journal.GetStreaks(r.Context(), userID, tz)
	if err != nil {
		s.log.Error().Err(err).Msg("failed_to_get_streaks")
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "failed to calculate streaks"})
		return
	}

	pnlMap := make(map[string]float64, len(dailyPnL))
	for _, d := range dailyPnL {
		pnlMap[d.Date] = d.PnL
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"daily_pnl":      pnlMap,
		"current_streak": streaks.CurrentStreak,
		"max_streak":     streaks.MaxStreak,
	})
}

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}
