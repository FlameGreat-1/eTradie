package performancereview

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ErrNotFound is returned by Get when no row exists for the given
// (user_id, period, period_start). Mirrors tradingplan.ErrNotFound
// so callers reuse the same error-handling shape.
var ErrNotFound = errors.New("performancereview: no record")

// Store handles persistence of user performance reviews in
// PostgreSQL. Shares the auth_users pool with auth, billing, consent,
// support, tradingsystem, and tradingplan so we inherit one
// connection budget.
type Store struct {
	pool *pgxpool.Pool
}

// NewStore creates a Store backed by the given connection pool.
func NewStore(pool *pgxpool.Pool) *Store {
	return &Store{pool: pool}
}

// MarkGenerating creates (or refreshes) a row for the given window
// with status='generating'. The review column stays NULL while the
// LLM call is in flight. A concurrent regenerate of the same window
// upserts on the unique constraint.
//
// last_error is always cleared on transition into 'generating' so a
// stale error from a prior attempt is not displayed alongside an
// in-flight regeneration.
//
// Returns the row id so the caller (the handler) can include it in
// the engine dispatch payload; the engine echoes it back in the
// callback so the gateway can update the exact row even if the
// composite key was rounded differently downstream.
func (s *Store) MarkGenerating(
	ctx context.Context,
	userID string,
	period Period,
	periodStart, periodEnd time.Time,
) (int64, error) {
	if userID == "" {
		return 0, errors.New("performancereview.MarkGenerating: user_id is required")
	}
	if !period.IsValid() {
		return 0, fmt.Errorf("performancereview.MarkGenerating: invalid period %q", string(period))
	}
	if periodEnd.Before(periodStart) {
		return 0, errors.New("performancereview.MarkGenerating: period_end must be on or after period_start")
	}

	now := time.Now().UTC()
	var id int64
	err := s.pool.QueryRow(ctx, `
		INSERT INTO user_performance_reviews
		  (user_id, period, period_start, period_end, status, review, last_error, created_at, updated_at)
		VALUES ($1, $2, $3, $4, 'generating', NULL, '', $5, $5)
		ON CONFLICT (user_id, period, period_start) DO UPDATE
		   SET status      = 'generating',
		       period_end  = EXCLUDED.period_end,
		       last_error  = '',
		       updated_at  = EXCLUDED.updated_at
		RETURNING id`,
		userID, string(period), periodStart, periodEnd, now,
	).Scan(&id)
	if err != nil {
		return 0, fmt.Errorf("performancereview.MarkGenerating: %w", err)
	}
	return id, nil
}

// MarkFailed records a generation failure WITHOUT clearing any prior
// review on the same window. message must be a short user-safe string
// (no stack traces, no internal IDs).
func (s *Store) MarkFailed(
	ctx context.Context,
	userID string,
	period Period,
	periodStart time.Time,
	message string,
) error {
	if userID == "" {
		return errors.New("performancereview.MarkFailed: user_id is required")
	}
	if len(message) > 512 {
		message = message[:512]
	}
	now := time.Now().UTC()
	res, err := s.pool.Exec(ctx, `
		UPDATE user_performance_reviews
		   SET status     = 'failed',
		       last_error = $4,
		       updated_at = $5
		 WHERE user_id      = $1
		   AND period       = $2
		   AND period_start = $3`,
		userID, string(period), periodStart, message, now,
	)
	if err != nil {
		return fmt.Errorf("performancereview.MarkFailed: %w", err)
	}
	if res.RowsAffected() == 0 {
		return ErrNotFound
	}
	return nil
}

