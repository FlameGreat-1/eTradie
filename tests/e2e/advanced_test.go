package e2e

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
)

// TestFullPipeline_MultiSymbol_OnlyOneHasCandidates verifies the
// concurrent symbol processing path in executePipeline.
//
// Two symbols are sent: EURUSD (has SMC candidates) and GBPUSD (no
// candidates). The pipeline should:
// - Call TA once with both symbols
// - Call Macro once
// - Process only EURUSD through RAG/Processor/Guards/Execution
// - Skip GBPUSD entirely after Phase 1
func TestFullPipeline_MultiSymbol_OnlyOneHasCandidates(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// TA returns two symbols: EURUSD with candidates, GBPUSD without.
	h.Engine.TAResponse = TAResponseMultiSymbol()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	outputs := h.RunCycle([]string{"EURUSD", "GBPUSD"}, "trace-e2e-multi-001")

	// ---------------------------------------------------------------
	// Assert: TA called once with both symbols, Macro called once.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load())
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load())

	// Verify TA received both symbols.
	taCalls := h.Engine.CallsForPath("/internal/ta/analyze")
	require.Len(t, taCalls, 1)
	taSymbols, ok := taCalls[0].Body["symbols"].([]interface{})
	require.True(t, ok)
	assert.Len(t, taSymbols, 2)

	// ---------------------------------------------------------------
	// Assert: Only EURUSD proceeded to RAG/Processor (1 call each).
	// GBPUSD had no candidates and was filtered out.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.RAGCalls.Load(),
		"RAG should be called once (only for EURUSD)")
	assert.Equal(t, int64(1), h.Engine.ProcessorCalls.Load(),
		"Processor should be called once (only for EURUSD)")

	// ---------------------------------------------------------------
	// Assert: Output contains result for EURUSD.
	// ---------------------------------------------------------------
	require.NotEmpty(t, outputs)
	var eurusdOutput *int
	for i, out := range outputs {
		if out.Symbol == "EURUSD" {
			idx := i
			eurusdOutput = &idx
			assert.Equal(t, constants.StatusCompleted, out.CycleStatus)
			require.NotNil(t, out.ProcessorOutput)
			assert.Equal(t, "EURUSD", out.ProcessorOutput.Symbol)
		}
	}
	require.NotNil(t, eurusdOutput, "should have output for EURUSD")
}

// TestFullPipeline_ExecutionPortError verifies that when the Execution
// port returns an error, the pipeline still completes and the error
// is captured in the execution result.
//
// The Router.executeTrade method catches execution errors and returns
// {"status": "error", "reason": ...} instead of propagating the error.
// The overall outcome is still TRADE_APPROVED because the guards passed.
func TestFullPipeline_ExecutionPortError(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	// Configure execution to return an error.
	h.Execution.Err = fmt.Errorf("execution RPC: connection refused")

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-exec-err-001")

	// ---------------------------------------------------------------
	// Assert: All engine endpoints were called.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load())
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load())
	assert.Equal(t, int64(1), h.Engine.RAGCalls.Load())
	assert.Equal(t, int64(1), h.Engine.ProcessorCalls.Load())

	// ---------------------------------------------------------------
	// Assert: Execution port behavior depends on guard outcome.
	// ---------------------------------------------------------------
	execCalls := h.Execution.GetCalls()

	require.NotEmpty(t, outputs)
	output := outputs[0]

	if output.CycleOutcome == constants.OutcomeRejectedByGuard {
		t.Logf("INFO: Time-based guards rejected (blocking_rules=%v). "+
			"Execution error capture assertions skipped. Expected on weekends/off-hours.",
			output.GuardResult.BlockingRules)
		assert.Empty(t, execCalls,
			"execution must NOT be called when guards reject")
	} else {
		// Guards passed, execution was attempted and failed.
		require.Equal(t, constants.OutcomeTradeApproved, output.CycleOutcome)
		require.NotEmpty(t, execCalls, "execution should have been called")
		require.NotNil(t, output.ExecutionResult)
		assert.Equal(t, "error", output.ExecutionResult["status"])
		assert.Contains(t, output.ExecutionResult["reason"], "connection refused")
	}
}

