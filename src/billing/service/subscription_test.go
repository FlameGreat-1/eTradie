package service_test

import (
	"context"
	"os"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/billing/events"
	"github.com/flamegreat-1/etradie/src/billing/service"
	"github.com/flamegreat-1/etradie/src/billing/store"
)

// recordingRevoker captures the user IDs passed to RevokeAllUserSessions so
// the test can assert revocation fired the correct number of times for the
// correct user. Thread-safe so concurrent tests do not race.
type recordingRevoker struct {
	mu      sync.Mutex
	calls   []string
	returns error
}

func (r *recordingRevoker) RevokeAllUserSessions(_ context.Context, userID string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.calls = append(r.calls, userID)
	return r.returns
}

func (r *recordingRevoker) snapshot() []string {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]string, len(r.calls))
	copy(out, r.calls)
	return out
}

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

func setupSchema(t *testing.T, pool *pgxpool.Pool) {
	t.Helper()
	ctx := context.Background()
	_, err := pool.Exec(ctx, auth.SchemaSQL())
	require.NoError(t, err)
	_, err = pool.Exec(ctx, store.SchemaSQL())
	require.NoError(t, err)
}

func truncateAll(t *testing.T, pool *pgxpool.Pool) {
	t.Helper()
	_, err := pool.Exec(context.Background(), `
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

func seedUser(t *testing.T, pool *pgxpool.Pool, id, username, email string) {
	t.Helper()
	now := time.Now().UTC()
	_, err := pool.Exec(context.Background(),
		`INSERT INTO auth_users (id, username, email, password_hash, role, active, created_at, updated_at)
		 VALUES ($1, $2, $3, '', 'etradie', TRUE, $4, $4)`,
		id, username, email, now,
	)
	require.NoError(t, err)
}

// buildService wires the production Service against the real store and a
// recording revoker. Returns the service, the revoker (for assertion), and
// the underlying stores so tests can introspect rows.
func buildService(t *testing.T, pool *pgxpool.Pool) (*service.Service, *recordingRevoker, *store.SubscriptionStore, *store.SubscriptionEventStore, *store.ProcessedEventStore) {
	t.Helper()
	subs := store.NewSubscriptionStore(pool)
	processed := store.NewProcessedEventStore(pool)
	audit := store.NewSubscriptionEventStore(pool)
	revoker := &recordingRevoker{}
	svc := service.NewService(subs, processed, audit, revoker, zerolog.Nop())
	return svc, revoker, subs, audit, processed
}

// countAuditRows returns the number of audit rows for a user. Sanity check.
func countAuditRows(t *testing.T, pool *pgxpool.Pool, userID string) int {
	t.Helper()
	var n int
	err := pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM billing_subscription_events WHERE user_id = $1`, userID,
	).Scan(&n)
	require.NoError(t, err)
	return n
}

// countProcessedRows returns processed_webhook_events count for a
// (provider, event_id) pair.
func countProcessedRows(t *testing.T, pool *pgxpool.Pool, provider, eventID string) int {
	t.Helper()
	var n int
	err := pool.QueryRow(context.Background(),
		`SELECT COUNT(*) FROM processed_webhook_events WHERE provider = $1 AND event_id = $2`,
		provider, eventID,
	).Scan(&n)
	require.NoError(t, err)
	return n
}

func TestHandleEvent_NewSubscription(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_new", "new_user", "new@example.com")

	svc, revoker, subs, _, _ := buildService(t, pool)

	ev := &events.NormalizedEvent{
		Provider:               "paddle",
		EventID:                "evt_new_1",
		EventName:              "subscription_created",
		EventTimestamp:         time.Now().UTC(),
		UserID:                 "u_new",
		ProviderCustomerID:     "cus_1",
		ProviderSubscriptionID: "sub_1",
		Tier:                   events.TierProBYOK,
		Status:                 events.StatusActive,
	}

	outcome, err := svc.HandleEvent(context.Background(), ev)
	require.NoError(t, err)
	assert.True(t, outcome.Applied)
	assert.False(t, outcome.OutOfOrder)
	assert.False(t, outcome.AlreadyProcessed)
	assert.True(t, outcome.TierChanged, "insert from nothing must count as tier change")
	assert.Equal(t, "u_new", outcome.UserID)

	sub, err := subs.GetSubscription(context.Background(), "u_new")
	require.NoError(t, err)
	assert.Equal(t, "pro_byok", sub.Tier)
	assert.Equal(t, "active", sub.Status)

	assert.Equal(t, 1, countAuditRows(t, pool, "u_new"), "audit row written")
	assert.Equal(t, 1, countProcessedRows(t, pool, "paddle", "evt_new_1"), "idempotency row written")
	assert.Equal(t, []string{"u_new"}, revoker.snapshot(), "revocation fired on tier change")
}

