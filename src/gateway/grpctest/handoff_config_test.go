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
	"github.com/flamegreat-1/etradie/src/auth"
	e2e "github.com/flamegreat-1/etradie/src/gateway/e2etest"
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

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 10*time.Second)
	defer cancel()

	resp, err := h.Client.NotifyExecutionCompleted(ctx, &gatewayv1.NotifyExecutionCompletedRequest{
		Symbol:          "EURUSD",
		BrokerOrderId:   "TKT-12345",
		FillPrice:       1.10000,
		Slippage:        0.00002,
		LotSize:         0.10,
		AnalysisId:      "SMC-EURUSD-H4-001",
		TraceId:         "trace-grpc-handoff-001",
		Direction:       "BUY",
		StopLoss:        1.09500,
		Tp1Price:        1.10500,
		Tp1Pct:          40,
		Tp2Price:        1.11000,
		Tp2Pct:          30,
		Tp3Price:        1.11500,
		Tp3Pct:          30,
		RiskAmount:      100.0,
		RiskPercent:     1.0,
		RrRatio:         3.0,
		Grade:           "A",
		TradingStyle:    "INTRADAY",
		Session:         "LONDON_NY_OVERLAP",
		ConfluenceScore: 8.5,
		ExecutionMode:   "LIMIT",
		SetupType:       "TURTLE_SOUP",
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

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 10*time.Second)
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

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 10*time.Second)
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

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 10*time.Second)
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

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 10*time.Second)
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

	authCtx := h.AuthContext("test-user-config-001", "testuser-config", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 10*time.Second)
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
	// No operator default basket exists any more: the field is always
	// empty. Symbols are sourced exclusively from the user's broker.
	assert.Empty(t, resp.DefaultSymbols)
	assert.True(t, resp.ExecutionEnabled)

	// A user with no persisted selection has an empty (non-nil) active
	// set — there is no fallback to a default basket.
	assert.NotNil(t, resp.ActiveSymbols)
	assert.Empty(t, resp.ActiveSymbols)
}

// ---------------------------------------------------------------------------
// GetActiveSymbols
// ---------------------------------------------------------------------------

// TestGRPC_GetActiveSymbols verifies that a user with no persisted
// selection gets an empty (non-nil) symbol set — there is no default
// basket to fall back to.
func TestGRPC_GetActiveSymbols(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	authCtx := h.AuthContext("test-user-noselection-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 10*time.Second)
	defer cancel()

	resp, err := h.Client.GetActiveSymbols(ctx, &gatewayv1.GetActiveSymbolsRequest{})

	require.NoError(t, err)
	require.NotNil(t, resp)

	// No selection -> empty, non-nil. Symbols come only from the broker.
	assert.NotNil(t, resp.Symbols)
	assert.Empty(t, resp.Symbols)
}

// ---------------------------------------------------------------------------
// SetActiveSymbols
// ---------------------------------------------------------------------------

// TestGRPC_SetActiveSymbols_Valid verifies that SetActiveSymbols accepts
// a new symbol list and returns the updated active symbols. The harness
// uses a real Redis, so the selection persists; the RPC must succeed
// and return a non-nil active set. (Symbol-vs-broker-catalogue
// validation lives on the REST PUT /api/v1/symbols path, not this gRPC
// setter, so arbitrary names are accepted here.)
func TestGRPC_SetActiveSymbols_Valid(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 10*time.Second)
	defer cancel()

	resp, err := h.Client.SetActiveSymbols(ctx, &gatewayv1.SetActiveSymbolsRequest{
		Symbols: []string{"EURUSD", "USDJPY", "GBPJPY"},
	})

	require.NoError(t, err, "SetActiveSymbols should not return gRPC error")
	require.NotNil(t, resp)

	// The RPC must succeed and return a valid (non-nil) response.
	assert.NotNil(t, resp.ActiveSymbols, "active symbols should be returned")
}

// ---------------------------------------------------------------------------
// ResetActiveSymbols
// ---------------------------------------------------------------------------

// TestGRPC_ResetActiveSymbols verifies that ResetActiveSymbols clears
// the user's selection. There is no default basket to restore to, so
// the post-reset active set is empty until the user re-selects from
// their broker catalogue.
func TestGRPC_ResetActiveSymbols(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	authCtx := h.AuthContext("test-user-reset-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 10*time.Second)
	defer cancel()

	resp, err := h.Client.ResetActiveSymbols(ctx, &gatewayv1.ResetActiveSymbolsRequest{})

	require.NoError(t, err, "ResetActiveSymbols should not return gRPC error")
	require.NotNil(t, resp)

	// After clear, the active set is empty (non-nil). No default basket.
	assert.NotNil(t, resp.ActiveSymbols)
	assert.Empty(t, resp.ActiveSymbols)
}

// ---------------------------------------------------------------------------
// GetHealth
// ---------------------------------------------------------------------------

// TestGRPC_GetHealth verifies that GetHealth returns a valid response.
// The test harness connects to real Redis on localhost:6379, so Redis
// should be healthy. The Engine mock is also running. Status should be "ok".
func TestGRPC_GetHealth(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 10*time.Second)
	defer cancel()

	resp, err := h.Client.GetHealth(ctx, &gatewayv1.GetHealthRequest{})

	require.NoError(t, err, "GetHealth should not return gRPC error")
	require.NotNil(t, resp)

	// Redis is connected in test harness (real Redis on localhost:6379).
	assert.True(t, resp.RedisConnected,
		"Redis should be connected in test harness")

	// Status should be "ok" since Redis is healthy.
	assert.Equal(t, "ok", resp.Status,
		"health status should be ok when Redis is connected")

	// Active cycles should be 0 (no cycles running).
	assert.Equal(t, int32(0), resp.ActiveCycles)
}

// ---------------------------------------------------------------------------
// RunCycle Input Validation
// ---------------------------------------------------------------------------

// TestGRPC_RunCycle_InvalidSymbol_EmptyString verifies that RunCycle
// handles an empty string in the symbols array gracefully. The pipeline
// should not panic and should produce a valid response.
func TestGRPC_RunCycle_InvalidSymbol_EmptyString(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = e2e.TAResponseNoCandidates()
	h.Engine.MacroResponse = e2e.MacroResponseFull()

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 60*time.Second)
	defer cancel()

	// Send a symbol list containing an empty string.
	resp, err := h.Client.RunCycle(ctx, &gatewayv1.RunCycleRequest{
		Symbols: []string{""},
		TraceId: "trace-grpc-empty-symbol-001",
	})

	// The server should not crash. It may return an error or handle gracefully.
	if err != nil {
		// If the server returns an error, it should be a proper gRPC status.
		st, ok := status.FromError(err)
		require.True(t, ok, "error should be a gRPC status")
		t.Logf("Server returned gRPC error for empty symbol: code=%s msg=%s",
			st.Code(), st.Message())
	} else {
		// If it succeeds, it should have valid outputs.
		require.NotNil(t, resp)
		for _, out := range resp.Outputs {
			assert.NotEqual(t, "PANIC", out.CycleStatus,
				"pipeline should never panic on invalid input")
		}
	}
}
