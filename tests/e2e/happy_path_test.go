package e2e

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
)

// TestFullPipeline_TradeApproved exercises the complete end-to-end pipeline:
//
//	Gateway.RunCycle → TA Collect → Macro Collect (parallel)
//	  → Query Build → RAG Retrieve → Context Assemble
//	  → Processor LLM → Guard Evaluate → Router → Execution
//
// Verifies every stage was called, correct data flowed through, and the
// final output matches the expected TRADE_APPROVED outcome.
func TestFullPipeline_TradeApproved(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// Configure mock engine responses for the happy path.
	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	// Run a full pipeline cycle.
	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-happy-001")

	// ---------------------------------------------------------------
	// Assert: All 4 engine endpoints were called exactly once.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load(), "TA endpoint should be called once")
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load(), "Macro endpoint should be called once")
	assert.Equal(t, int64(1), h.Engine.RAGCalls.Load(), "RAG endpoint should be called once")
	assert.Equal(t, int64(1), h.Engine.ProcessorCalls.Load(), "Processor endpoint should be called once")

	// ---------------------------------------------------------------
	// Assert: TA endpoint received correct symbols and trace_id.
	// ---------------------------------------------------------------
	taCalls := h.Engine.CallsForPath("/internal/ta/analyze")
	require.Len(t, taCalls, 1, "expected exactly 1 TA call")
	taBody := taCalls[0].Body
	require.NotNil(t, taBody, "TA request body should not be nil")

	// The symbols field is sent as []interface{} in JSON.
	taSymbols, ok := taBody["symbols"].([]interface{})
	require.True(t, ok, "TA body should contain symbols array")
	assert.Equal(t, []interface{}{"EURUSD"}, taSymbols)
	assert.Equal(t, "trace-e2e-happy-001", taBody["trace_id"])

	// ---------------------------------------------------------------
	// Assert: Pipeline produced exactly 1 output.
	// ---------------------------------------------------------------
	require.Len(t, outputs, 1, "expected exactly 1 output for single symbol")
	output := outputs[0]

	// ---------------------------------------------------------------
	// Assert: Output status and outcome.
	// ---------------------------------------------------------------
	assert.Equal(t, constants.StatusCompleted, output.CycleStatus,
		"cycle status should be COMPLETED")
	assert.Equal(t, constants.OutcomeTradeApproved, output.CycleOutcome,
		"cycle outcome should be TRADE_APPROVED")
	assert.Equal(t, constants.PhaseCompleted, output.PhaseReached,
		"phase reached should be COMPLETED")
	assert.Equal(t, "EURUSD", output.Symbol)
	assert.NotEmpty(t, output.TraceID, "trace ID should be propagated")
	assert.Empty(t, output.Error, "no error expected on happy path")
	assert.Empty(t, output.ErrorStage, "no error stage expected")
	assert.Greater(t, output.DurationMs, 0.0, "duration should be positive")

	// ---------------------------------------------------------------
	// Assert: ProcessorOutput was populated correctly.
	// ---------------------------------------------------------------
	require.NotNil(t, output.ProcessorOutput, "processor output should be present")
	proc := output.ProcessorOutput
	assert.True(t, proc.TradeValid, "trade should be valid")
	assert.Equal(t, "LONG", proc.Direction)
	assert.Equal(t, "EURUSD", proc.Symbol)
	assert.InDelta(t, 0.87, proc.Confidence, 0.001)
	assert.Equal(t, "A", proc.Grade)
	assert.Equal(t, "INTRADAY", proc.TradingStyle)
	assert.Equal(t, "LONDON_NY_OVERLAP", proc.Session)
	assert.Equal(t, "SMC-EURUSD-H4-001", proc.AnalysisID)
	assert.Equal(t, "LIMIT", proc.ExecutionMode)
	assert.True(t, proc.LTFConfirmed)
	assert.Equal(t, "TURTLE_SOUP", proc.SetupType)

	// Verify price levels.
	require.NotNil(t, proc.EntryPrice)
	assert.InDelta(t, 1.10000, *proc.EntryPrice, 0.00001)
	require.NotNil(t, proc.StopLoss)
	assert.InDelta(t, 1.09500, *proc.StopLoss, 0.00001)
	require.NotNil(t, proc.EntryZoneLow)
	assert.InDelta(t, 1.09950, *proc.EntryZoneLow, 0.00001)
	require.NotNil(t, proc.EntryZoneHigh)
	assert.InDelta(t, 1.10050, *proc.EntryZoneHigh, 0.00001)

	// Verify TP levels.
	require.NotNil(t, proc.TP1Price)
	assert.InDelta(t, 1.10500, *proc.TP1Price, 0.00001)
	assert.Equal(t, 40, proc.TP1Pct)
	require.NotNil(t, proc.TP2Price)
	assert.InDelta(t, 1.11000, *proc.TP2Price, 0.00001)
	assert.Equal(t, 30, proc.TP2Pct)
	require.NotNil(t, proc.TP3Price)
	assert.InDelta(t, 1.11500, *proc.TP3Price, 0.00001)
	assert.Equal(t, 30, proc.TP3Pct)

	// Verify RR ratio and confluence.
	require.NotNil(t, proc.RRRatio)
	assert.InDelta(t, 3.0, *proc.RRRatio, 0.001)
	assert.InDelta(t, 8.5, proc.ConfluenceScore, 0.001)

	// ---------------------------------------------------------------
	// Assert: Guards passed (no blocking rules).
	// ---------------------------------------------------------------
	require.NotNil(t, output.GuardResult, "guard result should be present")
	// Note: Guard verdict depends on current time (session, weekend, news).
	// We verify no REJECT verdict from counter-trend guard since the trade
	// is LONG with BULLISH trend (aligned).
	for _, check := range output.GuardResult.Checks {
		if check.Rule == constants.RuleCounterTrendNoChoch {
			assert.NotEqual(t, constants.VerdictReject, check.Verdict,
				"counter-trend guard should not reject an aligned trade")
		}
	}

	// ---------------------------------------------------------------
	// Assert: Execution port was called with the correct decision.
	// ---------------------------------------------------------------
	execCalls := h.Execution.GetCalls()

	// If guards rejected (e.g., weekend/session), execution won't be called.
	// If guards passed, execution must have been called exactly once.
	if output.CycleOutcome == constants.OutcomeTradeApproved {
		require.Len(t, execCalls, 1, "execution should be called once for approved trade")
		execDecision := execCalls[0].Decision
		assert.Equal(t, "EURUSD", execDecision.Symbol)
		assert.Equal(t, "LONG", execDecision.Direction)
		assert.Equal(t, "A", execDecision.Grade)
		assert.Equal(t, "SMC-EURUSD-H4-001", execDecision.AnalysisID)
	}

	// ---------------------------------------------------------------
	// Assert: Execution result is present.
	// ---------------------------------------------------------------
	if output.CycleOutcome == constants.OutcomeTradeApproved {
		require.NotNil(t, output.ExecutionResult, "execution result should be present")
		assert.Equal(t, true, output.ExecutionResult["accepted"])
		assert.Equal(t, "LIMIT_ORDER_PLACED", output.ExecutionResult["status"])
	}
}

