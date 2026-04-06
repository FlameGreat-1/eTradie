package monitoring

import (
	"context"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
)

// TickCache provides a shared, per-symbol tick price cache that
// eliminates redundant broker HTTP calls. Instead of N workers each
// calling GetTickPrice for the same symbol, one background poller
// per symbol fetches the price and all workers read from cache.
//
// This reduces broker load from O(active_trades) to O(unique_symbols).
// With ~30 forex pairs, that's 30 req/s instead of 3,000+ req/s.
type TickCache struct {
	bp         broker.Port
	pollMs     int
	log        zerolog.Logger

	// Cached prices per symbol.
	mu     sync.RWMutex
	prices map[string]*broker.TickPrice

	// Reference counting for symbol subscriptions.
	// When count drops to 0, the poller for that symbol is stopped.
	subMu   sync.Mutex
	subRefs map[string]int
	pollers map[string]context.CancelFunc

	// Auth token for broker calls. Tick prices are not user-scoped
	// (EURUSD bid/ask is the same for all users), so any valid token works.
	tokenMu  sync.RWMutex
	authToken string
}

// NewTickCache creates a shared tick price cache.
func NewTickCache(bp broker.Port, pollMs int) *TickCache {
	return &TickCache{
		bp:      bp,
		pollMs:  pollMs,
		log:     observability.Logger("tick_cache"),
		prices:  make(map[string]*broker.TickPrice),
		subRefs: make(map[string]int),
		pollers: make(map[string]context.CancelFunc),
	}
}

// SetAuthToken sets the JWT token used for broker tick price calls.
// Called with a service token on startup and refreshed when users
// authenticate. Any valid token works since tick prices are not
// user-scoped.
func (tc *TickCache) SetAuthToken(token string) {
	tc.tokenMu.Lock()
	tc.authToken = token
	tc.tokenMu.Unlock()
}

// GetTickPrice returns the cached tick price for a symbol.
// Returns nil if the symbol has not been fetched yet (first poll
// hasn't completed). Callers should handle nil gracefully.
func (tc *TickCache) GetTickPrice(symbol string) *broker.TickPrice {
	tc.mu.RLock()
	tick := tc.prices[symbol]
	tc.mu.RUnlock()
	return tick
}

// Subscribe registers interest in a symbol. Starts a background
// poller if this is the first subscriber for the symbol.
// Must be called when a trade is registered for monitoring.
func (tc *TickCache) Subscribe(symbol string) {
	tc.subMu.Lock()
	defer tc.subMu.Unlock()

	tc.subRefs[symbol]++
	if tc.subRefs[symbol] == 1 {
		// First subscriber for this symbol. Start poller.
		ctx, cancel := context.WithCancel(context.Background())
		tc.pollers[symbol] = cancel
		go tc.pollSymbol(ctx, symbol)
		tc.log.Info().Str("symbol", symbol).Msg("tick_poller_started")
	}
}

// Unsubscribe removes interest in a symbol. Stops the background
// poller if this was the last subscriber.
// Must be called when a trade is removed from monitoring.
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
		// Remove cached price.
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
	tc.prices = make(map[string]*broker.TickPrice)
	tc.mu.Unlock()

	tc.log.Info().Msg("tick_cache_shutdown")
}

// pollSymbol is the background goroutine that fetches the tick price
// for a single symbol at the configured interval.
func (tc *TickCache) pollSymbol(ctx context.Context, symbol string) {
	interval := time.Duration(tc.pollMs) * time.Millisecond
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	// Fetch immediately on start so the cache is populated before
	// the first worker tick cycle.
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
		observability.TickCacheFetchErrors.WithLabelValues(symbol).Inc()
		return // Keep stale price in cache rather than removing it.
	}

	tc.mu.Lock()
	tc.prices[symbol] = tick
	tc.mu.Unlock()
}
