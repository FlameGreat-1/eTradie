package store_test

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/billing/store"
)

// testPool opens a real pgx pool against the test database. Returns nil if
// BILLING_TEST_DATABASE_URL is not set; callers should t.Skip in that case.
// The pool is registered with t.Cleanup for shutdown.
func testPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	url := os.Getenv("BILLING_TEST_DATABASE_URL")
	if url == "" {
		return nil
	}
	pool, err := pgxpool.New(context.Background(), url)
	require.NoError(t, err)
	t.Cleanup(pool.Close)
	return pool
}

// setupSchema applies the auth + billing DDL so the FK constraints are
// satisfied. Idempotent.
func setupSchema(t *testing.T, pool *pgxpool.Pool) {
	t.Helper()
	ctx := context.Background()
	_, err := pool.Exec(ctx, auth.SchemaSQL())
	require.NoError(t, err)
	_, err = pool.Exec(ctx, store.SchemaSQL())
	require.NoError(t, err)
}

// truncateAll wipes the billing + auth tables between tests so each test
// sees a clean slate. ON DELETE CASCADE on billing_subscriptions.user_id
// means deleting auth_users sweeps the children.
func truncateAll(t *testing.T, pool *pgxpool.Pool) {
	t.Helper()
	ctx := context.Background()
	_, err := pool.Exec(ctx, `
		TRUNCATE TABLE
			billing_subscription_events,
			processed_webhook_events,
			billing_usage,
			billing_subscriptions,
			auth_users
		RESTART IDENTITY CASCADE
	`)
	require.NoError(t, err)
}

// seedUser creates a user the billing tables can FK against.
func seedUser(t *testing.T, pool *pgxpool.Pool, id, username, email string) {
	t.Helper()
	ctx := context.Background()
	now := time.Now().UTC()
	_, err := pool.Exec(ctx,
		`INSERT INTO auth_users (id, username, email, password_hash, role, active, created_at, updated_at)
		 VALUES ($1, $2, $3, '', 'etradie', TRUE, $4, $4)`,
		id, username, email, now,
	)
	require.NoError(t, err)
}

// withTx runs body inside a pgx.Tx and commits on success or rolls back
// on failure. Mirrors the service layer's transactional contract.
func withTx(t *testing.T, pool *pgxpool.Pool, body func(tx pgx.Tx)) {
	t.Helper()
	ctx := context.Background()
	tx, err := pool.BeginTx(ctx, pgx.TxOptions{IsoLevel: pgx.ReadCommitted})
	require.NoError(t, err)
	defer func() { _ = tx.Rollback(ctx) }()
	body(tx)
	require.NoError(t, tx.Commit(ctx))
}

func TestUpsertSubscription_InsertPath(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_insert", "insert_user", "insert@example.com")

	s := store.NewSubscriptionStore(pool)
	provider := "paddle"
	customerID := "cus_1"
	subID := "sub_1"
	periodEnd := time.Now().UTC().Add(30 * 24 * time.Hour)
	eventTS := time.Now().UTC()

	row := &store.Subscription{
		UserID:                 "u_insert",
		Tier:                   "pro_byok",
		Status:                 "active",
		PaymentProvider:        &provider,
		ProviderCustomerID:     &customerID,
		ProviderSubscriptionID: &subID,
		CurrentPeriodEnd:       &periodEnd,
		EventTimestamp:         eventTS,
	}

	withTx(t, pool, func(tx pgx.Tx) {
		applied, prevTier, prevStatus, err := s.UpsertSubscriptionTx(context.Background(), tx, row)
		require.NoError(t, err)
		assert.True(t, applied, "insert should be applied")
		assert.Equal(t, "", prevTier, "no previous tier on insert")
		assert.Equal(t, "", prevStatus, "no previous status on insert")
	})

	got, err := s.GetSubscription(context.Background(), "u_insert")
	require.NoError(t, err)
	assert.Equal(t, "pro_byok", got.Tier)
	assert.Equal(t, "active", got.Status)
}