// TestFullPipeline_NoCandidates verifies the early-exit path when TA
// analysis returns no trade candidates. The pipeline should:
// 1. Call TA and Macro endpoints (parallel collection)
// 2. NOT call RAG, Processor, or Execution
// 3. Return COMPLETED status with INSUFFICIENT_DATA outcome
func TestFullPipeline_NoCandidates(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// TA returns success but no candidates.
	h.Engine.TAResponse = TAResponseNoCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	// RAG and Processor should NOT be called, but set them to catch bugs.
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-nocandidate-001")

	// ---------------------------------------------------------------
	// Assert: Only TA and Macro were called.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load(), "TA should be called")
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load(), "Macro should be called")
	assert.Equal(t, int64(0), h.Engine.RAGCalls.Load(), "RAG should NOT be called")
	assert.Equal(t, int64(0), h.Engine.ProcessorCalls.Load(), "Processor should NOT be called")

	// ---------------------------------------------------------------
	// Assert: Output is COMPLETED with INSUFFICIENT_DATA.
	// ---------------------------------------------------------------
	require.Len(t, outputs, 1)
	output := outputs[0]
	assert.Equal(t, constants.StatusCompleted, output.CycleStatus)
	assert.Equal(t, constants.OutcomeInsufficientData, output.CycleOutcome)
	assert.Equal(t, constants.PhaseCompleted, output.PhaseReached)
	assert.Empty(t, output.Error)

	// ---------------------------------------------------------------
	// Assert: No processor output, no guard result, no execution.
	// ---------------------------------------------------------------
	assert.Nil(t, output.ProcessorOutput, "no processor output expected")
	assert.Nil(t, output.GuardResult, "no guard result expected")
	assert.Nil(t, output.ExecutionResult, "no execution result expected")

	// ---------------------------------------------------------------
	// Assert: Execution port was never called.
	// ---------------------------------------------------------------
	assert.Empty(t, h.Execution.GetCalls(), "execution should not be called")
}

// TestFullPipeline_ProcessorRejectsNoSetup verifies that when the
// Processor LLM determines there is no valid trade (trade_valid=false),
// the pipeline completes with NO_SETUP and does NOT call Execution.
// This tests the Router.Route early-exit path for processor rejection.
func TestFullPipeline_ProcessorRejectsNoSetup(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// TA has candidates (so pipeline proceeds past Phase 1).
	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	// Processor says NO SETUP.
	h.Engine.ProcessorResponse = ProcessorResponseNoSetup()

	outputs := h.RunCycle([]string{"EURUSD"}, "trace-e2e-nosetup-001")

	// ---------------------------------------------------------------
	// Assert: All 4 engine endpoints were called.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load())
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load())
	assert.Equal(t, int64(1), h.Engine.RAGCalls.Load())
	assert.Equal(t, int64(1), h.Engine.ProcessorCalls.Load())

	// ---------------------------------------------------------------
	// Assert: Output is COMPLETED with NO_SETUP.
	// ---------------------------------------------------------------
	require.Len(t, outputs, 1)
	output := outputs[0]
	assert.Equal(t, constants.StatusCompleted, output.CycleStatus)
	assert.Equal(t, constants.OutcomeNoSetup, output.CycleOutcome)
	assert.Equal(t, constants.PhaseCompleted, output.PhaseReached)
	assert.Equal(t, "EURUSD", output.Symbol)
	assert.Empty(t, output.Error)

	// ---------------------------------------------------------------
	// Assert: Processor output is present but trade_valid is false.
	// ---------------------------------------------------------------
	require.NotNil(t, output.ProcessorOutput)
	assert.False(t, output.ProcessorOutput.TradeValid)
	assert.Equal(t, "EURUSD", output.ProcessorOutput.Symbol)
	assert.InDelta(t, 0.35, output.ProcessorOutput.Confidence, 0.001)

	// ---------------------------------------------------------------
	// Assert: Execution was NOT called (processor said no setup).
	// ---------------------------------------------------------------
	assert.Empty(t, h.Execution.GetCalls(),
		"execution must NOT be called when processor rejects")
}
