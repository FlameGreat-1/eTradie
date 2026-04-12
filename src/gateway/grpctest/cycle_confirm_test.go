package gateway_grpc

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	gatewayv1 "github.com/flamegreat-1/etradie/proto/gateway/v1"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/e2etest"
)

// TestGRPC_RunCycle_HappyPath calls RunCycle via gRPC and verifies
// the full pipeline executes through the real GRPCServer, returning
// CycleOutput with processor output, guard result, and execution result.
func TestGRPC_RunCycle_HappyPath(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = e2e.TAResponseWithCandidates()
	h.Engine.MacroResponse = e2e.MacroResponseFull()
	h.Engine.RAGResponse = e2e.RAGResponseWithChunks()
	h.Engine.ProcessorResponse = e2e.ProcessorResponseTradeValid()

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 60*time.Second)
	defer cancel()

	resp, err := h.Client.RunCycle(ctx, &gatewayv1.RunCycleRequest{
		Symbols: []string{"EURUSD"},
		TraceId: "trace-grpc-runcycle-001",
	})

	require.NoError(t, err, "RunCycle RPC should not return error")
	require.NotNil(t, resp)
	require.NotEmpty(t, resp.Outputs, "should have at least one output")

	// ---------------------------------------------------------------
	// Assert: Engine endpoints were called.
	// ---------------------------------------------------------------
	assert.Equal(t, int64(1), h.Engine.TACalls.Load())
	assert.Equal(t, int64(1), h.Engine.MacroCalls.Load())
	assert.Equal(t, int64(1), h.Engine.RAGCalls.Load())
	assert.Equal(t, int64(1), h.Engine.ProcessorCalls.Load())

	// ---------------------------------------------------------------
	// Assert: First output has correct status.
	// ---------------------------------------------------------------
	output := resp.Outputs[0]
	assert.Equal(t, "COMPLETED", output.CycleStatus)
	assert.Equal(t, "EURUSD", output.Symbol)
	assert.Equal(t, "trace-grpc-runcycle-001", output.TraceId)
	assert.Greater(t, output.DurationMs, 0.0)
	assert.Empty(t, output.Error)

	// ---------------------------------------------------------------
	// Assert: Processor output JSON is populated and parseable.
	// ---------------------------------------------------------------
	assert.NotEmpty(t, output.ProcessorOutputJson,
		"processor_output_json should be populated")
	var procOutput map[string]interface{}
	err = json.Unmarshal(output.ProcessorOutputJson, &procOutput)
	require.NoError(t, err, "processor_output_json should be valid JSON")
	assert.Equal(t, true, procOutput["trade_valid"])
	assert.Equal(t, "LONG", procOutput["direction"])
	assert.Equal(t, "EURUSD", procOutput["symbol"])
}

// TestGRPC_RunCycle_NoCandidates verifies the gRPC response when TA
// returns no candidates. The pipeline completes with INSUFFICIENT_DATA.
func TestGRPC_RunCycle_NoCandidates(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = e2e.TAResponseNoCandidates()
	h.Engine.MacroResponse = e2e.MacroResponseFull()

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 60*time.Second)
	defer cancel()

	resp, err := h.Client.RunCycle(ctx, &gatewayv1.RunCycleRequest{
		Symbols: []string{"EURUSD"},
		TraceId: "trace-grpc-nocandidate-001",
	})

	require.NoError(t, err)
	require.NotNil(t, resp)
	require.NotEmpty(t, resp.Outputs)

	output := resp.Outputs[0]
	assert.Equal(t, "COMPLETED", output.CycleStatus)
	assert.Equal(t, "INSUFFICIENT_DATA", output.CycleOutcome)
	assert.Empty(t, output.Error)

	// RAG and Processor should NOT have been called.
	assert.Equal(t, int64(0), h.Engine.RAGCalls.Load())
	assert.Equal(t, int64(0), h.Engine.ProcessorCalls.Load())
}

