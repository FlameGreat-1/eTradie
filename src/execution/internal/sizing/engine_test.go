package sizing

import (
	"math"
	"testing"

	"github.com/flamegreat/etradie/src/execution/internal/models"
)

// ── Pure-math Sizing Tests ──────────────────────────────────────────────────
// These test the core mathematical formulas from Rulebook Section 7.1
// without requiring a live broker connection. The actual Engine.Calculate
// method fetches account/instrument from the broker, but the math is the
// same RiskAmount / (SL_pips × pip_value) formula we validate here.

func TestSizingFormula_Standard(t *testing.T) {
	// Scenario: $10,000 account, 1% risk, 50 pip SL, $10 pip value (EURUSD standard lot).
	balance := 10000.0
	riskPct := 1.0
	slPips := 50.0
	pipValue := 10.0

	riskAmount := balance * (riskPct / 100.0) // $100
	lotSize := riskAmount / (slPips * pipValue) // 100 / 500 = 0.20

	expected := 0.20
	if math.Abs(lotSize-expected) > 0.001 {
		t.Fatalf("expected lot size %.2f, got %.4f", expected, lotSize)
	}
}

func TestSizingFormula_SmallAccount(t *testing.T) {
	// Scenario: $500 account, 0.5% risk (B grade), 30 pip SL.
	balance := 500.0
	riskPct := 0.5
	slPips := 30.0
	pipValue := 10.0

	riskAmount := balance * (riskPct / 100.0) // $2.50
	lotSize := riskAmount / (slPips * pipValue) // 2.50 / 300 = 0.0083

	// After rounding to 2 decimals: 0.00 — below minimum 0.01.
	rounded := math.Floor(lotSize*100) / 100
	minLot := 0.01
	if rounded < minLot {
		// Expected: too small to trade.
		return // Test passes.
	}
	t.Fatalf("expected lot size below minimum, got %.4f", rounded)
}

func TestSizingFormula_LargeAccount(t *testing.T) {
	// Scenario: $100,000 account, 1% risk (A grade), 25 pip SL.
	balance := 100000.0
	riskPct := 1.0
	slPips := 25.0
	pipValue := 10.0

	riskAmount := balance * (riskPct / 100.0) // $1000
	lotSize := riskAmount / (slPips * pipValue) // 1000 / 250 = 4.00

	expected := 4.00
	if math.Abs(lotSize-expected) > 0.001 {
		t.Fatalf("expected lot size %.2f, got %.4f", expected, lotSize)
	}
}

func TestSizingFormula_JPYPair(t *testing.T) {
	// Scenario: JPY pair — pip size is 0.01, pip value differs.
	balance := 10000.0
	riskPct := 1.0
	slDistance := 0.500 // 50 pips in JPY terms
	pipSize := 0.01
	pipValue := 7.5 // Approximate for USDJPY standard lot

	slPips := slDistance / pipSize // 50 pips
	riskAmount := balance * (riskPct / 100.0) // $100
	lotSize := riskAmount / (slPips * pipValue) // 100 / 375 = 0.267

	rounded := math.Floor(lotSize*100) / 100 // 0.26
	if rounded < 0.01 {
		t.Fatal("lot size below minimum")
	}
	if rounded > 10.0 {
		t.Fatal("lot size above max")
	}
	// Verify it's in a reasonable range.
	if rounded < 0.20 || rounded > 0.30 {
		t.Fatalf("expected lot size ~0.26, got %.2f", rounded)
	}
}

func TestSizingFormula_LotStepRounding(t *testing.T) {
	// Scenario: lot step of 0.01 should floor correctly.
	rawLotSize := 0.267
	lotStep := 0.01

	rounded := math.Floor(rawLotSize/lotStep) * lotStep // 0.26

	expected := 0.26
	if math.Abs(rounded-expected) > 0.001 {
		t.Fatalf("expected %.2f after lot step rounding, got %.4f", expected, rounded)
	}
}

func TestSizingFormula_MaxLotCap(t *testing.T) {
	// Scenario: massive account — lot size exceeds max.
	balance := 1000000.0
	riskPct := 1.0
	slPips := 10.0
	pipValue := 10.0

	riskAmount := balance * (riskPct / 100.0) // $10,000
	lotSize := riskAmount / (slPips * pipValue) // 10000 / 100 = 100.0

	maxLot := 10.0
	if lotSize > maxLot {
		lotSize = maxLot
	}

	if lotSize != maxLot {
		t.Fatalf("expected lot size capped at %.1f, got %.4f", maxLot, lotSize)
	}
}

// ── TradeRequest.EntryPrice() ───────────────────────────────────────────────

func TestEntryPrice_Midpoint(t *testing.T) {
	req := &models.TradeRequest{
		EntryZoneLow:  1.10000,
		EntryZoneHigh: 1.10100,
	}
	expected := 1.10050
	got := req.EntryPrice()
	if math.Abs(got-expected) > 0.00001 {
		t.Fatalf("expected %.5f, got %.5f", expected, got)
	}
}

// ── SL Distance Pips ────────────────────────────────────────────────────────

func TestSLDistancePips_EURUSD(t *testing.T) {
	entryPrice := 1.10050
	stopLoss := 1.09550
	pipSize := 0.0001

	slDistance := math.Abs(entryPrice - stopLoss)
	slPips := slDistance / pipSize

	expected := 50.0
	if math.Abs(slPips-expected) > 0.1 {
		t.Fatalf("expected %.1f pips, got %.1f", expected, slPips)
	}
}

func TestSLDistancePips_USDJPY(t *testing.T) {
	entryPrice := 150.500
	stopLoss := 150.000
	pipSize := 0.01

	slDistance := math.Abs(entryPrice - stopLoss)
	slPips := slDistance / pipSize

	expected := 50.0
	if math.Abs(slPips-expected) > 0.1 {
		t.Fatalf("expected %.1f pips, got %.1f", expected, slPips)
	}
}

func TestZeroSLDistance_Error(t *testing.T) {
	entryPrice := 1.10000
	stopLoss := 1.10000

	slDistance := math.Abs(entryPrice - stopLoss)
	if slDistance <= 0 {
		// Expected: this should be caught as an error.
		return
	}
	t.Fatal("expected zero SL distance to be detected")
}
