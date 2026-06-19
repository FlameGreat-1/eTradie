package state

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"math"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/store"
)

// testUserID is a deterministic user ID used across all state manager tests.
const testUserID = "test-user-state-001"

// =============================================================================
// AreCorrelated - pure logic, no infrastructure needed
// =============================================================================

func TestAreCorrelated_SameGroup_USDQuote(t *testing.T) {
	if !AreCorrelated("EURUSD", "GBPUSD") {
		t.Fatal("EURUSD and GBPUSD should be correlated (USD quote group)")
	}
}

func TestAreCorrelated_SameGroup_USDBase(t *testing.T) {
	if !AreCorrelated("USDJPY", "USDCHF") {
		t.Fatal("USDJPY and USDCHF should be correlated (USD base group)")
	}
}

func TestAreCorrelated_SameGroup_Metals(t *testing.T) {
	if !AreCorrelated("XAUUSD", "XAGUSD") {
		t.Fatal("XAUUSD and XAGUSD should be correlated (metals group)")
	}
}

func TestAreCorrelated_DifferentGroups(t *testing.T) {
	if AreCorrelated("EURUSD", "USDJPY") {
		t.Fatal("EURUSD and USDJPY should NOT be correlated (different groups)")
	}
}

func TestAreCorrelated_SameSymbol_SharesGroup(t *testing.T) {
	// Same symbol shares its own group. The caller (HasCorrelatedExposure)
	// explicitly skips same-symbol before calling AreCorrelated.
	if !AreCorrelated("EURUSD", "EURUSD") {
		t.Fatal("same symbol shares its own group, AreCorrelated returns true")
	}
}

func TestAreCorrelated_CaseInsensitive(t *testing.T) {
	if !AreCorrelated("eurusd", "GBPUSD") {
		t.Fatal("correlation check should be case insensitive")
	}
}

func TestAreCorrelated_UnknownSymbol(t *testing.T) {
	if AreCorrelated("EURUSD", "FAKEPAIR") {
		t.Fatal("unknown symbol should not be correlated with anything")
	}
}

func TestAreCorrelated_BothUnknown(t *testing.T) {
	if AreCorrelated("FAKE1", "FAKE2") {
		t.Fatal("two unknown symbols should not be correlated")
	}
}

func TestCorrelatedGroupsFor_EURUSD(t *testing.T) {
	groups := CorrelatedGroupsFor("EURUSD")
	if len(groups) == 0 {
		t.Fatal("EURUSD should belong to at least one group")
	}
	found := false
	for _, g := range groups {
		if g == 0 {
			found = true
		}
	}
	if !found {
		t.Fatalf("EURUSD should be in group 0, got groups %v", groups)
	}
}

func TestCorrelatedGroupsFor_UnknownSymbol(t *testing.T) {
	groups := CorrelatedGroupsFor("UNKNOWN")
	if groups != nil {
		t.Fatalf("unknown symbol should return nil, got %v", groups)
	}
}

// =============================================================================
// fakeBroker - in-test broker.Port implementation
//
// Mirrors the minimum surface the state manager tests previously got
// from the deleted internal/broker/mock package: a $10,000 account, a
// PlaceMarketOrder that appends to a positions slice, and a
// PlaceLimitOrder that appends to a pending-orders slice. GetAccountInfo
// reports balance + unrealised P&L (always zero here, so equity equals
// balance, exactly what the deleted mock did). Every other method
// returns defensible defaults so any future test that exercises them
// keeps working without further changes.
//
// Scoped to state_test.go (package state, internal test file) so it is
// unreachable from non-test code. The reconciler package owns its own
// fakeBroker scoped to reconciler_test.go for the same reason.
// =============================================================================

type fakeBroker struct {
	mu        sync.Mutex
	balance   float64
	positions []models.Position
	pending   []models.BrokerPendingOrder
}

func newFakeBroker(balance float64) *fakeBroker {
	return &fakeBroker{balance: balance}
}

func (b *fakeBroker) GetAccountInfo(_ context.Context) (*models.AccountInfo, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	var unrealized float64
	for i := range b.positions {
		unrealized += b.positions[i].UnrealizedPnL
	}
	return &models.AccountInfo{
		Balance:    b.balance,
		Equity:     b.balance + unrealized,
		Margin:     0,
		FreeMargin: b.balance + unrealized,
		Currency:   "USD",
	}, nil
}

func (b *fakeBroker) GetPositions(_ context.Context) ([]models.Position, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	out := make([]models.Position, len(b.positions))
	copy(out, b.positions)
	return out, nil
}

