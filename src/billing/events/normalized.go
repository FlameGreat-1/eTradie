// Package events defines the canonical, provider-agnostic representation of a
// subscription change. Both Paddle and Lemon Squeezy parsers translate their
// native payloads into a NormalizedEvent so the service layer never branches
// on provider.
//
// The shape is intentionally narrow: it carries only what the service needs
// to write a billing_subscriptions row, append an audit record, and revoke
// the user's sessions. Provider-specific extras stay inside the parsers.
package events

import "time"

// Tier is the canonical subscription tier the platform enforces.
type Tier string

const (
	TierFree       Tier = "free"
	TierProBYOK    Tier = "pro_byok"
	TierProManaged Tier = "pro_managed"
)

// IsValidTier reports whether t is one of the canonical tier values.
// Used by both parsers to reject mappings that resolve to unknown tiers.
func IsValidTier(t Tier) bool {
	switch t {
	case TierFree, TierProBYOK, TierProManaged:
		return true
	}
	return false
}

// Status mirrors the canonical subscription status the platform enforces.
// Names map cleanly onto provider statuses but are deliberately our own
// vocabulary so a provider rename never breaks the system.
type Status string

const (
	StatusActive   Status = "active"
	StatusPastDue  Status = "past_due"
	StatusPaused   Status = "paused"
	StatusCanceled Status = "canceled"
	StatusRefunded Status = "refunded"
	StatusUnpaid   Status = "unpaid"
	StatusExpired  Status = "expired"
)

// NormalizedEvent is what every parser returns and the service consumes.
//
// UserID is the platform user id, recovered from the provider's custom-data
// passthrough that the gateway populates when creating the checkout. Without
// it the service has no way to correlate the event to a platform account, so
// parsers must reject events that lack it (the only legitimate exception is a
// subscription_updated whose user_id can be recovered via
// (provider, provider_subscription_id) lookup — the service handles that).
type NormalizedEvent struct {
	Provider       string    // "paddle" | "lemonsqueezy"
	EventID        string    // unique-per-event id (used for idempotency)
	EventName      string    // canonical lowercase event name (e.g. "subscription_created")
	EventTimestamp time.Time // provider-supplied event creation time

	UserID                 string // platform user id from custom data; "" → service must look up by ProviderSubscriptionID
	ProviderCustomerID     string
	ProviderSubscriptionID string
	CurrentPeriodEnd       *time.Time

	Tier   Tier
	Status Status
}
