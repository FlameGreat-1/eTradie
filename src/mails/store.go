package mails

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// SchemaSQL returns idempotent DDL for the waitlist table.
// Called once at startup, safe to re-run against a populated database.
func SchemaSQL() string {
	return `
CREATE TABLE IF NOT EXISTS waitlist (
    id         TEXT PRIMARY KEY,
    email      TEXT NOT NULL UNIQUE,
    status     TEXT NOT NULL DEFAULT 'pending',
    ip_address TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_waitlist_email ON waitlist (email);
CREATE INDEX IF NOT EXISTS idx_waitlist_created_at ON waitlist (created_at);
`
}

// Entry represents a single waitlist record.
type Entry struct {
	ID        string    `json:"id"`
	Email     string    `json:"email"`
	Status    string    `json:"status"`
	IPAddress string    `json:"ip_address,omitempty"`
	CreatedAt time.Time `json:"created_at"`
}

// WaitlistStore handles waitlist persistence in PostgreSQL.
type WaitlistStore struct {
	pool *pgxpool.Pool
}

// NewWaitlistStore creates a waitlist store backed by the given pool.
func NewWaitlistStore(pool *pgxpool.Pool) *WaitlistStore {
	return &WaitlistStore{pool: pool}
}

// CreateEntry inserts a new waitlist email. Returns the entry on success.
// If the email already exists, returns (nil, nil) — idempotent by design
// so duplicate submissions from the frontend never produce an error.
func (s *WaitlistStore) CreateEntry(ctx context.Context, email, ipAddress string) (*Entry, error) {
	email = strings.ToLower(strings.TrimSpace(email))
	if email == "" {
		return nil, fmt.Errorf("email is required")
	}

	id := generateID()
	now := time.Now().UTC()

	tag, err := s.pool.Exec(ctx,
		`INSERT INTO waitlist (id, email, status, ip_address, created_at)
		 VALUES ($1, $2, 'pending', $3, $4)
		 ON CONFLICT (email) DO NOTHING`,
		id, email, ipAddress, now,
	)
	if err != nil {
		return nil, fmt.Errorf("insert waitlist entry: %w", err)
	}

	// ON CONFLICT DO NOTHING returns 0 rows affected for duplicates.
	if tag.RowsAffected() == 0 {
		return nil, nil
	}

	return &Entry{
		ID:        id,
		Email:     email,
		Status:    "pending",
		IPAddress: ipAddress,
		CreatedAt: now,
	}, nil
}

// GetByEmail retrieves a waitlist entry by email. Returns (nil, nil) if
// not found.
func (s *WaitlistStore) GetByEmail(ctx context.Context, email string) (*Entry, error) {
	email = strings.ToLower(strings.TrimSpace(email))
	e := &Entry{}
	err := s.pool.QueryRow(ctx,
		`SELECT id, email, status, ip_address, created_at
		 FROM waitlist WHERE email = $1`, email,
	).Scan(&e.ID, &e.Email, &e.Status, &e.IPAddress, &e.CreatedAt)
	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("get waitlist entry: %w", err)
	}
	return e, nil
}

// Count returns the total number of waitlist entries.
func (s *WaitlistStore) Count(ctx context.Context) (int64, error) {
	var count int64
	err := s.pool.QueryRow(ctx, `SELECT COUNT(*) FROM waitlist`).Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("count waitlist: %w", err)
	}
	return count, nil
}
