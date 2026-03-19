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

	"github.com/flamegreat/etradie/src/management/internal/observability"
)

// Client handles broker execution actions (Modify, Close) over HTTP to the MT5 bridge.
type Client struct {
	baseURL    string
	httpClient *http.Client
	log        zerolog.Logger
}

// NewClient creates an MT5 broker client.
func NewClient(baseURL string, timeoutMs int) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: time.Duration(timeoutMs) * time.Millisecond,
		},
		log: observability.Logger("broker_client"),
	}
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
