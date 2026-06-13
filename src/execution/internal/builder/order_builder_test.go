package builder

import (
	"math"
	"strings"
	"testing"

	"github.com/flamegreat-1/etradie/src/execution/internal/config"
	"github.com/flamegreat-1/etradie/src/execution/internal/constants"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
)

// testConfig returns a minimal valid config for order building.
func testConfig() *config.Config {
	return &config.Config{
		OvershootToleranceMultiplier: 1.5,
	}
}

// testRequest returns a standard EURUSD LONG intraday trade request.
func testRequest() *models.TradeRequest {
	return &models.TradeRequest{
		Symbol:          "EURUSD",
		Direction:       constants.DirectionLong,
		EntryZoneLow:    1.09950,
		EntryZoneHigh:   1.10050,
		StopLoss:        1.09500,
		TP1Price:        1.10500,
		TP1Pct:          40,
		TP2Price:        1.11000,
		TP2Pct:          30,
		TP3Price:        1.11500,
		TP3Pct:          30,
		RRRatio:         3.0,
		Grade:           "A",
		RiskPercentage:  1.0,
		TradingStyle:    constants.StyleIntraday,
		Session:         "LONDON_NY_OVERLAP",
		ConfluenceScore: 8.5,
		Confidence:      0.85,
		AnalysisID:      "ANA-TEST-001",
		TraceID:         "TRC-TEST-001",
		LTFConfirmed:    false,
		SetupType:       "SMC_OB_RETEST",
	}
}

// testSizing returns a standard sizing result.
func testSizing() *models.SizingResult {
	return &models.SizingResult{
		LotSize:        0.10,
		RiskAmount:     100.0,
		AccountBalance: 10000.0,
		SLDistancePips: 50.0,
		PipValue:       10.0,
		PipSize:        0.0001,
	}
}

func floatClose(a, b, tol float64) bool {
	return math.Abs(a-b) < tol
}

// =============================================================================
// LIMIT Mode
// =============================================================================

func TestBuildWithMode_Limit_FieldMapping(t *testing.T) {
	req := testRequest()
	sizing := testSizing()
	cfg := testConfig()

	order := BuildWithMode(req, sizing, cfg, constants.ModeLimit)

	// Identity.
	if order.Symbol != "EURUSD" {
		t.Fatalf("expected EURUSD, got %s", order.Symbol)
	}
	if order.Direction != constants.DirectionLong {
		t.Fatalf("expected LONG, got %s", order.Direction)
	}
	if order.ExecutionMode != constants.ModeLimit {
		t.Fatalf("expected LIMIT mode, got %s", order.ExecutionMode)
	}

	// Entry price = midpoint of zone.
	expectedEntry := (1.09950 + 1.10050) / 2.0
	if !floatClose(order.EntryPrice, expectedEntry, 0.00001) {
		t.Fatalf("expected entry %.5f, got %.5f", expectedEntry, order.EntryPrice)
	}

	// Execution levels.
	if !floatClose(order.StopLoss, 1.09500, 0.00001) {
		t.Fatalf("expected SL 1.09500, got %.5f", order.StopLoss)
	}
	if !floatClose(order.TP1Price, 1.10500, 0.00001) {
		t.Fatalf("expected TP1 1.10500, got %.5f", order.TP1Price)
	}
	if order.TP1Pct != 40 {
		t.Fatalf("expected TP1Pct 40, got %d", order.TP1Pct)
	}
	if !floatClose(order.TP2Price, 1.11000, 0.00001) {
		t.Fatalf("expected TP2 1.11000, got %.5f", order.TP2Price)
	}
	if order.TP2Pct != 30 {
		t.Fatalf("expected TP2Pct 30, got %d", order.TP2Pct)
	}
	if !floatClose(order.TP3Price, 1.11500, 0.00001) {
		t.Fatalf("expected TP3 1.11500, got %.5f", order.TP3Price)
	}
	if order.TP3Pct != 30 {
		t.Fatalf("expected TP3Pct 30, got %d", order.TP3Pct)
	}

	// Risk fields from sizing.
	if !floatClose(order.LotSize, 0.10, 0.001) {
		t.Fatalf("expected lot 0.10, got %.4f", order.LotSize)
	}
	if !floatClose(order.RiskAmount, 100.0, 0.1) {
		t.Fatalf("expected risk 100.0, got %.2f", order.RiskAmount)
	}
	if !floatClose(order.AccountBalance, 10000.0, 0.1) {
		t.Fatalf("expected balance 10000.0, got %.2f", order.AccountBalance)
	}
	if !floatClose(order.SLDistancePips, 50.0, 0.1) {
		t.Fatalf("expected SL distance 50.0, got %.2f", order.SLDistancePips)
	}
	if !floatClose(order.PipValue, 10.0, 0.1) {
		t.Fatalf("expected pip value 10.0, got %.2f", order.PipValue)
	}
	if !floatClose(order.RiskPercent, 1.0, 0.01) {
		t.Fatalf("expected risk pct 1.0, got %.2f", order.RiskPercent)
	}
	if !floatClose(order.RRRatio, 3.0, 0.01) {
		t.Fatalf("expected RR 3.0, got %.2f", order.RRRatio)
	}

	// Context fields.
	if order.AnalysisID != "ANA-TEST-001" {
		t.Fatalf("expected analysis ID ANA-TEST-001, got %s", order.AnalysisID)
	}
	if order.TradingStyle != constants.StyleIntraday {
		t.Fatalf("expected INTRADAY style, got %s", order.TradingStyle)
	}
	if order.Session != "LONDON_NY_OVERLAP" {
		t.Fatalf("expected session LONDON_NY_OVERLAP, got %s", order.Session)
	}
	if order.Grade != "A" {
		t.Fatalf("expected grade A, got %s", order.Grade)
	}
	if !floatClose(order.Confluence, 8.5, 0.01) {
		t.Fatalf("expected confluence 8.5, got %.2f", order.Confluence)
	}
	if !floatClose(order.Confidence, 0.85, 0.01) {
		t.Fatalf("expected confidence 0.85, got %.2f", order.Confidence)
	}
	if order.SetupType != "SMC_OB_RETEST" {
		t.Fatalf("expected setup type SMC_OB_RETEST, got %s", order.SetupType)
	}
}