// Save persists a validated review and flips the row to status='ready'.
// Updates the existing (user_id, period, period_start) row written by
// MarkGenerating; if the row was lost (manual deletion, retention
// sweep) we INSERT a fresh one so the engine callback is never
// dropped silently.
func (s *Store) Save(
	ctx context.Context,
	userID string,
	review *Review,
) (*Record, error) {
	if userID == "" {
		return nil, errors.New("performancereview.Save: user_id is required")
	}
	if review == nil {
		return nil, errors.New("performancereview.Save: review is nil")
	}
	if !review.Period.IsValid() {
		return nil, fmt.Errorf("performancereview.Save: invalid period %q", string(review.Period))
	}
	review.SchemaVersion = CurrentSchemaVersion
	if review.GeneratedAt.IsZero() {
		review.GeneratedAt = time.Now().UTC()
	}
	if review.GeneratedBy == "" {
		review.GeneratedBy = "Exoper AI"
	}

	raw, err := json.Marshal(review)
	if err != nil {
		return nil, fmt.Errorf("performancereview.Save: marshal: %w", err)
	}

	now := time.Now().UTC()
	var (
		id        int64
		createdAt time.Time
		updatedAt time.Time
	)
	err = s.pool.QueryRow(ctx, `
		INSERT INTO user_performance_reviews
		  (user_id, period, period_start, period_end, status, review, last_error, created_at, updated_at)
		VALUES ($1, $2, $3, $4, 'ready', $5, '', $6, $6)
		ON CONFLICT (user_id, period, period_start) DO UPDATE
		   SET status     = 'ready',
		       period_end = EXCLUDED.period_end,
		       review     = EXCLUDED.review,
		       last_error = '',
		       updated_at = EXCLUDED.updated_at
		RETURNING id, created_at, updated_at`,
		userID, string(review.Period), review.PeriodStart, review.PeriodEnd, raw, now,
	).Scan(&id, &createdAt, &updatedAt)
	if err != nil {
		return nil, fmt.Errorf("performancereview.Save: upsert: %w", err)
	}

	return &Record{
		ID:          id,
		UserID:      userID,
		Period:      review.Period,
		PeriodStart: review.PeriodStart,
		PeriodEnd:   review.PeriodEnd,
		Status:      StatusReady,
		Review:      review,
		CreatedAt:   createdAt,
		UpdatedAt:   updatedAt,
	}, nil
}

// GetLatest returns the most recently updated row for the given user
// and period. Returns ErrNotFound when no row exists.
//
// A row in status='generating' is returned with Review==nil so the
// SPA can render a friendly progress state; status='failed' is
// returned with LastError populated.
func (s *Store) GetLatest(
	ctx context.Context,
	userID string,
	period Period,
) (*Record, error) {
	if userID == "" {
		return nil, errors.New("performancereview.GetLatest: user_id is required")
	}
	if !period.IsValid() {
		return nil, fmt.Errorf("performancereview.GetLatest: invalid period %q", string(period))
	}
	var (
		rec       Record
		reviewRaw []byte
	)
	rec.UserID = userID
	rec.Period = period
	err := s.pool.QueryRow(ctx, `
		SELECT id, period_start, period_end, status, review, last_error, created_at, updated_at
		  FROM user_performance_reviews
		 WHERE user_id = $1
		   AND period  = $2
		 ORDER BY updated_at DESC
		 LIMIT 1`,
		userID, string(period),
	).Scan(
		&rec.ID, &rec.PeriodStart, &rec.PeriodEnd,
		&rec.Status, &reviewRaw, &rec.LastError,
		&rec.CreatedAt, &rec.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("performancereview.GetLatest: %w", err)
	}
	if len(reviewRaw) > 0 {
		var r Review
		if err := json.Unmarshal(reviewRaw, &r); err != nil {
			return nil, fmt.Errorf("performancereview.GetLatest: unmarshal: %w", err)
		}
		rec.Review = &r
	}
	return &rec, nil
}

// GetByID returns a specific row by id, scoped by user_id. Returns
// ErrNotFound on miss or cross-tenant lookup.
func (s *Store) GetByID(ctx context.Context, userID string, id int64) (*Record, error) {
	if userID == "" {
		return nil, errors.New("performancereview.GetByID: user_id is required")
	}
	var (
		rec       Record
		reviewRaw []byte
		period    string
	)
	rec.UserID = userID
	rec.ID = id
	err := s.pool.QueryRow(ctx, `
		SELECT period, period_start, period_end, status, review, last_error, created_at, updated_at
		  FROM user_performance_reviews
		 WHERE id      = $1
		   AND user_id = $2`,
		id, userID,
	).Scan(
		&period, &rec.PeriodStart, &rec.PeriodEnd,
		&rec.Status, &reviewRaw, &rec.LastError,
		&rec.CreatedAt, &rec.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("performancereview.GetByID: %w", err)
	}
	rec.Period = Period(period)
	if len(reviewRaw) > 0 {
		var r Review
		if err := json.Unmarshal(reviewRaw, &r); err != nil {
			return nil, fmt.Errorf("performancereview.GetByID: unmarshal: %w", err)
		}
		rec.Review = &r
	}
	return &rec, nil
}

