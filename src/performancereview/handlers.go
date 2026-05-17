package performancereview

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"net/http"
	"runtime/debug"
	"strconv"
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
// the asynchronous engine LLM call. Defined here (not in the adapter
// package) so the package stays unit-testable with fakes and so the
// dependency graph is one-directional.
//
// Dispatch MUST return quickly: it kicks off the generation and
// returns. The engine eventually posts the finished review back to
// /internal/performance-review/callback. A non-nil error from
// Dispatch is treated as a hard failure and the row is flipped to
// status='failed'.
type EngineDispatcher interface {
	Dispatch(ctx context.Context, req GenerationRequest) error
}

// SystemReader is the minimal projection of the tradingsystem store
// the handler needs. The trading-system version is included in the
// dispatched review so the engine can render PLAN.md section 13
// (Performance vs Trading System Alignment).
type SystemReader interface {
	Get(ctx context.Context, userID string) (*tradingsystem.Record, error)
}

// Handler serves the performance-review REST API.
type Handler struct {
	store          *Store
	sysReader      SystemReader
	dispatcher     EngineDispatcher
	internalSecret string
	log            zerolog.Logger

	generateLimiter *userRateLimiter
	listLimiter     *userRateLimiter
	fetchLimiter    *userRateLimiter
}

// NewHandler builds a Handler. internalSecret is the same value the
// engine sends in X-Internal-Auth; pass an empty string only in
// tests. A deployed gateway with an empty secret refuses every
// internal call (safe by default).
//
// sysReader and dispatcher may be nil to disable the generation
// surface (the read endpoints still work). This lets the gateway
// boot cleanly in environments where the engine is not reachable and
// yields 503 on /generate instead of crashing.
func NewHandler(
	store *Store,
	sysReader SystemReader,
	dispatcher EngineDispatcher,
	internalSecret string,
	log zerolog.Logger,
) *Handler {
	return &Handler{
		store:           store,
		sysReader:       sysReader,
		dispatcher:      dispatcher,
		internalSecret:  strings.TrimSpace(internalSecret),
		log:             log,
		generateLimiter: newUserRateLimiter(5, time.Hour),
		listLimiter:     newUserRateLimiter(120, time.Minute),
		fetchLimiter:    newUserRateLimiter(240, time.Minute),
	}
}

// Close releases background goroutines owned by the rate limiters.
func (h *Handler) Close() {
	h.generateLimiter.Close()
	h.listLimiter.Close()
	h.fetchLimiter.Close()
}

// RegisterRoutes mounts the public REST surface. We use ServeMux's
// longest-prefix match so /api/v1/performance-review/history and
// /api/v1/performance-review/:id share the same parent path without
// stepping on each other.
func (h *Handler) RegisterRoutes(
	mux *http.ServeMux,
	authMiddleware func(http.Handler) http.Handler,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	wrap := func(handler http.HandlerFunc) http.Handler {
		return authMiddleware(csrfMiddleware(h.withPanicRecovery(handler)))
	}

	mux.Handle("/api/v1/performance-review/latest", wrap(h.handleLatest))
	mux.Handle("/api/v1/performance-review/history", wrap(h.handleHistory))
	mux.Handle("/api/v1/performance-review/generate", wrap(h.handleGenerate))
	// Catch-all for /api/v1/performance-review/{id}. The mux routes
	// the more-specific paths above first.
	mux.Handle("/api/v1/performance-review/", wrap(h.handleByID))
}

// RegisterInternalRoutes mounts the engine-callable surface.
func (h *Handler) RegisterInternalRoutes(mux *http.ServeMux) {
	mux.Handle("/internal/performance-review/callback", h.withPanicRecovery(h.handleInternalCallback))
	mux.Handle("/internal/performance-review/fail", h.withPanicRecovery(h.handleInternalFail))
	mux.Handle("/internal/performance-review/prior", h.withPanicRecovery(h.handleInternalPrior))
	mux.Handle("/internal/performance-review/active-users", h.withPanicRecovery(h.handleInternalActiveUsers))
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
					Msg("performance_review_panic_recovered")
				writeError(w, http.StatusInternalServerError, "internal server error")
			}
		}()
		next(w, r)
	})
}

