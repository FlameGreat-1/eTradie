package auth

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ---------------------------------------------------------------------------
// Password reset token
//
// The forgot/reset password flow uses a single-use, time-limited bearer
// token delivered out-of-band via email. The plaintext token is shown
// to the user exactly once (inside the reset link in the email) and
// never persisted: only its SHA-256 digest lives in auth_password_resets.
// A leaked database backup therefore cannot be used to perform a reset
// without the corresponding email being captured too.
//
// Invariants (enforced by the schema + the store):
//
//  - one OUTSTANDING reset per user at any time. Issuing a new token
//    revokes any prior unconsumed token for the same user (logically:
//    we mark them consumed; the partial-unique index keeps the table
//    honest if a race were to slip through).
//  - single-use: ConsumeByToken atomically flips consumed=TRUE and
//    returns the row in one UPDATE ... RETURNING so two parallel
//    redemptions of the same token cannot both succeed.
//  - bound to a user_id: the token is meaningless on its own; the
//    handler always loads the user fresh from the DB after consume
//    to apply the latest active/auth_provider state.
//
// The store deliberately does NOT cap creation rate; that responsibility
// lives one layer up in the handler's IP rate limiter. The schema is
// the bottom-most guard.
// ---------------------------------------------------------------------------

// PasswordReset is the persistent record of a forgot-password request.
// TokenHash is the SHA-256 hex digest of the plaintext token; the
// plaintext is never stored.
type PasswordReset struct {
	ID          string
	UserID      string
	TokenHash   string
	CreatedAt   time.Time
	ExpiresAt   time.Time
	Consumed    bool
	ConsumedAt  *time.Time
	RequestedIP string
	UserAgent   string
}

// IsExpired reports whether the token has passed its expiry time.
func (p *PasswordReset) IsExpired() bool {
	return time.Now().UTC().After(p.ExpiresAt)
}

// IsUsable returns true when the token is neither consumed nor expired.
func (p *PasswordReset) IsUsable() bool {
	return !p.Consumed && !p.IsExpired()
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

// PasswordResetStore handles persistence of password reset tokens.
type PasswordResetStore struct {
	pool *pgxpool.Pool
}

// NewPasswordResetStore creates a store backed by the given connection pool.
func NewPasswordResetStore(pool *pgxpool.Pool) *PasswordResetStore {
	return &PasswordResetStore{pool: pool}
}

// CreateToken inserts a new reset row for the user and atomically marks
// any prior unconsumed token for the same user as consumed. The two
// statements run inside a single transaction so a concurrent reset
// request cannot leave two live tokens for one user.
//
// The plaintext token is hashed before persistence and never stored.
func (s *PasswordResetStore) CreateToken(
	ctx context.Context,
	userID string,
	plaintextToken string,
	ttl time.Duration,
	requestedIP string,
	userAgent string,
) (*PasswordReset, error) {
	if userID == "" {
		return nil, fmt.Errorf("password reset: user_id is required")
	}
	if plaintextToken == "" {
		return nil, fmt.Errorf("password reset: token is required")
	}
	if ttl <= 0 {
		return nil, fmt.Errorf("password reset: ttl must be positive, got %s", ttl)
	}

	now := time.Now().UTC()
	row := &PasswordReset{
		ID:          GenerateID(),
		UserID:      userID,
		TokenHash:   hashToken(plaintextToken),
		CreatedAt:   now,
		ExpiresAt:   now.Add(ttl),
		Consumed:    false,
		RequestedIP: requestedIP,
		UserAgent:   userAgent,
	}

	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return nil, fmt.Errorf("password reset: begin tx: %w", err)
	}
	defer func() { _ = tx.Rollback(ctx) }()

	// Invalidate any prior outstanding tokens for this user. Logical
	// consume (consumed = TRUE) preserves the audit trail. The partial
	// unique index then makes the new insert safe.
	if _, err := tx.Exec(ctx,
		`UPDATE auth_password_resets
		    SET consumed    = TRUE,
		        consumed_at = $1
		  WHERE user_id  = $2
		    AND consumed = FALSE`,
		now, userID,
	); err != nil {
		return nil, fmt.Errorf("password reset: invalidate prior tokens: %w", err)
	}

	if _, err := tx.Exec(ctx,
		`INSERT INTO auth_password_resets
		   (id, user_id, token_hash, created_at, expires_at, consumed, requested_ip, user_agent)
		 VALUES ($1,$2,$3,$4,$5,$6,$7,$8)`,
		row.ID, row.UserID, row.TokenHash, row.CreatedAt, row.ExpiresAt,
		row.Consumed, row.RequestedIP, row.UserAgent,
	); err != nil {
		return nil, fmt.Errorf("password reset: insert: %w", err)
	}

	if err := tx.Commit(ctx); err != nil {
		return nil, fmt.Errorf("password reset: commit: %w", err)
	}

	return row, nil
}

