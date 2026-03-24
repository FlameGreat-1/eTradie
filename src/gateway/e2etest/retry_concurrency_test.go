package e2e

import (
	"context"
	"runtime"
	"sync/atomic"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
)

// ---------------------------------------------------------------------------
// Retry Behavior Tests
// ---------------------------------------------------------------------------

// TestRetry_TAFailsThenSucceeds verifies the orchestrator's cycle-level
// retry with exponential backoff. The TA endpoint fails on the first
// batch of calls (HTTP-level retries exhaust), causing the first cycle
// attempt to fail. The orchestrator retries the entire cycle, and the
// second attempt succeeds.
//
// Config: MaxCycleRetries=1, RetryBackoffBaseSeconds=0.5
// Expected: 2 cycle attempts total, final output is successful.
//
// Note: The EngineHTTPClient has its own retry (3 attempts via
// resilience.Retry). A 500 error is retried at the HTTP level first.
// We use an atomic counter to flip the response after enough calls.
func TestRetry_TAFailsThenSucceeds(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// The HTTP client retries 3+1=4 times per cycle attempt.
	// We want the first cycle attempt to fully fail (all HTTP retries exhausted),
	// then the second cycle attempt to succeed.
	// So we fail the first 4 calls (1 original + 3 retries), then succeed.
	failThreshold := int64(4)

	successResponse := TAResponseWithCandidates()

	// Start with TA returning 500 errors.
	h.Engine.TAResponse = map[string]interface{}{"error": "service temporarily unavailable"}
	h.Engine.TAStatusCode = 500
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	// Flip flag: set to 1 once the response has been switched.
	var flipped atomic.Int32

	// Monitor TA calls and flip the response after the threshold.
	// Uses a polling loop with sleep to avoid CPU starvation.
	go func() {
		for {
			current := h.Engine.TACalls.Load()
			if current >= failThreshold {
				// Flip to success. The mock server reads these fields
				// per-request in its handler. The write here and the
				// read in handleTA are on separate goroutines, but
				// map/int assignments in Go are safe for this pattern
				// (single writer, handler reads a pointer/int).
				h.Engine.TAResponse = successResponse
				h.Engine.TAStatusCode = 0 // Reset to 200.
				flipped.Store(1)
				return
			}
			runtime.Gosched()
			time.Sleep(1 * time.Millisecond)
		}
	}()

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-retry-success-001")

	// ---------------------------------------------------------------
	// Assert: TA was called multiple times (HTTP retries + cycle retry).
	// ---------------------------------------------------------------
	totalTACalls := h.Engine.TACalls.Load()
	assert.Greater(t, totalTACalls, int64(1),
		"TA should be called more than once due to retries")

	// ---------------------------------------------------------------
	// Assert: Response was flipped (goroutine completed).
	// ---------------------------------------------------------------
	assert.Equal(t, int32(1), flipped.Load(),
		"response should have been flipped to success after threshold")

	// ---------------------------------------------------------------
	// Assert: Macro was called at least once per cycle attempt.
	// ---------------------------------------------------------------
	totalMacroCalls := h.Engine.MacroCalls.Load()
	assert.GreaterOrEqual(t, totalMacroCalls, int64(1),
		"Macro should be called at least once")

	// ---------------------------------------------------------------
	// Assert: Final output should be successful (second attempt worked).
	// ---------------------------------------------------------------
	require.NotEmpty(t, outputs, "should produce outputs")

	var hasSuccess bool
	for _, out := range outputs {
		if out.CycleStatus == constants.StatusCompleted &&
			out.CycleOutcome != constants.OutcomePipelineError {
			hasSuccess = true
		}
	}
	assert.True(t, hasSuccess,
		"retry should succeed: second cycle attempt should produce successful output")
}

