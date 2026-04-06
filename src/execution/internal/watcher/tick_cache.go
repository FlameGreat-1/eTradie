package watcher

import (
	"context"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

// TickCache provides a shared, per-symbol tick price cache for watchers.
// Instead of N watchers each calling GetTickPrice for the same symbol,
// one background poller per symbol fetches the price and all watchers
// read from cache.
type TickCache struct {
	bp     broker.Port
	pollMs int
	log    zerolog.Logger

	mu     sync.RWMutex
	prices map[string]*models.TickPrice

	subMu   sync.Mutex
	subRefs map[string]int
	pollers map[string]context.CancelFunc

	tokenMu   sync.RWMutex
	authToken string
}

// NewTickCache creates a shared tick price cache for watchers.
func NewTickCache(bp broker.Port, pollMs int) *TickCache {
	return &TickCache{
		bp:      bp,
		pollMs:  pollMs,
		log:     observability.Logger("watcher_tick_cache"),
		prices:  make(map[string]*models.TickPrice),
		subRefs: make(map[string]int),
		pollers: make(map[string]context.CancelFunc),
	}
}

// SetAuthToken sets the JWT token used for broker tick price calls.
func (tc *TickCache) SetAuthToken(token string) {
	tc.tokenMu.Lock()
	tc.authToken = token
	tc.tokenMu.Unlock()
}

// GetTickPrice returns the cached tick price for a symbol.
// Returns nil if the symbol has not been fetched yet.
func (tc *TickCache) GetTickPrice(symbol string) *models.TickPrice {
	tc.mu.RLock()
	tick := tc.prices[symbol]
	tc.mu.RUnlock()
	return tick
}

// Subscribe registers interest in a symbol. Starts a background
// poller if this is the first subscriber.
func (tc *TickCache) Subscribe(symbol string) {
	tc.subMu.Lock()
	defer tc.subMu.Unlock()

	tc.subRefs[symbol]++
	if tc.subRefs[symbol] == 1 {
		ctx, cancel := context.WithCancel(context.Background())
		tc.pollers[symbol] = cancel
		go tc.pollSymbol(ctx, symbol)
		tc.log.Info().Str("symbol", symbol).Msg("tick_poller_started")
	}
}

// Unsubscribe removes interest in a symbol. Stops the poller if
// this was the last subscriber.
func (tc *TickCache) Unsubscribe(symbol string) {
	tc.subMu.Lock()
	defer tc.subMu.Unlock()

	tc.subRefs[symbol]--
	if tc.subRefs[symbol] <= 0 {
		delete(tc.subRefs, symbol)
		if cancel, ok := tc.pollers[symbol]; ok {
			cancel()
			delete(tc.pollers, symbol)
		}
		tc.mu.Lock()
		delete(tc.prices, symbol)
		tc.mu.Unlock()
		tc.log.Info().Str("symbol", symbol).Msg("tick_poller_stopped")
	}
}

// Shutdown stops all pollers.
func (tc *TickCache) Shutdown() {
	tc.subMu.Lock()
	for symbol, cancel := range tc.pollers {
		cancel()
		delete(tc.pollers, symbol)
	}
	tc.subRefs = make(map[string]int)
	tc.subMu.Unlock()

	tc.mu.Lock()
	tc.prices = make(map[string]*models.TickPrice)
	tc.mu.Unlock()
}

func (tc *TickCache) pollSymbol(ctx context.Context, symbol string) {
	interval := time.Duration(tc.pollMs) * time.Millisecond
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	tc.fetchAndCache(ctx, symbol)

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			tc.fetchAndCache(ctx, symbol)
		}
	}
}

func (tc *TickCache) fetchAndCache(ctx context.Context, symbol string) {
	tc.tokenMu.RLock()
	token := tc.authToken
	tc.tokenMu.RUnlock()

	authCtx := auth.InjectTokenIntoContext(ctx, token)

	tick, err := tc.bp.GetTickPrice(authCtx, symbol)
	if err != nil {
		return
	}

	tc.mu.Lock()
	tc.prices[symbol] = tick
	tc.mu.Unlock()
}
