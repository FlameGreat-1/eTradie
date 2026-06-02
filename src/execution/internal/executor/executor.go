package executor

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
	"github.com/flamegreat-1/etradie/src/execution/internal/constants"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
	"github.com/flamegreat-1/etradie/src/execution/internal/store"
	"github.com/flamegreat-1/etradie/src/execution/internal/watcher"
)

// Executor dispatches orders to the broker (limit) or arms watchers
// (instant) via the WatcherManager. Single responsibility: order dispatch.
//
// Section 3 (CHECKLIST):
//   - Idempotency: every placement claims a (user_id, idempotency_key)
//     row before the broker call. Duplicate submissions short-circuit.
//   - Latency budget: the executor refuses an order whose end-to-end
//     duration exceeds MaxOrderLatencyMs even if the broker accepted
//     it (best-effort CancelOrder fires).
type Executor struct {
	broker            broker.Port
	watcher           *watcher.Manager
	idempotency       *store.IdempotencyStore
	timeoutMs         int
	maxOrderLatencyMs int
	log               zerolog.Logger
}

// NewExecutor creates an order executor. The WatcherManager handles
// all instant-mode monitoring, confirmation, and market order firing.
//
// idempotency may be nil (development / test) in which case the
// idempotency contract is skipped and Section 3 protection is OFF.
// Production wires a real *store.IdempotencyStore.
//
// maxOrderLatencyMs <= 0 disables the latency kill-switch.
func NewExecutor(
	bp broker.Port,
	wm *watcher.Manager,
	idempotency *store.IdempotencyStore,
	brokerTimeoutMs, maxOrderLatencyMs int,
) *Executor {
	return &Executor{
		broker:            bp,
		watcher:           wm,
		idempotency:       idempotency,
		timeoutMs:         brokerTimeoutMs,
		maxOrderLatencyMs: maxOrderLatencyMs,
		log:               observability.Logger("executor"),
	}
}

// Execute places the order based on execution mode.
func (e *Executor) Execute(ctx context.Context, order *models.Order) (*models.ExecutionResult, error) {
	switch order.ExecutionMode {
	case constants.ModeLimit:
		return e.placeLimit(ctx, order)
	case constants.ModeInstant:
		return e.handleInstant(ctx, order)
	default:
		return nil, fmt.Errorf("executor: unknown execution mode %q", order.ExecutionMode)
	}
}

// idempotencyKeyFor returns the gateway-supplied key, or the order ID
// as a fallback for direct callers that omit it.
func idempotencyKeyFor(order *models.Order) string {
	if order.IdempotencyKey != "" {
		return order.IdempotencyKey
	}
	return order.OrderID
}