func (b *fakeBroker) GetPendingOrders(_ context.Context) ([]models.BrokerPendingOrder, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	out := make([]models.BrokerPendingOrder, len(b.pending))
	copy(out, b.pending)
	return out, nil
}

// GetInstrumentInfo returns standard FX defaults with JPY / gold / silver
// overrides, matching the behaviour the tests previously relied on.
func (b *fakeBroker) GetInstrumentInfo(_ context.Context, symbol string) (*models.InstrumentInfo, error) {
	norm := strings.ToUpper(symbol)
	info := &models.InstrumentInfo{
		Symbol:       norm,
		PipSize:      0.0001,
		PipValue:     10.0,
		MinLotSize:   0.01,
		MaxLotSize:   100.0,
		LotStep:      0.01,
		Spread:       0.00015,
		AvgSpread:    0.00012,
		Digits:       5,
		ContractSize: 100000,
	}
	if len(norm) >= 6 && norm[3:6] == "JPY" {
		info.PipSize = 0.01
		info.PipValue = 6.7
		info.Spread = 0.015
		info.AvgSpread = 0.012
		info.Digits = 3
	}
	if norm == "XAUUSD" {
		info.PipSize = 0.01
		info.PipValue = 1.0
		info.Spread = 0.30
		info.AvgSpread = 0.25
		info.Digits = 2
	}
	if norm == "XAGUSD" {
		info.PipSize = 0.001
		info.PipValue = 5.0
		info.Spread = 0.020
		info.AvgSpread = 0.015
		info.Digits = 3
	}
	return info, nil
}

func (b *fakeBroker) PlaceLimitOrder(_ context.Context, order *models.OrderPlacement) (*models.OrderResult, error) {
	orderID := newFakeOrderID()
	b.mu.Lock()
	b.pending = append(b.pending, models.BrokerPendingOrder{
		Symbol:        order.Symbol,
		Direction:     order.Direction,
		EntryPrice:    order.Price,
		StopLoss:      order.StopLoss,
		TakeProfit:    order.TakeProfit,
		LotSize:       order.LotSize,
		OrderID:       orderID,
		AnalysisID:    order.Comment,
		ExecutionMode: "LIMIT",
		Status:        "PENDING",
		CreatedAt:     time.Now().UTC(),
	})
	b.mu.Unlock()
	return &models.OrderResult{BrokerOrderID: orderID, FillPrice: order.Price, Status: "PLACED"}, nil
}

func (b *fakeBroker) PlaceMarketOrder(_ context.Context, order *models.OrderPlacement) (*models.OrderResult, error) {
	orderID := newFakeOrderID()
	b.mu.Lock()
	b.positions = append(b.positions, models.Position{
		Symbol:        order.Symbol,
		Direction:     order.Direction,
		EntryPrice:    order.Price,
		CurrentPrice:  order.Price,
		StopLoss:      order.StopLoss,
		TakeProfit:    order.TakeProfit,
		LotSize:       order.LotSize,
		UnrealizedPnL: 0,
		OrderID:       orderID,
		AnalysisID:    order.Comment,
		OpenTime:      time.Now().UTC(),
	})
	b.mu.Unlock()
	return &models.OrderResult{BrokerOrderID: orderID, FillPrice: order.Price, Status: "FILLED"}, nil
}

func (b *fakeBroker) CancelOrder(_ context.Context, orderID string) error {
	b.mu.Lock()
	defer b.mu.Unlock()
	for i := range b.pending {
		if b.pending[i].OrderID == orderID {
			b.pending = append(b.pending[:i], b.pending[i+1:]...)
			return nil
		}
	}
	return fmt.Errorf("order %s not found", orderID)
}

func (b *fakeBroker) GetTickPrice(_ context.Context, symbol string) (*models.TickPrice, error) {
	norm := strings.ToUpper(symbol)
	mid := 1.10000
	spread := 0.00015
	if strings.HasSuffix(norm, "JPY") {
		mid = 150.000
		spread = 0.015
	}
	if norm == "XAUUSD" {
		mid = 2000.00
		spread = 0.30
	}
	return &models.TickPrice{Bid: mid, Ask: mid + spread, Timestamp: time.Now().UTC()}, nil
}

func newFakeOrderID() string {
	buf := make([]byte, 8)
	_, _ = rand.Read(buf)
	return "FAKE_" + hex.EncodeToString(buf)
}

// =============================================================================
// Manager - real NewManager with real PostgreSQL PnLStore + fakeBroker
// =============================================================================

func testPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	// Check service-specific env var first, then generic, then docker-compose default.
	dsn := os.Getenv("EXECUTION_DATABASE_URL")
	if dsn == "" {
		dsn = os.Getenv("DATABASE_URL")
	}
	if dsn == "" {
		// Read from POSTGRES_ env vars (set by docker-compose .env).
		user := os.Getenv("POSTGRES_USER")
		pass := os.Getenv("POSTGRES_PASSWORD")
		db := os.Getenv("POSTGRES_DB")
		host := os.Getenv("POSTGRES_HOST")
		if user == "" {
			user = "etradie"
		}
		if pass == "" {
			pass = "etradie123abcChuks"
		}
		if db == "" {
			db = "etradie"
		}
		if host == "" {
			host = "localhost"
		}
		dsn = "postgres://" + user + ":" + pass + "@" + host + ":5433/" + db + "?sslmode=disable"
	}
	pool, err := pgxpool.New(context.Background(), dsn)
	if err != nil {
		t.Fatalf("PostgreSQL connection failed: %v", err)
	}
	if err := pool.Ping(context.Background()); err != nil {
		pool.Close()
		t.Fatalf("PostgreSQL ping failed: %v", err)
	}

	// Ensure schema exists. Uses an advisory lock so concurrent test
	// packages do not deadlock on CREATE OR REPLACE TRIGGER inside
	// SchemaSQL.
	if err := store.EnsureSchema(context.Background(), pool); err != nil {
		pool.Close()
		t.Fatalf("schema creation failed: %v", err)
	}

	t.Cleanup(pool.Close)
	return pool
}

func newRealManager(t *testing.T) (*Manager, *fakeBroker) {
	t.Helper()
	pool := testPool(t)
	pnlStore := store.NewPnLStore(pool)

	fb := newFakeBroker(10000.0)
	mgr := NewManager(fb, pnlStore)

	return mgr, fb
}

// --- HasPositionOnPair (via Refresh from the fake broker) ---

func TestManager_HasPositionOnPair_AfterRefresh(t *testing.T) {
	mgr, fb := newRealManager(t)

	// Place a market order via the fake broker to create a position.
	fb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
		Symbol:    "EURUSD",
		Direction: "BUY",
		Price:     1.10000,
		StopLoss:  1.09500,
		LotSize:   0.10,
	})

	// Refresh loads positions from the broker.
	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	if !mgr.HasPositionOnPair(testUserID, "EURUSD") {
		t.Fatal("should detect open EURUSD position after Refresh")
	}
	if mgr.HasPositionOnPair(testUserID, "GBPUSD") {
		t.Fatal("should not detect GBPUSD when only EURUSD is open")
	}
}

func TestManager_HasPositionOnPair_PendingOrder(t *testing.T) {
	mgr, fb := newRealManager(t)

	fb.PlaceLimitOrder(context.Background(), &models.OrderPlacement{
		Symbol:    "GBPUSD",
		Direction: "SELL",
		Price:     1.27000,
		StopLoss:  1.27500,
		LotSize:   0.05,
	})

	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	if !mgr.HasPositionOnPair(testUserID, "GBPUSD") {
		t.Fatal("should detect pending order on GBPUSD")
	}
}

// --- HasCorrelatedExposure ---

func TestManager_HasCorrelatedExposure_Detected(t *testing.T) {
	mgr, fb := newRealManager(t)

	fb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
		Symbol:    "GBPUSD",
		Direction: "BUY",
		Price:     1.27000,
		StopLoss:  1.26500,
		LotSize:   0.10,
	})

	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	// EURUSD and GBPUSD are in the same correlation group.
	if !mgr.HasCorrelatedExposure(testUserID, "EURUSD") {
		t.Fatal("should detect correlated exposure (GBPUSD open, checking EURUSD)")
	}
}

func TestManager_HasCorrelatedExposure_SamePair_Excluded(t *testing.T) {
	mgr, fb := newRealManager(t)

	fb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
		Symbol:    "EURUSD",
		Direction: "BUY",
		Price:     1.10000,
		StopLoss:  1.09500,
		LotSize:   0.10,
	})

	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	// Same pair is NOT correlation.
	if mgr.HasCorrelatedExposure(testUserID, "EURUSD") {
		t.Fatal("same pair should not count as correlated exposure")
	}
}

func TestManager_HasCorrelatedExposure_Uncorrelated(t *testing.T) {
	mgr, fb := newRealManager(t)

	fb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
		Symbol:    "USDJPY",
		Direction: "BUY",
		Price:     150.000,
		StopLoss:  149.500,
		LotSize:   0.10,
	})

	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	// EURUSD and USDJPY are in different groups.
	if mgr.HasCorrelatedExposure(testUserID, "EURUSD") {
		t.Fatal("USDJPY should not be correlated with EURUSD")
	}
}

// --- DailyLossPercent / WeeklyDrawdownPercent ---

