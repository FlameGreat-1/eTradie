package state

import (
	"math"
	"testing"

	"github.com/flamegreat-1/etradie/src/execution/internal/models"
)

// =============================================================================
// AreCorrelated
// =============================================================================

func TestAreCorrelated_SameGroup_USDQuote(t *testing.T) {
	// EURUSD and GBPUSD are in the USD quote group (risk-on basket).
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
	// EURUSD (USD quote) and USDJPY (USD base) are in different groups.
	if AreCorrelated("EURUSD", "USDJPY") {
		t.Fatal("EURUSD and USDJPY should NOT be correlated (different groups)")
	}
}

func TestAreCorrelated_SameSymbol_NotCorrelated(t *testing.T) {
	// Same symbol is not "correlated" - it's the same pair check.
	// AreCorrelated checks if they share a group, and same symbol
	// does share a group, so this returns true.
	// This is correct behavior - the caller (HasCorrelatedExposure)
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

// =============================================================================
// CorrelatedGroupsFor
// =============================================================================

func TestCorrelatedGroupsFor_EURUSD(t *testing.T) {
	groups := CorrelatedGroupsFor("EURUSD")
	if len(groups) == 0 {
		t.Fatal("EURUSD should belong to at least one group")
	}
	// EURUSD is in group 0 (USD quote group).
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
// Manager - in-memory state tests (no DB required)
// =============================================================================

// newTestManager creates a Manager with pre-set state for testing.
// Bypasses NewManager to avoid DB dependency.
func newTestManager() *Manager {
	return &Manager{
		positions:       []models.Position{},
		pendingOrders:   []models.BrokerPendingOrder{},
		dailyPeriodKey:  "2026-03-24",
		weeklyPeriodKey: "2026-W13",
	}
}

// --- HasPositionOnPair ---

func TestHasPositionOnPair_OpenPosition(t *testing.T) {
	m := newTestManager()
	m.positions = []models.Position{
		{Symbol: "EURUSD", Direction: "BUY", LotSize: 0.10},
	}

	if !m.HasPositionOnPair("EURUSD") {
		t.Fatal("should detect open position on EURUSD")
	}
}

func TestHasPositionOnPair_PendingOrder(t *testing.T) {
	m := newTestManager()
	m.pendingOrders = []models.BrokerPendingOrder{
		{Symbol: "GBPUSD", Direction: "SELL", LotSize: 0.05},
	}

	if !m.HasPositionOnPair("GBPUSD") {
		t.Fatal("should detect pending order on GBPUSD")
	}
}

func TestHasPositionOnPair_NoExposure(t *testing.T) {
	m := newTestManager()
	m.positions = []models.Position{
		{Symbol: "EURUSD", Direction: "BUY"},
	}

	if m.HasPositionOnPair("GBPUSD") {
		t.Fatal("should not detect exposure on GBPUSD when only EURUSD is open")
	}
}

func TestHasPositionOnPair_CaseInsensitive(t *testing.T) {
	m := newTestManager()
	m.positions = []models.Position{
		{Symbol: "EURUSD"},
	}

	if !m.HasPositionOnPair("eurusd") {
		t.Fatal("pair check should be case insensitive")
	}
}

// --- HasCorrelatedExposure ---

func TestHasCorrelatedExposure_CorrelatedPosition(t *testing.T) {
	m := newTestManager()
	m.positions = []models.Position{
		{Symbol: "GBPUSD", Direction: "BUY"},
	}

	// EURUSD and GBPUSD are in the same correlation group.
	if !m.HasCorrelatedExposure("EURUSD") {
		t.Fatal("should detect correlated exposure (GBPUSD open, checking EURUSD)")
	}
}

func TestHasCorrelatedExposure_SamePair_NotCorrelation(t *testing.T) {
	m := newTestManager()
	m.positions = []models.Position{
		{Symbol: "EURUSD", Direction: "BUY"},
	}

	// Same pair is NOT correlation - it's same-pair check.
	// HasCorrelatedExposure skips same symbol.
	if m.HasCorrelatedExposure("EURUSD") {
		t.Fatal("same pair should not count as correlated exposure")
	}
}

func TestHasCorrelatedExposure_Uncorrelated(t *testing.T) {
	m := newTestManager()
	m.positions = []models.Position{
		{Symbol: "USDJPY", Direction: "BUY"},
	}

	// EURUSD and USDJPY are in different groups.
	if m.HasCorrelatedExposure("EURUSD") {
		t.Fatal("USDJPY should not be correlated with EURUSD")
	}
}

func TestHasCorrelatedExposure_CorrelatedPendingOrder(t *testing.T) {
	m := newTestManager()
	m.pendingOrders = []models.BrokerPendingOrder{
		{Symbol: "AUDUSD", Direction: "BUY"},
	}

	// EURUSD and AUDUSD are in the same USD quote group.
	if !m.HasCorrelatedExposure("EURUSD") {
		t.Fatal("should detect correlated pending order (AUDUSD pending, checking EURUSD)")
	}
}

// --- DailyLossPercent ---

func TestDailyLossPercent_WithLoss(t *testing.T) {
	m := newTestManager()
	m.account = &models.AccountInfo{Balance: 10000.0}
	m.dailyPnL = -300.0 // Lost $300 today.

	pct := m.DailyLossPercent()
	// 300 / 10000 * 100 = 3.0%
	if math.Abs(pct-3.0) > 0.01 {
		t.Fatalf("expected 3.0%%, got %.2f%%", pct)
	}
}

func TestDailyLossPercent_Profitable(t *testing.T) {
	m := newTestManager()
	m.account = &models.AccountInfo{Balance: 10000.0}
	m.dailyPnL = 150.0

	pct := m.DailyLossPercent()
	if pct != 0 {
		t.Fatalf("profitable day should return 0, got %.2f", pct)
	}
}

func TestDailyLossPercent_NoAccount(t *testing.T) {
	m := newTestManager()
	m.dailyPnL = -500.0

	pct := m.DailyLossPercent()
	if pct != 0 {
		t.Fatalf("no account should return 0, got %.2f", pct)
	}
}

func TestDailyLossPercent_ZeroBalance(t *testing.T) {
	m := newTestManager()
	m.account = &models.AccountInfo{Balance: 0}
	m.dailyPnL = -100.0

	pct := m.DailyLossPercent()
	if pct != 0 {
		t.Fatalf("zero balance should return 0, got %.2f", pct)
	}
}

// --- WeeklyDrawdownPercent ---

func TestWeeklyDrawdownPercent_WithLoss(t *testing.T) {
	m := newTestManager()
	m.account = &models.AccountInfo{Balance: 10000.0}
	m.weeklyPnL = -500.0

	pct := m.WeeklyDrawdownPercent()
	// 500 / 10000 * 100 = 5.0%
	if math.Abs(pct-5.0) > 0.01 {
		t.Fatalf("expected 5.0%%, got %.2f%%", pct)
	}
}

func TestWeeklyDrawdownPercent_Profitable(t *testing.T) {
	m := newTestManager()
	m.account = &models.AccountInfo{Balance: 10000.0}
	m.weeklyPnL = 200.0

	pct := m.WeeklyDrawdownPercent()
	if pct != 0 {
		t.Fatalf("profitable week should return 0, got %.2f", pct)
	}
}

// --- OpenPositionCount ---

func TestOpenPositionCount_Empty(t *testing.T) {
	m := newTestManager()
	if m.OpenPositionCount() != 0 {
		t.Fatalf("expected 0, got %d", m.OpenPositionCount())
	}
}

func TestOpenPositionCount_WithPositions(t *testing.T) {
	m := newTestManager()
	m.positions = []models.Position{
		{Symbol: "EURUSD"},
		{Symbol: "GBPUSD"},
		{Symbol: "XAUUSD"},
	}
	if m.OpenPositionCount() != 3 {
		t.Fatalf("expected 3, got %d", m.OpenPositionCount())
	}
}

// --- Positions / PendingOrders return copies ---

func TestPositions_ReturnsCopy(t *testing.T) {
	m := newTestManager()
	m.positions = []models.Position{
		{Symbol: "EURUSD", LotSize: 0.10},
	}

	copy1 := m.Positions()
	copy1[0].LotSize = 999.0

	// Original should be unchanged.
	original := m.Positions()
	if original[0].LotSize == 999.0 {
		t.Fatal("Positions() should return a defensive copy")
	}
}

func TestPendingOrders_ReturnsCopy(t *testing.T) {
	m := newTestManager()
	m.pendingOrders = []models.BrokerPendingOrder{
		{Symbol: "GBPUSD", LotSize: 0.05},
	}

	copy1 := m.PendingOrders()
	copy1[0].LotSize = 999.0

	original := m.PendingOrders()
	if original[0].LotSize == 999.0 {
		t.Fatal("PendingOrders() should return a defensive copy")
	}
}

// --- Account ---

func TestAccount_NilWhenNotSet(t *testing.T) {
	m := newTestManager()
	if m.Account() != nil {
		t.Fatal("Account should be nil when not set")
	}
}

func TestAccount_ReturnsCopy(t *testing.T) {
	m := newTestManager()
	m.account = &models.AccountInfo{Balance: 10000.0, Equity: 10500.0}

	acct := m.Account()
	acct.Balance = 0

	// Original should be unchanged.
	if m.Account().Balance != 10000.0 {
		t.Fatal("Account() should return a defensive copy")
	}
}
