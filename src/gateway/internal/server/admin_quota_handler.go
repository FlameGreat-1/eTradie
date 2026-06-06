package server

import (
	"errors"
	"net/http"
	"strings"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	billingservice "github.com/flamegreat-1/etradie/src/billing/service"
	billingstore "github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
)

// AdminQuotaHandler exposes admin-only CRUD on tier_quota_policies.
//
// Chain: authMiddleware -> RequireAdmin -> csrfMiddleware -> handler.
// RequireAdmin sits between auth and CSRF so a non-admin gets 403
// before any state-changing concerns are evaluated. The CSRF
// middleware short-circuits safe methods (GET / HEAD / OPTIONS) and
// only gates POST / PUT / PATCH / DELETE; wrapping multi-method
// endpoints is correct by construction.
type AdminQuotaHandler struct {
	store *billingstore.QuotaPolicyStore
	log   zerolog.Logger

	// Per-admin token-bucket rate limiter. Mirrors AdminBillingHandler.
	// A runaway SPA refetch loop should not be allowed to slam the admin
	// quota endpoints. Keyed by admin user_id from the JWT.
	rateLimit *billingservice.TokenBucketRateLimiter
}

// NewAdminQuotaHandler builds the handler with default rate limits.
func NewAdminQuotaHandler(store *billingstore.QuotaPolicyStore) *AdminQuotaHandler {
	if store == nil {
		panic("admin_quota_handler: store must not be nil")
	}
	return &AdminQuotaHandler{
		store: store,
		log:   observability.Logger("admin_quota_handler"),
		rateLimit: billingservice.NewTokenBucketRateLimiter(billingservice.RateLimiterConfig{
			MaxKeys:    1024,
			RatePerSec: 60.0 / 60.0, // 60 req/min
			Burst:      30,
		}),
	}
}

// RegisterRoutes mounts the admin quota endpoints on mux.
func (h *AdminQuotaHandler) RegisterRoutes(
	mux *http.ServeMux,
	authMiddleware func(http.Handler) http.Handler,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	adminChain := func(handler http.HandlerFunc) http.Handler {
		return authMiddleware(auth.RequireAdmin(csrfMiddleware(http.HandlerFunc(handler))))
	}

	// Collection: GET only.
	mux.Handle("/api/v1/admin/quota/policies", adminChain(h.handleList))
	// Item: GET (fetch) + PUT (upsert). Path parameter is the tier
	// string. Trailing-slash variant covered by stdlib's mux
	// longest-prefix behaviour: the handler trims the prefix and parses
	// the remainder as the tier.
	mux.Handle("/api/v1/admin/quota/policies/", adminChain(h.handleItem))
}

// guard is the common preamble: enforce method via the caller, apply
// the per-admin rate limit, and resolve the admin's user_id. Returns
// the admin user_id and ok=true to proceed; on false the response has
// already been written.
func (h *AdminQuotaHandler) guard(w http.ResponseWriter, r *http.Request) (string, bool) {
	claims := auth.ClaimsFromContext(r.Context())
	if claims == nil {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return "", false
	}
	if !h.rateLimit.Allow(claims.UserID) {
		w.Header().Set("Retry-After", "30")
		writeJSONError(w, http.StatusTooManyRequests, "too many admin requests; please slow down")
		return "", false
	}
	return claims.UserID, true
}

// GET /api/v1/admin/quota/policies
func (h *AdminQuotaHandler) handleList(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.Header().Set("Allow", http.MethodGet)
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	adminID, ok := h.guard(w, r)
	if !ok {
		return
	}
	rows, err := h.store.ListPolicies(r.Context())
	if err != nil {
		h.log.Error().Err(err).Str("admin_id", adminID).Msg("admin_list_quota_policies_failed")
		writeJSONError(w, http.StatusInternalServerError, "failed to list quota policies")
		return
	}
	if rows == nil {
		rows = []*billingstore.QuotaPolicyRow{}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"rows":             rows,
		"canonical_tiers":  billingstore.CanonicalTiers,
	})
}

