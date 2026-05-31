package execution_broker

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/execution/internal/broker/mt5"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
)

// testSecret is a non-empty internal secret so the bridge does not
// short-circuit construction; the mock server does not validate it.
const testSecret = "test-internal-shared-secret-0000000000"

// testCtx returns a context carrying a user identity, which the
// bridge's stampInternalAuth requires to resolve the per-user broker.
func testCtx() context.Context {
	return auth.InjectIdentity(
		context.Background(),
		"test-user", "tester", auth.RoleEtradie, "pro_byok", "active",
	)
}

// ---------------------------------------------------------------------------
// GetAccountInfo
// ---------------------------------------------------------------------------

func TestBridge_GetAccountInfo(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.AccountInfoResponse = AccountInfoFixture()
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	info, err := bridge.GetAccountInfo(testCtx())

	require.NoError(t, err)
	require.NotNil(t, info)
	assert.InDelta(t, 10000.0, info.Balance, 0.01)
	assert.InDelta(t, 10250.50, info.Equity, 0.01)
	assert.InDelta(t, 500.0, info.Margin, 0.01)
	assert.InDelta(t, 9750.50, info.FreeMargin, 0.01)
	assert.Equal(t, "USD", info.Currency)
	assert.Equal(t, int64(1), srv.AccountInfoCalls.Load())
}

func TestBridge_GetAccountInfo_BrokerUnavailable(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.AccountInfoResponse = map[string]interface{}{"detail": "Broker unavailable"}
	srv.AccountInfoStatusCode = 502
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	_, err := bridge.GetAccountInfo(testCtx())

	require.Error(t, err)
	assert.Contains(t, err.Error(), "502")
}

// ---------------------------------------------------------------------------
// GetPositions
// ---------------------------------------------------------------------------

func TestBridge_GetPositions(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.PositionsResponse = PositionsFixture()
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	positions, err := bridge.GetPositions(testCtx())

	require.NoError(t, err)
	require.Len(t, positions, 1)

	p := positions[0]
	assert.Equal(t, "EURUSD", p.Symbol)
	assert.Equal(t, "BUY", p.Direction) // type=0 -> BUY
	assert.InDelta(t, 1.10000, p.EntryPrice, 0.00001)
	assert.InDelta(t, 1.10250, p.CurrentPrice, 0.00001)
	assert.InDelta(t, 1.09500, p.StopLoss, 0.00001)
	assert.InDelta(t, 1.11500, p.TakeProfit, 0.00001)
	assert.InDelta(t, 0.10, p.LotSize, 0.001)
	assert.InDelta(t, 25.0, p.UnrealizedPnL, 0.01)
	assert.Equal(t, "12345678", p.OrderID)
	assert.Equal(t, "SMC-EURUSD-H4-001", p.AnalysisID) // comment -> AnalysisID
	assert.False(t, p.OpenTime.IsZero(), "OpenTime should be set")
	assert.Equal(t, int64(1), srv.PositionsCalls.Load())
}

func TestBridge_GetPositions_Empty(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.PositionsResponse = []map[string]interface{}{}
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	positions, err := bridge.GetPositions(testCtx())

	require.NoError(t, err)
	assert.Empty(t, positions)
}

// ---------------------------------------------------------------------------
// GetPendingOrders
// ---------------------------------------------------------------------------

func TestBridge_GetPendingOrders(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.PendingOrdersResponse = PendingOrdersFixture()
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	orders, err := bridge.GetPendingOrders(testCtx())

	require.NoError(t, err)
	require.Len(t, orders, 1)

	o := orders[0]
	assert.Equal(t, "GBPUSD", o.Symbol)
	assert.Equal(t, "BUY", o.Direction) // type=2 (BUY_LIMIT) -> BUY
	assert.InDelta(t, 1.25000, o.EntryPrice, 0.00001)
	assert.InDelta(t, 1.24500, o.StopLoss, 0.00001)
	assert.InDelta(t, 1.26500, o.TakeProfit, 0.00001)
	assert.InDelta(t, 0.15, o.LotSize, 0.001)
	assert.Equal(t, "87654321", o.OrderID)
	assert.Equal(t, "SMC-GBPUSD-H4-002", o.AnalysisID)
	assert.Equal(t, "LIMIT", o.ExecutionMode)
	assert.Equal(t, "PENDING", o.Status)
	assert.Equal(t, int64(1), srv.PendingOrdersCalls.Load())
}

