package e2e

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
)

// TestFullPipeline_CounterTrendRejectedByGuard verifies MR-REJECT-006:
// a counter-trend trade (SHORT against BULLISH trend) with NO CHoCH
// events in the TA snapshots is rejected by the guard evaluator.
//
// This guard is deterministic (data-driven, not time-dependent) so
// the test result is stable regardless of when it runs.
//
// Pipeline flow:
//
//	TA (BULLISH trend, no CHoCH) + Macro → RAG → Processor (SHORT)
//	  → Guards (MR-REJECT-006 fires) → Execution NOT called
func TestFullPipeline_CounterTrendRejectedByGuard(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// TA: BULLISH trend, candidates present, but snapshots have
	// empty choch_events ([]interface{}{} → len=0 → totalChoch=0).
	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	// Processor approves a counter-trend SHORT against BULLISH trend.
	h.Engine.ProcessorResponse = ProcessorResponseCounterTrend()

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-guard-ct-001")

	// ---------------------------------------------------------------
	// Assert: All 4 engine endpoints were called (pipeline ran fully
	// through to guards before rejection).
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load())
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load())
	assert.Equal(t, int64(1), h.Engine.RAGCalls.Load())
	assert.Equal(t, int64(1), h.Engine.ProcessorCalls.Load())

	// ---------------------------------------------------------------
	// Assert: Output reflects guard rejection.
	// ---------------------------------------------------------------
	require.Len(t, outputs, 1)
	output := outputs[0]
	assert.Equal(t, constants.StatusCompleted, output.CycleStatus)
	assert.Equal(t, constants.OutcomeRejectedByGuard, output.CycleOutcome,
		"counter-trend SHORT against BULLISH with no CHoCH must be rejected")
	assert.Equal(t, constants.PhaseCompleted, output.PhaseReached)
	assert.Equal(t, "EURUSD", output.Symbol)
	assert.Empty(t, output.Error)

	// ---------------------------------------------------------------
	// Assert: Processor output is present (processor approved the trade,
	// but guards overrode it).
	// ---------------------------------------------------------------
	require.NotNil(t, output.ProcessorOutput)
	assert.True(t, output.ProcessorOutput.TradeValid,
		"processor said trade_valid=true, guards rejected it")
	assert.Equal(t, "SHORT", output.ProcessorOutput.Direction)

	// ---------------------------------------------------------------
	// Assert: Guard result shows MR-REJECT-006 fired.
	// ---------------------------------------------------------------
	require.NotNil(t, output.GuardResult)
	assert.Equal(t, constants.VerdictReject, output.GuardResult.OverallVerdict)
	assert.Contains(t, output.GuardResult.BlockingRules, string(constants.RuleCounterTrendNoChoch),
		"MR-REJECT-006 should be in blocking rules")

	// Verify the specific check details.
	var counterTrendCheck *constants.GuardVerdict
	for _, check := range output.GuardResult.Checks {
		if check.Rule == constants.RuleCounterTrendNoChoch {
			v := check.Verdict
			counterTrendCheck = &v
			assert.Equal(t, constants.VerdictReject, check.Verdict)
			assert.Contains(t, check.Reason, "Counter-trend trade without any CHoCH")
			// Verify metadata contains the trend/direction info.
			require.NotNil(t, check.Metadata)
			assert.Equal(t, "BULLISH", check.Metadata["trend"])
			assert.Equal(t, "SHORT", check.Metadata["direction"])
		}
	}
	require.NotNil(t, counterTrendCheck, "counter-trend check should be present")

	// ---------------------------------------------------------------
	// Assert: Execution was NOT called (guards blocked it).
	// ---------------------------------------------------------------
	assert.Empty(t, h.Execution.GetCalls(),
		"execution must NOT be called when guards reject")

	// ---------------------------------------------------------------
	// Assert: No execution result in output.
	// ---------------------------------------------------------------
	assert.Nil(t, output.ExecutionResult,
		"no execution result when guards reject")
}

// TestFullPipeline_TACollectionFailure verifies that when the TA engine
// returns an HTTP error, the pipeline fails gracefully.
//
// Since TA and Macro run in parallel, Macro IS still called.
// But RAG, Processor, and Execution are never reached.
func TestFullPipeline_TACollectionFailure(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// TA returns 500 error.
	h.Engine.TAResponse = map[string]interface{}{"error": "internal server error"}
	h.Engine.TAStatusCode = 500
	// Macro succeeds (parallel collection).
	h.Engine.MacroResponse = MacroResponseFull()
	// These should NOT be called.
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-ta-fail-001")

	// ---------------------------------------------------------------
	// Assert: TA was called (and failed), Macro was called (parallel).
	// ---------------------------------------------------------------
	assert.GreaterOrEqual(t, h.Engine.TACalls.Load(), int64(1),
		"TA should be called at least once (may retry)")
	assert.GreaterOrEqual(t, h.Engine.MacroCalls.Load(), int64(1),
		"Macro should be called at least once (parallel with TA, may be called again on retry)")

	// ---------------------------------------------------------------
	// Assert: RAG, Processor, Execution were NOT called.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(0), h.Engine.RAGCalls.Load(),
		"RAG should NOT be called when TA fails")
	assert.Equal(t, int64(0), h.Engine.ProcessorCalls.Load(),
		"Processor should NOT be called when TA fails")
	assert.Empty(t, h.Execution.GetCalls(),
		"Execution should NOT be called when TA fails")

	// ---------------------------------------------------------------
	// Assert: Pipeline produced error output.
	// ---------------------------------------------------------------
	require.NotEmpty(t, outputs, "should produce at least one output")
	// Find the error output (may have partial results + error output).
	var errorOutput *bool
	for _, out := range outputs {
		if out.CycleStatus == constants.StatusFailed || out.CycleStatus == constants.StatusTimedOut {
			v := true
			errorOutput = &v
			assert.NotEmpty(t, out.Error, "error message should be present")
			assert.Equal(t, constants.OutcomePipelineError, out.CycleOutcome)
		}
	}
	require.NotNil(t, errorOutput, "should have at least one failed output")
}

