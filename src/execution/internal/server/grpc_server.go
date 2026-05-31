package server

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/rs/zerolog"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"

	executionv1 "github.com/flamegreat-1/etradie/proto/execution/v1"
	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/execution/internal/audit"
	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
	"github.com/flamegreat-1/etradie/src/execution/internal/builder"
	"github.com/flamegreat-1/etradie/src/execution/internal/config"
	"github.com/flamegreat-1/etradie/src/execution/internal/constants"
	"github.com/flamegreat-1/etradie/src/execution/internal/executor"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
	"github.com/flamegreat-1/etradie/src/execution/internal/sizing"
	"github.com/flamegreat-1/etradie/src/execution/internal/state"
	"github.com/flamegreat-1/etradie/src/execution/internal/store"
	"github.com/flamegreat-1/etradie/src/execution/internal/validator"
	"github.com/flamegreat-1/etradie/src/execution/internal/watcher"
)

// ExecutionServer implements executionv1.ExecutionServiceServer.
type ExecutionServer struct {
	executionv1.UnimplementedExecutionServiceServer

	cfg       *config.Config
	validator *validator.Validator
	sizer     *sizing.Engine
	executor  *executor.Executor
	state     *state.Manager
	broker    broker.Port
	audit     *audit.Logger
	transport *alertredis.Transport
	settings  *store.SettingsStore
	watcher   *watcher.Manager
	queue     *executor.BurstQueue
	log       zerolog.Logger
}

// NewExecutionServer creates the gRPC server with all dependencies.
func NewExecutionServer(
	cfg *config.Config,
	v *validator.Validator,
	s *sizing.Engine,
	e *executor.Executor,
	sm *state.Manager,
	bp broker.Port,
	al *audit.Logger,
	transport *alertredis.Transport,
	ss *store.SettingsStore,
	wm *watcher.Manager,
	q *executor.BurstQueue,
) *ExecutionServer {
	return &ExecutionServer{
		cfg:       cfg,
		validator: v,
		sizer:     s,
		executor:  e,
		state:     sm,
		broker:    bp,
		audit:     al,
		transport: transport,
		settings:  ss,
		watcher:   wm,
		queue:     q,
		log:       observability.Logger("grpc_server"),
	}
}

// resolveExecutionMode reads the current execution mode from the DB.
// Falls back to AUTO if the DB read fails or the value is invalid.
func (s *ExecutionServer) resolveExecutionMode(ctx context.Context, userID string) constants.ExecutionMode {
	val, err := s.settings.Get(ctx, userID, store.KeyExecutionMode)
	if err != nil {
		return constants.ModeAuto
	}
	mode := constants.ExecutionMode(strings.ToUpper(val))
	if mode != constants.ModeLimit && mode != constants.ModeInstant && mode != constants.ModeAuto {
		return constants.ModeAuto
	}
	return mode
}

// resolveRuntimeParams reads all dashboard-configurable validation
// parameters from the settings store. Falls back to config defaults
// for any value that fails to load. Called on every trade so that
// dashboard changes take immediate effect.
func (s *ExecutionServer) resolveRuntimeParams(ctx context.Context, userID string) *validator.RuntimeParams {
	params := &validator.RuntimeParams{
		MaxConcurrentTrades: s.cfg.MaxConcurrentTrades,
		DailyLossLimitPct:   s.cfg.DailyLossLimitPct,
		WeeklyDrawdownPct:   s.cfg.WeeklyDrawdownPct,
	}

	if val, err := s.settings.Get(ctx, userID, store.KeyMaxConcurrentTrades); err == nil {
		if n, err := strconv.Atoi(val); err == nil && n >= 1 && n <= 10 {
			params.MaxConcurrentTrades = n
		}
	}

	if val, err := s.settings.Get(ctx, userID, store.KeyDailyLossLimitPct); err == nil {
		if f, err := strconv.ParseFloat(val, 64); err == nil && f >= 0.5 && f <= 10.0 {
			params.DailyLossLimitPct = f
		}
	}

	if val, err := s.settings.Get(ctx, userID, store.KeyWeeklyDrawdownPct); err == nil {
		if f, err := strconv.ParseFloat(val, 64); err == nil && f >= 1.0 && f <= 20.0 {
			params.WeeklyDrawdownPct = f
		}
	}

	return params
}

