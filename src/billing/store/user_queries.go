package store

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ---------------------------------------------------------------------------
// UserQueries — read-only, USER-SCOPED query surface for the dashboard's
// regular-user Payment panel.
//
// Every method takes the authenticated user_id as its first SQL bind
// (resolved server-side from the JWT, not from any query parameter), so
// a forged client cannot iterate over arbitrary user ids. This is the
// inverse of AdminQueries, which has no user_id filter because admins
// legitimately read across the whole table.
// ---------------------------------------------------------------------------

type UserQueries struct {
	db *pgxpool.Pool
}

func NewUserQueries(db *pgxpool.Pool) *UserQueries {
	return &UserQueries{db: db}
}

// ErrPaymentMethodNotConfigured is returned by GetUserPaymentMethod when
// the user has never paid (no subscription row exists, or one exists but
// the card snapshot is NULL because the user is on the implicit free
// tier seeded by the auth layer). Callers map it to a clean 'no payment
// method on file' UI state rather than a 5xx.
var ErrPaymentMethodNotConfigured = errors.New("billing: payment method not configured")

// UserPaymentMethod is the read shape returned to the SPA's Payment
// Methods card. All fields are non-nullable on the wire — the absence
// of a payment method is signalled by ErrPaymentMethodNotConfigured
// rather than a row of empty strings, so the SPA's render branch is
// driven by the HTTP status code, not by string emptiness checks.
type UserPaymentMethod struct {
	CardBrand          string `json:"card_brand"`
	CardLast4          string `json:"card_last4"`
	CardExpMonth       int    `json:"card_exp_month"`
	CardExpYear        int    `json:"card_exp_year"`
	PaymentProvider    string `json:"payment_provider"`
	ProviderCustomerID string `json:"provider_customer_id"`
}

// GetUserPaymentMethod returns the latest card snapshot for one user.
// Returns ErrPaymentMethodNotConfigured when the user has no
// subscription row OR the row has no card snapshot yet (the implicit
// free-tier seed populated by the auth layer never sets card_*).
func (q *UserQueries) GetUserPaymentMethod(
	ctx context.Context, userID string,
) (*UserPaymentMethod, error) {
	if strings.TrimSpace(userID) == "" {
		return nil, fmt.Errorf("user_payment_method: user_id is required")
	}

	const sqlStmt = `
		SELECT
			COALESCE(card_brand,         ''),
			COALESCE(card_last4,         ''),
			COALESCE(card_exp_month,     0),
			COALESCE(card_exp_year,      0),
			COALESCE(payment_provider,   ''),
			COALESCE(provider_customer_id, '')
		FROM billing_subscriptions
		WHERE user_id = $1
	`
	var m UserPaymentMethod
	err := q.db.QueryRow(ctx, sqlStmt, userID).Scan(
		&m.CardBrand, &m.CardLast4,
		&m.CardExpMonth, &m.CardExpYear,
		&m.PaymentProvider, &m.ProviderCustomerID,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrPaymentMethodNotConfigured
		}
		return nil, fmt.Errorf("user_payment_method: %w", err)
	}
	// A row exists but no card snapshot has ever been written (free seed,
	// or a paying user pre-card-snapshot rollout): treat the same as
	// 'not configured' for UI purposes.
	if m.CardBrand == "" && m.CardLast4 == "" {
		return nil, ErrPaymentMethodNotConfigured
	}
	return &m, nil
}

// ---------------------------------------------------------------------------
// Invoice / payment history
// ---------------------------------------------------------------------------

// UserPaymentHistoryRow is one entry in the dashboard's Invoice History
// list. Pointer fields mirror the underlying nullable columns so the
// JSON encoder emits null rather than zero values; the SPA renders —
// or hides — each cell based on whether the field is null.
type UserPaymentHistoryRow struct {
	ID             int64     `json:"id"`
	Provider       string    `json:"provider"`
	EventName      string    `json:"event_name"`
	EventTimestamp time.Time `json:"event_timestamp"`
	CreatedAt      time.Time `json:"created_at"`
	AmountCents    *int64    `json:"amount_cents"`
	Currency       *string   `json:"currency"`
	InvoiceURL     *string   `json:"invoice_url"`
	CardBrand      *string   `json:"card_brand"`
	CardLast4      *string   `json:"card_last4"`
}

// userFinancialEventNames is the canonical set of audit-table event
// names that represent a real money movement and therefore belong on
// the user's Invoice History. The list is closed and intentional so a
// future addition (e.g. a chargeback event) is a deliberate code change
// rather than a silent UI surprise.
//
//   Paddle:        transaction_completed
//   Lemon Squeezy: subscription_payment_success / _failed / _refunded
var userFinancialEventNames = []string{
	"transaction_completed",
	"subscription_payment_success",
	"subscription_payment_failed",
	"subscription_payment_refunded",
}

// GetUserPaymentHistory returns one page of financial events for the
// authenticated user, newest first.
//
// Page values follow the same normalisation as AdminQueries.Page: zero /
// negative inputs default to (1, 50); size > 100 is clamped (the
// AdminQueries clamp at 200 is fine for admins reading across the whole
// table, but per-user lists are bounded to a saner 100-row page).
func (q *UserQueries) GetUserPaymentHistory(
	ctx context.Context, userID string, p Page,
) (rows []UserPaymentHistoryRow, total int64, err error) {
	if strings.TrimSpace(userID) == "" {
		return nil, 0, fmt.Errorf("user_payment_history: user_id is required")
	}

	limit, offset := p.normalize()
	if limit > 100 {
		limit = 100
	}

	const countSQL = `
		SELECT COUNT(*)
		FROM billing_subscription_events
		WHERE user_id = $1
		  AND event_name = ANY($2::text[])
	`
	if err := q.db.QueryRow(ctx, countSQL, userID, userFinancialEventNames).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("user_payment_history: count: %w", err)
	}
	if total == 0 {
		return []UserPaymentHistoryRow{}, 0, nil
	}

	const listSQL = `
		SELECT
			id, provider, event_name, event_timestamp, created_at,
			amount_cents, currency, invoice_url,
			card_brand, card_last4
		FROM billing_subscription_events
		WHERE user_id = $1
		  AND event_name = ANY($2::text[])
		ORDER BY created_at DESC, id DESC
		LIMIT $3 OFFSET $4
	`
	dbRows, err := q.db.Query(ctx, listSQL, userID, userFinancialEventNames, limit, offset)
	if err != nil {
		return nil, 0, fmt.Errorf("user_payment_history: query: %w", err)
	}
	defer dbRows.Close()

	rows = make([]UserPaymentHistoryRow, 0, limit)
	for dbRows.Next() {
		var r UserPaymentHistoryRow
		if err := dbRows.Scan(
			&r.ID, &r.Provider, &r.EventName, &r.EventTimestamp, &r.CreatedAt,
			&r.AmountCents, &r.Currency, &r.InvoiceURL,
			&r.CardBrand, &r.CardLast4,
		); err != nil {
			return nil, 0, fmt.Errorf("user_payment_history: scan: %w", err)
		}
		rows = append(rows, r)
	}
	if err := dbRows.Err(); err != nil {
		return nil, 0, fmt.Errorf("user_payment_history: rows: %w", err)
	}
	return rows, total, nil
}
