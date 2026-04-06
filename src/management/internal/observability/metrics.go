package observability

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Trade lifecycle metrics.
var (
	ManagedTradesGauge = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "etradie_management_active_trades",
		Help: "Current number of trades under management",
	})

	TradeRegisteredTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_management_trades_registered_total",
		Help: "Total trades registered for management",
	}, []string{"symbol", "style"})

	TradeClosedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_management_trades_closed_total",
		Help: "Total trades closed by outcome",
	}, []string{"symbol", "outcome"})
)

// Stop loss management metrics.
var (
	BreakevenSetTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_management_breakeven_set_total",
		Help: "Total break-even SL moves",
	}, []string{"symbol"})

	TrailingSLMovedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_management_trailing_sl_moved_total",
		Help: "Total trailing SL adjustments",
	}, []string{"symbol"})
)

// Take profit metrics.
var (
	PartialCloseTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_management_partial_close_total",
		Help: "Total partial closes by TP level",
	}, []string{"symbol", "tp_level"})
)

// EOD protocol metrics.
var (
	EODClosureTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_management_eod_closure_total",
		Help: "Total end-of-day forced closures",
	}, []string{"symbol", "style"})
)

// Invalidation metrics.
var (
	InvalidationTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_management_invalidation_total",
		Help: "Total trade invalidations by reason",
	}, []string{"symbol", "reason"})
)

// Broker bridge metrics.
var (
	BrokerCallTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_management_broker_call_total",
		Help: "Total broker bridge calls by endpoint and status",
	}, []string{"endpoint", "status"})

	BrokerCallDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "etradie_management_broker_call_duration_seconds",
		Help:    "Broker bridge call latency by endpoint",
		Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0},
	}, []string{"endpoint"})
)

// P&L metrics.
var (
	RealizedPnL = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "etradie_management_realized_pnl",
		Help: "Cumulative realized P&L",
	})

	UnrealizedPnL = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "etradie_management_unrealized_pnl",
		Help: "Total unrealized P&L across all managed trades",
	})
)

// Journal write metrics.
var (
	JournalWriteFailures = promauto.NewCounter(prometheus.CounterOpts{
		Name: "etradie_management_journal_write_failures_total",
		Help: "Total journal write failures to PostgreSQL",
	})
)

// Tick cache metrics.
var (
	TickCacheFetchErrors = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_management_tick_cache_fetch_errors_total",
		Help: "Total tick cache fetch errors by symbol",
	}, []string{"symbol"})

	TickCacheActiveSymbols = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "etradie_management_tick_cache_active_symbols",
		Help: "Number of symbols actively being polled by the tick cache",
	})
)
