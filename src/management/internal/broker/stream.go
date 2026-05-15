package broker

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/gorilla/websocket"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
)

// Stream handles fetching live tick prices and position info from the
// MT5 bridge. Authentication contract matches Client (see NewClient).
type Stream struct {
	baseURL        string
	httpClient     *http.Client
	internalSecret string
	log            zerolog.Logger
}

// NewStream creates a stream connection. internalSecret must match
// the engine's ENGINE_INTERNAL_SHARED_SECRET (see NewMT5Broker).
func NewStream(baseURL string, timeoutMs int, internalSecret string) *Stream {
	s := &Stream{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: time.Duration(timeoutMs) * time.Millisecond,
		},
		internalSecret: strings.TrimSpace(internalSecret),
		log:            observability.Logger("broker_stream"),
	}
	// Warning logged once by Client; avoid double-logging here.
	return s
}

// stampInternalAuth attaches the X-Internal-Auth + X-User-Id headers
// required by the engine's internal-auth gate.
func (s *Stream) stampInternalAuth(ctx context.Context, req *http.Request) error {
	if s.internalSecret == "" {
		return fmt.Errorf("engine internal secret is not configured")
	}
	req.Header.Set(headerInternalAuth, s.internalSecret)
	userID := strings.TrimSpace(auth.UserIDFromContext(ctx))
	if userID == "" {
		return fmt.Errorf("missing user id in request context")
	}
	req.Header.Set(headerUserID, userID)
	return nil
}

