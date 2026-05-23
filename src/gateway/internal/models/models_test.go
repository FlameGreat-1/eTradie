package models

import (
	"testing"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
)

// =============================================================================
// TAResult.HasCandidates()
// =============================================================================

func TestHasCandidates_NoSymbolResults(t *testing.T) {
	r := &TAResult{}
	if r.HasCandidates() {
		t.Fatal("empty TAResult should have no candidates")
	}
}

func TestHasCandidates_AllSymbolsFailed(t *testing.T) {
	r := &TAResult{
		SymbolResults: []TASymbolResult{
			{Symbol: "EURUSD", Status: "error", SMCCandidates: []map[string]interface{}{{"id": "1"}}},
			{Symbol: "GBPUSD", Status: "insufficient_data"},
		},
	}
	if r.HasCandidates() {
		t.Fatal("candidates on failed symbols should not count")
	}
}

func TestHasCandidates_SuccessButNoCandidates(t *testing.T) {
	r := &TAResult{
		SymbolResults: []TASymbolResult{
			{Symbol: "EURUSD", Status: "success", SMCCandidates: nil, SnDCandidates: nil},
			{Symbol: "GBPUSD", Status: "success", SMCCandidates: []map[string]interface{}{}, SnDCandidates: []map[string]interface{}{}},
		},
	}
	if r.HasCandidates() {
		t.Fatal("success with empty candidate slices should return false")
	}
}

func TestHasCandidates_SMCOnly(t *testing.T) {
	r := &TAResult{
		SymbolResults: []TASymbolResult{
			{
				Symbol: "EURUSD",
				Status: "success",
				SMCCandidates: []map[string]interface{}{
					{"analysis_id": "SMC-001", "direction": "LONG"},
				},
			},
		},
	}
	if !r.HasCandidates() {
		t.Fatal("SMC candidates on successful symbol should return true")
	}
}

func TestHasCandidates_SnDOnly(t *testing.T) {
	r := &TAResult{
		SymbolResults: []TASymbolResult{
			{
				Symbol: "GBPUSD",
				Status: "success",
				SnDCandidates: []map[string]interface{}{
					{"analysis_id": "SND-001", "direction": "SHORT"},
				},
			},
		},
	}
	if !r.HasCandidates() {
		t.Fatal("SnD candidates on successful symbol should return true")
	}
}

func TestHasCandidates_BothFrameworks(t *testing.T) {
	r := &TAResult{
		SymbolResults: []TASymbolResult{
			{
				Symbol:        "XAUUSD",
				Status:        "success",
				SMCCandidates: []map[string]interface{}{{"id": "1"}},
				SnDCandidates: []map[string]interface{}{{"id": "2"}},
			},
		},
	}
	if !r.HasCandidates() {
		t.Fatal("both SMC and SnD candidates should return true")
	}
}

func TestHasCandidates_MixedSuccessAndError(t *testing.T) {
	r := &TAResult{
		SymbolResults: []TASymbolResult{
			{Symbol: "EURUSD", Status: "error"},
			{Symbol: "GBPUSD", Status: "success", SMCCandidates: []map[string]interface{}{{"id": "1"}}},
			{Symbol: "USDJPY", Status: "insufficient_data"},
		},
	}
	if !r.HasCandidates() {
		t.Fatal("one successful symbol with candidates should return true")
	}
}

// =============================================================================
// TAResult.SuccessfulSymbols()
// =============================================================================

func TestSuccessfulSymbols_Empty(t *testing.T) {
	r := &TAResult{}
	result := r.SuccessfulSymbols()
	if len(result) != 0 {
		t.Fatalf("expected empty slice, got %v", result)
	}
}

func TestSuccessfulSymbols_AllFailed(t *testing.T) {
	r := &TAResult{
		SymbolResults: []TASymbolResult{
			{Symbol: "EURUSD", Status: "error"},
			{Symbol: "GBPUSD", Status: "insufficient_data"},
		},
	}
	result := r.SuccessfulSymbols()
	if len(result) != 0 {
		t.Fatalf("expected empty slice for all-failed, got %v", result)
	}
}

func TestSuccessfulSymbols_Mixed(t *testing.T) {
	r := &TAResult{
		SymbolResults: []TASymbolResult{
			{Symbol: "EURUSD", Status: "success"},
			{Symbol: "GBPUSD", Status: "error"},
			{Symbol: "USDJPY", Status: "success"},
			{Symbol: "XAUUSD", Status: "insufficient_data"},
		},
	}
	result := r.SuccessfulSymbols()
	if len(result) != 2 {
		t.Fatalf("expected 2 successful symbols, got %d: %v", len(result), result)
	}
	if result[0] != "EURUSD" || result[1] != "USDJPY" {
		t.Fatalf("expected [EURUSD, USDJPY], got %v", result)
	}
}

func TestSuccessfulSymbols_AllSuccess(t *testing.T) {
	r := &TAResult{
		SymbolResults: []TASymbolResult{
			{Symbol: "EURUSD", Status: "success"},
			{Symbol: "GBPUSD", Status: "success"},
		},
	}
	result := r.SuccessfulSymbols()
	if len(result) != 2 {
		t.Fatalf("expected 2, got %d", len(result))
	}
}

