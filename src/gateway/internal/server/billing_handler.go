package server

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	billingstore "github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
)

// validTiers is the canonical allowlist of paid tiers the dashboard may
// initiate a checkout for. Free is intentionally excluded: a checkout for
// a free tier is meaningless.
var validTiers = map[string]bool{
	"pro_byok":    true,
	"pro_managed": true,
}

var validProviders = map[string]bool{
	"paddle":       true,
	"lemonsqueezy": true,
}

// paidTiers is the set of tiers that, when held by the user, block a
// fresh checkout (defect 1: prevent double-subscriptions). A user can
// still re-checkout if their paid period has elapsed; see
// alreadyEntitled below.
var paidTiers = map[string]bool{
	"pro_byok":    true,
	"pro_managed": true,
}

// accessGrantingStatuses are subscription statuses that, when paired
// with a paid tier and an unexpired current_period_end, still entitle
// the user to the paid product. A user in any of these states is
// blocked from a fresh checkout because they already have an active
// provider subscription.
var accessGrantingStatuses = map[string]bool{
	"active":   true,
	"past_due": true,
	"paused":   true,
	"canceled": true, // canceled-but-paid-period-not-yet-elapsed
	"refunded": true,
}

// BillingHandler exposes the dashboard-facing /api/v1/billing/* surface.
// All endpoints sit behind the auth + CSRF middleware. The handler
// delegates checkout creation to the billing microservice via
// BillingClient so provider API keys never live inside the gateway
// process.
type BillingHandler struct {
	subStore  *billingstore.SubscriptionStore
	client    *BillingClient
	userStore *auth.UserStore
	log       zerolog.Logger

	// subCache: in-process last-known-good cache, keyed by user_id.
	//
	// The previous implementation returned 500 on any non-NotFound DB
	// error from subStore.GetSubscription. The SPA does not retry 500s,
	// so a 200 ms postgres slow-query was enough to render a paying
	// customer's dashboard as broken. The cache holds the latest
	// successful read for 30 s; if a subsequent lookup fails AND a
	// cached entry exists, we serve the cached snapshot rather than
	// 503ing the customer out of their own account.
	subCache *subscriptionCache
}

// NewBillingHandler builds a handler with the in-process subscription cache.
func NewBillingHandler(
	subStore *billingstore.SubscriptionStore,
	client *BillingClient,
	userStore *auth.UserStore,
) *BillingHandler {
	return &BillingHandler{
		subStore:  subStore,
		client:    client,
		userStore: userStore,
		log:       observability.Logger("billing_handler"),
		subCache:  newSubscriptionCache(30 * time.Second),
	}
}

// RegisterRoutes mounts the dashboard-facing billing endpoints.
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

	sub, err := h.loadSubscriptionWithRetry(r.Context(), userID)
	if err != nil {
		if errors.Is(err, billingstore.ErrSubscriptionNotFound) {
			writeJSON(w, http.StatusOK, map[string]any{
				"tier":   "free",
				"status": "active",
			})
			return
		}
		h.log.Error().Err(err).Str("user_id", userID).Msg("billing_subscription_lookup_failed_after_retries")

		// Last-resort: serve the last-known-good cached snapshot if we
		// have one. A paying customer must not see 503 because the DB
		// is wobbling for a hundred milliseconds.
		if cached, ok := h.subCache.peek(userID); ok {
			writeJSON(w, http.StatusOK, cached)
			return
		}

		// 503 is the correct code (transient) and IS in the SPA's
		// retry policy. 500 implied a caller bug and was never retried.
		writeJSONError(w, http.StatusServiceUnavailable, "subscription temporarily unavailable")
		return
	}

	h.subCache.put(userID, sub)
	writeJSON(w, http.StatusOK, sub)
}

