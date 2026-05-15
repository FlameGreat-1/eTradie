package server

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	billingservice "github.com/flamegreat-1/etradie/src/billing/service"
	billingstore "github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
)

// AdminBillingHandler exposes read-only admin endpoints for the
// billing tables:
//
//   - subscriptions list (every user's current tier/status/provider),
//   - subscription-events feed (every webhook-driven transaction),
//   - per-user subscription-events drill-down,
//   - LLM usage list (every user's monthly AI-token counters),
//   - LLM usage aggregate (system-wide rollup tiles).
//
// Every endpoint is mounted behind auth -> RequireAdmin -> CSRF in
// RegisterRoutes. The handler itself does NOT re-check the role; the
// dedicated middleware is the single source of truth. This matches
// the pattern used by every other admin endpoint in the codebase
// (auth/admin/users, etc.) and keeps audit posture uniform.
type AdminBillingHandler struct {
	queries *billingstore.AdminQueries
	log     zerolog.Logger

	// Per-admin token-bucket rate limiter. An admin SPA with a runaway
	// refetch loop should not be allowed to scan the events table
	// hundreds of times per second. Default budget: 60 req/min, burst
	// 30. Keyed by admin user_id from the JWT.
	adminLimit *billingservice.TokenBucketRateLimiter
}

// NewAdminBillingHandler constructs the handler with default rate
// limits. The rate limiter is internal so production wiring stays
// simple; future tuning lives behind a config flag if it ever
// becomes operationally necessary.
func NewAdminBillingHandler(queries *billingstore.AdminQueries) *AdminBillingHandler {
	return &AdminBillingHandler{
		queries: queries,
		log:     observability.Logger("admin_billing_handler"),
		adminLimit: billingservice.NewTokenBucketRateLimiter(billingservice.RateLimiterConfig{
			MaxKeys:    1024,
			RatePerSec: 60.0 / 60.0, // 60 req/min
			Burst:      30,
		}),
	}
}

// RegisterRoutes mounts every admin billing endpoint on mux.
//
// Chain order: authMiddleware -> RequireAdmin -> csrfMiddleware -> handler.
// RequireAdmin sits between auth and CSRF so a non-admin gets 403
// before any state-changing concerns are evaluated; on the read-only
// GET endpoints in this handler the CSRF middleware short-circuits
// safe methods anyway, but the chain order is uniform with the rest
// of the gateway for future POST/DELETE admin endpoints.
func (h *AdminBillingHandler) RegisterRoutes(
	mux *http.ServeMux,
	authMiddleware func(http.Handler) http.Handler,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	adminChain := func(handler http.HandlerFunc) http.Handler {
		return authMiddleware(auth.RequireAdmin(csrfMiddleware(http.HandlerFunc(handler))))
	}

	mux.Handle("/api/v1/admin/billing/subscriptions", adminChain(h.handleListSubscriptions))
	mux.Handle("/api/v1/admin/billing/subscriptions/", adminChain(h.handleSubscriptionPath))
	mux.Handle("/api/v1/admin/billing/transactions", adminChain(h.handleListTransactions))
	mux.Handle("/api/v1/admin/billing/llm-usage", adminChain(h.handleListLLMUsage))
	mux.Handle("/api/v1/admin/billing/llm-usage/aggregate", adminChain(h.handleAggregateLLMUsage))
}

// ---------------------------------------------------------------------------
// Common helpers (used by handler methods landed in the next commit)
// ---------------------------------------------------------------------------

// allowAdmin enforces the per-admin rate limit. Returns true on allow,
// false on reject (caller writes 429 with Retry-After).
func (h *AdminBillingHandler) allowAdmin(adminID string) bool {
	return h.adminLimit.Allow(adminID)
}

// parsePage extracts (page, size) from the request query string with
// safe defaults and hard caps. Invalid integers fall back to defaults
// rather than 400 so a UI bug never blocks an admin entirely.
func parsePage(r *http.Request) billingstore.Page {
	page, _ := strconv.Atoi(strings.TrimSpace(r.URL.Query().Get("page")))
	size, _ := strconv.Atoi(strings.TrimSpace(r.URL.Query().Get("size")))
	return billingstore.Page{Page: page, Size: size}
}

// rejectMethod is the standard 405 reply for the GET-only endpoints.
func rejectMethod(w http.ResponseWriter, allowed string) {
	w.Header().Set("Allow", allowed)
	writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
}

// handleSubscriptionPath dispatches the sub-resource routes mounted
// under /api/v1/admin/billing/subscriptions/. Today only one form is
// recognised:
//
//   GET /api/v1/admin/billing/subscriptions/{user_id}/events
//
// Unknown sub-paths return 404 so a typo in the SPA does not silently
// fall through to the list endpoint. The handler body lives in the
// next commit; this commit just stubs the dispatcher so the route
// table is observable and the type compiles.
func (h *AdminBillingHandler) handleSubscriptionPath(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/v1/admin/billing/subscriptions/")
	parts := strings.Split(path, "/")
	if len(parts) == 2 && parts[1] == "events" && strings.TrimSpace(parts[0]) != "" {
		h.handleUserTransactionHistory(w, r, parts[0])
		return
	}
	writeJSONError(w, http.StatusNotFound, "not found")
}

// ---------------------------------------------------------------------------
// Handler methods
// ---------------------------------------------------------------------------

