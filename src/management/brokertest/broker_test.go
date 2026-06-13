package management_broker

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/management/internal/broker"
)

// testCtx returns a context populated with the canonical test identity
// the way production traffic arrives at broker.Client / broker.Stream:
// the JWT middleware has already injected a *auth.Claims, so
// auth.UserIDFromContext(ctx) returns a non-empty string and the
// X-User-Id header gets stamped by stampInternalAuth. The actual
// identity values match the test JWT contract used elsewhere
// (sub=u-test, role=etradie, tier=free, status=active).
func testCtx() context.Context {
	return auth.InjectIdentity(
		context.Background(),
		"u-test", "test-user", auth.RoleEtradie, "free", "active",
	)
}

// ---------------------------------------------------------------------------
// Stream: GetTickPrice
// ---------------------------------------------------------------------------

func TestStream_GetTickPrice(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.TickPriceResponse = map[string]interface{}{
		"bid":  1.10245,
		"ask":  1.10257,
		"time": int64(1711200060),
	}
	stream := broker.NewStream(srv.URL(), 5000, "test-secret")

	tick, err := stream.GetTickPrice(testCtx(), "EURUSD")

	require.NoError(t, err)
	require.NotNil(t, tick)
	assert.InDelta(t, 1.10245, tick.Bid, 0.00001)
	assert.InDelta(t, 1.10257, tick.Ask, 0.00001)

	calls := srv.CallsForPath("/internal/broker/tick_price")
	require.Len(t, calls, 1)
	assert.Contains(t, calls[0].Query, "symbol=EURUSD")
}

func TestStream_GetTickPrice_BrokerDown(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.TickPriceResponse = map[string]interface{}{"detail": "Broker unavailable"}
	srv.TickPriceStatusCode = 502
	stream := broker.NewStream(srv.URL(), 5000, "test-secret")

	_, err := stream.GetTickPrice(testCtx(), "EURUSD")

	require.Error(t, err)
	assert.Contains(t, err.Error(), "502")
}

// ---------------------------------------------------------------------------
// Stream: GetPosition
// ---------------------------------------------------------------------------

func TestStream_GetPosition(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.PositionResponse = map[string]interface{}{
		"symbol":        "EURUSD",
		"type":          0, // BUY
		"price_open":    1.10000,
		"price_current": 1.10250,
		"sl":            1.09500,
		"tp":            1.11500,
		"volume":        0.10,
		"profit":        25.0,
		"ticket":        int64(12345678),
	}
	stream := broker.NewStream(srv.URL(), 5000, "test-secret")

	pos, err := stream.GetPosition(testCtx(), "12345678")

	require.NoError(t, err)
	require.NotNil(t, pos)
	assert.Equal(t, "EURUSD", pos.Symbol)
	assert.Equal(t, "BUY", pos.Direction)
	assert.InDelta(t, 1.10000, pos.EntryPrice, 0.00001)
	assert.InDelta(t, 1.10250, pos.CurrentPrice, 0.00001)
	assert.InDelta(t, 1.09500, pos.StopLoss, 0.00001)
	assert.InDelta(t, 1.11500, pos.TakeProfit, 0.00001)
	assert.InDelta(t, 0.10, pos.Volume, 0.001)
	assert.InDelta(t, 25.0, pos.Profit, 0.01)
	assert.Equal(t, "12345678", pos.Ticket)

	calls := srv.CallsForPath("/internal/broker/position")
	require.Len(t, calls, 1)
	assert.Contains(t, calls[0].Query, "ticket=12345678")
}

func TestStream_GetPosition_SELL(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.PositionResponse = map[string]interface{}{
		"symbol":        "GBPUSD",
		"type":          1, // SELL
		"price_open":    1.25000,
		"price_current": 1.24800,
		"sl":            1.25500,
		"tp":            1.24000,
		"volume":        0.20,
		"profit":        40.0,
		"ticket":        int64(87654321),
	}
	stream := broker.NewStream(srv.URL(), 5000, "test-secret")

	pos, err := stream.GetPosition(testCtx(), "87654321")

	require.NoError(t, err)
	assert.Equal(t, "SELL", pos.Direction) // type=1 -> SELL
	assert.Equal(t, "GBPUSD", pos.Symbol)
}

func TestStream_GetPosition_NotFound(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.PositionResponse = map[string]interface{}{"detail": "Position unavailable"}
	srv.PositionStatusCode = 502
	stream := broker.NewStream(srv.URL(), 5000, "test-secret")

	_, err := stream.GetPosition(testCtx(), "99999999")

	require.Error(t, err)
	assert.Contains(t, err.Error(), "502")
}

// ---------------------------------------------------------------------------
// Stream: GetSymbolInfo (EM-C2 Point self-heal source)
// ---------------------------------------------------------------------------

func TestStream_GetSymbolInfo(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.SymbolInfoResponse = map[string]interface{}{
		"symbol": "EURUSD",
		"point":  0.00001,
		"digits": 5,
	}
	stream := broker.NewStream(srv.URL(), 5000, "test-secret")

	info, err := stream.GetSymbolInfo(testCtx(), "EURUSD")

	require.NoError(t, err)
	require.NotNil(t, info)
	assert.Equal(t, "EURUSD", info.Symbol)
	assert.InDelta(t, 0.00001, info.Point, 0.000001)
	assert.Equal(t, 5, info.Digits)

	calls := srv.CallsForPath("/internal/broker/symbol_info")
	require.Len(t, calls, 1)
	assert.Contains(t, calls[0].Query, "symbol=EURUSD")
}

