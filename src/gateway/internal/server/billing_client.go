package server

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
)

// InternalAuthHeader is the request header that carries the shared secret on
// calls to the billing microservice's /internal/* endpoints. Mirrors the
// constant defined in the billing service itself; we duplicate it here to
// avoid an import cycle (gateway should not depend on the billing server
// package).
const InternalAuthHeader = "X-Internal-Auth"

// BillingClient is a thin HTTP client over the billing microservice.
// Provider API keys live exclusively inside the billing service; the gateway
// only ever asks for a checkout URL.
type BillingClient struct {
	baseURL string
	secret  string
	http    *http.Client
}

// NewBillingClient validates the inputs and returns a ready-to-use client.
func NewBillingClient(baseURL, sharedSecret string, timeout time.Duration) (*BillingClient, error) {
	baseURL = strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if baseURL == "" {
		return nil, errors.New("billing client: base URL is required")
	}
	if len(sharedSecret) < 32 {
		return nil, errors.New("billing client: shared secret must be at least 32 characters")
	}
	if timeout <= 0 {
		timeout = 15 * time.Second
	}
	return &BillingClient{
		baseURL: baseURL,
		secret:  sharedSecret,
		http:    &http.Client{Timeout: timeout},
	}, nil
}

// CheckoutRequest mirrors the billing service request shape. Kept as a local
// type so the gateway never imports the billing service package.
type CheckoutRequest struct {
	Provider  string `json:"provider"`
	Tier      string `json:"tier"`
	UserID    string `json:"user_id"`
	UserEmail string `json:"user_email"`
}

// CheckoutResponse mirrors the billing service response shape.
type CheckoutResponse struct {
	CheckoutURL string `json:"checkout_url"`
}

// ErrUpstreamRejected is returned when the billing service replies with a 4xx.
// The gateway maps this to 400 (caller error) so the dashboard can show the
// reason inline. ErrUpstreamUnavailable maps to 502.
var (
	ErrUpstreamRejected    = errors.New("billing client: upstream rejected request")
	ErrUpstreamUnavailable = errors.New("billing client: upstream unavailable")
	// ErrUpstreamNotSupported maps the billing service's 501 response
	// (ErrPortalNotSupported) so the gateway handler can distinguish a
	// 'provider does not expose a portal URL for this customer' result
	// from a generic 5xx infrastructure failure. The dashboard surfaces
	// this as a clean 'portal unavailable' toast instead of a redirect
	// to an empty URL.
	ErrUpstreamNotSupported = errors.New("billing client: feature not supported by upstream provider")
)

// PortalRequest mirrors the billing service's PortalRequest shape.
type PortalRequest struct {
	Provider           string `json:"provider"`
	ProviderCustomerID string `json:"provider_customer_id"`
	UserID             string `json:"user_id"`
}

// PortalResponse mirrors the billing service's PortalResponse shape.
type PortalResponse struct {
	PortalURL string `json:"portal_url"`
}

// CreatePortalSession invokes /internal/portal on the billing service.
// Returns:
//   - ErrUpstreamRejected on any 4xx response;
//   - ErrUpstreamNotSupported when the billing service returns 501
//     (the customer has no portal URL on the provider side);
//   - ErrUpstreamUnavailable on transport failures or 5xx.
func (c *BillingClient) CreatePortalSession(ctx context.Context, req PortalRequest) (*PortalResponse, error) {
	raw, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("billing client: marshal: %w", err)
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/internal/portal", bytes.NewReader(raw))
	if err != nil {
		return nil, fmt.Errorf("billing client: build request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "application/json")
	httpReq.Header.Set(InternalAuthHeader, c.secret)

	resp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrUpstreamUnavailable, err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		var out PortalResponse
		if err := json.Unmarshal(body, &out); err != nil {
			return nil, fmt.Errorf("billing client: decode response: %w", err)
		}
		if out.PortalURL == "" {
			return nil, fmt.Errorf("%w: empty portal url", ErrUpstreamUnavailable)
		}
		return &out, nil
	}

	if resp.StatusCode == http.StatusNotImplemented {
		return nil, fmt.Errorf("%w: status=%d body=%s", ErrUpstreamNotSupported, resp.StatusCode, truncateForLog(string(body)))
	}
	if resp.StatusCode >= 400 && resp.StatusCode < 500 {
		return nil, fmt.Errorf("%w: status=%d body=%s", ErrUpstreamRejected, resp.StatusCode, truncateForLog(string(body)))
	}
	return nil, fmt.Errorf("%w: status=%d body=%s", ErrUpstreamUnavailable, resp.StatusCode, truncateForLog(string(body)))
}

// CreateCheckout invokes /internal/checkout. Returns ErrUpstreamRejected on
// any 4xx response (the message body is included in the error for logging),
// ErrUpstreamUnavailable on transport failures or 5xx.
func (c *BillingClient) CreateCheckout(ctx context.Context, req CheckoutRequest) (*CheckoutResponse, error) {
	raw, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("billing client: marshal: %w", err)
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/internal/checkout", bytes.NewReader(raw))
	if err != nil {
		return nil, fmt.Errorf("billing client: build request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "application/json")
	httpReq.Header.Set(InternalAuthHeader, c.secret)

	resp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", ErrUpstreamUnavailable, err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		var out CheckoutResponse
		if err := json.Unmarshal(body, &out); err != nil {
			return nil, fmt.Errorf("billing client: decode response: %w", err)
		}
		if out.CheckoutURL == "" {
			return nil, fmt.Errorf("%w: empty checkout url", ErrUpstreamUnavailable)
		}
		return &out, nil
	}

	if resp.StatusCode >= 400 && resp.StatusCode < 500 {
		return nil, fmt.Errorf("%w: status=%d body=%s", ErrUpstreamRejected, resp.StatusCode, truncateForLog(string(body)))
	}
	return nil, fmt.Errorf("%w: status=%d body=%s", ErrUpstreamUnavailable, resp.StatusCode, truncateForLog(string(body)))
}

func truncateForLog(s string) string {
	const max = 256
	if len(s) <= max {
		return s
	}
	return s[:max] + "…"
}
