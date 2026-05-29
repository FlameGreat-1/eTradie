package state

import (
	"context"
	"strings"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

// IdentityProvider yields a per-user identity context for broker
// calls. The MT5 bridge resolves which broker to dial from
// X-User-Id (set via auth.InjectIdentity), so the reconciler MUST
// build a per-user context before invoking GetPositions /
// GetPendingOrders. Implementations typically wrap userStore +
// tokenService.
type IdentityProvider interface {
	IdentityContext(ctx context.Context, userID string) (context.Context, error)
}

// Reconciler periodically compares the broker's view of open
// positions + pending orders against the engine's view, per-user,
// and surfaces drift to Prometheus + the audit log.
// Section 3 of CHECKLIST.
type Reconciler struct {
	broker   broker.Port
	state    *Manager
	identity IdentityProvider
	interval time.Duration
	log      zerolog.Logger

	mu      sync.Mutex
	stopped bool
}

var (
	reconcileTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_reconcile_total",
		Help: "Reconciliation cycles by outcome",
	}, []string{"outcome"}) // outcome: ok | broker_error | identity_error

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

// NewReconciler constructs a reconciler. interval <= 0 falls back to 60s.
// identity is REQUIRED to drive per-user broker calls; a nil provider
// disables the reconciler (it logs once and Loop returns immediately).
func NewReconciler(
	bp broker.Port,
	st *Manager,
	identity IdentityProvider,
	interval time.Duration,
) *Reconciler {
	if interval <= 0 {
		interval = 60 * time.Second
	}
	return &Reconciler{
		broker:   bp,
		state:    st,
		identity: identity,
		interval: interval,
		log:      observability.Logger("reconciler"),
	}
}

// Loop runs the reconciler until ctx is cancelled.
func (r *Reconciler) Loop(ctx context.Context) {
	if r.identity == nil {
		r.log.Warn().Msg("reconciler_disabled_no_identity_provider")
		return
	}
	ticker := time.NewTicker(r.interval)
	defer ticker.Stop()
	r.runOnce(ctx)
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

	userIDs := r.state.ActiveUserIDs()
	if len(userIDs) == 0 {
		return
	}

	for _, userID := range userIDs {
		select {
		case <-parent.Done():
			return
		default:
		}
		r.runOnceForUser(parent, userID)
	}
}

func (r *Reconciler) runOnceForUser(parent context.Context, userID string) {
	ctx, cancel := context.WithTimeout(parent, 30*time.Second)
	defer cancel()

	identityCtx, err := r.identity.IdentityContext(ctx, userID)
	if err != nil {
		reconcileTotal.WithLabelValues("identity_error").Inc()
		r.log.Warn().Err(err).Str("user_id", userID).Msg("reconcile_identity_failed")
		return
	}

	brokerPositions, err := r.broker.GetPositions(identityCtx)
	if err != nil {
		r.log.Warn().Err(err).Str("user_id", userID).Msg("reconcile_broker_positions_failed")
		reconcileTotal.WithLabelValues("broker_error").Inc()
		return
	}
	brokerPending, err := r.broker.GetPendingOrders(identityCtx)
	if err != nil {
		r.log.Warn().Err(err).Str("user_id", userID).Msg("reconcile_broker_pending_failed")
		reconcileTotal.WithLabelValues("broker_error").Inc()
		return
	}

	r.reconcilePositions(userID, brokerPositions)
	r.reconcilePending(userID, brokerPending)

	reconcileTotal.WithLabelValues("ok").Inc()
	r.log.Debug().
		Str("user_id", userID).
		Int("broker_positions", len(brokerPositions)).
		Int("broker_pending", len(brokerPending)).
		Msg("reconcile_user_complete")
}

