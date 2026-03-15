package server

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/rs/zerolog"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	executionv1 "github.com/flamegreat/etradie/proto/execution/v1"
	"github.com/flamegreat/etradie/src/execution/internal/audit"
	"github.com/flamegreat/etradie/src/execution/internal/broker"
	"github.com/flamegreat/etradie/src/execution/internal/builder"
	"github.com/flamegreat/etradie/src/execution/internal/config"
	"github.com/flamegreat/etradie/src/execution/internal/constants"
	"github.com/flamegreat/etradie/src/execution/internal/executor"
	"github.com/flamegreat/etradie/src/execution/internal/models"
	"github.com/flamegreat/etradie/src/execution/internal/notify"
	"github.com/flamegreat/etradie/src/execution/internal/observability"
	"github.com/flamegreat/etradie/src/execution/internal/sizing"
	"github.com/flamegreat/etradie/src/execution/internal/state"
	"github.com/flamegreat/etradie/src/execution/internal/validator"
)

const (
	idempotencyTTL      = 1 * time.Hour
	idempotencyMaxSize  = 10000
	idempotencyCleanup  = 5 * time.Minute
)

type idempotencyEntry struct {
	expiresAt time.Time
}

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
	notifier  *notify.Notifier
	log       zerolog.Logger

	processedMu sync.RWMutex
	processed   map[string]idempotencyEntry
	stopCleanup chan struct{}
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
	n *notify.Notifier,
) *ExecutionServer {
	srv := &ExecutionServer{
		cfg:         cfg,
		validator:   v,
		sizer:       s,
		executor:    e,
		state:       sm,
		broker:      bp,
		audit:       al,
		notifier:    n,
		log:         observability.Logger("grpc_server"),
		processed:   make(map[string]idempotencyEntry),
		stopCleanup: make(chan struct{}),
	}
	go srv.cleanupLoop()
	return srv
}

// cleanupLoop periodically evicts expired idempotency entries.
func (s *ExecutionServer) cleanupLoop() {
	ticker := time.NewTicker(idempotencyCleanup)
	defer ticker.Stop()
	for {
		select {
		case <-ticker.C:
			s.evictExpired()
		case <-s.stopCleanup:
			return
		}
	}
}

func (s *ExecutionServer) evictExpired() {
	now := time.Now()
	s.processedMu.Lock()
	for k, v := range s.processed {
		if now.After(v.expiresAt) {
			delete(s.processed, k)
		}
	}
	s.processedMu.Unlock()
}

func (s *ExecutionServer) markProcessed(analysisID string) {
	s.processedMu.Lock()
	// If at capacity, evict expired first; if still full, skip tracking.
	if len(s.processed) >= idempotencyMaxSize {
		now := time.Now()
		for k, v := range s.processed {
			if now.After(v.expiresAt) {
				delete(s.processed, k)
			}
		}
	}
	s.processed[analysisID] = idempotencyEntry{
		expiresAt: time.Now().Add(idempotencyTTL),
	}
	s.processedMu.Unlock()
}

func (s *ExecutionServer) isDuplicate(analysisID string) bool {
	s.processedMu.RLock()
	entry, exists := s.processed[analysisID]
	s.processedMu.RUnlock()
	if !exists {
		return false
	}
	return time.Now().Before(entry.expiresAt)
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
	if analysisID != "" && s.isDuplicate(analysisID) {
		s.log.Warn().Str("analysis_id", analysisID).Str("trace_id", traceID).Msg("duplicate_analysis_id")
		return &executionv1.ExecuteTradeResponse{
			Accepted:        false,
			Status:          string(constants.StatusRejected),
			RejectionReason: "duplicate analysis_id: already processed",
			AnalysisId:      analysisID,
			TraceId:         traceID,
		}, nil
	}

	s.log.Info().
		Str("symbol", req.GetSymbol()).
		Str("direction", req.GetDirection()).
		Str("grade", req.GetGrade()).
		Str("analysis_id", analysisID).
		Str("trace_id", traceID).
		Msg("execute_trade_received")

	tradeReq := parseRequest(req)

	if err := s.state.Refresh(ctx); err != nil {
		s.log.Error().Err(err).Str("trace_id", traceID).Msg("state_refresh_failed")
		s.notifier.NotifyError(req.GetSymbol(), "Failed to refresh broker state")
		return rejectedResponse(tradeReq, "broker state refresh failed: "+err.Error(), 0, traceID), nil
	}

	valResult := s.validator.Validate(ctx, tradeReq)
	if !valResult.Passed {
		s.audit.LogValidationRejected(ctx, tradeReq, valResult)
		s.notifier.NotifyRejected(tradeReq, valResult)

		if valResult.Outcome == constants.OutcomeLock {
			s.notifier.NotifyDailyLocked(s.state.DailyLossPercent())
		}
		if valResult.Outcome == constants.OutcomePause {
			s.notifier.NotifyWeeklyPaused(s.state.WeeklyDrawdownPercent())
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

	sizingResult, err := s.sizer.Calculate(ctx, tradeReq)
	if err != nil {
		s.log.Error().Err(err).Str("symbol", tradeReq.Symbol).Str("trace_id", traceID).Msg("sizing_failed")
		s.notifier.NotifyError(tradeReq.Symbol, "Position sizing failed: "+err.Error())

		elapsed := time.Since(start).Seconds()
		observability.ExecutionDuration.Observe(elapsed)
		observability.ExecutionTotal.WithLabelValues(req.GetSymbol(), req.GetDirection(), "sizing_error").Inc()

		return rejectedResponse(tradeReq, "sizing failed: "+err.Error(), 0, traceID), nil
	}

	s.audit.LogLotSizeCalculated(ctx, tradeReq, sizingResult)

	order := builder.Build(tradeReq, sizingResult, s.cfg)

	execResult, err := s.executor.Execute(ctx, order)
	if err != nil {
		s.log.Error().Err(err).Str("symbol", order.Symbol).Str("trace_id", traceID).Msg("execution_failed")
		s.notifier.NotifyError(order.Symbol, "Order execution failed: "+err.Error())

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

	s.audit.LogOrderPlaced(ctx, order)
	s.notifier.NotifyOrderPlaced(order)

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

	return &executionv1.CancelOrderResponse{
		Success: true,
		Status:  "CANCELLED",
		TraceId: traceID,
	}, nil
}

// GetExecutionState returns current positions, pending orders, and P&L.
func (s *ExecutionServer) GetExecutionState(ctx context.Context, req *executionv1.GetStateRequest) (*executionv1.GetStateResponse, error) {
	if err := s.state.Refresh(ctx); err != nil {
		s.log.Error().Err(err).Msg("get_state_refresh_failed")
		return nil, status.Errorf(codes.Unavailable, "broker state refresh failed")
	}

	positions := s.state.Positions()
	pending := s.state.PendingOrders()
	account := s.state.Account()

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
		DailyRealizedPnl:  s.state.DailyPnL(),
		WeeklyRealizedPnl: s.state.WeeklyPnL(),
		AccountBalance:    balance,
		AccountEquity:     equity,
		OpenPositions:     protoPositions,
		PendingOrders:     protoPending,
		TraceId:           req.GetTraceId(),
	}, nil
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
