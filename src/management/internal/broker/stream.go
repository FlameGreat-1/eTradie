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

	"github.com/flamegreat-1/etradie/src/management/internal/observability"
)

// Stream handles fetching live tick prices and position info from the MT5 bridge.
type Stream struct {
	baseURL    string
	httpClient *http.Client
	log        zerolog.Logger
}

// NewStream creates a stream connection.
func NewStream(baseURL string, timeoutMs int) *Stream {
	return &Stream{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: time.Duration(timeoutMs) * time.Millisecond,
		},
		log: observability.Logger("broker_stream"),
	}
}

func (s *Stream) GetTickPrice(ctx context.Context, symbol string) (*TickPrice, error) {
	var resp struct {
		Bid  float64 `json:"bid"`
		Ask  float64 `json:"ask"`
		Time int64   `json:"time"`
	}

	if err := s.get(ctx, fmt.Sprintf("/internal/broker/tick_price?symbol=%s", symbol), &resp); err != nil {
		return nil, fmt.Errorf("get tick price for %s: %w", symbol, err)
	}

	return &TickPrice{
		Bid: resp.Bid,
		Ask: resp.Ask,
	}, nil
}

func (s *Stream) GetPosition(ctx context.Context, ticket string) (*PositionInfo, error) {
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

	if err := s.get(ctx, fmt.Sprintf("/internal/broker/position?ticket=%s", ticket), &resp); err != nil {
		return nil, fmt.Errorf("get position %s: %w", ticket, err)
	}

	direction := "BUY"
	if resp.Type == 1 {
		direction = "SELL"
	}

	return &PositionInfo{
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

// get performs an HTTP GET and decodes the JSON response.
func (s *Stream) get(ctx context.Context, path string, dest interface{}) error {
	start := time.Now()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, s.baseURL+path, nil)
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}

	resp, err := s.httpClient.Do(req)
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
