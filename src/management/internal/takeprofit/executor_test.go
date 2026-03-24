package takeprofit

import (
	"context"
	"math"
	"os"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/broker/mock"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// testPool creates a pgxpool connected to the running PostgreSQL container.
// Falls back gracefully if DB is unavailable (journal errors are logged, not fatal).
func testPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "postgres://etradie:etradie_dev@localhost:5432/etradie?sslmode=disable"
	}
	pool, err := pgxpool.New(context.Background(), dsn)
	if err != nil {
		t.Skipf("PostgreSQL unavailable, skipping: %v", err)
	}
	// Verify connection.
	if err := pool.Ping(context.Background()); err != nil {
		pool.Close()
		t.Skipf("PostgreSQL ping failed, skipping: %v", err)
	}
	t.Cleanup(pool.Close)
	return pool
}

// newTestExecutor creates an executor with the mock broker and real journal.
func newTestExecutor(t *testing.T, mb *mock.Broker) *Executor {
	t.Helper()
	pool := testPool(t)
	repo := journal.NewRepository(pool)
	return NewExecutor(mb, repo)
}

// newLongTrade creates a standard EURUSD BUY trade for testing.
// Entry: 1.10000, SL: 1.09500 (50 pip risk), lot: 0.10
// TP1: 1.10500 (50 pips, 1R), TP2: 1.11000 (100 pips, 2R), TP3: 1.11500 (150 pips, 3R)
// TP split: 40/30/30 (intraday style)
func newLongTrade() *types.Trade {
	return &types.Trade{
		TradeID:          "TMG-test-tp-long",
		Symbol:           "EURUSD",
		Direction:        constants.DirectionBuy,
		EntryPrice:       1.10000,
		StopLoss:         1.09500,
		InitialSL:        1.09500,
		TP1Price:         1.10500,
		TP2Price:         1.11000,
		TP3Price:         1.11500,
		TP1Pct:           40,
		TP2Pct:           30,
		TP3Pct:           30,
		TotalLotSize:     0.10,
		RemainingLotSize: 0.10,
		RiskAmount:       100.0,
		TradingStyle:     constants.StyleIntraday,
		BrokerOrderID:    "TKT-TP-001",
		Status:           constants.StatusActive,
	}
}

// newShortTrade creates a GBPUSD SELL trade for testing.
// Entry: 1.27000, SL: 1.27500 (50 pip risk), lot: 0.10
// TP1: 1.26500, TP2: 1.26000, TP3: 1.25500
func newShortTrade() *types.Trade {
	return &types.Trade{
		TradeID:          "TMG-test-tp-short",
		Symbol:           "GBPUSD",
		Direction:        constants.DirectionSell,
		EntryPrice:       1.27000,
		StopLoss:         1.27500,
		InitialSL:        1.27500,
		TP1Price:         1.26500,
		TP2Price:         1.26000,
		TP3Price:         1.25500,
		TP1Pct:           40,
		TP2Pct:           30,
		TP3Pct:           30,
		TotalLotSize:     0.10,
		RemainingLotSize: 0.10,
		RiskAmount:       100.0,
		TradingStyle:     constants.StyleIntraday,
		BrokerOrderID:    "TKT-TP-002",
		Status:           constants.StatusActive,
	}
}

func floatClose(a, b, tolerance float64) bool {
	return math.Abs(a-b) < tolerance
}

// =============================================================================
// No TP Hit
// =============================================================================

func TestEvaluate_NoTPHit_PriceBelowTP1(t *testing.T) {
	mb := mock.NewBroker()
	mb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, mb)

	trade := newLongTrade()
	// Price at 1.10400 - just below TP1 at 1.10500.
	evt, err := exec.Evaluate(context.Background(), trade, 1.10400)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if evt != "" {
		t.Fatalf("expected no event, got %q", evt)
	}

	trade.RLock()
	if trade.TP1Hit || trade.TP2Hit || trade.TP3Hit {
		t.Fatal("no TP flags should be set")
	}
	if trade.RemainingLotSize != 0.10 {
		t.Fatalf("remaining lot should be unchanged, got %f", trade.RemainingLotSize)
	}
	trade.RUnlock()
}

// =============================================================================
// TP1 Hit
// =============================================================================