// TestFullPipeline_MacroCollectionFailure verifies that when the Macro
// engine returns an HTTP error, the pipeline fails gracefully.
//
// Since TA and Macro run in parallel, TA IS still called.
// But RAG, Processor, and Execution are never reached.
func TestFullPipeline_MacroCollectionFailure(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// TA succeeds.
	h.Engine.TAResponse = TAResponseWithCandidates()
	// Macro returns 500 error.
	h.Engine.MacroResponse = map[string]interface{}{"error": "internal server error"}
	h.Engine.MacroStatusCode = 500
	// These should NOT be called.
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-macro-fail-001")

	// ---------------------------------------------------------------
	// Assert: TA was called, Macro was called (and failed).
	// ---------------------------------------------------------------
	assert.GreaterOrEqual(t, h.Engine.TACalls.Load(), int64(1),
		"TA should be called at least once (parallel with Macro, may be called again on retry)")
	assert.GreaterOrEqual(t, h.Engine.MacroCalls.Load(), int64(1),
		"Macro should be called at least once (may retry)")

	// ---------------------------------------------------------------
	// Assert: RAG, Processor, Execution were NOT called.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(0), h.Engine.RAGCalls.Load(),
		"RAG should NOT be called when Macro fails")
	assert.Equal(t, int64(0), h.Engine.ProcessorCalls.Load(),
		"Processor should NOT be called when Macro fails")
	assert.Empty(t, h.Execution.GetCalls(),
		"Execution should NOT be called when Macro fails")

	// ---------------------------------------------------------------
	// Assert: Pipeline produced error output.
	// ---------------------------------------------------------------
	require.NotEmpty(t, outputs)
	var hasError bool
	for _, out := range outputs {
		if out.CycleStatus == constants.StatusFailed || out.CycleStatus == constants.StatusTimedOut {
			hasError = true
			assert.NotEmpty(t, out.Error)
			assert.Equal(t, constants.OutcomePipelineError, out.CycleOutcome)
		}
	}
	assert.True(t, hasError, "should have at least one failed output")
}

// TestFullPipeline_RAGFailure verifies that when the RAG retrieval
// endpoint returns an HTTP error, the pipeline fails for that symbol.
//
// TA and Macro succeed, but the per-symbol processing fails at RAG.
// Processor and Execution are never called.
func TestFullPipeline_RAGFailure(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	// RAG returns 500.
	h.Engine.RAGResponse = map[string]interface{}{"error": "vector store unavailable"}
	h.Engine.RAGStatusCode = 500
	// Processor should NOT be called.
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-rag-fail-001")

	// ---------------------------------------------------------------
	// Assert: TA, Macro called. RAG called (and failed).
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load())
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load())
	assert.GreaterOrEqual(t, h.Engine.RAGCalls.Load(), int64(1),
		"RAG should be called at least once (may retry)")

	// ---------------------------------------------------------------
	// Assert: Processor and Execution were NOT called.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(0), h.Engine.ProcessorCalls.Load(),
		"Processor should NOT be called when RAG fails")
	assert.Empty(t, h.Execution.GetCalls(),
		"Execution should NOT be called when RAG fails")

	// ---------------------------------------------------------------
	// Assert: Output reflects the failure.
	// ---------------------------------------------------------------
	require.NotEmpty(t, outputs)
	var hasSymbolError bool
	for _, out := range outputs {
		if out.Symbol == "EURUSD" && out.CycleStatus == constants.StatusFailed {
			hasSymbolError = true
			assert.Equal(t, constants.OutcomePipelineError, out.CycleOutcome)
			assert.NotEmpty(t, out.Error)
			assert.Contains(t, out.Error, "RAG")
		}
	}
	assert.True(t, hasSymbolError, "should have a failed output for EURUSD")
}

// TestFullPipeline_ProcessorHTTPFailure verifies that when the Processor
// LLM endpoint returns an HTTP error, the pipeline fails for that symbol.
//
// TA, Macro, and RAG all succeed. The failure occurs at Phase 5.
// Execution is never called.
func TestFullPipeline_ProcessorHTTPFailure(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	// Processor returns 500.
	h.Engine.ProcessorResponse = map[string]interface{}{"error": "LLM provider timeout"}
	h.Engine.ProcessorStatusCode = 500

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-proc-fail-001")

	// ---------------------------------------------------------------
	// Assert: TA, Macro, RAG called. Processor called (and failed).
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load())
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load())
	assert.Equal(t, int64(1), h.Engine.RAGCalls.Load())
	assert.GreaterOrEqual(t, h.Engine.ProcessorCalls.Load(), int64(1),
		"Processor should be called at least once (may retry)")

	// ---------------------------------------------------------------
	// Assert: Execution was NOT called.
	// ---------------------------------------------------------------
	assert.Empty(t, h.Execution.GetCalls(),
		"Execution should NOT be called when Processor fails")

	// ---------------------------------------------------------------
	// Assert: Output reflects the failure.
	// ---------------------------------------------------------------
	require.NotEmpty(t, outputs)
	var hasSymbolError bool
	for _, out := range outputs {
		if out.Symbol == "EURUSD" && out.CycleStatus == constants.StatusFailed {
			hasSymbolError = true
			assert.Equal(t, constants.OutcomePipelineError, out.CycleOutcome)
			assert.NotEmpty(t, out.Error)
		}
	}
	assert.True(t, hasSymbolError, "should have a failed output for EURUSD")
}
