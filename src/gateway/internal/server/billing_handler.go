package server

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"sync"
	"time"

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
// allowReupgrade below.
var paidTiers = map[string]bool{
	"pro_byok":    true,
	"pro_managed": true,
}

// Subscription statuses that, when paired with a paid tier and an
// unexpired current_period_end, still entitle the user to the paid
// product. A user in any of these states is blocked from a fresh
// checkout because they already have an active provider subscription.
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
// BillingClient so provider API keys never live inside the gateway process.
type BillingHandler struct {
	subStore  *billingstore.SubscriptionStore
	client    *BillingClient
	userStore *auth.UserStore
	log       zerologLogger

	// In-process subscription cache.
	//
	// `handleGetSubscription` returned 500 on any transient DB error,
	// which the SPA does not retry. A 200 ms postgres slow-query was
	// enough to brick the dashboard for a paying customer. The cache
	// holds the last-known good result keyed by user_id for 30 s so
	// the very next request from the same user during the same window
	// hits cache and renders the correct tier even if the DB is wobbling.
	subCache *subscriptionCache
}

// zerologLogger is the minimal contract this file needs from the
// observability package's logger; declared as a local interface so the
// file builds against either zerolog or a test-time fake without an
// import cycle.
type zerologLogger interface {
	Warn() loggerEvent
	Error() loggerEvent
}

type loggerEvent interface {
	Str(key, val string) loggerEvent
	Err(err error) loggerEvent
	Msg(msg string)
}

// NewBillingHandler builds a handler with an in-process subscription cache.
func NewBillingHandler(
	subStore *billingstore.SubscriptionStore,
	client *BillingClient,
	userStore *auth.UserStore,
) *BillingHandler {
	return &BillingHandler{
		subStore:  subStore,
		client:    client,
		userStore: userStore,
		log:       newBillingLogger(),
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
			payload := map[string]any{
				"tier":   "free",
				"status": "active",
			}
			writeJSON(w, http.StatusOK, payload)
			return
		}
		// Genuine transient infrastructure failure. 503 is the correct
		// code (the SPA's existing retry policy retries 503 once with
		// short backoff). 500 would imply a caller bug and is NEVER
		// retried by the dashboard.
		h.log.Error().Err(err).Str("user_id", userID).Msg("billing_subscription_lookup_failed_after_retries")

		// Last-resort: serve the last-known-good cached snapshot if we
		// have one for this user. A paying customer must not see a
		// 503 just because the DB is wobbling.
		if cached, ok := h.subCache.peek(userID); ok {
			writeJSON(w, http.StatusOK, cached)
			return
		}
		writeJSONError(w, http.StatusServiceUnavailable, "subscription temporarily unavailable")
		return
	}

	h.subCache.put(userID, sub)
	writeJSON(w, http.StatusOK, sub)
}

// loadSubscriptionWithRetry calls subStore.GetSubscription up to 3 times
// with 50 ms / 100 ms backoff before giving up. NotFound is returned on
// the FIRST attempt so the caller can fast-path the default-free response.
// Context cancellation aborts immediately.
func (h *BillingHandler) loadSubscriptionWithRetry(ctx context.Context, userID string) (*billingstore.Subscription, error) {
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
		writeJSON(w, http.StatusConflict, map[string]any{
			"error":              "already subscribed",
			"current_tier":       current.Tier,
			"current_status":     current.Status,
			"current_period_end": current.CurrentPeriodEnd,
		})
		return
	case err != nil && !errors.Is(err, billingstore.ErrSubscriptionNotFound):
		// Transient DB error on the guard. Refuse the checkout rather
		// than risk a double-charge by proceeding blind. The SPA will
		// surface the 503 to the user; they can retry.
		h.log.Error().Err(err).Str("user_id", claims.UserID).Msg("billing_checkout_tier_guard_failed")
		writeJSONError(w, http.StatusServiceUnavailable, "billing temporarily unavailable; please retry")
		return
	}

	// -----------------------------------------------------------------
	// Defect 6 fix: log email-lookup failure instead of silently swallowing.
	// -----------------------------------------------------------------
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

// alreadyEntitled returns true if the user holds an active paid subscription
// that has not yet elapsed. Used by the checkout handler to block re-checkout
// from a user who would otherwise be billed twice.
//
// Logic:
//   - tier must be in paidTiers (free users can always upgrade);
//   - status must be in accessGrantingStatuses (genuinely-expired states
//     like `unpaid` and `expired` allow a fresh upgrade);
//   - for non-active statuses (paused, past_due, canceled, refunded), the
//     current_period_end must NOT have elapsed — a fully-elapsed paid
//     period is the canonical signal that the user has lost access and
//     must re-checkout to regain it.
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
// Bounds the impact of a transient DB hiccup: we serve a paying customer
// their last-known-good subscription snapshot rather than 503ing them out
// of their own dashboard. TTL is small (30 s) so a real tier change (push
// from billing service via SUBSCRIPTION_* event, or webhook landing on the
// gateway path) is reflected on the next non-cached refetch.
// ---------------------------------------------------------------------------

type subscriptionCache struct {
	ttl   time.Duration
	mu    sync.RWMutex
	rows  map[string]subscriptionCacheEntry
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

// ---------------------------------------------------------------------------
// Logger adapter
//
// The handler used to call writeJSONError-only; we now log structured fields
// for operator visibility. Wrap zerolog in a tiny adapter so a future swap
// to slog (or any other logger) is a one-place edit.
// ---------------------------------------------------------------------------

func newBillingLogger() zerologLogger {
	return &zerologAdapter{l: observability.Logger("billing_handler")}
}

type zerologAdapter struct {
	l interface {
		Warn() *zerologEventReal
		Error() *zerologEventReal
	}
}

// zerologEventReal is the concrete type from rs/zerolog. We re-import it
// indirectly via the observability package so this file does not pull
// rs/zerolog directly; the cast happens at construction time.
type zerologEventReal = struct{}

// To avoid a heavyweight adapter that mirrors every zerolog method, we use
// observability.Logger directly through a thin wrapper. The wrapper below
// re-exports the Warn/Error methods to the loggerEvent interface that the
// handler uses; under the hood, the wrapper calls the real zerolog logger.
// This keeps the field set fixed (Str + Err + Msg) and the package import
// graph small.

func (a *zerologAdapter) Warn() loggerEvent  { return newEventWrapper("warn") }
func (a *zerologAdapter) Error() loggerEvent { return newEventWrapper("error") }

type eventWrapper struct {
	level  string
	fields []logField
	err    error
}

type logField struct{ k, v string }

func newEventWrapper(level string) *eventWrapper {
	return &eventWrapper{level: level}
}

func (e *eventWrapper) Str(k, v string) loggerEvent {
	e.fields = append(e.fields, logField{k, v})
	return e
}

func (e *eventWrapper) Err(err error) loggerEvent {
	e.err = err
	return e
}

func (e *eventWrapper) Msg(msg string) {
	l := observability.Logger("billing_handler")
	var ev interface {
		Msg(string)
	}
	switch e.level {
	case "error":
		zev := l.Error()
		for _, f := range e.fields {
			zev = zev.Str(f.k, f.v)
		}
		if e.err != nil {
			zev = zev.Err(e.err)
		}
		ev = zev
	default:
		zev := l.Warn()
		for _, f := range e.fields {
			zev = zev.Str(f.k, f.v)
		}
		if e.err != nil {
			zev = zev.Err(e.err)
		}
		ev = zev
	}
	ev.Msg(msg)
}
