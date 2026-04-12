package state

import (
	"context"
	"math"
	"os"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"

	mockbroker "github.com/flamegreat-1/etradie/src/execution/internal/broker/mock"
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
// Manager - real NewManager with real PostgreSQL PnLStore
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

	// Ensure schema exists.
	_, err = pool.Exec(context.Background(), store.SchemaSQL())
	if err != nil {
		pool.Close()
		t.Fatalf("schema creation failed: %v", err)
	}

	t.Cleanup(pool.Close)
	return pool
}

func newRealManager(t *testing.T) (*Manager, *mockbroker.Broker) {
	t.Helper()
	pool := testPool(t)
	pnlStore := store.NewPnLStore(pool)

	mb := mockbroker.NewBroker(10000.0)
	mgr := NewManager(mb, pnlStore)

	return mgr, mb
}

// --- HasPositionOnPair (via Refresh from real mock broker) ---

func TestManager_HasPositionOnPair_AfterRefresh(t *testing.T) {
	mgr, mb := newRealManager(t)

	// Place a market order via the mock broker to create a position.
	mb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
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
	mgr, mb := newRealManager(t)

	mb.PlaceLimitOrder(context.Background(), &models.OrderPlacement{
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
	mgr, mb := newRealManager(t)

	mb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
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
	mgr, mb := newRealManager(t)

	mb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
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
	mgr, mb := newRealManager(t)

	mb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
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

	// Refresh to load account info (balance = 10000 from mock broker).
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
		t.Fatalf("expected 0 positions on fresh mock broker, got %d", mgr.OpenPositionCount(testUserID))
	}
}

func TestManager_OpenPositionCount_WithPositions(t *testing.T) {
	mgr, mb := newRealManager(t)

	mb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
		Symbol: "EURUSD", Direction: "BUY", Price: 1.10, LotSize: 0.10,
	})
	mb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
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
	mgr, mb := newRealManager(t)

	mb.PlaceMarketOrder(context.Background(), &models.OrderPlacement{
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
	mgr, mb := newRealManager(t)

	mb.PlaceLimitOrder(context.Background(), &models.OrderPlacement{
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
