package paddle

// Payment-metadata coverage for the Paddle parser.
//
// These tests live in a separate file from parser_test.go so the
// new transaction.completed assertions stay isolated from the
// pre-existing subscription.* test bodies. They reuse the shared
// fixtures (testPriceBYOK, testPriceManaged, testPrices,
// requestWith) declared in parser_test.go since both files share
// the same internal package.

import (
	"errors"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/billing/events"
)

// TestParse_TransactionCompleted_AmountCurrencyCard exercises the
// happy path: a card-funded payment with a known price id, a
// custom_data.user_id, and a fully-populated method_details.card
// block. All seven payment-metadata fields (Amount, Currency,
// CardBrand, CardLast4, CardExpMonth, CardExpYear, plus tier
// derivation from items[].price.id) must be set.
func TestParse_TransactionCompleted_AmountCurrencyCard(t *testing.T) {
	body := `{
		"event_id": "evt_txn_001",
		"event_type": "transaction.completed",
		"occurred_at": "2025-02-01T00:00:00Z",
		"data": {
			"id": "txn_abc",
			"subscription_id": "sub_001",
			"customer_id": "cus_001",
			"currency_code": "usd",
			"custom_data": {"user_id": "u_42"},
			"details": {"totals": {"total": "1999"}},
			"items": [{"price": {"id": "` + testPriceManaged + `"}}],
			"payments": [{
				"method_details": {
					"type": "card",
					"card": {"type": "visa", "last4": "4242", "expiry_month": 12, "expiry_year": 2029}
				}
			}]
		}
	}`

	ev, err := Parse(requestWith(t, body, "evt_txn_001"), []byte(body), testPrices())
	require.NoError(t, err)

	assert.Equal(t, "transaction_completed", ev.EventName)
	assert.Equal(t, events.TierProManaged, ev.Tier, "tier resolves via price map")
	assert.Equal(t, events.StatusActive, ev.Status)
	assert.Equal(t, "u_42", ev.UserID)
	assert.Equal(t, "sub_001", ev.ProviderSubscriptionID, "transaction.subscription_id is the FK, not txn id")

	require.NotNil(t, ev.AmountCents, "AmountCents populated from details.totals.total")
	assert.Equal(t, int64(1999), *ev.AmountCents)
	require.NotNil(t, ev.Currency, "Currency populated when AmountCents present")
	assert.Equal(t, "USD", *ev.Currency, "currency_code is upper-cased")

	require.NotNil(t, ev.CardBrand)
	assert.Equal(t, "visa", *ev.CardBrand, "brand lower-cased")
	require.NotNil(t, ev.CardLast4)
	assert.Equal(t, "4242", *ev.CardLast4)
	require.NotNil(t, ev.CardExpMonth)
	assert.Equal(t, 12, *ev.CardExpMonth)
	require.NotNil(t, ev.CardExpYear)
	assert.Equal(t, 2029, *ev.CardExpYear)

	assert.Nil(t, ev.InvoiceURL, "Paddle webhooks never include a direct invoice URL")
}

// TestParse_TransactionCompleted_NonCardPaymentLeavesCardNil ensures
// a non-card payment method (PayPal, Apple Pay, etc.) does NOT pollute
// the card snapshot. The parser only reads from
// method_details.card when method_details.type == 'card'; for any
// other type, CardBrand/CardLast4/CardExp* stay nil so the previously
// stored snapshot on billing_subscriptions remains the current truth.
func TestParse_TransactionCompleted_NonCardPaymentLeavesCardNil(t *testing.T) {
	body := `{
		"event_id": "evt_txn_pp",
		"event_type": "transaction.completed",
		"occurred_at": "2025-02-01T00:00:00Z",
		"data": {
			"id": "txn_pp",
			"subscription_id": "sub_001",
			"customer_id": "cus_001",
			"currency_code": "EUR",
			"custom_data": {"user_id": "u_42"},
			"details": {"totals": {"total": "500"}},
			"items": [{"price": {"id": "` + testPriceBYOK + `"}}],
			"payments": [{"method_details": {"type": "paypal"}}]
		}
	}`

	ev, err := Parse(requestWith(t, body, "evt_txn_pp"), []byte(body), testPrices())
	require.NoError(t, err)
	assert.Nil(t, ev.CardBrand, "non-card payment must not surface a brand")
	assert.Nil(t, ev.CardLast4)
	assert.Nil(t, ev.CardExpMonth)
	assert.Nil(t, ev.CardExpYear)
	require.NotNil(t, ev.AmountCents)
	assert.Equal(t, int64(500), *ev.AmountCents)
}

// TestParse_TransactionCompleted_RejectedWithoutCorrelationKey covers
// the orphan-payment defence. A transaction.completed that carries
// neither custom_data.user_id NOR a subscription_id cannot be
// attached to any platform account; the parser rejects with
// ErrMissingUserID rather than silently dropping the audit row.
func TestParse_TransactionCompleted_RejectedWithoutCorrelationKey(t *testing.T) {
	body := `{
		"event_id": "evt_orphan",
		"event_type": "transaction.completed",
		"occurred_at": "2025-02-01T00:00:00Z",
		"data": {
			"id": "txn_orphan",
			"customer_id": "cus_orphan",
			"currency_code": "USD",
			"details": {"totals": {"total": "100"}},
			"items": []
		}
	}`
	_, err := Parse(requestWith(t, body, "evt_orphan"), []byte(body), testPrices())
	assert.True(t, errors.Is(err, ErrMissingUserID), "got %v", err)
}

// TestParse_TransactionCompleted_MalformedAmountKeepsEventValid
// guards against a regression where an unparseable totals.total
// string would fail the whole event. The parser must keep the
// event valid (tier/status/user still flow through) and simply
// leave AmountCents and Currency nil so the SPA renders the dash
// fallback on that row rather than the whole feed 5xx-ing.
func TestParse_TransactionCompleted_MalformedAmountKeepsEventValid(t *testing.T) {
	body := `{
		"event_id": "evt_bad_amount",
		"event_type": "transaction.completed",
		"occurred_at": "2025-02-01T00:00:00Z",
		"data": {
			"id": "txn_bad",
			"subscription_id": "sub_001",
			"customer_id": "cus_001",
			"currency_code": "USD",
			"custom_data": {"user_id": "u_42"},
			"details": {"totals": {"total": "not-a-number"}},
			"items": [{"price": {"id": "` + testPriceManaged + `"}}]
		}
	}`
	ev, err := Parse(requestWith(t, body, "evt_bad_amount"), []byte(body), testPrices())
	require.NoError(t, err)
	assert.Nil(t, ev.AmountCents, "unparseable total leaves AmountCents nil")
	assert.Nil(t, ev.Currency, "Currency requires AmountCents to be non-nil")
	assert.Equal(t, events.TierProManaged, ev.Tier, "tier still resolves from items[].price.id")
	assert.Equal(t, events.StatusActive, ev.Status)
}
