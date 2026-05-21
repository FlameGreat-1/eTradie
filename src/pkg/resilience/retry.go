package resilience

import (
	"context"
	"math"
	"math/rand"
	"time"
)

// RetryConfig holds parameters for exponential backoff retries.
type RetryConfig struct {
	MaxRetries    int
	BaseDelay     time.Duration
	MaxDelay      time.Duration
	JitterPercent float64 // e.g., 0.2 for 20% jitter
}

// DefaultRetryConfig retries up to 3 times on transient infrastructure
// errors (connection drops, network timeouts). Suitable for lightweight,
// idempotent, infrastructure-level calls (health checks, metadata reads).
//
// DO NOT use for high-cost or non-idempotent operations such as LLM
// processor calls. Use NoRetryConfig or TransientRetryConfig for those.
var DefaultRetryConfig = RetryConfig{
	MaxRetries:    3,
	BaseDelay:     500 * time.Millisecond,
	MaxDelay:      5 * time.Second,
	JitterPercent: 0.2,
}

// TransientRetryConfig retries a maximum of 1 time, only on HTTP 502/503/504
// (upstream proxy or gateway unavailability). This is the correct policy for
// calls to the Python engine's internal endpoints:
//
//   - 502 Bad Gateway   → upstream proxy issue; safe to retry once.
//   - 503 Service Unavailable → engine starting up; safe to retry once.
//   - 504 Gateway Timeout → upstream read timeout; safe to retry once.
//   - 500 Internal Server Error → application error (e.g. LLM 429 quota);
//     NOT retried — retrying a failed LLM call wastes quota and worsens
//     the problem.
//
// Use this config for all engine HTTP calls that drive significant compute
// (TA collection, macro collection, RAG retrieval).
var TransientRetryConfig = RetryConfig{
	MaxRetries:    1,
	BaseDelay:     1 * time.Second,
	MaxDelay:      3 * time.Second,
	JitterPercent: 0.1,
}

// NoRetryConfig disables retries entirely. Use this for operations that are:
//
//   - High-cost: each attempt consumes significant resources (LLM tokens,
//     API quota, money). Retrying a failed LLM call on a 429/500 response
//     wastes quota and delays the error back to the caller.
//   - Non-idempotent: multiple calls may produce different side effects
//     (e.g. duplicate trade signals, double-published alerts).
//   - Caller-managed: the Orchestrator's RunCycle already has its own
//     cycle-level retry policy (MAX_CYCLE_RETRIES). Double-retrying at
//     the HTTP layer creates an uncontrolled retry storm.
//
// Specifically required for: /internal/processor/process.
var NoRetryConfig = RetryConfig{
	MaxRetries:    0,
	BaseDelay:     0,
	MaxDelay:      0,
	JitterPercent: 0,
}

// IsRetryable is a predicate that decides whether an error warrants a retry.
type IsRetryable func(error) bool

// Retry executes the given operation with exponential backoff.
// Stops immediately if ctx is cancelled or the isRetryable predicate
// returns false. When cfg.MaxRetries is 0, operation is called exactly once.
func Retry(ctx context.Context, cfg RetryConfig, isRetryable IsRetryable, operation func() error) error {
	var err error
	for attempt := 0; attempt <= cfg.MaxRetries; attempt++ {
		err = operation()
		if err == nil {
			return nil // Success.
		}

		if !isRetryable(err) || attempt == cfg.MaxRetries {
			return err // Non-retryable error or max retries reached.
		}

		// Calculate backoff delay.
		delay := calculateDelay(attempt, cfg)

		// Wait or bail if context is done.
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(delay):
			// Continue to next attempt.
		}
	}
	return err
}

func calculateDelay(attempt int, cfg RetryConfig) time.Duration {
	if cfg.BaseDelay == 0 {
		return 0
	}

	// Base exponential calculation.
	delayF := float64(cfg.BaseDelay) * math.Pow(2, float64(attempt))

	// Apply max bounds.
	if delayF > float64(cfg.MaxDelay) {
		delayF = float64(cfg.MaxDelay)
	}

	// Apply jitter (±JitterPercent).
	jitterMag := delayF * cfg.JitterPercent
	// rand.Float64() returns [0.0, 1.0). Scale to [-jitterMag, +jitterMag].
	jitter := (rand.Float64() * 2 * jitterMag) - jitterMag

	finalDelay := delayF + jitter
	if finalDelay < float64(cfg.BaseDelay) {
		finalDelay = float64(cfg.BaseDelay)
	}

	return time.Duration(finalDelay)
}
