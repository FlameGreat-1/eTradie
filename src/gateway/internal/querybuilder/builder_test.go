package querybuilder

import (
	"strings"
	"testing"

	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
)

// ── Strategy Selection Tests ────────────────────────────────────────────────

func TestBuild_RuleFirstStrategy_NFPEvent(t *testing.T) {
	builder := NewBuilder()

	ta := &models.TASymbolResult{
		Symbol:        "EURUSD",
		Status:        "success",
		OverallTrend:  "BULLISH",
		HTFTimeframes: []string{"1D", "4H"},
		SMCCandidates: []map[string]interface{}{{"type": "OB"}},
		Snapshots:     map[string]map[string]interface{}{},
		Alignment:     map[string]map[string]interface{}{},
	}

	macro := &models.MacroResult{
		Calendar: map[string]interface{}{
			"events": []interface{}{
				map[string]interface{}{
					"event_name": "Non-Farm Payrolls",
					"impact":     "HIGH",
					"event_time": "2025-01-01T13:30:00+00:00",
				},
			},
		},
	}

	params := builder.Build(ta, macro, "", "trace-001")

	if params.Strategy != "rule_first" {
		t.Fatalf("expected strategy 'rule_first' for NFP event, got %s", params.Strategy)
	}
}

func TestBuild_ScenarioFirstStrategy_WhenFrameworkAndSetupPresent(t *testing.T) {
	builder := NewBuilder()

	ta := &models.TASymbolResult{
		Symbol:        "GBPUSD",
		Status:        "success",
		OverallTrend:  "BULLISH",
		HTFTimeframes: []string{"1D"},
		SMCCandidates: []map[string]interface{}{
			{
				"framework":         "smc",
				"setup_family":      "order_block_mitigation",
				"direction":         "long",
				"order_block_upper": true,
			},
		},
		Snapshots: map[string]map[string]interface{}{
			"4H": {"bms_events": []interface{}{"bms1"}},
		},
		Alignment: map[string]map[string]interface{}{},
	}

	macro := &models.MacroResult{}

	params := builder.Build(ta, macro, "", "trace-002")

	// With framework, setup family, and direction present, strategy should be scenario_first.
	if params.Strategy != "scenario_first" {
		t.Fatalf("expected 'scenario_first' for framework+setup combo, got %s", params.Strategy)
	}
}

func TestBuild_HybridStrategy_Default(t *testing.T) {
	builder := NewBuilder()

	ta := &models.TASymbolResult{
		Symbol:       "NZDUSD",
		Status:       "success",
		OverallTrend: "NEUTRAL",
		Snapshots:    map[string]map[string]interface{}{},
		Alignment:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}

	params := builder.Build(ta, macro, "", "trace-003")

	if params.Strategy != "hybrid" {
		t.Fatalf("expected 'hybrid' strategy as default, got %s", params.Strategy)
	}
}

// ── Query Text Tests ────────────────────────────────────────────────────────

func TestBuild_QueryTextContainsSymbol(t *testing.T) {
	builder := NewBuilder()

	ta := &models.TASymbolResult{
		Symbol:       "USDJPY",
		Status:       "success",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
		Alignment:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}

	params := builder.Build(ta, macro, "", "trace-004")

	if !strings.Contains(params.QueryText, "USDJPY") {
		t.Fatalf("expected query text to contain 'USDJPY', got: %s", params.QueryText)
	}
}

// ── Boolean Flags Tests ─────────────────────────────────────────────────────

func TestBuild_SMCFlags(t *testing.T) {
	builder := NewBuilder()

	ta := &models.TASymbolResult{
		Symbol:       "EURUSD",
		Status:       "success",
		OverallTrend: "BULLISH",
		SMCCandidates: []map[string]interface{}{
			{
				"type":              "OB",
				"direction":         "LONG",
				"bms_detected":      true,
				"order_block_upper": true,
			},
		},
		Snapshots: map[string]map[string]interface{}{
			"4H": {
				"trend_direction": "BULLISH",
			},
		},
		Alignment: map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}

	params := builder.Build(ta, macro, "", "trace-005")

	if !params.HasSMCCandidates {
		t.Fatal("expected HasSMCCandidates to be true when BMS and OB are present")
	}
}

func TestBuild_MacroFlags_DXYPresent(t *testing.T) {
	builder := NewBuilder()

	ta := &models.TASymbolResult{
		Symbol:       "EURUSD",
		Status:       "success",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
		Alignment:    map[string]map[string]interface{}{},
	}
	dxyVal := 104.5
	macro := &models.MacroResult{
		DXY: map[string]interface{}{
			"latest": map[string]interface{}{
				"value":    dxyVal,
				"momentum": "RISING",
			},
		},
	}

	params := builder.Build(ta, macro, "", "trace-006")

	if !params.HasDXYData {
		t.Fatal("expected HasDXYData true when DXY data is present")
	}
}

func TestBuild_MacroFlags_QEQTPresent(t *testing.T) {
	builder := NewBuilder()

	ta := &models.TASymbolResult{
		Symbol:       "EURUSD",
		Status:       "success",
		OverallTrend: "NEUTRAL",
		Snapshots:    map[string]map[string]interface{}{},
		Alignment:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{
		CentralBank: map[string]interface{}{
			"qe_qt": map[string]interface{}{
				"action": "QT",
				"bank":   "Federal Reserve",
			},
		},
	}

	params := builder.Build(ta, macro, "", "trace-007")

	// Strategy should be rule_first due to QE/QT presence.
	if params.HasQEQT && params.Strategy != "rule_first" {
		t.Fatalf("expected rule_first strategy with QE/QT, got %s", params.Strategy)
	}
}

// ── Framework Collection Tests ──────────────────────────────────────────────

func TestBuild_AllFrameworksAlwaysIncludesWyckoff(t *testing.T) {
	builder := NewBuilder()

	ta := &models.TASymbolResult{
		Symbol:       "AUDUSD",
		Status:       "success",
		OverallTrend: "NEUTRAL",
		Snapshots:    map[string]map[string]interface{}{},
		Alignment:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}

	params := builder.Build(ta, macro, "", "trace-008")

	found := false
	for _, fw := range params.AllFrameworks {
		if fw == "wyckoff" {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("expected 'wyckoff' in AllFrameworks, got %v", params.AllFrameworks)
	}
}

func TestBuild_SymbolPassthrough(t *testing.T) {
	builder := NewBuilder()

	ta := &models.TASymbolResult{
		Symbol:       "CADJPY",
		Status:       "success",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
		Alignment:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}

	params := builder.Build(ta, macro, "intraday", "trace-009")

	if params.Symbol != "CADJPY" {
		t.Fatalf("expected Symbol 'CADJPY', got %s", params.Symbol)
	}
	if params.Style != "intraday" {
		t.Fatalf("expected Style 'intraday', got %s", params.Style)
	}
}
