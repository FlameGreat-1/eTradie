package server

import (
	"context"
	"errors"
	"net"
	"net/http"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	billingservice "github.com/flamegreat-1/etradie/src/billing/service"
	billingstore "github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
)

// netSplitHostPortImpl avoids a name clash between the import 'net' and
// the variable netSplitHostPort declared below.
func netSplitHostPortImpl(s string) (string, string, error) {
	return net.SplitHostPort(s)
}

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
	portalAud *billingstore.PortalAuditStore
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

	// Per-user token-bucket rate limiter. Defends /api/v1/billing/checkout
	// and /api/v1/billing/portal against an authenticated-but-abusive
	// user (compromised account or buggy SPA build). Keyed by user_id
	// from the JWT (cannot be spoofed). Default budget: 10 req/min,
	// burst 20. Implementation reuses the same TokenBucketRateLimiter
	// primitive the billing service uses on its webhook surface.
	userLimit *billingservice.TokenBucketRateLimiter
}

// NewBillingHandler builds a handler with the in-process subscription cache
// and per-user rate limiter.
func NewBillingHandler(
	subStore *billingstore.SubscriptionStore,
	portalAud *billingstore.PortalAuditStore,
	client *BillingClient,
	userStore *auth.UserStore,
) *BillingHandler {
	return &BillingHandler{
		subStore:  subStore,
		portalAud: portalAud,
		client:    client,
		userStore: userStore,
		log:       observability.Logger("billing_handler"),
		subCache:  newSubscriptionCache(30 * time.Second),
		userLimit: billingservice.NewTokenBucketRateLimiter(billingservice.RateLimiterConfig{
			MaxKeys:    16384,
			RatePerSec: 10.0 / 60.0, // 10 requests per minute
			Burst:      20,
		}),
	}
}

// allowUser enforces the per-user rate limit. Returns true on allow,
// false on reject (caller writes 429 with Retry-After).
func (h *BillingHandler) allowUser(userID string) bool {
	return h.userLimit.Allow(userID)
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
	mux.Handle("/api/v1/billing/portal", authMiddleware(csrfMiddleware(http.HandlerFunc(h.handleCreatePortal))))
}

// ---------------------------------------------------------------------------
// POST /api/v1/billing/portal
//
// Returns a one-shot URL on the original payment provider where the user
// can update their payment method, cancel, change plan, or download
// invoices. The provider is whichever one took the user's first payment
// (recorded as payment_provider on billing_subscriptions). The gateway
// resolves provider + provider_customer_id from the authoritative table
// so the JWT cannot be spoofed to escalate against another user.
// ---------------------------------------------------------------------------

