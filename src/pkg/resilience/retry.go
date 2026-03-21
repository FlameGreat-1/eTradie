package resilience

import (
	"context"
	"math"
	"math/rand"
	"time"
)

// RetryConfig holds parameters for exponential backoff retries
type RetryConfig struct {
	MaxRetries    int
	BaseDelay     time.Duration
	MaxDelay      time.Duration
	JitterPercent float64 // e.g., 0.2 for 20% jitter
}

// DefaultRetryConfig provides sensible defaults (used across Gateway/Execution/Management)
var DefaultRetryConfig = RetryConfig{
	MaxRetries:    3,
	BaseDelay:     500 * time.Millisecond,
	MaxDelay:      5 * time.Second,
	JitterPercent: 0.2,
}

// IsRetryable is a function that determines if an error is temporary and should be retried.
type IsRetryable func(error) bool

// Retry executes the given operation with exponential backoff.
// The operation operates within the provided context, stopping if the context is canceled.
func Retry(ctx context.Context, cfg RetryConfig, isRetryable IsRetryable, operation func() error) error {
	var err error
	for attempt := 0; attempt <= cfg.MaxRetries; attempt++ {
		err = operation()
		if err == nil {
			return nil // Success
		}

		if !isRetryable(err) || attempt == cfg.MaxRetries {
			return err // Non-retryable error or max retries reached
		}

		// Calculate backoff delay
		delay := calculateDelay(attempt, cfg)
		
		// Wait or bail if context is done
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(delay):
			// Continue to next attempt
		}
	}
	return err
}

func calculateDelay(attempt int, cfg RetryConfig) time.Duration {
	// Base exponential calculation
	delayF := float64(cfg.BaseDelay) * math.Pow(2, float64(attempt))
	
	// Apply max bounds
	if delayF > float64(cfg.MaxDelay) {
		delayF = float64(cfg.MaxDelay)
	}

	// Apply jitter (plus or minus JitterPercent)
	jitterMag := delayF * cfg.JitterPercent
	// rand.Float64() returns [0.0, 1.0). Scale to [-jitterMag, +jitterMag]
	jitter := (rand.Float64() * 2 * jitterMag) - jitterMag
	
	finalDelay := delayF + jitter
	if finalDelay < float64(cfg.BaseDelay) {
		finalDelay = float64(cfg.BaseDelay)
	}
	
	return time.Duration(finalDelay)
}