func TestUpsertSubscription_NewerWins(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_newer", "newer_user", "newer@example.com")

	s := store.NewSubscriptionStore(pool)
	provider := "paddle"
	now := time.Now().UTC()

	// First event.
	withTx(t, pool, func(tx pgx.Tx) {
		_, _, _, err := s.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
			UserID:          "u_newer",
			Tier:            "pro_byok",
			Status:          "active",
			PaymentProvider: &provider,
			EventTimestamp:  now,
		})
		require.NoError(t, err)
	})

	// Newer event upgrades.
	withTx(t, pool, func(tx pgx.Tx) {
		applied, prevTier, prevStatus, err := s.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
			UserID:          "u_newer",
			Tier:            "pro_managed",
			Status:          "active",
			PaymentProvider: &provider,
			EventTimestamp:  now.Add(1 * time.Hour),
		})
		require.NoError(t, err)
		assert.True(t, applied)
		assert.Equal(t, "pro_byok", prevTier)
		assert.Equal(t, "active", prevStatus)
	})

	got, err := s.GetSubscription(context.Background(), "u_newer")
	require.NoError(t, err)
	assert.Equal(t, "pro_managed", got.Tier)
}

func TestUpsertSubscription_OlderDrops(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_older", "older_user", "older@example.com")

	s := store.NewSubscriptionStore(pool)
	provider := "paddle"
	now := time.Now().UTC()

	// Establish newer state first.
	withTx(t, pool, func(tx pgx.Tx) {
		_, _, _, err := s.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
			UserID:          "u_older",
			Tier:            "pro_managed",
			Status:          "active",
			PaymentProvider: &provider,
			EventTimestamp:  now,
		})
		require.NoError(t, err)
	})

	// Older event arrives late. Must NOT regress the row.
	withTx(t, pool, func(tx pgx.Tx) {
		applied, _, _, err := s.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
			UserID:          "u_older",
			Tier:            "pro_byok",
			Status:          "paused",
			PaymentProvider: &provider,
			EventTimestamp:  now.Add(-1 * time.Hour),
		})
		require.NoError(t, err)
		assert.False(t, applied, "older event must be dropped")
	})

	got, err := s.GetSubscription(context.Background(), "u_older")
	require.NoError(t, err)
	assert.Equal(t, "pro_managed", got.Tier, "row must not regress to older event")
	assert.Equal(t, "active", got.Status)
}

func TestDemoteToFreeTx_HappyPath(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_demote", "demote_user", "demote@example.com")

	s := store.NewSubscriptionStore(pool)
	provider := "paddle"
	pastPeriod := time.Now().UTC().Add(-24 * time.Hour)
	eventTS := time.Now().UTC().Add(-7 * 24 * time.Hour)

	withTx(t, pool, func(tx pgx.Tx) {
		_, _, _, err := s.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
			UserID:           "u_demote",
			Tier:             "pro_byok",
			Status:           "paused",
			PaymentProvider:  &provider,
			CurrentPeriodEnd: &pastPeriod,
			EventTimestamp:   eventTS,
		})
		require.NoError(t, err)
	})

	now := time.Now().UTC()
	withTx(t, pool, func(tx pgx.Tx) {
		applied, prevTier, prevStatus, err := s.DemoteToFreeTx(context.Background(), tx, "u_demote", now)
		require.NoError(t, err)
		assert.True(t, applied)
		assert.Equal(t, "pro_byok", prevTier)
		assert.Equal(t, "paused", prevStatus)
	})

	got, err := s.GetSubscription(context.Background(), "u_demote")
	require.NoError(t, err)
	assert.Equal(t, "free", got.Tier)
	assert.Equal(t, "canceled", got.Status)
}

