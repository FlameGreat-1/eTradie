package validator

import (
	"context"
	"testing"
	"time"

	"github.com/flamegreat-1/etradie/src/execution/internal/constants"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
)

// ── These tests target the individual check functions directly.
// ── Checks that depend on *state.Manager (6, 7, 8, 9, 10) require
// ── a running broker and DB — tested at integration level.
// ── Here we cover the pure-logic checks that accept only
// ── TradeRequest and time (12, 13) plus session/spread structure.

// ── Check 4: News Lockout (delegated to gateway) ────────────────────────────

func TestCheck4_AlwaysPass(t *testing.T) {
	result := check4NewsLockout(context.Background(), nil, nil, nil, nil, nil, time.Now())
	if !result.Passed {
		t.Fatal("check4 must always pass (delegated to gateway)")
	}
}

// ── Check 12: Min R:R ───────────────────────────────────────────────────────

func TestCheck12_IntradayGoodRR_Pass(t *testing.T) {
	req := &models.TradeRequest{TradingStyle: constants.StyleIntraday, RRRatio: 3.5}
	result := check12MinRR(context.Background(), req, nil, nil, nil, nil, time.Now())

	if !result.Passed {
		t.Fatalf("expected pass for R:R 3.5 (min 3.0), got: %s", result.Reason)
	}
}

func TestCheck12_IntradayBadRR_Reject(t *testing.T) {
	req := &models.TradeRequest{TradingStyle: constants.StyleIntraday, RRRatio: 2.0}
	result := check12MinRR(context.Background(), req, nil, nil, nil, nil, time.Now())

	if result.Passed {
		t.Fatal("expected rejection for R:R 2.0 < 3.0 intraday minimum")
	}
	if result.FailedCheck != constants.CheckMinRR {
		t.Fatalf("expected CheckMinRR, got %d", result.FailedCheck)
	}
	if result.Outcome != constants.OutcomeReject {
		t.Fatalf("expected REJECT, got %s", result.Outcome)
	}
}

func TestCheck12_ScalpingMinRR_Pass(t *testing.T) {
	req := &models.TradeRequest{TradingStyle: constants.StyleScalping, RRRatio: 2.5}
	result := check12MinRR(context.Background(), req, nil, nil, nil, nil, time.Now())

	if !result.Passed {
		t.Fatalf("expected pass for scalping R:R 2.5 (min 2.0), got: %s", result.Reason)
	}
}

func TestCheck12_ScalpingBadRR_Reject(t *testing.T) {
	req := &models.TradeRequest{TradingStyle: constants.StyleScalping, RRRatio: 1.5}
	result := check12MinRR(context.Background(), req, nil, nil, nil, nil, time.Now())

	if result.Passed {
		t.Fatal("expected rejection for scalping R:R 1.5 < 2.0")
	}
}

func TestCheck12_SwingMinRR_Pass(t *testing.T) {
	req := &models.TradeRequest{TradingStyle: constants.StyleSwing, RRRatio: 4.0}
	result := check12MinRR(context.Background(), req, nil, nil, nil, nil, time.Now())

	if !result.Passed {
		t.Fatalf("expected pass for swing R:R 4.0 (min 3.0), got: %s", result.Reason)
	}
}

func TestCheck12_PositionalMinRR_Reject(t *testing.T) {
	req := &models.TradeRequest{TradingStyle: constants.StylePositional, RRRatio: 4.0}
	result := check12MinRR(context.Background(), req, nil, nil, nil, nil, time.Now())

	if result.Passed {
		t.Fatal("expected rejection for positional R:R 4.0 < 5.0")
	}
}

func TestCheck12_PositionalGoodRR_Pass(t *testing.T) {
	req := &models.TradeRequest{TradingStyle: constants.StylePositional, RRRatio: 6.0}
	result := check12MinRR(context.Background(), req, nil, nil, nil, nil, time.Now())

	if !result.Passed {
		t.Fatalf("expected pass for positional R:R 6.0 (min 5.0), got: %s", result.Reason)
	}
}

func TestCheck12_UnknownStyle_FallsBackToIntraday(t *testing.T) {
	req := &models.TradeRequest{TradingStyle: "UNKNOWN", RRRatio: 2.5}
	result := check12MinRR(context.Background(), req, nil, nil, nil, nil, time.Now())

	// Fallback is INTRADAY min 3.0, so 2.5 should fail.
	if result.Passed {
		t.Fatal("expected rejection for unknown style R:R 2.5 < intraday fallback 3.0")
	}
}

// ── Check 13: Weekend/Day Filter ────────────────────────────────────────────

func makeDayTime(weekday time.Weekday, hour int) time.Time {
	now := time.Now().UTC()
	for now.Weekday() != weekday {
		now = now.Add(24 * time.Hour)
	}
	return time.Date(now.Year(), now.Month(), now.Day(), hour, 0, 0, 0, time.UTC)
}