func TestBuildWithMode_Limit_TTLCandles_ByStyle(t *testing.T) {
	cfg := testConfig()
	sizing := testSizing()

	tests := []struct {
		style    constants.TradingStyle
		expected int
	}{
		{constants.StyleScalping, 1},
		{constants.StyleIntraday, 4},
		{constants.StyleSwing, 18},
		{constants.StylePositional, 42},
	}

	for _, tc := range tests {
		req := testRequest()
		req.TradingStyle = tc.style
		order := BuildWithMode(req, sizing, cfg, constants.ModeLimit)

		if order.TTLCandles != tc.expected {
			t.Errorf("style=%s: expected TTL %d candles, got %d", tc.style, tc.expected, order.TTLCandles)
		}
	}
}

func TestBuildWithMode_Limit_HasNoInstantOnlyFields(t *testing.T) {
	order := BuildWithMode(testRequest(), testSizing(), testConfig(), constants.ModeLimit)

	// LIMIT mode DOES carry a WatcherID: the watcher Manager arms a
	// TTL watcher (LMT_<symbol>_<suffix>) that cancels the resting
	// broker order when the per-style TTL elapses or a news-lockout
	// event becomes imminent. See watcher/manager.go::Arm and
	// order_builder.go::BuildWithMode (case ModeLimit).
	if !strings.HasPrefix(order.WatcherID, "LMT_EURUSD_") {
		t.Fatalf("LIMIT WatcherID should start with LMT_EURUSD_, got %q", order.WatcherID)
	}

	// OvershootTolerance and LTFConfirmed are INSTANT-ONLY: they
	// only make sense for a tick-driven watcher that fires a market
	// order on zone re-entry. LIMIT mode must leave them at their
	// zero values.
	if order.OvershootTolerance != 0 {
		t.Fatalf("LIMIT mode should have 0 OvershootTolerance, got %f", order.OvershootTolerance)
	}
	if order.LTFConfirmed {
		t.Fatal("LIMIT mode should not set LTFConfirmed")
	}
}

// =============================================================================
// INSTANT Mode
// =============================================================================

func TestBuildWithMode_Instant_WatcherID(t *testing.T) {
	order := BuildWithMode(testRequest(), testSizing(), testConfig(), constants.ModeInstant)

	if order.WatcherID == "" {
		t.Fatal("INSTANT mode should generate WatcherID")
	}
	if !strings.HasPrefix(order.WatcherID, "GRT_EURUSD_") {
		t.Fatalf("WatcherID should start with GRT_EURUSD_, got %q", order.WatcherID)
	}
}

