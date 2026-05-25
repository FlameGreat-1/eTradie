package routing

import (
	"testing"
	"time"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
)

// ── High-Impact Event Proximity Guard ───────────────────────────────────────

func TestCheckHighImpactEventProximity_NoCalendar(t *testing.T) {
	macro := &models.MacroResult{}
	result := checkHighImpactEventProximity(macro)

	if result.Verdict != constants.VerdictPass {
		t.Fatalf("expected PASS when calendar is nil, got %s", result.Verdict)
	}
}

func TestCheckHighImpactEventProximity_NoHighImpactEvents(t *testing.T) {
	macro := &models.MacroResult{
		Calendar: map[string]interface{}{
			"events": []interface{}{
				map[string]interface{}{"impact": "LOW", "event_name": "Trade Balance"},
			},
		},
	}
	result := checkHighImpactEventProximity(macro)

	if result.Verdict != constants.VerdictPass {
		t.Fatalf("expected PASS for LOW impact events, got %s: %s", result.Verdict, result.Reason)
	}
}

func TestCheckHighImpactEventProximity_HighImpactWithinLockout(t *testing.T) {
	futureTime := time.Now().UTC().Add(15 * time.Minute).Format(time.RFC3339)
	macro := &models.MacroResult{
		Calendar: map[string]interface{}{
			"events": []interface{}{
				map[string]interface{}{
					"impact":     "HIGH",
					"event_name": "Non-Farm Payrolls",
					"event_time": futureTime,
				},
			},
		},
	}
	result := checkHighImpactEventProximity(macro)

	if result.Verdict != constants.VerdictReject {
		t.Fatalf("expected REJECT for HIGH impact within lockout, got %s: %s", result.Verdict, result.Reason)
	}
	if result.Metadata == nil {
		t.Fatal("expected metadata with event_name")
	}
	if result.Metadata["event_name"] != "Non-Farm Payrolls" {
		t.Fatalf("expected event_name 'Non-Farm Payrolls', got %v", result.Metadata["event_name"])
	}
}

func TestCheckHighImpactEventProximity_HighImpactOutsideLockout(t *testing.T) {
	futureTime := time.Now().UTC().Add(60 * time.Minute).Format(time.RFC3339)
	macro := &models.MacroResult{
		Calendar: map[string]interface{}{
			"events": []interface{}{
				map[string]interface{}{
					"impact":     "HIGH",
					"event_name": "FOMC Rate Decision",
					"event_time": futureTime,
				},
			},
		},
	}
	result := checkHighImpactEventProximity(macro)

	if result.Verdict != constants.VerdictPass {
		t.Fatalf("expected PASS for HIGH impact outside lockout, got %s: %s", result.Verdict, result.Reason)
	}
}

// ── Counter-Trend Guard ─────────────────────────────────────────────────────

func TestCheckCounterTrend_NoTrade(t *testing.T) {
	processor := &models.ProcessorOutput{TradeValid: false}
	ta := &models.TASymbolResult{Symbol: "EURUSD", OverallTrend: "BULLISH"}
	result := checkCounterTrend(processor, ta)

	if result.Verdict != constants.VerdictPass {
		t.Fatalf("expected PASS when trade is not valid, got %s", result.Verdict)
	}
}

func TestCheckCounterTrend_AlignedTrade(t *testing.T) {
	processor := &models.ProcessorOutput{TradeValid: true, Direction: "LONG"}
	ta := &models.TASymbolResult{Symbol: "EURUSD", OverallTrend: "BULLISH"}
	result := checkCounterTrend(processor, ta)

	if result.Verdict != constants.VerdictPass {
		t.Fatalf("expected PASS for aligned LONG + BULLISH, got %s: %s", result.Verdict, result.Reason)
	}
}

func TestCheckCounterTrend_CounterWithoutChoch_Reject(t *testing.T) {
	processor := &models.ProcessorOutput{TradeValid: true, Direction: "SHORT"}
	ta := &models.TASymbolResult{
		Symbol:       "EURUSD",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
	}
	result := checkCounterTrend(processor, ta)

	if result.Verdict != constants.VerdictReject {
		t.Fatalf("expected REJECT for counter-trend SHORT vs BULLISH without CHoCH, got %s: %s", result.Verdict, result.Reason)
	}
}

