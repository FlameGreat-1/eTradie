package auth

import (
	"context"
	"sync"
	"time"
)

// AttemptLimiter is the abuse-control contract the authentication
// endpoints depend on. It covers TWO distinct controls:
//
//   1. A cluster-wide sliding-window RATE LIMIT keyed by (scope, key)
//      — e.g. scope="login", key=<client IP> — so the limit is shared
//      across every gateway replica instead of being per-pod.
//
//   2. Per-ACCOUNT LOCKOUT: a failed-login counter keyed by the
//      account identifier (username, lowercased) that locks the
//      account for an exponentially-growing window after a threshold
//      of consecutive failures, defeating online password guessing
//      against a known username even from rotating IPs.
//
// The interface lives in the auth package so the dependency arrow
// points IN: the gateway implements it with Redis (cluster-wide,
// production) and injects it via Handler.WithAttemptLimiter. The auth
// package never imports gateway/infra. A service that does not serve
// the login routes (e.g. execution) simply never wires or calls a
// limiter.
type AttemptLimiter interface {
	// AllowRequest records one hit for (scope, key) and reports whether
	// it is within the configured rate for that scope. When denied it
	// returns the suggested Retry-After. Implementations MUST be atomic
	// across replicas (e.g. Redis INCR+EXPIRE) so the limit is global.
	AllowRequest(ctx context.Context, scope, key string) (allowed bool, retryAfter time.Duration)

	// IsLocked reports whether the account is currently locked out and,
	// if so, the remaining lock duration. Called BEFORE a password
	// verify so a locked account costs no hash computation.
	IsLocked(ctx context.Context, accountKey string) (locked bool, retryAfter time.Duration)

	// RegisterFailure records one failed login for the account and
	// returns whether the account is now locked and for how long.
	RegisterFailure(ctx context.Context, accountKey string) (locked bool, retryAfter time.Duration)

	// ResetFailures clears the failed-login counter for the account.
	// Called on a successful login.
	ResetFailures(ctx context.Context, accountKey string)
}

// Rate-limit scopes. Stable strings; the Redis implementation namespaces
// its keys with these so different routes have independent windows.
const (
	ScopeLogin    = "login"
	ScopeRegister = "register"
	ScopeRefresh  = "refresh"
)

// LockoutPolicy parameters. Exported so the Redis implementation and
// any test reuse the exact same numbers (no drift between the contract
// and the implementation).
const (
	// LockoutThreshold is the number of consecutive failed logins that
	// triggers a lock.
	LockoutThreshold = 5

	// LockoutBaseDuration is the first lock window once the threshold is
	// reached. Each additional failure past the threshold doubles the
	// window up to LockoutMaxDuration.
	LockoutBaseDuration = 1 * time.Minute

	// LockoutMaxDuration caps the exponential backoff so a sustained
	// attack does not lock a legitimate user out for an unbounded time.
	LockoutMaxDuration = 15 * time.Minute

	// LockoutCounterWindow is how long the failed-attempt counter
	// survives without a new failure. A user who fails twice, waits,
	// and comes back fresh is not penalised for stale failures.
	LockoutCounterWindow = 15 * time.Minute
)

// lockoutDurationFor returns the lock window for a given consecutive
// failure count. Shared by every AttemptLimiter implementation so the
// backoff curve is identical in dev and prod.
//
//   failures <  threshold      -> 0 (not locked)
//   failures == threshold      -> base
//   each failure beyond         -> base * 2^(n) capped at max
func lockoutDurationFor(failures int) time.Duration {
	if failures < LockoutThreshold {
		return 0
	}
	over := failures - LockoutThreshold // 0,1,2,...
	d := LockoutBaseDuration
	for i := 0; i < over; i++ {
		d *= 2
		if d >= LockoutMaxDuration {
			return LockoutMaxDuration
		}
	}
	if d > LockoutMaxDuration {
		d = LockoutMaxDuration
	}
	return d
}

// ---------------------------------------------------------------------------
// Dev/test-only in-memory implementation
// ---------------------------------------------------------------------------

// devInMemoryAttemptLimiter is a single-process AttemptLimiter for
// local development and unit tests ONLY. It is NEVER selected in
// production/staging: the gateway wiring requires the Redis-backed
// implementation there and fails fast if it is absent. Construction is
// loud (the caller logs a warning) so its use can never be silent.
type devInMemoryAttemptLimiter struct {
	mu       sync.Mutex
	rate     map[string]*rlWindow // scope:key -> sliding window
	failures map[string]*failEntry // accountKey -> failure state
	ratePer  map[string]int        // scope -> max per window
	window   time.Duration
}

type rlWindow struct {
	count   int
	resetAt time.Time
}

type failEntry struct {
	count     int
	lockUntil time.Time
	updatedAt time.Time
}

// newDevInMemoryAttemptLimiter builds the dev limiter with the same
// per-scope request budgets the production limiter uses.
func newDevInMemoryAttemptLimiter() *devInMemoryAttemptLimiter {
	return &devInMemoryAttemptLimiter{
		rate:     make(map[string]*rlWindow),
		failures: make(map[string]*failEntry),
		ratePer: map[string]int{
			ScopeLogin:    10,
			ScopeRegister: 5,
			ScopeRefresh:  20,
		},
		window: time.Minute,
	}
}

func (d *devInMemoryAttemptLimiter) AllowRequest(_ context.Context, scope, key string) (bool, time.Duration) {
	d.mu.Lock()
	defer d.mu.Unlock()
	limit, ok := d.ratePer[scope]
	if !ok {
		limit = 10
	}
	now := time.Now()
	k := scope + ":" + key
	w, exists := d.rate[k]
	if !exists || now.After(w.resetAt) {
		d.rate[k] = &rlWindow{count: 1, resetAt: now.Add(d.window)}
		return true, 0
	}
	if w.count >= limit {
		return false, time.Until(w.resetAt)
	}
	w.count++
	return true, 0
}

func (d *devInMemoryAttemptLimiter) IsLocked(_ context.Context, accountKey string) (bool, time.Duration) {
	d.mu.Lock()
	defer d.mu.Unlock()
	e, ok := d.failures[accountKey]
	if !ok {
		return false, 0
	}
	if now := time.Now(); now.Before(e.lockUntil) {
		return true, time.Until(e.lockUntil)
	}
	return false, 0
}

func (d *devInMemoryAttemptLimiter) RegisterFailure(_ context.Context, accountKey string) (bool, time.Duration) {
	d.mu.Lock()
	defer d.mu.Unlock()
	now := time.Now()
	e, ok := d.failures[accountKey]
	if !ok || now.Sub(e.updatedAt) > LockoutCounterWindow {
		e = &failEntry{}
		d.failures[accountKey] = e
	}
	e.count++
	e.updatedAt = now
	if d := lockoutDurationFor(e.count); d > 0 {
		e.lockUntil = now.Add(d)
		return true, d
	}
	return false, 0
}

func (d *devInMemoryAttemptLimiter) ResetFailures(_ context.Context, accountKey string) {
	d.mu.Lock()
	defer d.mu.Unlock()
	delete(d.failures, accountKey)
}

// NewDevAttemptLimiter returns an explicit dev/test in-memory
// AttemptLimiter. Exported for the gateway wiring (dev branch) and for
// tests. Production wiring must NOT call this; it must inject the
// Redis-backed implementation.
func NewDevAttemptLimiter() AttemptLimiter {
	return newDevInMemoryAttemptLimiter()
}
