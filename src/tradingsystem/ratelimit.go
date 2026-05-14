package tradingsystem

import (
	"sync"
	"time"
)

// userRateLimiter is a per-user sliding-window rate limiter. Unlike
// src/auth/ratelimit.go (which is IP-based and correct for public
// endpoints), this limiter keys on the authenticated user_id because
// the trading-system endpoints sit behind cookie auth and the IP axis
// would mistakenly share a budget across users on the same NAT.
//
// Safe for concurrent use. Ships a background-cleanup goroutine that
// reaps stale windows every 5 minutes. Call Close() during shutdown
// to terminate the goroutine cleanly.
type userRateLimiter struct {
	mu       sync.Mutex
	windows  map[string]*rlWindow
	limit    int
	interval time.Duration
	done     chan struct{}
}

type rlWindow struct {
	count   int
	resetAt time.Time
}

// newUserRateLimiter creates a rate limiter that allows `limit`
// requests per `interval` per user ID.
func newUserRateLimiter(limit int, interval time.Duration) *userRateLimiter {
	rl := &userRateLimiter{
		windows:  make(map[string]*rlWindow),
		limit:    limit,
		interval: interval,
		done:     make(chan struct{}),
	}
	go rl.cleanup()
	return rl
}

// Allow reports whether the given user_id is within budget. The first
// call from an unseen user opens a fresh window; subsequent calls
// within the interval increment the count until the limit is hit.
func (rl *userRateLimiter) Allow(userID string) bool {
	if userID == "" {
		// No identity to key on; defensively allow so an unauthenticated
		// path (which the middleware should already have rejected) never
		// hangs the legitimate user behind a phantom budget.
		return true
	}
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	w, exists := rl.windows[userID]
	if !exists || now.After(w.resetAt) {
		rl.windows[userID] = &rlWindow{
			count:   1,
			resetAt: now.Add(rl.interval),
		}
		return true
	}
	if w.count >= rl.limit {
		return false
	}
	w.count++
	return true
}

// Close stops the background cleanup goroutine.
func (rl *userRateLimiter) Close() {
	select {
	case <-rl.done:
		// already closed
	default:
		close(rl.done)
	}
}

func (rl *userRateLimiter) cleanup() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()
	for {
		select {
		case <-rl.done:
			return
		case <-ticker.C:
			rl.mu.Lock()
			now := time.Now()
			for uid, w := range rl.windows {
				if now.After(w.resetAt) {
					delete(rl.windows, uid)
				}
			}
			rl.mu.Unlock()
		}
	}
}