// guard is the common preamble for every method: enforce GET, apply
// the per-admin rate limit, and resolve the admin's user_id. Returns
// the admin user_id and ok=true to proceed; on false the response has
// already been written.
func (h *AdminBillingHandler) guard(w http.ResponseWriter, r *http.Request) (string, bool) {
	if r.Method != http.MethodGet {
		rejectMethod(w, http.MethodGet)
		return "", false
	}
	claims := auth.ClaimsFromContext(r.Context())
	if claims == nil {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return "", false
	}
	if !h.allowAdmin(claims.UserID) {
		w.Header().Set("Retry-After", "30")
		writeJSONError(w, http.StatusTooManyRequests, "too many admin requests; please slow down")
		return "", false
	}
	return claims.UserID, true
}

// GET /api/v1/admin/billing/subscriptions
func (h *AdminBillingHandler) handleListSubscriptions(w http.ResponseWriter, r *http.Request) {
	adminID, ok := h.guard(w, r)
	if !ok {
		return
	}
	q := r.URL.Query()
	filter := billingstore.SubscriptionFilter{
		Tier:     strings.TrimSpace(q.Get("tier")),
		Status:   strings.TrimSpace(q.Get("status")),
		Provider: strings.TrimSpace(q.Get("provider")),
		Search:   strings.TrimSpace(q.Get("search")),
	}
	page := parsePage(r)
	rows, total, err := h.queries.ListSubscriptions(r.Context(), filter, page)
	if err != nil {
		h.log.Error().Err(err).Str("admin_id", adminID).Msg("admin_list_subscriptions_failed")
		writeJSONError(w, http.StatusInternalServerError, "failed to list subscriptions")
		return
	}
	if rows == nil {
		rows = []billingstore.AdminSubscriptionRow{}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"rows":  rows,
		"total": total,
		"page":  effectivePage(page),
		"size":  effectiveSize(page),
	})
}

// GET /api/v1/admin/billing/transactions
func (h *AdminBillingHandler) handleListTransactions(w http.ResponseWriter, r *http.Request) {
	adminID, ok := h.guard(w, r)
	if !ok {
		return
	}
	q := r.URL.Query()
	filter := billingstore.EventFilter{
		Provider:  strings.TrimSpace(q.Get("provider")),
		EventName: strings.TrimSpace(q.Get("event_name")),
		UserID:    strings.TrimSpace(q.Get("user_id")),
		Search:    strings.TrimSpace(q.Get("search")),
	}
	page := parsePage(r)
	rows, total, err := h.queries.ListSubscriptionEvents(r.Context(), filter, page)
	if err != nil {
		h.log.Error().Err(err).Str("admin_id", adminID).Msg("admin_list_transactions_failed")
		writeJSONError(w, http.StatusInternalServerError, "failed to list transactions")
		return
	}
	if rows == nil {
		rows = []billingstore.AdminSubscriptionEventRow{}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"rows":  rows,
		"total": total,
		"page":  effectivePage(page),
		"size":  effectiveSize(page),
	})
}

// GET /api/v1/admin/billing/subscriptions/{user_id}/events
func (h *AdminBillingHandler) handleUserTransactionHistory(w http.ResponseWriter, r *http.Request, userID string) {
	adminID, ok := h.guard(w, r)
	if !ok {
		return
	}
	limit, _ := strconv.Atoi(strings.TrimSpace(r.URL.Query().Get("limit")))
	if limit <= 0 {
		limit = 100
	}
	rows, err := h.queries.GetUserSubscriptionEvents(r.Context(), userID, limit)
	if err != nil {
		h.log.Error().
			Err(err).
			Str("admin_id", adminID).
			Str("target_user_id", userID).
			Msg("admin_user_transactions_failed")
		writeJSONError(w, http.StatusInternalServerError, "failed to list user transactions")
		return
	}
	if rows == nil {
		rows = []billingstore.AdminSubscriptionEventRow{}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"rows":    rows,
		"user_id": userID,
	})
}

// GET /api/v1/admin/billing/llm-usage
func (h *AdminBillingHandler) handleListLLMUsage(w http.ResponseWriter, r *http.Request) {
	adminID, ok := h.guard(w, r)
	if !ok {
		return
	}
	search := strings.TrimSpace(r.URL.Query().Get("search"))
	page := parsePage(r)
	rows, total, err := h.queries.ListLLMUsage(r.Context(), search, page)
	if err != nil {
		h.log.Error().Err(err).Str("admin_id", adminID).Msg("admin_list_llm_usage_failed")
		writeJSONError(w, http.StatusInternalServerError, "failed to list LLM usage")
		return
	}
	if rows == nil {
		rows = []billingstore.AdminLLMUsageRow{}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"rows":  rows,
		"total": total,
		"page":  effectivePage(page),
		"size":  effectiveSize(page),
	})
}

// GET /api/v1/admin/billing/llm-usage/aggregate
func (h *AdminBillingHandler) handleAggregateLLMUsage(w http.ResponseWriter, r *http.Request) {
	adminID, ok := h.guard(w, r)
	if !ok {
		return
	}
	agg, err := h.queries.AggregateLLMUsage(r.Context())
	if err != nil {
		h.log.Error().Err(err).Str("admin_id", adminID).Msg("admin_aggregate_llm_usage_failed")
		writeJSONError(w, http.StatusInternalServerError, "failed to aggregate LLM usage")
		return
	}
	writeJSON(w, http.StatusOK, agg)
}

// effectivePage / effectiveSize echo back the post-normalisation
// values so the SPA can render the page/size it actually got, not
// what it asked for.
func effectivePage(p billingstore.Page) int {
	if p.Page <= 0 {
		return 1
	}
	return p.Page
}

func effectiveSize(p billingstore.Page) int {
	if p.Size <= 0 {
		return 50
	}
	if p.Size > 200 {
		return 200
	}
	return p.Size
}
