package context

import (
	"testing"

	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
)

// ── Assembler Tests ─────────────────────────────────────────────────────────

func TestAssemble_BasicStructure(t *testing.T) {
	assembler := NewAssembler()

	ta := &models.TASymbolResult{
		Symbol:        "EURUSD",
		HTFTimeframes: []string{"1D", "4H"},
		LTFTimeframes: []string{"M15", "M1"},
		Status:        "success",
		OverallTrend:  "BULLISH",
		SMCCandidates: []map[string]interface{}{
			{"type": "OB", "direction": "LONG"},
		},
		SnDCandidates: []map[string]interface{}{},
		Snapshots: map[string]map[string]interface{}{
			"4H": {"trend": "bullish"},
		},
		Alignment: map[string]map[string]interface{}{
			"overall": {"direction": "bullish"},
		},
	}

	macro := &models.MacroResult{
		CentralBank: map[string]interface{}{"fed": "hawkish"},
		DXY:         map[string]interface{}{"value": 104.5},
	}

	ragBundle := map[string]interface{}{
		"chunks":                []interface{}{"rule1", "rule2"},
		"strategy_used":         "scenario_first",
		"total_chunks_returned": 5,
	}

	result := assembler.Assemble("EURUSD", ta, macro, ragBundle, "trace-001")

	// Verify top-level structure.
	if result.Symbol != "EURUSD" {
		t.Fatalf("expected symbol EURUSD, got %s", result.Symbol)
	}
	if result.TAAnalysis == nil {
		t.Fatal("ta_analysis should not be nil")
	}
	if result.MacroAnalysis == nil {
		t.Fatal("macro_analysis should not be nil")
	}
	if result.RetrievedKnowledge == nil {
		t.Fatal("retrieved_knowledge should not be nil")
	}
	if result.Metadata == nil {
		t.Fatal("metadata should not be nil")
	}
}

func TestAssemble_TASection(t *testing.T) {
	assembler := NewAssembler()

	ta := &models.TASymbolResult{
		Symbol:        "GBPUSD",
		HTFTimeframes: []string{"1W", "1D"},
		LTFTimeframes: []string{"M5"},
		Status:        "success",
		OverallTrend:  "BEARISH",
		SMCCandidates: []map[string]interface{}{
			{"type": "BMS", "direction": "SHORT"},
		},
		SnDCandidates: []map[string]interface{}{
			{"type": "QML", "direction": "SHORT"},
		},
		Snapshots: map[string]map[string]interface{}{},
		Alignment: map[string]map[string]interface{}{},
	}

	macro := &models.MacroResult{}
	ragBundle := map[string]interface{}{}

	result := assembler.Assemble("GBPUSD", ta, macro, ragBundle, "trace-002")

	taSection := result.TAAnalysis
	if taSection["symbol"] != "GBPUSD" {
		t.Fatalf("expected TA symbol GBPUSD, got %v", taSection["symbol"])
	}
	if taSection["overall_trend"] != "BEARISH" {
		t.Fatalf("expected overall_trend BEARISH, got %v", taSection["overall_trend"])
	}

	smcCandidates, ok := taSection["smc_candidates"].([]map[string]interface{})
	if !ok || len(smcCandidates) != 1 {
		t.Fatalf("expected 1 SMC candidate, got %v", taSection["smc_candidates"])
	}

	sndCandidates, ok := taSection["snd_candidates"].([]map[string]interface{})
	if !ok || len(sndCandidates) != 1 {
		t.Fatalf("expected 1 SnD candidate, got %v", taSection["snd_candidates"])
	}
}

func TestAssemble_MacroSection(t *testing.T) {
	assembler := NewAssembler()

	ta := &models.TASymbolResult{
		Symbol:       "AUDUSD",
		Status:       "success",
		OverallTrend: "NEUTRAL",
		Snapshots:    map[string]map[string]interface{}{},
		Alignment:    map[string]map[string]interface{}{},
	}

	macro := &models.MacroResult{
		CentralBank: map[string]interface{}{"rba": "hawkish"},
		COT:         map[string]interface{}{"aud_net": 15000},
		DXY:         map[string]interface{}{"value": 103.2, "momentum": "FALLING"},
		Sentiment:   map[string]interface{}{"risk": "RISK_ON"},
	}

	ragBundle := map[string]interface{}{}
	result := assembler.Assemble("AUDUSD", ta, macro, ragBundle, "trace-003")

	macroSection := result.MacroAnalysis
	if macroSection["central_bank"] == nil {
		t.Fatal("expected central_bank in macro section")
	}
	if macroSection["cot"] == nil {
		t.Fatal("expected cot in macro section")
	}
	if macroSection["dxy"] == nil {
		t.Fatal("expected dxy in macro section")
	}
	if macroSection["sentiment"] == nil {
		t.Fatal("expected sentiment in macro section")
	}

	available, ok := macroSection["datasets_available"].([]string)
	if !ok {
		t.Fatal("expected datasets_available to be []string")
	}
	if len(available) != 4 {
		t.Fatalf("expected 4 available datasets, got %d: %v", len(available), available)
	}
}

func TestAssemble_RAGMetadataPropagation(t *testing.T) {
	assembler := NewAssembler()

	ta := &models.TASymbolResult{
		Symbol:       "NZDUSD",
		Status:       "success",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
		Alignment:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}

	ragBundle := map[string]interface{}{
		"strategy_used":         "hybrid",
		"coverage_result":       "FULL",
		"total_chunks_returned": float64(12),
		"coverage_gaps":         []interface{}{"risk_management"},
	}

	result := assembler.Assemble("NZDUSD", ta, macro, ragBundle, "trace-004")

	meta := result.Metadata
	if meta["rag_strategy_used"] != "hybrid" {
		t.Fatalf("expected rag_strategy_used 'hybrid', got %v", meta["rag_strategy_used"])
	}
	if meta["rag_coverage_result"] != "FULL" {
		t.Fatalf("expected rag_coverage_result 'FULL', got %v", meta["rag_coverage_result"])
	}
	if meta["rag_total_chunks_returned"] != float64(12) {
		t.Fatalf("expected rag_total_chunks_returned 12, got %v", meta["rag_total_chunks_returned"])
	}
}

func TestAssemble_MetadataContainsTraceID(t *testing.T) {
	assembler := NewAssembler()

	ta := &models.TASymbolResult{
		Symbol:       "EURUSD",
		Status:       "success",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
		Alignment:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}
	ragBundle := map[string]interface{}{}

	result := assembler.Assemble("EURUSD", ta, macro, ragBundle, "trace-999")

	if result.Metadata["trace_id"] != "trace-999" {
		t.Fatalf("expected trace_id 'trace-999', got %v", result.Metadata["trace_id"])
	}
	if result.Metadata["symbol"] != "EURUSD" {
		t.Fatalf("expected symbol in metadata, got %v", result.Metadata["symbol"])
	}
}
