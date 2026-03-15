package observability

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Cycle-level metrics.
var (
	GatewayCycleTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_gateway_cycle_total",
		Help: "Total gateway analysis cycles",
	}, []string{"status", "outcome"})

	GatewayCycleDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "etradie_gateway_cycle_duration_seconds",
		Help:    "Full gateway analysis cycle latency",
		Buckets: []float64{5.0, 10.0, 30.0, 60.0, 120.0, 180.0, 300.0},
	})

	GatewayActiveCycles = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "etradie_gateway_active_cycles",
		Help: "Number of currently running analysis cycles",
	})
)

// Phase-level metrics.
var GatewayPhaseDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
	Name:    "etradie_gateway_phase_duration_seconds",
	Help:    "Duration of individual pipeline phases",
	Buckets: []float64{0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0},
}, []string{"phase"})

// Collector metrics.
var (
	GatewayTACollectDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "etradie_gateway_ta_collect_duration_seconds",
		Help:    "TA collection phase latency",
		Buckets: []float64{0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0},
	}, []string{"symbol"})

	GatewayMacroCollectDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "etradie_gateway_macro_collect_duration_seconds",
		Help:    "Macro collection phase latency",
		Buckets: []float64{0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0},
	})

	GatewayTACandidatesPerCycle = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "etradie_gateway_ta_candidates_per_cycle",
		Help:    "Number of TA candidates detected per cycle",
		Buckets: []float64{0, 1, 2, 5, 10, 20, 50},
	}, []string{"framework"})
)

// RAG metrics.
var GatewayRAGDuration = promauto.NewHistogram(prometheus.HistogramOpts{
	Name:    "etradie_gateway_rag_duration_seconds",
	Help:    "RAG retrieval latency as seen by the gateway",
	Buckets: []float64{0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0},
})

// Processor metrics.
var GatewayProcessorDuration = promauto.NewHistogram(prometheus.HistogramOpts{
	Name:    "etradie_gateway_processor_duration_seconds",
	Help:    "Processor LLM call latency as seen by the gateway",
	Buckets: []float64{0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0},
})

// Guard metrics.
var (
	GatewayGuardRejections = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_gateway_guard_rejections_total",
		Help: "Guard rejection count by rule",
	}, []string{"rule"})

	GatewayGuardDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "etradie_gateway_guard_duration_seconds",
		Help:    "Guard evaluation latency",
		Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0},
	})
)

// Routing metrics.
var (
	GatewayTradeRouted = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_gateway_trade_routed_total",
		Help: "Trades routed to execution engine",
	}, []string{"symbol", "direction"})

	GatewayNoSetupTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "etradie_gateway_no_setup_total",
		Help: "Cycles that ended with NO SETUP",
	}, []string{"reason"})
)

// Error metrics.
var GatewayStageErrors = promauto.NewCounterVec(prometheus.CounterOpts{
	Name: "etradie_gateway_stage_errors_total",
	Help: "Errors by pipeline stage",
}, []string{"stage", "error_type"})
