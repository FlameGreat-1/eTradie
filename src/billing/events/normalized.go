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
//
// Payment-metadata fields (Amount, Currency, InvoiceURL, Card*) are optional
// pointers so 'absent' is unambiguous from 'zero'. A $0 refund must still be
// representable. Only events that carry a real money movement populate
// Amount/Currency/InvoiceURL; only events that carry card metadata populate
// the Card* group. The applier writes these to billing_subscription_events
// as-is and additionally mirrors the Card* group onto billing_subscriptions
// so the Payment Methods card surfaces the active method.
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

	// Money moved on this event in integer minor units (e.g. 999 = $9.99).
	// nil on non-financial events (subscription_updated, paused, etc.).
	AmountCents *int64
	// ISO-4217 alphabetic, uppercase. nil iff AmountCents is nil.
	Currency *string
	// Direct HTTPS link to the Merchant-of-Record-hosted invoice PDF.
	// nil for events the provider does not link to a receipt.
	InvoiceURL *string

	// Card snapshot at the time of this event. Display-only. nil if the
	// provider did not echo card metadata on this event type. Never
	// contains a PAN or CVV — those stay with the MoR.
	CardBrand    *string
	CardLast4    *string
	CardExpMonth *int
	CardExpYear  *int
}

// Helper constructors for the parsers. They normalise empty strings
// to nil so a provider returning '' is treated identically to a
// provider returning a missing field.

func StringPtr(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}

func Int64Ptr(v int64) *int64  { return &v }
func IntPtr(v int) *int        { return &v }
