package monitoring

import (
	"context"
	"fmt"
	"math"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/flamegreat-1/etradie/src/alert"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/stoploss"
	"github.com/flamegreat-1/etradie/src/management/internal/takeprofit"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// testCtx returns a context populated with the canonical test identity.
// Manager.GetPriceForSymbol resolves the per-(user, symbol) tick cache
// off auth.UserIDFromContext(ctx); a context with no identity is
// (correctly) rejected with ErrNoIdentityInCtx.
func testCtx() context.Context {
	return auth.InjectIdentity(
		context.Background(),
		"u-test", "test-user", auth.RoleEtradie, "free", "active",
	)
}

// noopTransport satisfies AlertTransport without doing anything.
type noopTransport struct{}

func (n *noopTransport) Publish(_ context.Context, _ *alert.Event) {}

// =============================================================================
// fakeBroker - in-test broker.Port for the monitoring package
//
// Mirrors the surface previously exposed by the deleted
// internal/broker/mock package: a synthetic $10k account, an in-memory
// positions map keyed by ticket, configurable tick prices per symbol,
// and the SL/TP modification + close primitives. The takeprofit
// package's executor_test.go holds an independent copy of this fake
// because Go test-internal types are not shareable across packages.
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

func (b *fakeBroker) SetTickPrice(symbol string, bid, ask float64) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.prices[symbol] = &broker.TickPrice{Bid: bid, Ask: ask}
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
	// Default mid for unknown symbols, matching the previous mock.
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

// newTestManager creates a Manager with the local fakeBroker and real
// sub-engines. The tick poll is set to 60s so workers don't fire during
// short tests.
func newTestManager(t *testing.T) (*Manager, *fakeBroker) {
	t.Helper()
	pool := testPool(t)
	repo := journal.NewRepository(pool)

	fb := newFakeBroker()
	// Set default prices so workers don't error on tick poll.
	fb.SetTickPrice("EURUSD", 1.10000, 1.10020)
	fb.SetTickPrice("GBPUSD", 1.27000, 1.27020)

	be := stoploss.NewBreakevenEngine(fb, repo)
	trail := stoploss.NewTrailingEngine(fb, repo)
	tp := takeprofit.NewExecutor(fb, repo)

	// 60000ms = 60s poll interval so workers don't fire during tests.
	mgr := NewManager(fb, be, trail, tp, repo, &noopTransport{}, 60000)
	t.Cleanup(mgr.Shutdown)

	return mgr, fb
}

func newTestTrade(id, symbol string) *types.Trade {
	return &types.Trade{
		TradeID:          id,
		Symbol:           symbol,
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
		BrokerOrderID:    "TKT-" + id,
		Status:           constants.StatusActive,
	}
}

// =============================================================================
// RegisterTrade
// =============================================================================

func TestRegisterTrade_AppearsInRegistry(t *testing.T) {
	mgr, fb := newTestManager(t)
	trade := newTestTrade("TMG-reg-001", "EURUSD")
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TMG-reg-001", Volume: 0.10})

	mgr.RegisterTrade(trade)

	if mgr.TradeCount() != 1 {
		t.Fatalf("expected 1 trade, got %d", mgr.TradeCount())
	}

	got := mgr.GetTrade("TMG-reg-001")
	if got == nil {
		t.Fatal("registered trade should be retrievable")
	}
	if got.Symbol != "EURUSD" {
		t.Fatalf("expected EURUSD, got %s", got.Symbol)
	}
}

func TestRegisterTrade_MultipleTrades(t *testing.T) {
	mgr, fb := newTestManager(t)

	trade1 := newTestTrade("TMG-multi-001", "EURUSD")
	trade2 := newTestTrade("TMG-multi-002", "GBPUSD")
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TMG-multi-001", Volume: 0.10})
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TMG-multi-002", Volume: 0.10})

	mgr.RegisterTrade(trade1)
	mgr.RegisterTrade(trade2)

	if mgr.TradeCount() != 2 {
		t.Fatalf("expected 2 trades, got %d", mgr.TradeCount())
	}
}

// =============================================================================
// GetTrade
// =============================================================================

func TestGetTrade_UnknownID_ReturnsNil(t *testing.T) {
	mgr, _ := newTestManager(t)

	got := mgr.GetTrade("TMG-nonexistent")
	if got != nil {
		t.Fatal("unknown trade ID should return nil")
	}
}

// =============================================================================
// GetAllTrades
// =============================================================================

func TestGetAllTrades_Empty(t *testing.T) {
	mgr, _ := newTestManager(t)

	trades := mgr.GetAllTrades()
	if len(trades) != 0 {
		t.Fatalf("expected 0 trades, got %d", len(trades))
	}
}

func TestGetAllTrades_ReturnsAll(t *testing.T) {
	mgr, fb := newTestManager(t)

	trade1 := newTestTrade("TMG-all-001", "EURUSD")
	trade2 := newTestTrade("TMG-all-002", "GBPUSD")
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TMG-all-001", Volume: 0.10})
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TMG-all-002", Volume: 0.10})

	mgr.RegisterTrade(trade1)
	mgr.RegisterTrade(trade2)

	trades := mgr.GetAllTrades()
	if len(trades) != 2 {
		t.Fatalf("expected 2 trades, got %d", len(trades))
	}

	// Verify both are present (order not guaranteed from map).
	found := map[string]bool{}
	for _, tr := range trades {
		found[tr.TradeID] = true
	}
	if !found["TMG-all-001"] || !found["TMG-all-002"] {
		t.Fatalf("expected both trades, found: %v", found)
	}
}

// =============================================================================
// RemoveTrade
// =============================================================================

func TestRemoveTrade_RemovesFromRegistry(t *testing.T) {
	mgr, fb := newTestManager(t)
	trade := newTestTrade("TMG-rem-001", "EURUSD")
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TMG-rem-001", Volume: 0.10})

	mgr.RegisterTrade(trade)
	if mgr.TradeCount() != 1 {
		t.Fatalf("expected 1 trade before remove, got %d", mgr.TradeCount())
	}

	mgr.RemoveTrade("TMG-rem-001")

	if mgr.TradeCount() != 0 {
		t.Fatalf("expected 0 trades after remove, got %d", mgr.TradeCount())
	}
	if mgr.GetTrade("TMG-rem-001") != nil {
		t.Fatal("removed trade should not be retrievable")
	}
}

func TestRemoveTrade_UnknownID_NoPanic(t *testing.T) {
	mgr, _ := newTestManager(t)

	// Should not panic.
	mgr.RemoveTrade("TMG-nonexistent")

	if mgr.TradeCount() != 0 {
		t.Fatalf("count should still be 0, got %d", mgr.TradeCount())
	}
}

func TestRemoveTrade_OnlyRemovesTarget(t *testing.T) {
	mgr, fb := newTestManager(t)

	trade1 := newTestTrade("TMG-target-001", "EURUSD")
	trade2 := newTestTrade("TMG-target-002", "GBPUSD")
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TMG-target-001", Volume: 0.10})
	fb.AddPosition(&broker.PositionInfo{Ticket: "TKT-TMG-target-002", Volume: 0.10})

	mgr.RegisterTrade(trade1)
	mgr.RegisterTrade(trade2)

	mgr.RemoveTrade("TMG-target-001")

	if mgr.TradeCount() != 1 {
		t.Fatalf("expected 1 trade remaining, got %d", mgr.TradeCount())
	}
	if mgr.GetTrade("TMG-target-002") == nil {
		t.Fatal("non-removed trade should still be present")
	}
}

// =============================================================================
// GetPriceForSymbol
// =============================================================================

func TestGetPriceForSymbol_ReturnsMidpoint(t *testing.T) {
	mgr, fb := newTestManager(t)
	fb.SetTickPrice("XAUUSD", 2350.50, 2351.50)

	price, err := mgr.GetPriceForSymbol(testCtx(), "XAUUSD")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	expected := (2350.50 + 2351.50) / 2.0
	if math.Abs(price-expected) > 0.01 {
		t.Fatalf("expected midpoint %.2f, got %.2f", expected, price)
	}
}

func TestGetPriceForSymbol_DefaultPrice(t *testing.T) {
	mgr, _ := newTestManager(t)

	// Fake broker returns default 1.08000/1.08020 for unknown symbols.
	price, err := mgr.GetPriceForSymbol(testCtx(), "USDJPY")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	expected := (1.08000 + 1.08020) / 2.0
	if math.Abs(price-expected) > 0.001 {
		t.Fatalf("expected default midpoint %.5f, got %.5f", expected, price)
	}
}

// =============================================================================
// GenerateTradeID
// =============================================================================

func TestGenerateTradeID_Format(t *testing.T) {
	id := GenerateTradeID()

	if !strings.HasPrefix(id, "TMG-") {
		t.Fatalf("trade ID should start with TMG-, got %q", id)
	}
	// TMG- (4) + 16 hex chars (8 bytes) = 20 total.
	if len(id) != 20 {
		t.Fatalf("expected 20 chars, got %d: %q", len(id), id)
	}
}

func TestGenerateTradeID_Unique(t *testing.T) {
	a := GenerateTradeID()
	b := GenerateTradeID()
	if a == b {
		t.Fatal("two generated IDs should be different")
	}
}
