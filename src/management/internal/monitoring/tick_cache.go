package monitoring

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"strings"
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

	// Identity for broker calls. Tick prices come from a specific
	// user's broker connection on the engine side, so the cache MUST
	// run with a real user identity (UserID drives broker resolution
	// in engine.helpers._resolve_user_broker). The chosen identity is
	// set once at startup by management/cmd/main.go (the first user
	// with a configured broker connection) and refreshed when a new
	// trade is registered.
	identMu      sync.RWMutex
	identClaims  *auth.Claims
	identToken   string
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

// SetServiceIdentity sets the identity used to authenticate broker
// tick-price calls. The claims drive auth.InjectClaimsIntoContext
// inside fetchAndCache, so the bridge's X-User-Id header resolves
// to a real user with a configured broker connection.
//
// rawToken is stored alongside the claims so any callee that still
// reads RawTokenFromContext keeps working; new code should rely on
// the claims only.
func (tc *TickCache) SetServiceIdentity(claims *auth.Claims, rawToken string) {
	tc.identMu.Lock()
	tc.identClaims = claims
	tc.identToken = rawToken
	tc.identMu.Unlock()
}

// SetAuthToken is the legacy entry point retained for callers that
// have not been migrated to SetServiceIdentity. Building Claims from
// a raw JWT without verifying the signature is acceptable here
// because the JWT was just minted by THIS service's TokenService
// (we're parsing our own token, not a remote one).
func (tc *TickCache) SetAuthToken(token string) {
	claims := parseLocalServiceToken(token)
	tc.SetServiceIdentity(claims, token)
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
	tc.identMu.RLock()
	claims := tc.identClaims
	token := tc.identToken
	tc.identMu.RUnlock()

	if claims == nil {
		// No identity configured yet (cold start before any user has
		// been resolved). Skip this poll; the next Subscribe call by
		// the manager will populate identity via SetServiceIdentity.
		return
	}

	authCtx := auth.InjectClaimsIntoContext(ctx, claims)
	if token != "" {
		authCtx = auth.InjectTokenIntoContext(authCtx, token)
	}

	tick, err := tc.bp.GetTickPrice(authCtx, symbol)
	if err != nil {
		tc.log.Error().Err(err).Str("symbol", symbol).Msg("tick_cache_fetch_failed")
		observability.TickCacheFetchErrors.WithLabelValues(symbol).Inc()
		return // Keep stale price in cache rather than removing it.
	}

	tc.mu.Lock()
	tc.prices[symbol] = tick
	tc.mu.Unlock()
}

// parseLocalServiceToken extracts Claims from a JWT minted by THIS
// service's TokenService. We trust the signature only because we
// just produced the token in-process; the parse here only decodes
// the payload to recover the claims for context injection. If the
// token is malformed, returns nil and the cache stays un-armed
// until the next SetServiceIdentity call.
func parseLocalServiceToken(token string) *auth.Claims {
	if token == "" {
		return nil
	}
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return nil
	}
	payload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil
	}
	var c auth.Claims
	if err := json.Unmarshal(payload, &c); err != nil {
		return nil
	}
	if c.UserID == "" {
		return nil
	}
	return &c
}