func (s *Stream) GetTickPrice(ctx context.Context, symbol string) (*TickPrice, error) {
	var resp struct {
		Bid  float64 `json:"bid"`
		Ask  float64 `json:"ask"`
		Time int64   `json:"time"`
	}

	if err := s.get(ctx, fmt.Sprintf("/internal/broker/tick_price?symbol=%s", url.QueryEscape(symbol)), &resp); err != nil {
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

	if err := s.get(ctx, fmt.Sprintf("/internal/broker/position?ticket=%s", url.QueryEscape(ticket)), &resp); err != nil {
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

// GetPositions returns ALL open positions from the broker.
// Reuses the existing Python endpoint /internal/broker/positions.
func (s *Stream) GetPositions(ctx context.Context) ([]PositionInfo, error) {
	var rawPositions []struct {
		Symbol       string  `json:"symbol"`
		Type         int     `json:"type"` // 0=BUY, 1=SELL
		PriceOpen    float64 `json:"price_open"`
		PriceCurrent float64 `json:"price_current"`
		SL           float64 `json:"sl"`
		TP           float64 `json:"tp"`
		Volume       float64 `json:"volume"`
		Profit       float64 `json:"profit"`
		Commission   float64 `json:"commission"`
		Swap         float64 `json:"swap"`
		Ticket       int64   `json:"ticket"`
		Comment      string  `json:"comment"`
		TimeSetup    int64   `json:"time_setup"`
	}

	if err := s.get(ctx, "/internal/broker/positions", &rawPositions); err != nil {
		return nil, fmt.Errorf("get positions: %w", err)
	}

	positions := make([]PositionInfo, 0, len(rawPositions))
	for _, p := range rawPositions {
		direction := "BUY"
		if p.Type == 1 {
			direction = "SELL"
		}
		positions = append(positions, PositionInfo{
			Symbol:       p.Symbol,
			Direction:    direction,
			EntryPrice:   p.PriceOpen,
			CurrentPrice: p.PriceCurrent,
			StopLoss:     p.SL,
			TakeProfit:   p.TP,
			Volume:       p.Volume,
			Profit:       p.Profit,
			Commission:   p.Commission,
			Swap:         p.Swap,
			Ticket:       fmt.Sprintf("%d", p.Ticket),
		})
	}

	return positions, nil
}

// GetHistory returns historical closed deals from the broker.
func (s *Stream) GetHistory(ctx context.Context, days int) ([]HistoryDealInfo, error) {
	var rawHistory []struct {
		Ticket     string  `json:"ticket"`
		PositionID string  `json:"position_id"`
		Symbol     string  `json:"symbol"`
		Direction  string  `json:"direction"`
		Volume     float64 `json:"volume"`
		Price      float64 `json:"price"`
		Profit     float64 `json:"profit"`
		Commission float64 `json:"commission"`
		Swap       float64 `json:"swap"`
		Time       int64   `json:"time"`
		Comment    string  `json:"comment"`
	}

	path := fmt.Sprintf("/internal/broker/history?days=%d", days)
	if err := s.get(ctx, path, &rawHistory); err != nil {
		return nil, fmt.Errorf("get history: %w", err)
	}

	history := make([]HistoryDealInfo, 0, len(rawHistory))
	for _, h := range rawHistory {
		history = append(history, HistoryDealInfo{
			Ticket:     h.Ticket,
			PositionID: h.PositionID,
			Symbol:     h.Symbol,
			Direction:  h.Direction,
			Volume:     h.Volume,
			Price:      h.Price,
			Profit:     h.Profit,
			Commission: h.Commission,
			Swap:       h.Swap,
			Time:       h.Time,
			Comment:    h.Comment,
		})
	}

	return history, nil
}

// get performs an HTTP GET and decodes the JSON response.
func (s *Stream) get(ctx context.Context, path string, dest interface{}) error {
	start := time.Now()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, s.baseURL+path, nil)
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}

	// Engine /internal/* uses X-Internal-Auth + X-User-Id, not Bearer.
	if err := s.stampInternalAuth(ctx, req); err != nil {
		observability.BrokerCallTotal.WithLabelValues(path, "auth_error").Inc()
		return fmt.Errorf("http get %s: %w", path, err)
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

// StreamPositions connects to the Python bridge WebSocket and streams position updates.
func (s *Stream) StreamPositions(ctx context.Context, ch chan<- []PositionInfo) error {
	wsURL := strings.Replace(s.baseURL, "http://", "ws://", 1)
	wsURL = strings.Replace(wsURL, "https://", "wss://", 1)
	wsURL += "/api/broker/stream-positions"

	dialer := websocket.DefaultDialer
	conn, resp, err := dialer.DialContext(ctx, wsURL, nil)
	if err != nil {
		if resp != nil {
			body, _ := io.ReadAll(resp.Body)
			s.log.Error().Int("status", resp.StatusCode).Str("body", string(body)).Msg("websocket_dial_failed")
		}
		return fmt.Errorf("websocket dial: %w", err)
	}

	// Send init message with token
	rawToken := auth.RawTokenFromContext(ctx)
	if rawToken == "" {
		_ = conn.Close()
		return fmt.Errorf("no auth token in context for websocket init")
	}

	initMsg := map[string]string{
		"token": rawToken,
	}
	if err := conn.WriteJSON(initMsg); err != nil {
		_ = conn.Close()
		return fmt.Errorf("websocket write init: %w", err)
	}

	defer conn.Close()
	for {
		select {
		case <-ctx.Done():
			return nil
		default:
		}

		var rawPositions []struct {
			Symbol       string  `json:"symbol"`
			Type         int     `json:"type"` // 0=BUY, 1=SELL
			PriceOpen    float64 `json:"price_open"`
			PriceCurrent float64 `json:"price_current"`
			SL           float64 `json:"sl"`
			TP           float64 `json:"tp"`
			Volume       float64 `json:"volume"`
			Profit       float64 `json:"profit"`
			Commission   float64 `json:"commission"`
			Swap         float64 `json:"swap"`
			Ticket       int64   `json:"ticket"`
		}

		if err := conn.ReadJSON(&rawPositions); err != nil {
			// Handle normal close
			if websocket.IsCloseError(err, websocket.CloseNormalClosure, websocket.CloseGoingAway) {
				s.log.Info().Msg("position_stream_closed_normally")
				return nil
			}
			// Engine returns close code 4004 when the user has no active
			// broker connection configured. Return the sentinel error so
			// the caller can apply exponential backoff instead of
			// hammering the Engine every 5 seconds.
			if websocket.IsCloseError(err, 4004) {
				s.log.Info().Msg("position_stream_no_broker_configured")
				return ErrNoBrokerConfigured
			}
			s.log.Error().Err(err).Msg("position_stream_read_error")
			return err // Terminate loop on error. Parent will reconnect if desired.
		}

		positions := make([]PositionInfo, 0, len(rawPositions))
		for _, p := range rawPositions {
			direction := "BUY"
			if p.Type == 1 {
				direction = "SELL"
			}
			positions = append(positions, PositionInfo{
				Symbol:       p.Symbol,
				Direction:    direction,
				EntryPrice:   p.PriceOpen,
				CurrentPrice: p.PriceCurrent,
				StopLoss:     p.SL,
				TakeProfit:   p.TP,
				Volume:       p.Volume,
				Profit:       p.Profit,
				Commission:   p.Commission,
				Swap:         p.Swap,
				Ticket:       fmt.Sprintf("%d", p.Ticket),
			})
		}

		// Send to channel without blocking if reader is slow
		select {
		case ch <- positions:
		case <-ctx.Done():
			return nil
		case <-time.After(500 * time.Millisecond):
			s.log.Warn().Msg("position_stream_channel_full_dropping_frame")
		}
	}
}