func TestCheckCounterTrend_CounterWithChoch_Warn(t *testing.T) {
	processor := &models.ProcessorOutput{TradeValid: true, Direction: "SHORT"}
	ta := &models.TASymbolResult{
		Symbol:       "EURUSD",
		OverallTrend: "BULLISH",
		Snapshots: map[string]map[string]interface{}{
			"4H": {"choch_events": []interface{}{"choch1", "choch2"}},
		},
	}
	result := checkCounterTrend(processor, ta)

	if result.Verdict != constants.VerdictWarn {
		t.Fatalf("expected WARN for counter-trend with CHoCH, got %s: %s", result.Verdict, result.Reason)
	}
}

func TestCheckCounterTrend_BearishTrendLongDirection_Reject(t *testing.T) {
	processor := &models.ProcessorOutput{TradeValid: true, Direction: "LONG"}
	ta := &models.TASymbolResult{
		Symbol:       "GBPUSD",
		OverallTrend: "BEARISH",
		Snapshots:    map[string]map[string]interface{}{},
	}
	result := checkCounterTrend(processor, ta)

	if result.Verdict != constants.VerdictReject {
		t.Fatalf("expected REJECT for LONG trade against BEARISH trend without CHoCH, got %s", result.Verdict)
	}
}

// ── Weekend Gap Risk Guard ──────────────────────────────────────────────────
// Note: These tests verify the logic but are time-dependent. In a CI
// environment, use a time injection pattern. For now, these validate
// the static branches.

func TestCheckWeekendGapRisk_Weekday(t *testing.T) {
	ta := &models.TASymbolResult{Symbol: "EURUSD"}
	result := checkWeekendGapRisk(ta)
	now := time.Now().UTC()

	if now.Weekday() >= time.Monday && now.Weekday() <= time.Thursday {
		if result.Verdict != constants.VerdictPass {
			t.Fatalf("expected PASS on weekday %s, got %s", now.Weekday(), result.Verdict)
		}
	}
	if now.Weekday() == time.Saturday || now.Weekday() == time.Sunday {
		if result.Verdict != constants.VerdictReject {
			t.Fatalf("expected REJECT on %s, got %s", now.Weekday(), result.Verdict)
		}
	}
}

// ── Low Liquidity Guard ─────────────────────────────────────────────────────

func TestCheckLowLiquidityHours(t *testing.T) {
	ta := &models.TASymbolResult{Symbol: "EURUSD"}
	result := checkLowLiquidityHours(ta)
	hour := time.Now().UTC().Hour()

	if hour >= 21 || hour < 1 {
		if result.Verdict != constants.VerdictWarn {
			t.Fatalf("expected WARN during low liquidity hours (hour=%d), got %s", hour, result.Verdict)
		}
	} else {
		if result.Verdict != constants.VerdictPass {
			t.Fatalf("expected PASS during normal hours (hour=%d), got %s", hour, result.Verdict)
		}
	}
}

// ── Full Guard Evaluator ────────────────────────────────────────────────────

