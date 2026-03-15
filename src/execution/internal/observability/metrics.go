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
	}, []string{"result"}) // "passed", "rejected", "queued", "locked", "paused"

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
	}, []string{"mode", "status"}) // mode: LIMIT/INSTANT, status: success/error

	OrderPlacementDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "etradie_execution_order_placement_duration_seconds",
		Help:    "Order placement latency (broker round-trip)",
		Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0},
	}, []string{"mode"})
)

// Broker call metrics.
var (
	BrokerCallTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_execution_broker_call_total",
		Help: "Total broker API calls by operation and status",
	}, []string{"operation", "status"})

	BrokerCallDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "etradie_execution_broker_call_duration_seconds",
		Help:    "Broker API call latency",
		Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0},
	}, []string{"operation"})
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
