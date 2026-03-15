package executor

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/execution/internal/broker"
	"github.com/flamegreat/etradie/src/execution/internal/constants"
	"github.com/flamegreat/etradie/src/execution/internal/models"
	"github.com/flamegreat/etradie/src/execution/internal/observability"
)

// Executor dispatches orders to the broker (limit) or arms Module C
// watchers (instant). Single responsibility: order placement.
type Executor struct {
	broker    broker.Port
	timeoutMs int
	log       zerolog.Logger
}

// NewExecutor creates an order executor.
func NewExecutor(bp broker.Port, brokerTimeoutMs int) *Executor {
	return &Executor{
		broker:    bp,
		timeoutMs: brokerTimeoutMs,
		log:       observability.Logger("executor"),
	}
}

// Execute places the order based on execution mode.
func (e *Executor) Execute(ctx context.Context, order *models.Order) (*models.ExecutionResult, error) {
	switch order.ExecutionMode {
	case constants.ModeLimit:
		return e.placeLimit(ctx, order)
	case constants.ModeInstant:
		return e.armInstant(ctx, order)
	default:
		return nil, fmt.Errorf("executor: unknown execution mode %q", order.ExecutionMode)
	}
}

func (e *Executor) placeLimit(ctx context.Context, order *models.Order) (*models.ExecutionResult, error) {
	start := time.Now()

	brokerCtx, cancel := context.WithTimeout(ctx, time.Duration(e.timeoutMs)*time.Millisecond)
	defer cancel()

	placement := &models.OrderPlacement{
		Symbol:     order.Symbol,
		Direction:  constants.BrokerDirection(order.Direction),
		OrderType:  string(constants.BrokerOrderLimit),
		Price:      order.EntryPrice,
		StopLoss:   order.StopLoss,
		TakeProfit: order.TP1Price,
		LotSize:    order.LotSize,
		Comment:    order.AnalysisID,
	}

	result, err := e.broker.PlaceLimitOrder(brokerCtx, placement)

	elapsed := time.Since(start).Seconds()
	observability.OrderPlacementDuration.WithLabelValues("LIMIT").Observe(elapsed)

	if err != nil {
		observability.OrderPlacementTotal.WithLabelValues("LIMIT", "error").Inc()
		return nil, fmt.Errorf("executor: place limit order for %s: %w", order.Symbol, err)
	}

	if result.Status == "REJECTED" {
		observability.OrderPlacementTotal.WithLabelValues("LIMIT", "rejected").Inc()
		return &models.ExecutionResult{
			Accepted:        false,
			Status:          constants.StatusRejected,
			RejectionReason: fmt.Sprintf("broker rejected: %s", result.ErrorMessage),
			Order:           order,
		}, nil
	}

	observability.OrderPlacementTotal.WithLabelValues("LIMIT", "success").Inc()

	order.BrokerOrderID = result.BrokerOrderID

	e.log.Info().
		Str("symbol", order.Symbol).
		Str("direction", string(order.Direction)).
		Str("order_id", order.OrderID).
		Str("broker_order_id", result.BrokerOrderID).
		Float64("entry_price", order.EntryPrice).
		Float64("stop_loss", order.StopLoss).
		Float64("lot_size", order.LotSize).
		Int("ttl_candles", order.TTLCandles).
		Str("analysis_id", order.AnalysisID).
		Float64("duration_ms", elapsed*1000).
		Msg("limit_order_placed")

	return &models.ExecutionResult{
		Accepted: true,
		Status:   constants.StatusPending,
		OrderID:  order.OrderID,
		Order:    order,
	}, nil
}

// armInstant records the watcher as armed and returns the watcher ID.
// Module C is responsible for watching ticks and firing the market
// order when price touches the entry level. The arming handoff to
// Module C happens via gRPC (Module C's responsibility to implement
// the ArmWatcher RPC). Module B's job ends at recording the intent.
func (e *Executor) armInstant(_ context.Context, order *models.Order) (*models.ExecutionResult, error) {
	start := time.Now()

	elapsed := time.Since(start).Seconds()
	observability.OrderPlacementDuration.WithLabelValues("INSTANT").Observe(elapsed)
	observability.OrderPlacementTotal.WithLabelValues("INSTANT", "success").Inc()

	e.log.Info().
		Str("symbol", order.Symbol).
		Str("direction", string(order.Direction)).
		Str("order_id", order.OrderID).
		Str("watcher_id", order.WatcherID).
		Float64("watch_level", order.EntryPrice).
		Float64("overshoot_tolerance", order.OvershootTolerance).
		Float64("stop_loss", order.StopLoss).
		Float64("lot_size", order.LotSize).
		Str("analysis_id", order.AnalysisID).
		Float64("duration_ms", elapsed*1000).
		Msg("watcher_armed")

	return &models.ExecutionResult{
		Accepted: true,
		Status:   constants.StatusWatching,
		OrderID:  order.WatcherID,
		Order:    order,
	}, nil
}