// TestGRPC_RunCycle_EmptySymbols_UsesDefaults verifies that when
// RunCycle is called with an empty symbols list, the server falls
// back to the active symbols from the SymbolStore (which falls back
// to config defaults since Redis is unreachable in tests).
func TestGRPC_RunCycle_EmptySymbols_UsesDefaults(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = e2e.TAResponseNoCandidates()
	h.Engine.MacroResponse = e2e.MacroResponseFull()

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 60*time.Second)
	defer cancel()

	resp, err := h.Client.RunCycle(ctx, &gatewayv1.RunCycleRequest{
		Symbols: nil, // Empty: server should use defaults.
		TraceId: "trace-grpc-defaults-001",
	})

	require.NoError(t, err)
	require.NotNil(t, resp)
	require.NotEmpty(t, resp.Outputs)

	// TA should have been called with the default symbols.
	taCalls := h.Engine.CallsForPath("/internal/ta/analyze")
	require.NotEmpty(t, taCalls)
	taBody := taCalls[0].Body
	require.NotNil(t, taBody)

	// Default symbols from config: ["EURUSD", "GBPUSD"]
	taSymbols, ok := taBody["symbols"].([]interface{})
	require.True(t, ok)
	assert.Len(t, taSymbols, 2, "should use 2 default symbols")
}

// TestGRPC_ConfirmSetup_Confirmed calls ConfirmSetup via gRPC and
// verifies the response when LTF confirmation is met.
func TestGRPC_ConfirmSetup_Confirmed(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	h.Engine.TAResponse = e2e.TAResponseWithCandidates()

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 30*time.Second)
	defer cancel()

	resp, err := h.Client.ConfirmSetup(ctx, &gatewayv1.ConfirmSetupRequest{
		Symbol:     "EURUSD",
		AnalysisId: "SMC-EURUSD-H4-001",
		TraceId:    "trace-grpc-confirm-001",
	})

	require.NoError(t, err)
	require.NotNil(t, resp)

	assert.True(t, resp.Confirmed, "LTF should be confirmed")
	assert.True(t, resp.LtfConfirmation)
	assert.Equal(t, "SMC LTF confirmation met", resp.Reason)
	assert.Equal(t, "trace-grpc-confirm-001", resp.TraceId)

	// Only TA should have been called (confirmation pulse bypasses others).
	assert.Equal(t, int64(1), h.Engine.TACalls.Load())
	assert.Equal(t, int64(0), h.Engine.MacroCalls.Load())
	assert.Equal(t, int64(0), h.Engine.RAGCalls.Load())
	assert.Equal(t, int64(0), h.Engine.ProcessorCalls.Load())
}

// TestGRPC_ConfirmSetup_ValidationError verifies that ConfirmSetup
// returns InvalidArgument when required fields are missing.
func TestGRPC_ConfirmSetup_ValidationError(t *testing.T) {
	h := NewHarness(t)
	defer h.Close()

	authCtx := h.AuthContext("test-user-001", "testuser", auth.RoleEtradie)
	ctx, cancel := context.WithTimeout(authCtx, 10*time.Second)
	defer cancel()

	// Missing symbol.
	_, err := h.Client.ConfirmSetup(ctx, &gatewayv1.ConfirmSetupRequest{
		Symbol:     "",
		AnalysisId: "SMC-EURUSD-H4-001",
	})

	require.Error(t, err)
	st, ok := status.FromError(err)
	require.True(t, ok, "error should be a gRPC status")
	assert.Equal(t, codes.InvalidArgument, st.Code())
	assert.Contains(t, st.Message(), "required")

	// Missing analysis_id.
	_, err = h.Client.ConfirmSetup(ctx, &gatewayv1.ConfirmSetupRequest{
		Symbol:     "EURUSD",
		AnalysisId: "",
	})

	require.Error(t, err)
	st, ok = status.FromError(err)
	require.True(t, ok)
	assert.Equal(t, codes.InvalidArgument, st.Code())
}