// ---------------------------------------------------------------------------
// GET /api/v1/performance-review/latest?period=weekly|monthly
// ---------------------------------------------------------------------------

func (h *Handler) handleLatest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	if !h.fetchLimiter.Allow(userID) {
		PerfReviewRateLimitedTotal.WithLabelValues(endpointFetch).Inc()
		w.Header().Set("Retry-After", "60")
		writeError(w, http.StatusTooManyRequests, "too many requests; try again shortly")
		return
	}

	period := Period(strings.ToLower(strings.TrimSpace(r.URL.Query().Get("period"))))
	if period == "" {
		period = PeriodWeekly
	}
	if !period.IsValid() {
		writeError(w, http.StatusBadRequest, "period must be 'weekly' or 'monthly'")
		return
	}

	rec, err := h.store.GetLatest(r.Context(), userID, period)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			PerfReviewFetchTotal.WithLabelValues(outcomeEmpty).Inc()
			writeJSON(w, http.StatusOK, map[string]interface{}{
				"period":     string(period),
				"status":     "none",
				"has_review": false,
			})
			return
		}
		PerfReviewFetchTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("performance_review_latest_failed")
		writeError(w, http.StatusInternalServerError, "failed to load review")
		return
	}

	if rec.Review != nil {
		PerfReviewFetchTotal.WithLabelValues(outcomeHit).Inc()
	} else {
		PerfReviewFetchTotal.WithLabelValues(outcomeEmpty).Inc()
	}
	writeJSON(w, http.StatusOK, recordResponse(rec))
}

// ---------------------------------------------------------------------------
// GET /api/v1/performance-review/history?period=&offset=&limit=
// ---------------------------------------------------------------------------

func (h *Handler) handleHistory(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	if !h.listLimiter.Allow(userID) {
		PerfReviewRateLimitedTotal.WithLabelValues(endpointList).Inc()
		w.Header().Set("Retry-After", "60")
		writeError(w, http.StatusTooManyRequests, "too many requests; try again shortly")
		return
	}

	q := r.URL.Query()
	periodStr := strings.ToLower(strings.TrimSpace(q.Get("period")))
	var period Period
	if periodStr != "" {
		period = Period(periodStr)
		if !period.IsValid() {
			writeError(w, http.StatusBadRequest, "period must be 'weekly' or 'monthly'")
			return
		}
	}
	offset, _ := strconv.Atoi(q.Get("offset"))
	limit, _ := strconv.Atoi(q.Get("limit"))

	recs, total, err := h.store.ListHistory(r.Context(), userID, period, offset, limit)
	if err != nil {
		PerfReviewFetchTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("performance_review_history_failed")
		writeError(w, http.StatusInternalServerError, "failed to load history")
		return
	}

	items := make([]map[string]interface{}, 0, len(recs))
	for _, rec := range recs {
		items = append(items, historyRowResponse(rec))
	}
	PerfReviewFetchTotal.WithLabelValues(outcomeHit).Inc()
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"items":  items,
		"total":  total,
		"offset": offset,
		"limit":  effectiveLimit(limit),
	})
}

func effectiveLimit(limit int) int {
	if limit <= 0 {
		return HistoryDefaultLimit
	}
	if limit > HistoryMaxLimit {
		return HistoryMaxLimit
	}
	return limit
}

// ---------------------------------------------------------------------------
// GET /api/v1/performance-review/:id
// ---------------------------------------------------------------------------

