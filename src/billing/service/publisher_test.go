package service_test

import (
	"context"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/billing/events"
	"github.com/flamegreat-1/etradie/src/billing/service"
	"github.com/flamegreat-1/etradie/src/billing/store"
)

// recordingPublisher composes a recordingRevoker (defined in
// subscription_test.go in the same package) and adds the
// SubscriptionEventPublisher behaviour so the service can reach the
// publish path via the same type-assertion it uses in production.
//
// Both the embedded revoker AND the new publisher slice are protected
// by their own locks so parallel test cases do not race on shared
// state. The slice copy returned by snapshotPubs is taken under the
// publisher lock so callers never see a mid-write view.
type recordingPublisher struct {
	inner *recordingRevoker

	pubMu sync.Mutex
	pubs  []service.SubscriptionChange
}

func newRecordingPublisher() *recordingPublisher {
	return &recordingPublisher{inner: &recordingRevoker{}}
}

func (p *recordingPublisher) RevokeAllUserSessions(ctx context.Context, userID string) error {
	return p.inner.RevokeAllUserSessions(ctx, userID)
}

func (p *recordingPublisher) PublishSubscriptionChange(_ context.Context, change service.SubscriptionChange) {
	p.pubMu.Lock()
	defer p.pubMu.Unlock()
	p.pubs = append(p.pubs, change)
}

func (p *recordingPublisher) revokeCalls() []string {
	return p.inner.snapshot()
}

func (p *recordingPublisher) publishCalls() []service.SubscriptionChange {
	p.pubMu.Lock()
	defer p.pubMu.Unlock()
	out := make([]service.SubscriptionChange, len(p.pubs))
	copy(out, p.pubs)
	return out
}

// buildServiceWithPublisher wires the production Service against the
// real store and a publisher-aware revoker that records both calls and
// publishes for assertion. Mirrors buildService from
// subscription_test.go but injects the richer dependency so the
// SubscriptionEventPublisher branch in subscription.go is exercised.
func buildServiceWithPublisher(t *testing.T, pool *pgxpool.Pool) (*service.Service, *recordingPublisher) {
	t.Helper()
	subs := store.NewSubscriptionStore(pool)
	processed := store.NewProcessedEventStore(pool)
	audit := store.NewSubscriptionEventStore(pool)
	pub := newRecordingPublisher()
	svc := service.NewService(subs, processed, audit, pub, zerolog.Nop())
	return svc, pub
}

func TestHandleEvent_PublisherFiresOnInsert(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_pub_insert", "pub_insert", "pi@example.com")

	svc, pub := buildServiceWithPublisher(t, pool)

	ev := &events.NormalizedEvent{
		Provider:               "paddle",
		EventID:                "evt_pub_insert_1",
		EventName:              "subscription_created",
		EventTimestamp:         time.Now().UTC(),
		UserID:                 "u_pub_insert",
		ProviderCustomerID:     "cus_pi",
		ProviderSubscriptionID: "sub_pi",
		Tier:                   events.TierProBYOK,
		Status:                 events.StatusActive,
	}

	outcome, err := svc.HandleEvent(context.Background(), ev)
	require.NoError(t, err)
	assert.True(t, outcome.Applied)
	assert.True(t, outcome.TierChanged)

	pubs := pub.publishCalls()
	require.Len(t, pubs, 1, "publisher must fire exactly once on new subscription")
	assert.Equal(t, "u_pub_insert", pubs[0].UserID)
	assert.Equal(t, "paddle", pubs[0].Provider)
	assert.Equal(t, "evt_pub_insert_1", pubs[0].EventID)
	assert.Equal(t, "", pubs[0].PreviousTier)
	assert.Equal(t, "pro_byok", pubs[0].NewTier)
	assert.Equal(t, "", pubs[0].PreviousStatus)
	assert.Equal(t, "active", pubs[0].NewStatus)
	assert.True(t, pubs[0].TierChanged)
	assert.True(t, pubs[0].StatusChanged)

	assert.Equal(t, []string{"u_pub_insert"}, pub.revokeCalls(),
		"revoker fires alongside the publisher")
}

func TestHandleEvent_PublisherFiresOnTierChange(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_pub_tier", "pub_tier", "pt@example.com")

	svc, pub := buildServiceWithPublisher(t, pool)
	now := time.Now().UTC()

	// Seed at pro_byok.
	_, err := svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:               "paddle",
		EventID:                "evt_pub_tier_seed",
		EventName:              "subscription_created",
		EventTimestamp:         now,
		UserID:                 "u_pub_tier",
		ProviderCustomerID:     "cus_pt",
		ProviderSubscriptionID: "sub_pt",
		Tier:                   events.TierProBYOK,
		Status:                 events.StatusActive,
	})
	require.NoError(t, err)
	require.Len(t, pub.publishCalls(), 1)

	// Upgrade to pro_managed.
	_, err = svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:               "paddle",
		EventID:                "evt_pub_tier_upgrade",
		EventName:              "subscription_updated",
		EventTimestamp:         now.Add(1 * time.Hour),
		UserID:                 "u_pub_tier",
		ProviderCustomerID:     "cus_pt",
		ProviderSubscriptionID: "sub_pt",
		Tier:                   events.TierProManaged,
		Status:                 events.StatusActive,
	})
	require.NoError(t, err)

	pubs := pub.publishCalls()
	require.Len(t, pubs, 2, "second publish fires for tier transition")
	assert.Equal(t, "pro_byok", pubs[1].PreviousTier)
	assert.Equal(t, "pro_managed", pubs[1].NewTier)
	assert.True(t, pubs[1].TierChanged)
	assert.False(t, pubs[1].StatusChanged,
		"status did not change so StatusChanged stays false")

	assert.Equal(t, []string{"u_pub_tier", "u_pub_tier"}, pub.revokeCalls(),
		"revoker invoked once per applied transition")
}