func (e *Executor) placeLimit(ctx context.Context, order *models.Order) (*models.ExecutionResult, error) {
	start := time.Now()

	idemKey := idempotencyKeyFor(order)
	if e.idempotency != nil {
		claim, err := e.idempotency.TryClaim(ctx, &store.IdempotencyRecord{
			UserID:         order.UserID,
			IdempotencyKey: idemKey,
			OrderID:        order.OrderID,
			Symbol:         order.Symbol,
			Direction:      string(order.Direction),
			ExecutionMode:  string(order.ExecutionMode),
			EntryPrice:     order.EntryPrice,
			StopLoss:       order.StopLoss,
			LotSize:        order.LotSize,
		})
		if err != nil {
			// A store failure must not block trading; fall through to a
			// non-idempotent placement, latency + broker guards still apply.
			e.log.Warn().Err(err).Str("order_id", order.OrderID).Msg("idempotency_claim_failed_falling_through")
		} else if !claim.FirstClaim && claim.Existing != nil {
			ex := claim.Existing
			e.log.Info().
				Str("order_id", order.OrderID).
				Str("idempotency_key", idemKey).
				Str("existing_broker_order_id", ex.BrokerOrderID).
				Str("existing_status", ex.Status).
				Msg("duplicate_order_short_circuit")
			order.BrokerOrderID = ex.BrokerOrderID
			return &models.ExecutionResult{
				Accepted:        true,
				Status:          constants.StatusDuplicate,
				RejectionReason: "duplicate idempotency key; returning prior placement",
				OrderID:         order.OrderID,
				Order:           order,
			}, nil
		}
	}

	brokerCtx, cancel := context.WithTimeout(ctx, time.Duration(e.timeoutMs)*time.Millisecond)
	defer cancel()

	placement := &models.OrderPlacement{
		Symbol:    order.Symbol,
		Direction: constants.BrokerDirection(order.Direction),
		OrderType: string(constants.BrokerOrderLimit),
		Price:     order.EntryPrice,
		StopLoss:  order.StopLoss,
		// Attach the FINAL target (TP3) to the broker, not TP1: a
		// position-level TP closes the whole position, so the broker TP
		// must sit beyond the software TP1/TP2 partials (CRITICAL).
		TakeProfit: order.BrokerTakeProfit(),
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

	// ---- Section 3: latency kill-switch ----
	if e.maxOrderLatencyMs > 0 && time.Since(start) > time.Duration(e.maxOrderLatencyMs)*time.Millisecond {
		observability.OrderLatencyBreachTotal.Inc()
		observability.OrderPlacementTotal.WithLabelValues("LIMIT", "latency_breach").Inc()
		if result.BrokerOrderID != "" {
			// Best-effort cancel so the slow-but-accepted order does
			// not linger as a real exposure on the broker.
			cancelCtx, cancelCancel := context.WithTimeout(
				context.Background(),
				time.Duration(e.timeoutMs)*time.Millisecond,
			)
			if cerr := e.broker.CancelOrder(cancelCtx, result.BrokerOrderID); cerr != nil {
				e.log.Error().Err(cerr).
					Str("broker_order_id", result.BrokerOrderID).
					Str("symbol", order.Symbol).
					Msg("latency_breach_cancel_failed")
			}
			cancelCancel()
		}
		return &models.ExecutionResult{
			Accepted:        false,
			Status:          constants.StatusRejected,
			RejectionReason: fmt.Sprintf("latency_budget_exceeded: %.0fms > %dms", elapsed*1000, e.maxOrderLatencyMs),
			Order:           order,
		}, nil
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

	// Section 3: partial-fill detection.
	status := constants.StatusPending
	if result.Status == "PARTIALLY_FILLED" {
		status = constants.StatusPartiallyFilled
		observability.PartialFillTotal.WithLabelValues(order.Symbol, string(order.Direction)).Inc()
	}

	observability.OrderPlacementTotal.WithLabelValues("LIMIT", "success").Inc()

	order.BrokerOrderID = result.BrokerOrderID

	// Persist the broker outcome to the idempotency row so duplicate
	// submissions surface the actual fill state, not just "CLAIMED".
	if e.idempotency != nil {
		if rerr := e.idempotency.RecordResult(
			context.Background(),
			order.UserID,
			idemKey,
			result.BrokerOrderID,
			string(status),
			result.FillPrice,
			result.VolumeFilled,
			result.VolumeRemaining,
		); rerr != nil {
			e.log.Warn().Err(rerr).Str("order_id", order.OrderID).Msg("idempotency_record_result_failed")
		}
	}

	// Arm the watcher for TTL enforcement. The watcher will monitor
	// the timeout and cancel the broker order if it expires unfilled.
	e.watcher.Arm(order)

	e.log.Info().
		Str("symbol", order.Symbol).
		Str("direction", string(order.Direction)).
		Str("order_id", order.OrderID).
		Str("broker_order_id", result.BrokerOrderID).
		Str("watcher_id", order.WatcherID).
		Float64("entry_price", order.EntryPrice).
		Float64("stop_loss", order.StopLoss).
		Float64("lot_size", order.LotSize).
		Int("ttl_candles", order.TTLCandles).
		Str("analysis_id", order.AnalysisID).
		Float64("duration_ms", elapsed*1000).
		Msg("limit_order_placed")

	return &models.ExecutionResult{
		Accepted: true,
		Status:   status,
		OrderID:  order.OrderID,
		Order:    order,
	}, nil
}

// handleInstant arms the watcher manager to monitor the entry zone.
// The watcher autonomously polls tick prices, calls Gateway for LTF
// confirmation, and fires the market order when conditions are met.
//
// A duplicate submission must not arm a second watcher, since each
// watcher can independently fire a market order. The claim runs before
// arming and short-circuits duplicates.
func (e *Executor) handleInstant(ctx context.Context, order *models.Order) (*models.ExecutionResult, error) {
	start := time.Now()

	idemKey := idempotencyKeyFor(order)
	if e.idempotency != nil {
		claim, err := e.idempotency.TryClaim(ctx, &store.IdempotencyRecord{
			UserID:         order.UserID,
			IdempotencyKey: idemKey,
			OrderID:        order.OrderID,
			Symbol:         order.Symbol,
			Direction:      string(order.Direction),
			ExecutionMode:  string(order.ExecutionMode),
			EntryPrice:     order.EntryPrice,
			StopLoss:       order.StopLoss,
			LotSize:        order.LotSize,
		})
		if err != nil {
			e.log.Warn().Err(err).Str("order_id", order.OrderID).Msg("idempotency_claim_failed_falling_through")
		} else if !claim.FirstClaim && claim.Existing != nil {
			ex := claim.Existing
			e.log.Info().
				Str("order_id", order.OrderID).
				Str("idempotency_key", idemKey).
				Str("existing_order_id", ex.OrderID).
				Str("existing_status", ex.Status).
				Msg("duplicate_instant_order_short_circuit_not_arming")
			return &models.ExecutionResult{
				Accepted:        true,
				Status:          constants.StatusDuplicate,
				RejectionReason: "duplicate idempotency key; watcher already armed for prior submission",
				OrderID:         ex.OrderID,
				Order:           order,
			}, nil
		}
	}

	e.watcher.Arm(order)

	// Record WATCHING so a later duplicate sees a populated status. The
	// broker_order_id is filled in by the watcher on fill.
	if e.idempotency != nil {
		if rerr := e.idempotency.RecordResult(
			context.Background(),
			order.UserID,
			idemKey,
			order.BrokerOrderID,
			string(constants.StatusWatching),
			0, 0, 0,
		); rerr != nil {
			e.log.Warn().Err(rerr).Str("order_id", order.OrderID).Msg("idempotency_record_result_failed")
		}
	}

	elapsed := time.Since(start).Seconds()
	observability.OrderPlacementDuration.WithLabelValues("INSTANT").Observe(elapsed)

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
