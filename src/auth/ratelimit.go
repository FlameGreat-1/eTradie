package auth

import (
	"net"
	"net/http"
	"sync"
	"time"
)

// RateLimiter provides IP-based rate limiting for auth endpoints.
// Uses a sliding window counter per IP address with automatic cleanup
// of stale entries. Safe for concurrent use.
type RateLimiter struct {
	mu       sync.Mutex
	windows  map[string]*window
	limit    int
	interval time.Duration
	done     chan struct{}
}

type window struct {
	count   int
	resetAt time.Time
}

// NewRateLimiter creates a rate limiter that allows `limit` requests
// per `interval` per IP address.
func NewRateLimiter(limit int, interval time.Duration) *RateLimiter {
	rl := &RateLimiter{
		windows:  make(map[string]*window),
		limit:    limit,
		interval: interval,
		done:     make(chan struct{}),
	}
	// Background cleanup of stale entries every 5 minutes.
	go rl.cleanup()
	return rl
}

// Allow checks if the given IP is within the rate limit.
// Returns true if the request is allowed, false if rate limited.
func (rl *RateLimiter) Allow(ip string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	w, exists := rl.windows[ip]

	if !exists || now.After(w.resetAt) {
		// New window.
		rl.windows[ip] = &window{
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

// RateLimitMiddlewareWithResolver wraps an http.HandlerFunc with rate
// limiting. The rate-limit identity is resolved via the supplied
// ClientIPResolver, which honours forwarding headers only from
// trusted proxies. Returns 429 Too Many Requests when the limit is
// exceeded.
func (rl *RateLimiter) RateLimitMiddlewareWithResolver(resolver *ClientIPResolver, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ip := resolver.Resolve(r)
		if !rl.Allow(ip) {
			w.Header().Set("Retry-After", "60")
			writeAuthError(w, http.StatusTooManyRequests, "rate limit exceeded, try again later")
			return
		}
		next(w, r)
	}
}

// RateLimitMiddleware wraps an http.HandlerFunc with rate limiting
// using a safe default identity: the immediate connection peer.
// Forwarding headers are NOT honoured because no resolver was
// supplied, which prevents header spoofing in any caller that has not
// yet been wired through Config.IPResolver(). Returns 429 Too Many
// Requests when the limit is exceeded.
//
// Prefer RateLimitMiddlewareWithResolver in new code.
func (rl *RateLimiter) RateLimitMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ip := peerOnly(r.RemoteAddr)
		if !rl.Allow(ip) {
			w.Header().Set("Retry-After", "60")
			writeAuthError(w, http.StatusTooManyRequests, "rate limit exceeded, try again later")
			return
		}
		next(w, r)
	}
}

// peerOnly returns the host portion of a RemoteAddr, falling back to
// the raw value if it cannot be parsed. Mirrors the safe path of the
// trust-aware resolver's untrusted-peer branch.
func peerOnly(remoteAddr string) string {
	if remoteAddr == "" {
		return remoteAddr
	}
	host, _, err := net.SplitHostPort(remoteAddr)
	if err != nil {
		return remoteAddr
	}
	return host
}

// Close stops the background cleanup goroutine.
// Must be called during graceful shutdown to prevent goroutine leaks.
func (rl *RateLimiter) Close() {
	close(rl.done)
}

func (rl *RateLimiter) cleanup() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()
	for {
		select {
		case <-rl.done:
			return
		case <-ticker.C:
			rl.mu.Lock()
			now := time.Now()
			for ip, w := range rl.windows {
				if now.After(w.resetAt) {
					delete(rl.windows, ip)
				}
			}
			rl.mu.Unlock()
		}
	}
}