// ExecuteTrade is the main RPC. Orchestrates the full Module B pipeline.
func (s *ExecutionServer) ExecuteTrade(ctx context.Context, req *executionv1.ExecuteTradeRequest) (resp *executionv1.ExecuteTradeResponse, err error) {
	defer func() {
		if r := recover(); r != nil {
			s.log.Error().Interface("panic", r).Str("trace_id", req.GetTraceId()).Msg("execute_trade_panic")
			err = status.Errorf(codes.Internal, "internal error")
			resp = nil
		}
	}()

	start := time.Now()
	traceID := req.GetTraceId()

	if err := validateRequest(req); err != nil {
		return nil, status.Errorf(codes.InvalidArgument, "invalid request: %s", err.Error())
	}

	analysisID := req.GetAnalysisId()

	s.log.Info().
		Str("symbol", req.GetSymbol()).
		Str("direction", req.GetDirection()).
		Str("grade", req.GetGrade()).
		Str("analysis_id", analysisID).
		Str("trace_id", traceID).
		Msg("execute_trade_received")

	// Extract authenticated user + tier from context (set by auth interceptor).
	// Defense-in-depth: the gateway router already blocks Free-tier execution
	// at the perimeter, but Execution must also reject directly so that any
	// future caller path (or a misconfigured ingress) cannot bypass billing.
	claims := auth.ClaimsFromContext(ctx)
	if claims == nil {
		return nil, status.Errorf(codes.Unauthenticated, "missing claims in context")
	}
	userID := claims.UserID
	if userID == "" {
		return nil, status.Errorf(codes.Unauthenticated, "user_id not found in context")
	}
	if claims.Role != auth.RoleAdmin && claims.Tier == "free" {
		return nil, status.Errorf(codes.PermissionDenied,
			"automated trade execution is restricted to Pro users")
	}

	// Backpressure: acquire a queue slot before any broker-touching
	// work. Overflow / deadline returns a non-retryable QUEUED response
	// (not a gRPC error) so the gateway does not retry and defeat the
	// gate. A nil queue (tests) skips the gate.
	if s.queue != nil {
		release, qErr := s.queue.Enter(ctx, userID)
		if qErr != nil {
			s.log.Warn().Err(qErr).Str("user_id", userID).Str("trace_id", traceID).Msg("execute_trade_queue_rejected")
			observability.ExecutionTotal.WithLabelValues(req.GetSymbol(), req.GetDirection(), "queue_rejected").Inc()
			return &executionv1.ExecuteTradeResponse{
				Accepted:        false,
				Status:          string(constants.StatusQueued),
				RejectionReason: "execution intake at capacity: " + qErr.Error(),
				AnalysisId:      analysisID,
				TraceId:         traceID,
			}, nil
		}
		defer release()
	}

	tradeReq := parseRequest(req)
	tradeReq.UserID = userID

	// Refresh identity (tier, status, username) AND token on every
	// active watcher owned by this user. Critical because watcher
	// timeouts (default 45m) exceed access-token TTLs (default 15m),
	// and because tier changes mid-session must reach the watcher's
	// IdentityCtx in lock-step with the new JWT.
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		s.watcher.RefreshUserOrderIdentity(claims, rawToken)
	}

	// Step 1: Refresh broker state.
	if err := s.state.Refresh(ctx, userID); err != nil {
		s.log.Error().Err(err).Str("trace_id", traceID).Msg("state_refresh_failed")
		s.transport.Publish(ctx, alert.NewEvent(alert.SourceExecution, alert.TypeExecutionError, alert.SeverityError,
			"Failed to refresh broker state").WithUserID(userID).WithSymbol(req.GetSymbol()).WithTraceID(traceID))
		return rejectedResponse(tradeReq, "broker state refresh failed: "+err.Error(), 0, traceID), nil
	}

	// Step 2: Resolve runtime params from DB and validate.
	runtimeParams := s.resolveRuntimeParams(ctx, userID)
	valResult := s.validator.Validate(ctx, tradeReq, runtimeParams)
	if !valResult.Passed {
		s.audit.LogValidationRejected(ctx, tradeReq, valResult)

		s.transport.Publish(ctx, alert.NewEvent(alert.SourceExecution, alert.TypeOrderRejected, alert.SeverityWarning,
			"Trade rejected: "+valResult.Reason).
			WithUserID(userID).WithSymbol(req.GetSymbol()).WithDirection(req.GetDirection()).WithTraceID(traceID).
			WithDetails(map[string]interface{}{
				"check":       int32(valResult.FailedCheck),
				"outcome":     string(valResult.Outcome),
				"analysis_id": tradeReq.AnalysisID,
			}))

		if valResult.Outcome == constants.OutcomeLock {
			s.transport.Publish(ctx, alert.NewEvent(alert.SourceExecution, alert.TypeDailyLimitLocked, alert.SeverityCritical,
				"Execution locked: daily loss limit reached").
				WithUserID(userID).WithDetail("daily_loss_pct", s.state.DailyLossPercent(userID)))
		}
		if valResult.Outcome == constants.OutcomePause {
			s.transport.Publish(ctx, alert.NewEvent(alert.SourceExecution, alert.TypeWeeklyPaused, alert.SeverityCritical,
				"Execution paused: weekly drawdown limit reached").
				WithUserID(userID).WithDetail("weekly_drawdown_pct", s.state.WeeklyDrawdownPercent(userID)))
		}

		elapsed := time.Since(start).Seconds()
		observability.ExecutionDuration.Observe(elapsed)
		observability.ExecutionTotal.WithLabelValues(req.GetSymbol(), req.GetDirection(), string(valResult.Outcome)).Inc()

		return &executionv1.ExecuteTradeResponse{
			Accepted:        false,
			Status:          string(outcomeToStatus(valResult.Outcome)),
			RejectionReason: valResult.Reason,
			RejectionCheck:  int32(valResult.FailedCheck),
			AnalysisId:      tradeReq.AnalysisID,
			TraceId:         traceID,
		}, nil
	}

	s.audit.LogValidationPassed(ctx, tradeReq)

	// Step 3: Calculate position size.
	sizingResult, err := s.sizer.Calculate(ctx, tradeReq)
	if err != nil {
		s.log.Error().Err(err).Str("symbol", tradeReq.Symbol).Str("trace_id", traceID).Msg("sizing_failed")
		s.transport.Publish(ctx, alert.NewEvent(alert.SourceExecution, alert.TypeExecutionError, alert.SeverityError,
			"Position sizing failed: "+err.Error()).WithUserID(userID).WithSymbol(tradeReq.Symbol).WithTraceID(traceID))

		elapsed := time.Since(start).Seconds()
		observability.ExecutionDuration.Observe(elapsed)
		observability.ExecutionTotal.WithLabelValues(req.GetSymbol(), req.GetDirection(), "sizing_error").Inc()

		return rejectedResponse(tradeReq, "sizing failed: "+err.Error(), 0, traceID), nil
	}

	s.audit.LogLotSizeCalculated(ctx, tradeReq, sizingResult)

	// Step 4: Resolve execution mode. User Setting is Law.
	// If user sets LIMIT or INSTANT, force it. If AUTO, let LLM decide.
	execMode := s.resolveExecutionMode(ctx, userID)
	if execMode == constants.ModeAuto {
		execMode = s.cfg.ExecutionMode() // Fallback to config default initially
		if tradeReq.ExecutionMode != "" {
			m := constants.ExecutionMode(strings.ToUpper(tradeReq.ExecutionMode))
			if m == constants.ModeLimit || m == constants.ModeInstant {
				execMode = m // LLM decision applied
			}
		}
	}
	order := builder.BuildWithMode(tradeReq, sizingResult, s.cfg, execMode)

	// Stamp the full identity on the order so the watcher goroutine
	// can build claims-bearing contexts (Order.IdentityCtx) without
	// re-parsing the JWT. The four identity fields and the raw token
	// all originate at the trust boundary (auth interceptor) and flow
	// top-down.
	order.UserID = userID
	order.Username = claims.Username
	order.Role = string(claims.Role)
	order.Tier = claims.Tier
	order.StatusJWT = claims.Status
	order.AuthToken = auth.RawTokenFromContext(ctx)

	// Stamp the gateway-supplied idempotency key so the executor's
	// claim matches across RPC retries. Absent for direct callers, in
	// which case the executor falls back to OrderID.
	if idemKey := incomingIdempotencyKey(ctx); idemKey != "" {
		order.IdempotencyKey = idemKey
	}

	// Step 5: Execute.
	execResult, err := s.executor.Execute(ctx, order)
	if err != nil {
		s.log.Error().Err(err).Str("symbol", order.Symbol).Str("trace_id", traceID).Msg("execution_failed")
		s.transport.Publish(ctx, alert.NewEvent(alert.SourceExecution, alert.TypeExecutionError, alert.SeverityError,
			"Order execution failed: "+err.Error()).WithUserID(userID).WithSymbol(order.Symbol).WithTraceID(traceID))

		elapsed := time.Since(start).Seconds()
		observability.ExecutionDuration.Observe(elapsed)
		observability.ExecutionTotal.WithLabelValues(req.GetSymbol(), req.GetDirection(), "execution_error").Inc()

		return rejectedResponse(tradeReq, "execution failed: "+err.Error(), 0, traceID), nil
	}

	if !execResult.Accepted {
		elapsed := time.Since(start).Seconds()
		observability.ExecutionDuration.Observe(elapsed)
		observability.ExecutionTotal.WithLabelValues(req.GetSymbol(), req.GetDirection(), "broker_rejected").Inc()

		return &executionv1.ExecuteTradeResponse{
			Accepted:        false,
			Status:          string(execResult.Status),
			RejectionReason: execResult.RejectionReason,
			AnalysisId:      tradeReq.AnalysisID,
			TraceId:         traceID,
		}, nil
	}

	// Step 6: Audit + notify + idempotency.
	s.audit.LogOrderPlaced(ctx, order)

	modeLabel := "Limit order placed"
	if order.ExecutionMode == constants.ModeInstant {
		modeLabel = "Price watcher armed"
	}
	s.transport.Publish(ctx, alert.NewEvent(alert.SourceExecution, alert.TypeOrderPlaced, alert.SeverityInfo,
		modeLabel+" for "+order.Symbol).
		WithUserID(userID).WithSymbol(order.Symbol).WithDirection(string(order.Direction)).WithTraceID(traceID).
		WithDetails(map[string]interface{}{
			"order_id":       order.OrderID,
			"entry_price":    order.EntryPrice,
			"stop_loss":      order.StopLoss,
			"lot_size":       order.LotSize,
			"risk_amount":    order.RiskAmount,
			"grade":          order.Grade,
			"execution_mode": string(order.ExecutionMode),
			"analysis_id":    order.AnalysisID,
		}))

	if analysisID != "" {
		s.markProcessed(analysisID)
	}

	elapsed := time.Since(start).Seconds()
	observability.ExecutionDuration.Observe(elapsed)
	observability.ExecutionTotal.WithLabelValues(req.GetSymbol(), req.GetDirection(), "accepted").Inc()

	s.log.Info().
		Str("symbol", order.Symbol).
		Str("direction", string(order.Direction)).
		Str("order_id", order.OrderID).
		Str("mode", string(order.ExecutionMode)).
		Float64("lot_size", order.LotSize).
		Float64("risk_amount", order.RiskAmount).
		Float64("entry_price", order.EntryPrice).
		Str("analysis_id", order.AnalysisID).
		Str("trace_id", traceID).
		Float64("duration_ms", elapsed*1000).
		Msg("execute_trade_completed")

	return &executionv1.ExecuteTradeResponse{
		Accepted:       true,
		Status:         string(execResult.Status),
		OrderId:        execResult.OrderID,
		LotSize:        order.LotSize,
		RiskAmount:     order.RiskAmount,
		AccountBalance: order.AccountBalance,
		SlDistancePips: order.SLDistancePips,
		PipValue:       order.PipValue,
		ExecutionMode:  string(order.ExecutionMode),
		EntryPrice:     order.EntryPrice,
		AnalysisId:     order.AnalysisID,
		TraceId:        traceID,
	}, nil
}

