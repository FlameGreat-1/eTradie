package infra

import (
	"context"
	"fmt"

	"github.com/rs/zerolog"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	executionv1 "github.com/flamegreat/etradie/proto/execution/v1"
	"github.com/flamegreat/etradie/src/gateway/internal/models"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
)

// ExecutionGRPCAdapter implements ports.ExecutionPort by calling
// Module B's ExecutionService via gRPC.
type ExecutionGRPCAdapter struct {
	client executionv1.ExecutionServiceClient
	conn   *grpc.ClientConn
	log    zerolog.Logger
}

// NewExecutionGRPCAdapter creates a gRPC client for Module B's execution engine.
// Uses grpc.NewClient (non-blocking). The connection is established lazily
// on the first RPC call. Startup health is verified separately in main.go.
func NewExecutionGRPCAdapter(addr string, timeoutMs int) (*ExecutionGRPCAdapter, error) {
	log := observability.Logger("execution_grpc_adapter")

	_ = timeoutMs // Retained in signature for config compatibility; per-RPC timeouts are set via context.

	conn, err := grpc.NewClient(addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		return nil, fmt.Errorf("execution adapter: create client for %s: %w", addr, err)
	}

	log.Info().Str("addr", addr).Msg("execution_grpc_client_created")

	return &ExecutionGRPCAdapter{
		client: executionv1.NewExecutionServiceClient(conn),
		conn:   conn,
		log:    log,
	}, nil
}

// HealthCheck verifies the execution engine is reachable by calling GetExecutionState.
func (a *ExecutionGRPCAdapter) HealthCheck(ctx context.Context) bool {
	_, err := a.client.GetExecutionState(ctx, &executionv1.GetStateRequest{})
	if err != nil {
		a.log.Warn().Err(err).Msg("execution_health_check_failed")
		return false
	}
	return true
}

// Execute converts ProcessorOutput to an ExecuteTradeRequest, calls
// Module B, and returns the response as a map for the router.
func (a *ExecutionGRPCAdapter) Execute(ctx context.Context, decision *models.ProcessorOutput) (map[string]interface{}, error) {
	req := buildExecuteRequest(decision)

	a.log.Info().
		Str("symbol", req.GetSymbol()).
		Str("direction", req.GetDirection()).
		Str("grade", req.GetGrade()).
		Str("analysis_id", req.GetAnalysisId()).
		Msg("calling_execution_service")

	resp, err := a.client.ExecuteTrade(ctx, req)
	if err != nil {
		a.log.Error().Err(err).Str("symbol", req.GetSymbol()).Msg("execution_rpc_failed")
		return nil, fmt.Errorf("execution RPC: %w", err)
	}

	result := map[string]interface{}{
		"accepted":         resp.GetAccepted(),
		"status":           resp.GetStatus(),
		"order_id":         resp.GetOrderId(),
		"rejection_reason": resp.GetRejectionReason(),
		"rejection_check":  resp.GetRejectionCheck(),
		"lot_size":         resp.GetLotSize(),
		"risk_amount":      resp.GetRiskAmount(),
		"account_balance":  resp.GetAccountBalance(),
		"sl_distance_pips": resp.GetSlDistancePips(),
		"pip_value":        resp.GetPipValue(),
		"execution_mode":   resp.GetExecutionMode(),
		"entry_price":      resp.GetEntryPrice(),
		"analysis_id":      resp.GetAnalysisId(),
		"trace_id":         resp.GetTraceId(),
	}

	a.log.Info().
		Str("symbol", req.GetSymbol()).
		Bool("accepted", resp.GetAccepted()).
		Str("status", resp.GetStatus()).
		Str("order_id", resp.GetOrderId()).
		Msg("execution_response_received")

	return result, nil
}

// Close shuts down the gRPC connection.
func (a *ExecutionGRPCAdapter) Close() error {
	if a.conn != nil {
		return a.conn.Close()
	}
	return nil
}

func buildExecuteRequest(d *models.ProcessorOutput) *executionv1.ExecuteTradeRequest {
	req := &executionv1.ExecuteTradeRequest{
		Symbol:          d.Symbol,
		Direction:       d.Direction,
		Confidence:      d.Confidence,
		Grade:           d.Grade,
		TradingStyle:    d.TradingStyle,
		Session:         d.Session,
		ConfluenceScore: d.ConfluenceScore,
		AnalysisId:      d.AnalysisID,
		TraceId:         d.AnalysisID, // Trace correlation: analysis_id doubles as trace_id when no explicit trace_id exists.
		Tp1Pct:          int32(d.TP1Pct),
		Tp2Pct:          int32(d.TP2Pct),
		Tp3Pct:          int32(d.TP3Pct),
	}

	// Safely dereference pointer fields.
	if d.EntryZoneLow != nil {
		req.EntryZoneLow = *d.EntryZoneLow
	}
	if d.EntryZoneHigh != nil {
		req.EntryZoneHigh = *d.EntryZoneHigh
	}
	if d.StopLoss != nil {
		req.StopLoss = *d.StopLoss
	}
	if d.TP1Price != nil {
		req.Tp1Price = *d.TP1Price
	}
	if d.TP2Price != nil {
		req.Tp2Price = *d.TP2Price
	}
	if d.TP3Price != nil {
		req.Tp3Price = *d.TP3Price
	}
	if d.RiskPercentage != nil {
		req.RiskPercentage = *d.RiskPercentage
	}
	if d.RRRatio != nil {
		req.RrRatio = *d.RRRatio
	}

	return req
}