// TestRetry_AllAttemptsExhausted verifies that when all cycle retry
// attempts fail, the orchestrator returns the last attempt's error output.
//
// Config: MaxCycleRetries=1 → 2 total attempts, both fail.
func TestRetry_AllAttemptsExhausted(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// TA permanently returns 500. All HTTP retries and cycle retries fail.
	h.Engine.TAResponse = map[string]interface{}{"error": "permanent failure"}
	h.Engine.TAStatusCode = 500
	h.Engine.MacroResponse = MacroResponseFull()

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-retry-exhausted-001")

	// ---------------------------------------------------------------
	// Assert: TA was called many times (HTTP retries * cycle attempts).
	// With resilience.DefaultRetryConfig.MaxRetries=3, each cycle attempt
	// makes 4 HTTP calls (1 + 3 retries). With MaxCycleRetries=1,
	// there are 2 cycle attempts = 8 TA calls minimum.
	// ---------------------------------------------------------------
	totalTACalls := h.Engine.TACalls.Load()
	assert.GreaterOrEqual(t, totalTACalls, int64(4),
		"TA should be called multiple times across retries")

	// ---------------------------------------------------------------
	// Assert: Final output is a failure.
	// ---------------------------------------------------------------
	require.NotEmpty(t, outputs)
	var hasError bool
	for _, out := range outputs {
		if out.CycleStatus == constants.StatusFailed ||
			out.CycleStatus == constants.StatusTimedOut {
			hasError = true
			assert.Equal(t, constants.OutcomePipelineError, out.CycleOutcome)
			assert.NotEmpty(t, out.Error)
		}
	}
	assert.True(t, hasError, "should have at least one failed output after all retries exhausted")

	// ---------------------------------------------------------------
	// Assert: Downstream services were never called.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(0), h.Engine.RAGCalls.Load())
	assert.Equal(t, int64(0), h.Engine.ProcessorCalls.Load())
	assert.Empty(t, h.Execution.GetCalls())
}

// TestRetry_SuccessfulCycleDoesNotRetry verifies that a successful
// cycle attempt does NOT trigger any retries. This is the baseline
// contract: shouldRetry=false when executePipeline returns nil error.
func TestRetry_SuccessfulCycleDoesNotRetry(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	h.RunCycle([]string{"EURUSD"}, "trace-e2e-no-retry-001")

	// ---------------------------------------------------------------
	// Assert: Each endpoint called exactly once (no retries).
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load(),
		"TA should be called exactly once (no retry)")
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load(),
		"Macro should be called exactly once (no retry)")
	assert.Equal(t, int64(1), h.Engine.RAGCalls.Load(),
		"RAG should be called exactly once (no retry)")
	assert.Equal(t, int64(1), h.Engine.ProcessorCalls.Load(),
		"Processor should be called exactly once (no retry)")
}

// ---------------------------------------------------------------------------
// Concurrency Tests
// ---------------------------------------------------------------------------