// CancelPendingOrder cancels a pending limit order or disarms a watcher.
func (s *ExecutionServer) CancelPendingOrder(ctx context.Context, req *executionv1.CancelOrderRequest) (*executionv1.CancelOrderResponse, error) {
	userID := auth.UserIDFromContext(ctx)
	if userID == "" {
		return nil, status.Errorf(codes.Unauthenticated, "user_id not found in context")
	}
	_ = userID // Used by audit logger via context extraction.

	traceID := req.GetTraceId()

	if req.GetOrderId() == "" {
		return nil, status.Errorf(codes.InvalidArgument, "order_id is required")
	}

	s.log.Info().
		Str("order_id", req.GetOrderId()).
		Str("symbol", req.GetSymbol()).
		Str("reason", req.GetReason()).
		Str("trace_id", traceID).
		Msg("cancel_order_received")

	if err := s.broker.CancelOrder(ctx, req.GetOrderId()); err != nil {
		s.log.Error().Err(err).Str("order_id", req.GetOrderId()).Msg("cancel_order_failed")
		return &executionv1.CancelOrderResponse{
			Success: false,
			Status:  "NOT_FOUND",
			TraceId: traceID,
		}, nil
	}

	s.audit.LogOrderCancelled(ctx, req.GetOrderId(), req.GetSymbol(), req.GetReason(), traceID)

	s.transport.Publish(ctx, alert.NewEvent(alert.SourceExecution, alert.TypeOrderCancelled, alert.SeverityInfo,
		fmt.Sprintf("Order %s cancelled: %s", req.GetOrderId(), req.GetReason())).
		WithUserID(userID).WithSymbol(req.GetSymbol()).WithTraceID(traceID).
		WithDetails(map[string]interface{}{
			"order_id": req.GetOrderId(),
			"reason":   req.GetReason(),
		}))

	return &executionv1.CancelOrderResponse{
		Success: true,
		Status:  "CANCELLED",
		TraceId: traceID,
	}, nil
}

