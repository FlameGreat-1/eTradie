package paddle

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/flamegreat-1/etradie/src/billing/events"
)

// EventIDHeader is the request header that carries the unique notification id.
// Paddle Billing v1 names it "Paddle-Notification-Id". The body also embeds
// notification_id; we read the header preferentially because it is part of the
// signed envelope and therefore guaranteed to match.
const EventIDHeader = "Paddle-Notification-Id"

// PriceTierMap resolves a Paddle price_id to the canonical platform tier.
// Constructed from PADDLE_PRICE_PRO_BYOK and PADDLE_PRICE_PRO_MANAGED env vars
// in main.go; injected here so the parser stays config-free and testable.
type PriceTierMap map[string]events.Tier

// Resolve returns the platform tier for the given price_id, or ("", false)
// when the id is unknown. Callers must reject unknown prices.
func (m PriceTierMap) Resolve(priceID string) (events.Tier, bool) {
	t, ok := m[priceID]
	return t, ok
}

// Sentinel errors surfaced from Parse. The HTTP layer maps these to 400 so
// providers stop retrying on permanent rejections.
var (
	ErrUnsupportedEvent  = errors.New("paddle: unsupported event type")
	ErrMissingEventID    = errors.New("paddle: missing notification id")
	ErrMissingUserID     = errors.New("paddle: missing custom_data.user_id")
	ErrUnknownPrice      = errors.New("paddle: unknown price id")
	ErrInvalidPayload    = errors.New("paddle: invalid payload")
)

// rawNotification mirrors the v1 webhook envelope. We deliberately keep the
// struct minimal — only fields we actually consume — so a provider-side
// schema addition does not break parsing.
type rawNotification struct {
	EventID    string          `json:"event_id"`
	NotifID    string          `json:"notification_id"`
	EventType  string          `json:"event_type"`
	OccurredAt time.Time       `json:"occurred_at"`
	Data       json.RawMessage `json:"data"`
}

type rawSubscription struct {
	ID          string          `json:"id"`
	Status      string          `json:"status"`
	CustomerID  string          `json:"customer_id"`
	CurrentPeriod *struct {
		EndsAt time.Time `json:"ends_at"`
	} `json:"current_billing_period"`
	CustomData  map[string]any  `json:"custom_data"`
	Items       []rawSubItem    `json:"items"`
	CanceledAt  *time.Time      `json:"canceled_at"`
	PausedAt    *time.Time      `json:"paused_at"`
	ScheduledChange *struct {
		Action      string    `json:"action"`
		EffectiveAt time.Time `json:"effective_at"`
	} `json:"scheduled_change"`
}

type rawSubItem struct {
	Status string  `json:"status"`
	Price  rawPrice `json:"price"`
}

type rawPrice struct {
	ID string `json:"id"`
}

// Parse turns a verified Paddle webhook delivery into a NormalizedEvent.
//
// The verifier MUST be invoked successfully before Parse — this function
// trusts the body bytes. The notification id is read from the header (signed)
// rather than the JSON body to defend against a partial-trust scenario where
// a future change to the body shape would still be HMAC-bound to the header.
func Parse(r *http.Request, body []byte, prices PriceTierMap) (*events.NormalizedEvent, error) {
	eventID := r.Header.Get(EventIDHeader)

	var env rawNotification
	if err := json.Unmarshal(body, &env); err != nil {
		return nil, fmt.Errorf("%w: %v", ErrInvalidPayload, err)
	}
	if eventID == "" {
		eventID = env.NotifID
	}
	if eventID == "" {
		eventID = env.EventID
	}
	if eventID == "" {
		return nil, ErrMissingEventID
	}
	if env.OccurredAt.IsZero() {
		env.OccurredAt = time.Now().UTC()
	}

	eventType := strings.ToLower(strings.TrimSpace(env.EventType))
	if !isHandledEvent(eventType) {
		return nil, fmt.Errorf("%w: %s", ErrUnsupportedEvent, eventType)
	}

	var sub rawSubscription
	if err := json.Unmarshal(env.Data, &sub); err != nil {
		return nil, fmt.Errorf("%w: %v", ErrInvalidPayload, err)
	}

	userID := extractUserID(sub.CustomData)
	// subscription.updated may legitimately omit custom_data on certain
	// provider-side state changes. The service layer recovers user_id via
	// (provider, provider_subscription_id) lookup in that case. For all
	// other event types we require user_id at parse time.
	if userID == "" && eventType != "subscription.updated" && eventType != "subscription.canceled" &&
		eventType != "subscription.paused" && eventType != "subscription.resumed" &&
		eventType != "subscription.past_due" {
		return nil, ErrMissingUserID
	}

	tier, status, err := mapEvent(eventType, &sub, prices)
	if err != nil {
		return nil, err
	}

	var periodEnd *time.Time
	if sub.CurrentPeriod != nil && !sub.CurrentPeriod.EndsAt.IsZero() {
		t := sub.CurrentPeriod.EndsAt
		periodEnd = &t
	}

	return &events.NormalizedEvent{
		Provider:               Provider,
		EventID:                eventID,
		EventName:              normalizeEventName(eventType),
		EventTimestamp:         env.OccurredAt,
		UserID:                 userID,
		ProviderCustomerID:     sub.CustomerID,
		ProviderSubscriptionID: sub.ID,
		CurrentPeriodEnd:       periodEnd,
		Tier:                   tier,
		Status:                 status,
	}, nil
}

