package server

import (
	"encoding/json"
	"net/http"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/billing/store"
)

type BillingHandler struct {
	subStore *store.SubscriptionStore
}

func NewBillingHandler(subStore *store.SubscriptionStore) *BillingHandler {
	return &BillingHandler{subStore: subStore}
}

func (h *BillingHandler) RegisterRoutes(mux *http.ServeMux, authMiddleware func(http.Handler) http.Handler) {
	mux.Handle("/api/v1/billing/subscription", authMiddleware(http.HandlerFunc(h.handleGetSubscription)))
	mux.Handle("/api/v1/billing/checkout", authMiddleware(http.HandlerFunc(h.handleCreateCheckout)))
}

func (h *BillingHandler) handleGetSubscription(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	userID := auth.UserIDFromContext(r.Context())
	sub, err := h.subStore.GetSubscription(r.Context(), userID)
	if err != nil {
		// If not found, return a default free tier sub
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"tier":   "free",
			"status": "active",
		})
		return
	}

	writeJSON(w, http.StatusOK, sub)
}

type checkoutRequest struct {
	Provider string `json:"provider"` // "paddle" or "lemonsqueezy"
	Tier     string `json:"tier"`     // "pro_byok" or "pro_managed"
}

func (h *BillingHandler) handleCreateCheckout(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	var req checkoutRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSONError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	// This is where the integration with Paddle/Lemon Squeezy would happen
	// For now, we return a mock checkout URL based on the provider
	var checkoutURL string
	switch req.Provider {
	case "paddle":
		checkoutURL = "https://checkout.paddle.com/test-checkout-url"
	case "lemonsqueezy":
		checkoutURL = "https://etradie.lemonsqueezy.com/checkout/buy/test-id"
	default:
		writeJSONError(w, http.StatusBadRequest, "invalid provider")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{
		"checkout_url": checkoutURL,
	})
}