// GetExecutionState returns current positions, pending orders, and P&L.
func (s *ExecutionServer) GetExecutionState(ctx context.Context, req *executionv1.GetStateRequest) (*executionv1.GetStateResponse, error) {
	userID := auth.UserIDFromContext(ctx)
	if userID == "" {
		return nil, status.Errorf(codes.Unauthenticated, "user_id not found in context")
	}

	// Refresh auth tokens on active watchers for this user.
	if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
		s.watcher.RefreshUserOrderTokens(userID, rawToken)
	}

	if err := s.state.Refresh(ctx, userID); err != nil {
		s.log.Error().Err(err).Msg("get_state_refresh_failed")
		return nil, status.Errorf(codes.Unavailable, "broker state refresh failed")
	}

	positions := s.state.Positions(userID)
	pending := s.state.PendingOrders(userID)
	account := s.state.Account(userID)

	var balance, equity float64
	if account != nil {
		balance = account.Balance
		equity = account.Equity
	}

	protoPositions := make([]*executionv1.OpenPosition, 0, len(positions))
	for _, p := range positions {
		protoPositions = append(protoPositions, &executionv1.OpenPosition{
			Symbol:        p.Symbol,
			Direction:     p.Direction,
			EntryPrice:    p.EntryPrice,
			CurrentPrice:  p.CurrentPrice,
			StopLoss:      p.StopLoss,
			LotSize:       p.LotSize,
			UnrealizedPnl: p.UnrealizedPnL,
			OrderId:       p.OrderID,
			AnalysisId:    p.AnalysisID,
			TradingStyle:  p.TradingStyle,
		})
	}

	protoPending := make([]*executionv1.PendingOrder, 0, len(pending))
	for _, p := range pending {
		protoPending = append(protoPending, &executionv1.PendingOrder{
			Symbol:        p.Symbol,
			Direction:     p.Direction,
			EntryPrice:    p.EntryPrice,
			StopLoss:      p.StopLoss,
			LotSize:       p.LotSize,
			OrderId:       p.OrderID,
			AnalysisId:    p.AnalysisID,
			ExecutionMode: p.ExecutionMode,
			Status:        p.Status,
		})
	}

	return &executionv1.GetStateResponse{
		OpenPositionCount: int32(len(positions)),
		PendingOrderCount: int32(len(pending)),
		DailyRealizedPnl:  s.state.DailyPnL(userID),
		WeeklyRealizedPnl: s.state.WeeklyPnL(userID),
		AccountBalance:    balance,
		AccountEquity:     equity,
		OpenPositions:     protoPositions,
		PendingOrders:     protoPending,
		TraceId:           req.GetTraceId(),
	}, nil
}

