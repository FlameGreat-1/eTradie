package store

import (
	"context"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ErrSubscriptionNotFound is returned by GetSubscription when no row exists
// for the given user. Callers should treat this as "user is on the default
// free tier" — distinct from any other DB error which must surface as 5xx.
var ErrSubscriptionNotFound = errors.New("billing: subscription not found")

// SubscriptionStore reads and writes the canonical billing_subscriptions table.
// All write paths are race-safe: an update is only applied if the incoming
// event_timestamp is at least as recent as the stored one. Out-of-order
// webhook delivery cannot regress newer state.
type SubscriptionStore struct {
	db *pgxpool.Pool
}

func NewSubscriptionStore(db *pgxpool.Pool) *SubscriptionStore {
	return &SubscriptionStore{db: db}
}

// Pool exposes the underlying pool so the service layer can run a multi-statement
// transaction (idempotency check + subscription update + audit insert) atomically.
func (s *SubscriptionStore) Pool() *pgxpool.Pool { return s.db }

type Subscription struct {
	UserID                 string     `json:"user_id"`
	Tier                   string     `json:"tier"`
	Status                 string     `json:"status"`
	PaymentProvider        *string    `json:"payment_provider"`
	ProviderCustomerID     *string    `json:"provider_customer_id"`
	ProviderSubscriptionID *string    `json:"provider_subscription_id"`
	CurrentPeriodEnd       *time.Time `json:"current_period_end"`
	EventTimestamp         time.Time  `json:"event_timestamp"`
	CreatedAt              time.Time  `json:"created_at"`
	UpdatedAt              time.Time  `json:"updated_at"`
}

const subscriptionColumns = `
	user_id, tier, status,
	payment_provider, provider_customer_id, provider_subscription_id,
	current_period_end, event_timestamp, created_at, updated_at
`

func scanSubscription(row pgx.Row) (*Subscription, error) {
	var sub Subscription
	err := row.Scan(
		&sub.UserID, &sub.Tier, &sub.Status,
		&sub.PaymentProvider, &sub.ProviderCustomerID, &sub.ProviderSubscriptionID,
		&sub.CurrentPeriodEnd, &sub.EventTimestamp, &sub.CreatedAt, &sub.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrSubscriptionNotFound
		}
		return nil, err
	}
	return &sub, nil
}

// GetSubscription returns the subscription row for the given user.
// Returns ErrSubscriptionNotFound when no row exists; any other error is a
// genuine infrastructure failure and must be surfaced as 5xx by callers.
func (s *SubscriptionStore) GetSubscription(ctx context.Context, userID string) (*Subscription, error) {
	query := `SELECT ` + subscriptionColumns + ` FROM billing_subscriptions WHERE user_id = $1`
	return scanSubscription(s.db.QueryRow(ctx, query, userID))
}

// GetByProviderSubscriptionID looks a subscription up by provider-issued
// subscription ID. Used by webhook handlers when the event payload identifies
// the subscription but not the platform user_id directly.
func (s *SubscriptionStore) GetByProviderSubscriptionID(
	ctx context.Context, provider, providerSubscriptionID string,
) (*Subscription, error) {
	query := `
		SELECT ` + subscriptionColumns + `
		FROM billing_subscriptions
		WHERE payment_provider = $1 AND provider_subscription_id = $2
	`
	return scanSubscription(s.db.QueryRow(ctx, query, provider, providerSubscriptionID))
}

// UpsertSubscriptionTx applies a subscription change inside an existing
// transaction. The update is race-safe: it only takes effect when the
// incoming event_timestamp is greater than or equal to the stored one,
// so a delayed older event cannot overwrite newer state.
//
// Returns (applied, previousTier, previousStatus, error):
//   - applied=true  → row was inserted or updated; previous_* reflect the
//     row state before the change ("","" on insert).
//   - applied=false → a newer event_timestamp already exists; the caller's
//     event was older and was discarded as expected.
func (s *SubscriptionStore) UpsertSubscriptionTx(
	ctx context.Context, tx pgx.Tx, sub *Subscription,
) (applied bool, previousTier, previousStatus string, err error) {
	query := `
		WITH prev AS (
			SELECT tier, status, event_timestamp
			FROM billing_subscriptions
			WHERE user_id = $1
		),
		up AS (
			INSERT INTO billing_subscriptions (
				user_id, tier, status,
				payment_provider, provider_customer_id, provider_subscription_id,
				current_period_end, event_timestamp, updated_at
			) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
			ON CONFLICT (user_id) DO UPDATE SET
				tier                     = EXCLUDED.tier,
				status                   = EXCLUDED.status,
				payment_provider         = EXCLUDED.payment_provider,
				provider_customer_id     = EXCLUDED.provider_customer_id,
				provider_subscription_id = EXCLUDED.provider_subscription_id,
				current_period_end       = EXCLUDED.current_period_end,
				event_timestamp          = EXCLUDED.event_timestamp,
				updated_at               = NOW()
			WHERE billing_subscriptions.event_timestamp <= EXCLUDED.event_timestamp
			RETURNING 1
		)
		SELECT
			(SELECT COUNT(*) FROM up) AS applied,
			COALESCE((SELECT tier   FROM prev), '') AS prev_tier,
			COALESCE((SELECT status FROM prev), '') AS prev_status
	`
	var appliedCount int
	err = tx.QueryRow(ctx, query,
		sub.UserID, sub.Tier, sub.Status,
		sub.PaymentProvider, sub.ProviderCustomerID, sub.ProviderSubscriptionID,
		sub.CurrentPeriodEnd, sub.EventTimestamp,
	).Scan(&appliedCount, &previousTier, &previousStatus)
	if err != nil {
		return false, "", "", err
	}
	return appliedCount > 0, previousTier, previousStatus, nil
}
