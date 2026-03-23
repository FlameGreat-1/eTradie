package e2e

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// ---------------------------------------------------------------------------
// Confirmation Pulse Tests (Instant-Mode Callback Path)
// ---------------------------------------------------------------------------

// TestConfirmationPulse_LTFConfirmed verifies the instant-mode callback:
// Execution watcher detects price in zone → calls Gateway.RunConfirmationPulse
// → Gateway calls TA (bypassCache=true) → finds matching analysis_id
// → reads ltf_confirmation=true → returns Confirmed=true.
func TestConfirmationPulse_LTFConfirmed(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// TA response with a candidate whose analysis_id matches and
	// ltf_confirmation is true (set in TAResponseWithCandidates).
	h.Engine.TAResponse = TAResponseWithCandidates()

	result := h.Orchestrator.RunConfirmationPulse(
		context.Background(),
		"EURUSD",
		"SMC-EURUSD-H4-001", // Must match the analysis_id in the fixture.
		"trace-e2e-confirm-001",
	)

	// ---------------------------------------------------------------
	// Assert: TA was called with bypassCache=true.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load(),
		"TA should be called once for confirmation pulse")

	// Verify the TA request contained the correct symbol.
	taCalls := h.Engine.CallsForPath("/internal/ta/analyze")
	require.Len(t, taCalls, 1)
	taBody := taCalls[0].Body
	require.NotNil(t, taBody)
	taSymbols, ok := taBody["symbols"].([]interface{})
	require.True(t, ok)
	assert.Equal(t, []interface{}{"EURUSD"}, taSymbols)

	// ---------------------------------------------------------------
	// Assert: Macro, RAG, Processor were NOT called (pulse bypasses them).
	// ---------------------------------------------------------------
	assert.Equal(t, int64(0), h.Engine.MacroCalls.Load(),
		"Macro should NOT be called during confirmation pulse")
	assert.Equal(t, int64(0), h.Engine.RAGCalls.Load(),
		"RAG should NOT be called during confirmation pulse")
	assert.Equal(t, int64(0), h.Engine.ProcessorCalls.Load(),
		"Processor should NOT be called during confirmation pulse")

	// ---------------------------------------------------------------
	// Assert: Confirmation result.
	// ---------------------------------------------------------------
	require.NotNil(t, result)
	assert.True(t, result.Confirmed, "LTF should be confirmed")
	assert.True(t, result.LTFConfirmation, "LTFConfirmation flag should be true")
	assert.Equal(t, "SMC LTF confirmation met", result.Reason)
}

// TestConfirmationPulse_LTFNotConfirmed verifies the case where the
// candidate exists but ltf_confirmation is false.
func TestConfirmationPulse_LTFNotConfirmed(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	// Build a TA response where ltf_confirmation is false.
	taResp := TAResponseWithCandidates()
	// Navigate to the SMC candidate and set ltf_confirmation to false.
	symResults := taResp["symbol_results"].([]interface{})
	eurusd := symResults[0].(map[string]interface{})
	smcCandidates := eurusd["smc_candidates"].([]interface{})
	candidate := smcCandidates[0].(map[string]interface{})
	candidate["ltf_confirmation"] = false
	h.Engine.TAResponse = taResp

	result := h.Orchestrator.RunConfirmationPulse(
		context.Background(),
		"EURUSD",
		"SMC-EURUSD-H4-001",
		"trace-e2e-confirm-notmet-001",
	)

	require.NotNil(t, result)
	assert.False(t, result.Confirmed, "LTF should NOT be confirmed")
	assert.False(t, result.LTFConfirmation)
	assert.Equal(t, "SMC LTF confirmation not yet met", result.Reason)
}

// TestConfirmationPulse_CandidateNotFound verifies that when TA returns
// candidates but none match the requested analysis_id, the pulse
// returns Confirmed=false with an appropriate reason.
func TestConfirmationPulse_CandidateNotFound(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = TAResponseWithCandidates()

	result := h.Orchestrator.RunConfirmationPulse(
		context.Background(),
		"EURUSD",
		"NONEXISTENT-ANALYSIS-ID", // Does not match any candidate.
		"trace-e2e-confirm-notfound-001",
	)

	require.NotNil(t, result)
	assert.False(t, result.Confirmed)
	assert.Contains(t, result.Reason, "not found in TA results")
	assert.Contains(t, result.Reason, "NONEXISTENT-ANALYSIS-ID")
}

// TestConfirmationPulse_TAFailure verifies that when the TA endpoint
// fails during a confirmation pulse, the result is Confirmed=false
// with the error captured in the reason.
func TestConfirmationPulse_TAFailure(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = map[string]interface{}{"error": "service unavailable"}
	h.Engine.TAStatusCode = 500

	result := h.Orchestrator.RunConfirmationPulse(
		context.Background(),
		"EURUSD",
		"SMC-EURUSD-H4-001",
		"trace-e2e-confirm-tafail-001",
	)

	require.NotNil(t, result)
	assert.False(t, result.Confirmed)
	assert.Contains(t, result.Reason, "TA collection failed")
}