// incomingIdempotencyKey reads the x-idempotency-key value from inbound
// gRPC metadata, or "" when absent.
func incomingIdempotencyKey(ctx context.Context) string {
	md, ok := metadata.FromIncomingContext(ctx)
	if !ok {
		return ""
	}
	vals := md.Get("x-idempotency-key")
	if len(vals) == 0 {
		return ""
	}
	return strings.TrimSpace(vals[0])
}

func validateRequest(req *executionv1.ExecuteTradeRequest) error {
	if strings.TrimSpace(req.GetSymbol()) == "" {
		return fmt.Errorf("symbol is required")
	}
	d := strings.ToUpper(req.GetDirection())
	if d != "LONG" && d != "SHORT" {
		return fmt.Errorf("direction must be LONG or SHORT, got %q", req.GetDirection())
	}
	if req.GetEntryZoneLow() <= 0 || req.GetEntryZoneHigh() <= 0 {
		return fmt.Errorf("entry_zone_low and entry_zone_high must be positive")
	}
	if req.GetEntryZoneLow() > req.GetEntryZoneHigh() {
		return fmt.Errorf("entry_zone_low must be <= entry_zone_high")
	}
	if req.GetStopLoss() <= 0 {
		return fmt.Errorf("stop_loss must be positive")
	}
	if req.GetRiskPercentage() <= 0 || req.GetRiskPercentage() > 5.0 {
		return fmt.Errorf("risk_percentage must be 0..5, got %.2f", req.GetRiskPercentage())
	}
	if req.GetRrRatio() <= 0 {
		return fmt.Errorf("rr_ratio must be positive")
	}
	return nil
}

