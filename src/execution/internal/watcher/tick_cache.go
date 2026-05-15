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

// tickKey uniquely identifies a (user_id, symbol) pair. Tick prices
// come from the user's own broker on the engine side, so two users
// trading the same symbol must each get their own poller and cache
// slot. A single-key (symbol-only) cache would silently serve
// User A's watcher prices fetched from User B's broker.
type tickKey struct {
	userID string
	symbol string
}

// userIdentity holds one user's authentication context for the
// poller that runs on that user's behalf.
type userIdentity struct {
	claims *auth.Claims
	token  string
}

// TickCache provides a per-(user, symbol) tick price cache for
// watchers. Each pair has its own poller goroutine running with that
// user's identity, so multi-tenant correctness is preserved.
type TickCache struct {
	bp     broker.Port
	pollMs int
	log    zerolog.Logger

	mu     sync.RWMutex
	prices map[tickKey]*models.TickPrice

	subMu   sync.Mutex
	subRefs map[tickKey]int
	pollers map[tickKey]context.CancelFunc

	// Per-user identity. Each poller reads its slot via identityFor
	// before every fetch. Identity updates are atomic per user.
	identMu    sync.RWMutex
	identities map[string]*userIdentity
}

// NewTickCache creates a per-(user, symbol) tick price cache.
func NewTickCache(bp broker.Port, pollMs int) *TickCache {
	return &TickCache{
		bp:         bp,
		pollMs:     pollMs,
		log:        observability.Logger("watcher_tick_cache"),
		prices:     make(map[tickKey]*models.TickPrice),
		subRefs:    make(map[tickKey]int),
		pollers:    make(map[tickKey]context.CancelFunc),
		identities: make(map[string]*userIdentity),
	}
}

// SetServiceIdentity stores the (claims, token) identity for the
// user identified by claims.UserID. Pollers for that user pick it
// up on their next fetch cycle. Identities for OTHER users are
// untouched.
func (tc *TickCache) SetServiceIdentity(claims *auth.Claims, rawToken string) {
	if claims == nil || claims.UserID == "" {
		return
	}
	tc.identMu.Lock()
	tc.identities[claims.UserID] = &userIdentity{claims: claims, token: rawToken}
	tc.identMu.Unlock()
}

// SetAuthToken is the legacy entry point retained for callers that
// have only a token. Parses the local-mint JWT and delegates.
// A malformed token is a no-op.
func (tc *TickCache) SetAuthToken(token string) {
	claims := parseLocalServiceToken(token)
	if claims == nil {
		return
	}
	tc.SetServiceIdentity(claims, token)
}

// identityFor returns the stored identity for user u, or nil when
// none has been configured yet.
func (tc *TickCache) identityFor(userID string) *userIdentity {
	tc.identMu.RLock()
	id := tc.identities[userID]
	tc.identMu.RUnlock()
	return id
}

// GetTickPrice returns the cached price for (userID, symbol) or nil
// when no poll for that pair has completed yet.
func (tc *TickCache) GetTickPrice(userID, symbol string) *models.TickPrice {
	k := tickKey{userID: userID, symbol: symbol}
	tc.mu.RLock()
	tick := tc.prices[k]
	tc.mu.RUnlock()
	return tick
}

// Subscribe registers interest in (userID, symbol). Starts a
// dedicated poller for that pair when it's the first subscriber.
func (tc *TickCache) Subscribe(userID, symbol string) {
	k := tickKey{userID: userID, symbol: symbol}
	tc.subMu.Lock()
	defer tc.subMu.Unlock()

	tc.subRefs[k]++
	if tc.subRefs[k] == 1 {
		ctx, cancel := context.WithCancel(context.Background())
		tc.pollers[k] = cancel
		go tc.pollPair(ctx, k)
		tc.log.Info().
			Str("user_id", userID).
			Str("symbol", symbol).
			Msg("tick_poller_started")
	}
}

// Unsubscribe removes interest in (userID, symbol). Stops the
// dedicated poller when ref count drops to zero.
func (tc *TickCache) Unsubscribe(userID, symbol string) {
	k := tickKey{userID: userID, symbol: symbol}
	tc.subMu.Lock()
	defer tc.subMu.Unlock()

	tc.subRefs[k]--
	if tc.subRefs[k] <= 0 {
		delete(tc.subRefs, k)
		if cancel, ok := tc.pollers[k]; ok {
			cancel()
			delete(tc.pollers, k)
		}
		tc.mu.Lock()
		delete(tc.prices, k)
		tc.mu.Unlock()
		tc.log.Info().
			Str("user_id", userID).
			Str("symbol", symbol).
			Msg("tick_poller_stopped")
	}
}

// Shutdown stops all pollers and clears caches.
func (tc *TickCache) Shutdown() {
	tc.subMu.Lock()
	for k, cancel := range tc.pollers {
		cancel()
		delete(tc.pollers, k)
	}
	tc.subRefs = make(map[tickKey]int)
	tc.subMu.Unlock()

	tc.mu.Lock()
	tc.prices = make(map[tickKey]*models.TickPrice)
	tc.mu.Unlock()

	tc.identMu.Lock()
	tc.identities = make(map[string]*userIdentity)
	tc.identMu.Unlock()
}

func (tc *TickCache) pollPair(ctx context.Context, k tickKey) {
	interval := time.Duration(tc.pollMs) * time.Millisecond
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	tc.fetchAndCache(ctx, k)

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			tc.fetchAndCache(ctx, k)
		}
	}
}

func (tc *TickCache) fetchAndCache(ctx context.Context, k tickKey) {
	if tc.bp == nil {
		return // No broker port available (test mode).
	}

	id := tc.identityFor(k.userID)
	if id == nil || id.claims == nil {
		return
	}

	authCtx := auth.InjectClaimsIntoContext(ctx, id.claims)
	if id.token != "" {
		authCtx = auth.InjectTokenIntoContext(authCtx, id.token)
	}

	tick, err := tc.bp.GetTickPrice(authCtx, k.symbol)
	if err != nil {
		observability.TickCacheFetchErrors.WithLabelValues(k.symbol).Inc()
		return // Keep stale price in cache rather than removing it.
	}

	tc.mu.Lock()
	tc.prices[k] = tick
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
