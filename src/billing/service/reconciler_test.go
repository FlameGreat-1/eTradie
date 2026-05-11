package service_test

import (
	"context"
	"sort"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/billing/service"
	"github.com/flamegreat-1/etradie/src/billing/store"
)

// buildReconciler returns a Reconciler wired against the real stores plus
// a recordingRevoker so tests can assert revocation behaviour without
// touching auth_sessions.
func buildReconciler(t *testing.T, pool *pgxpool.Pool, retentionDays int) (*service.Reconciler, *recordingRevoker, *store.SubscriptionStore, *store.ProcessedEventStore) {
	t.Helper()
	subs := store.NewSubscriptionStore(pool)
	processed := store.NewProcessedEventStore(pool)
	audit := store.NewSubscriptionEventStore(pool)
	revoker := &recordingRevoker{}
	r, err := service.NewReconciler(
		subs, processed, audit, revoker,
		service.NoopReconcilerMetrics{},
		zerolog.Nop(),
		service.ReconcilerConfig{
			Interval:                 1 * time.Hour, // not exercised; we call runOnce indirectly
			IdempotencyRetentionDays: retentionDays,
		},
	)
	require.NoError(t, err)
	return r, revoker, subs, processed
}

// runOnceViaContext exercises the reconciler's per-tick logic. The Run loop
// runs a sweep + prune immediately before its ticker fires, so a context
// cancelled after a brief sleep gives us a single full tick.
func runOnceViaContext(t *testing.T, r *service.Reconciler) {
	t.Helper()
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		r.Run(ctx)
		close(done)
	}()
	// The reconciler does its immediate runOnce synchronously before the
	// first ticker fire. 200ms is more than enough for the sweep + prune
	// to finish against a local DB; if it isn't, the test fails clearly
	// rather than hanging.
	time.Sleep(200 * time.Millisecond)
	cancel()
	select {
	case <-done:
	case <-time.After(5 * time.Second):
		t.Fatal("reconciler did not exit after context cancellation")
	}
}

func TestReconciler_DemotesOnlyExpiredLossStatus(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)

	provider := "paddle"
	past := time.Now().UTC().Add(-1 * time.Hour)
	future := time.Now().UTC().Add(24 * time.Hour)
	eventTS := time.Now().UTC().Add(-7 * 24 * time.Hour)

	type fixture struct {
		uid          string
		tier, status string
		periodEnd    *time.Time
		shouldDemote bool
	}
	fixtures := []fixture{
		{"u_paused_pro", "pro_byok", "paused", &past, true},
		{"u_canceled_pro", "pro_managed", "canceled", &past, true},
		{"u_refunded_pro", "pro_byok", "refunded", &past, true},
		{"u_active_pro", "pro_byok", "active", &past, false},
		{"u_paused_future", "pro_byok", "paused", &future, false},
	}

	subsStore := store.NewSubscriptionStore(pool)
	for _, f := range fixtures {
		seedUser(t, pool, f.uid, f.uid+"_n", f.uid+"@example.com")
		tx, err := pool.Begin(context.Background())
		require.NoError(t, err)
		_, _, _, err = subsStore.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
			UserID: f.uid, Tier: f.tier, Status: f.status,
			PaymentProvider: &provider, CurrentPeriodEnd: f.periodEnd, EventTimestamp: eventTS,
		})
		require.NoError(t, err)
		require.NoError(t, tx.Commit(context.Background()))
	}

	r, revoker, _, _ := buildReconciler(t, pool, 30)
	runOnceViaContext(t, r)

	// Assert per-user row state.
	var expectedDemoted []string
	for _, f := range fixtures {
		sub, err := subsStore.GetSubscription(context.Background(), f.uid)
		require.NoError(t, err, "user %s row should exist", f.uid)
		if f.shouldDemote {
			assert.Equal(t, "free", sub.Tier, "user %s should be demoted", f.uid)
			assert.Equal(t, "canceled", sub.Status, "user %s should be canceled", f.uid)
			expectedDemoted = append(expectedDemoted, f.uid)
		} else {
			assert.Equal(t, f.tier, sub.Tier, "user %s must NOT be demoted", f.uid)
			assert.Equal(t, f.status, sub.Status, "user %s status unchanged", f.uid)
		}
	}

	// Audit table: one row per demotion, with the right previous_tier.
	rows, err := pool.Query(context.Background(),
		`SELECT user_id, previous_tier, new_tier, new_status, provider, event_name
		 FROM billing_subscription_events
		 WHERE provider = 'reconciler'`)
	require.NoError(t, err)
	defer rows.Close()
	gotAudit := map[string]string{} // user_id -> previous_tier
	for rows.Next() {
		var uid, prevTier, newTier, newStatus, prov, name string
		require.NoError(t, rows.Scan(&uid, &prevTier, &newTier, &newStatus, &prov, &name))
		assert.Equal(t, "free", newTier)
		assert.Equal(t, "canceled", newStatus)
		assert.Equal(t, "reconciler", prov)
		assert.Equal(t, "reconciler.period_end_expired", name)
		gotAudit[uid] = prevTier
	}
	assert.Equal(t, "pro_byok", gotAudit["u_paused_pro"])
	assert.Equal(t, "pro_managed", gotAudit["u_canceled_pro"])
	assert.Equal(t, "pro_byok", gotAudit["u_refunded_pro"])
	assert.Len(t, gotAudit, len(expectedDemoted))

	// Revoker was called exactly for the demoted users.
	calls := revoker.snapshot()
	sort.Strings(calls)
	sort.Strings(expectedDemoted)
	assert.Equal(t, expectedDemoted, calls, "revoker called for demoted users only")
}

