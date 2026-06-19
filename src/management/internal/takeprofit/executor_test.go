package takeprofit

import (
	"context"
	"fmt"
	"math"
	"os"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// =============================================================================
// fakeBroker - in-test broker.Port for the takeprofit package
//
// Independent copy of the in-test fake from monitoring/manager_test.go.
// Go does not allow two test packages to share a type declared in an
// internal _test.go without exporting it into non-test production code,
// which would re-introduce a production-visible mock. The duplication
// is intentional and matches the pattern already used by
// src/execution/internal/state (state_test.go + reconciler_test.go
// each carry their own fakeBroker).
// =============================================================================

type fakeBroker struct {
	mu        sync.RWMutex
	positions map[string]*broker.PositionInfo
	prices    map[string]*broker.TickPrice
	symbols   map[string]*broker.SymbolInfo
}

func newFakeBroker() *fakeBroker {
	return &fakeBroker{
		positions: make(map[string]*broker.PositionInfo),
		prices:    make(map[string]*broker.TickPrice),
		symbols:   make(map[string]*broker.SymbolInfo),
	}
}

func (b *fakeBroker) AddPosition(pos *broker.PositionInfo) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.positions[pos.Ticket] = pos
}

func (b *fakeBroker) GetTickPrice(_ context.Context, symbol string) (*broker.TickPrice, error) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	if tp, ok := b.prices[symbol]; ok {
		return tp, nil
	}
	return &broker.TickPrice{Bid: 1.08000, Ask: 1.08020}, nil
}

func (b *fakeBroker) GetAccountInfo(_ context.Context) (*broker.AccountInfo, error) {
	return &broker.AccountInfo{
		Balance:    10000.0,
		Equity:     10000.0,
		Margin:     0.0,
		FreeMargin: 10000.0,
		Currency:   "USD",
	}, nil
}

func (b *fakeBroker) GetPosition(_ context.Context, ticket string) (*broker.PositionInfo, error) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	pos, ok := b.positions[ticket]
	if !ok {
		return nil, fmt.Errorf("position %s not found", ticket)
	}
	return pos, nil
}

func (b *fakeBroker) GetSymbolInfo(_ context.Context, symbol string) (*broker.SymbolInfo, error) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	if si, ok := b.symbols[symbol]; ok {
		return si, nil
	}
	return &broker.SymbolInfo{
		Symbol:         symbol,
		Point:          0.00001,
		Digits:         5,
		TradeTickValue: 1.0,
		TradeTickSize:  0.00001,
	}, nil
}

func (b *fakeBroker) GetPositions(_ context.Context) ([]broker.PositionInfo, error) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	list := make([]broker.PositionInfo, 0, len(b.positions))
	for _, p := range b.positions {
		list = append(list, *p)
	}
	return list, nil
}

func (b *fakeBroker) GetHistory(_ context.Context, _ int) ([]broker.HistoryDealInfo, error) {
	return []broker.HistoryDealInfo{}, nil
}

func (b *fakeBroker) WatchPositions(
	ctx context.Context,
	interval time.Duration,
) (<-chan []broker.PositionInfo, <-chan error) {
	positions := make(chan []broker.PositionInfo, 1)
	errors := make(chan error, 1)
	if interval <= 0 {
		interval = time.Second
	}
	go func() {
		defer close(positions)
		defer close(errors)
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		emit := func() {
			snap, _ := b.GetPositions(ctx)
			select {
			case positions <- snap:
			case <-ctx.Done():
			default:
				select {
				case <-positions:
				default:
				}
				select {
				case positions <- snap:
				case <-ctx.Done():
				}
			}
		}
		emit()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				emit()
			}
		}
	}()
	return positions, errors
}

func (b *fakeBroker) ModifyPosition(_ context.Context, ticket string, newSL, newTP float64) error {
	b.mu.Lock()
	defer b.mu.Unlock()
	pos, ok := b.positions[ticket]
	if !ok {
		return fmt.Errorf("position %s not found", ticket)
	}
	pos.StopLoss = newSL
	pos.TakeProfit = newTP
	return nil
}