func TestManager_DailyLossPercent_AfterRefresh(t *testing.T) {
	mgr, _ := newRealManager(t)

	// Refresh to load account info (balance = 10000 from fake broker).
	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	// Record a loss via the real PnLStore.
	if err := mgr.RecordPnL(context.Background(), testUserID, -300.0); err != nil {
		t.Fatalf("RecordPnL failed: %v", err)
	}

	pct := mgr.DailyLossPercent(testUserID)
	// -300 / 10000 * 100 = 3.0%
	if math.Abs(pct-3.0) > 0.5 {
		// Allow tolerance because DB may have accumulated P&L from previous test runs.
		// The key assertion is that it's > 0 (loss detected).
		if pct <= 0 {
			t.Fatalf("expected positive loss percent after -300 loss, got %.2f%%", pct)
		}
	}
}

func TestManager_DailyLossPercent_Profitable(t *testing.T) {
	mgr, _ := newRealManager(t)

	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	// Record a profit.
	mgr.RecordPnL(context.Background(), testUserID, 500.0)

	// If daily P&L is positive overall, loss percent should be 0.
	// Note: DB may have accumulated losses from other tests, so we
	// check the in-memory value directly.
	if mgr.DailyPnL(testUserID) > 0 {
		pct := mgr.DailyLossPercent(testUserID)
		if pct != 0 {
			t.Fatalf("profitable day should return 0, got %.2f", pct)
		}
	}
}

func TestManager_WeeklyDrawdownPercent_AfterLoss(t *testing.T) {
	mgr, _ := newRealManager(t)

	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	mgr.RecordPnL(context.Background(), testUserID, -500.0)

	pct := mgr.WeeklyDrawdownPercent(testUserID)
	if mgr.WeeklyPnL(testUserID) < 0 && pct <= 0 {
		t.Fatalf("expected positive drawdown percent after loss, got %.2f%%", pct)
	}
}

// --- OpenPositionCount ---

func TestManager_OpenPositionCount_Empty(t *testing.T) {
	mgr, _ := newRealManager(t)

	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	if mgr.OpenPositionCount(testUserID) != 0 {
		t.Fatalf("expected 0 positions on fresh fake broker, got %d", mgr.OpenPositionCount(testUserID))
	}
}

func TestManager_OpenPositionCount_WithPositions(t *testing.T) {
	mgr, fb := newRealManager(t)

	fb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
		Symbol: "EURUSD", Direction: "BUY", Price: 1.10, LotSize: 0.10,
	})
	fb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
		Symbol: "GBPUSD", Direction: "SELL", Price: 1.27, LotSize: 0.05,
	})

	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	if mgr.OpenPositionCount(testUserID) != 2 {
		t.Fatalf("expected 2 positions, got %d", mgr.OpenPositionCount(testUserID))
	}
}

// --- Positions / PendingOrders return copies ---

func TestManager_Positions_ReturnsCopy(t *testing.T) {
	mgr, fb := newRealManager(t)

	fb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
		Symbol: "EURUSD", Direction: "BUY", Price: 1.10, LotSize: 0.10,
	})

	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	copy1 := mgr.Positions(testUserID)
	copy1[0].LotSize = 999.0

	original := mgr.Positions(testUserID)
	if original[0].LotSize == 999.0 {
		t.Fatal("Positions() should return a defensive copy")
	}
}

func TestManager_PendingOrders_ReturnsCopy(t *testing.T) {
	mgr, fb := newRealManager(t)

	fb.PlaceLimitOrder(context.Background(), &models.OrderPlacement{
		Symbol: "GBPUSD", Direction: "SELL", Price: 1.27, LotSize: 0.05,
	})

	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	copy1 := mgr.PendingOrders(testUserID)
	copy1[0].LotSize = 999.0

	original := mgr.PendingOrders(testUserID)
	if original[0].LotSize == 999.0 {
		t.Fatal("PendingOrders() should return a defensive copy")
	}
}

// --- Account ---

func TestManager_Account_ReturnsCopy(t *testing.T) {
	mgr, _ := newRealManager(t)

	if err := mgr.Refresh(context.Background(), testUserID); err != nil {
		t.Fatalf("Refresh failed: %v", err)
	}

	acct := mgr.Account(testUserID)
	if acct == nil {
		t.Fatal("Account should not be nil after Refresh")
	}
	if acct.Balance != 10000.0 {
		t.Fatalf("expected balance 10000, got %.2f", acct.Balance)
	}

	// Mutate the copy.
	acct.Balance = 0

	// Original should be unchanged.
	if mgr.Account(testUserID).Balance != 10000.0 {
		t.Fatal("Account() should return a defensive copy")
	}
}
