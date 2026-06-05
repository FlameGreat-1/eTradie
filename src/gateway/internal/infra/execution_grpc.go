package infra

import (
	"context"
	"fmt"
	"strings"

	"github.com/google/uuid"
	"github.com/rs/zerolog"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"

	executionv1 "github.com/flamegreat-1/etradie/proto/execution/v1"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/pkg/resilience"
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
	req := BuildExecuteRequest(decision)

	a.log.Info().
		Str("symbol", req.GetSymbol()).
		Str("direction", req.GetDirection()).
		Str("grade", req.GetGrade()).
		Str("analysis_id", req.GetAnalysisId()).
		Msg("calling_execution_service")

	// Use AnalysisID as idempotency key, fallback to UUID
	idempotencyKey := req.GetAnalysisId()
	if idempotencyKey == "" {
		idempotencyKey = uuid.New().String()
	}

	// Forward the JWT authorization header from the incoming Gateway
	// request to the outgoing Execution gRPC call. gRPC incoming
	// metadata is NOT automatically copied to outgoing metadata.
	metadataKVs := []string{"x-idempotency-key", idempotencyKey}
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		metadataKVs = append(metadataKVs, "authorization", "Bearer "+rawToken)
	}
	retryCtx := metadata.AppendToOutgoingContext(ctx, metadataKVs...)

	var resp *executionv1.ExecuteTradeResponse
	operation := func() error {
		var err error
		resp, err = a.client.ExecuteTrade(retryCtx, req)
		return err
	}

	isRetryable := func(err error) bool {
		st, ok := status.FromError(err)
		if !ok {
			return false
		}
		return st.Code() == codes.Unavailable || st.Code() == codes.DeadlineExceeded || st.Code() == codes.Internal
	}

	if err := resilience.Retry(ctx, resilience.DefaultRetryConfig, isRetryable, operation); err != nil {
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

// GetState retrieves the current execution state (open positions, pending orders).
func (a *ExecutionGRPCAdapter) GetState(ctx context.Context, traceID string) (map[string]interface{}, error) {
	req := &executionv1.GetStateRequest{TraceId: traceID}

	var metadataKVs []string
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		metadataKVs = append(metadataKVs, "authorization", "Bearer "+rawToken)
	}
	retryCtx := metadata.AppendToOutgoingContext(ctx, metadataKVs...)

	var resp *executionv1.GetStateResponse
	operation := func() error {
		var err error
		resp, err = a.client.GetExecutionState(retryCtx, req)
		return err
	}

	isRetryable := func(err error) bool {
		st, ok := status.FromError(err)
		if !ok {
			return false
		}
		return st.Code() == codes.Unavailable || st.Code() == codes.DeadlineExceeded || st.Code() == codes.Internal
	}

	if err := resilience.Retry(ctx, resilience.DefaultRetryConfig, isRetryable, operation); err != nil {
		a.log.Error().Err(err).Msg("execution_rpc_failed_get_state")
		return nil, fmt.Errorf("execution get state: %w", err)
	}

	// For simplicity, just return the raw struct, or map.
	// Since port expects a map for easy routing use, we build a simple map.
	result := map[string]interface{}{
		"open_position_count": resp.GetOpenPositionCount(),
		"pending_order_count": resp.GetPendingOrderCount(),
		"pending_orders":      resp.GetPendingOrders(),
		"open_positions":      resp.GetOpenPositions(),
	}

	return result, nil
}

// CancelOrder cancels a pending order by ID.
func (a *ExecutionGRPCAdapter) CancelOrder(ctx context.Context, orderID, symbol, reason, traceID string) error {
	req := &executionv1.CancelOrderRequest{
		OrderId: orderID,
		Symbol:  symbol,
		Reason:  reason,
		TraceId: traceID,
	}

	var metadataKVs []string
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		metadataKVs = append(metadataKVs, "authorization", "Bearer "+rawToken)
	}
	retryCtx := metadata.AppendToOutgoingContext(ctx, metadataKVs...)

	var resp *executionv1.CancelOrderResponse
	operation := func() error {
		var err error
		resp, err = a.client.CancelPendingOrder(retryCtx, req)
		return err
	}

	isRetryable := func(err error) bool {
		st, ok := status.FromError(err)
		if !ok {
			return false
		}
		return st.Code() == codes.Unavailable || st.Code() == codes.DeadlineExceeded || st.Code() == codes.Internal
	}

	if err := resilience.Retry(ctx, resilience.DefaultRetryConfig, isRetryable, operation); err != nil {
		a.log.Error().Err(err).Str("order_id", orderID).Msg("execution_rpc_failed_cancel_order")
		return fmt.Errorf("execution cancel order: %w", err)
	}

	if !resp.GetSuccess() {
		return fmt.Errorf("cancel order failed: %s", resp.GetStatus())
	}

	return nil
}