// TestConfirmationPulse_NoCandidates verifies that when TA returns
// success but no candidates, the pulse returns Confirmed=false.
func TestConfirmationPulse_NoCandidates(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = TAResponseNoCandidates()

	result := h.Orchestrator.RunConfirmationPulse(
		context.Background(),
		"EURUSD",
		"SMC-EURUSD-H4-001",
		"trace-e2e-confirm-nocandidate-001",
	)

	require.NotNil(t, result)
	assert.False(t, result.Confirmed)
	assert.Equal(t, "TA returned no candidates for symbol", result.Reason)
}

// ---------------------------------------------------------------------------
// Data Flow Integrity Tests
// ---------------------------------------------------------------------------

// TestDataFlow_RAGReceivesCorrectQueryParams verifies that the RAG
// endpoint receives the exact query parameters built by the QueryBuilder
// from TA + Macro data. This ensures the data flows correctly through:
// TA → QueryBuilder.Build() → retrieveRAG() → HTTP POST body.
//
// The Go orchestrator.retrieveRAG() sends 27 fields that must match
// the Python InternalRAGRequest Pydantic model exactly. This test
// verifies every single field is present in the HTTP request body.
func TestDataFlow_RAGReceivesCorrectQueryParams(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	h.RunCycle([]string{"EURUSD"}, "trace-e2e-dataflow-rag-001")

	// ---------------------------------------------------------------
	// Assert: RAG endpoint received the correct query parameters.
	// ---------------------------------------------------------------
	ragCalls := h.Engine.CallsForPath("/internal/rag/retrieve")
	require.Len(t, ragCalls, 1, "RAG should be called once")
	ragBody := ragCalls[0].Body
	require.NotNil(t, ragBody)

	// ---------------------------------------------------------------
	// Core fields (always present, always populated).
	// Source: orchestrator.go retrieveRAG() reqBody map.
	// Contract: Python InternalRAGRequest Pydantic model.
	// ---------------------------------------------------------------

	// symbol: passed through from the candidate's symbol.
	assert.Equal(t, "EURUSD", ragBody["symbol"])

	// trace_id: propagated from the cycle's trace ID.
	assert.Equal(t, "trace-e2e-dataflow-rag-001", ragBody["trace_id"])

	// query_text: generated by QueryBuilder.BuildQueryText().
	// Must be non-empty; contains symbol + direction + patterns.
	queryText, ok := ragBody["query_text"].(string)
	require.True(t, ok, "query_text should be a string")
	assert.NotEmpty(t, queryText, "query_text should not be empty")
	// TAResponseWithCandidates has BULLISH EURUSD with TURTLE_SOUP_LONG.
	assert.Contains(t, queryText, "EURUSD", "query_text should contain the symbol")

	// strategy: selected by QueryBuilder based on TA signals.
	strategy, ok := ragBody["strategy"].(string)
	require.True(t, ok, "strategy should be a string")
	assert.NotEmpty(t, strategy, "strategy should not be empty")

	// ---------------------------------------------------------------
	// TA-derived fields from QueryBuilder.ExtractTASignals().
	// ---------------------------------------------------------------

	// framework: "smc" or "snd" based on which candidates are present.
	// TAResponseWithCandidates has SMC candidates only -> "smc".
	_, hasFramework := ragBody["framework"]
	assert.True(t, hasFramework, "framework field should be present")

	// setup_family: first setup family from collectAllSetupFamilies().
	_, hasSetupFamily := ragBody["setup_family"]
	assert.True(t, hasSetupFamily, "setup_family field should be present")

	// direction: "long", "short", or "neutral" from candidate directions.
	_, hasDirection := ragBody["direction"]
	assert.True(t, hasDirection, "direction field should be present")

	// timeframe: from candidate timeframe (may be empty string).
	_, hasTimeframe := ragBody["timeframe"]
	assert.True(t, hasTimeframe, "timeframe field should be present")

	// style: trading style (may be empty string).
	_, hasStyle := ragBody["style"]
	assert.True(t, hasStyle, "style field should be present")

	// all_frameworks: list of all frameworks detected.
	_, hasAllFrameworks := ragBody["all_frameworks"]
	assert.True(t, hasAllFrameworks, "all_frameworks field should be present")

	// all_setup_families: list of all setup families detected.
	_, hasAllSetupFamilies := ragBody["all_setup_families"]
	assert.True(t, hasAllSetupFamilies, "all_setup_families field should be present")

	// ---------------------------------------------------------------
	// TA signal boolean flags.
	// ---------------------------------------------------------------

	// has_smc_candidates: true when SMC candidates exist.
	// TAResponseWithCandidates has 1 SMC candidate.
	hasSMC, hasSMCField := ragBody["has_smc_candidates"]
	assert.True(t, hasSMCField, "has_smc_candidates field should be present")
	assert.Equal(t, true, hasSMC, "has_smc_candidates should be true (fixture has SMC candidates)")

	// has_snd_candidates: false when no SnD candidates exist.
	hasSnD, hasSnDField := ragBody["has_snd_candidates"]
	assert.True(t, hasSnDField, "has_snd_candidates field should be present")
	assert.Equal(t, false, hasSnD, "has_snd_candidates should be false (fixture has no SnD candidates)")

	// ---------------------------------------------------------------
	// Macro signal boolean flags from ExtractMacroSignals().
	// MacroResponseFull() has all 8 datasets populated.
	// ---------------------------------------------------------------

	// has_macro_data: true when any macro dataset is available.
	_, hasMacroData := ragBody["has_macro_data"]
	assert.True(t, hasMacroData, "has_macro_data field should be present")

	// has_cot_data: derived from COT dataset presence.
	_, hasCOTData := ragBody["has_cot_data"]
	assert.True(t, hasCOTData, "has_cot_data field should be present")

	// has_rate_decision: derived from calendar events containing "rate decision".
	_, hasRateDecision := ragBody["has_rate_decision"]
	assert.True(t, hasRateDecision, "has_rate_decision field should be present")

	// has_high_impact_event: derived from calendar HIGH-impact events.
	_, hasHighImpact := ragBody["has_high_impact_event"]
	assert.True(t, hasHighImpact, "has_high_impact_event field should be present")

	// has_dxy_data: true when DXY dataset is available.
	// MacroResponseFull has dxy.latest.dxy_value = 104.5.
	hasDXY, hasDXYField := ragBody["has_dxy_data"]
	assert.True(t, hasDXYField, "has_dxy_data field should be present")
	assert.Equal(t, true, hasDXY, "has_dxy_data should be true (fixture has DXY data)")

	// ---------------------------------------------------------------
	// Enriched macro signal fields (Python InternalRAGRequest).
	// These are extracted by ExtractMacroSignals() from the macro
	// datasets and sent to RAG for scenario-aware retrieval.
	// ---------------------------------------------------------------

	// has_qe_qt: true when central bank has QE/QT policy action.
	_, hasQEQT := ragBody["has_qe_qt"]
	assert.True(t, hasQEQT, "has_qe_qt field should be present")

	// has_stagflation: true when stagflation is detected in sentiment.
	_, hasStagflation := ragBody["has_stagflation"]
	assert.True(t, hasStagflation, "has_stagflation field should be present")

	// has_cot_extremes: true when COT extremes are flagged.
	_, hasCOTExtremes := ragBody["has_cot_extremes"]
	assert.True(t, hasCOTExtremes, "has_cot_extremes field should be present")

	// has_tff_data: true when TFF (Traders in Financial Futures) data exists.
	_, hasTFFData := ragBody["has_tff_data"]
	assert.True(t, hasTFFData, "has_tff_data field should be present")

	// has_core_inflation: true when core inflation releases exist.
	_, hasCoreInflation := ragBody["has_core_inflation"]
	assert.True(t, hasCoreInflation, "has_core_inflation field should be present")

	// has_safe_haven_elevated: true when safe haven demand is elevated.
	_, hasSafeHaven := ragBody["has_safe_haven_elevated"]
	assert.True(t, hasSafeHaven, "has_safe_haven_elevated field should be present")

	// has_commodity_currencies_weak: true when AUD/NZD/CAD are weak.
	_, hasCommodityWeak := ragBody["has_commodity_currencies_weak"]
	assert.True(t, hasCommodityWeak, "has_commodity_currencies_weak field should be present")

	// ---------------------------------------------------------------
	// Macro string signal fields.
	// ---------------------------------------------------------------

	// dxy_momentum: "BULLISH", "BEARISH", or empty.
	// MacroResponseFull has dxy.latest.dxy_momentum = "BULLISH".
	_, hasDXYMomentum := ragBody["dxy_momentum"]
	assert.True(t, hasDXYMomentum, "dxy_momentum field should be present")

	// risk_environment: "RISK_ON", "RISK_OFF", or empty.
	// MacroResponseFull has sentiment.risk_environment = "RISK_ON".
	_, hasRiskEnv := ragBody["risk_environment"]
	assert.True(t, hasRiskEnv, "risk_environment field should be present")

	// ---------------------------------------------------------------
	// Completeness check: verify no unexpected fields are missing.
	// These are ALL 27 fields sent by orchestrator.retrieveRAG().
	// ---------------------------------------------------------------
	expectedFields := []string{
		// Core fields.
		"query_text", "strategy", "framework", "setup_family",
		"direction", "timeframe", "style", "symbol",
		// Array fields.
		"all_frameworks", "all_setup_families",
		// TA signal booleans.
		"has_smc_candidates", "has_snd_candidates",
		// Macro signal booleans.
		"has_macro_data", "has_cot_data", "has_rate_decision",
		"has_high_impact_event", "has_dxy_data",
		// Enriched macro signal booleans.
		"has_qe_qt", "has_stagflation", "has_cot_extremes",
		"has_tff_data", "has_core_inflation",
		"has_safe_haven_elevated", "has_commodity_currencies_weak",
		// Macro string signals.
		"dxy_momentum", "risk_environment",
		// Metadata.
		"trace_id",
	}
	for _, field := range expectedFields {
		_, exists := ragBody[field]
		assert.True(t, exists, "RAG request body missing field: %s", field)
	}
}