func TestDemoteToFreeTx_SkipsOnNewerEvent(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_race", "race_user", "race@example.com")

	s := store.NewSubscriptionStore(pool)
	provider := "paddle"
	// The stored event is in the FUTURE relative to the reconciler's
	// proposed event_timestamp. Reconciler must lose the race.
	storedEventTS := time.Now().UTC().Add(1 * time.Hour)
	withTx(t, pool, func(tx pgx.Tx) {
		_, _, _, err := s.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
			UserID:          "u_race",
			Tier:            "pro_managed",
			Status:          "active",
			PaymentProvider: &provider,
			EventTimestamp:  storedEventTS,
		})
		require.NoError(t, err)
	})

	reconcilerTS := time.Now().UTC()
	withTx(t, pool, func(tx pgx.Tx) {
		applied, _, _, err := s.DemoteToFreeTx(context.Background(), tx, "u_race", reconcilerTS)
		require.NoError(t, err)
		assert.False(t, applied, "reconciler must lose the race against a newer event")
	})

	got, err := s.GetSubscription(context.Background(), "u_race")
	require.NoError(t, err)
	assert.Equal(t, "pro_managed", got.Tier, "newer event wins")
}

func TestListExpiredForDemotion_Filters(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)

	s := store.NewSubscriptionStore(pool)
	provider := "paddle"
	past := time.Now().UTC().Add(-1 * time.Hour)
	future := time.Now().UTC().Add(24 * time.Hour)
	eventTS := time.Now().UTC().Add(-7 * 24 * time.Hour)

	// 1) Free tier paused with elapsed period — EXCLUDED (already free).
	seedUser(t, pool, "u_free", "free_user", "free@example.com")
	withTx(t, pool, func(tx pgx.Tx) {
		_, _, _, err := s.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
			UserID: "u_free", Tier: "free", Status: "paused",
			PaymentProvider: &provider, CurrentPeriodEnd: &past, EventTimestamp: eventTS,
		})
		require.NoError(t, err)
	})

	// 2) Pro paused with NULL period_end — EXCLUDED.
	seedUser(t, pool, "u_null", "null_user", "null@example.com")
	withTx(t, pool, func(tx pgx.Tx) {
		_, _, _, err := s.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
			UserID: "u_null", Tier: "pro_byok", Status: "paused",
			PaymentProvider: &provider, CurrentPeriodEnd: nil, EventTimestamp: eventTS,
		})
		require.NoError(t, err)
	})

	// 3) Pro paused with future period_end — EXCLUDED.
	seedUser(t, pool, "u_future", "future_user", "future@example.com")
	withTx(t, pool, func(tx pgx.Tx) {
		_, _, _, err := s.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
			UserID: "u_future", Tier: "pro_byok", Status: "paused",
			PaymentProvider: &provider, CurrentPeriodEnd: &future, EventTimestamp: eventTS,
		})
		require.NoError(t, err)
	})

	// 4) Pro ACTIVE with elapsed period_end — EXCLUDED (active is not a loss status).
	seedUser(t, pool, "u_active", "active_user", "active@example.com")
	withTx(t, pool, func(tx pgx.Tx) {
		_, _, _, err := s.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
			UserID: "u_active", Tier: "pro_byok", Status: "active",
			PaymentProvider: &provider, CurrentPeriodEnd: &past, EventTimestamp: eventTS,
		})
		require.NoError(t, err)
	})

	// 5..8) Every loss status with elapsed period_end — INCLUDED.
	lossStatuses := []string{"paused", "past_due", "canceled", "refunded"}
	expected := make(map[string]bool, len(lossStatuses))
	for _, st := range lossStatuses {
		uid := "u_" + st
		expected[uid] = true
		seedUser(t, pool, uid, st+"_user", st+"@example.com")
		withTx(t, pool, func(tx pgx.Tx) {
			_, _, _, err := s.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
				UserID: uid, Tier: "pro_byok", Status: st,
				PaymentProvider: &provider, CurrentPeriodEnd: &past, EventTimestamp: eventTS,
			})
			require.NoError(t, err)
		})
	}

	now := time.Now().UTC()
	expired, err := s.ListExpiredForDemotion(context.Background(), now, 100)
	require.NoError(t, err)

	got := make(map[string]bool, len(expired))
	for _, e := range expired {
		got[e.UserID] = true
		assert.Equal(t, "pro_byok", e.Tier)
	}
	assert.Equal(t, expected, got, "only loss-status pro users with elapsed period_end should be returned")
}
