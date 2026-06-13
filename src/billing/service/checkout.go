package service

import (
	"bytes"
	"context"
	cryptoRand "crypto/rand"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/billing/events"
)

// CheckoutRequest is the gateway-side request shape that arrives at the
// billing service's /internal/checkout endpoint. The user's identity has
// already been authenticated by the gateway; we trust the user_id and email
// because the call is over the service-to-service shared secret.
type CheckoutRequest struct {
	Provider  string      `json:"provider"`
	Tier      events.Tier `json:"tier"`
	UserID    string      `json:"user_id"`
	UserEmail string      `json:"user_email"`
}

// CheckoutResponse is the gateway-side response shape returned by the
// billing service's /internal/checkout endpoint.
type CheckoutResponse struct {
	CheckoutURL string `json:"checkout_url"`
}

// Sentinel errors. The HTTP layer maps these to 4xx (caller error) vs 5xx
// (provider/infrastructure error).
var (
	ErrInvalidProvider     = errors.New("billing: invalid provider")
	ErrInvalidTier         = errors.New("billing: invalid tier")
	ErrUnconfiguredProduct = errors.New("billing: provider product is not configured for this tier")
	ErrProviderAPI         = errors.New("billing: provider api error")
	// ErrPortalNotSupported is returned by CreatePortalSession when the
	// provider response carries no portal URL. The Lemon Squeezy customer
	// resource exposes attributes.urls.customer_portal only for accounts
	// that have completed at least one successful checkout; the gateway
	// maps this to a 501 so the SPA shows a clear 'portal unavailable'
	// toast instead of redirecting the user to an empty URL.
	ErrPortalNotSupported = errors.New("billing: portal not supported by provider")
)

// PortalRequest is the gateway-side request shape for /internal/portal.
// The gateway has already looked up the user's (provider, customer_id)
// from billing_subscriptions and resolved their identity from the JWT.
type PortalRequest struct {
	Provider           string `json:"provider"`
	ProviderCustomerID string `json:"provider_customer_id"`
	UserID             string `json:"user_id"`
}

// PortalResponse is the gateway-side response. PortalURL is the one-shot
// provider-managed page where the customer can update card, cancel,
// change plan, or download invoices. Paddle expires its portal_session
// in minutes by design; the gateway must NOT cache this value.
type PortalResponse struct {
	PortalURL string `json:"portal_url"`
}

// CheckoutService creates one-shot checkout URLs against the configured
// payment providers. It owns the provider API keys; user-facing services
// never see them.
//
// Idempotency invariant: the same (user_id, provider, tier) tuple resolves
// to the SAME checkout URL for `intentTTL` (default 5 minutes). This
// defeats double-click and navigation-race double-charges. The cache is
// backed by billing_checkout_intents and pruned by the reconciler janitor;
// callers do not need to manage lifecycle.
//
// Resilience: every outbound provider call passes through a per-provider
// circuit breaker so a hard-down provider fast-fails after
// FailureThreshold consecutive 5xx / transport errors instead of pinning
// goroutines on a dead TCP socket.
type CheckoutService struct {
	cfg       CheckoutConfig
	client    *http.Client
	log       zerolog.Logger
	intents   checkoutIntentStore // optional; nil disables the cache for tests
	intentTTL time.Duration

	// Per-provider circuit breakers. Keyed by canonical provider name
	// ("paddle", "lemonsqueezy"). nil-valued lookups are treated as
	// 'always allow' so an unmapped provider still works.
	breakers map[string]*Breaker
}

// checkoutIntentStore is the narrow contract the service needs from the
// idempotency cache. *store.CheckoutIntentStore satisfies it directly.
// Declared here as an interface so unit tests can inject a fake without
// importing the store package.
type checkoutIntentStore interface {
	Get(ctx context.Context, userID, provider, tier string) (*checkoutIntent, error)
	Record(ctx context.Context, intent *checkoutIntent) error
}

// checkoutIntent mirrors store.CheckoutIntent. A local alias keeps the
// service decoupled from the store package's concrete type so this file
// remains importable from tests that supply only the interface.
type checkoutIntent struct {
	UserID      string
	Provider    string
	Tier        string
	CheckoutURL string
	ExpiresAt   time.Time
}

