package monitoring

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	"github.com/flamegreat-1/etradie/src/auth"
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

	// Set this user's identity in the per-user identity map BEFORE
	// subscribing, so the first poll for the (user, symbol) pair has
	// a non-nil identity to authenticate with. When the trade was
	// restored from a pre-upgrade DB row missing identity fields,
	// fall back to the parse-the-token shim.
	if trade.UserID != "" {
		m.tickCache.SetServiceIdentity(&auth.Claims{
			UserID:   trade.UserID,
			Username: trade.Username,
			Role:     auth.Role(trade.Role),
			Tier:     trade.Tier,
			Status:   trade.StatusJWT,
		}, trade.AuthToken)
	} else if trade.AuthToken != "" {
		m.tickCache.SetAuthToken(trade.AuthToken)
	}

	// Subscribe to the per-(user, symbol) cache slot. Starts a
	// dedicated poller for this user when it's the first
	// subscription for that (user, symbol) pair.
	m.tickCache.Subscribe(trade.UserID, trade.Symbol)

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

	// Capture (userID, symbol) before deleting for cache unsubscribe.
	var userID, symbol string
	if t, ok := m.trades[tradeID]; ok {
		userID = t.UserID
		symbol = t.Symbol
	}

	if cancel, ok := m.cancels[tradeID]; ok {
		cancel()
		delete(m.cancels, tradeID)
	}
	delete(m.trades, tradeID)
	m.mu.Unlock()

	// Unsubscribe the (user, symbol) pair. Stops the dedicated poller
	// for this user when this was the last trade on that symbol.
	if symbol != "" {
		m.tickCache.Unsubscribe(userID, symbol)
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

// RefreshUserTradeIdentity updates the full identity (UserID is the
// matching key; Username, Role, Tier, StatusJWT, and AuthToken are
// the writable fields) on every active trade owned by claims.UserID.
//
// Called by every gRPC handler after the auth interceptor produced a
// fresh *auth.Claims, and by the 24h service-token renewal goroutine
// after issuing a renewed token. Every identity field is overwritten
// atomically under the per-Trade write lock so a concurrent worker
// reading via Trade.IdentityCtx never sees a partial update.
func (m *Manager) RefreshUserTradeIdentity(claims *auth.Claims, newToken string) int {
	if claims == nil || claims.UserID == "" || newToken == "" {
		return 0
	}

	m.mu.RLock()
	defer m.mu.RUnlock()

	refreshed := 0
	for _, t := range m.trades {
		t.RLock()
		ownerMatch := t.UserID == claims.UserID
		currentToken := t.AuthToken
		currentTier := t.Tier
		currentStatus := t.StatusJWT
		t.RUnlock()

		if !ownerMatch {
			continue
		}
		if currentToken == newToken && currentTier == claims.Tier && currentStatus == claims.Status {
			continue // nothing to update
		}

		t.Lock()
		t.Username = claims.Username
		t.Role = string(claims.Role)
		t.Tier = claims.Tier
		t.StatusJWT = claims.Status
		t.AuthToken = newToken
		t.Unlock()
		refreshed++
	}

	if refreshed > 0 {
		m.log.Info().
			Str("user_id", claims.UserID).
			Str("tier", claims.Tier).
			Str("status", claims.Status).
			Int("trades_refreshed", refreshed).
			Msg("trade_identity_refreshed")
	}

	return refreshed
}

// RefreshUserTradeTokens is the legacy entry point retained for the
// (rare) caller that has only a token. It parses the local-mint JWT
// payload to recover the full *auth.Claims and delegates to
// RefreshUserTradeIdentity. A malformed token is a no-op (returns 0).
//
// Prefer RefreshUserTradeIdentity in any new code path that already
// has *auth.Claims in hand — it avoids the parse and the parse's
// failure modes.
func (m *Manager) RefreshUserTradeTokens(userID, newToken string) int {
	if userID == "" || newToken == "" {
		return 0
	}
	claims := parseLocalServiceToken(newToken)
	if claims == nil || claims.UserID != userID {
		// Token doesn't match expected user; refuse to update.
		m.log.Warn().
			Str("expected_user_id", userID).
			Msg("trade_token_refresh_skipped_claim_mismatch")
		return 0
	}
	return m.RefreshUserTradeIdentity(claims, newToken)
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

// GetPriceForSymbol returns the current check price for the user
// identified by ctx (via auth.UserIDFromContext) and the given symbol
// from the per-(user, symbol) tick cache. No HTTP call is made when
// the cache is populated; falls back to a direct authenticated
// broker call on cache miss.
//
// Caller MUST stamp ctx with the trade's identity (Trade.IdentityCtx)
// before calling so the broker resolves to the right per-user
// connection. An empty UserID in ctx is reported as ErrNoIdentityInCtx.
func (m *Manager) GetPriceForSymbol(ctx context.Context, symbol string) (float64, error) {
	userID := auth.UserIDFromContext(ctx)
	if userID == "" {
		return 0, ErrNoIdentityInCtx
	}
	tick := m.tickCache.GetTickPrice(userID, symbol)
	if tick == nil {
		var err error
		tick, err = m.bp.GetTickPrice(ctx, symbol)
		if err != nil {
			return 0, err
		}
	}
	return (tick.Bid + tick.Ask) / 2.0, nil
}

// ErrNoIdentityInCtx is returned by GetPriceForSymbol when the caller
// did not stamp the context with a user identity. Always a bug at the
// call site; the user_id is required to look up the correct per-user
// broker on the engine.
var ErrNoIdentityInCtx = fmt.Errorf("no user identity in context (call Trade.IdentityCtx first)")

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
