package paddle

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
	testPriceBYOK    = "pri_byok_01"
	testPriceManaged = "pri_managed_01"
)

func testPrices() PriceTierMap {
	return PriceTierMap{
		testPriceBYOK:    events.TierProBYOK,
		testPriceManaged: events.TierProManaged,
	}
}

func requestWith(t *testing.T, body string, eventID string) *http.Request {
	t.Helper()
	r := httptest.NewRequest(http.MethodPost, "/webhooks/paddle", strings.NewReader(body))
	if eventID != "" {
		r.Header.Set(EventIDHeader, eventID)
	}
	return r
}

func TestParse_SubscriptionCreated(t *testing.T) {
	body := `{
		"event_id": "evt_001",
		"event_type": "subscription.created",
		"occurred_at": "2025-01-01T00:00:00Z",
		"data": {
			"id": "sub_001",
			"status": "active",
			"customer_id": "cus_001",
			"current_billing_period": {"ends_at": "2025-02-01T00:00:00Z"},
			"custom_data": {"user_id": "u_42"},
			"items": [{"status": "active", "price": {"id": "` + testPriceBYOK + `"}}]
		}
	}`

	ev, err := Parse(requestWith(t, body, "evt_001"), []byte(body), testPrices())
	require.NoError(t, err)
	assert.Equal(t, Provider, ev.Provider)
	assert.Equal(t, "evt_001", ev.EventID)
	assert.Equal(t, "subscription_created", ev.EventName)
	assert.Equal(t, "u_42", ev.UserID)
	assert.Equal(t, "sub_001", ev.ProviderSubscriptionID)
	assert.Equal(t, "cus_001", ev.ProviderCustomerID)
	assert.Equal(t, events.TierProBYOK, ev.Tier)
	assert.Equal(t, events.StatusActive, ev.Status)
	require.NotNil(t, ev.CurrentPeriodEnd)
}

func TestParse_SubscriptionCanceled(t *testing.T) {
	body := `{
		"event_id": "evt_002",
		"event_type": "subscription.canceled",
		"occurred_at": "2025-01-15T00:00:00Z",
		"data": {"id": "sub_001", "status": "canceled", "customer_id": "cus_001", "items": []}
	}`

	ev, err := Parse(requestWith(t, body, "evt_002"), []byte(body), testPrices())
	require.NoError(t, err)
	assert.Equal(t, events.TierFree, ev.Tier)
	assert.Equal(t, events.StatusCanceled, ev.Status)
}

func TestParse_SubscriptionPastDue(t *testing.T) {
	body := `{
		"event_id": "evt_003",
		"event_type": "subscription.past_due",
		"occurred_at": "2025-01-15T00:00:00Z",
		"data": {
			"id": "sub_001",
			"status": "past_due",
			"customer_id": "cus_001",
			"items": [{"status": "past_due", "price": {"id": "` + testPriceManaged + `"}}]
		}
	}`

	ev, err := Parse(requestWith(t, body, "evt_003"), []byte(body), testPrices())
	require.NoError(t, err)
	assert.Equal(t, events.TierProManaged, ev.Tier)
	assert.Equal(t, events.StatusPastDue, ev.Status)
}

func TestParse_SubscriptionUpdatedStatusMapping(t *testing.T) {
	body := `{
		"event_id": "evt_004",
		"event_type": "subscription.updated",
		"occurred_at": "2025-01-20T00:00:00Z",
		"data": {
			"id": "sub_001",
			"status": "paused",
			"customer_id": "cus_001",
			"items": [{"status": "paused", "price": {"id": "` + testPriceBYOK + `"}}]
		}
	}`

	ev, err := Parse(requestWith(t, body, "evt_004"), []byte(body), testPrices())
	require.NoError(t, err)
	assert.Equal(t, events.TierProBYOK, ev.Tier)
	assert.Equal(t, events.StatusPaused, ev.Status)
}

func TestParse_UnsupportedEvent(t *testing.T) {
	body := `{"event_id":"e","event_type":"customer.created","data":{}}`
	_, err := Parse(requestWith(t, body, "e"), []byte(body), testPrices())
	assert.True(t, errors.Is(err, ErrUnsupportedEvent), "got %v", err)
}

func TestParse_MissingEventID(t *testing.T) {
	body := `{"event_type":"subscription.created","data":{"id":"sub","items":[],"custom_data":{"user_id":"u"}}}`
	_, err := Parse(requestWith(t, body, ""), []byte(body), testPrices())
	assert.True(t, errors.Is(err, ErrMissingEventID), "got %v", err)
}

func TestParse_MissingUserIDOnCreate(t *testing.T) {
	body := `{
		"event_id":"evt_x",
		"event_type":"subscription.created",
		"occurred_at":"2025-01-01T00:00:00Z",
		"data":{
			"id":"sub_x",
			"status":"active",
			"customer_id":"cus_x",
			"items":[{"status":"active","price":{"id":"` + testPriceBYOK + `"}}]
		}
	}`
	_, err := Parse(requestWith(t, body, "evt_x"), []byte(body), testPrices())
	assert.True(t, errors.Is(err, ErrMissingUserID), "got %v", err)
}

func TestParse_UnknownPrice(t *testing.T) {
	body := `{
		"event_id":"evt_y",
		"event_type":"subscription.created",
		"occurred_at":"2025-01-01T00:00:00Z",
		"data":{
			"id":"sub_y",
			"status":"active",
			"customer_id":"cus_y",
			"custom_data":{"user_id":"u_y"},
			"items":[{"status":"active","price":{"id":"pri_unknown"}}]
		}
	}`
	_, err := Parse(requestWith(t, body, "evt_y"), []byte(body), testPrices())
	assert.True(t, errors.Is(err, ErrUnknownPrice), "got %v", err)
}

func TestParse_InvalidJSON(t *testing.T) {
	body := `{not valid json`
	_, err := Parse(requestWith(t, body, "evt_z"), []byte(body), testPrices())
	assert.True(t, errors.Is(err, ErrInvalidPayload), "got %v", err)
}