// CheckoutConfig is the static config the service needs. Loaded from env
// in main.go and passed in. Keeping it as a struct (not env reads inline)
// keeps the service unit-testable.
type CheckoutConfig struct {
	PaddleAPIBaseURL       string
	PaddleAPIKey           string
	PaddlePriceProBYOK     string
	PaddlePriceProManaged  string
	LSAPIBaseURL           string
	LSAPIKey               string
	LSStoreID              string
	LSVariantProBYOK       string
	LSVariantProManaged    string
	SuccessURL             string
	CancelURL              string
	HTTPTimeout            time.Duration
}

// NewCheckoutService validates config and returns a ready-to-use service.
//
// The idempotency cache is OPTIONAL. Production callers MUST supply one via
// WithIntentCache; the test harness can call NewCheckoutService alone and get
// a service that bypasses the cache (every call reaches the provider).
//
// The constructor builds:
//   - a hardened http.Transport with explicit per-host connection caps,
//     idle-conn timeout, TLS-handshake timeout, response-header timeout,
//     and expect-continue timeout so a slow-loris provider endpoint can
//     never hold dead TCP connections indefinitely;
//   - one circuit breaker per provider (paddle, lemonsqueezy) keyed by
//     the same constant the rest of the system uses. Steady-state cost
//     of the breaker is ~5ns per call; under a provider hard-down it
//     fast-fails after FailureThreshold consecutive 5xx / transport
//     errors, stops hammering the dead provider, and reopens via a
//     single half-open probe after the configured cooldown.
func NewCheckoutService(cfg CheckoutConfig, log zerolog.Logger) (*CheckoutService, error) {
	if cfg.HTTPTimeout <= 0 {
		cfg.HTTPTimeout = 10 * time.Second
	}
	if cfg.SuccessURL == "" || cfg.CancelURL == "" {
		return nil, errors.New("billing: checkout success/cancel URLs are required")
	}

	transport := &http.Transport{
		MaxConnsPerHost:        32,
		MaxIdleConnsPerHost:    16,
		IdleConnTimeout:        90 * time.Second,
		TLSHandshakeTimeout:    5 * time.Second,
		ExpectContinueTimeout:  1 * time.Second,
		ResponseHeaderTimeout:  5 * time.Second,
		ForceAttemptHTTP2:      true,
		DisableKeepAlives:      false,
	}

	return &CheckoutService{
		cfg: cfg,
		client: &http.Client{
			Timeout:   cfg.HTTPTimeout,
			Transport: transport,
		},
		log:       log,
		intentTTL: 5 * time.Minute,
		breakers: map[string]*Breaker{
			"paddle":       NewBreaker(BreakerConfig{Name: "paddle"}),
			"lemonsqueezy": NewBreaker(BreakerConfig{Name: "lemonsqueezy"}),
		},
	}, nil
}

// SetBreakerObserver attaches a state-change observer to every provider
// breaker. Wired in main.go against the Prometheus metric pack so the
// service package does not import the server package (no cycle).
func (c *CheckoutService) SetBreakerObserver(obs BreakerObserver) {
	for name, br := range c.breakers {
		cfg := BreakerConfig{
			Name:                 name,
			FailureThreshold:     5,
			OpenCooldown:         30 * time.Second,
			HalfOpenProbeTimeout: 30 * time.Second,
			Observer:             obs,
		}
		// Rebuild the breaker with the observer attached. Safe because
		// SetBreakerObserver is called once at startup, before any traffic.
		c.breakers[name] = NewBreaker(cfg)
		_ = br // preserved for clarity; the old breaker has no state yet.
	}
}

// breakerFor returns the per-provider breaker. Unknown providers fall
// through to a nil breaker; the helper below treats nil as 'always allow'
// so a future provider added without a breaker entry still works.
func (c *CheckoutService) breakerFor(provider string) *Breaker {
	return c.breakers[strings.ToLower(strings.TrimSpace(provider))]
}

// WithIntentCache attaches the idempotency cache. Wired in main.go
// against *store.CheckoutIntentStore. The store is wrapped by a small
// in-place adapter so this package does not import the store package.
func (c *CheckoutService) WithIntentCache(
	get func(ctx context.Context, userID, provider, tier string) (userID2, providerOut, tierOut, url string, expiresAt time.Time, ok bool, err error),
	record func(ctx context.Context, userID, provider, tier, url string, expiresAt time.Time) error,
) {
	c.intents = adapterIntentStore{getFn: get, recordFn: record}
}

