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

// tickKey uniquely identifies a (user_id, symbol) pair. Tick prices
// come from the user's own broker on the engine side, so two users
// trading the same symbol must each get their own poller and their
// own cache slot. A single-key (symbol-only) cache would silently
// serve User A's worker prices fetched from User B's broker.
type tickKey struct {
	userID string
	symbol string
}

// userIdentity is the per-user authentication context that the
// poller uses for one user's tick fetches.
type userIdentity struct {
	claims *auth.Claims
	token  string
}

// TickCache provides a per-(user, symbol) tick price cache. Each
// (user, symbol) pair has its own poller goroutine running with
// that user's identity, so multi-tenant correctness is preserved
// even when two users hold positions on the same symbol but trade
// against different brokers.
//
// Load profile: O(unique (user, symbol) pairs) HTTP calls per
// interval. With 1,000 active users averaging 1.5 symbols each
// this is 1,500 polls per interval, well within the engine's
// budget at the standard 1s cadence.
type TickCache struct {
	bp     broker.Port
	pollMs int
	log    zerolog.Logger

	// Cached prices per (user_id, symbol).
	mu     sync.RWMutex
	prices map[tickKey]*broker.TickPrice

	// Reference counting + poller registry per (user_id, symbol).
	subMu   sync.Mutex
	subRefs map[tickKey]int
	pollers map[tickKey]context.CancelFunc

	// Per-user identity. SetServiceIdentity / SetAuthToken set a value
	// here keyed by claims.UserID; each poller reads its slot before
	// every fetch. Identity updates are atomic per user.
	identMu    sync.RWMutex
	identities map[string]*userIdentity
}

// NewTickCache creates a per-(user, symbol) tick price cache.
func NewTickCache(bp broker.Port, pollMs int) *TickCache {
	return &TickCache{
		bp:         bp,
		pollMs:     pollMs,
		log:        observability.Logger("tick_cache"),
		prices:     make(map[tickKey]*broker.TickPrice),
		subRefs:    make(map[tickKey]int),
		pollers:    make(map[tickKey]context.CancelFunc),
		identities: make(map[string]*userIdentity),
	}
}

// SetServiceIdentity stores the (claims, token) identity for the
// user identified by claims.UserID. Pollers for that user pick it
// up on their next fetch cycle. Identity for OTHER users is
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
// have only a token. Parses the local-mint JWT payload to recover
// claims and delegates. A malformed token is a no-op.
func (tc *TickCache) SetAuthToken(token string) {
	claims := parseLocalServiceToken(token)
	if claims == nil {
		return
	}
	tc.SetServiceIdentity(claims, token)
}

// HasServiceIdentity reports whether any user identity has been
// configured. Used by the reconciler supervisor to seed the cache
// exactly once on a cold start.
func (tc *TickCache) HasServiceIdentity() bool {
	tc.identMu.RLock()
	n := len(tc.identities)
	tc.identMu.RUnlock()
	return n > 0
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
func (tc *TickCache) GetTickPrice(userID, symbol string) *broker.TickPrice {
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

// Shutdown stops all pollers and clears the cache.
func (tc *TickCache) Shutdown() {
	tc.subMu.Lock()
	for k, cancel := range tc.pollers {
		cancel()
		delete(tc.pollers, k)
	}
	tc.subRefs = make(map[tickKey]int)
	tc.subMu.Unlock()

	tc.mu.Lock()
	tc.prices = make(map[tickKey]*broker.TickPrice)
	tc.mu.Unlock()

	tc.identMu.Lock()
	tc.identities = make(map[string]*userIdentity)
	tc.identMu.Unlock()

	tc.log.Info().Msg("tick_cache_shutdown")
}

// pollPair is the background goroutine for one (user_id, symbol)
// tuple. Fetches with the user's stored identity on each interval.
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
	id := tc.identityFor(k.userID)
	if id == nil || id.claims == nil {
		// No identity configured yet for this user. Skip; the next
		// authenticated action by the user (or the renewal goroutine)
		// will populate it via SetServiceIdentity.
		return
	}

	authCtx := auth.InjectClaimsIntoContext(ctx, id.claims)
	if id.token != "" {
		authCtx = auth.InjectTokenIntoContext(authCtx, id.token)
	}

	tick, err := tc.bp.GetTickPrice(authCtx, k.symbol)
	if err != nil {
		tc.log.Error().Err(err).
			Str("user_id", k.userID).
			Str("symbol", k.symbol).
			Msg("tick_cache_fetch_failed")
		observability.TickCacheFetchErrors.WithLabelValues(k.symbol).Inc()
		return // Keep stale price in cache rather than removing it.
	}

	tc.mu.Lock()
	tc.prices[k] = tick
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
