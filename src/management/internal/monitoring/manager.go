package monitoring

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/alert"
	"github.com/flamegreat/etradie/src/management/internal/broker"
	"github.com/flamegreat/etradie/src/management/internal/constants"
	"github.com/flamegreat/etradie/src/management/internal/eod"
	"github.com/flamegreat/etradie/src/management/internal/journal"
	"github.com/flamegreat/etradie/src/management/internal/observability"
	"github.com/flamegreat/etradie/src/management/internal/stoploss"
	"github.com/flamegreat/etradie/src/management/internal/takeprofit"
	"github.com/flamegreat/etradie/src/management/pkg/types"
)

// AlertTransport abstracts the alert publishing interface.
type AlertTransport interface {
	Publish(ctx context.Context, event *alert.Event)
}

// Manager orchestrates all active trade monitoring workers. It is the
// central hub that spawns per-trade goroutines and coordinates lifecycle.
type Manager struct {
	mu sync.RWMutex

	// Active trades indexed by trade ID.
	trades map[string]*types.Trade

	// Per-trade worker cancel functions.
	cancels map[string]context.CancelFunc

	// Sub-engines.
	bp        broker.Port
	be        *stoploss.BreakevenEngine
	trail     *stoploss.TrailingEngine
	tp        *takeprofit.Executor
	journal   *journal.Repository
	transport AlertTransport

	// Config.
	tickPollMs int

	wg  sync.WaitGroup
	log zerolog.Logger
}

// NewManager creates a trade monitoring manager.
func NewManager(
	bp broker.Port,
	be *stoploss.BreakevenEngine,
	trail *stoploss.TrailingEngine,
	tp *takeprofit.Executor,
	journal *journal.Repository,
	transport AlertTransport,
	tickPollMs int,
) *Manager {
	return &Manager{
		trades:     make(map[string]*types.Trade),
		cancels:    make(map[string]context.CancelFunc),
		bp:         bp,
		be:         be,
		trail:      trail,
		tp:         tp,
		journal:    journal,
		transport:  transport,
		tickPollMs: tickPollMs,
		log:        observability.Logger("monitoring"),
	}
}

// RegisterTrade adds a filled trade to active management and spawns
// a monitoring worker goroutine.
func (m *Manager) RegisterTrade(trade *types.Trade) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.trades[trade.TradeID] = trade

	ctx, cancel := context.WithCancel(context.Background())
	m.cancels[trade.TradeID] = cancel

	m.wg.Add(1)
	go m.runWorker(ctx, trade)

	observability.ManagedTradesGauge.Inc()

	m.log.Info().
		Str("trade_id", trade.TradeID).
		Str("symbol", trade.Symbol).
		Str("direction", string(trade.Direction)).
		Str("style", string(trade.TradingStyle)).
		Float64("entry", trade.EntryPrice).
		Float64("sl", trade.StopLoss).
		Float64("lot_size", trade.TotalLotSize).
		Msg("trade_registered_for_management")
}

// RemoveTrade stops monitoring a trade and removes it from the map.
func (m *Manager) RemoveTrade(tradeID string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if cancel, ok := m.cancels[tradeID]; ok {
		cancel()
		delete(m.cancels, tradeID)
	}
	delete(m.trades, tradeID)

	observability.ManagedTradesGauge.Dec()
}

// GetAllTrades returns a snapshot of all actively managed trades.
func (m *Manager) GetAllTrades() []*types.Trade {
	m.mu.RLock()
	defer m.mu.RUnlock()

	trades := make([]*types.Trade, 0, len(m.trades))
	for _, t := range m.trades {
		trades = append(trades, t)
	}
	return trades
}

// GetTrade returns a single trade by ID, or nil if not found.
func (m *Manager) GetTrade(tradeID string) *types.Trade {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.trades[tradeID]
}

// TradeCount returns the number of active trades.
func (m *Manager) TradeCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.trades)
}

// Shutdown stops all monitoring workers and waits for completion.
func (m *Manager) Shutdown() {
	m.mu.Lock()
	for id, cancel := range m.cancels {
		cancel()
		delete(m.cancels, id)
	}
	m.mu.Unlock()

	m.wg.Wait()
	m.log.Info().Msg("monitoring_manager_shutdown_complete")
}

// GetPriceForSymbol fetches the current check price for a symbol.
// Exposed for the EOD scheduler.
func (m *Manager) GetPriceForSymbol(ctx context.Context, symbol string) (float64, error) {
	tick, err := m.bp.GetTickPrice(ctx, symbol)
	if err != nil {
		return 0, err
	}
	return (tick.Bid + tick.Ask) / 2.0, nil
}



// GenerateTradeID creates a unique trade management ID.
func GenerateTradeID() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return "TMG-" + hex.EncodeToString(b)
}