// SetIntentTTL overrides the default cache window. Optional; bounds 1–60 min.
func (c *CheckoutService) SetIntentTTL(ttl time.Duration) {
	if ttl < time.Minute {
		ttl = time.Minute
	}
	if ttl > 60*time.Minute {
		ttl = 60 * time.Minute
	}
	c.intentTTL = ttl
}

// adapterIntentStore lifts caller-supplied closures (over the concrete
// *store.CheckoutIntentStore) into the interface this package expects.
// Keeps the store import out of the service package.
type adapterIntentStore struct {
	getFn func(ctx context.Context, userID, provider, tier string) (string, string, string, string, time.Time, bool, error)
	recordFn func(ctx context.Context, userID, provider, tier, url string, expiresAt time.Time) error
}

func (a adapterIntentStore) Get(ctx context.Context, userID, provider, tier string) (*checkoutIntent, error) {
	u, p, t, url, exp, ok, err := a.getFn(ctx, userID, provider, tier)
	if err != nil {
		return nil, err
	}
	if !ok {
		return nil, errors.New("billing: checkout intent cache miss")
	}
	return &checkoutIntent{UserID: u, Provider: p, Tier: t, CheckoutURL: url, ExpiresAt: exp}, nil
}

func (a adapterIntentStore) Record(ctx context.Context, intent *checkoutIntent) error {
	return a.recordFn(ctx, intent.UserID, intent.Provider, intent.Tier, intent.CheckoutURL, intent.ExpiresAt)
}

// CreateCheckout dispatches by provider and returns the redirect URL.
//
// The idempotency cache (when configured) short-circuits when a fresh
// (user, provider, tier) cache entry exists, so a double-click on the
// SPA's Upgrade button always returns the SAME checkout URL within the
// TTL window. This is the platform's primary defence against
// double-charge — the provider's own idempotency catches the rest.
func (c *CheckoutService) CreateCheckout(ctx context.Context, req CheckoutRequest) (*CheckoutResponse, error) {
	if !events.IsValidTier(req.Tier) || req.Tier == events.TierFree {
		return nil, ErrInvalidTier
	}
	if req.UserID == "" {
		return nil, errors.New("billing: user_id is required")
	}

	provider := strings.ToLower(strings.TrimSpace(req.Provider))
	tierStr := string(req.Tier)

	// 1. Cache hit: return the existing URL. Provider is never called.
	//    The cache is checked BEFORE the circuit breaker on purpose:
	//    a hard-down provider must not invalidate a still-fresh
	//    checkout URL that a customer is about to complete.
	if c.intents != nil {
		if cached, err := c.intents.Get(ctx, req.UserID, provider, tierStr); err == nil && cached != nil && cached.CheckoutURL != "" {
			return &CheckoutResponse{CheckoutURL: cached.CheckoutURL}, nil
		}
	}

	// 2. Cache miss: dispatch to the provider.
	var (
		resp *CheckoutResponse
		err  error
	)
	switch provider {
	case "paddle":
		resp, err = c.createPaddleCheckout(ctx, req)
	case "lemonsqueezy":
		resp, err = c.createLemonSqueezyCheckout(ctx, req)
	default:
		return nil, ErrInvalidProvider
	}
	if err != nil {
		return nil, err
	}

	// 3. Best-effort cache write. Failure here is non-fatal: the
	//    customer's checkout still works; we just lose the
	//    double-click defence for this one window. Provider-side
	//    idempotency is the second layer.
	if c.intents != nil && resp != nil && resp.CheckoutURL != "" {
		_ = c.intents.Record(ctx, &checkoutIntent{
			UserID:      req.UserID,
			Provider:    provider,
			Tier:        tierStr,
			CheckoutURL: resp.CheckoutURL,
			ExpiresAt:   time.Now().UTC().Add(c.intentTTL),
		})
	}
	return resp, nil
}

// ---------------------------------------------------------------------------
// Paddle: POST /transactions
// Docs: https://developer.paddle.com/api-reference/transactions/create-transaction
// ---------------------------------------------------------------------------

