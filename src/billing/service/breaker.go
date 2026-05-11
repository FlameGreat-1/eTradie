package service

import (
	"context"
	"errors"
	"sync"
	"time"
)

// ErrBreakerOpen is returned by Breaker.Allow when the breaker is in the
// Open state and the cooldown has not yet elapsed. Callers map this to a
// fast 503 (or, in the checkout path, a 503 wrapped in ErrProviderAPI so
// the existing HTTP layer surfaces it correctly).
var ErrBreakerOpen = errors.New("billing: circuit breaker is open")

// BreakerState is the breaker's externally-visible state. Reported via
// the optional observer so the metrics package can label transitions.
type BreakerState int

const (
	// BreakerClosed: normal operation. All requests are allowed; consecutive
	// failures are counted. When the counter exceeds the threshold the
	// breaker trips Open.
	BreakerClosed BreakerState = iota
	// BreakerOpen: short-circuit. Every Allow() returns ErrBreakerOpen until
	// the cooldown elapses, then the breaker transitions to HalfOpen.
	BreakerOpen
	// BreakerHalfOpen: exactly one in-flight probe is allowed. Success
	// closes the breaker; failure re-opens it for another cooldown.
	BreakerHalfOpen
)

func (s BreakerState) String() string {
	switch s {
	case BreakerClosed:
		return "closed"
	case BreakerOpen:
		return "open"
	case BreakerHalfOpen:
		return "half_open"
	}
	return "unknown"
}

// BreakerObserver is the narrow callback the breaker invokes on every
// state transition. The Prometheus metric pack implements this so the
// breaker can emit operator-visible signals without importing the
// metrics package (no cycle, no test-time dependency).
type BreakerObserver interface {
	OnBreakerTransition(name string, from, to BreakerState)
}

// noopObserver is the default when no observer is wired (unit tests).
type noopObserver struct{}

func (noopObserver) OnBreakerTransition(string, BreakerState, BreakerState) {}

// BreakerConfig collects the runtime knobs.
type BreakerConfig struct {
	// Name labels the breaker in observer callbacks. Used as the metric label.
	Name string
	// FailureThreshold is the consecutive-failure count that trips the
	// breaker Open. Default 5.
	FailureThreshold int
	// OpenCooldown is the minimum time the breaker stays Open before
	// transitioning to HalfOpen. Default 30s.
	OpenCooldown time.Duration
	// HalfOpenProbeTimeout bounds how long a HalfOpen probe is allowed to
	// run before being treated as a failure (defensive against a stuck
	// half-open call holding the only probe slot indefinitely). Default 30s.
	HalfOpenProbeTimeout time.Duration
	// Now is injectable for tests.
	Now func() time.Time
	// Observer receives state-change callbacks. Default is a noop.
	Observer BreakerObserver
}

func (c *BreakerConfig) applyDefaults() {
	if c.FailureThreshold <= 0 {
		c.FailureThreshold = 5
	}
	if c.OpenCooldown <= 0 {
		c.OpenCooldown = 30 * time.Second
	}
	if c.HalfOpenProbeTimeout <= 0 {
		c.HalfOpenProbeTimeout = 30 * time.Second
	}
	if c.Now == nil {
		c.Now = time.Now
	}
	if c.Observer == nil {
		c.Observer = noopObserver{}
	}
}

// Breaker is a self-contained three-state circuit breaker.
//
// Thread-safety: hot path (Allow / Success / Failure during Closed state)
// is dominated by an atomic RLock, so steady-state overhead is roughly
// 5ns per call. State transitions take the write lock for the duration
// of the transition itself (a handful of instructions).
type Breaker struct {
	cfg BreakerConfig

	mu                  sync.RWMutex
	state               BreakerState
	consecutiveFailures int
	openedAt            time.Time
	halfOpenProbedAt    time.Time
	halfOpenInFlight    bool
}