// ---------------------------------------------------------------------------
// GetInstrumentInfo
// ---------------------------------------------------------------------------

func TestBridge_GetInstrumentInfo(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.SymbolInfoResponse = SymbolInfoFixture()
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	info, err := bridge.GetInstrumentInfo(testCtx(), "EURUSD")

	require.NoError(t, err)
	require.NotNil(t, info)

	// EURUSD: 5-digit pair. point=0.00001, pipPointRatio=10.
	// pipSize = 0.00001 * 10 = 0.0001
	assert.InDelta(t, 0.0001, info.PipSize, 0.000001)

	// pipValue = tickValue * (pipSize / tickSize) = 1.0 * (0.0001 / 0.00001) = 10.0
	assert.InDelta(t, 10.0, info.PipValue, 0.01)

	assert.InDelta(t, 0.01, info.MinLotSize, 0.001)
	assert.InDelta(t, 100.0, info.MaxLotSize, 0.01)
	assert.InDelta(t, 0.01, info.LotStep, 0.001)

	// Spread: 12 points * 0.00001 = 0.00012
	assert.InDelta(t, 0.00012, info.Spread, 0.000001)

	assert.Equal(t, int32(5), info.Digits)
	assert.InDelta(t, 100000.0, info.ContractSize, 0.01)

	// Verify the query parameter was sent correctly.
	calls := srv.CallsForPath("/internal/broker/symbol_info")
	require.Len(t, calls, 1)
	assert.Contains(t, calls[0].Query, "symbol=EURUSD")
}

func TestBridge_GetInstrumentInfo_JPYPair(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	// USDJPY: 3-digit pair. point=0.001, digits=3.
	srv.SymbolInfoResponse = map[string]interface{}{
		"symbol":              "USDJPY",
		"point":               0.001,
		"digits":              int32(3),
		"spread":              15,
		"trade_contract_size": 100000.0,
		"volume_min":          0.01,
		"volume_max":          100.0,
		"volume_step":         0.01,
		"trade_tick_value":    6.67, // Approximate for USDJPY on USD account.
		"trade_tick_size":     0.001,
	}
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	info, err := bridge.GetInstrumentInfo(testCtx(), "USDJPY")

	require.NoError(t, err)
	// USDJPY: 3-digit. pipPointRatio=10 (digits > 2).
	// pipSize = 0.001 * 10 = 0.01
	assert.InDelta(t, 0.01, info.PipSize, 0.0001)

	// pipValue = 6.67 * (0.01 / 0.001) = 66.7
	assert.InDelta(t, 66.7, info.PipValue, 0.1)
}

// ---------------------------------------------------------------------------
// GetTickPrice
// ---------------------------------------------------------------------------

func TestBridge_GetTickPrice(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.TickPriceResponse = TickPriceFixture()
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	tick, err := bridge.GetTickPrice(testCtx(), "EURUSD")

	require.NoError(t, err)
	require.NotNil(t, tick)
	assert.InDelta(t, 1.10245, tick.Bid, 0.00001)
	assert.InDelta(t, 1.10257, tick.Ask, 0.00001)
	assert.False(t, tick.Timestamp.IsZero())
	assert.Equal(t, time.Unix(1711200060, 0).UTC(), tick.Timestamp)

	calls := srv.CallsForPath("/internal/broker/tick_price")
	require.Len(t, calls, 1)
	assert.Contains(t, calls[0].Query, "symbol=EURUSD")
}

// ---------------------------------------------------------------------------
// PlaceLimitOrder / PlaceMarketOrder
// ---------------------------------------------------------------------------

