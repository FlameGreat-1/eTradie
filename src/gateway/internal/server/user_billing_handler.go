package server

import (
	"errors"
	"net/http"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	billingservice "github.com/flamegreat-1/etradie/src/billing/service"
	billingstore "github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
)

// UserBillingHandler exposes the regular-user-facing read endpoints that
// power the dashboard's Payment Methods card and Invoice History feed:
//
//   GET /api/v1/billing/payment-method  — latest card snapshot
//   GET /api/v1/billing/transactions    — paginated financial events
//
// Both are user-scoped: every query binds claims.UserID server-side, so
// a forged query parameter cannot escalate to another user's data. The
// handler is the read-side complement of BillingHandler (which owns the
// state-changing portal/checkout endpoints); they share the same
// gateway-side rate-limit primitive and the same JSON conventions.
//
// Admin variants of these queries already live on AdminBillingHandler
// behind the RequireAdmin middleware; this handler deliberately does
// NOT call RequireAdmin so non-admin users can read their own data.
type UserBillingHandler struct {
	queries *billingstore.UserQueries
	log     zerolog.Logger

	// Per-user token-bucket rate limiter. Defends both endpoints
	// against an authenticated-but-abusive caller (compromised
	// account, buggy SPA build). Default budget: 60 req/min, burst 30 —
	// same budget AdminBillingHandler uses, sized for the dashboard's
	// expected refetch interval (every 15s on user navigation,
	// occasional refresh button clicks).
	limit *billingservice.TokenBucketRateLimiter
}

// NewUserBillingHandler constructs the handler with default rate limits.
func NewUserBillingHandler(queries *billingstore.UserQueries) *UserBillingHandler {
	return &UserBillingHandler{
		queries: queries,
		log:     observability.Logger("user_billing_handler"),
		limit: billingservice.NewTokenBucketRateLimiter(billingservice.RateLimiterConfig{
			MaxKeys:    16384,
			RatePerSec: 60.0 / 60.0,
			Burst:      30,
		}),
	}
}

// RegisterRoutes mounts the two endpoints on mux.
//
// Chain order: authMiddleware -> csrfMiddleware -> handler. RequireCSRF
// short-circuits GET (these are read-only), but the wrap stays uniform
// with the rest of the gateway so future POST endpoints under the same
// resource (e.g. force-refresh, override) inherit CSRF without further
// changes.
func (h *UserBillingHandler) RegisterRoutes(
	mux *http.ServeMux,
	authMiddleware func(http.Handler) http.Handler,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	wrap := func(handler http.HandlerFunc) http.Handler {
		return authMiddleware(csrfMiddleware(http.HandlerFunc(handler)))
	}
	mux.Handle("/api/v1/billing/payment-method", wrap(h.handleGetPaymentMethod))
	mux.Handle("/api/v1/billing/transactions", wrap(h.handleListTransactions))
}

// guard is the common preamble: enforce GET, apply rate limit, resolve
// authenticated user_id. Returns (userID, ok). When ok=false the response
// is already written.
func (h *UserBillingHandler) guard(w http.ResponseWriter, r *http.Request) (string, bool) {
	if r.Method != http.MethodGet {
		rejectMethod(w, http.MethodGet)
		return "", false
	}
	claims := auth.ClaimsFromContext(r.Context())
	if claims == nil || claims.UserID == "" {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return "", false
	}
	if !h.limit.Allow(claims.UserID) {
		w.Header().Set("Retry-After", "30")
		writeJSONError(w, http.StatusTooManyRequests, "too many requests; please slow down")
		return "", false
	}
	return claims.UserID, true
}

// ---------------------------------------------------------------------------
// GET /api/v1/billing/payment-method
// ---------------------------------------------------------------------------

func (h *UserBillingHandler) handleGetPaymentMethod(w http.ResponseWriter, r *http.Request) {
	userID, ok := h.guard(w, r)
	if !ok {
		return
	}

	pm, err := h.queries.GetUserPaymentMethod(r.Context(), userID)
	if err != nil {
		if errors.Is(err, billingstore.ErrPaymentMethodNotConfigured) {
			// No payment method on file. 204 lets the SPA render the
			// empty state without parsing a body. We intentionally do
			// NOT 404 here — the endpoint exists; the resource is
			// absent.
			w.WriteHeader(http.StatusNoContent)
			return
		}
		h.log.Error().Err(err).Str("user_id", userID).Msg("user_payment_method_lookup_failed")
		writeJSONError(w, http.StatusInternalServerError, "failed to load payment method")
		return
	}
	writeJSON(w, http.StatusOK, pm)
}

// ---------------------------------------------------------------------------
// GET /api/v1/billing/transactions
// ---------------------------------------------------------------------------

func (h *UserBillingHandler) handleListTransactions(w http.ResponseWriter, r *http.Request) {
	userID, ok := h.guard(w, r)
	if !ok {
		return
	}

	page := parsePage(r)
	rows, total, err := h.queries.GetUserPaymentHistory(r.Context(), userID, page)
	if err != nil {
		h.log.Error().Err(err).Str("user_id", userID).Msg("user_payment_history_lookup_failed")
		writeJSONError(w, http.StatusInternalServerError, "failed to load transactions")
		return
	}
	if rows == nil {
		rows = []billingstore.UserPaymentHistoryRow{}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"rows":  rows,
		"total": total,
		"page":  effectivePage(page),
		"size":  userPageSize(page),
	})
}

// userPageSize echoes back the post-clamp page size. AdminQueries clamps
// at 200; UserQueries.GetUserPaymentHistory clamps at 100. Mirror that
// here so the SPA sees the size it actually got.
func userPageSize(p billingstore.Page) int {
	if p.Size <= 0 {
		return 50
	}
	if p.Size > 100 {
		return 100
	}
	return p.Size
}