// handleItem dispatches GET / PUT on /api/v1/admin/quota/policies/{tier}
func (h *AdminQuotaHandler) handleItem(w http.ResponseWriter, r *http.Request) {
	tier := strings.TrimPrefix(r.URL.Path, "/api/v1/admin/quota/policies/")
	tier = strings.Trim(tier, "/ ")
	if tier == "" {
		writeJSONError(w, http.StatusNotFound, "tier path segment is required")
		return
	}

	switch r.Method {
	case http.MethodGet:
		h.handleGet(w, r, tier)
	case http.MethodPut:
		h.handlePut(w, r, tier)
	default:
		w.Header().Set("Allow", strings.Join([]string{http.MethodGet, http.MethodPut}, ", "))
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// GET /api/v1/admin/quota/policies/{tier}
func (h *AdminQuotaHandler) handleGet(w http.ResponseWriter, r *http.Request, tier string) {
	adminID, ok := h.guard(w, r)
	if !ok {
		return
	}
	row, err := h.store.GetPolicy(r.Context(), tier)
	if err != nil {
		if errors.Is(err, billingstore.ErrPolicyNotFound) {
			writeJSONError(w, http.StatusNotFound, "policy not found for tier")
			return
		}
		h.log.Error().
			Err(err).
			Str("admin_id", adminID).
			Str("tier", tier).
			Msg("admin_get_quota_policy_failed")
		writeJSONError(w, http.StatusInternalServerError, "failed to fetch quota policy")
		return
	}
	writeJSON(w, http.StatusOK, row)
}

// PUT /api/v1/admin/quota/policies/{tier}
func (h *AdminQuotaHandler) handlePut(w http.ResponseWriter, r *http.Request, tier string) {
	adminID, ok := h.guard(w, r)
	if !ok {
		return
	}

	var body billingstore.QuotaPolicyRow
	if err := auth.DecodeJSONStrict(w, r, &body, 0); err != nil {
		status, msg := auth.DecodeJSONError(err)
		writeJSONError(w, status, msg)
		return
	}

	// Path tier wins over body tier so an admin cannot accidentally
	// overwrite the wrong row by leaving a stale value in the editor.
	body.Tier = strings.ToLower(strings.TrimSpace(tier))

	if err := h.store.UpsertPolicy(r.Context(), &body, adminID); err != nil {
		h.log.Error().
			Err(err).
			Str("admin_id", adminID).
			Str("tier", body.Tier).
			Msg("admin_upsert_quota_policy_failed")
		// Validation failures surface as 400 so the SPA can show the
		// admin the exact field that failed. Anything else is 500.
		if strings.Contains(err.Error(), "validate") {
			writeJSONError(w, http.StatusBadRequest, err.Error())
			return
		}
		writeJSONError(w, http.StatusInternalServerError, "failed to update quota policy")
		return
	}

	// Re-read so the response carries the canonical row shape (with
	// updated_at + updated_by populated by the DB).
	row, err := h.store.GetPolicy(r.Context(), body.Tier)
	if err != nil {
		h.log.Warn().
			Err(err).
			Str("admin_id", adminID).
			Str("tier", body.Tier).
			Msg("admin_upsert_quota_policy_reread_failed")
		// Upsert already succeeded; degrade to echoing the request body.
		writeJSON(w, http.StatusOK, &body)
		return
	}

	h.log.Info().
		Str("admin_id", adminID).
		Str("tier", body.Tier).
		Int64("daily_input", row.DailyInputTokens).
		Int64("daily_output", row.DailyOutputTokens).
		Int64("monthly_input", row.MonthlyInputTokens).
		Int64("monthly_output", row.MonthlyOutputTokens).
		Int64("max_per_call", row.MaxInputTokensPerCall).
		Int("soft_cap_percent", row.SoftCapPercent).
		Bool("enforced", row.Enforced).
		Msg("admin_quota_policy_updated")

	writeJSON(w, http.StatusOK, row)
}