// loadSubscriptionWithRetry calls subStore.GetSubscription up to 3 times
// with 50 ms / 100 ms backoff before giving up. NotFound is returned on
// the FIRST attempt so the caller can fast-path to the default-free
// response. Context cancellation aborts immediately.
func (h *BillingHandler) loadSubscriptionWithRetry(
	ctx context.Context, userID string,
) (*billingstore.Subscription, error) {
	var lastErr error
	delays := []time.Duration{0, 50 * time.Millisecond, 100 * time.Millisecond}
	for _, d := range delays {
		if d > 0 {
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			case <-time.After(d):
			}
		}
		sub, err := h.subStore.GetSubscription(ctx, userID)
		if err == nil {
			return sub, nil
		}
		if errors.Is(err, billingstore.ErrSubscriptionNotFound) {
			return nil, err
		}
		lastErr = err
	}
	return nil, lastErr
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

	// -----------------------------------------------------------------
	// Defect 1 fix: enforce current-tier guard before allowing checkout.
	//
	// We do NOT trust claims.Tier here. It can be:
	//   - stale (access token issued before a refund webhook landed),
	//   - frozen (a service-issued token carries a snapshot tier),
	//   - wrong (a refresh that happened before billing_subscriptions
	//     was updated).
	// The authoritative source is the billing_subscriptions table.
	// -----------------------------------------------------------------
	guardCtx, cancelGuard := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancelGuard()
	current, err := h.subStore.GetSubscription(guardCtx, claims.UserID)
	switch {
	case err == nil && h.alreadyEntitled(current):
		payload := map[string]any{
			"error":           "already subscribed",
			"current_tier":    current.Tier,
			"current_status":  current.Status,
		}
		if current.CurrentPeriodEnd != nil {
			payload["current_period_end"] = current.CurrentPeriodEnd.UTC().Format(time.RFC3339)
		}
		writeJSON(w, http.StatusConflict, payload)
		return
	case err != nil && !errors.Is(err, billingstore.ErrSubscriptionNotFound):
		// Transient DB error on the guard. Refuse the checkout rather
		// than risk a double-charge by proceeding blind. The SPA shows
		// the 503 and the user can retry.
		h.log.Error().Err(err).Str("user_id", claims.UserID).Msg("billing_checkout_tier_guard_failed")
		writeJSONError(w, http.StatusServiceUnavailable, "billing temporarily unavailable; please retry")
		return
	}

	// Defect 6 fix: log email-lookup failure rather than silently
	// swallowing it.
	email := ""
	lookupCtx, cancelLookup := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancelLookup()
	u, lookupErr := h.userStore.GetUserByID(lookupCtx, claims.UserID)
	if lookupErr != nil {
		h.log.Warn().Err(lookupErr).Str("user_id", claims.UserID).Msg("billing_checkout_email_lookup_failed")
	} else if u != nil {
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

// alreadyEntitled returns true if the user holds an active paid
// subscription that has not yet elapsed. Used by the checkout handler
// to block re-checkout from a user who would otherwise be billed twice.
//
// Logic:
//   - tier must be in paidTiers (free users can always upgrade);
//   - status must be in accessGrantingStatuses (genuinely-expired
//     states like `unpaid` and `expired` allow a fresh upgrade);
//   - for non-active statuses (paused, past_due, canceled, refunded),
//     the current_period_end must NOT have elapsed — a fully-elapsed
//     paid period is the canonical signal that the user has lost
//     access and must re-checkout to regain it.
func (h *BillingHandler) alreadyEntitled(sub *billingstore.Subscription) bool {
	if sub == nil {
		return false
	}
	if !paidTiers[sub.Tier] {
		return false
	}
	if !accessGrantingStatuses[sub.Status] {
		return false
	}
	if sub.Status == "active" {
		return true
	}
	if sub.CurrentPeriodEnd == nil {
		// Non-active status with no recorded period end: treat as
		// elapsed so the user can re-checkout rather than be locked.
		return false
	}
	return time.Now().UTC().Before(*sub.CurrentPeriodEnd)
}

// ---------------------------------------------------------------------------
// In-process subscription cache.
//
// Bounds the impact of a transient DB hiccup: we serve a paying
// customer their last-known-good subscription snapshot rather than
// 503ing them out of their own dashboard. TTL is small (30 s) so a
// real tier change — either pushed via the SUBSCRIPTION_* alert event
// or detected on the next non-cached refetch — is reflected promptly.
// ---------------------------------------------------------------------------

type subscriptionCache struct {
	ttl  time.Duration
	mu   sync.RWMutex
	rows map[string]subscriptionCacheEntry
}

type subscriptionCacheEntry struct {
	sub *billingstore.Subscription
	at  time.Time
}

func newSubscriptionCache(ttl time.Duration) *subscriptionCache {
	return &subscriptionCache{ttl: ttl, rows: map[string]subscriptionCacheEntry{}}
}

func (c *subscriptionCache) put(userID string, sub *billingstore.Subscription) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.rows[userID] = subscriptionCacheEntry{sub: sub, at: time.Now()}
}

func (c *subscriptionCache) peek(userID string) (*billingstore.Subscription, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	e, ok := c.rows[userID]
	if !ok {
		return nil, false
	}
	if time.Since(e.at) > c.ttl {
		return nil, false
	}
	return e.sub, true
}
