package auth

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// Account-recovery observability (CHECKLIST Tier 1 "Recovery attempt
// monitoring").
//
// These counters surface the password-reset request and redemption
// outcomes to the metrics rail so operators can alert on
// account-takeover / abuse signals WITHOUT scraping logs. The
// forgot-password endpoint stays non-enumerable on the wire (it always
// returns one generic 202); the outcome breakdown lives ONLY here, in
// the operator-side metric, never in the user-facing response.
//
// Registered via promauto on the Prometheus default registry, the same
// pattern as clientip_metrics.go and src/support/metrics.go. The auth
// package is imported once per gateway process, so there is no
// duplicate-registration risk. The /metrics endpoint the gateway HTTP
// server already mounts exposes them; the existing ServiceMonitor
// scrapes them with no extra wiring.
//
// Cardinality is bounded: every label value below is a fixed compile-
// time constant (the skipReason* set + the success / failure labels),
// so the series count per metric is small and stable.

// Password-reset request outcome labels. The skip reasons mirror the
// stable skipReason* constants used by logForgotSkip so a metric series
// and a log line for the same event carry the identical reason string.
const (
	recoveryRequestDispatched = "dispatched"
	// The remaining request outcomes reuse the skipReason* constants
	// declared in password_reset_handlers.go (user_not_found,
	// user_inactive, user_federated, per_user_rate_limited,
	// lookup_failed, token_generation_failed, persist_failed).
)

// Password-reset redemption outcome labels.
const (
	recoveryRedeemed             = "redeemed"
	recoveryRedeemInvalidExpired = "invalid_or_expired"
	recoveryRedeemComplexity     = "complexity_rejected"
	recoveryRedeemReused         = "reused_password"
	recoveryRedeemBreached       = "breached_password"
	recoveryRedeemPersistFailed  = "persist_failed"
	recoveryRedeemInternalError  = "internal_error"
)

var (
	// PasswordResetRequestsTotal counts every POST /auth/password/forgot
	// outcome, partitioned by outcome. "dispatched" is the success path
	// (an email was queued); every other value is a silent-skip branch
	// that the wire response hides behind the generic 202.
	//
	// Alerting examples:
	//   increase(auth_password_reset_requests_total{outcome="per_user_rate_limited"}[15m]) > 0
	//     -> a single account is being mailbombed / ATO-probed.
	//   a rising ratio of outcome="user_not_found" to the total
	//     -> an email-enumeration sweep against the endpoint.
	PasswordResetRequestsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "auth_password_reset_requests_total",
		Help: "Password-reset (forgot) request outcomes, partitioned by outcome (dispatched or a silent-skip reason). The wire response is always a generic 202; this metric is the operator-side recovery-attempt monitor.",
	}, []string{"outcome"})

	// PasswordResetRedemptionsTotal counts every POST /auth/password/reset
	// outcome, partitioned by outcome. A spike in "redeemed" with no
	// preceding "dispatched" volume, or a spike in
	// "invalid_or_expired", indicates stolen-token redemption attempts.
	PasswordResetRedemptionsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "auth_password_reset_redemptions_total",
		Help: "Password-reset redemption outcomes, partitioned by outcome (redeemed or a typed failure).",
	}, []string{"outcome"})
)
