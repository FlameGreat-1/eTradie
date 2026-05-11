package lemonsqueezy

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/flamegreat-1/etradie/src/billing/events"
)

// VariantTierMap resolves a Lemon Squeezy variant_id to the canonical platform
// tier. Lemon Squeezy stringifies variant ids in custom_data even though the
// REST resource expresses them as integers; the map keys here are strings so
// callers normalise once at config-load time.
type VariantTierMap map[string]events.Tier

func (m VariantTierMap) Resolve(variantID string) (events.Tier, bool) {
	t, ok := m[variantID]
	return t, ok
}

// Sentinel errors surfaced from Parse.
var (
	ErrUnsupportedEvent = errors.New("lemonsqueezy: unsupported event type")
	ErrMissingEventID   = errors.New("lemonsqueezy: missing event id")
	ErrMissingUserID    = errors.New("lemonsqueezy: missing custom_data.user_id")
	ErrUnknownVariant   = errors.New("lemonsqueezy: unknown variant id")
	ErrInvalidPayload   = errors.New("lemonsqueezy: invalid payload")
)

// rawWebhook mirrors the documented webhook envelope. Lemon Squeezy puts the
// event metadata under "meta" and the resource under "data".
type rawWebhook struct {
	Meta rawMeta `json:"meta"`
	Data rawData `json:"data"`
}

type rawMeta struct {
	EventName  string         `json:"event_name"`
	EventID    string         `json:"event_id"`
	CustomData map[string]any `json:"custom_data"`
}

type rawData struct {
	Type       string        `json:"type"`
	ID         json.Number   `json:"id"`
	Attributes rawAttributes `json:"attributes"`
}

type rawAttributes struct {
	StoreID    json.Number    `json:"store_id"`
	CustomerID json.Number    `json:"customer_id"`
	ProductID  json.Number    `json:"product_id"`
	VariantID  json.Number    `json:"variant_id"`
	Status     string         `json:"status"`
	RenewsAt   *time.Time     `json:"renews_at"`
	EndsAt     *time.Time     `json:"ends_at"`
	CreatedAt  time.Time      `json:"created_at"`
	UpdatedAt  time.Time      `json:"updated_at"`
	Cancelled  bool           `json:"cancelled"`
	CustomData map[string]any `json:"custom_data"`
}

// Parse turns a verified Lemon Squeezy webhook delivery into a NormalizedEvent.
func Parse(r *http.Request, body []byte, variants VariantTierMap) (*events.NormalizedEvent, error) {
	eventName := strings.ToLower(strings.TrimSpace(r.Header.Get(EventNameHeader)))
	if eventName == "" {
		return nil, ErrUnsupportedEvent
	}
	if !isHandledEvent(eventName) {
		return nil, fmt.Errorf("%w: %s", ErrUnsupportedEvent, eventName)
	}

	var env rawWebhook
	dec := json.NewDecoder(strings.NewReader(string(body)))
	dec.UseNumber()
	if err := dec.Decode(&env); err != nil {
		return nil, fmt.Errorf("%w: %v", ErrInvalidPayload, err)
	}

	eventID := strings.TrimSpace(env.Meta.EventID)
	if eventID == "" {
		return nil, ErrMissingEventID
	}

	userID := extractUserID(env.Meta.CustomData)
	if userID == "" {
		userID = extractUserID(env.Data.Attributes.CustomData)
	}
	// Same correlation policy as Paddle: every event except
	// subscription_updated/cancelled/expired/paused/unpaused/resumed must
	// carry user_id; for those the service layer falls back to provider id.
	if userID == "" && !canRecoverByProviderID(eventName) {
		return nil, ErrMissingUserID
	}

	tier, status, err := mapEvent(eventName, &env.Data.Attributes, variants)
	if err != nil {
		return nil, err
	}

	var periodEnd *time.Time
	if env.Data.Attributes.RenewsAt != nil && !env.Data.Attributes.RenewsAt.IsZero() {
		t := *env.Data.Attributes.RenewsAt
		periodEnd = &t
	} else if env.Data.Attributes.EndsAt != nil && !env.Data.Attributes.EndsAt.IsZero() {
		t := *env.Data.Attributes.EndsAt
		periodEnd = &t
	}

	eventTS := env.Data.Attributes.UpdatedAt
	if eventTS.IsZero() {
		eventTS = env.Data.Attributes.CreatedAt
	}
	if eventTS.IsZero() {
		eventTS = time.Now().UTC()
	}

	return &events.NormalizedEvent{
		Provider:               Provider,
		EventID:                eventID,
		EventName:              eventName,
		EventTimestamp:         eventTS,
		UserID:                 userID,
		ProviderCustomerID:     env.Data.Attributes.CustomerID.String(),
		ProviderSubscriptionID: env.Data.ID.String(),
		CurrentPeriodEnd:       periodEnd,
		Tier:                   tier,
		Status:                 status,
	}, nil
}

