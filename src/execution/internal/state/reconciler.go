package state

import (
	"context"
	"strings"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

// Reconciler periodically compares the broker's view of open
// positions + pending orders against the engine's view and surfaces
// drift to Prometheus + the audit log. Section 3 of CHECKLIST.
//
// Drift classes:
//   - broker_only: a position/order at the broker that the engine
//                  does NOT know about. Recovered by adopting the
//                  broker's view into engine state.
//   - engine_only: a position the engine tracks but the broker does
//                  NOT report. Logged for operator review; never
//                  silently deleted (a real position cannot vanish
//                  by itself, so the safe assumption is broker-side
//                  data lag, not engine-side bug).
//   - mismatch:    same ticket but different SL/TP/lot_size. Engine
//                  view is replaced with the broker's because the
//                  broker is the source of truth.
type Reconciler struct {
	broker   broker.Port
	state    *Manager
	interval time.Duration
	log      zerolog.Logger

	mu      sync.Mutex
	stopped bool
}

var (
	reconcileTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_reconcile_total",
		Help: "Reconciliation cycles by outcome",
	}, []string{"outcome"}) // outcome: ok | broker_error

	reconcileDrift = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_reconcile_drift_total",
		Help: "Drift observations by class",
	}, []string{"class"}) // class: broker_only_position | engine_only_position | mismatch | broker_only_pending

	reconcileDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "etradie_execution_reconcile_duration_seconds",
		Help:    "Reconciliation cycle duration",
		Buckets: []float64{0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0},
	})
)

// NewReconciler constructs a reconciler bound to the supplied broker
// port + state manager. interval <= 0 falls back to 60s.
func NewReconciler(bp broker.Port, st *Manager, interval time.Duration) *Reconciler {
	if interval <= 0 {
		interval = 60 * time.Second
	}
	return &Reconciler{
		broker:   bp,
		state:    st,
		interval: interval,
		log:      observability.Logger("reconciler"),
	}
}

// Loop runs the reconciler until ctx is cancelled. Each cycle is
// bounded by a 30s internal timeout so a hung broker cannot block
// the next tick.
func (r *Reconciler) Loop(ctx context.Context) {
	ticker := time.NewTicker(r.interval)
	defer ticker.Stop()
	r.runOnce(ctx) // first cycle immediate
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			r.runOnce(ctx)
		}
	}
}

func (r *Reconciler) runOnce(parent context.Context) {
	start := time.Now()
	defer func() {
		reconcileDuration.Observe(time.Since(start).Seconds())
	}()

	ctx, cancel := context.WithTimeout(parent, 30*time.Second)
	defer cancel()

	brokerPositions, err := r.broker.GetPositions(ctx)
	if err != nil {
		r.log.Warn().Err(err).Msg("reconcile_broker_positions_failed")
		reconcileTotal.WithLabelValues("broker_error").Inc()
		return
	}
	brokerPending, err := r.broker.GetPendingOrders(ctx)
	if err != nil {
		r.log.Warn().Err(err).Msg("reconcile_broker_pending_failed")
		reconcileTotal.WithLabelValues("broker_error").Inc()
		return
	}

	r.reconcilePositions(brokerPositions)
	r.reconcilePending(brokerPending)

	reconcileTotal.WithLabelValues("ok").Inc()
	r.log.Debug().
		Int("broker_positions", len(brokerPositions)).
		Int("broker_pending", len(brokerPending)).
		Dur("duration", time.Since(start)).
		Msg("reconcile_cycle_complete")
}

