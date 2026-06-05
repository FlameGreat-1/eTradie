package watcher

import (
	"context"
	"sync"
	"time"
)

// HaltReader reads the durable kill-switch flags. store.SettingsStore
// satisfies it, so enforcement uses the same source as intake.
type HaltReader interface {
	IsGlobalHalted(ctx context.Context) (bool, error)
	IsUserHalted(ctx context.Context, userID string) (bool, error)
}

// haltCacheTTL bounds staleness of a cached verdict, keeping the
// per-tick fire path off a cold DB read while reacting within one tick.
const haltCacheTTL = time.Second

// cachedHaltReader adds a short per-scope TTL cache over a HaltReader.
// A read error resolves to not-halted and leaves the prior value in
// place: a transient DB blip must not self-inflict a trading halt.
type cachedHaltReader struct {
	inner HaltReader

	mu        sync.Mutex
	globalVal bool
	globalAt  time.Time
	userVals  map[string]haltEntry
}

type haltEntry struct {
	val bool
	at  time.Time
}

func newCachedHaltReader(inner HaltReader) *cachedHaltReader {
	return &cachedHaltReader{inner: inner, userVals: make(map[string]haltEntry)}
}

// halted reports whether placement is blocked for userID, with global
// taking precedence over per-user. The returned scope ("global"|"user"|"")
// is for audit/logging.
func (c *cachedHaltReader) halted(ctx context.Context, userID string) (bool, string) {
	if c == nil || c.inner == nil {
		return false, ""
	}
	if c.isGlobalHalted(ctx) {
		return true, "global"
	}
	if userID != "" && c.isUserHalted(ctx, userID) {
		return true, "user"
	}
	return false, ""
}

func (c *cachedHaltReader) isGlobalHalted(ctx context.Context) bool {
	c.mu.Lock()
	if time.Since(c.globalAt) < haltCacheTTL {
		v := c.globalVal
		c.mu.Unlock()
		return v
	}
	c.mu.Unlock()

	v, err := c.inner.IsGlobalHalted(ctx)
	if err != nil {
		c.mu.Lock()
		prev := c.globalVal
		c.mu.Unlock()
		return prev
	}
	c.mu.Lock()
	c.globalVal, c.globalAt = v, time.Now()
	c.mu.Unlock()
	return v
}

func (c *cachedHaltReader) isUserHalted(ctx context.Context, userID string) bool {
	c.mu.Lock()
	if e, ok := c.userVals[userID]; ok && time.Since(e.at) < haltCacheTTL {
		c.mu.Unlock()
		return e.val
	}
	c.mu.Unlock()

	v, err := c.inner.IsUserHalted(ctx, userID)
	if err != nil {
		c.mu.Lock()
		prev := c.userVals[userID].val
		c.mu.Unlock()
		return prev
	}
	c.mu.Lock()
	c.userVals[userID] = haltEntry{val: v, at: time.Now()}
	c.mu.Unlock()
	return v
}
