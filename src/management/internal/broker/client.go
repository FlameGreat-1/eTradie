package broker

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
)

// Client handles broker execution actions (Modify, Close) over HTTP
// to the engine's /internal/broker/* surface. Authentication is by
// shared secret + X-User-Id, NOT the user JWT; see the engine's
// engine.shared.internal_auth.verify_internal_auth dependency.
type Client struct {
	baseURL        string
	httpClient     *http.Client
	internalSecret string
	log            zerolog.Logger
}

// Header names mirror the engine constants. Kept as local consts so a
// rename on either side is a one-place edit.
const (
	headerInternalAuth = "X-Internal-Auth"
	headerUserID       = "X-User-Id"
)

// NewClient creates an MT5 broker client. See NewMT5Broker for the
// internalSecret contract.
func NewClient(baseURL string, timeoutMs int, internalSecret string) *Client {
	c := &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: time.Duration(timeoutMs) * time.Millisecond,
		},
		internalSecret: strings.TrimSpace(internalSecret),
		log:            observability.Logger("broker_client"),
	}
	if c.internalSecret == "" {
		c.log.Warn().Msg(
			"engine_internal_secret_missing: every /internal/broker/* call " +
				"will be rejected with 401 by the engine. Set " +
				"MANAGEMENT_ENGINE_INTERNAL_SHARED_SECRET to match the engine.",
		)
	}
	return c
}

// stampInternalAuth attaches the X-Internal-Auth shared secret and
// X-User-Id headers required by the engine's internal-auth gate.
func (c *Client) stampInternalAuth(ctx context.Context, req *http.Request) error {
	if c.internalSecret == "" {
		return fmt.Errorf("engine internal secret is not configured")
	}
	req.Header.Set(headerInternalAuth, c.internalSecret)
	userID := strings.TrimSpace(auth.UserIDFromContext(ctx))
	if userID == "" {
		return fmt.Errorf("missing user id in request context")
	}
	req.Header.Set(headerUserID, userID)
	return nil
}

func (c *Client) ModifyPosition(ctx context.Context, ticket string, newSL, newTP float64) error {
	payload := map[string]interface{}{
		"ticket":      ticket,
		"stop_loss":   newSL,
		"take_profit": newTP,
	}

	var resp struct {
		Success bool   `json:"success"`
		Error   string `json:"error"`
	}

	if err := c.post(ctx, "/internal/broker/modify_position", payload, &resp); err != nil {
		return fmt.Errorf("modify position %s: %w", ticket, err)
	}

	if !resp.Success {
		return fmt.Errorf("modify position %s: %s", ticket, resp.Error)
	}

	c.log.Info().
		Str("ticket", ticket).
		Float64("new_sl", newSL).
		Float64("new_tp", newTP).
		Msg("position_modified")

	return nil
}

func (c *Client) ClosePartial(ctx context.Context, ticket string, volumeToClose float64) error {
	payload := map[string]interface{}{
		"ticket": ticket,
		"volume": volumeToClose,
	}

	var resp struct {
		Success bool    `json:"success"`
		Price   float64 `json:"close_price"`
		Error   string  `json:"error"`
	}

	if err := c.post(ctx, "/internal/broker/close_partial", payload, &resp); err != nil {
		return fmt.Errorf("partial close position %s (%.2f lots): %w", ticket, volumeToClose, err)
	}

	if !resp.Success {
		return fmt.Errorf("partial close position %s: %s", ticket, resp.Error)
	}

	c.log.Info().
		Str("ticket", ticket).
		Float64("volume_closed", volumeToClose).
		Float64("close_price", resp.Price).
		Msg("partial_close_executed")

	return nil
}

func (c *Client) ClosePosition(ctx context.Context, ticket string) error {
	payload := map[string]interface{}{
		"ticket": ticket,
	}

	var resp struct {
		Success bool    `json:"success"`
		Price   float64 `json:"close_price"`
		Error   string  `json:"error"`
	}

	if err := c.post(ctx, "/internal/broker/close_position", payload, &resp); err != nil {
		return fmt.Errorf("close position %s: %w", ticket, err)
	}

	if !resp.Success {
		return fmt.Errorf("close position %s: %s", ticket, resp.Error)
	}

	c.log.Info().
		Str("ticket", ticket).
		Float64("close_price", resp.Price).
		Msg("position_closed")

	return nil
}

// post performs an HTTP POST with JSON body and decodes the response.
func (c *Client) post(ctx context.Context, path string, payload interface{}, dest interface{}) error {
	start := time.Now()

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal payload: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+path, strings.NewReader(string(body)))
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	// The engine's /internal/* surface uses X-Internal-Auth + X-User-Id,
	// not the user JWT. Bearer token is intentionally not forwarded.
	if err := c.stampInternalAuth(ctx, req); err != nil {
		observability.BrokerCallTotal.WithLabelValues(path, "auth_error").Inc()
		return fmt.Errorf("http post %s: %w", path, err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		observability.BrokerCallTotal.WithLabelValues(path, "error").Inc()
		return fmt.Errorf("http post %s: %w", path, err)
	}
	defer resp.Body.Close()

	elapsed := time.Since(start).Seconds()
	observability.BrokerCallDuration.WithLabelValues(path).Observe(elapsed)

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		observability.BrokerCallTotal.WithLabelValues(path, "http_error").Inc()
		return fmt.Errorf("http post %s: status %d: %s", path, resp.StatusCode, string(respBody))
	}

	observability.BrokerCallTotal.WithLabelValues(path, "success").Inc()

	if err := json.NewDecoder(resp.Body).Decode(dest); err != nil {
		return fmt.Errorf("decode response from %s: %w", path, err)
	}

	return nil
}
