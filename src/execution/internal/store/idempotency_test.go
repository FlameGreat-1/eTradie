package store_test

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/stretchr/testify/require"

	"github.com/flamegreat-1/etradie/src/execution/internal/store"
)

// newTestPool brings up a pgxpool from EXECUTION_DATABASE_URL or skips.
// The brokertest package (CI fixture) already ensures Postgres is up,
// so this test runs end-to-end against ON CONFLICT semantics rather
// than mocking them.
func newTestPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	dsn := os.Getenv("EXECUTION_DATABASE_URL")
	if dsn == "" {
		t.Skip("EXECUTION_DATABASE_URL not set")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	pool, err := pgxpool.New(ctx, dsn)
	require.NoError(t, err)
	require.NoError(t, pool.Ping(ctx))
	// EnsureSchema (not pool.Exec(SchemaSQL())) so the state +
	// store test packages running in parallel do not deadlock on
	// the CREATE OR REPLACE TRIGGER statements inside SchemaSQL.
	require.NoError(t, store.EnsureSchema(ctx, pool))
	return pool
}

func cleanupIdempotency(t *testing.T, pool *pgxpool.Pool, userID string) {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_, _ = pool.Exec(ctx, "DELETE FROM execution_order_idempotency WHERE user_id = $1", userID)
}

func TestTryClaimFirstAndDuplicate(t *testing.T) {
	pool := newTestPool(t)
	defer pool.Close()
	s := store.NewIdempotencyStore(pool)
	userID := "test-user-idem-1"
	defer cleanupIdempotency(t, pool, userID)

	ctx := context.Background()
	rec := &store.IdempotencyRecord{
		UserID:         userID,
		IdempotencyKey: "key-aaa",
		OrderID:        "order-1",
		Symbol:         "EURUSD",
		Direction:      "LONG",
		ExecutionMode:  "LIMIT",
		EntryPrice:     1.1000,
		StopLoss:       1.0950,
		LotSize:        0.10,
	}

	claim, err := s.TryClaim(ctx, rec)
	require.NoError(t, err)
	require.True(t, claim.FirstClaim)
	require.Nil(t, claim.Existing)

	require.NoError(t, s.RecordResult(ctx, userID, "key-aaa", "broker-42", "FILLED", 1.1001, 0.10, 0))

	claim2, err := s.TryClaim(ctx, rec)
	require.NoError(t, err)
	require.False(t, claim2.FirstClaim)
	require.NotNil(t, claim2.Existing)
	require.Equal(t, "broker-42", claim2.Existing.BrokerOrderID)
	require.Equal(t, "FILLED", claim2.Existing.Status)
	require.InDelta(t, 1.1001, claim2.Existing.FillPrice, 1e-9)
	require.InDelta(t, 0.10, claim2.Existing.VolumeFilled, 1e-9)
}

func TestRecordResultPersistsPartialFill(t *testing.T) {
	pool := newTestPool(t)
	defer pool.Close()
	s := store.NewIdempotencyStore(pool)
	userID := "test-user-idem-2"
	defer cleanupIdempotency(t, pool, userID)
	ctx := context.Background()

	rec := &store.IdempotencyRecord{
		UserID:         userID,
		IdempotencyKey: "key-partial",
		OrderID:        "order-2",
		Symbol:         "GBPUSD",
		Direction:      "SHORT",
		ExecutionMode:  "LIMIT",
		LotSize:        1.0,
	}
	_, err := s.TryClaim(ctx, rec)
	require.NoError(t, err)
	require.NoError(t, s.RecordResult(ctx, userID, "key-partial", "broker-99", "PARTIALLY_FILLED", 1.2700, 0.30, 0.70))

	claim, err := s.TryClaim(ctx, rec)
	require.NoError(t, err)
	require.False(t, claim.FirstClaim)
	require.NotNil(t, claim.Existing)
	require.Equal(t, "PARTIALLY_FILLED", claim.Existing.Status)
	require.InDelta(t, 0.30, claim.Existing.VolumeFilled, 1e-9)
	require.InDelta(t, 0.70, claim.Existing.VolumeRemaining, 1e-9)
}

func TestGarbageCollect(t *testing.T) {
	pool := newTestPool(t)
	defer pool.Close()
	s := store.NewIdempotencyStore(pool)
	userID := "test-user-idem-3"
	defer cleanupIdempotency(t, pool, userID)
	ctx := context.Background()

	rec := &store.IdempotencyRecord{
		UserID:         userID,
		IdempotencyKey: "key-gc",
		OrderID:        "order-3",
		Symbol:         "USDJPY",
		Direction:      "LONG",
		ExecutionMode:  "LIMIT",
	}
	_, err := s.TryClaim(ctx, rec)
	require.NoError(t, err)

	// Backdate the row so GC's cutoff sweeps it up.
	_, err = pool.Exec(ctx,
		"UPDATE execution_order_idempotency SET created_at = NOW() - interval '48 hours' WHERE user_id = $1",
		userID,
	)
	require.NoError(t, err)

	deleted, err := s.GarbageCollect(ctx, time.Now().Add(-24*time.Hour))
	require.NoError(t, err)
	require.GreaterOrEqual(t, deleted, int64(1))
}