func (b *fakeBroker) ClosePartial(_ context.Context, ticket string, volumeToClose float64) error {
	b.mu.Lock()
	defer b.mu.Unlock()
	pos, ok := b.positions[ticket]
	if !ok {
		return fmt.Errorf("position %s not found", ticket)
	}
	if volumeToClose > pos.Volume {
		return fmt.Errorf("cannot close %.2f lots on position with %.2f lots", volumeToClose, pos.Volume)
	}
	pos.Volume -= volumeToClose
	return nil
}

func (b *fakeBroker) ClosePosition(_ context.Context, ticket string) error {
	b.mu.Lock()
	defer b.mu.Unlock()
	if _, ok := b.positions[ticket]; !ok {
		return fmt.Errorf("position %s not found", ticket)
	}
	delete(b.positions, ticket)
	return nil
}

// testPool creates a pgxpool connected to the running PostgreSQL container.
// Falls back gracefully if DB is unavailable (journal errors are logged, not fatal).
func testPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		user := os.Getenv("POSTGRES_USER")
		pass := os.Getenv("POSTGRES_PASSWORD")
		db := os.Getenv("POSTGRES_DB")
		host := os.Getenv("POSTGRES_HOST")
		if user == "" {
			user = "etradie"
		}
		if pass == "" {
			pass = "etradie_dev"
		}
		if db == "" {
			db = "etradie"
		}
		if host == "" {
			host = "localhost"
		}
		dsn = "postgres://" + user + ":" + pass + "@" + host + ":5432/" + db + "?sslmode=disable"
	}
	pool, err := pgxpool.New(context.Background(), dsn)
	if err != nil {
		t.Fatalf("PostgreSQL connection failed: %v", err)
	}
	if err := pool.Ping(context.Background()); err != nil {
		pool.Close()
		t.Fatalf("PostgreSQL ping failed: %v", err)
	}
	t.Cleanup(pool.Close)
	return pool
}

// newTestExecutor creates an executor with the local fakeBroker and real journal.
func newTestExecutor(t *testing.T, fb *fakeBroker) *Executor {
	t.Helper()
	pool := testPool(t)
	repo := journal.NewRepository(pool)
	return NewExecutor(fb, repo)
}

// newLongTrade creates a standard EURUSD BUY trade for testing.
// Entry: 1.10000, SL: 1.09500 (50 pip risk), lot: 0.10
// TP1: 1.10500 (50 pips, 1R), TP2: 1.11000 (100 pips, 2R), TP3: 1.11500 (150 pips, 3R)
// TP split: 40/30/30 (intraday style)
func newLongTrade() *types.Trade {
	return &types.Trade{
		TradeID:          "TMG-test-tp-long",
		UserID:           "u-test",
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
func newShortTrade() *types.Trade {
	return &types.Trade{
		TradeID:          "TMG-test-tp-short",
		UserID:           "u-test",
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
	fb := newFakeBroker()
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, fb)

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
	fb := newFakeBroker()
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, fb)

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
	fb := newFakeBroker()
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, fb)

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
	fb := newFakeBroker()
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, fb)

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
	fb := newFakeBroker()
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, fb)

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
	fb := newFakeBroker()
	exec := newTestExecutor(t, fb)

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
	fb := newFakeBroker()
	// Don't add the position - ClosePartial will return "not found".
	exec := newTestExecutor(t, fb)

	trade := newLongTrade()
	_, err := exec.Evaluate(context.Background(), trade, 1.10550)
	if err == nil {
		t.Fatal("expected broker error to propagate")
	}
	// executor.go wraps every TP error with "%s close: %w" where the
	// label is TP1/TP2/TP3.
	expectedMsg := "TP1 close"
	if !contains(err.Error(), expectedMsg) {
		t.Fatalf("error should mention TP1 close, got: %v", err)
	}
}

// =============================================================================
// SELL direction
// =============================================================================

func TestEvaluate_TP1Hit_Short(t *testing.T) {
	fb := newFakeBroker()
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-002", Volume: 0.10})
	exec := newTestExecutor(t, fb)

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
	fb := newFakeBroker()
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-002", Volume: 0.10})
	exec := newTestExecutor(t, fb)

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
	fb := newFakeBroker()
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TP-001", Volume: 0.10})
	exec := newTestExecutor(t, fb)

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
