package broker

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net/http"
	"net/url"
	"sort"
	"strings"
	"time"

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

// WatchPositions implements Port.WatchPositions. See the interface
// doc for the contract; this implementation polls GetPositions at
// the supplied interval, emits only structurally-changed frames,
// and coalesces unconsumed snapshots so the consumer always sees
// the latest broker state.
//
// The poller uses a small minimum interval (250ms) to protect the
// engine from a misconfigured caller passing 0; the maximum is
// unbounded because long intervals are a valid operator choice.
func (s *Stream) WatchPositions(
	ctx context.Context,
	interval time.Duration,
) (<-chan []PositionInfo, <-chan error) {
	// Buffer of 1 with coalescing on send (see emit() below). Consumer
	// always sees the latest snapshot, never a backlog.
	positions := make(chan []PositionInfo, 1)
	errors := make(chan error, 1)

	if interval < 250*time.Millisecond {
		interval = 250 * time.Millisecond
	}

	go func() {
		defer close(positions)
		defer close(errors)

		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		var lastHash [32]byte
		var haveLast bool

		pollOnce := func() bool {
			snapshot, err := s.GetPositions(ctx)
			if err != nil {
				// The engine returns 503 with a body containing
				// "No broker connection configured" when the user
				// has not set up a broker. Map that to the public
				// sentinel so the reconciler can back off.
				if isNoBrokerConfiguredError(err) {
					s.emitError(ctx, errors, ErrNoBrokerConfigured)
					return false
				}
				// Transient broker / network failure. Log the warning and keep the poller loop running.
				// Returning true keeps the goroutine alive so the next tick will poll again.
				s.log.Warn().Err(err).Msg("watch_positions_poll_failed_transient")
				return true
			}

			h := hashPositions(snapshot)
			if haveLast && h == lastHash {
				// No structural change; skip emission. The
				// consumer's existing snapshot is still valid.
				return true
			}
			lastHash = h
			haveLast = true
			s.emitPositions(ctx, positions, snapshot)
			return true
		}

		// Prime the watcher: do one immediate poll so the consumer
		// receives the current state without waiting a full interval.
		// If that poll fails with a fatal error the loop returns and
		// the consumer's range over `positions` exits.
		if !pollOnce() {
			return
		}

		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				if !pollOnce() {
					return
				}
			}
		}
	}()

	return positions, errors
}

// emitPositions performs a coalescing send on the position channel.
// If the consumer has not yet read the previous snapshot, that
// stale snapshot is discarded and replaced by the newer one.
//
// The channel parameter is intentionally bidirectional rather than
// send-only so the helper can drain a stale snapshot from the buffer
// before retrying the send. The caller (WatchPositions) constructs
// the channel bidirectionally and narrows it to <-chan []PositionInfo
// only in its public return value, so widening the parameter here
// does not loosen the external API surface.
func (s *Stream) emitPositions(ctx context.Context, ch chan []PositionInfo, snapshot []PositionInfo) {
	for {
		select {
		case ch <- snapshot:
			return
		case <-ctx.Done():
			return
		default:
			// Channel full: drain one stale snapshot and retry.
			select {
			case <-ch:
			default:
			}
		}
	}
}

// emitError sends on the error channel without blocking. The channel
// is size-1 by design: the first fatal error wins and subsequent
// poll attempts are short-circuited by the caller anyway.
func (s *Stream) emitError(ctx context.Context, ch chan<- error, err error) {
	select {
	case ch <- err:
	case <-ctx.Done():
	default:
		// Buffer already has an error; the first one wins.
	}
}

// isNoBrokerConfiguredError detects the engine's standard 503 body
// shape that means "this user has not configured a broker yet".
// The engine writes this from `_resolve_user_broker` in helpers.py.
func isNoBrokerConfiguredError(err error) bool {
	if err == nil {
		return false
	}
	msg := err.Error()
	return strings.Contains(msg, "No broker connection configured")
}

// hashPositions computes a stable structural hash of the position
// list. Positions are sorted by ticket before hashing so a list-order
// change at the broker side does NOT trigger a spurious diff. The
// hash covers every field the reconciler reacts to (SL, TP, volume,
// commission, swap, current price) plus ticket and symbol.
//
// CurrentPrice is included in the hash so price-only movements
// produce frames the reconciler can use to update Swap/Commission
// continuously for the dashboard. If price-only updates ever become
// too noisy in production we can drop CurrentPrice from the hash
// and emit a separate price-tick channel; today the rate is bounded
// by the watcher interval and is not a problem.
func hashPositions(positions []PositionInfo) [32]byte {
	sorted := make([]PositionInfo, len(positions))
	copy(sorted, positions)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Ticket < sorted[j].Ticket
	})

	h := sha256.New()
	var buf [8]byte
	writeF := func(f float64) {
		binary.LittleEndian.PutUint64(buf[:], math.Float64bits(f))
		h.Write(buf[:])
	}
	for _, p := range sorted {
		h.Write([]byte(p.Ticket))
		h.Write([]byte{0})
		h.Write([]byte(p.Symbol))
		h.Write([]byte{0})
		h.Write([]byte(p.Direction))
		h.Write([]byte{0})
		writeF(p.EntryPrice)
		writeF(p.CurrentPrice)
		writeF(p.StopLoss)
		writeF(p.TakeProfit)
		writeF(p.Volume)
		writeF(p.Profit)
		writeF(p.Commission)
		writeF(p.Swap)
	}
	var out [32]byte
	copy(out[:], h.Sum(nil))
	return out
}