func TestReconciler_PrunesIdempotency(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)

	ctx := context.Background()
	now := time.Now().UTC()
	old := now.Add(-31 * 24 * time.Hour)
	recent := now.Add(-1 * 24 * time.Hour)

	// Insert rows directly (PruneOlderThan doesn't go through MarkProcessedTx).
	_, err := pool.Exec(ctx,
		`INSERT INTO processed_webhook_events (provider, event_id, event_name, received_at)
		 VALUES ('paddle','e_old_1','subscription_created',$1),
		        ('paddle','e_old_2','subscription_updated',$1),
		        ('paddle','e_recent_1','subscription_created',$2)`,
		old, recent)
	require.NoError(t, err)

	r, _, _, _ := buildReconciler(t, pool, 30) // cutoff = now - 30 days
	runOnceViaContext(t, r)

	var n int
	require.NoError(t, pool.QueryRow(ctx,
		`SELECT COUNT(*) FROM processed_webhook_events`,
	).Scan(&n))
	assert.Equal(t, 1, n, "only the recent row should survive a 30-day cutoff")

	var surviving string
	require.NoError(t, pool.QueryRow(ctx,
		`SELECT event_id FROM processed_webhook_events`,
	).Scan(&surviving))
	assert.Equal(t, "e_recent_1", surviving)
}

func TestReconciler_IsIdempotent(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)

	provider := "paddle"
	past := time.Now().UTC().Add(-1 * time.Hour)
	eventTS := time.Now().UTC().Add(-7 * 24 * time.Hour)

	seedUser(t, pool, "u_once", "once_user", "once@example.com")
	subsStore := store.NewSubscriptionStore(pool)
	tx, err := pool.Begin(context.Background())
	require.NoError(t, err)
	_, _, _, err = subsStore.UpsertSubscriptionTx(context.Background(), tx, &store.Subscription{
		UserID: "u_once", Tier: "pro_byok", Status: "paused",
		PaymentProvider: &provider, CurrentPeriodEnd: &past, EventTimestamp: eventTS,
	})
	require.NoError(t, err)
	require.NoError(t, tx.Commit(context.Background()))

	r, revoker, _, _ := buildReconciler(t, pool, 30)
	runOnceViaContext(t, r)

	// Second run should find nothing to do.
	runOnceViaContext(t, r)

	sub, err := subsStore.GetSubscription(context.Background(), "u_once")
	require.NoError(t, err)
	assert.Equal(t, "free", sub.Tier)

	var auditCount int
	require.NoError(t, pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM billing_subscription_events WHERE user_id = 'u_once'`,
	).Scan(&auditCount))
	assert.Equal(t, 1, auditCount, "only one demotion audit row even after two runs")

	assert.Equal(t, []string{"u_once"}, revoker.snapshot(), "revoker called exactly once")
}
