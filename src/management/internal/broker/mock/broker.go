package mock

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
)

// Broker is a mock implementation of broker.Port for development
// and testing. It simulates position state in memory without any
// real broker connection.
type Broker struct {
	mu        sync.RWMutex
	positions map[string]*broker.PositionInfo
	prices    map[string]*broker.TickPrice
	log       zerolog.Logger
}

// NewBroker creates a mock broker for Module C.
func NewBroker() *Broker {
	return &Broker{
		positions: make(map[string]*broker.PositionInfo),
		prices:    make(map[string]*broker.TickPrice),
		log:       observability.Logger("mock_broker"),
	}
}

// SetTickPrice sets a simulated tick price for testing.
func (b *Broker) SetTickPrice(symbol string, bid, ask float64) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.prices[symbol] = &broker.TickPrice{Bid: bid, Ask: ask}
}

// AddPosition adds a simulated position for testing.
func (b *Broker) AddPosition(pos *broker.PositionInfo) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.positions[pos.Ticket] = pos
}

func (b *Broker) GetTickPrice(_ context.Context, symbol string) (*broker.TickPrice, error) {
	b.mu.RLock()
	defer b.mu.RUnlock()

	tp, ok := b.prices[symbol]
	if !ok {
		return &broker.TickPrice{Bid: 1.08000, Ask: 1.08020}, nil
	}
	return tp, nil
}

func (b *Broker) GetPosition(_ context.Context, ticket string) (*broker.PositionInfo, error) {
	b.mu.RLock()
	defer b.mu.RUnlock()

	pos, ok := b.positions[ticket]
	if !ok {
		return nil, fmt.Errorf("position %s not found", ticket)
	}
	return pos, nil
}

func (b *Broker) GetPositions(_ context.Context) ([]broker.PositionInfo, error) {
	b.mu.RLock()
	defer b.mu.RUnlock()

	var list []broker.PositionInfo
	for _, p := range b.positions {
		list = append(list, *p)
	}
	return list, nil
}

func (b *Broker) GetHistory(_ context.Context, days int) ([]broker.HistoryDealInfo, error) {
	return []broker.HistoryDealInfo{}, nil
}

// WatchPositions implements broker.Port.WatchPositions for the mock.
// Emits the current in-memory positions at the configured interval.
// Used in tests and the BROKER_MODE=mock dev path.
func (b *Broker) WatchPositions(
	ctx context.Context,
	interval time.Duration,
) (<-chan []broker.PositionInfo, <-chan error) {
	positions := make(chan []broker.PositionInfo, 1)
	errors := make(chan error, 1)

	if interval <= 0 {
		interval = time.Second
	}

	go func() {
		defer close(positions)
		defer close(errors)

		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		emit := func() {
			snap, _ := b.GetPositions(ctx)
			select {
			case positions <- snap:
			case <-ctx.Done():
			default:
				// Drain stale snapshot, then send.
				select {
				case <-positions:
				default:
				}
				select {
				case positions <- snap:
				case <-ctx.Done():
				}
			}
		}

		emit() // Prime
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				emit()
			}
		}
	}()

	return positions, errors
}

func (b *Broker) ModifyPosition(_ context.Context, ticket string, newSL, newTP float64) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	pos, ok := b.positions[ticket]
	if !ok {
		return fmt.Errorf("position %s not found", ticket)
	}

	pos.StopLoss = newSL
	pos.TakeProfit = newTP

	b.log.Info().
		Str("ticket", ticket).
		Float64("new_sl", newSL).
		Float64("new_tp", newTP).
		Msg("mock_position_modified")

	return nil
}

func (b *Broker) ClosePartial(_ context.Context, ticket string, volumeToClose float64) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	pos, ok := b.positions[ticket]
	if !ok {
		return fmt.Errorf("position %s not found", ticket)
	}

	if volumeToClose > pos.Volume {
		return fmt.Errorf("cannot close %.2f lots on position with %.2f lots", volumeToClose, pos.Volume)
	}

	pos.Volume -= volumeToClose

	b.log.Info().
		Str("ticket", ticket).
		Float64("volume_closed", volumeToClose).
		Float64("remaining_volume", pos.Volume).
		Msg("mock_partial_close")

	return nil
}

func (b *Broker) ClosePosition(_ context.Context, ticket string) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	_, ok := b.positions[ticket]
	if !ok {
		return fmt.Errorf("position %s not found", ticket)
	}

	delete(b.positions, ticket)

	b.log.Info().
		Str("ticket", ticket).
		Msg("mock_position_closed")

	return nil
}