// =============================================================================
// MacroResult.AvailableDatasets()
// =============================================================================

func TestAvailableDatasets_AllNil(t *testing.T) {
	r := &MacroResult{}
	result := r.AvailableDatasets()
	if len(result) != 0 {
		t.Fatalf("all-nil MacroResult should return empty, got %v", result)
	}
}

func TestAvailableDatasets_AllPopulated(t *testing.T) {
	r := &MacroResult{
		CentralBank: map[string]interface{}{"rate": 5.25},
		COT:         map[string]interface{}{"net_long": 1000},
		Economic:    map[string]interface{}{"gdp": 2.1},
		Calendar:    map[string]interface{}{"next_event": "NFP"},
		DXY:         map[string]interface{}{"value": 104.5},
		Intermarket: map[string]interface{}{"sp500": 5200},
		Sentiment:   map[string]interface{}{"score": 0.65},
	}
	result := r.AvailableDatasets()
	if len(result) != 7 {
		t.Fatalf("expected 7 datasets, got %d: %v", len(result), result)
	}

	// Verify ordering matches field declaration order.
	expected := []string{
		"central_bank", "cot", "economic",
		"calendar", "dxy", "intermarket", "sentiment",
	}
	for i, name := range expected {
		if result[i] != name {
			t.Errorf("position %d: expected %q, got %q", i, name, result[i])
		}
	}
}

func TestAvailableDatasets_PartialData(t *testing.T) {
	r := &MacroResult{
		CentralBank: map[string]interface{}{"rate": 5.25},
		DXY:         map[string]interface{}{"value": 104.5},
		Sentiment:   map[string]interface{}{"score": 0.65},
	}
	result := r.AvailableDatasets()
	if len(result) != 3 {
		t.Fatalf("expected 3 datasets, got %d: %v", len(result), result)
	}
	if result[0] != "central_bank" || result[1] != "dxy" || result[2] != "sentiment" {
		t.Fatalf("expected [central_bank, dxy, sentiment], got %v", result)
	}
}

func TestAvailableDatasets_OnlyCalendar(t *testing.T) {
	r := &MacroResult{
		Calendar: map[string]interface{}{"events": []string{"FOMC"}},
	}
	result := r.AvailableDatasets()
	if len(result) != 1 || result[0] != "calendar" {
		t.Fatalf("expected [calendar], got %v", result)
	}
}

// =============================================================================
// GuardEvaluationResult.IsApproved()
// =============================================================================

func TestIsApproved_PassVerdict(t *testing.T) {
	r := &GuardEvaluationResult{
		OverallVerdict: constants.VerdictPass,
	}
	if !r.IsApproved() {
		t.Fatal("PASS verdict should be approved")
	}
}

func TestIsApproved_RejectVerdict(t *testing.T) {
	r := &GuardEvaluationResult{
		OverallVerdict: constants.VerdictReject,
		BlockingRules:  []string{"MR-REJECT-001"},
	}
	if r.IsApproved() {
		t.Fatal("REJECT verdict should not be approved")
	}
}

func TestIsApproved_WarnVerdict(t *testing.T) {
	r := &GuardEvaluationResult{
		OverallVerdict: constants.VerdictWarn,
	}
	if !r.IsApproved() {
		t.Log("WARN verdict should be approved (advisory only, no hard rejection)")
		t.Fatal("WARN verdict should be approved")
	}
}

func TestIsApproved_EmptyVerdict(t *testing.T) {
	r := &GuardEvaluationResult{}
	if r.IsApproved() {
		t.Fatal("empty verdict should not be approved")
	}
}

func TestIsApproved_WithChecks(t *testing.T) {
	r := &GuardEvaluationResult{
		OverallVerdict: constants.VerdictPass,
		Checks: []GuardCheckResult{
			{Rule: constants.RuleHighImpactEventProximity, Verdict: constants.VerdictPass, Reason: "no high-impact events"},
			{Rule: constants.RuleSessionRestriction, Verdict: constants.VerdictPass, Reason: "within trading hours"},
			{Rule: constants.RuleCounterTrendNoChoch, Verdict: constants.VerdictPass, Reason: "aligned with trend"},
		},
	}
	if !r.IsApproved() {
		t.Fatal("all-PASS checks with PASS overall should be approved")
	}
}

func TestIsApproved_RejectWithMultipleBlockingRules(t *testing.T) {
	r := &GuardEvaluationResult{
		OverallVerdict: constants.VerdictReject,
		BlockingRules:  []string{"MR-REJECT-001", "MR-REJECT-002"},
		Checks: []GuardCheckResult{
			{Rule: constants.RuleHighImpactEventProximity, Verdict: constants.VerdictReject, Reason: "FOMC in 15 minutes"},
			{Rule: constants.RuleSessionRestriction, Verdict: constants.VerdictReject, Reason: "weekend"},
		},
	}
	if r.IsApproved() {
		t.Fatal("REJECT with blocking rules should not be approved")
	}
	if len(r.BlockingRules) != 2 {
		t.Fatalf("expected 2 blocking rules, got %d", len(r.BlockingRules))
	}
}