func (r *Reconciler) reconcilePositions(brokerPositions []models.Position) {
	enginePositions := r.state.GetOpenPositions()

	// Build broker view by ticket.
	brokerByTicket := make(map[string]models.Position, len(brokerPositions))
	for _, p := range brokerPositions {
		brokerByTicket[p.OrderID] = p
	}

	// Build engine view by ticket.
	engineByTicket := make(map[string]*models.Order, len(enginePositions))
	for _, o := range enginePositions {
		if o.BrokerOrderID != "" {
			engineByTicket[o.BrokerOrderID] = o
		}
	}

	// broker_only: adopt into engine state.
	for ticket, bp := range brokerByTicket {
		if _, ok := engineByTicket[ticket]; ok {
			continue
		}
		reconcileDrift.WithLabelValues("broker_only_position").Inc()
		r.log.Warn().
			Str("broker_order_id", ticket).
			Str("symbol", bp.Symbol).
			Str("direction", bp.Direction).
			Float64("lot_size", bp.LotSize).
			Msg("reconcile_broker_only_position_adopting")
		r.state.AdoptBrokerPosition(&bp)
	}

	// engine_only: log but never silently delete.
	for ticket, o := range engineByTicket {
		if _, ok := brokerByTicket[ticket]; ok {
			continue
		}
		reconcileDrift.WithLabelValues("engine_only_position").Inc()
		r.log.Error().
			Str("broker_order_id", ticket).
			Str("symbol", o.Symbol).
			Str("direction", string(o.Direction)).
			Float64("lot_size", o.LotSize).
			Msg("reconcile_engine_only_position_review_required")
	}

	// mismatch: replace engine view with broker view.
	for ticket, bp := range brokerByTicket {
		o, ok := engineByTicket[ticket]
		if !ok {
			continue
		}
		if positionsDiffer(o, &bp) {
			reconcileDrift.WithLabelValues("mismatch").Inc()
			r.log.Warn().
				Str("broker_order_id", ticket).
				Str("symbol", o.Symbol).
				Float64("engine_lot", o.LotSize).
				Float64("broker_lot", bp.LotSize).
				Float64("engine_sl", o.StopLoss).
				Float64("broker_sl", bp.StopLoss).
				Float64("engine_tp", o.TP1Price).
				Float64("broker_tp", bp.TakeProfit).
				Msg("reconcile_mismatch_replacing_engine_view")
			r.state.ReplaceBrokerPosition(&bp)
		}
	}
}

func (r *Reconciler) reconcilePending(brokerPending []models.BrokerPendingOrder) {
	engineOrders := r.state.GetPendingOrders()

	engineByTicket := make(map[string]string, len(engineOrders))
	for _, o := range engineOrders {
		if o.BrokerOrderID != "" {
			engineByTicket[o.BrokerOrderID] = o.Symbol
		}
	}

	for _, bp := range brokerPending {
		if _, ok := engineByTicket[bp.OrderID]; !ok {
			reconcileDrift.WithLabelValues("broker_only_pending").Inc()
			r.log.Warn().
				Str("broker_order_id", bp.OrderID).
				Str("symbol", bp.Symbol).
				Str("direction", bp.Direction).
				Float64("price", bp.EntryPrice).
				Msg("reconcile_broker_only_pending_review_required")
		}
	}
}

func positionsDiffer(o *models.Order, bp *models.Position) bool {
	if !floatNear(o.LotSize, bp.LotSize) {
		return true
	}
	if !floatNear(o.StopLoss, bp.StopLoss) {
		return true
	}
	if !floatNear(o.TP1Price, bp.TakeProfit) {
		return true
	}
	if !strings.EqualFold(string(o.Direction), bp.Direction) &&
		!directionAlias(string(o.Direction), bp.Direction) {
		return true
	}
	return false
}

func directionAlias(engineDir, brokerDir string) bool {
	engine := strings.ToUpper(strings.TrimSpace(engineDir))
	bk := strings.ToUpper(strings.TrimSpace(brokerDir))
	if engine == "LONG" && bk == "BUY" {
		return true
	}
	if engine == "SHORT" && bk == "SELL" {
		return true
	}
	return false
}

func floatNear(a, b float64) bool {
	diff := a - b
	if diff < 0 {
		diff = -diff
	}
	return diff < 1e-6
}