func TestGuardEvaluator_AllPassOnAlignedTrade(t *testing.T) {
	eval := NewGuardEvaluator()

	futureTime := time.Now().UTC().Add(2 * time.Hour).Format(time.RFC3339)
	processor := &models.ProcessorOutput{TradeValid: true, Direction: "LONG", Confidence: 0.85, Grade: "A"}
	ta := &models.TASymbolResult{
		Symbol:       "USDJPY",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{
		Calendar: map[string]interface{}{
			"events": []interface{}{
				map[string]interface{}{
					"impact": "HIGH", "event_name": "CPI", "event_time": futureTime,
				},
			},
		},
	}

	result := eval.Evaluate(processor, ta, macro, "test-trace-001")

	now := time.Now().UTC()
	isAsian := now.Hour() >= 0 && now.Hour() < 7
	isWeekend := now.Weekday() == time.Saturday || now.Weekday() == time.Sunday
	isFriLate := now.Weekday() == time.Friday && now.Hour() >= 20

	if !isAsian && !isWeekend && !isFriLate {
		if result.OverallVerdict == constants.VerdictReject {
			t.Fatalf("expected non-REJECT verdict for aligned trade during active hours, got REJECT: blocking=%v", result.BlockingRules)
		}
	}

	if len(result.Checks) != 5 {
		t.Fatalf("expected 5 guard checks, got %d", len(result.Checks))
	}
}

func TestGuardEvaluator_CounterTrendRejectsWithoutChoch(t *testing.T) {
	eval := NewGuardEvaluator()

	processor := &models.ProcessorOutput{TradeValid: true, Direction: "SHORT", Confidence: 0.7, Grade: "B"}
	ta := &models.TASymbolResult{
		Symbol:       "EURUSD",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
	}
	macro := &models.MacroResult{}

	result := eval.Evaluate(processor, ta, macro, "test-trace-002")

	found := false
	for _, rule := range result.BlockingRules {
		if rule == string(constants.RuleCounterTrendNoChoch) {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("expected MR-REJECT-006 in blocking rules, got %v", result.BlockingRules)
	}
}

// ── Pre-LLM / Post-LLM split ────────────────────────────────────────────────

func TestEvaluatePreLLM_ContainsOnlyDeterministicChecks(t *testing.T) {
	eval := NewGuardEvaluator()
	ta := &models.TASymbolResult{Symbol: "EURUSD", OverallTrend: "BULLISH"}
	macro := &models.MacroResult{}

	result := eval.EvaluatePreLLM(ta, macro, "trace-pre-001")

	if len(result.Checks) != 4 {
		t.Fatalf("expected 4 pre-LLM checks, got %d", len(result.Checks))
	}
	for _, c := range result.Checks {
		if c.Rule == constants.RuleCounterTrendNoChoch {
			t.Fatalf("counter-trend (MR-REJECT-006) must NOT appear in pre-LLM checks")
		}
	}
}

func TestEvaluatePostLLM_ContainsOnlyCounterTrend(t *testing.T) {
	eval := NewGuardEvaluator()
	processor := &models.ProcessorOutput{TradeValid: true, Direction: "LONG"}
	ta := &models.TASymbolResult{
		Symbol:       "EURUSD",
		OverallTrend: "BULLISH",
		Snapshots:    map[string]map[string]interface{}{},
	}

	result := eval.EvaluatePostLLM(processor, ta, "trace-post-001")

	if len(result.Checks) != 1 {
		t.Fatalf("expected exactly 1 post-LLM check, got %d", len(result.Checks))
	}
	if result.Checks[0].Rule != constants.RuleCounterTrendNoChoch {
		t.Fatalf("expected post-LLM check to be MR-REJECT-006, got %s", result.Checks[0].Rule)
	}
}

func TestMergeResults_PreservesCanonicalOrder(t *testing.T) {
	eval := NewGuardEvaluator()
	processor := &models.ProcessorOutput{TradeValid: true, Direction: "LONG"}
	ta := &models.TASymbolResult{Symbol: "USDJPY", OverallTrend: "BULLISH", Snapshots: map[string]map[string]interface{}{}}
	macro := &models.MacroResult{}

	pre := eval.EvaluatePreLLM(ta, macro, "trace-merge-001")
	post := eval.EvaluatePostLLM(processor, ta, "trace-merge-001")
	merged := MergeResults(pre, post)

	if len(merged.Checks) != 5 {
		t.Fatalf("expected 5 merged checks, got %d", len(merged.Checks))
	}
	want := []constants.GuardRule{
		constants.RuleHighImpactEventProximity,
		constants.RuleSessionRestriction,
		constants.RuleCounterTrendNoChoch,
		constants.RuleWeekendGapRisk,
		constants.RuleLowLiquidityHours,
	}
	for i, rule := range want {
		if merged.Checks[i].Rule != rule {
			t.Fatalf("merged checks not in canonical order: at index %d want %s, got %s", i, rule, merged.Checks[i].Rule)
		}
	}
}

func TestMergeResults_PreLLMRejectStillRejectsAfterMerge(t *testing.T) {
	pre := &models.GuardEvaluationResult{
		Checks: []models.GuardCheckResult{
			{Rule: constants.RuleSessionRestriction, Verdict: constants.VerdictReject, Reason: "Asian session"},
		},
	}
	post := &models.GuardEvaluationResult{
		Checks: []models.GuardCheckResult{
			{Rule: constants.RuleCounterTrendNoChoch, Verdict: constants.VerdictPass, Reason: "aligned"},
		},
	}
	merged := MergeResults(pre, post)
	if merged.OverallVerdict != constants.VerdictReject {
		t.Fatalf("expected REJECT after merge with pre-LLM reject, got %s", merged.OverallVerdict)
	}
	found := false
	for _, r := range merged.BlockingRules {
		if r == string(constants.RuleSessionRestriction) {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected MR-REJECT-002 in merged blocking rules, got %v", merged.BlockingRules)
	}
}
