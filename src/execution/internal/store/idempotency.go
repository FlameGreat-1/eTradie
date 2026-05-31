package store

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

// IdempotencyRecord is the persisted state of a single idempotent
// order placement attempt.
type IdempotencyRecord struct {
	UserID          string
	IdempotencyKey  string
	OrderID         string
	Symbol          string
	Direction       string
	ExecutionMode   string
	EntryPrice      float64
	StopLoss        float64
	LotSize         float64
	BrokerOrderID   string
	Status          string
	FillPrice       float64
	VolumeFilled    float64
	VolumeRemaining float64
	CreatedAt       time.Time
}

// IdempotencyClaim describes the result of a TryClaim attempt.
type IdempotencyClaim struct {
	// FirstClaim is true when this caller won the race and now owns
	// the right to call the broker. When false the caller MUST NOT
	// call the broker and instead surface Existing.
	FirstClaim bool

	// Existing is the prior record returned when FirstClaim=false.
	// nil when FirstClaim=true.
	Existing *IdempotencyRecord
}

// IdempotencyStore handles all PostgreSQL operations for the order
// idempotency table. CHECKLIST Section 3.
type IdempotencyStore struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

// NewIdempotencyStore constructs a store backed by the given pool.
func NewIdempotencyStore(pool *pgxpool.Pool) *IdempotencyStore {
	return &IdempotencyStore{
		pool: pool,
		log:  observability.Logger("idempotency_store"),
	}
}

// claimSQL returns order_id only when the INSERT actually happened.
// A returned row means we won the race; pgx.ErrNoRows means the
// (user_id, idempotency_key) row already existed.
const claimSQL = `
INSERT INTO execution_order_idempotency (
    user_id, idempotency_key, order_id, symbol, direction,
    execution_mode, entry_price, stop_loss, lot_size
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9
)
ON CONFLICT (user_id, idempotency_key) DO NOTHING
RETURNING order_id
`

const existingSQL = `
SELECT user_id, idempotency_key, order_id, symbol, direction,
       execution_mode, entry_price, stop_loss, lot_size,
       broker_order_id, status, fill_price, volume_filled,
       volume_remaining, created_at
FROM execution_order_idempotency
WHERE user_id = $1 AND idempotency_key = $2
`

const recordResultSQL = `
UPDATE execution_order_idempotency
SET broker_order_id = $3,
    status = $4,
    fill_price = $5,
    volume_filled = $6,
    volume_remaining = $7,
    completed_at = NOW()
WHERE user_id = $1 AND idempotency_key = $2
`

const gcSQL = `
DELETE FROM execution_order_idempotency
WHERE created_at < $1
`

// TryClaim atomically claims an idempotency key. The happy path is a
// single round-trip: the INSERT either inserts (FirstClaim=true) or
// is a no-op via ON CONFLICT, in which case a second SELECT recovers
// the existing row.
func (s *IdempotencyStore) TryClaim(
	ctx context.Context,
	rec *IdempotencyRecord,
) (*IdempotencyClaim, error) {
	if rec.UserID == "" || rec.IdempotencyKey == "" {
		return nil, fmt.Errorf("idempotency: user_id and idempotency_key are required")
	}

	var insertedOrderID string
	err := s.pool.QueryRow(ctx, claimSQL,
		rec.UserID,
		rec.IdempotencyKey,
		rec.OrderID,
		rec.Symbol,
		rec.Direction,
		rec.ExecutionMode,
		rec.EntryPrice,
		rec.StopLoss,
		rec.LotSize,
	).Scan(&insertedOrderID)

	if err == nil {
		// RETURNING fired on a successful INSERT - we won the race.
		observability.OrderIdempotencyTotal.WithLabelValues("claimed").Inc()
		s.log.Info().
			Str("user_id", rec.UserID).
			Str("idempotency_key", rec.IdempotencyKey).
			Str("order_id", rec.OrderID).
			Msg("idempotency_claimed")
		return &IdempotencyClaim{FirstClaim: true}, nil
	}

	if !errors.Is(err, pgx.ErrNoRows) {
		return nil, fmt.Errorf("idempotency: claim insert: %w", err)
	}

	// ON CONFLICT DO NOTHING fired - row already existed. Fetch it.
	existing, fetchErr := s.fetch(ctx, rec.UserID, rec.IdempotencyKey)
	if fetchErr != nil {
		return nil, fetchErr
	}
	observability.OrderIdempotencyTotal.WithLabelValues("duplicate").Inc()
	s.log.Info().
		Str("user_id", rec.UserID).
		Str("idempotency_key", rec.IdempotencyKey).
		Str("existing_broker_order_id", existing.BrokerOrderID).
		Str("existing_status", existing.Status).
		Msg("idempotency_duplicate")
	return &IdempotencyClaim{FirstClaim: false, Existing: existing}, nil
}

func (s *IdempotencyStore) fetch(
	ctx context.Context,
	userID, key string,
) (*IdempotencyRecord, error) {
	var r IdempotencyRecord
	err := s.pool.QueryRow(ctx, existingSQL, userID, key).Scan(
		&r.UserID, &r.IdempotencyKey, &r.OrderID, &r.Symbol, &r.Direction,
		&r.ExecutionMode, &r.EntryPrice, &r.StopLoss, &r.LotSize,
		&r.BrokerOrderID, &r.Status, &r.FillPrice, &r.VolumeFilled,
		&r.VolumeRemaining, &r.CreatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("idempotency: fetch existing: %w", err)
	}
	return &r, nil
}

// RecordResult updates the claimed row with the broker outcome.
// Called after the broker call returns (success, failure, partial).
func (s *IdempotencyStore) RecordResult(
	ctx context.Context,
	userID, key, brokerOrderID, status string,
	fillPrice, volumeFilled, volumeRemaining float64,
) error {
	if userID == "" || key == "" {
		return fmt.Errorf("idempotency: user_id and idempotency_key are required")
	}
	_, err := s.pool.Exec(ctx, recordResultSQL,
		userID, key, brokerOrderID, status,
		fillPrice, volumeFilled, volumeRemaining,
	)
	if err != nil {
		return fmt.Errorf("idempotency: record result: %w", err)
	}
	return nil
}

// GarbageCollect prunes records older than the supplied cutoff. Run
// from a periodic goroutine (every hour by default) to keep the
// table bounded - the idempotency window is finite (24h default).
func (s *IdempotencyStore) GarbageCollect(
	ctx context.Context,
	olderThan time.Time,
) (int64, error) {
	res, err := s.pool.Exec(ctx, gcSQL, olderThan)
	if err != nil {
		return 0, fmt.Errorf("idempotency: gc: %w", err)
	}
	return res.RowsAffected(), nil
}
