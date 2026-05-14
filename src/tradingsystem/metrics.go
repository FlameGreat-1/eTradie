package tradingsystem

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Prometheus instruments for the trading-system module.
//
// Registered via promauto on the default registry, identical to the
// pattern used by src/support/metrics.go and
// src/auth/clientip_metrics.go. The package is imported exactly once
// per gateway process (from main.go), so there is no duplicate-
// registration risk.
//
// Cardinality bounds (per Prometheus best practice):
//   - outcome (save):              3 values (success, validation_error, error)
//   - outcome (skip/reset):        2 values (success, error)
//   - outcome (fetch):             3 values (hit, empty, error)
//   - outcome (internal_fetch):    4 values (hit, empty, unauthorized, error)
//   - endpoint (rate_limited):     3 values (save, skip, reset)
// Total label combinations per metric stay well under the 100-series
// budget recommended by the Prometheus operations guide.

const (
	// Outcome labels (save).
	outcomeSuccess         = "success"
	outcomeValidationError = "validation_error"
	outcomeError           = "error"

	// Outcome labels (fetch).
	outcomeHit          = "hit"
	outcomeEmpty        = "empty"
	outcomeUnauthorized = "unauthorized"

	// Endpoint labels (rate-limited).
	endpointSave  = "save"
	endpointSkip  = "skip"
	endpointReset = "reset"
)

var (
	// TradingSystemSaveTotal counts every PUT /api/v1/trading-system
	// outcome. Validation_error is split out so an alarm on
	//   rate(trading_system_save_total{outcome="error"}[5m]) > 0
	// fires only on actual server-side failures, not on user
	// 422-eligible payloads.
	TradingSystemSaveTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_system_save_total",
		Help: "Trading-system save attempts, partitioned by outcome.",
	}, []string{"outcome"})

	// TradingSystemSaveDuration is a histogram of the wall-clock spent
	// inside the save path (validation + DB upsert). Buckets tuned for
	// the sub-second envelope a healthy Postgres write should sit in.
	TradingSystemSaveDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "trading_system_save_duration_seconds",
		Help:    "Wall-clock spent persisting a trading-system profile.",
		Buckets: []float64{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0},
	})

	// TradingSystemSkipTotal counts every POST /skip outcome.
	TradingSystemSkipTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_system_skip_total",
		Help: "Trading-system skip attempts, partitioned by outcome.",
	}, []string{"outcome"})

	// TradingSystemResetTotal counts every POST /reset outcome.
	TradingSystemResetTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_system_reset_total",
		Help: "Trading-system reset attempts, partitioned by outcome.",
	}, []string{"outcome"})

	// TradingSystemFetchTotal counts every GET /api/v1/trading-system.
	// 'hit' = user has an active profile, 'empty' = user has not
	// built one (status='none' or 'skipped'), 'error' = DB failure.
	TradingSystemFetchTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_system_fetch_total",
		Help: "Trading-system public fetch outcomes.",
	}, []string{"outcome"})

	// TradingSystemInternalFetchTotal counts every POST
	// /internal/trading-system/get. 'unauthorized' is the canary for
	// shared-secret drift between gateway and engine.
	TradingSystemInternalFetchTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_system_internal_fetch_total",
		Help: "Trading-system internal fetch outcomes (engine -> gateway).",
	}, []string{"outcome"})

	// TradingSystemInternalFetchDuration is the latency histogram for
	// the engine-side fetch. A long tail here directly delays every
	// analysis cycle, so the buckets are tight.
	TradingSystemInternalFetchDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "trading_system_internal_fetch_duration_seconds",
		Help:    "Wall-clock spent serving the engine-side trading-system fetch.",
		Buckets: []float64{0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0},
	})

	// TradingSystemRateLimitedTotal counts every per-user rate-limit
	// rejection. A flat counter is healthy; a sudden spike on one
	// endpoint typically indicates a compromised user account or a
	// scripted abuse pattern.
	TradingSystemRateLimitedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "trading_system_rate_limited_total",
		Help: "Trading-system requests rejected by the per-user rate limiter.",
	}, []string{"endpoint"})
)
