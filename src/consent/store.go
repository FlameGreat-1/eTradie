package consent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Store handles consent persistence in PostgreSQL.
//
// The store is intentionally tiny: every write is an append, every
// read is either a single-row "latest" lookup keyed on an indexed
// column or a bounded history scan. The model is immutable by design
// so GDPR Art. 7.1 ("the controller shall be able to demonstrate that
// the data subject has consented") is satisfied without any
// after-the-fact reasoning about updates.
type Store struct {
	pool *pgxpool.Pool
}

// NewStore creates a consent store backed by the given pool.
func NewStore(pool *pgxpool.Pool) *Store {
	return &Store{pool: pool}
}

// InsertParams is the input to Store.Insert. The split between an
// optional UserID (nil when the visitor has not yet signed in) and a
// mandatory AnonymousID is what implements anonymous-then-attach.
type InsertParams struct {
	UserID        *string
	AnonymousID   string
	PolicyVersion string
	Categories    Categories
	IPHash        string
	UserAgent     string
}

// Insert appends a new consent decision and returns the materialised
// row. The store guarantees the returned Record's timestamp is the
// authoritative server time, not whatever the client claimed.
func (s *Store) Insert(ctx context.Context, p InsertParams) (*Record, error) {
	if err := ValidateAnonymousID(p.AnonymousID); err != nil {
		return nil, err
	}
	if err := ValidatePolicyVersion(p.PolicyVersion); err != nil {
		return nil, err
	}

	catsJSON, err := json.Marshal(p.Categories)
	if err != nil {
		// json.Marshal on a typed struct of bools cannot fail in
		// practice; surface as a wrapped error for paranoia.
		return nil, fmt.Errorf("consent: marshal categories: %w", err)
	}

	id := generateID()
	now := time.Now().UTC()
	ua := TruncateUserAgent(p.UserAgent)

	_, err = s.pool.Exec(ctx,
		`INSERT INTO consent_records
		   (id, user_id, anonymous_id, policy_version, categories, ip_hash, user_agent, created_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
		id, p.UserID, p.AnonymousID, p.PolicyVersion, catsJSON, p.IPHash, ua, now,
	)
	if err != nil {
		return nil, fmt.Errorf("consent: insert: %w", err)
	}

	return &Record{
		ID:            id,
		UserID:        p.UserID,
		AnonymousID:   p.AnonymousID,
		PolicyVersion: p.PolicyVersion,
		Categories:    p.Categories,
		CreatedAt:     now,
	}, nil
}

// LatestForAnonymousID returns the most recent decision for an
// anonymous identifier, or (nil, nil) when no decision has been
// recorded. Used by GET /api/v1/consent so the SPA can reconcile its
// local cache with the server on every load.
func (s *Store) LatestForAnonymousID(ctx context.Context, anonymousID string) (*Record, error) {
	if err := ValidateAnonymousID(anonymousID); err != nil {
		return nil, err
	}
	return s.queryLatest(ctx,
		`SELECT id, user_id, anonymous_id, policy_version, categories, created_at
		   FROM consent_records
		  WHERE anonymous_id = $1
		  ORDER BY created_at DESC
		  LIMIT 1`,
		anonymousID,
	)
}

// LatestForUserID returns the most recent decision for an
// authenticated user. Used after attach-on-login so the SPA can pick
// up a decision the user made on a previous device.
func (s *Store) LatestForUserID(ctx context.Context, userID string) (*Record, error) {
	if userID == "" {
		return nil, errors.New("consent: empty user_id")
	}
	return s.queryLatest(ctx,
		`SELECT id, user_id, anonymous_id, policy_version, categories, created_at
		   FROM consent_records
		  WHERE user_id = $1
		  ORDER BY created_at DESC
		  LIMIT 1`,
		userID,
	)
}

// HistoryForUserID returns up to `limit` most-recent decisions for an
// authenticated user, ordered newest-first. Backs the GDPR Article 15
// right-of-access response surfaced by GET /api/v1/consent/history.
//
// The hard upper bound is enforced here (not at the handler) so a
// future caller from inside the gateway cannot accidentally request a
// thousand rows.
func (s *Store) HistoryForUserID(ctx context.Context, userID string, limit int) ([]Record, error) {
	if userID == "" {
		return nil, errors.New("consent: empty user_id")
	}
	if limit <= 0 {
		limit = 25
	}
	if limit > 100 {
		limit = 100
	}

	rows, err := s.pool.Query(ctx,
		`SELECT id, user_id, anonymous_id, policy_version, categories, created_at
		   FROM consent_records
		  WHERE user_id = $1
		  ORDER BY created_at DESC
		  LIMIT $2`,
		userID, limit,
	)
	if err != nil {
		return nil, fmt.Errorf("consent: history query: %w", err)
	}
	defer rows.Close()

	out := make([]Record, 0, limit)
	for rows.Next() {
		rec, err := scanRecord(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, *rec)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("consent: history scan: %w", err)
	}
	return out, nil
}

// DefaultRetention is the recommended GDPR Art. 5(1)(e) storage
// limitation window for consent records: 24 months. Operators may
// pass a different duration to DeleteExpired when their DPO has
// approved an alternative retention policy.
const DefaultRetention = 24 * 30 * 24 * time.Hour

// DeleteExpired removes every consent_records row strictly older than
// cutoff EXCEPT the most recent row per anonymous_id AND the most
// recent row per user_id. The retained rows are the legally-required
// proof of consent under GDPR Art. 7.1 and must be preserved while
// the visitor / user is still relevant.
//
// Returns the number of rows deleted. The SQL is a single statement
// so the deletion is atomic; the latest-per-key sub-queries are
// served by the existing (anonymous_id, created_at DESC) and
// (user_id, created_at DESC) WHERE user_id IS NOT NULL indexes.
func (s *Store) DeleteExpired(ctx context.Context, cutoff time.Time) (int64, error) {
	if cutoff.IsZero() {
		return 0, errors.New("consent: DeleteExpired: zero cutoff")
	}
	tag, err := s.pool.Exec(ctx,
		`DELETE FROM consent_records
		  WHERE created_at < $1
		    AND id NOT IN (
		      SELECT DISTINCT ON (anonymous_id) id
		        FROM consent_records
		       ORDER BY anonymous_id, created_at DESC
		    )
		    AND (
		      user_id IS NULL
		      OR id NOT IN (
		        SELECT DISTINCT ON (user_id) id
		          FROM consent_records
		         WHERE user_id IS NOT NULL
		         ORDER BY user_id, created_at DESC
		      )
		    )`,
		cutoff,
	)
	if err != nil {
		return 0, fmt.Errorf("consent: delete expired: %w", err)
	}
	return tag.RowsAffected(), nil
}

// AttachAnonymousToUser links every consent_records row currently
// keyed only on the given anonymous_id to the supplied user_id. The
// original timestamps are preserved — the column we update is
// user_id only — so the row that legally represents the moment of
// consent stays intact.
//
// Returns the number of rows attached.
func (s *Store) AttachAnonymousToUser(ctx context.Context, anonymousID, userID string) (int64, error) {
	if err := ValidateAnonymousID(anonymousID); err != nil {
		return 0, err
	}
	if userID == "" {
		return 0, errors.New("consent: empty user_id")
	}
	tag, err := s.pool.Exec(ctx,
		`UPDATE consent_records
		    SET user_id = $1
		  WHERE anonymous_id = $2
		    AND user_id IS NULL`,
		userID, anonymousID,
	)
	if err != nil {
		return 0, fmt.Errorf("consent: attach: %w", err)
	}
	return tag.RowsAffected(), nil
}

// ----------------------------------------------------------------------
// Internal scan helpers
// ----------------------------------------------------------------------

func (s *Store) queryLatest(ctx context.Context, sql string, args ...any) (*Record, error) {
	row := s.pool.QueryRow(ctx, sql, args...)
	rec, err := scanRecord(row)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return rec, nil
}

// rowScanner is the minimal interface satisfied by both pgx.Row and
// pgx.Rows so the same scan logic powers QueryRow and Query paths.
type rowScanner interface {
	Scan(dest ...any) error
}

func scanRecord(r rowScanner) (*Record, error) {
	var (
		rec     Record
		userID  *string
		catsRaw []byte
	)
	if err := r.Scan(&rec.ID, &userID, &rec.AnonymousID, &rec.PolicyVersion, &catsRaw, &rec.CreatedAt); err != nil {
		return nil, err
	}
	if err := json.Unmarshal(catsRaw, &rec.Categories); err != nil {
		return nil, fmt.Errorf("consent: unmarshal categories: %w", err)
	}
	rec.UserID = userID
	return &rec, nil
}
