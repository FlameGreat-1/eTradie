package service

import (
	"bytes"
	"context"
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
)

// CheckoutService creates one-shot checkout URLs against the configured
// payment providers. It owns the provider API keys; user-facing services
// never see them.
type CheckoutService struct {
	cfg    CheckoutConfig
	client *http.Client
	log    zerolog.Logger
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
func NewCheckoutService(cfg CheckoutConfig, log zerolog.Logger) (*CheckoutService, error) {
	if cfg.HTTPTimeout <= 0 {
		cfg.HTTPTimeout = 10 * time.Second
	}
	if cfg.SuccessURL == "" || cfg.CancelURL == "" {
		return nil, errors.New("billing: checkout success/cancel URLs are required")
	}
	return &CheckoutService{
		cfg:    cfg,
		client: &http.Client{Timeout: cfg.HTTPTimeout},
		log:    log,
	}, nil
}

// CreateCheckout dispatches by provider and returns the redirect URL.
func (c *CheckoutService) CreateCheckout(ctx context.Context, req CheckoutRequest) (*CheckoutResponse, error) {
	if !events.IsValidTier(req.Tier) || req.Tier == events.TierFree {
		return nil, ErrInvalidTier
	}
	if req.UserID == "" {
		return nil, errors.New("billing: user_id is required")
	}

	switch strings.ToLower(strings.TrimSpace(req.Provider)) {
	case "paddle":
		return c.createPaddleCheckout(ctx, req)
	case "lemonsqueezy":
		return c.createLemonSqueezyCheckout(ctx, req)
	}
	return nil, ErrInvalidProvider
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

	// One retry on 5xx; 4xx is a permanent caller error and short-circuits.
	var lastErr error
	for attempt := 0; attempt < 2; attempt++ {
		req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(raw))
		if err != nil {
			return fmt.Errorf("billing: build request: %w", err)
		}
		req.Header.Set("Authorization", "Bearer "+bearer)
		req.Header.Set("Content-Type", contentType)
		req.Header.Set("Accept", accept)

		resp, err := c.client.Do(req)
		if err != nil {
			lastErr = fmt.Errorf("%w: %v", ErrProviderAPI, err)
			continue
		}
		respBody, _ := io.ReadAll(resp.Body)
		_ = resp.Body.Close()

		if resp.StatusCode >= 200 && resp.StatusCode < 300 {
			if out == nil {
				return nil
			}
			if err := json.Unmarshal(respBody, out); err != nil {
				return fmt.Errorf("billing: decode response: %w", err)
			}
			return nil
		}

		if resp.StatusCode >= 500 {
			lastErr = fmt.Errorf("%w: status=%d body=%s", ErrProviderAPI, resp.StatusCode, truncate(string(respBody), 256))
			continue
		}

		// 4xx — permanent. Don't retry.
		return fmt.Errorf("%w: status=%d body=%s", ErrProviderAPI, resp.StatusCode, truncate(string(respBody), 256))
	}
	return lastErr
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}