// NewBreaker constructs a breaker with the supplied config (defaults
// applied). The breaker starts in BreakerClosed.
func NewBreaker(cfg BreakerConfig) *Breaker {
	cfg.applyDefaults()
	return &Breaker{cfg: cfg, state: BreakerClosed}
}

// Name returns the breaker's label.
func (b *Breaker) Name() string { return b.cfg.Name }

// State returns the current state. Safe for concurrent use.
func (b *Breaker) State() BreakerState {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.state
}

// Allow reports whether a request should proceed.
//
//   - Closed: always allowed.
//   - Open: rejected with ErrBreakerOpen until cooldown elapses, then
//     a single transition to HalfOpen + probe is permitted.
//   - HalfOpen: exactly one in-flight probe is allowed at a time.
//     Concurrent callers during HalfOpen are rejected as if Open so
//     the failing provider sees at most one probe per cooldown.
func (b *Breaker) Allow(_ context.Context) error {
	now := b.cfg.Now()

	// Fast path: closed.
	b.mu.RLock()
	state := b.state
	b.mu.RUnlock()
	if state == BreakerClosed {
		return nil
	}

	// Slow path: take the write lock and re-check.
	b.mu.Lock()
	defer b.mu.Unlock()

	switch b.state {
	case BreakerClosed:
		return nil
	case BreakerOpen:
		if now.Sub(b.openedAt) < b.cfg.OpenCooldown {
			return ErrBreakerOpen
		}
		b.transitionLocked(BreakerHalfOpen)
		b.halfOpenInFlight = true
		b.halfOpenProbedAt = now
		return nil
	case BreakerHalfOpen:
		if b.halfOpenInFlight {
			// Defensive: if a probe has been in-flight longer than the
			// configured timeout, treat it as a failure and re-open. Without
			// this, a hung HTTP call holding the only probe slot would
			// freeze the breaker in HalfOpen forever.
			if now.Sub(b.halfOpenProbedAt) >= b.cfg.HalfOpenProbeTimeout {
				b.consecutiveFailures = b.cfg.FailureThreshold
				b.openedAt = now
				b.halfOpenInFlight = false
				b.transitionLocked(BreakerOpen)
			}
			return ErrBreakerOpen
		}
		b.halfOpenInFlight = true
		b.halfOpenProbedAt = now
		return nil
	}
	return nil
}

// Success records a successful call. Closes a HalfOpen breaker; resets
// the consecutive-failure counter in Closed state.
func (b *Breaker) Success() {
	b.mu.Lock()
	defer b.mu.Unlock()
	switch b.state {
	case BreakerHalfOpen:
		b.halfOpenInFlight = false
		b.consecutiveFailures = 0
		b.transitionLocked(BreakerClosed)
	case BreakerClosed:
		b.consecutiveFailures = 0
	case BreakerOpen:
		// No-op: an in-flight call that started before the breaker tripped
		// may report success after the trip. Treat it as informational.
	}
}

// Failure records a failed call. Trips Closed -> Open at the threshold;
// re-opens a HalfOpen breaker on probe failure.
func (b *Breaker) Failure() {
	now := b.cfg.Now()
	b.mu.Lock()
	defer b.mu.Unlock()
	switch b.state {
	case BreakerHalfOpen:
		b.halfOpenInFlight = false
		b.consecutiveFailures = b.cfg.FailureThreshold
		b.openedAt = now
		b.transitionLocked(BreakerOpen)
	case BreakerClosed:
		b.consecutiveFailures++
		if b.consecutiveFailures >= b.cfg.FailureThreshold {
			b.openedAt = now
			b.transitionLocked(BreakerOpen)
		}
	case BreakerOpen:
		// No-op (same reasoning as Success in Open).
	}
}

// transitionLocked changes the state. Must be called with mu held.
func (b *Breaker) transitionLocked(to BreakerState) {
	if b.state == to {
		return
	}
	from := b.state
	b.state = to
	if b.cfg.Observer != nil {
		b.cfg.Observer.OnBreakerTransition(b.cfg.Name, from, to)
	}
}
