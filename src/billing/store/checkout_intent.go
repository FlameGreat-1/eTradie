// Checkout idempotency.
//
// A double-click on the "Upgrade" button or a browser navigation race
// (back/forward + retry) can produce two POSTs to /internal/checkout
// with the same (user_id, provider, tier) tuple within milliseconds.
// Without an idempotency guard, both calls reach Paddle or Lemon
// Squeezy and the provider creates two checkout sessions for the same
// customer. If both complete (the user finishes one, navigates back,
// finishes the other), the customer is billed twice and the platform
// ends up with two `billing_subscriptions` rows fighting over the
// race-safe upsert.
//
// CheckoutIntentStore caches the provider-issued checkout URL keyed
// by (user_id, provider, tier) for a short window (5 minutes by
// default). Repeat requests within the window get the SAME URL so
// the user always lands on the same provider checkout page; the
// provider's own idempotency takes over from there.
//
// The window is chosen to balance:
//   - long enough to defeat any realistic double-click / navigation
//     race (browsers retry on user-driven actions within seconds);
//   - short enough that a legitimate "I changed my mind, let me
//     upgrade to the OTHER tier" doesn't get locked out (a tier
//     change is a different cache key, so this is not an issue;
//     only identical (user, provider, tier) is locked).
package store

import (
	"context"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// DefaultCheckoutIntentTTL is the window during which a (user, provider,
// tier) tuple returns the same cached checkout URL.
const DefaultCheckoutIntentTTL = 5 * time.Minute

// ErrCheckoutIntentNotFound signals the lookup found no row OR found an
// expired one. Callers MUST treat this as the cache-miss path (no replay
// possible); distinguishing it from a real DB error is what lets the
// service safely fall through to the provider API.
var ErrCheckoutIntentNotFound = errors.New("billing: checkout intent not found")

// CheckoutIntent is the row written by Record and read by Get.
type CheckoutIntent struct {
	UserID      string
	Provider    string
	Tier        string
	CheckoutURL string
	ExpiresAt   time.Time
}

// CheckoutIntentStore reads and writes billing_checkout_intents.
// Safe for concurrent use after construction.
type CheckoutIntentStore struct {
	db *pgxpool.Pool
}

// NewCheckoutIntentStore builds a store bound to the supplied pool.
func NewCheckoutIntentStore(db *pgxpool.Pool) *CheckoutIntentStore {
	return &CheckoutIntentStore{db: db}
}

// Get returns the cached intent for (user, provider, tier) if one
// exists AND is still fresh. Expired rows are treated as cache misses;
// the reconciler janitor deletes them on its next tick. Returns
// ErrCheckoutIntentNotFound on miss.
func (s *CheckoutIntentStore) Get(
	ctx context.Context, userID, provider, tier string,
) (*CheckoutIntent, error) {
	var out CheckoutIntent
	err := s.db.QueryRow(ctx, `
SELECT user_id, provider, tier, checkout_url, expires_at
FROM   billing_checkout_intents
WHERE  user_id = $1
  AND  provider = $2
  AND  tier     = $3
  AND  expires_at > NOW()
`, userID, provider, tier).Scan(
		&out.UserID, &out.Provider, &out.Tier,
		&out.CheckoutURL, &out.ExpiresAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrCheckoutIntentNotFound
		}
		return nil, err
	}
	return &out, nil
}

// Record upserts the intent. ON CONFLICT makes a retry of the same
// (user, provider, tier) within the window race-safe at the DB level:
// the second caller's URL wins, but the first caller's URL was
// returned to the user already so they remain on the same page.
func (s *CheckoutIntentStore) Record(ctx context.Context, intent *CheckoutIntent) error {
	_, err := s.db.Exec(ctx, `
INSERT INTO billing_checkout_intents (user_id, provider, tier, checkout_url, expires_at)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (user_id, provider, tier) DO UPDATE
   SET checkout_url = EXCLUDED.checkout_url,
       expires_at   = EXCLUDED.expires_at
`, intent.UserID, intent.Provider, intent.Tier, intent.CheckoutURL, intent.ExpiresAt)
	return err
}

// PruneExpired deletes intents whose expires_at has elapsed. Called by
// the existing billing reconciler janitor; pure maintenance.
func (s *CheckoutIntentStore) PruneExpired(ctx context.Context) (int64, error) {
	tag, err := s.db.Exec(ctx,
		`DELETE FROM billing_checkout_intents WHERE expires_at < NOW()`)
	if err != nil {
		return 0, err
	}
	return tag.RowsAffected(), nil
}
