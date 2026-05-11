package service

import (
	"context"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// fakeClock is a monotonically advanceable clock for breaker tests.
type fakeClock struct {
	mu  sync.Mutex
	now time.Time
}

func newFakeClock() *fakeClock {
	return &fakeClock{now: time.Unix(1_700_000_000, 0).UTC()}
}

func (c *fakeClock) Now() time.Time {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.now
}

func (c *fakeClock) Advance(d time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.now = c.now.Add(d)
}

// recordingObserver counts state transitions for assertions.
type recordingObserver struct {
	mu          sync.Mutex
	transitions []string
}

func (r *recordingObserver) OnBreakerTransition(name string, from, to BreakerState) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.transitions = append(r.transitions, from.String()+"->"+to.String())
}

func (r *recordingObserver) snapshot() []string {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]string, len(r.transitions))
	copy(out, r.transitions)
	return out
}

func TestBreaker_TripsAfterThreshold(t *testing.T) {
	clock := newFakeClock()
	obs := &recordingObserver{}
	b := NewBreaker(BreakerConfig{
		Name:                 "test",
		FailureThreshold:     3,
		OpenCooldown:         10 * time.Second,
		HalfOpenProbeTimeout: 5 * time.Second,
		Now:                  clock.Now,
		Observer:             obs,
	})

	ctx := context.Background()
	for i := 0; i < 2; i++ {
		if err := b.Allow(ctx); err != nil {
			t.Fatalf("Allow #%d: %v", i, err)
		}
		b.Failure()
	}
	if b.State() != BreakerClosed {
		t.Fatalf("want Closed after 2 failures, got %s", b.State())
	}

	if err := b.Allow(ctx); err != nil {
		t.Fatalf("Allow #3: %v", err)
	}
	b.Failure()
	if b.State() != BreakerOpen {
		t.Fatalf("want Open after threshold reached, got %s", b.State())
	}

	if err := b.Allow(ctx); err != ErrBreakerOpen {
		t.Fatalf("want ErrBreakerOpen during cooldown, got %v", err)
	}
}

func TestBreaker_CooldownThenHalfOpenProbeSucceeds(t *testing.T) {
	clock := newFakeClock()
	b := NewBreaker(BreakerConfig{
		Name:                 "test",
		FailureThreshold:     1,
		OpenCooldown:         10 * time.Second,
		HalfOpenProbeTimeout: 5 * time.Second,
		Now:                  clock.Now,
	})

	ctx := context.Background()
	_ = b.Allow(ctx)
	b.Failure() // trips Open
	if b.State() != BreakerOpen {
		t.Fatalf("want Open, got %s", b.State())
	}

	clock.Advance(11 * time.Second)
	if err := b.Allow(ctx); err != nil {
		t.Fatalf("want HalfOpen probe to be allowed, got %v", err)
	}
	if b.State() != BreakerHalfOpen {
		t.Fatalf("want HalfOpen during probe, got %s", b.State())
	}
	b.Success()
	if b.State() != BreakerClosed {
		t.Fatalf("want Closed after probe success, got %s", b.State())
	}
}

func TestBreaker_HalfOpenSingleProbeOnly(t *testing.T) {
	clock := newFakeClock()
	b := NewBreaker(BreakerConfig{
		Name:                 "test",
		FailureThreshold:     1,
		OpenCooldown:         10 * time.Second,
		HalfOpenProbeTimeout: 5 * time.Second,
		Now:                  clock.Now,
	})

	ctx := context.Background()
	_ = b.Allow(ctx)
	b.Failure()
	clock.Advance(11 * time.Second)

	// First Allow transitions to HalfOpen.
	if err := b.Allow(ctx); err != nil {
		t.Fatalf("first probe: %v", err)
	}
	// Subsequent concurrent Allow is rejected as if Open.
	if err := b.Allow(ctx); err != ErrBreakerOpen {
		t.Fatalf("want ErrBreakerOpen for concurrent probe, got %v", err)
	}
}

func TestBreaker_HalfOpenProbeTimeoutReOpens(t *testing.T) {
	clock := newFakeClock()
	b := NewBreaker(BreakerConfig{
		Name:                 "test",
		FailureThreshold:     1,
		OpenCooldown:         10 * time.Second,
		HalfOpenProbeTimeout: 5 * time.Second,
		Now:                  clock.Now,
	})

	ctx := context.Background()
	_ = b.Allow(ctx)
	b.Failure()
	clock.Advance(11 * time.Second)
	_ = b.Allow(ctx) // enters HalfOpen, probe in-flight

	clock.Advance(6 * time.Second) // exceeds HalfOpenProbeTimeout
	if err := b.Allow(ctx); err != ErrBreakerOpen {
		t.Fatalf("want ErrBreakerOpen after probe timeout, got %v", err)
	}
	if b.State() != BreakerOpen {
		t.Fatalf("want Open after timed-out probe, got %s", b.State())
	}
}

func TestBreaker_ConcurrentAllowSafe(t *testing.T) {
	// Smoke test: 1000 goroutines hitting Allow + Success in Closed
	// state must not deadlock or race. Run under -race.
	b := NewBreaker(BreakerConfig{
		Name:             "test",
		FailureThreshold: 100,
	})
	var wg sync.WaitGroup
	var count atomic.Int64
	for i := 0; i < 1000; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if err := b.Allow(context.Background()); err == nil {
				b.Success()
				count.Add(1)
			}
		}()
	}
	wg.Wait()
	if count.Load() != 1000 {
		t.Fatalf("want 1000 allowed in Closed steady state, got %d", count.Load())
	}
}
