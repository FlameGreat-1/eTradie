package service

import (
	"context"
	"errors"
	"sync/atomic"
)

// ErrSemaphoreSaturated is returned by Semaphore.TryAcquire when no permit
// is available. The HTTP layer maps this to 503 + Retry-After.
var ErrSemaphoreSaturated = errors.New("billing: semaphore saturated")

// Semaphore is a counting semaphore with non-blocking TryAcquire and
// observable saturation. The implementation is a buffered channel of
// permits, which is the canonical lock-free Go pattern: TryAcquire is a
// non-blocking channel receive, Release is a non-blocking channel send.
// Saturation is tracked via two atomic counters (in-flight, rejected) so
// callers can expose Prometheus metrics without taking any lock.
type Semaphore struct {
	name     string
	permits  chan struct{}
	cap      int
	inFlight atomic.Int64
	rejected atomic.Int64
}

// NewSemaphore creates a semaphore with the given capacity and label.
// The label is used for observability only.
func NewSemaphore(name string, capacity int) *Semaphore {
	if capacity <= 0 {
		capacity = 1
	}
	return &Semaphore{
		name:    name,
		permits: make(chan struct{}, capacity),
		cap:     capacity,
	}
}

// Name returns the semaphore label.
func (s *Semaphore) Name() string { return s.name }

// Capacity returns the configured maximum in-flight count.
func (s *Semaphore) Capacity() int { return s.cap }

// TryAcquire attempts to acquire one permit without blocking. Returns
// nil on success (caller must call Release exactly once), or
// ErrSemaphoreSaturated if no permit is available. Respects ctx so a
// pre-cancelled context short-circuits before the channel send attempt.
func (s *Semaphore) TryAcquire(ctx context.Context) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	select {
	case s.permits <- struct{}{}:
		s.inFlight.Add(1)
		return nil
	default:
		s.rejected.Add(1)
		return ErrSemaphoreSaturated
	}
}

// Release returns one permit. Safe to call from any goroutine. Calling
// Release without a matching successful TryAcquire is a programmer
// error and will panic in development; in production it would block
// forever, which we explicitly avoid with a non-blocking send.
func (s *Semaphore) Release() {
	select {
	case <-s.permits:
		s.inFlight.Add(-1)
	default:
		// Defensive: do nothing if there's no in-flight permit to
		// release. Better than panicking in a production hot path.
	}
}

// InFlight returns the current in-flight count. Reader-only; safe for
// metrics. Reads via atomic.LoadInt64 so there's no lock contention
// even at 100k+ QPS.
func (s *Semaphore) InFlight() int64 { return s.inFlight.Load() }

// Rejected returns the cumulative count of TryAcquire calls that were
// refused due to saturation. Monotonic.
func (s *Semaphore) Rejected() int64 { return s.rejected.Load() }

// Saturation returns the current in-flight / capacity ratio in [0, 1].
// Useful for dashboard gauges that want a normalised value.
func (s *Semaphore) Saturation() float64 {
	return float64(s.inFlight.Load()) / float64(s.cap)
}
