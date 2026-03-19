package mt5

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/management/internal/broker"
	"github.com/flamegreat/etradie/src/management/internal/observability"
)

// Bridge implements broker.Port for Module C by calling the Python MT5
// bridge service over HTTP. This is the same FastAPI service used by
// Module B — Module C simply uses the position-management endpoints
// (modify, partial close, full close) rather than order placement.
type Bridge struct {
	baseURL    string
	httpClient *http.Client
	log        zerolog.Logger
}

// NewBridge creates an MT5 bridge client for Module C.
func NewBridge(baseURL string, timeoutMs int) *Bridge {
	return &Bridge{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: time.Duration(timeoutMs) * time.Millisecond,
		},
		log: observability.Logger("mt5_bridge"),
	}
}

func (b *Bridge) GetTickPrice(ctx context.Context, symbol string) (*broker.TickPrice, error) {
	var resp struct {
		Bid  float64 `json:"bid"`
		Ask  float64 `json:"ask"`
		Time int64   `json:"time"`
	}

	if err := b.get(ctx, fmt.Sprintf("/internal/broker/tick_price?symbol=%s", symbol), &resp); err != nil {
		return nil, fmt.Errorf("get tick price for %s: %w", symbol, err)
	}

	return &broker.TickPrice{
		Bid: resp.Bid,
		Ask: resp.Ask,
	}, nil
}

func (b *Bridge) GetPosition(ctx context.Context, ticket string) (*broker.PositionInfo, error) {
	var resp struct {
		Symbol       string  `json:"symbol"`
		Type         int     `json:"type"` // 0=BUY, 1=SELL
		PriceOpen    float64 `json:"price_open"`
		PriceCurrent float64 `json:"price_current"`
		SL           float64 `json:"sl"`
		TP           float64 `json:"tp"`
		Volume       float64 `json:"volume"`
		Profit       float64 `json:"profit"`
		Ticket       int64   `json:"ticket"`
	}

	if err := b.get(ctx, fmt.Sprintf("/internal/broker/position?ticket=%s", ticket), &resp); err != nil {
		return nil, fmt.Errorf("get position %s: %w", ticket, err)
	}

	direction := "BUY"
	if resp.Type == 1 {
		direction = "SELL"
	}

	return &broker.PositionInfo{
		Symbol:       resp.Symbol,
		Direction:    direction,
		EntryPrice:   resp.PriceOpen,
		CurrentPrice: resp.PriceCurrent,
		StopLoss:     resp.SL,
		TakeProfit:   resp.TP,
		Volume:       resp.Volume,
		Profit:       resp.Profit,
		Ticket:       fmt.Sprintf("%d", resp.Ticket),
	}, nil
}

func (b *Bridge) ModifyPosition(ctx context.Context, ticket string, newSL, newTP float64) error {
	payload := map[string]interface{}{
		"ticket":    ticket,
		"stop_loss": newSL,
		"take_profit": newTP,
	}

	var resp struct {
		Success bool   `json:"success"`
		Error   string `json:"error"`
	}

	if err := b.post(ctx, "/internal/broker/modify_position", payload, &resp); err != nil {
		return fmt.Errorf("modify position %s: %w", ticket, err)
	}

	if !resp.Success {
		return fmt.Errorf("modify position %s: %s", ticket, resp.Error)
	}

	b.log.Info().
		Str("ticket", ticket).
		Float64("new_sl", newSL).
		Float64("new_tp", newTP).
		Msg("position_modified")

	return nil
}

func (b *Bridge) ClosePartial(ctx context.Context, ticket string, volumeToClose float64) error {
	payload := map[string]interface{}{
		"ticket": ticket,
		"volume": volumeToClose,
	}

	var resp struct {
		Success bool    `json:"success"`
		Price   float64 `json:"close_price"`
		Error   string  `json:"error"`
	}

	if err := b.post(ctx, "/internal/broker/close_partial", payload, &resp); err != nil {
		return fmt.Errorf("partial close position %s (%.2f lots): %w", ticket, volumeToClose, err)
	}

	if !resp.Success {
		return fmt.Errorf("partial close position %s: %s", ticket, resp.Error)
	}

	b.log.Info().
		Str("ticket", ticket).
		Float64("volume_closed", volumeToClose).
		Float64("close_price", resp.Price).
		Msg("partial_close_executed")

	return nil
}

func (b *Bridge) ClosePosition(ctx context.Context, ticket string) error {
	payload := map[string]interface{}{
		"ticket": ticket,
	}

	var resp struct {
		Success bool    `json:"success"`
		Price   float64 `json:"close_price"`
		Error   string  `json:"error"`
	}

	if err := b.post(ctx, "/internal/broker/close_position", payload, &resp); err != nil {
		return fmt.Errorf("close position %s: %w", ticket, err)
	}

	if !resp.Success {
		return fmt.Errorf("close position %s: %s", ticket, resp.Error)
	}

	b.log.Info().
		Str("ticket", ticket).
		Float64("close_price", resp.Price).
		Msg("position_closed")

	return nil
}

// get performs an HTTP GET and decodes the JSON response.
func (b *Bridge) get(ctx context.Context, path string, dest interface{}) error {
	start := time.Now()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, b.baseURL+path, nil)
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}

	resp, err := b.httpClient.Do(req)
	if err != nil {
		observability.BrokerCallTotal.WithLabelValues(path, "error").Inc()
		return fmt.Errorf("http get %s: %w", path, err)
	}
	defer resp.Body.Close()

	elapsed := time.Since(start).Seconds()
	observability.BrokerCallDuration.WithLabelValues(path).Observe(elapsed)

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		observability.BrokerCallTotal.WithLabelValues(path, "http_error").Inc()
		return fmt.Errorf("http get %s: status %d: %s", path, resp.StatusCode, string(body))
	}

	observability.BrokerCallTotal.WithLabelValues(path, "success").Inc()

	if err := json.NewDecoder(resp.Body).Decode(dest); err != nil {
		return fmt.Errorf("decode response from %s: %w", path, err)
	}

	return nil
}

// post performs an HTTP POST with JSON body and decodes the response.
func (b *Bridge) post(ctx context.Context, path string, payload interface{}, dest interface{}) error {
	start := time.Now()

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal payload: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, b.baseURL+path, strings.NewReader(string(body)))
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := b.httpClient.Do(req)
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