// ListHistory returns paginated history for the user, optionally
// filtered by period. Order is updated_at DESC so the SPA renders
// newest first. limit is clamped to HistoryMaxLimit; offset is
// floored at 0. Returns the page slice and the total count for
// pagination controls.
//
// review payloads are NOT hydrated in the list query - that keeps
// the response small even when a user has many monthly rows. The
// SPA fetches the full review on demand via GetByID.
func (s *Store) ListHistory(
	ctx context.Context,
	userID string,
	period Period,
	offset, limit int,
) ([]*Record, int, error) {
	if userID == "" {
		return nil, 0, errors.New("performancereview.ListHistory: user_id is required")
	}
	if offset < 0 {
		offset = 0
	}
	if limit <= 0 {
		limit = HistoryDefaultLimit
	}
	if limit > HistoryMaxLimit {
		limit = HistoryMaxLimit
	}

	where := "WHERE user_id = $1"
	args := []interface{}{userID}
	idx := 2
	if period != "" {
		if !period.IsValid() {
			return nil, 0, fmt.Errorf("performancereview.ListHistory: invalid period %q", string(period))
		}
		where += fmt.Sprintf(" AND period = $%d", idx)
		args = append(args, string(period))
		idx++
	}

	var total int
	countQuery := fmt.Sprintf(
		"SELECT COUNT(*) FROM user_performance_reviews %s", where,
	)
	if err := s.pool.QueryRow(ctx, countQuery, args...).Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("performancereview.ListHistory: count: %w", err)
	}

	query := fmt.Sprintf(`
		SELECT id, period, period_start, period_end, status, last_error, created_at, updated_at
		  FROM user_performance_reviews
		  %s
		 ORDER BY updated_at DESC
		 LIMIT $%d OFFSET $%d`, where, idx, idx+1,
	)
	args = append(args, limit, offset)

	rows, err := s.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("performancereview.ListHistory: query: %w", err)
	}
	defer rows.Close()

	out := make([]*Record, 0, limit)
	for rows.Next() {
		var (
			rec    Record
			period string
		)
		rec.UserID = userID
		if err := rows.Scan(
			&rec.ID, &period, &rec.PeriodStart, &rec.PeriodEnd,
			&rec.Status, &rec.LastError, &rec.CreatedAt, &rec.UpdatedAt,
		); err != nil {
			return nil, 0, fmt.Errorf("performancereview.ListHistory: scan: %w", err)
		}
		rec.Period = Period(period)
		out = append(out, &rec)
	}
	return out, total, nil
}

// GetLatestReadyBefore returns the most recent ready row strictly
// before `before`. Used by the engine generator to compute trader-
// evolution deltas (PLAN.md section 12) without re-running the LLM
// over the prior window's raw data.
//
// Returns ErrNotFound when there is no prior ready row.
func (s *Store) GetLatestReadyBefore(
	ctx context.Context,
	userID string,
	period Period,
	before time.Time,
) (*Record, error) {
	if userID == "" {
		return nil, errors.New("performancereview.GetLatestReadyBefore: user_id is required")
	}
	if !period.IsValid() {
		return nil, fmt.Errorf("performancereview.GetLatestReadyBefore: invalid period %q", string(period))
	}
	var (
		rec       Record
		reviewRaw []byte
	)
	rec.UserID = userID
	rec.Period = period
	err := s.pool.QueryRow(ctx, `
		SELECT id, period_start, period_end, status, review, last_error, created_at, updated_at
		  FROM user_performance_reviews
		 WHERE user_id      = $1
		   AND period       = $2
		   AND status       = 'ready'
		   AND period_start < $3
		 ORDER BY period_start DESC
		 LIMIT 1`,
		userID, string(period), before,
	).Scan(
		&rec.ID, &rec.PeriodStart, &rec.PeriodEnd,
		&rec.Status, &reviewRaw, &rec.LastError,
		&rec.CreatedAt, &rec.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("performancereview.GetLatestReadyBefore: %w", err)
	}
	if len(reviewRaw) > 0 {
		var r Review
		if err := json.Unmarshal(reviewRaw, &r); err != nil {
			return nil, fmt.Errorf("performancereview.GetLatestReadyBefore: unmarshal: %w", err)
		}
		rec.Review = &r
	}
	return &rec, nil
}