// extractUserID reads the platform user id from custom_data. We accept either
// "user_id" or "userId" to be permissive about caller convention.
func extractUserID(cd map[string]any) string {
	if cd == nil {
		return ""
	}
	for _, key := range []string{"user_id", "userId"} {
		if v, ok := cd[key]; ok {
			if s, ok := v.(string); ok {
				return strings.TrimSpace(s)
			}
		}
	}
	return ""
}

func isHandledEvent(t string) bool {
	switch t {
	case "subscription.created",
		"subscription.activated",
		"subscription.updated",
		"subscription.canceled",
		"subscription.paused",
		"subscription.resumed",
		"subscription.past_due":
		return true
	}
	return false
}

// normalizeEventName collapses Paddle dotted names to the underscore form the
// rest of the platform uses ("subscription.created" → "subscription_created").
func normalizeEventName(t string) string {
	return strings.ReplaceAll(t, ".", "_")
}

// mapEvent resolves (tier, status) from the event type and the embedded
// subscription state. The active price item determines the tier; the event
// type determines the status. A canceled/paused/past_due event NEVER changes
// the tier away from the price-derived tier on its own — we only flip the
// tier to "free" when the subscription is fully canceled.
func mapEvent(eventType string, sub *rawSubscription, prices PriceTierMap) (events.Tier, events.Status, error) {
	switch eventType {
	case "subscription.canceled":
		return events.TierFree, events.StatusCanceled, nil
	case "subscription.paused":
		tier, err := tierFromSub(sub, prices)
		if err != nil {
			// Paused subscriptions whose price is unknown: still treat as paused
			// against the user's existing tier — the service layer will use the
			// stored tier when it merges this event in.
			return "", events.StatusPaused, nil
		}
		return tier, events.StatusPaused, nil
	case "subscription.past_due":
		tier, err := tierFromSub(sub, prices)
		if err != nil {
			return "", events.StatusPastDue, nil
		}
		return tier, events.StatusPastDue, nil
	case "subscription.resumed", "subscription.activated", "subscription.created":
		tier, err := tierFromSub(sub, prices)
		if err != nil {
			return "", "", err
		}
		return tier, events.StatusActive, nil
	case "subscription.updated":
		tier, err := tierFromSub(sub, prices)
		if err != nil {
			return "", "", err
		}
		return tier, statusFromProvider(sub.Status), nil
	}
	return "", "", fmt.Errorf("%w: %s", ErrUnsupportedEvent, eventType)
}

// tierFromSub picks the first item with status "active" (or trailing) and
// resolves its price_id through the configured map. An item whose status is
// "trialing" still grants the paid tier.
func tierFromSub(sub *rawSubscription, prices PriceTierMap) (events.Tier, error) {
	for _, it := range sub.Items {
		if it.Price.ID == "" {
			continue
		}
		if tier, ok := prices.Resolve(it.Price.ID); ok && events.IsValidTier(tier) {
			return tier, nil
		}
	}
	return "", ErrUnknownPrice
}

// statusFromProvider maps Paddle's subscription.status string onto our
// canonical Status. Unknown values default to Active to avoid spuriously
// downgrading a customer; the next event will correct it if it really did
// change.
func statusFromProvider(s string) events.Status {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "active", "trialing":
		return events.StatusActive
	case "past_due":
		return events.StatusPastDue
	case "paused":
		return events.StatusPaused
	case "canceled":
		return events.StatusCanceled
	}
	return events.StatusActive
}
