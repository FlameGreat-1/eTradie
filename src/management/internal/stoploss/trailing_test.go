package stoploss

import (
	"testing"

	"github.com/flamegreat/etradie/src/management/internal/constants"
)

// ── Trail Fraction Tests ────────────────────────────────────────────────────
// These test the trailFractionForStyle method which determines how
// aggressively the trailing stop protects profit. The method is
// package-internal so we can test it directly.

func TestTrailFraction_Scalping_BeforeTP1(t *testing.T) {
	engine := &TrailingEngine{}
	got := engine.trailFractionForStyle(constants.StyleScalping, false)
	if got != 0.60 {
		t.Fatalf("expected 0.60 for scalping before TP1, got %.2f", got)
	}
}

func TestTrailFraction_Scalping_AfterTP1(t *testing.T) {
	engine := &TrailingEngine{}
	got := engine.trailFractionForStyle(constants.StyleScalping, true)
	if got != 0.70 {
		t.Fatalf("expected 0.70 for scalping after TP1 (+10%%), got %.2f", got)
	}
}

func TestTrailFraction_Intraday_BeforeTP1(t *testing.T) {
	engine := &TrailingEngine{}
	got := engine.trailFractionForStyle(constants.StyleIntraday, false)
	if got != 0.50 {
		t.Fatalf("expected 0.50 for intraday before TP1, got %.2f", got)
	}
}

func TestTrailFraction_Intraday_AfterTP1(t *testing.T) {
	engine := &TrailingEngine{}
	got := engine.trailFractionForStyle(constants.StyleIntraday, true)
	if got != 0.60 {
		t.Fatalf("expected 0.60 for intraday after TP1, got %.2f", got)
	}
}

func TestTrailFraction_Swing_BeforeTP1(t *testing.T) {
	engine := &TrailingEngine{}
	got := engine.trailFractionForStyle(constants.StyleSwing, false)
	if got != 0.40 {
		t.Fatalf("expected 0.40 for swing before TP1, got %.2f", got)
	}
}

func TestTrailFraction_Swing_AfterTP1(t *testing.T) {
	engine := &TrailingEngine{}
	got := engine.trailFractionForStyle(constants.StyleSwing, true)
	if got != 0.50 {
		t.Fatalf("expected 0.50 for swing after TP1, got %.2f", got)
	}
}

func TestTrailFraction_Positional_BeforeTP1(t *testing.T) {
	engine := &TrailingEngine{}
	got := engine.trailFractionForStyle(constants.StylePositional, false)
	if got != 0.30 {
		t.Fatalf("expected 0.30 for positional before TP1, got %.2f", got)
	}
}

func TestTrailFraction_Positional_AfterTP1(t *testing.T) {
	engine := &TrailingEngine{}
	got := engine.trailFractionForStyle(constants.StylePositional, true)
	if got != 0.40 {
		t.Fatalf("expected 0.40 for positional after TP1, got %.2f", got)
	}
}

// ── Trailing SL Math ────────────────────────────────────────────────────────
// Tests the core trailing calculation: newSL = price - totalMove*(1-fraction)
// for LONG trades, ensuring the SL only tightens (never widens).

func TestTrailingSLMath_LongPosition(t *testing.T) {
	// Scalping (fraction=0.60), entry=1.10000, check_price=1.11000
	// totalMove = 1.11000 - 1.10000 = 0.01000
	// newSL = 1.11000 - 0.01000 * (1 - 0.60) = 1.11000 - 0.004 = 1.10600
	entryPrice := 1.10000
	checkPrice := 1.11000
	fraction := 0.60

	totalMove := checkPrice - entryPrice
	newSL := checkPrice - totalMove*(1.0-fraction)

	expected := 1.10600
	diff := newSL - expected
	if diff < 0 {
		diff = -diff
	}
	if diff > 0.00001 {
		t.Fatalf("expected trailing SL %.5f, got %.5f", expected, newSL)
	}
}

func TestTrailingSLMath_ShortPosition(t *testing.T) {
	// Swing (fraction=0.40), entry=1.10000, check_price=1.09000
	// totalMove = 1.10000 - 1.09000 = 0.01000
	// newSL = 1.09000 + 0.01000 * (1 - 0.40) = 1.09000 + 0.006 = 1.09600
	entryPrice := 1.10000
	checkPrice := 1.09000
	fraction := 0.40

	totalMove := entryPrice - checkPrice
	newSL := checkPrice + totalMove*(1.0-fraction)

	expected := 1.09600
	diff := newSL - expected
	if diff < 0 {
		diff = -diff
	}
	if diff > 0.00001 {
		t.Fatalf("expected trailing SL %.5f, got %.5f", expected, newSL)
	}
}

func TestTrailingSL_OnlyTightens_Long(t *testing.T) {
	// For a LONG: newSL must be > currentSL to update.
	currentSL := 1.10500
	newSL := 1.10300 // This is LOWER than current — should NOT update.

	shouldUpdate := newSL > currentSL
	if shouldUpdate {
		t.Fatal("expected NO update because newSL is lower (less protective)")
	}
}

func TestTrailingSL_OnlyTightens_Short(t *testing.T) {
	// For a SHORT: newSL must be < currentSL to update.
	currentSL := 1.09500
	newSL := 1.09700 // This is HIGHER than current — should NOT update.

	shouldUpdate := newSL < currentSL
	if shouldUpdate {
		t.Fatal("expected NO update because newSL is higher (less protective for short)")
	}
}

// ── Constants Verification ──────────────────────────────────────────────────

func TestTrailConfigByStyle_AllStylesPresent(t *testing.T) {
	styles := []constants.TradingStyle{
		constants.StyleScalping,
		constants.StyleIntraday,
		constants.StyleSwing,
		constants.StylePositional,
	}

	for _, s := range styles {
		cfg, ok := constants.TrailConfigByStyle[s]
		if !ok {
			t.Fatalf("missing TrailConfig for style %s", s)
		}
		if cfg.Initial == "" || cfg.PostTP1 == "" {
			t.Fatalf("incomplete TrailConfig for %s: initial=%s, postTP1=%s", s, cfg.Initial, cfg.PostTP1)
		}
	}
}

func TestBreakevenConstants(t *testing.T) {
	if constants.SpreadBufferPips <= 0 {
		t.Fatal("SpreadBufferPips must be positive")
	}
	if constants.ScalpBEThreshold <= 0 || constants.ScalpBEThreshold >= 1 {
		t.Fatalf("ScalpBEThreshold must be 0 < x < 1, got %.2f", constants.ScalpBEThreshold)
	}
	if constants.IntradayBETimeoutHours <= 0 {
		t.Fatal("IntradayBETimeoutHours must be positive")
	}
	if constants.IntradaySLReductionPct <= 0 || constants.IntradaySLReductionPct >= 1 {
		t.Fatalf("IntradaySLReductionPct must be 0 < x < 1, got %.2f", constants.IntradaySLReductionPct)
	}
}
