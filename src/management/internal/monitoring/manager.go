package monitoring

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/internal/stoploss"
	"github.com/flamegreat-1/etradie/src/management/internal/takeprofit"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
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

	// Shared tick price cache. One poller per symbol instead of one
	// HTTP call per trade. Reduces broker load from O(trades) to
	// O(unique_symbols).
	tickCache *TickCache

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
	mgr := &Manager{
		trades:     make(map[string]*types.Trade),
		cancels:    make(map[string]context.CancelFunc),
		bp:         bp,
		be:         be,
		trail:      trail,
		tp:         tp,
		journal:    journal,
		transport:  transport,
		tickCache:  NewTickCache(bp, tickPollMs),
		tickPollMs: tickPollMs,
		log:        observability.Logger("monitoring"),
	}

	// This ctx is never cancelled until manager dies, or we can use a dedicated ctx
	ctx, cancel := context.WithCancel(context.Background())
	mgr.cancels["_system_gauge_updater"] = cancel
	mgr.wg.Add(1)
	go func() {
		defer mgr.wg.Done()
		mgr.updateGauges(ctx)
	}()

	return mgr
}

// RegisterTrade adds a filled trade to active management and spawns
// a monitoring worker goroutine.
func (m *Manager) RegisterTrade(trade *types.Trade) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.trades[trade.TradeID] = trade

	ctx, cancel := context.WithCancel(context.Background())
	m.cancels[trade.TradeID] = cancel

	// Subscribe to tick cache for this symbol. Starts a poller if
	// this is the first trade on this symbol.
	m.tickCache.Subscribe(trade.Symbol)

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

// updateGauges periodically aggregates and publishes whole-portfolio PnL.
func (m *Manager) updateGauges(ctx context.Context) {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			trades := m.GetAllTrades()
			var totalUnrealized float64
			var totalRealized float64

			for _, t := range trades {
				t.RLock()
				totalUnrealized += t.UnrealizedPnL // updated constantly by workers
				totalRealized += t.RealizedPnL     // updated on partial closures
				t.RUnlock()
			}

			observability.UnrealizedPnL.Set(totalUnrealized)
			observability.RealizedPnL.Set(totalRealized)
		}
	}
}

// RemoveTrade stops monitoring a trade and removes it from the map.
func (m *Manager) RemoveTrade(tradeID string) {
	m.mu.Lock()

	// Get symbol before deleting for cache unsubscribe.
	var symbol string
	if t, ok := m.trades[tradeID]; ok {
		symbol = t.Symbol
	}

	if cancel, ok := m.cancels[tradeID]; ok {
		cancel()
		delete(m.cancels, tradeID)
	}
	delete(m.trades, tradeID)
	m.mu.Unlock()

	// Unsubscribe from tick cache. Stops the poller if this was the
	// last trade on this symbol.
	if symbol != "" {
		m.tickCache.Unsubscribe(symbol)
	}

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

// RefreshUserTradeTokens updates the AuthToken on all active trades
// owned by the given user. Called when the user makes any authenticated
// request (gRPC or HTTP) so that background workers (monitoring, EOD,
// news) can make authenticated broker calls on the user's behalf.
//
// This is critical after a service restart: restored trades have empty
// AuthTokens because the original JWT expired. The first authenticated
// action by the user refreshes all their trades with the new token.
func (m *Manager) RefreshUserTradeTokens(userID, newToken string) int {
	if userID == "" || newToken == "" {
		return 0
	}

	m.mu.RLock()
	defer m.mu.RUnlock()

	refreshed := 0
	for _, t := range m.trades {
		t.RLock()
		ownerMatch := t.UserID == userID
		currentToken := t.AuthToken
		t.RUnlock()

		if ownerMatch && currentToken != newToken {
			t.Lock()
			t.AuthToken = newToken
			t.Unlock()
			refreshed++
		}
	}

	if refreshed > 0 {
		m.log.Info().
			Str("user_id", userID).
			Int("trades_refreshed", refreshed).
			Msg("trade_auth_tokens_refreshed")
	}

	return refreshed
}

// TradeCount returns the number of active trades.
func (m *Manager) TradeCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return len(m.trades)
}

// Shutdown stops all monitoring workers and the tick cache.
func (m *Manager) Shutdown() {
	m.mu.Lock()
	for id, cancel := range m.cancels {
		cancel()
		delete(m.cancels, id)
	}
	m.mu.Unlock()

	m.tickCache.Shutdown()
	m.wg.Wait()
	m.log.Info().Msg("monitoring_manager_shutdown_complete")
}

// GetPriceForSymbol returns the current check price for a symbol
// from the shared tick cache. No HTTP call is made; the cache is
// populated by background pollers.
// Exposed for the EOD scheduler, news engine, and alert hub subscriber.
func (m *Manager) GetPriceForSymbol(ctx context.Context, symbol string) (float64, error) {
	tick := m.tickCache.GetTickPrice(symbol)
	if tick == nil {
		// Cache miss: symbol not yet polled or poller hasn't completed
		// first fetch. Fall back to direct broker call.
		var err error
		tick, err = m.bp.GetTickPrice(ctx, symbol)
		if err != nil {
			return 0, err
		}
	}
	return (tick.Bid + tick.Ask) / 2.0, nil
}

// TickCache returns the shared tick price cache. Exposed so that
// main.go can set the auth token on startup.
func (m *Manager) TickCache() *TickCache {
	return m.tickCache
}

// GenerateTradeID creates a unique trade management ID.
func GenerateTradeID() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return "TMG-" + hex.EncodeToString(b)
}