func TestHandleEvent_Idempotent(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_dup", "dup_user", "dup@example.com")

	svc, revoker, _, _, _ := buildService(t, pool)
	ev := &events.NormalizedEvent{
		Provider:       "paddle",
		EventID:        "evt_dup_1",
		EventName:      "subscription_created",
		EventTimestamp: time.Now().UTC(),
		UserID:         "u_dup",
		Tier:           events.TierProBYOK,
		Status:         events.StatusActive,
	}

	// First delivery: applied.
	_, err := svc.HandleEvent(context.Background(), ev)
	require.NoError(t, err)

	// Second delivery, same (provider, event_id): duplicate.
	outcome, err := svc.HandleEvent(context.Background(), ev)
	require.NoError(t, err)
	assert.True(t, outcome.AlreadyProcessed)
	assert.False(t, outcome.Applied)
	assert.False(t, outcome.TierChanged)

	assert.Equal(t, 1, countAuditRows(t, pool, "u_dup"), "audit row NOT written for duplicate")
	assert.Equal(t, []string{"u_dup"}, revoker.snapshot(), "revoker fired exactly once (for the first delivery)")
}

func TestHandleEvent_OutOfOrder(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_ooo", "ooo_user", "ooo@example.com")

	svc, _, subs, _, _ := buildService(t, pool)
	now := time.Now().UTC()

	// Newer event first.
	_, err := svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:       "paddle",
		EventID:        "evt_newer",
		EventName:      "subscription_updated",
		EventTimestamp: now,
		UserID:         "u_ooo",
		Tier:           events.TierProManaged,
		Status:         events.StatusActive,
	})
	require.NoError(t, err)

	// Older event arrives late. Different event_id so idempotency does not
	// block it — only event_timestamp ordering should reject the change.
	outcome, err := svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:       "paddle",
		EventID:        "evt_older",
		EventName:      "subscription_paused",
		EventTimestamp: now.Add(-1 * time.Hour),
		UserID:         "u_ooo",
		Tier:           events.TierProBYOK,
		Status:         events.StatusPaused,
	})
	require.NoError(t, err)
	assert.True(t, outcome.OutOfOrder)
	assert.False(t, outcome.Applied)

	sub, err := subs.GetSubscription(context.Background(), "u_ooo")
	require.NoError(t, err)
	assert.Equal(t, "pro_managed", sub.Tier, "older event must not regress the row")
	assert.Equal(t, "active", sub.Status)

	assert.Equal(t, 1, countAuditRows(t, pool, "u_ooo"), "only the applied event yields an audit row")
}

func TestHandleEvent_RecoverByProviderID(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_recover", "recover_user", "recover@example.com")

	svc, _, subs, _, _ := buildService(t, pool)
	now := time.Now().UTC()

	// Seed with a known (provider, subscription_id) for u_recover.
	_, err := svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:               "paddle",
		EventID:                "evt_recover_seed",
		EventName:              "subscription_created",
		EventTimestamp:         now,
		UserID:                 "u_recover",
		ProviderSubscriptionID: "sub_recover_1",
		Tier:                   events.TierProBYOK,
		Status:                 events.StatusActive,
	})
	require.NoError(t, err)

	// Update event arrives WITHOUT user_id (legitimate Paddle behaviour on
	// subscription.updated). The service must recover via
	// (provider, provider_subscription_id) and apply the change to u_recover.
	outcome, err := svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:               "paddle",
		EventID:                "evt_recover_update",
		EventName:              "subscription_updated",
		EventTimestamp:         now.Add(1 * time.Hour),
		UserID:                 "",
		ProviderSubscriptionID: "sub_recover_1",
		Tier:                   events.TierProManaged,
		Status:                 events.StatusActive,
	})
	require.NoError(t, err)
	assert.True(t, outcome.Applied)
	assert.Equal(t, "u_recover", outcome.UserID, "user id recovered from provider subscription id")

	sub, err := subs.GetSubscription(context.Background(), "u_recover")
	require.NoError(t, err)
	assert.Equal(t, "pro_managed", sub.Tier)
}

func TestHandleEvent_CannotResolveUser(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)

	svc, _, _, _, _ := buildService(t, pool)

	// No user_id and no matching subscription row — cannot resolve.
	_, err := svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:               "paddle",
		EventID:                "evt_orphan",
		EventName:              "subscription_updated",
		EventTimestamp:         time.Now().UTC(),
		UserID:                 "",
		ProviderSubscriptionID: "sub_unknown_999",
		Tier:                   events.TierProBYOK,
		Status:                 events.StatusActive,
	})
	assert.ErrorIs(t, err, service.ErrCannotResolveUser)
}
