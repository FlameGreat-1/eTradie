package store

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type SubscriptionStore struct {
	db *pgxpool.Pool
}

func NewSubscriptionStore(db *pgxpool.Pool) *SubscriptionStore {
	return &SubscriptionStore{db: db}
}

type Subscription struct {
	UserID                 string    `json:"user_id"`
	Tier                   string    `json:"tier"`
	Status                 string    `json:"status"`
	PaymentProvider        *string   `json:"payment_provider"`
	ProviderCustomerID     *string   `json:"provider_customer_id"`
	ProviderSubscriptionID *string   `json:"provider_subscription_id"`
	CurrentPeriodEnd       *time.Time `json:"current_period_end"`
	CreatedAt              time.Time `json:"created_at"`
	UpdatedAt              time.Time `json:"updated_at"`
}

func (s *SubscriptionStore) GetSubscription(ctx context.Context, userID string) (*Subscription, error) {
	query := `
		SELECT user_id, tier, status, payment_provider, provider_customer_id, provider_subscription_id, current_period_end, created_at, updated_at
		FROM billing_subscriptions
		WHERE user_id = $1
	`
	var sub Subscription
	err := s.db.QueryRow(ctx, query, userID).Scan(
		&sub.UserID, &sub.Tier, &sub.Status, &sub.PaymentProvider, &sub.ProviderCustomerID, &sub.ProviderSubscriptionID, &sub.CurrentPeriodEnd, &sub.CreatedAt, &sub.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	return &sub, nil
}

func (s *SubscriptionStore) UpdateSubscription(ctx context.Context, sub *Subscription) error {
	query := `
		INSERT INTO billing_subscriptions (
			user_id, tier, status, payment_provider, provider_customer_id, provider_subscription_id, current_period_end, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
		ON CONFLICT (user_id) DO UPDATE SET
			tier = EXCLUDED.tier,
			status = EXCLUDED.status,
			payment_provider = EXCLUDED.payment_provider,
			provider_customer_id = EXCLUDED.provider_customer_id,
			provider_subscription_id = EXCLUDED.provider_subscription_id,
			current_period_end = EXCLUDED.current_period_end,
			updated_at = NOW()
	`
	_, err := s.db.Exec(ctx, query,
		sub.UserID, sub.Tier, sub.Status, sub.PaymentProvider, sub.ProviderCustomerID, sub.ProviderSubscriptionID, sub.CurrentPeriodEnd,
	)
	return err
}