func (h *Handler) handleByID(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	userID := auth.UserIDFromContext(r.Context())
	if userID == "" {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	if !h.fetchLimiter.Allow(userID) {
		PerfReviewRateLimitedTotal.WithLabelValues(endpointFetch).Inc()
		w.Header().Set("Retry-After", "60")
		writeError(w, http.StatusTooManyRequests, "too many requests; try again shortly")
		return
	}

	// Extract :id from the URL path. The catch-all route is
	// /api/v1/performance-review/, so anything after the trailing
	// slash that is non-empty and parses as int64 is the id.
	prefix := "/api/v1/performance-review/"
	if !strings.HasPrefix(r.URL.Path, prefix) {
		writeError(w, http.StatusNotFound, "not found")
		return
	}
	tail := strings.TrimPrefix(r.URL.Path, prefix)
	tail = strings.Trim(tail, "/")
	if tail == "" || strings.Contains(tail, "/") {
		writeError(w, http.StatusNotFound, "not found")
		return
	}
	id, err := strconv.ParseInt(tail, 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "invalid review id")
		return
	}

	rec, err := h.store.GetByID(r.Context(), userID, id)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			PerfReviewFetchTotal.WithLabelValues(outcomeEmpty).Inc()
			writeError(w, http.StatusNotFound, "review not found")
			return
		}
		PerfReviewFetchTotal.WithLabelValues(outcomeError).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Int64("id", id).
			Msg("performance_review_get_by_id_failed")
		writeError(w, http.StatusInternalServerError, "failed to load review")
		return
	}
	PerfReviewFetchTotal.WithLabelValues(outcomeHit).Inc()
	writeJSON(w, http.StatusOK, recordResponse(rec))
}

// ---------------------------------------------------------------------------
// POST /api/v1/performance-review/generate {period}
// ---------------------------------------------------------------------------

type generateRequest struct {
	Period string `json:"period"`
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
			"performance review generation is temporarily disabled")
		return
	}

	start := time.Now()

	var body generateRequest
	if r.ContentLength > 0 {
		r.Body = http.MaxBytesReader(w, r.Body, 4*1024)
		dec := json.NewDecoder(r.Body)
		dec.DisallowUnknownFields()
		_ = dec.Decode(&body)
	}
	period := Period(strings.ToLower(strings.TrimSpace(body.Period)))
	if period == "" {
		period = PeriodWeekly
	}
	if !period.IsValid() {
		writeError(w, http.StatusBadRequest, "period must be 'weekly' or 'monthly'")
		return
	}

	defer func() {
		PerfReviewGenerateDuration.Observe(time.Since(start).Seconds())
	}()

	if !h.generateLimiter.Allow(userID) {
		PerfReviewGenerateTotal.WithLabelValues(outcomeThrottled, string(period)).Inc()
		PerfReviewRateLimitedTotal.WithLabelValues(endpointGenerate).Inc()
		w.Header().Set("Retry-After", "3600")
		writeError(w, http.StatusTooManyRequests,
			"too many review generations; try again later")
		return
	}

	sysRec, err := h.sysReader.Get(r.Context(), userID)
	if err != nil {
		if errors.Is(err, tradingsystem.ErrNotFound) || sysRec == nil {
			PerfReviewGenerateTotal.WithLabelValues(outcomeValidationError, string(period)).Inc()
			writeError(w, http.StatusPreconditionFailed,
				"build your trading system before requesting a review")
			return
		}
		PerfReviewGenerateTotal.WithLabelValues(outcomeError, string(period)).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("performance_review_sys_read_failed")
		writeError(w, http.StatusInternalServerError, "failed to load trading system")
		return
	}
	if sysRec.Status != tradingsystem.StatusActive || sysRec.Profile == nil {
		PerfReviewGenerateTotal.WithLabelValues(outcomeValidationError, string(period)).Inc()
		writeError(w, http.StatusPreconditionFailed,
			"trading system must be active before requesting a review")
		return
	}

	periodStart, periodEnd := computeWindow(period, time.Now().UTC())

	if _, err := h.store.MarkGenerating(r.Context(), userID, period, periodStart, periodEnd); err != nil {
		PerfReviewGenerateTotal.WithLabelValues(outcomeError, string(period)).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("performance_review_mark_generating_failed")
		writeError(w, http.StatusInternalServerError, "failed to record generation state")
		return
	}

	req := GenerationRequest{
		UserID:         userID,
		Period:         period,
		PeriodStart:    periodStart,
		PeriodEnd:      periodEnd,
		ProfileVersion: sysRec.Version,
	}

	// Dispatch with a generous timeout independent of the user's
	// request context so a slow client cannot cancel an LLM call
	// mid-flight (mirrors the trading-plan dispatch pattern).
	dispatchCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	go func() {
		defer cancel()
		if err := h.dispatcher.Dispatch(dispatchCtx, req); err != nil {
			h.log.Error().Err(err).Str("user_id", userID).Msg("performance_review_dispatch_failed")
			failCtx, failCancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer failCancel()
			msg := "failed to start review generation"
			if markErr := h.store.MarkFailed(failCtx, userID, period, periodStart, msg); markErr != nil {
				h.log.Error().Err(markErr).Str("user_id", userID).Msg("performance_review_mark_failed_after_dispatch")
			}
		}
	}()

	PerfReviewGenerateTotal.WithLabelValues(outcomeQueued, string(period)).Inc()
	h.log.Info().
		Str("user_id", userID).
		Str("period", string(period)).
		Time("period_start", periodStart).
		Time("period_end", periodEnd).
		Int("profile_version", sysRec.Version).
		Msg("performance_review_generation_dispatched")

	writeJSON(w, http.StatusAccepted, map[string]interface{}{
		"status":       string(StatusGenerating),
		"period":       string(period),
		"period_start": periodStart,
		"period_end":   periodEnd,
		"message":      "review generation in progress",
	})
}

