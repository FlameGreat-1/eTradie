package auth

import (
	"context"
	"testing"
	"time"
)

func TestLockoutDurationForFailures(t *testing.T) {
	if d := LockoutDurationForFailures(LockoutThreshold - 1); d != 0 {
		t.Fatalf("below threshold should be 0, got %v", d)
	}
	if d := LockoutDurationForFailures(LockoutThreshold); d != LockoutBaseDuration {
		t.Fatalf("at threshold should be base %v, got %v", LockoutBaseDuration, d)
	}
	// One past threshold doubles the base (still under the cap).
	if d := LockoutDurationForFailures(LockoutThreshold + 1); d != 2*LockoutBaseDuration {
		t.Fatalf("threshold+1 should be 2*base %v, got %v", 2*LockoutBaseDuration, d)
	}
	// Far past threshold is capped at max.
	if d := LockoutDurationForFailures(LockoutThreshold + 100); d != LockoutMaxDuration {
		t.Fatalf("large failure count should cap at %v, got %v", LockoutMaxDuration, d)
	}
}

func TestLockoutCounterWindowMillis(t *testing.T) {
	if got, want := LockoutCounterWindowMillis(), LockoutCounterWindow.Milliseconds(); got != want {
		t.Fatalf("millis helper = %d, want %d", got, want)
	}
}

func TestDevAttemptLimiter_RateBudget(t *testing.T) {
	lim := NewDevAttemptLimiter()
	ctx := context.Background()
	// ScopeRegister budget is 5/min in the dev limiter.
	for i := 0; i < 5; i++ {
		if ok, _ := lim.AllowRequest(ctx, ScopeRegister, "1.2.3.4"); !ok {
			t.Fatalf("request %d should be allowed within budget", i+1)
		}
	}
	if ok, retry := lim.AllowRequest(ctx, ScopeRegister, "1.2.3.4"); ok || retry <= 0 {
		t.Fatalf("6th request should be denied with a positive retry-after, ok=%v retry=%v", ok, retry)
	}
	// A different key has its own window.
	if ok, _ := lim.AllowRequest(ctx, ScopeRegister, "5.6.7.8"); !ok {
		t.Fatalf("a different IP should have an independent budget")
	}
}

func TestDevAttemptLimiter_LockoutLifecycle(t *testing.T) {
	lim := NewDevAttemptLimiter()
	ctx := context.Background()
	const acct = "alice"

	if locked, _ := lim.IsLocked(ctx, acct); locked {
		t.Fatalf("account should start unlocked")
	}
	// Fail up to (threshold-1): still unlocked.
	for i := 0; i < LockoutThreshold-1; i++ {
		if locked, _ := lim.RegisterFailure(ctx, acct); locked {
			t.Fatalf("locked too early at failure %d", i+1)
		}
	}
	// The threshold failure locks.
	locked, retry := lim.RegisterFailure(ctx, acct)
	if !locked || retry <= 0 {
		t.Fatalf("threshold failure should lock with positive retry, locked=%v retry=%v", locked, retry)
	}
	if l, _ := lim.IsLocked(ctx, acct); !l {
		t.Fatalf("IsLocked should report locked after threshold")
	}
	// Reset clears it.
	lim.ResetFailures(ctx, acct)
	if l, _ := lim.IsLocked(ctx, acct); l {
		t.Fatalf("ResetFailures should clear the lock")
	}
	_ = time.Second
}