func (c *CheckoutService) paddlePriceID(tier events.Tier) string {
	switch tier {
	case events.TierProBYOK:
		return c.cfg.PaddlePriceProBYOK
	case events.TierProManaged:
		return c.cfg.PaddlePriceProManaged
	}
	return ""
}

type paddleTxRequest struct {
	Items       []paddleTxItem    `json:"items"`
	CustomerEmail string          `json:"customer_email,omitempty"`
	CustomData  map[string]string `json:"custom_data"`
	Checkout    paddleTxCheckout  `json:"checkout"`
}

type paddleTxItem struct {
	PriceID  string `json:"price_id"`
	Quantity int    `json:"quantity"`
}

type paddleTxCheckout struct {
	URL string `json:"url"`
}

type paddleTxResponse struct {
	Data struct {
		ID       string `json:"id"`
		Checkout struct {
			URL string `json:"url"`
		} `json:"checkout"`
	} `json:"data"`
}

func (c *CheckoutService) createPaddleCheckout(ctx context.Context, req CheckoutRequest) (*CheckoutResponse, error) {
	priceID := c.paddlePriceID(req.Tier)
	if priceID == "" {
		return nil, fmt.Errorf("%w: paddle %s", ErrUnconfiguredProduct, req.Tier)
	}
	if c.cfg.PaddleAPIKey == "" {
		return nil, errors.New("billing: PADDLE_API_KEY is not configured")
	}

	payload := paddleTxRequest{
		Items: []paddleTxItem{{PriceID: priceID, Quantity: 1}},
		CustomerEmail: req.UserEmail,
		CustomData: map[string]string{
			"user_id": req.UserID,
			"tier":    string(req.Tier),
		},
		Checkout: paddleTxCheckout{URL: c.cfg.SuccessURL},
	}

	var resp paddleTxResponse
	endpoint := strings.TrimRight(c.cfg.PaddleAPIBaseURL, "/") + "/transactions"
	if err := c.postJSON(ctx, endpoint, c.cfg.PaddleAPIKey, payload, &resp); err != nil {
		return nil, err
	}
	if resp.Data.Checkout.URL == "" {
		return nil, fmt.Errorf("%w: paddle returned empty checkout url", ErrProviderAPI)
	}
	return &CheckoutResponse{CheckoutURL: resp.Data.Checkout.URL}, nil
}

// ---------------------------------------------------------------------------
// Lemon Squeezy: POST /v1/checkouts
// Docs: https://docs.lemonsqueezy.com/api/checkouts/create-checkout
// ---------------------------------------------------------------------------

func (c *CheckoutService) lsVariantID(tier events.Tier) string {
	switch tier {
	case events.TierProBYOK:
		return c.cfg.LSVariantProBYOK
	case events.TierProManaged:
		return c.cfg.LSVariantProManaged
	}
	return ""
}

type lsCheckoutRequest struct {
	Data lsCheckoutRequestData `json:"data"`
}

type lsCheckoutRequestData struct {
	Type          string                  `json:"type"`
	Attributes    lsCheckoutAttributes    `json:"attributes"`
	Relationships lsCheckoutRelationships `json:"relationships"`
}

type lsCheckoutAttributes struct {
	CheckoutData lsCheckoutData `json:"checkout_data"`
	ProductOptions lsProductOptions `json:"product_options"`
}

type lsCheckoutData struct {
	Email      string            `json:"email,omitempty"`
	Custom     map[string]string `json:"custom"`
}

type lsProductOptions struct {
	RedirectURL string `json:"redirect_url"`
}

type lsCheckoutRelationships struct {
	Store   lsRelationshipRef `json:"store"`
	Variant lsRelationshipRef `json:"variant"`
}

type lsRelationshipRef struct {
	Data lsRelationshipData `json:"data"`
}

type lsRelationshipData struct {
	Type string `json:"type"`
	ID   string `json:"id"`
}

type lsCheckoutResponse struct {
	Data struct {
		ID         string `json:"id"`
		Attributes struct {
			URL string `json:"url"`
		} `json:"attributes"`
	} `json:"data"`
}

