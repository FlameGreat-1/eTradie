package performancereview

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Prometheus instruments for the performance-review module.
// Registered via promauto on the default registry to match
// tradingsystem, tradingplan, and support. The package is imported
// exactly once per gateway process (from main.go), so there is no
// duplicate-registration risk.
//
// Label budgets stay well within the Prometheus operations guide's
// recommended 100-series-per-metric ceiling:
//
//   - outcome (generate):   4 values (queued, validation_error, throttled, error)
//   - outcome (callback):   4 values (success, validation_error, unauthorized, error)
//   - outcome (fetch):      3 values (hit, empty, error)
//   - period (everywhere):  2 values (weekly, monthly)
//   - endpoint (rate_lim):  3 values (generate, list, fetch)
const (
	outcomeSuccess         = "success"
	outcomeValidationError = "validation_error"
	outcomeError           = "error"
	outcomeQueued          = "queued"
	outcomeThrottled       = "throttled"
	outcomeHit             = "hit"
	outcomeEmpty           = "empty"
	outcomeUnauthorized    = "unauthorized"

	endpointGenerate = "generate"
	endpointList     = "list"
	endpointFetch    = "fetch"
)

var (
	// PerfReviewGenerateTotal counts every POST /generate outcome,
	// partitioned by outcome and period. 'queued' is the success
	// path (the LLM call is fired and the row is now
	// status='generating').
	PerfReviewGenerateTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "performance_review_generate_total",
		Help: "Performance-review generation attempts, partitioned by outcome and period.",
	}, []string{"outcome", "period"})

	// PerfReviewGenerateDuration measures wall-clock spent inside
	// the synchronous portion of /generate (load profile, mark
	// generating, dispatch).
	PerfReviewGenerateDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "performance_review_generate_dispatch_duration_seconds",
		Help:    "Wall-clock spent dispatching a performance-review generation request.",
		Buckets: []float64{0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0},
	})

	// PerfReviewLLMCallDuration measures end-to-end time from
	// dispatch to engine callback completing.
	PerfReviewLLMCallDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "performance_review_llm_call_duration_seconds",
		Help:    "Wall-clock between generation dispatch and engine callback, by period.",
		Buckets: []float64{1, 2.5, 5, 10, 20, 30, 45, 60, 90, 120, 180, 300},
	}, []string{"period"})

	// PerfReviewCallbackTotal counts every POST
	// /internal/performance-review/callback. 'unauthorized' is the
	// canary for shared-secret drift between gateway and engine.
	PerfReviewCallbackTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "performance_review_callback_total",
		Help: "Performance-review internal callback outcomes (engine -> gateway).",
	}, []string{"outcome", "period"})

	// PerfReviewFetchTotal counts every GET on the public surface.
	PerfReviewFetchTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "performance_review_fetch_total",
		Help: "Performance-review public fetch outcomes.",
	}, []string{"outcome"})

	// PerfReviewRateLimitedTotal counts every per-user rate-limit
	// rejection.
	PerfReviewRateLimitedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "performance_review_rate_limited_total",
		Help: "Performance-review requests rejected by the per-user rate limiter.",
	}, []string{"endpoint"})

	// PerfReviewConfidenceBandTotal records the confidence band of
	// every persisted review. A spike in 'insufficient' likely means
	// onboarding users with empty journals are triggering /generate.
	PerfReviewConfidenceBandTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "performance_review_confidence_band_total",
		Help: "Persisted reviews partitioned by confidence band and period.",
	}, []string{"band", "period"})
)