func (h *BillingHandler) handleCreatePortal(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	claims := auth.ClaimsFromContext(r.Context())
	if claims == nil {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	if !h.allowUser(claims.UserID) {
		w.Header().Set("Retry-After", "60")
		h.recordPortalAudit(r, claims.UserID, "", "rate_limited", "per-user rate limit exceeded")
		writeJSONError(w, http.StatusTooManyRequests, "too many portal attempts; please slow down")
		return
	}

	// Resolve the authoritative subscription. We use the with-retry helper
	// so a transient DB hiccup does not force the user through the upgrade
	// flow when they already have an active subscription.
	sub, err := h.loadSubscriptionWithRetry(r.Context(), claims.UserID)
	if err != nil {
		if errors.Is(err, billingstore.ErrSubscriptionNotFound) {
			writeJSONError(w, http.StatusNotFound, "no active subscription")
			return
		}
		h.log.Error().Err(err).Str("user_id", claims.UserID).Msg("billing_portal_subscription_lookup_failed")
		writeJSONError(w, http.StatusServiceUnavailable, "billing temporarily unavailable; please retry")
		return
	}

	if sub.PaymentProvider == nil || *sub.PaymentProvider == "" || sub.ProviderCustomerID == nil || *sub.ProviderCustomerID == "" {
		// Subscription row exists but the provider link is incomplete.
		// This happens for the seed default-free row a user has before
		// any successful checkout. Treat it as 'no active subscription'
		// rather than confusing the user with a 500.
		writeJSONError(w, http.StatusNotFound, "no active subscription")
		return
	}

	respCtx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()

	resp, err := h.client.CreatePortalSession(respCtx, PortalRequest{
		Provider:           *sub.PaymentProvider,
		ProviderCustomerID: *sub.ProviderCustomerID,
		UserID:             claims.UserID,
	})
	if err != nil {
		switch {
		case errors.Is(err, ErrUpstreamNotSupported):
			h.recordPortalAudit(r, claims.UserID, *sub.PaymentProvider, "not_supported", err.Error())
			writeJSONError(w, http.StatusNotImplemented, "customer portal is not available for this account")
			return
		case errors.Is(err, ErrUpstreamRejected):
			h.recordPortalAudit(r, claims.UserID, *sub.PaymentProvider, "upstream_rejected", err.Error())
			writeJSONError(w, http.StatusBadRequest, "portal request rejected by billing service")
			return
		case errors.Is(err, ErrUpstreamUnavailable):
			h.recordPortalAudit(r, claims.UserID, *sub.PaymentProvider, "upstream_error", err.Error())
			writeJSONError(w, http.StatusBadGateway, "billing service unavailable")
			return
		}
		h.recordPortalAudit(r, claims.UserID, *sub.PaymentProvider, "error", err.Error())
		h.log.Error().Err(err).Str("user_id", claims.UserID).Msg("billing_portal_failed")
		writeJSONError(w, http.StatusInternalServerError, "portal failed")
		return
	}

	// Compliance audit row. Fire-and-forget with a 5s detached context
	// so a slow audit insert never blocks the user's redirect.
	h.recordPortalAudit(r, claims.UserID, *sub.PaymentProvider, "success", "")

	writeJSON(w, http.StatusOK, map[string]string{
		"portal_url": resp.PortalURL,
	})
}

// recordPortalAudit appends an audit row for /api/v1/billing/portal.
// Best-effort: errors are logged but never propagated, because the
// user's flow must not be blocked by an audit-table hiccup. SOC 2 /
// PCI-DSS auditors care that we attempt the write on every request;
// they accept that the table is best-effort consistent with logs as
// long as both surfaces are monitored.
func (h *BillingHandler) recordPortalAudit(r *http.Request, userID, provider, status, reason string) {
	if h.portalAud == nil {
		return
	}
	ev := &billingstore.PortalAuditEvent{
		UserID:    userID,
		Provider:  provider,
		ClientIP:  clientIPFromRequest(r),
		UserAgent: r.UserAgent(),
		Status:    status,
		Error:     reason,
	}
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := h.portalAud.Append(ctx, ev); err != nil {
			h.log.Warn().Err(err).Str("user_id", userID).Str("status", status).Msg("billing_portal_audit_append_failed")
		}
	}()
}

// clientIPFromRequest returns r.RemoteAddr's IP component. We do NOT
// trust X-Forwarded-For here because this endpoint is on the gateway
// which is itself the terminating reverse-proxy in our deployment.
// If you front the gateway with another proxy, add a header-walking
// helper analogous to billing/server/http.go::clientIP.
func clientIPFromRequest(r *http.Request) string {
	host, _, err := netSplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

// netSplitHostPort is wrapped so the import list stays explicit.
var netSplitHostPort = func(s string) (string, string, error) {
	return netSplitHostPortImpl(s)
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
			writeJSON(w, http.StatusOK, userSubscriptionView(cached))
			return
		}

		// 503 is the correct code (transient) and IS in the SPA's
		// retry policy. 500 implied a caller bug and was never retried.
		writeJSONError(w, http.StatusServiceUnavailable, "subscription temporarily unavailable")
		return
	}

	h.subCache.put(userID, sub)
	writeJSON(w, http.StatusOK, userSubscriptionView(sub))
}

// userSubscriptionView projects a Subscription onto the fields the
// user-facing dashboard needs. The provider customer / subscription IDs
// and internal timestamps are deliberately excluded: the dashboard
// reads tier/status from /auth/me and never needs the provider
// identifiers, which the portal endpoint resolves server-side.
func userSubscriptionView(sub *billingstore.Subscription) map[string]any {
	if sub == nil {
		return map[string]any{"tier": "free", "status": "active"}
	}
	view := map[string]any{
		"tier":   sub.Tier,
		"status": sub.Status,
	}
	if sub.CurrentPeriodEnd != nil {
		view["current_period_end"] = sub.CurrentPeriodEnd.UTC().Format(time.RFC3339)
	}
	return view
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

	claimsForLimit := auth.ClaimsFromContext(r.Context())
	if claimsForLimit == nil {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}
	if !h.allowUser(claimsForLimit.UserID) {
		w.Header().Set("Retry-After", "60")
		writeJSONError(w, http.StatusTooManyRequests, "too many checkout attempts; please slow down")
		return
	}

	var req checkoutRequest
	if err := auth.DecodeJSONStrict(w, r, &req, 16*1024); err != nil {
		status, msg := auth.DecodeJSONError(err)
		writeJSONError(w, status, msg)
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
			"error":          "already subscribed",
			"current_tier":   current.Tier,
			"current_status": current.Status,
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