func TestHandleEvent_PublisherFiresOnStatusOnlyChange(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_pub_status", "pub_status", "ps@example.com")

	svc, pub := buildServiceWithPublisher(t, pool)
	now := time.Now().UTC()

	_, err := svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:               "paddle",
		EventID:                "evt_pub_status_seed",
		EventName:              "subscription_created",
		EventTimestamp:         now,
		UserID:                 "u_pub_status",
		ProviderCustomerID:     "cus_ps",
		ProviderSubscriptionID: "sub_ps",
		Tier:                   events.TierProManaged,
		Status:                 events.StatusActive,
	})
	require.NoError(t, err)
	require.Len(t, pub.publishCalls(), 1)

	// Same tier, status flips to past_due.
	_, err = svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:               "paddle",
		EventID:                "evt_pub_status_pastdue",
		EventName:              "subscription_payment_failed",
		EventTimestamp:         now.Add(1 * time.Hour),
		UserID:                 "u_pub_status",
		ProviderCustomerID:     "cus_ps",
		ProviderSubscriptionID: "sub_ps",
		Tier:                   events.TierProManaged,
		Status:                 events.StatusPastDue,
	})
	require.NoError(t, err)

	pubs := pub.publishCalls()
	require.Len(t, pubs, 2)
	assert.False(t, pubs[1].TierChanged, "tier unchanged")
	assert.True(t, pubs[1].StatusChanged, "status flipped to past_due")
	assert.Equal(t, "active", pubs[1].PreviousStatus)
	assert.Equal(t, "past_due", pubs[1].NewStatus)
}

func TestHandleEvent_PublisherSilentOnDuplicate(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_pub_dup", "pub_dup", "pd@example.com")

	svc, pub := buildServiceWithPublisher(t, pool)
	ev := &events.NormalizedEvent{
		Provider:       "paddle",
		EventID:        "evt_pub_dup_1",
		EventName:      "subscription_created",
		EventTimestamp: time.Now().UTC(),
		UserID:         "u_pub_dup",
		Tier:           events.TierProBYOK,
		Status:         events.StatusActive,
	}

	_, err := svc.HandleEvent(context.Background(), ev)
	require.NoError(t, err)
	require.Len(t, pub.publishCalls(), 1)

	outcome, err := svc.HandleEvent(context.Background(), ev)
	require.NoError(t, err)
	assert.True(t, outcome.AlreadyProcessed)

	assert.Len(t, pub.publishCalls(), 1,
		"duplicate delivery must NOT re-publish (idempotency aborts before post-commit)")
	assert.Len(t, pub.revokeCalls(), 1,
		"duplicate delivery must NOT re-revoke either")
}

func TestHandleEvent_PublisherSilentOnOutOfOrder(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_pub_ooo", "pub_ooo", "po@example.com")

	svc, pub := buildServiceWithPublisher(t, pool)
	now := time.Now().UTC()

	_, err := svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:               "paddle",
		EventID:                "evt_pub_ooo_newer",
		EventName:              "subscription_updated",
		EventTimestamp:         now,
		UserID:                 "u_pub_ooo",
		ProviderSubscriptionID: "sub_po",
		Tier:                   events.TierProManaged,
		Status:                 events.StatusActive,
	})
	require.NoError(t, err)
	require.Len(t, pub.publishCalls(), 1)

	// Older event arrives late. Different event_id so idempotency does not
	// block it; the event_timestamp guard in UpsertSubscriptionTx must.
	outcome, err := svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:               "paddle",
		EventID:                "evt_pub_ooo_older",
		EventName:              "subscription_paused",
		EventTimestamp:         now.Add(-1 * time.Hour),
		UserID:                 "u_pub_ooo",
		ProviderSubscriptionID: "sub_po",
		Tier:                   events.TierProBYOK,
		Status:                 events.StatusPaused,
	})
	require.NoError(t, err)
	assert.True(t, outcome.OutOfOrder)
	assert.False(t, outcome.Applied)

	assert.Len(t, pub.publishCalls(), 1,
		"out-of-order event must NOT publish (applied=false short-circuits)")
	assert.Len(t, pub.revokeCalls(), 1,
		"out-of-order event must NOT revoke either")
}

func TestHandleEvent_PublisherUnwiredWarnsButNotFails(t *testing.T) {
	pool := testPool(t)
	if pool == nil {
		t.Skip("BILLING_TEST_DATABASE_URL not set")
	}
	setupSchema(t, pool)
	truncateAll(t, pool)
	seedUser(t, pool, "u_pub_bare", "pub_bare", "pb@example.com")

	// Bare revoker: implements SessionRevoker but NOT
	// SubscriptionEventPublisher. Mirrors a misconfigured deployment.
	subs := store.NewSubscriptionStore(pool)
	processed := store.NewProcessedEventStore(pool)
	audit := store.NewSubscriptionEventStore(pool)
	revoker := &recordingRevoker{}
	svc := service.NewService(subs, processed, audit, revoker, zerolog.Nop())

	outcome, err := svc.HandleEvent(context.Background(), &events.NormalizedEvent{
		Provider:       "paddle",
		EventID:        "evt_pub_bare_1",
		EventName:      "subscription_created",
		EventTimestamp: time.Now().UTC(),
		UserID:         "u_pub_bare",
		Tier:           events.TierProBYOK,
		Status:         events.StatusActive,
	})
	require.NoError(t, err, "service must complete cleanly even without a publisher")
	assert.True(t, outcome.Applied)
	assert.True(t, outcome.TierChanged)

	assert.Equal(t, []string{"u_pub_bare"}, revoker.snapshot(),
		"revoker still fires on the bare-revoker path")
}
