package store

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ProcessedEventStore writes one row per webhook event we have committed work
// for. The (provider, event_id) primary key gives us cheap, race-safe dedupe:
// the first call to MarkProcessedTx for a given pair returns isNew=true; every
// subsequent call returns isNew=false. Callers MUST short-circuit and ack the
// webhook when isNew=false so the provider stops retrying.
type ProcessedEventStore struct{ db *pgxpool.Pool }

func NewProcessedEventStore(db *pgxpool.Pool) *ProcessedEventStore {
	return &ProcessedEventStore{db: db}
}

// MarkProcessedTx attempts to record (provider, eventID, eventName) inside
// the supplied transaction. Returns (true, nil) if the row was inserted (i.e.
// this is the first time we have seen this event), (false, nil) if the row
// already exists (duplicate delivery), or (false, err) on infrastructure error.
func (s *ProcessedEventStore) MarkProcessedTx(
	ctx context.Context, tx pgx.Tx, provider, eventID, eventName string,
) (bool, error) {
	const q = `
		INSERT INTO processed_webhook_events (provider, event_id, event_name)
		VALUES ($1, $2, $3)
		ON CONFLICT (provider, event_id) DO NOTHING
		RETURNING 1
	`
	var inserted int
	err := tx.QueryRow(ctx, q, provider, eventID, eventName).Scan(&inserted)
	if err == pgx.ErrNoRows {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	return inserted == 1, nil
}

// SubscriptionEventStore appends an immutable audit record per subscription
// transition. Read-only support paths use the row history to answer
// "what was this user's tier at time X" and to debug provider edge cases.
type SubscriptionEventStore struct{ db *pgxpool.Pool }

func NewSubscriptionEventStore(db *pgxpool.Pool) *SubscriptionEventStore {
	return &SubscriptionEventStore{db: db}
}

// SubscriptionEvent is the audit-row payload for an applied subscription change.
type SubscriptionEvent struct {
	UserID         string
	Provider       string
	EventName      string
	EventID        string
	PreviousTier   string
	NewTier        string
	PreviousStatus string
	NewStatus      string
	EventTimestamp time.Time
}

// AppendTx writes one immutable audit row inside the supplied transaction.
func (s *SubscriptionEventStore) AppendTx(
	ctx context.Context, tx pgx.Tx, ev *SubscriptionEvent,
) error {
	const q = `
		INSERT INTO billing_subscription_events (
			user_id, provider, event_name, event_id,
			previous_tier, new_tier, previous_status, new_status,
			event_timestamp
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
	`
	_, err := tx.Exec(ctx, q,
		ev.UserID, ev.Provider, ev.EventName, ev.EventID,
		nullableString(ev.PreviousTier), ev.NewTier,
		nullableString(ev.PreviousStatus), ev.NewStatus,
		ev.EventTimestamp,
	)
	return err
}

func nullableString(s string) any {
	if s == "" {
		return nil
	}
	return s
}
