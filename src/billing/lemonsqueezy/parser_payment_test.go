package lemonsqueezy

// Payment-metadata coverage for the Lemon Squeezy parser.
//
// These tests live in a separate file from parser_test.go so the
// new invoice-resource assertions stay isolated from the
// pre-existing subscription-resource test bodies. They reuse the
// shared fixtures (testVariantBYOK, testVariantManaged,
// testVariants, reqWithEvent) declared in parser_test.go since
// both files share the same internal package.
//
// What is verified:
//   - subscription_created surfaces card snapshot from the
//     subscription resource (LS mirrors the latest card onto the
//     subscription so Payment Methods works on first webhook),
//   - subscription_payment_success surfaces amount + currency +
//     invoice_url AND overrides ProviderSubscriptionID with
//     attributes.subscription_id (data.id is the invoice id, not
//     the subscription id, on invoice-resource events),
//   - subscription_payment_refunded prefers refunded_amount over
//     total when refunded=true, keeping the audit row honest about
//     money moved BACK to the customer,
//   - subscription_payment_failed still surfaces the attempted total
//     so the Invoice History row can render an amount with the
//     failed-payment styling.

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/billing/events"
)

func TestLSParse_SubscriptionCreated_CardSnapshot(t *testing.T) {
	body := `{
		"meta": {"event_name": "subscription_created", "event_id": "ev_card_1", "custom_data": {"user_id": "u_42"}},
		"data": {
			"type": "subscriptions",
			"id": "77",
			"attributes": {
				"store_id": 1, "customer_id": 555,
				"variant_id": ` + testVariantManaged + `,
				"status": "active",
				"renews_at": "2025-02-01T00:00:00Z",
				"created_at": "2025-01-01T00:00:00Z",
				"updated_at": "2025-01-01T00:00:00Z",
				"card_brand": "Mastercard",
				"card_last_four": "5454"
			}
		}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_created"), []byte(body), testVariants())
	require.NoError(t, err)
	require.NotNil(t, ev.CardBrand, "subscription_created must surface card snapshot when LS provides it")
	assert.Equal(t, "mastercard", *ev.CardBrand, "brand lower-cased")
	require.NotNil(t, ev.CardLast4)
	assert.Equal(t, "5454", *ev.CardLast4)
	assert.Nil(t, ev.AmountCents, "subscription state events carry no money")
	assert.Nil(t, ev.Currency)
	assert.Nil(t, ev.InvoiceURL)
}

func TestLSParse_PaymentSuccess_AmountCurrencyInvoiceURL(t *testing.T) {
	body := `{
		"meta": {"event_name": "subscription_payment_success", "event_id": "ev_pay_1", "custom_data": {"user_id": "u_42"}},
		"data": {
			"type": "subscription-invoices",
			"id": "inv_99",
			"attributes": {
				"store_id": 1,
				"customer_id": 555,
				"variant_id": ` + testVariantManaged + `,
				"subscription_id": 77,
				"status": "paid",
				"currency": "usd",
				"total": 2999,
				"created_at": "2025-01-01T00:00:00Z",
				"updated_at": "2025-02-01T00:00:00Z",
				"card_brand": "visa",
				"card_last_four": "4242",
				"urls": {"invoice_url": "https://app.lemonsqueezy.com/my-orders/inv_99"}
			}
		}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_payment_success"), []byte(body), testVariants())
	require.NoError(t, err)

	assert.Equal(t, events.TierProManaged, ev.Tier)
	assert.Equal(t, events.StatusActive, ev.Status)
	assert.Equal(t, "77", ev.ProviderSubscriptionID,
		"invoice events must surface the SUBSCRIPTION id, not the invoice id, as the FK")

	require.NotNil(t, ev.AmountCents)
	assert.Equal(t, int64(2999), *ev.AmountCents)
	require.NotNil(t, ev.Currency)
	assert.Equal(t, "USD", *ev.Currency, "currency upper-cased")
	require.NotNil(t, ev.InvoiceURL)
	assert.Equal(t, "https://app.lemonsqueezy.com/my-orders/inv_99", *ev.InvoiceURL)

	require.NotNil(t, ev.CardBrand)
	assert.Equal(t, "visa", *ev.CardBrand)
	require.NotNil(t, ev.CardLast4)
	assert.Equal(t, "4242", *ev.CardLast4)
}

func TestLSParse_PaymentRefunded_UsesRefundedAmount(t *testing.T) {
	body := `{
		"meta": {"event_name": "subscription_payment_refunded", "event_id": "ev_refund_1", "custom_data": {"user_id": "u_42"}},
		"data": {
			"type": "subscription-invoices",
			"id": "inv_100",
			"attributes": {
				"store_id": 1, "customer_id": 555,
				"variant_id": ` + testVariantManaged + `,
				"subscription_id": 77,
				"status": "refunded",
				"currency": "USD",
				"total": 2999,
				"refunded": true,
				"refunded_amount": 1500,
				"created_at": "2025-01-01T00:00:00Z",
				"updated_at": "2025-02-15T00:00:00Z",
				"urls": {"invoice_url": "https://app.lemonsqueezy.com/my-orders/inv_100"}
			}
		}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_payment_refunded"), []byte(body), testVariants())
	require.NoError(t, err)

	assert.Equal(t, events.TierProManaged, ev.Tier, "refund must keep variant-derived tier")
	assert.Equal(t, events.StatusRefunded, ev.Status)
	assert.Equal(t, "77", ev.ProviderSubscriptionID)

	require.NotNil(t, ev.AmountCents, "refund event surfaces an amount")
	assert.Equal(t, int64(1500), *ev.AmountCents,
		"refunded_amount must take precedence over total on refund events")
	require.NotNil(t, ev.Currency)
	assert.Equal(t, "USD", *ev.Currency)
	require.NotNil(t, ev.InvoiceURL)
}

func TestLSParse_PaymentFailed_SurfacesAttemptedAmount(t *testing.T) {
	body := `{
		"meta": {"event_name": "subscription_payment_failed", "event_id": "ev_fail_1", "custom_data": {"user_id": "u_42"}},
		"data": {
			"type": "subscription-invoices",
			"id": "inv_101",
			"attributes": {
				"store_id": 1, "customer_id": 555,
				"variant_id": ` + testVariantBYOK + `,
				"subscription_id": 77,
				"status": "past_due",
				"currency": "EUR",
				"total": 999,
				"created_at": "2025-01-01T00:00:00Z",
				"updated_at": "2025-01-25T00:00:00Z"
			}
		}
	}`
	ev, err := Parse(reqWithEvent(t, body, "subscription_payment_failed"), []byte(body), testVariants())
	require.NoError(t, err)
	assert.Equal(t, events.StatusPastDue, ev.Status)
	require.NotNil(t, ev.AmountCents)
	assert.Equal(t, int64(999), *ev.AmountCents)
	require.NotNil(t, ev.Currency)
	assert.Equal(t, "EUR", *ev.Currency)
}
