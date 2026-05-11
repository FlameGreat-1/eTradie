package server

import (
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/collectors"

	"github.com/flamegreat-1/etradie/src/billing/service"
)

// Metrics holds the Prometheus instruments the billing service exposes.
// Registered on a private *prometheus.Registry so the binary is safe to import
// (or run alongside) other modules that also use the global registry.
type Metrics struct {
	Registry *prometheus.Registry

	WebhookReceived *prometheus.CounterVec
	WebhookDuration *prometheus.HistogramVec
	ApplyOutcome    *prometheus.CounterVec
	CheckoutCreated *prometheus.CounterVec

	// Reconciler instruments. *Metrics implements service.ReconcilerMetrics
	// via the methods at the bottom of this file.
	ReconcilerRuns     *prometheus.CounterVec
	ReconcilerDemoted  *prometheus.CounterVec
	ReconcilerErrors   *prometheus.CounterVec
	IdempotencyPruned  prometheus.Counter
	ReconcilerDuration prometheus.Histogram

	// Resilience instruments. *Metrics implements
	// service.BreakerObserver via OnBreakerTransition below.
	BreakerTransitions  *prometheus.CounterVec
	BreakerState        *prometheus.GaugeVec
	SemaphoreInFlight   *prometheus.GaugeVec
	SemaphoreCapacity   *prometheus.GaugeVec
	SemaphoreRejected   *prometheus.CounterVec
	WebhookRateLimited  *prometheus.CounterVec
	WebhookRateTracked  prometheus.Gauge
}

// NewMetrics constructs and registers the instrument set.
func NewMetrics() *Metrics {
	reg := prometheus.NewRegistry()
	reg.MustRegister(collectors.NewGoCollector())
	reg.MustRegister(collectors.NewProcessCollector(collectors.ProcessCollectorOpts{}))

	webhookReceived := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "billing_webhook_received_total",
			Help: "Total webhook deliveries received, partitioned by provider, event name, and final result.",
		},
		[]string{"provider", "event", "result"},
	)
	webhookDuration := prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "billing_webhook_duration_seconds",
			Help:    "Wall-clock duration of webhook handling, including signature verify and DB transaction.",
			Buckets: prometheus.ExponentialBuckets(0.01, 2, 10), // 10ms .. ~10s
		},
		[]string{"provider"},
	)
	applyOutcome := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "billing_subscription_apply_total",
			Help: "Outcomes of subscription state application (applied, duplicate, out_of_order, error).",
		},
		[]string{"provider", "outcome"},
	)
	checkoutCreated := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "billing_checkout_created_total",
			Help: "Outcomes of checkout creation requests, partitioned by provider, tier, and result.",
		},
		[]string{"provider", "tier", "result"},
	)
	reconcilerRuns := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "billing_reconciler_runs_total",
			Help: "Reconciler ticks, labelled by outcome (ok, sweep_error, prune_error, sweep_and_prune_error).",
		},
		[]string{"outcome"},
	)
	reconcilerDemoted := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "billing_reconciler_demoted_total",
			Help: "Subscriptions demoted to free by the period-end reconciler, labelled by their previous tier.",
		},
		[]string{"previous_tier"},
	)
	reconcilerErrors := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "billing_reconciler_errors_total",
			Help: "Reconciler per-stage errors (list, begin_tx, demote, audit, commit, prune).",
		},
		[]string{"stage"},
	)
	idempotencyPruned := prometheus.NewCounter(
		prometheus.CounterOpts{
			Name: "billing_idempotency_pruned_total",
			Help: "Total processed_webhook_events rows deleted by the retention janitor.",
		},
	)
	reconcilerDuration := prometheus.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "billing_reconciler_duration_seconds",
			Help:    "Wall-clock duration of a single reconciler tick (sweep + prune).",
			Buckets: prometheus.ExponentialBuckets(0.05, 2, 10), // 50ms .. ~50s
		},
	)
	breakerTransitions := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "billing_breaker_transitions_total",
			Help: "Circuit-breaker state transitions, labelled by breaker name and direction. Alert on rate > 0 with to=open.",
		},
		[]string{"name", "from", "to"},
	)
	breakerState := prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "billing_breaker_state",
			Help: "Current circuit-breaker state: 0=closed, 1=half_open, 2=open.",
		},
		[]string{"name"},
	)
	semInFlight := prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "billing_semaphore_in_flight",
			Help: "Current in-flight permits held per semaphore. Compare against billing_semaphore_capacity.",
		},
		[]string{"name"},
	)
	semCapacity := prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "billing_semaphore_capacity",
			Help: "Configured maximum permits per semaphore (constant per process lifetime).",
		},
		[]string{"name"},
	)
	semRejected := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "billing_semaphore_rejected_total",
			Help: "TryAcquire calls refused due to semaphore saturation.",
		},
		[]string{"name"},
	)
	webhookRateLimited := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "billing_webhook_rate_limited_total",
			Help: "Webhook requests dropped before HMAC verification (rate_limit or saturated).",
		},
		[]string{"reason"},
	)
	webhookRateTracked := prometheus.NewGauge(
		prometheus.GaugeOpts{
			Name: "billing_webhook_rate_tracked_keys",
			Help: "Number of distinct client IPs currently held in the rate-limit LRU.",
		},
	)

	reg.MustRegister(
		webhookReceived, webhookDuration, applyOutcome, checkoutCreated,
		reconcilerRuns, reconcilerDemoted, reconcilerErrors,
		idempotencyPruned, reconcilerDuration,
		breakerTransitions, breakerState,
		semInFlight, semCapacity, semRejected,
		webhookRateLimited, webhookRateTracked,
	)

	return &Metrics{
		Registry:           reg,
		WebhookReceived:    webhookReceived,
		WebhookDuration:    webhookDuration,
		ApplyOutcome:       applyOutcome,
		CheckoutCreated:    checkoutCreated,
		ReconcilerRuns:     reconcilerRuns,
		ReconcilerDemoted:  reconcilerDemoted,
		ReconcilerErrors:   reconcilerErrors,
		IdempotencyPruned:  idempotencyPruned,
		ReconcilerDuration: reconcilerDuration,
		BreakerTransitions: breakerTransitions,
		BreakerState:       breakerState,
		SemaphoreInFlight:  semInFlight,
		SemaphoreCapacity:  semCapacity,
		SemaphoreRejected:  semRejected,
		WebhookRateLimited: webhookRateLimited,
		WebhookRateTracked: webhookRateTracked,
	}
}