// computeWindow returns the inclusive [start, end] window for the
// given period anchored at `now` (UTC).
//
//   weekly:  trailing 7 days ending at the start of today UTC.
//            start = midnight 7 days ago; end = midnight today minus 1ns.
//   monthly: last full calendar month.
//            start = 1st of last month 00:00 UTC; end = last day of
//            last month 23:59:59.999999999 UTC.
func computeWindow(period Period, now time.Time) (time.Time, time.Time) {
	now = now.UTC()
	switch period {
	case PeriodMonthly:
		thisMonth := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, time.UTC)
		lastMonthStart := thisMonth.AddDate(0, -1, 0)
		lastMonthEnd := thisMonth.Add(-time.Nanosecond)
		return lastMonthStart, lastMonthEnd
	default: // weekly
		today := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, time.UTC)
		start := today.AddDate(0, 0, -7)
		end := today.Add(-time.Nanosecond)
		return start, end
	}
}

// ---------------------------------------------------------------------------
// Internal: POST /internal/performance-review/callback
// ---------------------------------------------------------------------------

type internalCallbackBody struct {
	UserID string  `json:"user_id"`
	Review *Review `json:"review"`
}

func (h *Handler) handleInternalCallback(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.verifyInternalSecret(r) {
		PerfReviewCallbackTotal.WithLabelValues(outcomeUnauthorized, "unknown").Inc()
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	// 512 KB ceiling: a fully-populated 14-section review is ~30 KB.
	r.Body = http.MaxBytesReader(w, r.Body, 512*1024)

	var body internalCallbackBody
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&body); err != nil {
		PerfReviewCallbackTotal.WithLabelValues(outcomeValidationError, "unknown").Inc()
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	userID := strings.TrimSpace(body.UserID)
	if userID == "" {
		userID = strings.TrimSpace(r.Header.Get(internalUserIDHeader))
	}
	if userID == "" {
		PerfReviewCallbackTotal.WithLabelValues(outcomeValidationError, "unknown").Inc()
		writeError(w, http.StatusBadRequest, "user_id is required")
		return
	}
	if body.Review == nil {
		PerfReviewCallbackTotal.WithLabelValues(outcomeValidationError, "unknown").Inc()
		writeError(w, http.StatusBadRequest, "review is required")
		return
	}

	periodLabel := string(body.Review.Period)
	if periodLabel == "" {
		periodLabel = "unknown"
	}

	if err := Validate(body.Review); err != nil {
		var verr *ValidationError
		if errors.As(err, &verr) {
			PerfReviewCallbackTotal.WithLabelValues(outcomeValidationError, periodLabel).Inc()
			h.log.Warn().
				Str("user_id", userID).
				Str("period", periodLabel).
				Interface("fields", verr.Fields).
				Msg("performance_review_callback_validation_failed")
			writeJSON(w, http.StatusUnprocessableEntity, map[string]interface{}{
				"error":  verr.Message,
				"fields": verr.Fields,
			})
			return
		}
		PerfReviewCallbackTotal.WithLabelValues(outcomeValidationError, periodLabel).Inc()
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	rec, err := h.store.Save(r.Context(), userID, body.Review)
	if err != nil {
		PerfReviewCallbackTotal.WithLabelValues(outcomeError, periodLabel).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("performance_review_callback_save_failed")
		writeError(w, http.StatusInternalServerError, "failed to persist review")
		return
	}

	if !body.Review.GenerationStartedAt.IsZero() {
		PerfReviewLLMCallDuration.WithLabelValues(periodLabel).
			Observe(time.Since(body.Review.GenerationStartedAt).Seconds())
	}
	PerfReviewConfidenceBandTotal.WithLabelValues(string(body.Review.ConfidenceReport.Band), periodLabel).Inc()
	PerfReviewCallbackTotal.WithLabelValues(outcomeSuccess, periodLabel).Inc()

	h.log.Info().
		Str("user_id", userID).
		Str("period", periodLabel).
		Int64("id", rec.ID).
		Str("confidence_band", string(body.Review.ConfidenceReport.Band)).
		Int("sample_size", body.Review.ConfidenceReport.SampleSize).
		Msg("performance_review_callback_persisted")

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"persisted": true,
		"id":        rec.ID,
	})
}