func TestEvaluate_TP1Hit_Long(t *testing.T) {
	mb := mock.NewBroker()
	mb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, mb)

	trade := newLongTrade()
	// Price at 1.10550 - above TP1 at 1.10500.
	evt, err := exec.Evaluate(context.Background(), trade, 1.10550)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if evt != constants.EventTP1Hit {
		t.Fatalf("expected TP1_HIT event, got %q", evt)
	}

	trade.RLock()
	defer trade.RUnlock()

	if !trade.TP1Hit {
		t.Fatal("TP1Hit flag should be true")
	}
	if trade.TP2Hit || trade.TP3Hit {
		t.Fatal("TP2/TP3 should not be hit")
	}

	// TP1 closes 40% of 0.10 = 0.04 lots.
	expectedRemaining := 0.10 - 0.04
	if !floatClose(trade.RemainingLotSize, expectedRemaining, 0.001) {
		t.Fatalf("expected remaining %.4f, got %.4f", expectedRemaining, trade.RemainingLotSize)
	}

	if trade.Partials != 1 {
		t.Fatalf("expected 1 partial, got %d", trade.Partials)
	}
}

// =============================================================================
// TP2 requires TP1 already hit
// =============================================================================

func TestEvaluate_TP2Skipped_WhenTP1NotHit(t *testing.T) {
	mb := mock.NewBroker()
	mb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, mb)

	trade := newLongTrade()
	// Price above TP2 but TP1 not yet hit - should only trigger TP1.
	evt, err := exec.Evaluate(context.Background(), trade, 1.11050)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Should hit TP1 first (price is above TP1 too).
	if evt != constants.EventTP1Hit {
		t.Fatalf("expected TP1_HIT (TP2 requires TP1 first), got %q", evt)
	}

	trade.RLock()
	if trade.TP2Hit {
		t.Fatal("TP2 should not be hit when TP1 wasn't hit before")
	}
	trade.RUnlock()
}

func TestEvaluate_TP2Hit_AfterTP1(t *testing.T) {
	mb := mock.NewBroker()
	mb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, mb)

	trade := newLongTrade()

	// First: trigger TP1.
	_, err := exec.Evaluate(context.Background(), trade, 1.10550)
	if err != nil {
		t.Fatalf("TP1 error: %v", err)
	}

	// Now trigger TP2.
	evt, err := exec.Evaluate(context.Background(), trade, 1.11050)
	if err != nil {
		t.Fatalf("TP2 error: %v", err)
	}
	if evt != constants.EventTP2Hit {
		t.Fatalf("expected TP2_HIT, got %q", evt)
	}

	trade.RLock()
	defer trade.RUnlock()

	if !trade.TP2Hit {
		t.Fatal("TP2Hit flag should be true")
	}

	// TP1 closed 0.04, TP2 closes 30% of 0.10 = 0.03.
	expectedRemaining := 0.10 - 0.04 - 0.03
	if !floatClose(trade.RemainingLotSize, expectedRemaining, 0.001) {
		t.Fatalf("expected remaining %.4f, got %.4f", expectedRemaining, trade.RemainingLotSize)
	}

	if trade.Partials != 2 {
		t.Fatalf("expected 2 partials, got %d", trade.Partials)
	}
}

// =============================================================================
// TP3 Hit (full close of runner)
// =============================================================================

func TestEvaluate_TP3Hit_FullClose(t *testing.T) {
	mb := mock.NewBroker()
	mb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, mb)

	trade := newLongTrade()

	// Trigger TP1.
	_, _ = exec.Evaluate(context.Background(), trade, 1.10550)
	// Trigger TP2.
	_, _ = exec.Evaluate(context.Background(), trade, 1.11050)

	// Trigger TP3 - should fully close remaining.
	evt, err := exec.Evaluate(context.Background(), trade, 1.11550)
	if err != nil {
		t.Fatalf("TP3 error: %v", err)
	}
	if evt != constants.EventTP3Hit {
		t.Fatalf("expected TP3_HIT, got %q", evt)
	}

	trade.RLock()
	defer trade.RUnlock()

	if !trade.TP3Hit {
		t.Fatal("TP3Hit flag should be true")
	}

	// All lots should be closed.
	if trade.RemainingLotSize != 0 {
		t.Fatalf("expected 0 remaining after TP3, got %f", trade.RemainingLotSize)
	}

	if trade.Status != constants.StatusClosed {
		t.Fatalf("expected CLOSED status after TP3, got %s", trade.Status)
	}

	if trade.Partials != 3 {
		t.Fatalf("expected 3 partials, got %d", trade.Partials)
	}
}