func TestBridge_PlaceLimitOrder(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.PlaceOrderResponse = PlaceOrderSuccessFixture()
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	order := &models.OrderPlacement{
		Symbol:     "EURUSD",
		Direction:  "BUY",
		OrderType:  "LIMIT",
		Price:      1.10000,
		StopLoss:   1.09500,
		TakeProfit: 1.11500,
		LotSize:    0.10,
		Comment:    "SMC-EURUSD-H4-001",
	}

	result, err := bridge.PlaceLimitOrder(testCtx(), order)

	require.NoError(t, err)
	require.NotNil(t, result)
	assert.Equal(t, "99887766", result.BrokerOrderID)
	assert.InDelta(t, 1.10000, result.FillPrice, 0.00001)
	assert.InDelta(t, 0.0, result.Slippage, 0.00001) // price == fill_price
	assert.Equal(t, "PLACED", result.Status)
	assert.Empty(t, result.ErrorMessage)

	// Verify the request body sent to the Python endpoint.
	calls := srv.CallsForPath("/internal/broker/place_order")
	require.Len(t, calls, 1)
	body := calls[0].Body
	require.NotNil(t, body)
	assert.Equal(t, "EURUSD", body["symbol"])
	assert.Equal(t, "BUY", body["direction"])
	assert.Equal(t, "LIMIT", body["order_type"])
	assert.InDelta(t, 1.10000, body["price"].(float64), 0.00001)
	assert.InDelta(t, 1.09500, body["stop_loss"].(float64), 0.00001)
	assert.InDelta(t, 1.11500, body["take_profit"].(float64), 0.00001)
	assert.InDelta(t, 0.10, body["lot_size"].(float64), 0.001)
	assert.Equal(t, "SMC-EURUSD-H4-001", body["comment"])
}

func TestBridge_PlaceMarketOrder_Filled(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.PlaceOrderResponse = PlaceOrderFilledFixture()
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	order := &models.OrderPlacement{
		Symbol:     "EURUSD",
		Direction:  "BUY",
		OrderType:  "MARKET",
		Price:      1.10000, // Requested price.
		StopLoss:   1.09500,
		TakeProfit: 1.11500,
		LotSize:    0.10,
		Comment:    "SMC-EURUSD-H4-001",
	}

	result, err := bridge.PlaceMarketOrder(testCtx(), order)

	require.NoError(t, err)
	require.NotNil(t, result)
	assert.Equal(t, "99887767", result.BrokerOrderID)
	assert.InDelta(t, 1.10003, result.FillPrice, 0.00001)
	// Slippage = fill_price - requested_price = 1.10003 - 1.10000 = 0.00003
	assert.InDelta(t, 0.00003, result.Slippage, 0.000001)
	assert.Equal(t, "FILLED", result.Status)

	// Verify order_type was sent as MARKET.
	calls := srv.CallsForPath("/internal/broker/place_order")
	require.Len(t, calls, 1)
	assert.Equal(t, "MARKET", calls[0].Body["order_type"])
}

func TestBridge_PlaceOrder_Rejected(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.PlaceOrderResponse = PlaceOrderRejectedFixture()
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	order := &models.OrderPlacement{
		Symbol:    "EURUSD",
		Direction: "BUY",
		Price:     1.10000,
		StopLoss:  1.09500,
		LotSize:   100.0, // Huge lot -> insufficient margin.
	}

	result, err := bridge.PlaceLimitOrder(testCtx(), order)

	// The bridge does NOT return an error for rejected orders;
	// it returns the result with Status="REJECTED" and ErrorMessage set.
	require.NoError(t, err)
	require.NotNil(t, result)
	assert.Equal(t, "REJECTED", result.Status)
	assert.Contains(t, result.ErrorMessage, "Insufficient margin")
}

// ---------------------------------------------------------------------------
// CancelOrder
// ---------------------------------------------------------------------------

func TestBridge_CancelOrder_Success(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.CancelOrderResponse = CancelOrderSuccessFixture()
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	err := bridge.CancelOrder(testCtx(), "87654321")

	require.NoError(t, err)

	// Verify the request body.
	calls := srv.CallsForPath("/internal/broker/cancel_order")
	require.Len(t, calls, 1)
	assert.Equal(t, "87654321", calls[0].Body["order_id"])
}

func TestBridge_CancelOrder_NotFound(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.CancelOrderResponse = CancelOrderFailFixture()
	bridge := mt5.NewBridge(srv.URL(), 5000, testSecret)

	err := bridge.CancelOrder(testCtx(), "99999999")

	require.Error(t, err)
	assert.Contains(t, err.Error(), "Order not found")
}
