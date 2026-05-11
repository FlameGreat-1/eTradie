package lemonsqueezy

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/billing/events"
)

const (
	testVariantBYOK    = "99001"
	testVariantManaged = "99002"
)

func testVariants() VariantTierMap {
	return VariantTierMap{
		testVariantBYOK:    events.TierProBYOK,
		testVariantManaged: events.TierProManaged,
	}
}

func reqWithEvent(t *testing.T, body, eventName string) *http.Request {
	t.Helper()
	r := httptest.NewRequest(http.MethodPost, "/webhooks/lemonsqueezy", strings.NewReader(body))
	if eventName != "" {
		r.Header.Set(EventNameHeader, eventName)
	}
	return r
}

func TestLSParse_SubscriptionCreated(t *testing.T) {
	body := `{
		"meta": {"event_name": "subscription_created", "event_id": "ev_1", "custom_data": {"user_id": "u_42"}},
		"data": {
			"type": "subscriptions",
			"id": "77",
			"attributes": {
				"store_id": 1,
				"customer_id": 555,
				"variant_id": ` + testVariantManaged + `,
				"status": "active",
				"renews_at": "2025-02-01T00:00:00Z",
				"created_at": "2025-01-01T00:00:00Z",
				"updated_at": "2025-01-01T00:00:00Z"
			}
		}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_created"), []byte(body), testVariants())
	require.NoError(t, err)
	assert.Equal(t, Provider, ev.Provider)
	assert.Equal(t, "ev_1", ev.EventID)
	assert.Equal(t, "subscription_created", ev.EventName)
	assert.Equal(t, "u_42", ev.UserID)
	assert.Equal(t, "77", ev.ProviderSubscriptionID)
	assert.Equal(t, "555", ev.ProviderCustomerID)
	assert.Equal(t, events.TierProManaged, ev.Tier)
	assert.Equal(t, events.StatusActive, ev.Status)
	require.NotNil(t, ev.CurrentPeriodEnd)
}

func TestLSParse_SubscriptionCancelled(t *testing.T) {
	body := `{
		"meta": {"event_name": "subscription_cancelled", "event_id": "ev_2"},
		"data": {
			"type": "subscriptions", "id": "77",
			"attributes": {"store_id":1,"customer_id":555,"variant_id":` + testVariantBYOK + `,"status":"cancelled","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-15T00:00:00Z"}
		}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_cancelled"), []byte(body), testVariants())
	require.NoError(t, err)
	assert.Equal(t, events.TierFree, ev.Tier)
	assert.Equal(t, events.StatusCanceled, ev.Status)
}

func TestLSParse_SubscriptionExpired(t *testing.T) {
	body := `{
		"meta": {"event_name": "subscription_expired", "event_id": "ev_3"},
		"data": {"type":"subscriptions","id":"77","attributes":{"store_id":1,"customer_id":555,"variant_id":` + testVariantBYOK + `,"status":"expired","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-15T00:00:00Z"}}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_expired"), []byte(body), testVariants())
	require.NoError(t, err)
	assert.Equal(t, events.TierFree, ev.Tier)
	assert.Equal(t, events.StatusCanceled, ev.Status)
}

// TestLSParse_PaymentRefunded verifies that subscription_payment_refunded
// keeps the variant-derived tier in place and only flips status to
// refunded. Demotion to free now happens via subscription_cancelled /
// subscription_expired or the period-end reconciler — not a single
// refund event, which would aggressively cut Pro access mid-period.
func TestLSParse_PaymentRefunded(t *testing.T) {
	body := `{
		"meta": {"event_name": "subscription_payment_refunded", "event_id": "ev_4"},
		"data": {"type":"subscriptions","id":"77","attributes":{"store_id":1,"customer_id":555,"variant_id":` + testVariantManaged + `,"status":"active","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-20T00:00:00Z"}}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_payment_refunded"), []byte(body), testVariants())
	require.NoError(t, err)
	assert.Equal(t, events.TierProManaged, ev.Tier, "refund must keep the variant-derived tier")
	assert.Equal(t, events.StatusRefunded, ev.Status)
}

// TestLSParse_PaymentRefunded_UnknownVariant covers the secondary path:
// a refund whose variant is no longer in our map (e.g., a long-cancelled
// product). The parser must yield an empty tier so the service layer
// inherits the stored tier via the recovery path; it must NOT raise
// ErrUnknownVariant for the refund event, which would 422 the webhook
// and trigger provider retries forever.
func TestLSParse_PaymentRefunded_UnknownVariant(t *testing.T) {
	body := `{
		"meta": {"event_name": "subscription_payment_refunded", "event_id": "ev_4b"},
		"data": {"type":"subscriptions","id":"77","attributes":{"store_id":1,"customer_id":555,"variant_id":424242,"status":"active","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-20T00:00:00Z"}}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_payment_refunded"), []byte(body), testVariants())
	require.NoError(t, err)
	assert.Equal(t, events.Tier(""), ev.Tier, "refund with unknown variant must yield empty tier so service inherits stored tier")
	assert.Equal(t, events.StatusRefunded, ev.Status)
}

func TestLSParse_PaymentFailed(t *testing.T) {
	body := `{
		"meta": {"event_name": "subscription_payment_failed", "event_id": "ev_5"},
		"data": {"type":"subscriptions","id":"77","attributes":{"store_id":1,"customer_id":555,"variant_id":` + testVariantBYOK + `,"status":"past_due","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-25T00:00:00Z"}}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_payment_failed"), []byte(body), testVariants())
	require.NoError(t, err)
	assert.Equal(t, events.TierProBYOK, ev.Tier)
	assert.Equal(t, events.StatusPastDue, ev.Status)
}

func TestLSParse_UpdatedStatusMapping(t *testing.T) {
	body := `{
		"meta": {"event_name": "subscription_updated", "event_id": "ev_6"},
		"data": {"type":"subscriptions","id":"77","attributes":{"store_id":1,"customer_id":555,"variant_id":` + testVariantBYOK + `,"status":"paused","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-30T00:00:00Z"}}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_updated"), []byte(body), testVariants())
	require.NoError(t, err)
	assert.Equal(t, events.TierProBYOK, ev.Tier)
	assert.Equal(t, events.StatusPaused, ev.Status)
}

func TestLSParse_MissingEventName(t *testing.T) {
	body := `{"meta":{"event_id":"e"},"data":{}}`
	_, err := Parse(reqWithEvent(t, body, ""), []byte(body), testVariants())
	assert.True(t, errors.Is(err, ErrUnsupportedEvent), "got %v", err)
}

func TestLSParse_MissingEventID(t *testing.T) {
	body := `{"meta":{"event_name":"subscription_created"},"data":{"type":"subscriptions","id":"77","attributes":{"variant_id":` + testVariantBYOK + `}}}`
	_, err := Parse(reqWithEvent(t, body, "subscription_created"), []byte(body), testVariants())
	assert.True(t, errors.Is(err, ErrMissingEventID), "got %v", err)
}

func TestLSParse_UnknownVariant(t *testing.T) {
	body := `{
		"meta":{"event_name":"subscription_created","event_id":"ev_v","custom_data":{"user_id":"u"}},
		"data":{"type":"subscriptions","id":"77","attributes":{"store_id":1,"customer_id":555,"variant_id":99999,"status":"active","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z"}}
	}`
	_, err := Parse(reqWithEvent(t, body, "subscription_created"), []byte(body), testVariants())
	assert.True(t, errors.Is(err, ErrUnknownVariant), "got %v", err)
}

func TestLSParse_InvalidJSON(t *testing.T) {
	body := `{not json`
	_, err := Parse(reqWithEvent(t, body, "subscription_created"), []byte(body), testVariants())
	assert.True(t, errors.Is(err, ErrInvalidPayload), "got %v", err)
}

func TestLSParse_UserIDAsJSONNumber(t *testing.T) {
	// Lemon Squeezy stringifies numeric custom_data values to JSON Numbers
	// in some cases. The parser must extract them as strings.
	body := `{
		"meta":{"event_name":"subscription_created","event_id":"ev_num","custom_data":{"user_id":12345}},
		"data":{"type":"subscriptions","id":"77","attributes":{"store_id":1,"customer_id":555,"variant_id":` + testVariantBYOK + `,"status":"active","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z"}}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_created"), []byte(body), testVariants())
	require.NoError(t, err)
	assert.Equal(t, "12345", ev.UserID)
}
