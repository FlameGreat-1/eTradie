package server

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	"github.com/flamegreat-1/etradie/src/auth"
	billingstore "github.com/flamegreat-1/etradie/src/billing/store"
)

// validTiers is the canonical allowlist of paid tiers the dashboard may
// initiate a checkout for. Free is intentionally excluded: a checkout for a
// free tier is meaningless.
var validTiers = map[string]bool{
	"pro_byok":    true,
	"pro_managed": true,
}

var validProviders = map[string]bool{
	"paddle":       true,
	"lemonsqueezy": true,
}

// BillingHandler exposes the dashboard-facing /api/v1/billing/* surface.
// All endpoints sit behind the auth middleware (require a valid Bearer JWT).
// The handler delegates checkout creation to the billing microservice via
// BillingClient so provider API keys never live inside the gateway process.
type BillingHandler struct {
	subStore  *billingstore.SubscriptionStore
	client    *BillingClient
	userStore *auth.UserStore
}

func NewBillingHandler(
	subStore *billingstore.SubscriptionStore,
	client *BillingClient,
	userStore *auth.UserStore,
) *BillingHandler {
	return &BillingHandler{subStore: subStore, client: client, userStore: userStore}
}

// RegisterRoutes mounts the dashboard-facing billing endpoints on the
// given mux.
//
// csrfMiddleware is layered between auth and the handler so the
// state-changing /api/v1/billing/checkout is CSRF-protected. The
// read-only /api/v1/billing/subscription endpoint is wrapped too;
// RequireCSRF short-circuits GET, so wrapping is a no-op for that
// route and keeps the registration pattern uniform.
func (h *BillingHandler) RegisterRoutes(
	mux *http.ServeMux,
	authMiddleware func(http.Handler) http.Handler,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	mux.Handle("/api/v1/billing/subscription", authMiddleware(csrfMiddleware(http.HandlerFunc(h.handleGetSubscription))))
	mux.Handle("/api/v1/billing/checkout", authMiddleware(csrfMiddleware(http.HandlerFunc(h.handleCreateCheckout))))
}

// ---------------------------------------------------------------------------
// GET /api/v1/billing/subscription
// ---------------------------------------------------------------------------

func (h *BillingHandler) handleGetSubscription(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	userID := auth.UserIDFromContext(r.Context())
	sub, err := h.subStore.GetSubscription(r.Context(), userID)
	if err != nil {
		if errors.Is(err, billingstore.ErrSubscriptionNotFound) {
			writeJSON(w, http.StatusOK, map[string]any{
				"tier":   "free",
				"status": "active",
			})
			return
		}
		// Genuine infrastructure failure. Surface as 500 so the dashboard does
		// not silently treat a paying customer as free during DB hiccups.
		writeJSONError(w, http.StatusInternalServerError, "failed to load subscription")
		return
	}
	writeJSON(w, http.StatusOK, sub)
}

// ---------------------------------------------------------------------------
// POST /api/v1/billing/checkout
// ---------------------------------------------------------------------------

type checkoutRequest struct {
	Provider string `json:"provider"`
	Tier     string `json:"tier"`
}

func (h *BillingHandler) handleCreateCheckout(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	var req checkoutRequest
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 16*1024)).Decode(&req); err != nil {
		writeJSONError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	if !validProviders[req.Provider] {
		writeJSONError(w, http.StatusBadRequest, "invalid provider; must be one of paddle, lemonsqueezy")
		return
	}
	if !validTiers[req.Tier] {
		writeJSONError(w, http.StatusBadRequest, "invalid tier; must be one of pro_byok, pro_managed")
		return
	}

	claims := auth.ClaimsFromContext(r.Context())
	if claims == nil {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	// Look up the canonical email from the user store so the provider
	// pre-fills the checkout form. Failure here is non-fatal: we proceed
	// without an email rather than blocking the upgrade.
	email := ""
	lookupCtx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()
	if u, err := h.userStore.GetUserByID(lookupCtx, claims.UserID); err == nil && u != nil {
		email = u.Email
	}

	respCtx, cancelResp := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancelResp()

	resp, err := h.client.CreateCheckout(respCtx, CheckoutRequest{
		Provider:  req.Provider,
		Tier:      req.Tier,
		UserID:    claims.UserID,
		UserEmail: email,
	})
	if err != nil {
		switch {
		case errors.Is(err, ErrUpstreamRejected):
			writeJSONError(w, http.StatusBadRequest, "checkout rejected by billing service")
			return
		case errors.Is(err, ErrUpstreamUnavailable):
			writeJSONError(w, http.StatusBadGateway, "billing service unavailable")
			return
		}
		writeJSONError(w, http.StatusInternalServerError, "checkout failed")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{
		"checkout_url": resp.CheckoutURL,
	})
}