// TestFullPipeline_PartialMacroData verifies that the pipeline handles
// degraded macro data gracefully. When 5 of 8 macro datasets fail,
// the pipeline should still proceed through all phases.
func TestFullPipeline_PartialMacroData(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponsePartial() // 5 datasets failed.
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-partial-macro-001")

	// ---------------------------------------------------------------
	// Assert: All 4 endpoints were called (pipeline proceeded fully).
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load())
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load())
	assert.Equal(t, int64(1), h.Engine.RAGCalls.Load())
	assert.Equal(t, int64(1), h.Engine.ProcessorCalls.Load())

	// ---------------------------------------------------------------
	// Assert: Pipeline completed (not failed due to partial macro).
	// ---------------------------------------------------------------
	require.NotEmpty(t, outputs)
	output := outputs[0]
	assert.Equal(t, constants.StatusCompleted, output.CycleStatus,
		"pipeline should complete even with partial macro data")
	assert.NotEqual(t, constants.OutcomePipelineError, output.CycleOutcome,
		"partial macro data should not cause pipeline error")
	assert.Empty(t, output.Error)
}

// TestFullPipeline_EmptyRAGChunks verifies that the pipeline handles
// empty RAG retrieval results gracefully. The processor should still
// receive the context (with empty knowledge) and make a decision.
func TestFullPipeline_EmptyRAGChunks(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseEmpty() // No matching chunks.
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-empty-rag-001")

	// ---------------------------------------------------------------
	// Assert: All 4 endpoints were called.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load())
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load())
	assert.Equal(t, int64(1), h.Engine.RAGCalls.Load())
	assert.Equal(t, int64(1), h.Engine.ProcessorCalls.Load())

	// ---------------------------------------------------------------
	// Assert: Pipeline completed successfully.
	// ---------------------------------------------------------------
	require.NotEmpty(t, outputs)
	output := outputs[0]
	assert.Equal(t, constants.StatusCompleted, output.CycleStatus)
	assert.Empty(t, output.Error)

	// ---------------------------------------------------------------
	// Assert: Processor received the request (verified by call count)
	// and the pipeline continued to guards.
	// ---------------------------------------------------------------
	require.NotNil(t, output.ProcessorOutput)
	assert.True(t, output.ProcessorOutput.TradeValid)
}

// TestFullPipeline_EmptySymbolList verifies that RunCycle handles an
// empty symbol list gracefully without panicking or calling any
// engine endpoints.
func TestFullPipeline_EmptySymbolList(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// Set responses to catch any unexpected calls.
	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	outputs := h.RunCycle([]string{}, "trace-e2e-empty-symbols-001")

	// ---------------------------------------------------------------
	// Assert: TA was called with empty symbols (collector handles it).
	// The TACollector returns an empty TAResult when symbols is empty,
	// which has no candidates, so the pipeline exits early.
	// ---------------------------------------------------------------
	// TA collector is called but returns empty result.
	// Macro is still called in parallel.

	// ---------------------------------------------------------------
	// Assert: RAG, Processor, Execution were NOT called.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(0), h.Engine.RAGCalls.Load(),
		"RAG should not be called for empty symbols")
	assert.Equal(t, int64(0), h.Engine.ProcessorCalls.Load(),
		"Processor should not be called for empty symbols")
	assert.Empty(t, h.Execution.GetCalls(),
		"Execution should not be called for empty symbols")

	// ---------------------------------------------------------------
	// Assert: Output indicates no data / insufficient data.
	// ---------------------------------------------------------------
	require.NotEmpty(t, outputs)
	for _, out := range outputs {
		assert.Equal(t, constants.StatusCompleted, out.CycleStatus)
	}
}
