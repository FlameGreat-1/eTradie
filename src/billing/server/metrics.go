package server

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/collectors"
)

// Metrics holds the Prometheus instruments the billing service exposes.
// Registered on a private *prometheus.Registry so the binary is safe to import
// (or run alongside) other modules that also use the global registry.
type Metrics struct {
	Registry *prometheus.Registry

	WebhookReceived  *prometheus.CounterVec
	WebhookDuration  *prometheus.HistogramVec
	ApplyOutcome     *prometheus.CounterVec
	CheckoutCreated  *prometheus.CounterVec
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
	reg.MustRegister(webhookReceived, webhookDuration, applyOutcome, checkoutCreated)

	return &Metrics{
		Registry:        reg,
		WebhookReceived: webhookReceived,
		WebhookDuration: webhookDuration,
		ApplyOutcome:    applyOutcome,
		CheckoutCreated: checkoutCreated,
	}
}
