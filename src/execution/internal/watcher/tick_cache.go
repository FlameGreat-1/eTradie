package watcher

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"strings"
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

	// Identity used to authenticate broker tick-price calls. The
	// engine resolves the per-user broker from X-User-Id (read from
	// auth.UserIDFromContext), so this cache MUST run with a real
	// user identity. Bootstrapped at startup and refreshed when
	// watchers are armed (see Manager.Arm).
	identMu     sync.RWMutex
	identClaims *auth.Claims
	identToken  string
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

// SetServiceIdentity sets the identity used to authenticate broker
// tick-price calls. Driven by Manager.Arm so the cache always uses
// the latest known identity for the symbol's owner.
func (tc *TickCache) SetServiceIdentity(claims *auth.Claims, rawToken string) {
	tc.identMu.Lock()
	tc.identClaims = claims
	tc.identToken = rawToken
	tc.identMu.Unlock()
}

// SetAuthToken is the legacy entry point retained for callers that
// pass only a raw JWT. Builds Claims from the local-mint token
// payload (we minted it in-process so no signature check needed)
// and delegates to SetServiceIdentity. Malformed tokens are dropped
// silently; the cache stays un-armed until the next set call.
func (tc *TickCache) SetAuthToken(token string) {
	claims := parseLocalServiceToken(token)
	tc.SetServiceIdentity(claims, token)
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
	if tc.bp == nil {
		return // No broker port available (test mode).
	}

	tc.identMu.RLock()
	claims := tc.identClaims
	token := tc.identToken
	tc.identMu.RUnlock()

	if claims == nil {
		// Identity not yet configured. The next Arm call will set it
		// and the next ticker beat will pick up the new identity.
		return
	}

	authCtx := auth.InjectClaimsIntoContext(ctx, claims)
	if token != "" {
		authCtx = auth.InjectTokenIntoContext(authCtx, token)
	}

	tick, err := tc.bp.GetTickPrice(authCtx, symbol)
	if err != nil {
		observability.TickCacheFetchErrors.WithLabelValues(symbol).Inc()
		return // Keep stale price in cache rather than removing it.
	}

	tc.mu.Lock()
	tc.prices[symbol] = tick
	tc.mu.Unlock()
}

// parseLocalServiceToken decodes the payload of a JWT minted by THIS
// service's TokenService. Signature is not verified because the
// token was produced in-process; the parse only recovers claims for
// context injection. Returns nil for malformed tokens.
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