// ---------------------------------------------------------------------------
// Internal: POST /internal/performance-review/fail
// ---------------------------------------------------------------------------

type internalFailBody struct {
	UserID      string `json:"user_id"`
	Period      string `json:"period"`
	PeriodStart string `json:"period_start"`
	Message     string `json:"message"`
}

func (h *Handler) handleInternalFail(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.verifyInternalSecret(r) {
		PerfReviewCallbackTotal.WithLabelValues(outcomeUnauthorized, "unknown").Inc()
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
	period := Period(strings.ToLower(strings.TrimSpace(body.Period)))
	if !period.IsValid() {
		writeError(w, http.StatusBadRequest, "period must be 'weekly' or 'monthly'")
		return
	}
	periodStart, err := time.Parse(time.RFC3339, body.PeriodStart)
	if err != nil {
		writeError(w, http.StatusBadRequest, "period_start must be RFC3339")
		return
	}
	message := strings.TrimSpace(body.Message)
	if message == "" {
		message = "review generation failed; please try again"
	}
	if err := h.store.MarkFailed(r.Context(), userID, period, periodStart, message); err != nil {
		if errors.Is(err, ErrNotFound) {
			// Idempotent: a fail-callback that arrives before the
			// generating row was written is harmless; ack and move on.
			writeJSON(w, http.StatusOK, map[string]interface{}{"recorded": true, "no_row": true})
			return
		}
		PerfReviewCallbackTotal.WithLabelValues(outcomeError, string(period)).Inc()
		h.log.Error().Err(err).Str("user_id", userID).Msg("performance_review_mark_failed_callback")
		writeError(w, http.StatusInternalServerError, "failed to record failure state")
		return
	}
	h.log.Warn().
		Str("user_id", userID).
		Str("period", string(period)).
		Str("message", message).
		Msg("performance_review_marked_failed")
	writeJSON(w, http.StatusOK, map[string]interface{}{"recorded": true})
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Internal: GET /internal/performance-review/prior?user_id=&period=&before=
//
// Returns the most recent ready review row for (user_id, period)
// strictly before the supplied RFC3339 `before` timestamp. Used by
// the engine generator to compute trader-evolution deltas (PLAN.md
// section 12) without re-running the LLM over the prior window.
//
// Returns 404 when no prior ready row exists; the engine treats this
// as 'no comparison available' and forces trader_evolution.items to
// be empty in the prompt.
// ---------------------------------------------------------------------------

func (h *Handler) handleInternalPrior(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.verifyInternalSecret(r) {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	q := r.URL.Query()
	userID := strings.TrimSpace(q.Get("user_id"))
	if userID == "" {
		userID = strings.TrimSpace(r.Header.Get(internalUserIDHeader))
	}
	if userID == "" {
		writeError(w, http.StatusBadRequest, "user_id is required")
		return
	}
	period := Period(strings.ToLower(strings.TrimSpace(q.Get("period"))))
	if !period.IsValid() {
		writeError(w, http.StatusBadRequest, "period must be 'weekly' or 'monthly'")
		return
	}
	beforeStr := strings.TrimSpace(q.Get("before"))
	if beforeStr == "" {
		writeError(w, http.StatusBadRequest, "before is required")
		return
	}
	before, err := time.Parse(time.RFC3339, beforeStr)
	if err != nil {
		writeError(w, http.StatusBadRequest, "before must be RFC3339")
		return
	}
	rec, err := h.store.GetLatestReadyBefore(r.Context(), userID, period, before)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeError(w, http.StatusNotFound, "no prior review")
			return
		}
		h.log.Error().Err(err).Str("user_id", userID).Msg("performance_review_prior_failed")
		writeError(w, http.StatusInternalServerError, "failed to load prior review")
		return
	}
	writeJSON(w, http.StatusOK, recordResponse(rec))
}

// ---------------------------------------------------------------------------
// Internal: GET /internal/performance-review/active-users
//
// Returns the list of user_ids that have an ACTIVE trading-system
// profile. The engine scheduler iterates this list to dispatch one
// review-generation job per user per cron tick (weekly Monday 06:00
// UTC, monthly 1st 06:00 UTC).
//
// Users without an active trading system are excluded: the review
// requires the system as its rulebook, so dispatching without one
// would produce an immediate 'precondition failed' fail-callback.
// ---------------------------------------------------------------------------

func (h *Handler) handleInternalActiveUsers(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.verifyInternalSecret(r) {
		writeError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	ids, err := h.store.ListActiveTradingSystemUserIDs(r.Context())
	if err != nil {
		h.log.Error().Err(err).Msg("performance_review_active_users_failed")
		writeError(w, http.StatusInternalServerError, "failed to list active users")
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"user_ids": ids,
		"count":    len(ids),
	})
}

// verifyInternalSecret performs a constant-time comparison of the
// X-Internal-Auth header against the configured shared secret. Uses
// the same SHA-256 pre-hash dance as tradingplan / tradingsystem so
// the secret length is never leaked via timing.
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

// recordResponse projects a Record into the JSON shape the SPA
// expects on /latest and /:id. Reviews in status='generating' return
// review=null so the SPA can render a spinner; status='failed'
// returns last_error so the SPA renders a retry CTA.
func recordResponse(rec *Record) map[string]interface{} {
	return map[string]interface{}{
		"id":           rec.ID,
		"period":       string(rec.Period),
		"period_start": rec.PeriodStart,
		"period_end":   rec.PeriodEnd,
		"status":       string(rec.Status),
		"has_review":   rec.Review != nil,
		"review":       rec.Review,
		"last_error":   rec.LastError,
		"created_at":   rec.CreatedAt,
		"updated_at":   rec.UpdatedAt,
	}
}

// historyRowResponse omits the heavy review JSONB blob - the SPA
// fetches the full review on demand via GET /:id.
func historyRowResponse(rec *Record) map[string]interface{} {
	return map[string]interface{}{
		"id":           rec.ID,
		"period":       string(rec.Period),
		"period_start": rec.PeriodStart,
		"period_end":   rec.PeriodEnd,
		"status":       string(rec.Status),
		"last_error":   rec.LastError,
		"created_at":   rec.CreatedAt,
		"updated_at":   rec.UpdatedAt,
	}
}

func writeJSON(w http.ResponseWriter, status int, body interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