// GetUsableByToken loads a reset row by plaintext token (hashed on the
// fly) and returns it only when the row is non-consumed and non-expired.
// Returns (nil, nil) for not-found / expired / consumed.
//
// Callers MUST treat the three cases (not-found, expired, consumed) as
// indistinguishable in user-facing responses so a leaked token cannot
// be probed for its lifecycle stage.
func (s *PasswordResetStore) GetUsableByToken(ctx context.Context, plaintextToken string) (*PasswordReset, error) {
	if plaintextToken == "" {
		return nil, nil
	}
	hash := hashToken(plaintextToken)
	row := &PasswordReset{}
	err := s.pool.QueryRow(ctx,
		`SELECT id, user_id, token_hash, created_at, expires_at, consumed, consumed_at,
		        requested_ip, user_agent
		   FROM auth_password_resets
		  WHERE token_hash = $1`,
		hash,
	).Scan(
		&row.ID, &row.UserID, &row.TokenHash, &row.CreatedAt, &row.ExpiresAt,
		&row.Consumed, &row.ConsumedAt, &row.RequestedIP, &row.UserAgent,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, fmt.Errorf("password reset: get by token: %w", err)
	}
	if !row.IsUsable() {
		return nil, nil
	}
	return row, nil
}

// ConsumeByToken atomically marks the matching row as consumed and
// returns it. Single-use enforcement: the WHERE clause requires the row
// to be currently unconsumed and unexpired, so a concurrent second
// redemption sees zero rows updated and falls into the (nil, nil)
// branch.
func (s *PasswordResetStore) ConsumeByToken(ctx context.Context, plaintextToken string) (*PasswordReset, error) {
	if plaintextToken == "" {
		return nil, nil
	}
	hash := hashToken(plaintextToken)
	now := time.Now().UTC()
	row := &PasswordReset{}
	err := s.pool.QueryRow(ctx,
		`UPDATE auth_password_resets
		    SET consumed    = TRUE,
		        consumed_at = $1
		  WHERE token_hash = $2
		    AND consumed   = FALSE
		    AND expires_at > $1
		 RETURNING id, user_id, token_hash, created_at, expires_at, consumed, consumed_at,
		           requested_ip, user_agent`,
		now, hash,
	).Scan(
		&row.ID, &row.UserID, &row.TokenHash, &row.CreatedAt, &row.ExpiresAt,
		&row.Consumed, &row.ConsumedAt, &row.RequestedIP, &row.UserAgent,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, fmt.Errorf("password reset: consume: %w", err)
	}
	return row, nil
}

// CountRecentRequests returns the number of reset requests issued for a
// user within the trailing window. Handlers use this to apply a per-user
// soft rate limit on top of the IP limiter, defeating an attacker who
// rotates IPs to flood one mailbox.
func (s *PasswordResetStore) CountRecentRequests(ctx context.Context, userID string, within time.Duration) (int, error) {
	if userID == "" {
		return 0, nil
	}
	cutoff := time.Now().UTC().Add(-within)
	var count int
	err := s.pool.QueryRow(ctx,
		`SELECT COUNT(*) FROM auth_password_resets
		  WHERE user_id = $1 AND created_at >= $2`,
		userID, cutoff,
	).Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("password reset: count recent: %w", err)
	}
	return count, nil
}

// DeleteExpiredTokens removes rows that expired more than the retention
// window ago. Called by the gateway's hourly janitor.
func (s *PasswordResetStore) DeleteExpiredTokens(ctx context.Context) (int64, error) {
	// Retain a 24h post-expiry window so a freshly-expired token can
	// still be reasoned about in audit logs.
	cutoff := time.Now().UTC().Add(-24 * time.Hour)
	tag, err := s.pool.Exec(ctx,
		`DELETE FROM auth_password_resets WHERE expires_at < $1`, cutoff,
	)
	if err != nil {
		return 0, fmt.Errorf("password reset: cleanup expired: %w", err)
	}
	return tag.RowsAffected(), nil
}

// ---------------------------------------------------------------------------
// Token generation helper
// ---------------------------------------------------------------------------

// GeneratePasswordResetToken produces a cryptographically random 32-byte
// (64 hex char) token used as the bearer credential inside the reset
// link emailed to the user. Matches the shape and entropy of
// GenerateRefreshToken; uses crypto/rand for unguessability.
func GeneratePasswordResetToken() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", fmt.Errorf("password reset: read random bytes: %w", err)
	}
	return hex.EncodeToString(b), nil
}