func (c *CheckoutService) createLemonSqueezyCheckout(ctx context.Context, req CheckoutRequest) (*CheckoutResponse, error) {
	variantID := c.lsVariantID(req.Tier)
	if variantID == "" {
		return nil, fmt.Errorf("%w: lemonsqueezy %s", ErrUnconfiguredProduct, req.Tier)
	}
	if c.cfg.LSAPIKey == "" {
		return nil, errors.New("billing: LEMONSQUEEZY_API_KEY is not configured")
	}
	if c.cfg.LSStoreID == "" {
		return nil, errors.New("billing: LEMONSQUEEZY_STORE_ID is not configured")
	}

	payload := lsCheckoutRequest{
		Data: lsCheckoutRequestData{
			Type: "checkouts",
			Attributes: lsCheckoutAttributes{
				CheckoutData: lsCheckoutData{
					Email: req.UserEmail,
					Custom: map[string]string{
						"user_id": req.UserID,
						"tier":    string(req.Tier),
					},
				},
				ProductOptions: lsProductOptions{
					RedirectURL: c.cfg.SuccessURL,
				},
			},
			Relationships: lsCheckoutRelationships{
				Store:   lsRelationshipRef{Data: lsRelationshipData{Type: "stores", ID: c.cfg.LSStoreID}},
				Variant: lsRelationshipRef{Data: lsRelationshipData{Type: "variants", ID: variantID}},
			},
		},
	}

	var resp lsCheckoutResponse
	endpoint := strings.TrimRight(c.cfg.LSAPIBaseURL, "/") + "/v1/checkouts"
	if err := c.postJSONAPI(ctx, endpoint, c.cfg.LSAPIKey, payload, &resp); err != nil {
		return nil, err
	}
	if resp.Data.Attributes.URL == "" {
		return nil, fmt.Errorf("%w: lemonsqueezy returned empty checkout url", ErrProviderAPI)
	}
	return &CheckoutResponse{CheckoutURL: resp.Data.Attributes.URL}, nil
}

// ---------------------------------------------------------------------------
// HTTP plumbing
// ---------------------------------------------------------------------------

// postJSON posts a JSON body and decodes a JSON response. Used by Paddle.
func (c *CheckoutService) postJSON(ctx context.Context, endpoint, bearer string, body any, out any) error {
	return c.post(ctx, endpoint, bearer, "application/json", "application/json", body, out)
}

// postJSONAPI posts a {json:api} body and decodes a JSON response. Used by
// Lemon Squeezy, which requires the application/vnd.api+json Content-Type and
// Accept headers per JSON:API.
func (c *CheckoutService) postJSONAPI(ctx context.Context, endpoint, bearer string, body any, out any) error {
	return c.post(ctx, endpoint, bearer, "application/vnd.api+json", "application/vnd.api+json", body, out)
}

func (c *CheckoutService) post(
	ctx context.Context, endpoint, bearer, contentType, accept string, body any, out any,
) error {
	raw, err := json.Marshal(body)
	if err != nil {
		return fmt.Errorf("billing: marshal request: %w", err)
	}
	return attemptWithBackoff(ctx, func() (*http.Request, error) {
		req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(raw))
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", "Bearer "+bearer)
		req.Header.Set("Content-Type", contentType)
		req.Header.Set("Accept", accept)
		return req, nil
	}, c.client, c.breakerForEndpoint(endpoint), out)
}

// breakerForEndpoint returns the breaker matching the host of endpoint.
// Endpoints in the configured provider base URLs map 1:1 to a registered
// breaker. Unknown hosts return nil (i.e. always-allow), which is the
// correct behaviour for tests that point at example.invalid.
func (c *CheckoutService) breakerForEndpoint(endpoint string) *Breaker {
	switch {
	case strings.HasPrefix(endpoint, strings.TrimRight(c.cfg.PaddleAPIBaseURL, "/")):
		return c.breakerFor("paddle")
	case strings.HasPrefix(endpoint, strings.TrimRight(c.cfg.LSAPIBaseURL, "/")):
		return c.breakerFor("lemonsqueezy")
	}
	return nil
}

