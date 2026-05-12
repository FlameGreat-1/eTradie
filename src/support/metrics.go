package support

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Prometheus instruments for the support module.
//
// Registered via promauto on the default registry, identical to the
// pattern used by src/auth/clientip_metrics.go and
// src/gateway/internal/observability/metrics.go. The package is
// imported exactly once per gateway process (from the gateway's
// container), so there is no duplicate-registration risk.
//
// Cardinality bounds (per Prometheus best practice):
//   - channel  : 4 values (email, discord, telegram, whatsapp)
//   - outcome  : 3 values (delivered, failed, dropped)
//   - category : 9 values (the closed enum in TicketCategory)
//   - scope    : 4 values (ip, email, open_ticket_ceiling, honeypot)
// Total label combinations per metric are well under the 100-series
// budget recommended by the Prometheus operations guide.

const (
	// Channel labels.
	channelLabelEmail    = "email"
	channelLabelDiscord  = "discord"
	channelLabelTelegram = "telegram"
	channelLabelWhatsApp = "whatsapp"

	// Outcome labels.
	outcomeDelivered = "delivered"
	outcomeFailed    = "failed"
	outcomeDropped   = "dropped"

	// Rate-limit scope labels.
	rateScopeIP                 = "ip"
	rateScopeEmail              = "email"
	rateScopeOpenTicketCeiling  = "open_ticket_ceiling"
	rateScopeHoneypot           = "honeypot"
)

var (
	// SupportNotificationsTotal counts every fan-out outcome per channel.
	//
	// Recommended dashboard:
	//   sum by (channel) (rate(support_notifications_total{outcome="failed"}[5m]))
	//     / sum by (channel) (rate(support_notifications_total[5m]))
	// alerts on a >1% per-channel error rate over a 5-minute window.
	SupportNotificationsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "support_notifications_total",
		Help: "Outcome of support notification fan-out attempts, partitioned by channel.",
	}, []string{"channel", "outcome"})

	// SupportNotificationDuration is a per-channel histogram of the
	// total wall-clock spent inside postWithRetry / sendEmail per
	// event. Buckets are tuned for HTTP webhook latencies (sub-second
	// at the low end, with headroom for retries and SMTP).
	SupportNotificationDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "support_notification_duration_seconds",
		Help:    "Wall-clock spent delivering a single support notification, partitioned by channel.",
		Buckets: []float64{0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0},
	}, []string{"channel"})

	// SupportTicketsCreatedTotal counts every successful ticket
	// creation. Useful both for product analytics (which categories
	// drive the most volume) and for capacity planning (what fraction
	// of tickets come via the public contact form vs the dashboard).
	SupportTicketsCreatedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "support_tickets_created_total",
		Help: "Tickets successfully persisted, partitioned by channel and category.",
	}, []string{"channel", "category"})

	// SupportRateLimitedTotal counts every 429-producing rejection.
	// Operators can alarm on a sudden spike per scope (typically
	// indicates a botnet hitting the public contact endpoint) and
	// distinguish IP-rotation attacks (scope='email') from
	// volumetric attacks (scope='ip').
	SupportRateLimitedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "support_rate_limited_total",
		Help: "Public support requests rejected by a rate-limit or anti-abuse layer, partitioned by scope.",
	}, []string{"scope"})
)
