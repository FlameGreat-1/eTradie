package routing

import (
	"testing"
	"time"

	"github.com/flamegreat/etradie/src/gateway/internal/constants"
	"github.com/flamegreat/etradie/src/gateway/internal/models"
)

// ── News Proximity Guard ────────────────────────────────────────────────────

func TestCheckNewsProximity_NoCalendar(t *testing.T) {
	macro := &models.MacroResult{}
	result := checkNewsProximity(macro)

	if result.Verdict != constants.VerdictPass {
		t.Fatalf("expected PASS when calendar is nil, got %s", result.Verdict)
	}
}

func TestCheckNewsProximity_NoHighImpactEvents(t *testing.T) {
	macro := &models.MacroResult{
		Calendar: map[string]interface{}{
			"events": []interface{}{
				map[string]interface{}{"impact": "LOW", "event_name": "Trade Balance"},
			},
		},
	}
	result := checkNewsProximity(macro)

	if result.Verdict != constants.VerdictPass {
		t.Fatalf("expected PASS for LOW impact events, got %s: %s", result.Verdict, result.Reason)
	}
}

func TestCheckNewsProximity_HighImpactWithinLockout(t *testing.T) {
	// Schedule a HIGH-impact event 15 minutes from now — within the 30-min lockout.
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
	result := checkNewsProximity(macro)

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

func TestCheckNewsProximity_HighImpactOutsideLockout(t *testing.T) {
	// Schedule a HIGH-impact event 60 minutes from now — outside 30-min lockout.
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
	result := checkNewsProximity(macro)

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
		Snapshots:    map[string]map[string]interface{}{}, // no choch_events
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
// Note: These tests verify the logic but are time-dependent.
// In a CI environment, use a time injection pattern. For now, these validate
// the static branches.

func TestCheckWeekendGapRisk_Weekday(t *testing.T) {
	// This test checks the non-weekend branch.
	// If today is a weekday before Friday 20:00 UTC, this will pass.
	result := checkWeekendGapRisk()
	now := time.Now().UTC()

	if now.Weekday() >= time.Monday && now.Weekday() <= time.Thursday {
		if result.Verdict != constants.VerdictPass {
			t.Fatalf("expected PASS on weekday %s, got %s", now.Weekday(), result.Verdict)
		}
	}
	// On Friday after 20:00 or weekends, REJECT is expected — just verify it's deterministic.
	if now.Weekday() == time.Saturday || now.Weekday() == time.Sunday {
		if result.Verdict != constants.VerdictReject {
			t.Fatalf("expected REJECT on %s, got %s", now.Weekday(), result.Verdict)
		}
	}
}

// ── Low Liquidity Guard ─────────────────────────────────────────────────────

func TestCheckLowLiquidityHours(t *testing.T) {
	result := checkLowLiquidityHours()
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

	// The only guard that might reject is time-dependent (session, weekend, liquidity).
	// If we're running during normal London/NY hours on a weekday, all should pass.
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

	// Counter-trend without CHoCH must be in blocking rules.
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
