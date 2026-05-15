package store

import (
	"context"
	"errors"
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
	if errors.Is(err, pgx.ErrNoRows) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	return inserted == 1, nil
}

// PruneOlderThan deletes rows whose received_at is strictly older than the
// supplied cutoff and returns the number of rows removed.
//
// Idempotency only matters during the provider's retry window (Paddle and
// Lemon Squeezy both retry well under 7 days). The reconciler calls this
// hourly with a 30-day cutoff by default so processed_webhook_events stays
// bounded forever. The DELETE is index-scanned via the existing
// idx_processed_webhook_events_received_at index.
func (s *ProcessedEventStore) PruneOlderThan(
	ctx context.Context, cutoff time.Time,
) (int64, error) {
	const q = `DELETE FROM processed_webhook_events WHERE received_at < $1`
	tag, err := s.db.Exec(ctx, q, cutoff)
	if err != nil {
		return 0, err
	}
	return tag.RowsAffected(), nil
}

// SubscriptionEventStore appends an immutable audit record per subscription
// transition. Read-only support paths use the row history to answer
// "what was this user's tier at time X" and to debug provider edge cases.
type SubscriptionEventStore struct{ db *pgxpool.Pool }

func NewSubscriptionEventStore(db *pgxpool.Pool) *SubscriptionEventStore {
	return &SubscriptionEventStore{db: db}
}

// SubscriptionEvent is the audit-row payload for an applied subscription change.
//
// Payment-metadata fields (AmountCents, Currency, InvoiceURL, Card*) are
// nullable pointers so 'absent' is unambiguous on tier-change events that
// carry no money or card. They map one-for-one onto the matching nullable
// columns added to billing_subscription_events in the schema migration.
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

	AmountCents *int64
	Currency    *string
	InvoiceURL  *string

	CardBrand    *string
	CardLast4    *string
	CardExpMonth *int
	CardExpYear  *int
}

// AppendTx writes one immutable audit row inside the supplied transaction.
//
// Pointer fields that are nil land as SQL NULL via the nullable* helpers
// below; this is the only place those columns are ever populated, so a
// tier-change-only event produces an audit row whose financial columns
// remain NULL forever (the SPA's Invoice History filter then skips them).
func (s *SubscriptionEventStore) AppendTx(
	ctx context.Context, tx pgx.Tx, ev *SubscriptionEvent,
) error {
	const q = `
		INSERT INTO billing_subscription_events (
			user_id, provider, event_name, event_id,
			previous_tier, new_tier, previous_status, new_status,
			event_timestamp,
			amount_cents, currency, invoice_url,
			card_brand, card_last4, card_exp_month, card_exp_year
		) VALUES (
			$1, $2, $3, $4,
			$5, $6, $7, $8,
			$9,
			$10, $11, $12,
			$13, $14, $15, $16
		)
	`
	_, err := tx.Exec(ctx, q,
		ev.UserID, ev.Provider, ev.EventName, ev.EventID,
		nullableString(ev.PreviousTier), ev.NewTier,
		nullableString(ev.PreviousStatus), ev.NewStatus,
		ev.EventTimestamp,
		nullableInt64Ptr(ev.AmountCents),
		nullableStringPtr(ev.Currency),
		nullableStringPtr(ev.InvoiceURL),
		nullableStringPtr(ev.CardBrand),
		nullableStringPtr(ev.CardLast4),
		nullableIntPtr(ev.CardExpMonth),
		nullableIntPtr(ev.CardExpYear),
	)
	return err
}

// nullableStringPtr / nullableInt64Ptr / nullableIntPtr convert pointer
// fields on SubscriptionEvent into the explicit nil pgx needs to write
// SQL NULL. Returning any rather than the underlying type lets pgx pick
// the wire format.
func nullableStringPtr(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}

func nullableInt64Ptr(p *int64) any {
	if p == nil {
		return nil
	}
	return *p
}

func nullableIntPtr(p *int) any {
	if p == nil {
		return nil
	}
	return *p
}

// nullableString converts an empty string to a nil SQL parameter so audit
// columns that are nullable (previous_tier, previous_status on first-insert)
// stay NULL instead of being written as empty strings. The any return type
// lets pgx pick the wire format.
//
// The service package has its own service.nullablePtr helper with a *string
// return for the row-storage *string fields on store.Subscription. The two
// are deliberately separate because they target columns with different
// nullability constraints and Go types; merging them would force one
// consumer to convert at every call site.
func nullableString(s string) any {
	if s == "" {
		return nil
	}
	return s
}