func TestCheck13_Saturday_Reject(t *testing.T) {
	now := makeDayTime(time.Saturday, 12)
	req := &models.TradeRequest{TradingStyle: constants.StyleIntraday}
	result := check13WeekendDayFilter(context.Background(), req, nil, nil, nil, nil, now)

	if result.Passed {
		t.Fatal("expected rejection on Saturday")
	}
	if result.FailedCheck != constants.CheckWeekendDayFilter {
		t.Fatalf("expected CheckWeekendDayFilter, got %d", result.FailedCheck)
	}
}

func TestCheck13_Sunday_Reject(t *testing.T) {
	now := makeDayTime(time.Sunday, 15)
	req := &models.TradeRequest{TradingStyle: constants.StyleIntraday}
	result := check13WeekendDayFilter(context.Background(), req, nil, nil, nil, nil, now)

	if result.Passed {
		t.Fatal("expected rejection on Sunday")
	}
}

func TestCheck13_MondayBefore7_Reject(t *testing.T) {
	now := makeDayTime(time.Monday, 3)
	req := &models.TradeRequest{TradingStyle: constants.StyleIntraday}
	result := check13WeekendDayFilter(context.Background(), req, nil, nil, nil, nil, now)

	if result.Passed {
		t.Fatal("expected rejection on Monday before 07:00 UTC")
	}
}

func TestCheck13_MondayAfter7_Pass(t *testing.T) {
	now := makeDayTime(time.Monday, 10)
	req := &models.TradeRequest{TradingStyle: constants.StyleIntraday}
	result := check13WeekendDayFilter(context.Background(), req, nil, nil, nil, nil, now)

	if !result.Passed {
		t.Fatalf("expected pass on Monday 10:00 UTC, got: %s", result.Reason)
	}
}

func TestCheck13_FridayCutoff_Scalping_Reject(t *testing.T) {
	now := makeDayTime(time.Friday, 14) // After scalping cutoff of 12:00
	req := &models.TradeRequest{TradingStyle: constants.StyleScalping}
	result := check13WeekendDayFilter(context.Background(), req, nil, nil, nil, nil, now)

	if result.Passed {
		t.Fatal("expected rejection on Friday 14:00 for scalping (cutoff 12:00)")
	}
}

func TestCheck13_FridayCutoff_Scalping_Pass(t *testing.T) {
	now := makeDayTime(time.Friday, 10) // Before scalping cutoff of 12:00
	req := &models.TradeRequest{TradingStyle: constants.StyleScalping}
	result := check13WeekendDayFilter(context.Background(), req, nil, nil, nil, nil, now)

	if !result.Passed {
		t.Fatalf("expected pass on Friday 10:00 for scalping (cutoff 12:00), got: %s", result.Reason)
	}
}

func TestCheck13_FridayCutoff_Swing_Reject(t *testing.T) {
	now := makeDayTime(time.Friday, 15) // After swing cutoff of 14:00
	req := &models.TradeRequest{TradingStyle: constants.StyleSwing}
	result := check13WeekendDayFilter(context.Background(), req, nil, nil, nil, nil, now)

	if result.Passed {
		t.Fatal("expected rejection on Friday 15:00 for swing (cutoff 14:00)")
	}
}

func TestCheck13_Wednesday_Pass(t *testing.T) {
	now := makeDayTime(time.Wednesday, 10)
	req := &models.TradeRequest{TradingStyle: constants.StyleIntraday}
	result := check13WeekendDayFilter(context.Background(), req, nil, nil, nil, nil, now)

	if !result.Passed {
		t.Fatalf("expected pass on Wednesday 10:00 UTC, got: %s", result.Reason)
	}
}

// ── TradeRequest EntryPrice helper ──────────────────────────────────────────

func TestTradeRequest_EntryPrice(t *testing.T) {
	req := &models.TradeRequest{
		EntryZoneLow:  1.10000,
		EntryZoneHigh: 1.10100,
	}
	expected := 1.10050
	got := req.EntryPrice()
	diff := got - expected
	if diff < 0 {
		diff = -diff
	}
	if diff > 0.00001 {
		t.Fatalf("expected entry price %.5f, got %.5f", expected, got)
	}
}

func TestTradeRequest_EntryZoneWidth(t *testing.T) {
	req := &models.TradeRequest{
		EntryZoneLow:  1.10000,
		EntryZoneHigh: 1.10100,
	}
	expected := 0.00100
	got := req.EntryZoneWidth()
	diff := got - expected
	if diff < 0 {
		diff = -diff
	}
	if diff > 0.000001 {
		t.Fatalf("expected zone width %.5f, got %.5f", expected, got)
	}
}