// retryBackoffs is the sleep schedule between attempts. Three total
// attempts (1 initial + 2 retries) is the right balance for a synchronous
// user-facing call: long enough to ride out a single 5xx blip on the
// provider, short enough that the gateway's 20s timeout still bounds the
// total wall-clock. Jitter is added on top of each delay below.
var retryBackoffs = []time.Duration{
	200 * time.Millisecond,
	500 * time.Millisecond,
}

// attemptWithBackoff retries a request up to len(retryBackoffs)+1 times.
// Returns on:
//   - 2xx: decodes into out (when non-nil), reports Success to the
//     breaker, returns nil.
//   - 4xx (permanent caller error): returns ErrProviderAPI wrapped with
//     the response body, NO breaker accounting (a malformed user
//     request must not trip a shared breaker).
//   - 5xx or transport error: sleeps with jittered backoff, reports
//     Failure to the breaker on each retried attempt, retries up to
//     the schedule limit. Abort immediately on ctx cancellation.
//   - Breaker open: short-circuits with ErrProviderAPI wrapping
//     ErrBreakerOpen on attempt 0, no HTTP call is made.
//
// The buildReq closure rebuilds the *http.Request on every attempt so
// the body reader is fresh — reusing a consumed bytes.Reader would yield
// an empty body on retry.
func attemptWithBackoff(
	ctx context.Context,
	buildReq func() (*http.Request, error),
	client *http.Client,
	breaker *Breaker,
	out any,
) error {
	var lastErr error
	for attempt := 0; attempt <= len(retryBackoffs); attempt++ {
		if attempt > 0 {
			delay := jitter(retryBackoffs[attempt-1], 50*time.Millisecond)
			select {
			case <-ctx.Done():
				return fmt.Errorf("%w: context cancelled before retry: %v", ErrProviderAPI, ctx.Err())
			case <-time.After(delay):
			}
		}

		if breaker != nil {
			if err := breaker.Allow(ctx); err != nil {
				// Fast-fail. Do NOT continue the retry loop; the breaker is
				// signalling 'do not hammer the provider'. The 'lastErr'
				// value (if any from a previous attempt) is preserved and
				// surfaces as the response so operators see the underlying
				// failure that tripped the breaker, not just 'breaker open'.
				if lastErr != nil {
					return lastErr
				}
				return fmt.Errorf("%w: %v", ErrProviderAPI, err)
			}
		}

		req, err := buildReq()
		if err != nil {
			return fmt.Errorf("billing: build request: %w", err)
		}

		resp, err := client.Do(req)
		if err != nil {
			if breaker != nil {
				breaker.Failure()
			}
			lastErr = fmt.Errorf("%w: %v", ErrProviderAPI, err)
			continue
		}
		respBody, _ := io.ReadAll(resp.Body)
		_ = resp.Body.Close()

		if resp.StatusCode >= 200 && resp.StatusCode < 300 {
			if breaker != nil {
				breaker.Success()
			}
			if out == nil {
				return nil
			}
			if err := json.Unmarshal(respBody, out); err != nil {
				return fmt.Errorf("billing: decode response: %w", err)
			}
			return nil
		}

		if resp.StatusCode >= 500 {
			if breaker != nil {
				breaker.Failure()
			}
			lastErr = fmt.Errorf("%w: status=%d body=%s", ErrProviderAPI, resp.StatusCode, truncate(string(respBody), 256))
			continue
		}

		// 4xx — permanent caller error. Do NOT trip the breaker:
		// a malformed user input must not impact other users.
		return fmt.Errorf("%w: status=%d body=%s", ErrProviderAPI, resp.StatusCode, truncate(string(respBody), 256))
	}
	return lastErr
}

// jitter returns base + a uniform random offset in [-spread, +spread].
// Uses crypto/rand so concurrent goroutines do not synchronise their
// retry waves under load. Falls back to base on entropy failure (which
// crypto/rand documents as effectively never happening on supported
// platforms).
func jitter(base, spread time.Duration) time.Duration {
	if spread <= 0 {
		return base
	}
	var buf [8]byte
	if _, err := cryptoRand.Read(buf[:]); err != nil {
		return base
	}
	n := binary.LittleEndian.Uint64(buf[:])
	offset := time.Duration(n%uint64(2*spread)) - spread // #nosec G115 -- modulo keeps result within [0,2*spread) which fits in time.Duration (int64).
	result := base + offset
	if result < 0 {
		return 0
	}
	return result
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}