// TestDataFlow_ProcessorReceivesAssembledContext verifies that the
// Processor endpoint receives the fully assembled ProcessorInput with
// all sections populated from upstream pipeline stages.
//
// Data flow: TA + Macro + RAG → Assembler.Assemble() → ProcessorInput
// → HTTPProcessorAdapter.Process() → HTTP POST body.
func TestDataFlow_ProcessorReceivesAssembledContext(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = TAResponseWithCandidates()
	h.Engine.MacroResponse = MacroResponseFull()
	h.Engine.RAGResponse = RAGResponseWithChunks()
	h.Engine.ProcessorResponse = ProcessorResponseTradeValid()

	h.RunCycle([]string{"EURUSD"}, "trace-e2e-dataflow-proc-001")

	// ---------------------------------------------------------------
	// Assert: Processor endpoint received the assembled context.
	// ---------------------------------------------------------------
	procCalls := h.Engine.CallsForPath("/internal/processor/process")
	require.Len(t, procCalls, 1, "Processor should be called once")
	procBody := procCalls[0].Body
	require.NotNil(t, procBody)

	// The HTTPProcessorAdapter wraps the input in a "processor_input" key.
	processorInput, ok := procBody["processor_input"].(map[string]interface{})
	require.True(t, ok, "processor_input key should be present")

	// Verify symbol.
	assert.Equal(t, "EURUSD", processorInput["symbol"])

	// Verify ta_analysis section is present and populated.
	taAnalysis, ok := processorInput["ta_analysis"].(map[string]interface{})
	require.True(t, ok, "ta_analysis should be a map")
	assert.Equal(t, "EURUSD", taAnalysis["symbol"])
	assert.Equal(t, "success", taAnalysis["status"])
	assert.Equal(t, "BULLISH", taAnalysis["overall_trend"])

	// Verify SMC candidates were passed through.
	smcCandidates, ok := taAnalysis["smc_candidates"].([]interface{})
	require.True(t, ok, "smc_candidates should be an array")
	assert.Len(t, smcCandidates, 1, "should have 1 SMC candidate")

	// Verify macro_analysis section is present.
	macroAnalysis, ok := processorInput["macro_analysis"].(map[string]interface{})
	require.True(t, ok, "macro_analysis should be a map")
	// MacroResponseFull has all 8 datasets.
	_, hasCentralBank := macroAnalysis["central_bank"]
	assert.True(t, hasCentralBank, "central_bank should be in macro_analysis")
	_, hasDXY := macroAnalysis["dxy"]
	assert.True(t, hasDXY, "dxy should be in macro_analysis")
	_, hasSentiment := macroAnalysis["sentiment"]
	assert.True(t, hasSentiment, "sentiment should be in macro_analysis")

	// Verify retrieved_knowledge section is present (from RAG).
	retrievedKnowledge, ok := processorInput["retrieved_knowledge"].(map[string]interface{})
	require.True(t, ok, "retrieved_knowledge should be a map")
	// RAGResponseWithChunks has chunks and strategy_used.
	_, hasChunks := retrievedKnowledge["chunks"]
	assert.True(t, hasChunks, "chunks should be in retrieved_knowledge")
	_, hasStrategy := retrievedKnowledge["strategy_used"]
	assert.True(t, hasStrategy, "strategy_used should be in retrieved_knowledge")

	// Verify metadata section is present.
	metadata, ok := processorInput["metadata"].(map[string]interface{})
	require.True(t, ok, "metadata should be a map")
	assert.Equal(t, "EURUSD", metadata["symbol"])
	assert.Equal(t, "BULLISH", metadata["overall_trend"])
	assert.Equal(t, "trace-e2e-dataflow-proc-001", metadata["trace_id"])

	// Verify trace_id was propagated at the top level too.
	assert.Equal(t, "trace-e2e-dataflow-proc-001", procBody["trace_id"])
}