// ---------------------------------------------------------------------------
// Client: ModifyPosition
// ---------------------------------------------------------------------------

func TestClient_ModifyPosition_Success(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.ModifyPositionResponse = map[string]interface{}{
		"success": true,
		"error":   "",
	}
	client := broker.NewClient(srv.URL(), 5000, "test-secret")

	err := client.ModifyPosition(testCtx(), "12345678", 1.09800, 1.11000)

	require.NoError(t, err)

	calls := srv.CallsForPath("/internal/broker/modify_position")
	require.Len(t, calls, 1)
	body := calls[0].Body
	require.NotNil(t, body)
	assert.Equal(t, "12345678", body["ticket"])
	assert.InDelta(t, 1.09800, body["stop_loss"].(float64), 0.00001)
	assert.InDelta(t, 1.11000, body["take_profit"].(float64), 0.00001)
}

func TestClient_ModifyPosition_BrokerRejects(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.ModifyPositionResponse = map[string]interface{}{
		"success": false,
		"error":   "Invalid stop loss level",
	}
	client := broker.NewClient(srv.URL(), 5000, "test-secret")

	err := client.ModifyPosition(testCtx(), "12345678", 1.12000, 1.11000)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "Invalid stop loss level")
}

func TestClient_ModifyPosition_HttpError(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.ModifyPositionResponse = map[string]interface{}{"detail": "Broker unavailable"}
	srv.ModifyPositionStatusCode = 502
	client := broker.NewClient(srv.URL(), 5000, "test-secret")

	err := client.ModifyPosition(testCtx(), "12345678", 1.09800, 1.11000)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "502")
}

// ---------------------------------------------------------------------------
// Client: ClosePartial
// ---------------------------------------------------------------------------

func TestClient_ClosePartial_Success(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.ClosePartialResponse = map[string]interface{}{
		"success":     true,
		"close_price": 1.10500,
		"error":       "",
	}
	client := broker.NewClient(srv.URL(), 5000, "test-secret")

	err := client.ClosePartial(testCtx(), "12345678", 0.04)

	require.NoError(t, err)

	calls := srv.CallsForPath("/internal/broker/close_partial")
	require.Len(t, calls, 1)
	body := calls[0].Body
	require.NotNil(t, body)
	assert.Equal(t, "12345678", body["ticket"])
	assert.InDelta(t, 0.04, body["volume"].(float64), 0.001)
}

func TestClient_ClosePartial_BrokerRejects(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.ClosePartialResponse = map[string]interface{}{
		"success":     false,
		"close_price": 0.0,
		"error":       "Volume exceeds position size",
	}
	client := broker.NewClient(srv.URL(), 5000, "test-secret")

	err := client.ClosePartial(testCtx(), "12345678", 999.0)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "Volume exceeds position size")
}

func TestClient_ClosePartial_HttpError(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.ClosePartialResponse = map[string]interface{}{"detail": "Broker unavailable"}
	srv.ClosePartialStatusCode = 502
	client := broker.NewClient(srv.URL(), 5000, "test-secret")

	err := client.ClosePartial(testCtx(), "12345678", 0.04)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "502")
}

// ---------------------------------------------------------------------------
// Client: ClosePosition
// ---------------------------------------------------------------------------

func TestClient_ClosePosition_Success(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.ClosePositionResponse = map[string]interface{}{
		"success":     true,
		"close_price": 1.10500,
		"error":       "",
	}
	client := broker.NewClient(srv.URL(), 5000, "test-secret")

	err := client.ClosePosition(testCtx(), "12345678")

	require.NoError(t, err)

	calls := srv.CallsForPath("/internal/broker/close_position")
	require.Len(t, calls, 1)
	body := calls[0].Body
	require.NotNil(t, body)
	assert.Equal(t, "12345678", body["ticket"])
}

func TestClient_ClosePosition_BrokerRejects(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	srv.ClosePositionResponse = map[string]interface{}{
		"success":     false,
		"close_price": 0.0,
		"error":       "Position already closed",
	}
	client := broker.NewClient(srv.URL(), 5000, "test-secret")

	err := client.ClosePosition(testCtx(), "12345678")

	require.Error(t, err)
	assert.Contains(t, err.Error(), "Position already closed")
}

// ---------------------------------------------------------------------------
// MT5Broker Composite: verifies the composition satisfies Port interface
// ---------------------------------------------------------------------------

func TestMT5Broker_Composite(t *testing.T) {
	srv := NewMockBrokerServer()
	defer srv.Close()

	// MT5Broker composes Client + Stream into a single broker.Port.
	mb := broker.NewMT5Broker(srv.URL(), 5000, "test-secret")

	// Verify it satisfies the Port interface by calling methods from both.
	srv.TickPriceResponse = map[string]interface{}{
		"bid":  1.10245,
		"ask":  1.10257,
		"time": int64(1711200060),
	}
	srv.ModifyPositionResponse = map[string]interface{}{
		"success": true,
		"error":   "",
	}

	// Stream method.
	tick, err := mb.GetTickPrice(testCtx(), "EURUSD")
	require.NoError(t, err)
	assert.InDelta(t, 1.10245, tick.Bid, 0.00001)

	// Client method.
	err = mb.ModifyPosition(testCtx(), "12345678", 1.09800, 1.11000)
	require.NoError(t, err)

	assert.Equal(t, int64(1), srv.TickPriceCalls.Load())
	assert.Equal(t, int64(1), srv.ModifyPositionCalls.Load())
}