// ---------------------------------------------------------------------------
// Customer portal
//   - Paddle: POST /customers/{id}/portal-sessions (Paddle Billing v1)
//   - Lemon Squeezy: GET /v1/customers/{id}, read attributes.urls.customer_portal
//
// The portal URL is one-shot per customer and short-lived (Paddle returns
// a session that expires within minutes). We never cache it; every call
// hits the provider so the URL is always fresh.
// ---------------------------------------------------------------------------

type paddlePortalResponse struct {
	Data struct {
		ID   string `json:"id"`
		URLs struct {
			General string `json:"general"`
		} `json:"urls"`
	} `json:"data"`
}

type lsCustomerResponse struct {
	Data struct {
		ID         string `json:"id"`
		Attributes struct {
			URLs struct {
				CustomerPortal string `json:"customer_portal"`
			} `json:"urls"`
		} `json:"attributes"`
	} `json:"data"`
}

// CreatePortalSession resolves a one-shot customer-portal URL for the
// supplied (provider, customer_id). Provider API keys live exclusively
// inside this service.
func (c *CheckoutService) CreatePortalSession(
	ctx context.Context, req PortalRequest,
) (*PortalResponse, error) {
	provider := strings.ToLower(strings.TrimSpace(req.Provider))
	customerID := strings.TrimSpace(req.ProviderCustomerID)
	if customerID == "" {
		return nil, fmt.Errorf("%w: provider_customer_id is required", ErrPortalNotSupported)
	}

	switch provider {
	case "paddle":
		return c.createPaddlePortal(ctx, customerID)
	case "lemonsqueezy":
		return c.createLemonSqueezyPortal(ctx, customerID)
	default:
		return nil, ErrInvalidProvider
	}
}

func (c *CheckoutService) createPaddlePortal(ctx context.Context, customerID string) (*PortalResponse, error) {
	if c.cfg.PaddleAPIKey == "" {
		return nil, errors.New("billing: PADDLE_API_KEY is not configured")
	}

	endpoint := strings.TrimRight(c.cfg.PaddleAPIBaseURL, "/") + "/customers/" + customerID + "/portal-sessions"

	var resp paddlePortalResponse
	// Paddle's portal-sessions endpoint accepts an empty JSON body. We
	// send {} explicitly so the request is well-formed regardless of
	// any future server-side validation that rejects zero-byte payloads.
	if err := c.postJSON(ctx, endpoint, c.cfg.PaddleAPIKey, struct{}{}, &resp); err != nil {
		return nil, err
	}
	if resp.Data.URLs.General == "" {
		return nil, fmt.Errorf("%w: paddle returned empty portal url", ErrPortalNotSupported)
	}
	return &PortalResponse{PortalURL: resp.Data.URLs.General}, nil
}

func (c *CheckoutService) createLemonSqueezyPortal(ctx context.Context, customerID string) (*PortalResponse, error) {
	if c.cfg.LSAPIKey == "" {
		return nil, errors.New("billing: LEMONSQUEEZY_API_KEY is not configured")
	}
	endpoint := strings.TrimRight(c.cfg.LSAPIBaseURL, "/") + "/v1/customers/" + customerID

	var resp lsCustomerResponse
	if err := c.getJSONAPI(ctx, endpoint, c.cfg.LSAPIKey, &resp); err != nil {
		return nil, err
	}
	if resp.Data.Attributes.URLs.CustomerPortal == "" {
		return nil, fmt.Errorf("%w: lemonsqueezy customer has no portal url", ErrPortalNotSupported)
	}
	return &PortalResponse{PortalURL: resp.Data.Attributes.URLs.CustomerPortal}, nil
}

// getJSONAPI performs a GET against a JSON:API endpoint and decodes the
// response into out. Shares the same retry + breaker + bounded error
// policy as post().
func (c *CheckoutService) getJSONAPI(
	ctx context.Context, endpoint, bearer string, out any,
) error {
	return attemptWithBackoff(ctx, func() (*http.Request, error) {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", "Bearer "+bearer)
		req.Header.Set("Accept", "application/vnd.api+json")
		return req, nil
	}, c.client, c.breakerForEndpoint(endpoint), out)
}