func TestBuildWithMode_Instant_OvershootTolerance(t *testing.T) {
	req := testRequest()
	cfg := testConfig()
	cfg.OvershootToleranceMultiplier = 1.5

	order := BuildWithMode(req, testSizing(), cfg, constants.ModeInstant)

	// Zone width = 1.10050 - 1.09950 = 0.00100
	// Overshoot = 0.00100 * 1.5 = 0.00150
	expected := 0.00100 * 1.5
	if !floatClose(order.OvershootTolerance, expected, 0.00001) {
		t.Fatalf("expected overshoot %.5f, got %.5f", expected, order.OvershootTolerance)
	}
}

func TestBuildWithMode_Instant_LTFConfirmed_True(t *testing.T) {
	req := testRequest()
	req.LTFConfirmed = true

	order := BuildWithMode(req, testSizing(), testConfig(), constants.ModeInstant)

	if !order.LTFConfirmed {
		t.Fatal("LTFConfirmed should be propagated from request")
	}
}

func TestBuildWithMode_Instant_LTFConfirmed_False(t *testing.T) {
	req := testRequest()
	req.LTFConfirmed = false

	order := BuildWithMode(req, testSizing(), testConfig(), constants.ModeInstant)

	if order.LTFConfirmed {
		t.Fatal("LTFConfirmed=false should be propagated")
	}
}

func TestBuildWithMode_Instant_NoTTLCandles(t *testing.T) {
	order := BuildWithMode(testRequest(), testSizing(), testConfig(), constants.ModeInstant)

	if order.TTLCandles != 0 {
		t.Fatalf("INSTANT mode should have 0 TTLCandles, got %d", order.TTLCandles)
	}
}

// =============================================================================
// Order ID Format
// =============================================================================

func TestBuildWithMode_OrderID_Format(t *testing.T) {
	order := BuildWithMode(testRequest(), testSizing(), testConfig(), constants.ModeLimit)

	if !strings.HasPrefix(order.OrderID, "ORD_EURUSD_") {
		t.Fatalf("OrderID should start with ORD_EURUSD_, got %q", order.OrderID)
	}

	// Format: ORD_{symbol}_{date}_{time}_{hex}
	parts := strings.Split(order.OrderID, "_")
	// ORD, EURUSD, 20260324, 070000, hex
	if len(parts) < 5 {
		t.Fatalf("OrderID should have at least 5 parts, got %d: %q", len(parts), order.OrderID)
	}
}

func TestBuildWithMode_OrderID_Unique(t *testing.T) {
	req := testRequest()
	sizing := testSizing()
	cfg := testConfig()

	a := BuildWithMode(req, sizing, cfg, constants.ModeLimit)
	b := BuildWithMode(req, sizing, cfg, constants.ModeLimit)

	if a.OrderID == b.OrderID {
		t.Fatal("two orders should have different IDs")
	}
}

// =============================================================================
// SHORT direction
// =============================================================================

func TestBuildWithMode_Short_Direction(t *testing.T) {
	req := testRequest()
	req.Direction = constants.DirectionShort

	order := BuildWithMode(req, testSizing(), testConfig(), constants.ModeLimit)

	if order.Direction != constants.DirectionShort {
		t.Fatalf("expected SHORT direction, got %s", order.Direction)
	}
}

// =============================================================================
// CreatedAt timestamp
// =============================================================================

func TestBuildWithMode_CreatedAt_Set(t *testing.T) {
	order := BuildWithMode(testRequest(), testSizing(), testConfig(), constants.ModeLimit)

	if order.CreatedAt.IsZero() {
		t.Fatal("CreatedAt should be set")
	}
}

// =============================================================================
// Unknown style falls back to intraday TTL
// =============================================================================

func TestBuildWithMode_Limit_UnknownStyle_FallsBackToIntraday(t *testing.T) {
	req := testRequest()
	req.TradingStyle = "UNKNOWN_STYLE"

	order := BuildWithMode(req, testSizing(), testConfig(), constants.ModeLimit)

	// Should fall back to intraday TTL = 4.
	expectedTTL := constants.LimitTTLCandlesByStyle[constants.StyleIntraday]
	if order.TTLCandles != expectedTTL {
		t.Fatalf("unknown style should fall back to intraday TTL=%d, got %d", expectedTTL, order.TTLCandles)
	}
}
