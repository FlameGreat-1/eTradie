package observability

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Validation metrics.
var (
	ValidationTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_validation_total",
		Help: "Total pre-execution validation runs",
	}, []string{"result"})

	ValidationRejections = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_validation_rejections_total",
		Help: "Validation rejections by check number",
	}, []string{"check"})

	ValidationDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "etradie_execution_validation_duration_seconds",
		Help:    "Pre-execution validation latency",
		Buckets: []float64{0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1},
	})
)

// Sizing metrics.
var (
	SizingDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "etradie_execution_sizing_duration_seconds",
		Help:    "Position sizing calculation latency",
		Buckets: []float64{0.0001, 0.0005, 0.001, 0.005, 0.01},
	})

	SizingLotSize = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "etradie_execution_lot_size",
		Help:    "Calculated lot sizes",
		Buckets: []float64{0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0},
	})
)

// Order placement metrics.
var (
	OrderPlacementTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_order_placement_total",
		Help: "Total order placements by mode and status",
	}, []string{"mode", "status"})

	OrderPlacementDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "etradie_execution_order_placement_duration_seconds",
		Help:    "Order placement latency (broker round-trip)",
		Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0},
	}, []string{"mode"})
)

// End-to-end execution metrics.
var (
	ExecutionTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_total",
		Help: "Total execution attempts by outcome",
	}, []string{"symbol", "direction", "outcome"})

	ExecutionDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "etradie_execution_duration_seconds",
		Help:    "End-to-end execution latency (validate + size + place)",
		Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0},
	})
)

// State metrics.
var (
	OpenPositionCount = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "etradie_execution_open_positions",
		Help: "Current number of open positions",
	})

	PendingOrderCount = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "etradie_execution_pending_orders",
		Help: "Current number of pending orders",
	})

	DailyPnL = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "etradie_execution_daily_pnl",
		Help: "Daily realized P&L",
	})

	WeeklyPnL = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "etradie_execution_weekly_pnl",
		Help: "Weekly realized P&L",
	})
)

// Broker bridge metrics.
var (
	BrokerCallTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_broker_call_total",
		Help: "Total broker bridge calls by endpoint and status",
	}, []string{"endpoint", "status"})

	BrokerCallDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "etradie_execution_broker_call_duration_seconds",
		Help:    "Broker bridge call latency by endpoint",
		Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0},
	}, []string{"endpoint"})
)

// Audit metrics.
var (
	AuditWriteFailures = promauto.NewCounter(prometheus.CounterOpts{
		Name: "etradie_execution_audit_write_failures_total",
		Help: "Total audit log write failures to PostgreSQL",
	})
)

// Tick cache metrics.
var (
	TickCacheFetchErrors = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_tick_cache_fetch_errors_total",
		Help: "Total tick cache fetch errors by symbol",
	}, []string{"symbol"})
)

var (
	OrderIdempotencyTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_order_idempotency_total",
		Help: "Order placement idempotency outcomes",
	}, []string{"result"}) // result: claimed | duplicate

	OrderLatencyBreachTotal = promauto.NewCounter(prometheus.CounterOpts{
		Name: "etradie_execution_order_latency_breach_total",
		Help: "Orders rejected because end-to-end latency exceeded max_order_latency_ms",
	})

	// IdempotencyStoreErrorsTotal counts the times the executor fell
	// through to a NON-idempotent placement because the idempotency
	// store (TryClaim) returned an error. This is the deliberate
	// availability-over-safety path: a DB blip must not block trading.
	// A sustained non-zero rate means duplicate-order protection is
	// effectively OFF and needs operator attention (DB health / pool).
	IdempotencyStoreErrorsTotal = promauto.NewCounter(prometheus.CounterOpts{
		Name: "etradie_execution_idempotency_store_errors_total",
		Help: "Times the executor fell through to a non-idempotent placement because the idempotency store errored",
	})

	PartialFillTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_partial_fill_total",
		Help: "Partial-fill events observed at the broker",
	}, []string{"symbol", "direction"})
)

// Request-signature metrics (CHECKLIST Tier 8: signed internal
// execution requests + replay protection).
var (
	// RequestSignatureTotal counts ExecuteTrade signature verification
	// outcomes. outcome: ok|bad_signature|stale|replay|missing.
	// enforced: true|false (warn-only mode reports false). A spike in
	// bad_signature/replay with enforced=true is a security event; the
	// same spike with enforced=false during rollout is a wiring bug to
	// fix BEFORE flipping enforcement on.
	RequestSignatureTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_request_signature_total",
		Help: "ExecuteTrade request-signature verification outcomes",
	}, []string{"outcome", "enforced"})
)

// Kill-switch metrics (CHECKLIST Section 8).
var (
	// KillSwitchChangedTotal counts operator toggles of the execution
	// kill switch. scope: global|user. state: engaged|released. The
	// per-trade BLOCK is metered separately via ValidationTotal{HALTED}
	// and ExecutionTotal{outcome=HALTED}.
	KillSwitchChangedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_kill_switch_changed_total",
		Help: "Kill-switch toggle actions by scope and resulting state",
	}, []string{"scope", "state"})
)

// RateLimitedTotal counts requests rejected with HTTP 429 by the
// per-user limiter on the execution dashboard API. The route label is
// the limited endpoint ("settings" or "orders_cancel").
var RateLimitedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
	Name: "etradie_execution_rate_limited_total",
	Help: "Requests rejected with HTTP 429 by the execution per-user rate limiter",
}, []string{"route"})