func extractUserID(cd map[string]any) string {
	if cd == nil {
		return ""
	}
	for _, key := range []string{"user_id", "userId"} {
		if v, ok := cd[key]; ok {
			switch t := v.(type) {
			case string:
				return strings.TrimSpace(t)
			case json.Number:
				return strings.TrimSpace(t.String())
			case float64:
				return strconv.FormatInt(int64(t), 10)
			}
		}
	}
	return ""
}

func canRecoverByProviderID(eventName string) bool {
	switch eventName {
	case "subscription_updated",
		"subscription_cancelled",
		"subscription_expired",
		"subscription_paused",
		"subscription_unpaused",
		"subscription_resumed",
		"subscription_payment_failed",
		"subscription_payment_success",
		"subscription_payment_refunded":
		return true
	}
	return false
}

func isHandledEvent(eventName string) bool {
	switch eventName {
	case "subscription_created",
		"subscription_updated",
		"subscription_cancelled",
		"subscription_resumed",
		"subscription_expired",
		"subscription_paused",
		"subscription_unpaused",
		"subscription_payment_success",
		"subscription_payment_failed",
		"subscription_payment_refunded":
		return true
	}
	return false
}

func mapEvent(name string, attrs *rawAttributes, variants VariantTierMap) (events.Tier, events.Status, error) {
	tierFromVariant := func() (events.Tier, error) {
		vid := strings.TrimSpace(attrs.VariantID.String())
		if vid == "" {
			return "", ErrUnknownVariant
		}
		if tier, ok := variants.Resolve(vid); ok && events.IsValidTier(tier) {
			return tier, nil
		}
		return "", ErrUnknownVariant
	}

	switch name {
	case "subscription_cancelled", "subscription_expired":
		return events.TierFree, events.StatusCanceled, nil
	case "subscription_payment_refunded":
		// A refund event records that money moved back to the customer; it
		// does NOT by itself mean the subscription is over. The subscription
		// resource is still under the same variant, so the price-derived
		// tier is still the user's entitlement until either:
		//   - a subscription_cancelled / subscription_expired event lands, or
		//   - the period-end reconciler sees status='refunded' and
		//     current_period_end < NOW() and demotes.
		// If the variant is unknown (which can happen on a refund of a
		// long-cancelled product), we leave the tier empty and the service
		// layer inherits the stored tier via the recovery-by-provider-id
		// path. Either way, we do not instantly downgrade.
		tier, err := tierFromVariant()
		if err != nil {
			return "", events.StatusRefunded, nil
		}
		return tier, events.StatusRefunded, nil
	case "subscription_paused":
		tier, err := tierFromVariant()
		if err != nil {
			return "", events.StatusPaused, nil
		}
		return tier, events.StatusPaused, nil
	case "subscription_payment_failed":
		tier, err := tierFromVariant()
		if err != nil {
			return "", events.StatusPastDue, nil
		}
		return tier, events.StatusPastDue, nil
	case "subscription_created",
		"subscription_resumed",
		"subscription_unpaused",
		"subscription_payment_success":
		tier, err := tierFromVariant()
		if err != nil {
			return "", "", err
		}
		return tier, events.StatusActive, nil
	case "subscription_updated":
		tier, err := tierFromVariant()
		if err != nil {
			return "", "", err
		}
		return tier, statusFromProvider(attrs.Status), nil
	}
	return "", "", fmt.Errorf("%w: %s", ErrUnsupportedEvent, name)
}

func statusFromProvider(s string) events.Status {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "active", "on_trial":
		return events.StatusActive
	case "past_due":
		return events.StatusPastDue
	case "paused":
		return events.StatusPaused
	case "cancelled", "canceled":
		return events.StatusCanceled
	case "expired":
		return events.StatusExpired
	case "unpaid":
		return events.StatusUnpaid
	}
	return events.StatusActive
}
