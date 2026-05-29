package state_test

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/state"
)

// fakeBroker is the smallest broker.Port that exercises the
// reconciler's two read paths. Every method not used by the
// reconciler returns ErrNotImplemented so a future test that
// accidentally calls one fails loudly.
type fakeBroker struct {
	mu       sync.Mutex
	posByUID map[string][]models.Position
	pendByUID map[string][]models.BrokerPendingOrder
}

var errNotImpl = errors.New("fake broker: not implemented")

func (f *fakeBroker) GetAccountInfo(ctx context.Context) (*models.AccountInfo, error) {
	return nil, errNotImpl
}
func (f *fakeBroker) GetPositions(ctx context.Context) ([]models.Position, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	uid := userIDFromCtx(ctx)
	return append([]models.Position(nil), f.posByUID[uid]...), nil
}
func (f *fakeBroker) GetPendingOrders(ctx context.Context) ([]models.BrokerPendingOrder, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	uid := userIDFromCtx(ctx)
	return append([]models.BrokerPendingOrder(nil), f.pendByUID[uid]...), nil
}
func (f *fakeBroker) GetInstrumentInfo(ctx context.Context, symbol string) (*models.InstrumentInfo, error) {
	return nil, errNotImpl
}
func (f *fakeBroker) PlaceLimitOrder(ctx context.Context, o *models.OrderPlacement) (*models.OrderResult, error) {
	return nil, errNotImpl
}
func (f *fakeBroker) PlaceMarketOrder(ctx context.Context, o *models.OrderPlacement) (*models.OrderResult, error) {
	return nil, errNotImpl
}
func (f *fakeBroker) CancelOrder(ctx context.Context, brokerOrderID string) error {
	return errNotImpl
}
func (f *fakeBroker) GetTickPrice(ctx context.Context, symbol string) (*models.TickPrice, error) {
	return nil, errNotImpl
}

type ctxKeyUID struct{}

func userIDFromCtx(ctx context.Context) string {
	if v, ok := ctx.Value(ctxKeyUID{}).(string); ok {
		return v
	}
	return ""
}

type fakeIdentity struct{}

func (fakeIdentity) IdentityContext(ctx context.Context, userID string) (context.Context, error) {
	return context.WithValue(ctx, ctxKeyUID{}, userID), nil
}

func seedManager(t *testing.T, m *state.Manager, userID string, positions []models.Position) {
	t.Helper()
	for i := range positions {
		p := positions[i]
		m.AdoptBrokerPosition(userID, &p)
	}
}

func TestReconcilerHappyPathNoDrift(t *testing.T) {
	posU1 := models.Position{
		OrderID: "42", Symbol: "EURUSD", Direction: "BUY",
		LotSize: 0.10, StopLoss: 1.0950, TakeProfit: 1.1100, EntryPrice: 1.1000,
	}
	fb := &fakeBroker{
		posByUID: map[string][]models.Position{"u1": {posU1}},
	}
	mgr := state.NewManager(fb, nil)
	seedManager(t, mgr, "u1", []models.Position{posU1})

	rec := state.NewReconciler(fb, mgr, fakeIdentity{}, 0)
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()
	rec.Loop(ctx)

	require.Len(t, mgr.Positions("u1"), 1)
}

func TestReconcilerBrokerOnlyPositionAdopted(t *testing.T) {
	posU1 := models.Position{
		OrderID: "99", Symbol: "GBPUSD", Direction: "SELL",
		LotSize: 0.25, StopLoss: 1.2750, TakeProfit: 1.2600, EntryPrice: 1.2700,
	}
	fb := &fakeBroker{
		posByUID: map[string][]models.Position{"u1": {posU1}},
	}
	mgr := state.NewManager(fb, nil)
	// Force user state to exist (so ActiveUserIDs returns u1) but
	// without any positions.
	mgr.AdoptBrokerPosition("u1", &models.Position{OrderID: "sentinel", Symbol: "X"})

	rec := state.NewReconciler(fb, mgr, fakeIdentity{}, 0)
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()
	rec.Loop(ctx)

	// The broker-only position must now appear in the engine state.
	found := false
	for _, p := range mgr.Positions("u1") {
		if p.OrderID == "99" {
			found = true
		}
	}
	require.True(t, found, "broker_only position should be adopted")
}

func TestReconcilerMismatchReplacesEngineView(t *testing.T) {
	engineView := models.Position{
		OrderID: "77", Symbol: "USDJPY", Direction: "BUY",
		LotSize: 0.10, StopLoss: 145.00, TakeProfit: 146.00, EntryPrice: 145.50,
	}
	brokerView := models.Position{
		OrderID: "77", Symbol: "USDJPY", Direction: "BUY",
		LotSize: 0.10, StopLoss: 144.50, TakeProfit: 147.00, EntryPrice: 145.50,
	}
	fb := &fakeBroker{
		posByUID: map[string][]models.Position{"u1": {brokerView}},
	}
	mgr := state.NewManager(fb, nil)
	seedManager(t, mgr, "u1", []models.Position{engineView})

	rec := state.NewReconciler(fb, mgr, fakeIdentity{}, 0)
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()
	rec.Loop(ctx)

	positions := mgr.Positions("u1")
	require.Len(t, positions, 1)
	require.InDelta(t, 144.50, positions[0].StopLoss, 1e-9, "engine SL must now match broker SL")
	require.InDelta(t, 147.00, positions[0].TakeProfit, 1e-9, "engine TP must now match broker TP")
}

func TestReconcilerEngineOnlyLoggedNotDeleted(t *testing.T) {
	engineOnly := models.Position{
		OrderID: "orphan", Symbol: "AUDUSD", Direction: "BUY",
		LotSize: 0.05, EntryPrice: 0.6800,
	}
	fb := &fakeBroker{
		posByUID: map[string][]models.Position{"u1": {}},
	}
	mgr := state.NewManager(fb, nil)
	seedManager(t, mgr, "u1", []models.Position{engineOnly})

	rec := state.NewReconciler(fb, mgr, fakeIdentity{}, 0)
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()
	rec.Loop(ctx)

	// The engine_only entry MUST still be present (never silently
	// deleted). Operator review path.
	found := false
	for _, p := range mgr.Positions("u1") {
		if p.OrderID == "orphan" {
			found = true
		}
	}
	require.True(t, found, "engine_only position must not be silently deleted")
}
