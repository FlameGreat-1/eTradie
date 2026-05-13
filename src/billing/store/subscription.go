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

// ExpiredSubscription is the projection returned by ListExpiredForDemotion.
// The reconciler only needs the user id (to demote and revoke sessions),
// the current tier and status (for the audit row that gets appended on
// demotion), and the provider/subscription id pair (to surface in logs
// when a demotion fires so operators can correlate against the provider
// dashboard).
type ExpiredSubscription struct {
	UserID                 string
	Tier                   string
	Status                 string
	Provider               string
	ProviderSubscriptionID string
	CurrentPeriodEnd       time.Time
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
// Returns (applied, previousTier, previousStatus, previousPeriodEnd, error):
//   - applied=true  → row was inserted or updated; previous_* reflect the
//     row state before the change ("", "", nil on insert).
//   - applied=false → a newer event_timestamp already exists; the caller's
//     event was older and was discarded as expected.
//
// previousPeriodEnd is the pre-change current_period_end (nil when there
// was no prior row or the prior row had a NULL period_end). The service
// layer compares it against the incoming CurrentPeriodEnd to detect
// renewals so it can fire side effects scoped to billing-cycle
// rollovers (e.g. UsageStore.MonthlyReset for the LLM token quota).
func (s *SubscriptionStore) UpsertSubscriptionTx(
	ctx context.Context, tx pgx.Tx, sub *Subscription,
) (applied bool, previousTier, previousStatus string, previousPeriodEnd *time.Time, err error) {
	query := `
		WITH prev AS (
			SELECT tier, status, current_period_end, event_timestamp
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
			COALESCE((SELECT status FROM prev), '') AS prev_status,
			(SELECT current_period_end FROM prev) AS prev_period_end
	`
	var appliedCount int
	err = tx.QueryRow(ctx, query,
		sub.UserID, sub.Tier, sub.Status,
		sub.PaymentProvider, sub.ProviderCustomerID, sub.ProviderSubscriptionID,
		sub.CurrentPeriodEnd, sub.EventTimestamp,
	).Scan(&appliedCount, &previousTier, &previousStatus, &previousPeriodEnd)
	if err != nil {
		return false, "", "", nil, err
	}
	return appliedCount > 0, previousTier, previousStatus, previousPeriodEnd, nil
}

// ListExpiredForDemotion returns subscriptions in a tentative-loss status
// (paused, past_due, canceled, refunded) whose current_period_end has
// elapsed. These users have lost entitlement to their Pro tier but the
// system has not yet recorded the downgrade because no fresh provider
// event has arrived (e.g. Paddle subscription.paused with no follow-up
// subscription.canceled; a refund with no subsequent cancellation event).
//
// Rows with NULL current_period_end are deliberately excluded — without a
// known end-date we cannot prove the user has lost entitlement, and the
// next webhook will clarify. The limit parameter bounds the result set
// so the reconciler can process under load in fixed-size chunks.
func (s *SubscriptionStore) ListExpiredForDemotion(
	ctx context.Context, now time.Time, limit int,
) ([]ExpiredSubscription, error) {
	if limit <= 0 {
		limit = 100
	}
	const query = `
		SELECT user_id, tier, status,
		       COALESCE(payment_provider, ''),
		       COALESCE(provider_subscription_id, ''),
		       current_period_end
		FROM billing_subscriptions
		WHERE status IN ('paused', 'past_due', 'canceled', 'refunded')
		  AND current_period_end IS NOT NULL
		  AND current_period_end < $1
		  AND tier <> 'free'
		ORDER BY current_period_end ASC
		LIMIT $2
	`
	rows, err := s.db.Query(ctx, query, now, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []ExpiredSubscription
	for rows.Next() {
		var e ExpiredSubscription
		if err := rows.Scan(
			&e.UserID, &e.Tier, &e.Status,
			&e.Provider, &e.ProviderSubscriptionID, &e.CurrentPeriodEnd,
		); err != nil {
			return nil, err
		}
		out = append(out, e)
	}
	return out, rows.Err()
}

// DemoteToFreeTx flips a user's subscription to (tier=free, status=canceled)
// inside the supplied transaction. The reconciler calls this when it
// determines a subscription has lost entitlement via ListExpiredForDemotion.
//
// The implementation reuses the same race-safe single-statement CTE as
// UpsertSubscriptionTx: the UPDATE only takes effect if eventTimestamp is
// greater than or equal to the row's stored event_timestamp. Callers pass
// time.Now().UTC() so the demotion beats every older stored event but loses
// to any genuinely-newer webhook arriving concurrently — exactly the
// desired behaviour (a re-subscribe event that arrives at the same time
// must not be overwritten by the reaper).
//
// payment_provider, provider_customer_id, provider_subscription_id, and
// current_period_end are deliberately preserved (the historical link
// to the provider remains in the audit trail). Only tier and status flip.
//
// Returns (applied, previousTier, previousStatus, error). applied=false
// means a newer event_timestamp already exists — the reconciler should
// log and move on.
func (s *SubscriptionStore) DemoteToFreeTx(
	ctx context.Context, tx pgx.Tx, userID string, eventTimestamp time.Time,
) (applied bool, previousTier, previousStatus string, err error) {
	const query = `
		WITH prev AS (
			SELECT tier, status, event_timestamp
			FROM billing_subscriptions
			WHERE user_id = $1
		),
		up AS (
			UPDATE billing_subscriptions
			SET tier            = 'free',
			    status          = 'canceled',
			    event_timestamp = $2,
			    updated_at      = NOW()
			WHERE user_id = $1
			  AND event_timestamp <= $2
			RETURNING 1
		)
		SELECT
			(SELECT COUNT(*) FROM up) AS applied,
			COALESCE((SELECT tier   FROM prev), '') AS prev_tier,
			COALESCE((SELECT status FROM prev), '') AS prev_status
	`
	var appliedCount int
	err = tx.QueryRow(ctx, query, userID, eventTimestamp).
		Scan(&appliedCount, &previousTier, &previousStatus)
	if err != nil {
		return false, "", "", err
	}
	return appliedCount > 0, previousTier, previousStatus, nil
}