// HaltState reads the kill-switch flags from the execution service
// (CHECKLIST Section 8). Forwards the JWT so the server can enforce
// authz on cross-user reads.
func (a *ExecutionGRPCAdapter) HaltState(ctx context.Context, targetUserID string) (bool, bool, error) {
	req := &executionv1.GetHaltStateRequest{TargetUserId: targetUserID}

	var metadataKVs []string
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		metadataKVs = append(metadataKVs, "authorization", "Bearer "+rawToken)
	}
	callCtx := metadata.AppendToOutgoingContext(ctx, metadataKVs...)

	var resp *executionv1.GetHaltStateResponse
	operation := func() error {
		var err error
		resp, err = a.client.GetHaltState(callCtx, req)
		return err
	}
	isRetryable := func(err error) bool {
		st, ok := status.FromError(err)
		if !ok {
			return false
		}
		return st.Code() == codes.Unavailable || st.Code() == codes.DeadlineExceeded || st.Code() == codes.Internal
	}
	if err := resilience.Retry(ctx, resilience.DefaultRetryConfig, isRetryable, operation); err != nil {
		return false, false, fmt.Errorf("execution get halt state: %w", err)
	}
	return resp.GetGlobalHalted(), resp.GetUserHalted(), nil
}

// SetHaltState writes a kill-switch flag via the execution service
// (CHECKLIST Section 8). scope is "global" or "user"; the JWT is
// forwarded so the server enforces admin/self authz.
func (a *ExecutionGRPCAdapter) SetHaltState(ctx context.Context, scope, targetUserID string, halted bool) (bool, bool, error) {
	var protoScope executionv1.KillSwitchScope
	switch strings.ToLower(strings.TrimSpace(scope)) {
	case "global":
		protoScope = executionv1.KillSwitchScope_KILL_SWITCH_SCOPE_GLOBAL
	case "user":
		protoScope = executionv1.KillSwitchScope_KILL_SWITCH_SCOPE_USER
	default:
		return false, false, fmt.Errorf("execution set halt state: invalid scope %q", scope)
	}

	req := &executionv1.SetHaltStateRequest{
		Scope:        protoScope,
		TargetUserId: targetUserID,
		Halted:       halted,
	}

	var metadataKVs []string
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		metadataKVs = append(metadataKVs, "authorization", "Bearer "+rawToken)
	}
	callCtx := metadata.AppendToOutgoingContext(ctx, metadataKVs...)

	var resp *executionv1.SetHaltStateResponse
	operation := func() error {
		var err error
		resp, err = a.client.SetHaltState(callCtx, req)
		return err
	}
	// Authorization / argument failures must NOT be retried; only
	// transient transport errors are.
	isRetryable := func(err error) bool {
		st, ok := status.FromError(err)
		if !ok {
			return false
		}
		return st.Code() == codes.Unavailable || st.Code() == codes.DeadlineExceeded
	}
	if err := resilience.Retry(ctx, resilience.DefaultRetryConfig, isRetryable, operation); err != nil {
		return false, false, fmt.Errorf("execution set halt state: %w", err)
	}
	return resp.GetGlobalHalted(), resp.GetUserHalted(), nil
}

// Close shuts down the gRPC connection.
func (a *ExecutionGRPCAdapter) Close() error {
	if a.conn != nil {
		return a.conn.Close()
	}
	return nil
}

func BuildExecuteRequest(d *models.ProcessorOutput) *executionv1.ExecuteTradeRequest {
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
		ExecutionMode:   d.ExecutionMode,
		LtfConfirmed:    d.LTFConfirmed,
		SetupType:       d.SetupType,
		ObUpper:         d.OBUpper,
		ObLower:         d.OBLower,
		LtfTimeframe:    d.LTFTimeframe,
		HtfTimeframe:    d.HTFTimeframe,
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
