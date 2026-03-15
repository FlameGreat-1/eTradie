package server

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

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

// ExecutionServer implements the ExecutionService gRPC server.
type ExecutionServer struct {
	cfg       *config.Config
	validator *validator.Validator
	sizer     *sizing.Engine
	executor  *executor.Executor
	state     *state.Manager
	broker    broker.Port
	audit     *audit.Logger
	notifier  *notify.Notifier
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
	n *notify.Notifier,
) *ExecutionServer {
	return &ExecutionServer{
		cfg:       cfg,
		validator: v,
		sizer:     s,
		executor:  e,
		state:     sm,
		broker:    bp,
		audit:     al,
		notifier:  n,
		log:       observability.Logger("grpc_server"),
	}
}

// ExecuteTrade is the main RPC. Orchestrates the full Module B pipeline.
func (s *ExecutionServer) ExecuteTrade(ctx context.Context, req *ExecuteTradeRequest) (resp *ExecuteTradeResponse, err error) {
	defer func() {
		if r := recover(); r != nil {
			s.log.Error().Interface("panic", r).Str("trace_id", req.GetTraceId()).Msg("execute_trade_panic")
			err = status.Errorf(codes.Internal, "internal error")
			resp = nil
		}
	}()

	start := time.Now()
	traceID := req.GetTraceId()

	s.log.Info().
		Str("symbol", req.GetSymbol()).
		Str("direction", req.GetDirection()).
		Str("grade", req.GetGrade()).
		Str("analysis_id", req.GetAnalysisId()).
		Str("trace_id", traceID).
		Msg("execute_trade_received")

	// Step 1: Parse request.
	tradeReq := parseRequest(req)

	// Step 2: Refresh state from broker.
	if err := s.state.Refresh(ctx); err != nil {
		s.log.Error().Err(err).Str("trace_id", traceID).Msg("state_refresh_failed")
		s.notifier.NotifyError(req.GetSymbol(), "Failed to refresh broker state")
		return rejectedResponse(tradeReq, "broker state refresh failed: "+err.Error(), 0, traceID), nil
	}

	// Step 3: Validate.
	valResult := s.validator.Validate(tradeReq)
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

		return &ExecuteTradeResponse{
			Accepted:        false,
			Status:          string(outcomeToStatus(valResult.Outcome)),
			RejectionReason: valResult.Reason,
			RejectionCheck:  int32(valResult.FailedCheck),
			AnalysisId:      tradeReq.AnalysisID,
			TraceId:         traceID,
		}, nil
	}

	s.audit.LogValidationPassed(ctx, tradeReq)

	// Step 4: Calculate position size.
	sizingResult, err := s.sizer.Calculate(ctx, tradeReq)
	if err != nil {
		s.log.Error().Err(err).Str("symbol", tradeReq.Symbol).Str("trace_id", traceID).Msg("sizing_failed")
		s.notifier.NotifyError(tradeReq.Symbol, "Position sizing failed: "+err.Error())

		elapsed := time.Since(start).Seconds()
		observability.ExecutionDuration.Observe(elapsed)
		observability.ExecutionTotal.WithLabelValues(req.GetSymbol(), req.GetDirection(), "sizing_error").Inc()

		return rejectedResponse(tradeReq, "sizing failed: "+err.Error(), 0, traceID), nil
	}

	// Step 5: Build order.
	order := builder.Build(tradeReq, sizingResult, s.cfg)

	// Step 6: Execute.
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

		return &ExecuteTradeResponse{
			Accepted:        false,
			Status:          string(execResult.Status),
			RejectionReason: execResult.RejectionReason,
			AnalysisId:      tradeReq.AnalysisID,
			TraceId:         traceID,
		}, nil
	}

	// Step 7: Audit + notify.
	s.audit.LogOrderPlaced(ctx, order)
	s.notifier.NotifyOrderPlaced(order)

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

	return &ExecuteTradeResponse{
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
func (s *ExecutionServer) CancelPendingOrder(ctx context.Context, req *CancelOrderRequest) (*CancelOrderResponse, error) {
	traceID := req.GetTraceId()

	s.log.Info().
		Str("order_id", req.GetOrderId()).
		Str("symbol", req.GetSymbol()).
		Str("reason", req.GetReason()).
		Str("trace_id", traceID).
		Msg("cancel_order_received")

	if err := s.broker.CancelOrder(ctx, req.GetOrderId()); err != nil {
		s.log.Error().Err(err).Str("order_id", req.GetOrderId()).Msg("cancel_order_failed")
		return &CancelOrderResponse{
			Success: false,
			Status:  "NOT_FOUND",
			TraceId: traceID,
		}, nil
	}

	s.audit.LogOrderCancelled(ctx, req.GetOrderId(), req.GetSymbol(), req.GetReason(), traceID)

	return &CancelOrderResponse{
		Success: true,
		Status:  "CANCELLED",
		TraceId: traceID,
	}, nil
}

// GetExecutionState returns current positions, pending orders, and P&L.
func (s *ExecutionServer) GetExecutionState(ctx context.Context, req *GetStateRequest) (*GetStateResponse, error) {
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

	protoPositions := make([]*OpenPosition, 0, len(positions))
	for _, p := range positions {
		protoPositions = append(protoPositions, &OpenPosition{
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

	protoPending := make([]*PendingOrder, 0, len(pending))
	for _, p := range pending {
		protoPending = append(protoPending, &PendingOrder{
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

	return &GetStateResponse{
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

func parseRequest(req *ExecuteTradeRequest) *models.TradeRequest {
	return &models.TradeRequest{
		Symbol:          req.GetSymbol(),
		Direction:       constants.Direction(req.GetDirection()),
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
		TradingStyle:    constants.TradingStyle(req.GetTradingStyle()),
		Session:         req.GetSession(),
		ConfluenceScore: req.GetConfluenceScore(),
		Confidence:      req.GetConfidence(),
		AnalysisID:      req.GetAnalysisId(),
		TraceID:         req.GetTraceId(),
	}
}

func rejectedResponse(req *models.TradeRequest, reason string, check int32, traceID string) *ExecuteTradeResponse {
	return &ExecuteTradeResponse{
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

// Proto message types referenced in this file. These are temporary
// type aliases until proto generation is wired. They mirror the
// proto/execution/v1/execution.proto message definitions exactly.
type ExecuteTradeRequest struct {
	Symbol          string
	Direction       string
	EntryZoneLow    float64
	EntryZoneHigh   float64
	StopLoss        float64
	Tp1Price        float64
	Tp1Pct          int32
	Tp2Price        float64
	Tp2Pct          int32
	Tp3Price        float64
	Tp3Pct          int32
	RrRatio         float64
	Grade           string
	RiskPercentage  float64
	TradingStyle    string
	Session         string
	ConfluenceScore float64
	Confidence      float64
	AnalysisId      string
	TraceId         string
}

func (r *ExecuteTradeRequest) GetSymbol() string          { return r.Symbol }
func (r *ExecuteTradeRequest) GetDirection() string        { return r.Direction }
func (r *ExecuteTradeRequest) GetEntryZoneLow() float64    { return r.EntryZoneLow }
func (r *ExecuteTradeRequest) GetEntryZoneHigh() float64   { return r.EntryZoneHigh }
func (r *ExecuteTradeRequest) GetStopLoss() float64        { return r.StopLoss }
func (r *ExecuteTradeRequest) GetTp1Price() float64        { return r.Tp1Price }
func (r *ExecuteTradeRequest) GetTp1Pct() int32            { return r.Tp1Pct }
func (r *ExecuteTradeRequest) GetTp2Price() float64        { return r.Tp2Price }
func (r *ExecuteTradeRequest) GetTp2Pct() int32            { return r.Tp2Pct }
func (r *ExecuteTradeRequest) GetTp3Price() float64        { return r.Tp3Price }
func (r *ExecuteTradeRequest) GetTp3Pct() int32            { return r.Tp3Pct }
func (r *ExecuteTradeRequest) GetRrRatio() float64         { return r.RrRatio }
func (r *ExecuteTradeRequest) GetGrade() string            { return r.Grade }
func (r *ExecuteTradeRequest) GetRiskPercentage() float64  { return r.RiskPercentage }
func (r *ExecuteTradeRequest) GetTradingStyle() string     { return r.TradingStyle }
func (r *ExecuteTradeRequest) GetSession() string          { return r.Session }
func (r *ExecuteTradeRequest) GetConfluenceScore() float64 { return r.ConfluenceScore }
func (r *ExecuteTradeRequest) GetConfidence() float64      { return r.Confidence }
func (r *ExecuteTradeRequest) GetAnalysisId() string       { return r.AnalysisId }
func (r *ExecuteTradeRequest) GetTraceId() string          { return r.TraceId }

type ExecuteTradeResponse struct {
	Accepted        bool
	Status          string
	OrderId         string
	RejectionReason string
	RejectionCheck  int32
	LotSize         float64
	RiskAmount      float64
	AccountBalance  float64
	SlDistancePips  float64
	PipValue        float64
	ExecutionMode   string
	EntryPrice      float64
	AnalysisId      string
	TraceId         string
}

type CancelOrderRequest struct {
	OrderId string
	Symbol  string
	Reason  string
	TraceId string
}

func (r *CancelOrderRequest) GetOrderId() string { return r.OrderId }
func (r *CancelOrderRequest) GetSymbol() string  { return r.Symbol }
func (r *CancelOrderRequest) GetReason() string  { return r.Reason }
func (r *CancelOrderRequest) GetTraceId() string { return r.TraceId }

type CancelOrderResponse struct {
	Success bool
	Status  string
	TraceId string
}

type GetStateRequest struct {
	TraceId string
}

func (r *GetStateRequest) GetTraceId() string { return r.TraceId }

type GetStateResponse struct {
	OpenPositionCount int32
	PendingOrderCount int32
	DailyRealizedPnl  float64
	WeeklyRealizedPnl float64
	AccountBalance    float64
	AccountEquity     float64
	OpenPositions     []*OpenPosition
	PendingOrders     []*PendingOrder
	TraceId           string
}

type OpenPosition struct {
	Symbol        string
	Direction     string
	EntryPrice    float64
	CurrentPrice  float64
	StopLoss      float64
	LotSize       float64
	UnrealizedPnl float64
	OrderId       string
	AnalysisId    string
	TradingStyle  string
}

type PendingOrder struct {
	Symbol        string
	Direction     string
	EntryPrice    float64
	StopLoss      float64
	LotSize       float64
	OrderId       string
	AnalysisId    string
	ExecutionMode string
	Status        string
}