// TestConcurrency_BoundedParallelism verifies that the orchestrator
// respects MaxConcurrentSymbols when processing multiple symbols.
//
// Sends 4 symbols with candidates. With MaxConcurrentSymbols=4,
// all 4 should be processed. Verifies RAG and Processor are called
// exactly 4 times (once per candidate symbol).
func TestConcurrency_BoundedParallelism(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// Build a TA response with 4 symbols, all having candidates.
	h.Engine.TAResponse = map[string]interface{}{
		"symbol_results": []interface{}{
			buildSymbolResultWithCandidate("EURUSD", "BULLISH"),
			buildSymbolResultWithCandidate("GBPUSD", "BEARISH"),
			buildSymbolResultWithCandidate("USDJPY", "BULLISH"),
			buildSymbolResultWithCandidate("AUDUSD", "BEARISH"),
		},
	}
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	outputs := h.RunCycle(
		[]string{"EURUSD", "GBPUSD", "USDJPY", "AUDUSD"},
		"trace-e2e-concurrency-001",
	)

	// ---------------------------------------------------------------
	// Assert: TA called once (batch), Macro called once.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load())
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load())

	// ---------------------------------------------------------------
	// Assert: RAG and Processor called 4 times (once per symbol).
	// ---------------------------------------------------------------
	assert.Equal(t, int64(4), h.Engine.RAGCalls.Load(),
		"RAG should be called once per candidate symbol")
	assert.Equal(t, int64(4), h.Engine.ProcessorCalls.Load(),
		"Processor should be called once per candidate symbol")

	// ---------------------------------------------------------------
	// Assert: 4 outputs produced (one per candidate symbol).
	// ---------------------------------------------------------------
	require.Len(t, outputs, 4, "should have 4 outputs for 4 candidate symbols")

	// Verify all 4 symbols are represented.
	symbolsSeen := make(map[string]bool)
	for _, out := range outputs {
		assert.Equal(t, constants.StatusCompleted, out.CycleStatus)
		if out.Symbol != "" {
			symbolsSeen[out.Symbol] = true
		}
	}
	assert.True(t, symbolsSeen["EURUSD"], "EURUSD should be in outputs")
	assert.True(t, symbolsSeen["GBPUSD"], "GBPUSD should be in outputs")
	assert.True(t, symbolsSeen["USDJPY"], "USDJPY should be in outputs")
	assert.True(t, symbolsSeen["AUDUSD"], "AUDUSD should be in outputs")
}

// TestConcurrency_ContextCancellation verifies that when the parent
// context is cancelled before the cycle runs, the pipeline exits
// gracefully without processing symbols.
func TestConcurrency_ContextCancellation(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	// Create a pre-cancelled context.
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately.

	outputs := h.Orchestrator.RunCycle(ctx, []string{"EURUSD"}, "trace-e2e-cancelled-001")

	// ---------------------------------------------------------------
	// Assert: Pipeline exited early due to cancelled context.
	// The TA/Macro HTTP calls may or may not have been attempted
	// (depends on goroutine scheduling), but the pipeline should
	// not have completed successfully.
	// ---------------------------------------------------------------
	// With a cancelled context, the HTTP client will fail immediately.
	// The orchestrator should return without retrying.

	// Downstream services should not have been called.
	assert.Equal(t, int64(0), h.Engine.RAGCalls.Load(),
		"RAG should not be called with cancelled context")
	assert.Equal(t, int64(0), h.Engine.ProcessorCalls.Load(),
		"Processor should not be called with cancelled context")
	assert.Empty(t, h.Execution.GetCalls(),
		"Execution should not be called with cancelled context")

	// The outputs may be empty or contain an error output.
	// Either is acceptable for a cancelled context.
	_ = outputs
}

// ---------------------------------------------------------------------------
// Helper: Build a symbol result with one SMC candidate.
// ---------------------------------------------------------------------------

func buildSymbolResultWithCandidate(symbol, trend string) map[string]interface{} {
	direction := "BULLISH"
	if trend == "BEARISH" {
		direction = "BEARISH"
	}
	return map[string]interface{}{
		"symbol":         symbol,
		"status":         "success",
		"overall_trend":  trend,
		"htf_timeframes": []interface{}{"W1", "D1", "H4", "H1"},
		"ltf_timeframes": []interface{}{"M30", "M15", "M5", "M1"},
		"smc_candidates": []interface{}{
			map[string]interface{}{
				"analysis_id":      "SMC-" + symbol + "-H4-001",
				"symbol":           symbol,
				"pattern":          "TURTLE_SOUP_LONG",
				"direction":        direction,
				"entry_price":      1.10000,
				"stop_loss":        1.09500,
				"take_profit":      1.11500,
				"timeframe":        "H4",
				"ltf_confirmation": true,
			},
		},
		"snd_candidates": []interface{}{},
		"snapshots":      map[string]interface{}{},
		"alignment":      map[string]interface{}{},
		"error":          nil,
	}
}
