package types

import (
	"testing"
	"time"

	"github.com/flamegreat-1/etradie/src/management/internal/constants"
)

// ── IsLong ──────────────────────────────────────────────────────────────────

func TestIsLong_BuyDirection(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionBuy}
	if !trade.IsLong() {
		t.Fatal("expected IsLong() true for BUY direction")
	}
}

func TestIsLong_SellDirection(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionSell}
	if trade.IsLong() {
		t.Fatal("expected IsLong() false for SELL direction")
	}
}

// ── SLDistanceFromEntry ─────────────────────────────────────────────────────

func TestSLDistanceFromEntry_Long(t *testing.T) {
	trade := &Trade{
		EntryPrice: 1.10000,
		InitialSL:  1.09500,
	}
	expected := 0.00500
	got := trade.SLDistanceFromEntry()
	if abs(got-expected) > 0.00001 {
		t.Fatalf("expected %.5f, got %.5f", expected, got)
	}
}

func TestSLDistanceFromEntry_Short(t *testing.T) {
	trade := &Trade{
		EntryPrice: 1.10000,
		InitialSL:  1.10500,
	}
	expected := 0.00500
	got := trade.SLDistanceFromEntry()
	if abs(got-expected) > 0.00001 {
		t.Fatalf("expected %.5f, got %.5f", expected, got)
	}
}

// ── RMultiple ───────────────────────────────────────────────────────────────

func TestRMultiple_Profit(t *testing.T) {
	trade := &Trade{RiskAmount: 100.0}
	rm := trade.RMultiple(300.0)
	if abs(rm-3.0) > 0.001 {
		t.Fatalf("expected R:3.0, got %.2f", rm)
	}
}

func TestRMultiple_Loss(t *testing.T) {
	trade := &Trade{RiskAmount: 100.0}
	rm := trade.RMultiple(-50.0)
	if abs(rm-(-0.5)) > 0.001 {
		t.Fatalf("expected R:-0.50, got %.2f", rm)
	}
}

func TestRMultiple_ZeroRisk(t *testing.T) {
	trade := &Trade{RiskAmount: 0}
	rm := trade.RMultiple(100.0)
	if rm != 0 {
		t.Fatalf("expected 0 when risk is 0, got %.2f", rm)
	}
}

// ── IsSLHit ─────────────────────────────────────────────────────────────────

func TestIsSLHit_Long_Hit(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionBuy, StopLoss: 1.09500}
	if !trade.IsSLHit(1.09400) {
		t.Fatal("expected SL hit for long position when price < SL")
	}
}

func TestIsSLHit_Long_NotHit(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionBuy, StopLoss: 1.09500}
	if trade.IsSLHit(1.10000) {
		t.Fatal("expected SL NOT hit for long position when price > SL")
	}
}

func TestIsSLHit_Short_Hit(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionSell, StopLoss: 1.10500}
	if !trade.IsSLHit(1.10600) {
		t.Fatal("expected SL hit for short position when price > SL")
	}
}

func TestIsSLHit_Short_NotHit(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionSell, StopLoss: 1.10500}
	if trade.IsSLHit(1.10000) {
		t.Fatal("expected SL NOT hit for short position when price < SL")
	}
}

// ── IsTP1Hit / IsTP2Hit / IsTP3Hit ──────────────────────────────────────────

func TestIsTP1Hit_Long(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionBuy, TP1Price: 1.11000}
	if !trade.IsTP1Hit(1.11100) {
		t.Fatal("expected TP1 hit for long when price >= TP1")
	}
	if trade.IsTP1Hit(1.10500) {
		t.Fatal("expected TP1 NOT hit for long when price < TP1")
	}
}

func TestIsTP1Hit_Short(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionSell, TP1Price: 1.09000}
	if !trade.IsTP1Hit(1.08900) {
		t.Fatal("expected TP1 hit for short when price <= TP1")
	}
	if trade.IsTP1Hit(1.09500) {
		t.Fatal("expected TP1 NOT hit for short when price > TP1")
	}
}

func TestIsTP2Hit_Long(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionBuy, TP2Price: 1.12000}
	if !trade.IsTP2Hit(1.12000) {
		t.Fatal("expected TP2 hit exactly at level")
	}
}

func TestIsTP3Hit_Short(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionSell, TP3Price: 1.07000}
	if !trade.IsTP3Hit(1.06900) {
		t.Fatal("expected TP3 hit for short when price <= TP3")
	}
}

// ── LotSizeForTP ────────────────────────────────────────────────────────────

func TestLotSizeForTP_50Pct(t *testing.T) {
	trade := &Trade{TotalLotSize: 1.0}
	got := trade.LotSizeForTP(50)
	if abs(got-0.50) > 0.001 {
		t.Fatalf("expected 0.50 lots for 50%%, got %.4f", got)
	}
}

func TestLotSizeForTP_33Pct(t *testing.T) {
	trade := &Trade{TotalLotSize: 0.30}
	got := trade.LotSizeForTP(33)
	expected := 0.30 * 33.0 / 100.0
	if abs(got-expected) > 0.001 {
		t.Fatalf("expected %.4f, got %.4f", expected, got)
	}
}

// ── PriceForCheck ───────────────────────────────────────────────────────────

func TestPriceForCheck_Long_UsesBid(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionBuy}
	got := trade.PriceForCheck(1.10050, 1.10080)
	if got != 1.10050 {
		t.Fatalf("expected bid 1.10050 for long, got %.5f", got)
	}
}

func TestPriceForCheck_Short_UsesAsk(t *testing.T) {
	trade := &Trade{Direction: constants.DirectionSell}
	got := trade.PriceForCheck(1.10050, 1.10080)
	if got != 1.10080 {
		t.Fatalf("expected ask 1.10080 for short, got %.5f", got)
	}
}

// ── DurationMinutes ─────────────────────────────────────────────────────────

func TestDurationMinutes_OpenTrade(t *testing.T) {
	trade := &Trade{
		OpenedAt: time.Now().UTC().Add(-30 * time.Minute),
	}
	got := trade.DurationMinutes()
	if got < 29 || got > 31 {
		t.Fatalf("expected ~30 minutes, got %d", got)
	}
}

func TestDurationMinutes_ClosedTrade(t *testing.T) {
	opened := time.Date(2025, 1, 1, 10, 0, 0, 0, time.UTC)
	closed := time.Date(2025, 1, 1, 12, 30, 0, 0, time.UTC)
	trade := &Trade{
		OpenedAt: opened,
		ClosedAt: closed,
	}
	got := trade.DurationMinutes()
	if got != 150 {
		t.Fatalf("expected 150 minutes, got %d", got)
	}
}

// ── Concurrency Safety ──────────────────────────────────────────────────────

func TestTrade_ConcurrentLocking(t *testing.T) {
	trade := &Trade{
		Direction:  constants.DirectionBuy,
		EntryPrice: 1.10000,
		StopLoss:   1.09500,
	}

	done := make(chan struct{})

	// Simulate concurrent read and write.
	go func() {
		trade.Lock()
		trade.StopLoss = 1.10050 // Move to breakeven
		trade.BreakevenSet = true
		trade.Unlock()
		done <- struct{}{}
	}()

	go func() {
		trade.RLock()
		_ = trade.IsSLHit(1.09400)
		trade.RUnlock()
		done <- struct{}{}
	}()

	<-done
	<-done
	// If we reach here without deadlock or race, the test passes.
}

func abs(f float64) float64 {
	if f < 0 {
		return -f
	}
	return f
}