func parseRequest(req *executionv1.ExecuteTradeRequest) *models.TradeRequest {
	return &models.TradeRequest{
		Symbol:          req.GetSymbol(),
		Direction:       constants.Direction(strings.ToUpper(req.GetDirection())),
		EntryZoneLow:    req.GetEntryZoneLow(),
		EntryZoneHigh:   req.GetEntryZoneHigh(),
		StopLoss:        req.GetStopLoss(),
		TP1Price:        req.GetTp1Price(),
		TP1Pct:          req.GetTp1Pct(),
		TP2Price:        req.GetTp2Price(),
		TP2Pct:          req.GetTp2Pct(),
		TP3Price:        req.GetTp3Price(),
		TP3Pct:          req.GetTp3Pct(),
		RRRatio:         req.GetRrRatio(),
		Grade:           req.GetGrade(),
		RiskPercentage:  req.GetRiskPercentage(),
		TradingStyle:    constants.TradingStyle(strings.ToUpper(req.GetTradingStyle())),
		Session:         strings.ToUpper(req.GetSession()),
		ConfluenceScore: req.GetConfluenceScore(),
		Confidence:      req.GetConfidence(),
		AnalysisID:      req.GetAnalysisId(),
		TraceID:         req.GetTraceId(),
		ExecutionMode:   req.GetExecutionMode(),
		LTFConfirmed:    req.GetLtfConfirmed(),
		SetupType:       req.GetSetupType(),
		OBUpper:         req.GetObUpper(),
		OBLower:         req.GetObLower(),
		LTFTimeframe:    req.GetLtfTimeframe(),
		HTFTimeframe:    req.GetHtfTimeframe(),
	}
}

func rejectedResponse(req *models.TradeRequest, reason string, check int32, traceID string) *executionv1.ExecuteTradeResponse {
	return &executionv1.ExecuteTradeResponse{
		Accepted:        false,
		Status:          string(constants.StatusRejected),
		RejectionReason: reason,
		RejectionCheck:  check,
		AnalysisId:      req.AnalysisID,
		TraceId:         traceID,
	}
}

func outcomeToStatus(outcome constants.ValidationOutcome) constants.OrderStatus {
	switch outcome {
	case constants.OutcomeReject:
		return constants.StatusRejected
	case constants.OutcomeQueue:
		return constants.StatusQueued
	case constants.OutcomeLock:
		return constants.StatusLocked
	case constants.OutcomePause:
		return constants.StatusPaused
	default:
		return constants.StatusRejected
	}
}
