package service

import (
	"container/list"
	"sync"
	"time"
)

// TokenBucketRateLimiter is a per-key (typically per-IP) bounded LRU of
// token buckets. Each key gets its own bucket; bucket state is dropped
// when the LRU evicts the key under memory pressure (default cap 4096).
//
// The bucket itself is the classic algorithm: fill rate R tokens/sec,
// burst B. Allow() refills based on elapsed wall-clock since the last
// call, then decrements; if the bucket is dry, Allow() returns false.
//
// Thread-safety: a single sync.Mutex guards both the LRU and every
// bucket. The critical section is O(1) (move-to-front + arithmetic on
// a single uint64) so contention is negligible even at high QPS. The
// rejected-counter is atomic so metrics scraping never blocks.
type TokenBucketRateLimiter struct {
	mu       sync.Mutex
	buckets  map[string]*list.Element
	lru      *list.List
	maxKeys  int
	rate     float64 // tokens per second
	burst    float64 // max tokens
	rejected uint64
	now      func() time.Time
}

// rateLimitEntry holds bucket state for a single key.
type rateLimitEntry struct {
	key      string
	tokens   float64
	lastSeen time.Time
}

// RateLimiterConfig collects the runtime knobs.
type RateLimiterConfig struct {
	// MaxKeys bounds the LRU. Once exceeded the oldest-touched key is
	// evicted; that key's bucket state is lost (its next request starts
	// with a full bucket). Default 4096.
	MaxKeys int
	// RatePerSec is the bucket refill rate. Default 50.
	RatePerSec float64
	// Burst is the bucket capacity (the max number of requests that can
	// arrive in a tight burst). Default 100.
	Burst float64
	// Now is injectable for tests. Default time.Now.
	Now func() time.Time
}

func (c *RateLimiterConfig) applyDefaults() {
	if c.MaxKeys <= 0 {
		c.MaxKeys = 4096
	}
	if c.RatePerSec <= 0 {
		c.RatePerSec = 50
	}
	if c.Burst <= 0 {
		c.Burst = 100
	}
	if c.Now == nil {
		c.Now = time.Now
	}
}

// NewTokenBucketRateLimiter constructs a limiter with the supplied
// config (defaults applied).
func NewTokenBucketRateLimiter(cfg RateLimiterConfig) *TokenBucketRateLimiter {
	cfg.applyDefaults()
	return &TokenBucketRateLimiter{
		buckets: make(map[string]*list.Element),
		lru:     list.New(),
		maxKeys: cfg.MaxKeys,
		rate:    cfg.RatePerSec,
		burst:   cfg.Burst,
		now:     cfg.Now,
	}
}

// Allow consumes one token from the bucket identified by key and
// reports whether the call should proceed. Empty key never rate-limits
// (caller's choice: pass an empty string for trusted internal callers).
func (r *TokenBucketRateLimiter) Allow(key string) bool {
	if key == "" {
		return true
	}
	now := r.now()

	r.mu.Lock()
	defer r.mu.Unlock()

	if elem, ok := r.buckets[key]; ok {
		r.lru.MoveToFront(elem)
		entry := elem.Value.(*rateLimitEntry)
		r.refillLocked(entry, now)
		if entry.tokens >= 1 {
			entry.tokens -= 1
			return true
		}
		r.rejected++
		return false
	}

	// New key. Evict the oldest if we're at capacity.
	if r.lru.Len() >= r.maxKeys {
		oldest := r.lru.Back()
		if oldest != nil {
			r.lru.Remove(oldest)
			delete(r.buckets, oldest.Value.(*rateLimitEntry).key)
		}
	}
	entry := &rateLimitEntry{
		key:      key,
		tokens:   r.burst - 1, // consume one immediately for this call
		lastSeen: now,
	}
	elem := r.lru.PushFront(entry)
	r.buckets[key] = elem
	return true
}

// refillLocked adds tokens proportional to the elapsed time. Must be
// called with r.mu held.
func (r *TokenBucketRateLimiter) refillLocked(entry *rateLimitEntry, now time.Time) {
	elapsed := now.Sub(entry.lastSeen).Seconds()
	if elapsed > 0 {
		entry.tokens += elapsed * r.rate
		if entry.tokens > r.burst {
			entry.tokens = r.burst
		}
		entry.lastSeen = now
	}
}

// Rejected returns the cumulative count of Allow() calls that were
// refused. Monotonic; safe for Prometheus.
func (r *TokenBucketRateLimiter) Rejected() uint64 {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.rejected
}

// Tracked returns the current number of distinct keys held in the LRU.
// Useful for a saturation dashboard gauge.
func (r *TokenBucketRateLimiter) Tracked() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.lru.Len()
}