// OnBreakerTransition implements service.BreakerObserver. Called by
// every breaker on every state change. Lock-free on the hot path
// (Prometheus counter Inc + gauge Set are atomic).
func (m *Metrics) OnBreakerTransition(name string, from, to service.BreakerState) {
	m.BreakerTransitions.WithLabelValues(name, from.String(), to.String()).Inc()
	m.BreakerState.WithLabelValues(name).Set(float64(to))
}

// ObserveReconcilerRun records one full reconciler tick. Implements
// service.ReconcilerMetrics.
func (m *Metrics) ObserveReconcilerRun(outcome string, duration time.Duration) {
	m.ReconcilerRuns.WithLabelValues(outcome).Inc()
	m.ReconcilerDuration.Observe(duration.Seconds())
}

// IncReconcilerDemoted records one successful period-end demotion.
// Implements service.ReconcilerMetrics.
func (m *Metrics) IncReconcilerDemoted(previousTier string) {
	m.ReconcilerDemoted.WithLabelValues(previousTier).Inc()
}

// IncReconcilerError records one per-stage failure. Implements
// service.ReconcilerMetrics.
func (m *Metrics) IncReconcilerError(stage string) {
	m.ReconcilerErrors.WithLabelValues(stage).Inc()
}

// AddIdempotencyPruned records the number of rows the janitor deleted.
// Implements service.ReconcilerMetrics.
func (m *Metrics) AddIdempotencyPruned(rows int64) {
	if rows > 0 {
		m.IdempotencyPruned.Add(float64(rows))
	}
}
