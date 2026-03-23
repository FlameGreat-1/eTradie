package gateway_grpc

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	gatewayv1 "github.com/flamegreat-1/etradie/proto/gateway/v1"
)

// ---------------------------------------------------------------------------
// NotifyExecutionCompleted (Module B → Gateway → Module C handoff)
// ---------------------------------------------------------------------------

// TestGRPC_NotifyExecutionCompleted_NoMgmtClient verifies that when
// the management client is nil (Module C not configured), the server
// returns success=true as graceful degradation. The trade is filled
// at the broker but Module C handoff is skipped.
func TestGRPC_NotifyExecutionCompleted_NoMgmtClient(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	resp, err := h.Client.NotifyExecutionCompleted(ctx, &gatewayv1.NotifyExecutionCompletedRequest{
		Symbol:        "EURUSD",
		BrokerOrderId: "TKT-12345",
		FillPrice:     1.10000,
		Slippage:      0.00002,
		LotSize:       0.10,
		AnalysisId:    "SMC-EURUSD-H4-001",
		TraceId:       "trace-grpc-handoff-001",
		Direction:     "BUY",
		StopLoss:      1.09500,
		Tp1Price:      1.10500,
		Tp1Pct:        40,
		Tp2Price:      1.11000,
		Tp2Pct:        30,
		Tp3Price:      1.11500,
		Tp3Pct:        30,
		RiskAmount:    100.0,
		RiskPercent:   1.0,
		RrRatio:       3.0,
		Grade:         "A",
		TradingStyle:  "INTRADAY",
		Session:       "LONDON_NY_OVERLAP",
		ConfluenceScore: 8.5,
		ExecutionMode: "LIMIT",
		SetupType:     "TURTLE_SOUP",
	})

	// With nil mgmtClient, server returns success=true (graceful skip).
	require.NoError(t, err, "should not return gRPC error")
	require.NotNil(t, resp)
	assert.True(t, resp.Success,
		"should return success even without management client")
	// ManagementTradeId will be empty since handoff was skipped.
	assert.Empty(t, resp.ManagementTradeId)
}

// TestGRPC_NotifyExecutionCompleted_AllFieldsPropagated verifies that
// every field in the NotifyExecutionCompletedRequest is accepted by
// the server without error. This tests the full proto field mapping
// from Module B's order context through to the Gateway handler.
func TestGRPC_NotifyExecutionCompleted_AllFieldsPropagated(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	req := &gatewayv1.NotifyExecutionCompletedRequest{
		Symbol:          "GBPUSD",
		BrokerOrderId:   "TKT-99999",
		FillPrice:       1.25000,
		Slippage:        0.00005,
		LotSize:         0.20,
		AnalysisId:      "SND-GBPUSD-H4-002",
		TraceId:         "trace-grpc-handoff-fields-001",
		Direction:       "SELL",
		StopLoss:        1.25500,
		Tp1Price:        1.24500,
		Tp1Pct:          40,
		Tp2Price:        1.24000,
		Tp2Pct:          30,
		Tp3Price:        1.23500,
		Tp3Pct:          30,
		RiskAmount:      200.0,
		RiskPercent:     2.0,
		RrRatio:         2.0,
		Grade:           "B",
		TradingStyle:    "SWING",
		Session:         "LONDON_OPEN",
		ConfluenceScore: 7.0,
		ExecutionMode:   "INSTANT",
		SetupType:       "QML_BASELINE",
	}

	resp, err := h.Client.NotifyExecutionCompleted(ctx, req)
	require.NoError(t, err)
	require.NotNil(t, resp)
	assert.True(t, resp.Success)
}

// ---------------------------------------------------------------------------
// SetCycleInterval
// ---------------------------------------------------------------------------

// TestGRPC_SetCycleInterval_Valid sets the cycle interval to 120s
// and verifies the response.
func TestGRPC_SetCycleInterval_Valid(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	resp, err := h.Client.SetCycleInterval(ctx, &gatewayv1.SetCycleIntervalRequest{
		IntervalSeconds: 120,
	})

	require.NoError(t, err)
	require.NotNil(t, resp)
	assert.True(t, resp.Success)
	assert.Equal(t, int32(120), resp.CurrentIntervalSeconds)
	assert.Contains(t, resp.Message, "120")
}

// TestGRPC_SetCycleInterval_TooLow verifies that intervals below 60s
// are rejected with InvalidArgument.
func TestGRPC_SetCycleInterval_TooLow(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	_, err := h.Client.SetCycleInterval(ctx, &gatewayv1.SetCycleIntervalRequest{
		IntervalSeconds: 30,
	})

	require.Error(t, err)
	st, ok := status.FromError(err)
	require.True(t, ok)
	assert.Equal(t, codes.InvalidArgument, st.Code())
	assert.Contains(t, st.Message(), "60")
}

// TestGRPC_SetCycleInterval_TooHigh verifies that intervals above
// 86400s are rejected with InvalidArgument.
func TestGRPC_SetCycleInterval_TooHigh(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	_, err := h.Client.SetCycleInterval(ctx, &gatewayv1.SetCycleIntervalRequest{
		IntervalSeconds: 100000,
	})

	require.Error(t, err)
	st, ok := status.FromError(err)
	require.True(t, ok)
	assert.Equal(t, codes.InvalidArgument, st.Code())
	assert.Contains(t, st.Message(), "86400")
}

// ---------------------------------------------------------------------------
// GetGatewayConfig
// ---------------------------------------------------------------------------

// TestGRPC_GetGatewayConfig verifies that GetGatewayConfig returns
// all config fields matching the test configuration.
func TestGRPC_GetGatewayConfig(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	resp, err := h.Client.GetGatewayConfig(ctx, &gatewayv1.GetGatewayConfigRequest{})

	require.NoError(t, err)
	require.NotNil(t, resp)

	assert.True(t, resp.Enabled)
	assert.Equal(t, int32(60), resp.CycleIntervalSeconds)
	assert.Equal(t, int32(300), resp.CycleTimeoutSeconds)
	assert.Equal(t, int32(4), resp.MaxConcurrentSymbols)
	assert.Equal(t, int32(0), resp.TaCacheTtlSeconds) // Disabled in test config.
	assert.Equal(t, int32(0), resp.MacroCacheTtlSeconds)
	assert.Equal(t, int32(1), resp.MaxCycleRetries)
	assert.Equal(t, []string{"EURUSD", "GBPUSD"}, resp.DefaultSymbols)
	assert.True(t, resp.ExecutionEnabled)

	// Active symbols should be the defaults (Redis unreachable).
	assert.NotEmpty(t, resp.ActiveSymbols)
}

// ---------------------------------------------------------------------------
// GetActiveSymbols
// ---------------------------------------------------------------------------

// TestGRPC_GetActiveSymbols verifies that GetActiveSymbols returns
// the default symbols when Redis is unreachable.
func TestGRPC_GetActiveSymbols(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	resp, err := h.Client.GetActiveSymbols(ctx, &gatewayv1.GetActiveSymbolsRequest{})

	require.NoError(t, err)
	require.NotNil(t, resp)

	// Falls back to config defaults since Redis is unreachable.
	assert.Contains(t, resp.Symbols, "EURUSD")
	assert.Contains(t, resp.Symbols, "GBPUSD")
}