func (r *Reconciler) reconcilePositions(userID string, brokerPositions []models.Position) {
	enginePositions := r.state.Positions(userID)

	brokerByTicket := make(map[string]models.Position, len(brokerPositions))
	for _, p := range brokerPositions {
		brokerByTicket[p.OrderID] = p
	}

	engineByTicket := make(map[string]*models.Position, len(enginePositions))
	for i := range enginePositions {
		p := &enginePositions[i]
		if p.OrderID != "" {
			engineByTicket[p.OrderID] = p
		}
	}

	// broker_only: adopt into engine state.
	for ticket, bp := range brokerByTicket {
		if _, ok := engineByTicket[ticket]; ok {
			continue
		}
		reconcileDrift.WithLabelValues("broker_only_position").Inc()
		r.log.Warn().
			Str("user_id", userID).
			Str("broker_order_id", ticket).
			Str("symbol", bp.Symbol).
			Str("direction", bp.Direction).
			Float64("lot_size", bp.LotSize).
			Msg("reconcile_broker_only_position_adopting")
		posCopy := bp
		r.state.AdoptBrokerPosition(userID, &posCopy)
	}

	// engine_only: log but never silently delete.
	for ticket, ep := range engineByTicket {
		if _, ok := brokerByTicket[ticket]; ok {
			continue
		}
		reconcileDrift.WithLabelValues("engine_only_position").Inc()
		r.log.Error().
			Str("user_id", userID).
			Str("broker_order_id", ticket).
			Str("symbol", ep.Symbol).
			Str("direction", ep.Direction).
			Float64("lot_size", ep.LotSize).
			Msg("reconcile_engine_only_position_review_required")
	}

	// mismatch: replace engine view with broker view.
	for ticket, bp := range brokerByTicket {
		ep, ok := engineByTicket[ticket]
		if !ok {
			continue
		}
		if positionsDiffer(ep, &bp) {
			reconcileDrift.WithLabelValues("mismatch").Inc()
			r.log.Warn().
				Str("user_id", userID).
				Str("broker_order_id", ticket).
				Str("symbol", ep.Symbol).
				Float64("engine_lot", ep.LotSize).
				Float64("broker_lot", bp.LotSize).
				Float64("engine_sl", ep.StopLoss).
				Float64("broker_sl", bp.StopLoss).
				Float64("engine_tp", ep.TakeProfit).
				Float64("broker_tp", bp.TakeProfit).
				Msg("reconcile_mismatch_replacing_engine_view")
			posCopy := bp
			r.state.ReplaceBrokerPosition(userID, &posCopy)
		}
	}
}

func (r *Reconciler) reconcilePending(userID string, brokerPending []models.BrokerPendingOrder) {
	enginePending := r.state.PendingOrders(userID)

	engineByTicket := make(map[string]string, len(enginePending))
	for _, o := range enginePending {
		if o.OrderID != "" {
			engineByTicket[o.OrderID] = o.Symbol
		}
	}

	for _, bp := range brokerPending {
		if _, ok := engineByTicket[bp.OrderID]; !ok {
			reconcileDrift.WithLabelValues("broker_only_pending").Inc()
			r.log.Warn().
				Str("user_id", userID).
				Str("broker_order_id", bp.OrderID).
				Str("symbol", bp.Symbol).
				Str("direction", bp.Direction).
				Float64("price", bp.EntryPrice).
				Msg("reconcile_broker_only_pending_review_required")
		}
	}
}

func positionsDiffer(ep *models.Position, bp *models.Position) bool {
	if !floatNear(ep.LotSize, bp.LotSize) {
		return true
	}
	if !floatNear(ep.StopLoss, bp.StopLoss) {
		return true
	}
	if !floatNear(ep.TakeProfit, bp.TakeProfit) {
		return true
	}
	if !strings.EqualFold(ep.Direction, bp.Direction) {
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

// Compile-time check: the auth import is required for callers that
// construct IdentityProviders. Keeping the symbol referenced here
// keeps `go build` honest if the import is ever pruned by mistake.
var _ = auth.UserIDFromContext