// =============================================================================
// All TPs already hit - no action
// =============================================================================

func TestEvaluate_AllTPsAlreadyHit(t *testing.T) {
	mb := mock.NewBroker()
	exec := newTestExecutor(t, mb)

	trade := newLongTrade()
	trade.TP1Hit = true
	trade.TP2Hit = true
	trade.TP3Hit = true
	trade.RemainingLotSize = 0
	trade.Status = constants.StatusClosed

	evt, err := exec.Evaluate(context.Background(), trade, 1.12000)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if evt != "" {
		t.Fatalf("expected no event when all TPs hit, got %q", evt)
	}
}

// =============================================================================
// Broker error propagation
// =============================================================================

func TestEvaluate_BrokerError_Propagated(t *testing.T) {
	mb := mock.NewBroker()
	// Don't add the position - ClosePartial will return "not found".
	exec := newTestExecutor(t, mb)

	trade := newLongTrade()
	_, err := exec.Evaluate(context.Background(), trade, 1.10550)
	if err == nil {
		t.Fatal("expected broker error to propagate")
	}
	expectedMsg := "TP1 partial close"
	if !contains(err.Error(), expectedMsg) {
		t.Fatalf("error should mention TP1 partial close, got: %v", err)
	}
}

// =============================================================================
// SELL direction
// =============================================================================

func TestEvaluate_TP1Hit_Short(t *testing.T) {
	mb := mock.NewBroker()
	mb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-002", Volume: 0.10})
	exec := newTestExecutor(t, mb)

	trade := newShortTrade()
	// For SELL: TP1 at 1.26500, price drops to 1.26450 (below TP1).
	evt, err := exec.Evaluate(context.Background(), trade, 1.26450)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if evt != constants.EventTP1Hit {
		t.Fatalf("expected TP1_HIT for short, got %q", evt)
	}

	trade.RLock()
	defer trade.RUnlock()

	if !trade.TP1Hit {
		t.Fatal("TP1Hit should be true for short trade")
	}

	expectedRemaining := 0.10 - 0.04
	if !floatClose(trade.RemainingLotSize, expectedRemaining, 0.001) {
		t.Fatalf("expected remaining %.4f, got %.4f", expectedRemaining, trade.RemainingLotSize)
	}
}

func TestEvaluate_NoTPHit_Short_PriceAboveTP1(t *testing.T) {
	mb := mock.NewBroker()
	mb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-002", Volume: 0.10})
	exec := newTestExecutor(t, mb)

	trade := newShortTrade()
	// For SELL: TP1 at 1.26500, price at 1.26600 (above TP1, not hit).
	evt, err := exec.Evaluate(context.Background(), trade, 1.26600)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if evt != "" {
		t.Fatalf("expected no event for short above TP1, got %q", evt)
	}
}

// =============================================================================
// PnL estimation
// =============================================================================

func TestEvaluate_TP1Hit_PnLEstimate(t *testing.T) {
	mb := mock.NewBroker()
	mb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, mb)

	trade := newLongTrade()
	// TP1 at 1.10500, close at 1.10500 exactly = 1R.
	_, err := exec.Evaluate(context.Background(), trade, 1.10500)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	trade.RLock()
	defer trade.RUnlock()

	// SL distance = 1.10000 - 1.09500 = 0.00500
	// Price distance = 1.10500 - 1.10000 = 0.00500
	// R-multiple = 0.00500 / 0.00500 = 1.0
	// PnL estimate = 1.0 * 100.0 * (0.04 / 0.10) = 40.0
	if !floatClose(trade.RealizedPnL, 40.0, 0.1) {
		t.Fatalf("expected PnL ~40.0, got %.2f", trade.RealizedPnL)
	}
}

// contains checks if s contains substr.
func contains(s, substr string) bool {
	return len(s) >= len(substr) && searchString(s, substr)
}

func searchString(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
