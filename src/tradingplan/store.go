package tradingplan

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
// user. Callers map this to a 404 or treat it as Status='none'
// depending on the endpoint contract.
var ErrNotFound = errors.New("tradingplan: no record")

// Store handles persistence of user trading plans in PostgreSQL.
// Shares the auth_users pool with auth, billing, consent, support,
// and tradingsystem so we inherit one connection budget.
type Store struct {
	pool *pgxpool.Pool
}

// NewStore creates a Store backed by the given connection pool.
func NewStore(pool *pgxpool.Pool) *Store {
	return &Store{pool: pool}
}

// Get returns the full record (including the JSONB plan) for the
// given user. Returns ErrNotFound when no row exists.
func (s *Store) Get(ctx context.Context, userID string) (*Record, error) {
	var (
		rec     Record
		planRaw []byte
	)
	rec.UserID = userID
	err := s.pool.QueryRow(ctx,
		`SELECT status, version, plan, last_error, created_at, updated_at
		   FROM user_trading_plans
		  WHERE user_id = $1`, userID,
	).Scan(&rec.Status, &rec.Version, &planRaw, &rec.LastError, &rec.CreatedAt, &rec.UpdatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("tradingplan.Get: %w", err)
	}

	if len(planRaw) > 0 {
		var p Plan
		if err := json.Unmarshal(planRaw, &p); err != nil {
			return nil, fmt.Errorf("tradingplan.Get: unmarshal plan: %w", err)
		}
		rec.Plan = &p
	}
	return &rec, nil
}

// GetStatus returns the lightweight projection used by the dashboard.
// Does NOT hydrate the JSONB plan column so it stays cheap on every
// page load (the workbook can be tens of kilobytes once filled in).
func (s *Store) GetStatus(ctx context.Context, userID string) (*StatusView, error) {
	var (
		status    Status
		version   int
		lastErr   string
		updatedAt time.Time
		hasPlan   bool
	)
	err := s.pool.QueryRow(ctx,
		`SELECT status, version, last_error, updated_at, plan IS NOT NULL
		   FROM user_trading_plans
		  WHERE user_id = $1`, userID,
	).Scan(&status, &version, &lastErr, &updatedAt, &hasPlan)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return &StatusView{
				Status:    StatusNone,
				Version:   0,
				HasPlan:   false,
				UpdatedAt: nil,
			}, nil
		}
		return nil, fmt.Errorf("tradingplan.GetStatus: %w", err)
	}
	return &StatusView{
		Status:    status,
		Version:   version,
		HasPlan:   hasPlan,
		LastError: lastErr,
		UpdatedAt: &updatedAt,
	}, nil
}

// MarkGenerating flips the row to status='generating' WITHOUT
// clearing an existing plan. The previous successful plan stays
// visible to the SPA while a new one is being generated so the UI
// never goes blank during a regenerate.
//
// last_error is cleared on every transition into 'generating' so a
// stale error from a prior attempt is not displayed alongside a
// fresh in-flight generation.
func (s *Store) MarkGenerating(ctx context.Context, userID string) error {
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx,
		`INSERT INTO user_trading_plans (user_id, status, version, plan, last_error, created_at, updated_at)
		      VALUES ($1, 'generating', 0, NULL, '', $2, $2)
		 ON CONFLICT (user_id) DO UPDATE
		    SET status     = 'generating',
		        last_error = '',
		        updated_at = EXCLUDED.updated_at`,
		userID, now,
	)
	if err != nil {
		return fmt.Errorf("tradingplan.MarkGenerating: %w", err)
	}
	return nil
}

// MarkFailed records a generation failure WITHOUT clearing any
// previously successful plan. The user sees their last good plan
// alongside a retry banner. message must be a short user-safe string
// (no stack traces, no internal IDs); the caller is responsible for
// scrubbing.
func (s *Store) MarkFailed(ctx context.Context, userID, message string) error {
	now := time.Now().UTC()
	if len(message) > 512 {
		message = message[:512]
	}
	_, err := s.pool.Exec(ctx,
		`INSERT INTO user_trading_plans (user_id, status, version, plan, last_error, created_at, updated_at)
		      VALUES ($1, 'failed', 0, NULL, $2, $3, $3)
		 ON CONFLICT (user_id) DO UPDATE
		    SET status     = 'failed',
		        last_error = EXCLUDED.last_error,
		        updated_at = EXCLUDED.updated_at`,
		userID, message, now,
	)
	if err != nil {
		return fmt.Errorf("tradingplan.MarkFailed: %w", err)
	}
	return nil
}

// Save upserts an ACTIVE plan for the user, bumping the version
// counter and clearing any prior last_error. This is the only path
// that ever writes the plan column; MarkGenerating and MarkFailed
// use narrow statements so we never accidentally clobber a plan on a
// status-only update.
func (s *Store) Save(ctx context.Context, userID string, plan *Plan) (*Record, error) {
	if plan == nil {
		return nil, errors.New("tradingplan.Save: plan is nil")
	}
	plan.SchemaVersion = CurrentSchemaVersion
	if plan.GeneratedAt.IsZero() {
		plan.GeneratedAt = time.Now().UTC()
	}
	if plan.GeneratedBy == "" {
		plan.GeneratedBy = "Exoper AI"
	}

	raw, err := json.Marshal(plan)
	if err != nil {
		return nil, fmt.Errorf("tradingplan.Save: marshal: %w", err)
	}

	now := time.Now().UTC()
	var (
		outStatus    Status
		outVersion   int
		outCreatedAt time.Time
		outUpdatedAt time.Time
	)
	err = s.pool.QueryRow(ctx,
		`INSERT INTO user_trading_plans (user_id, status, version, plan, last_error, created_at, updated_at)
		      VALUES ($1, 'active', 1, $2, '', $3, $3)
		 ON CONFLICT (user_id) DO UPDATE
		    SET status     = 'active',
		        version    = user_trading_plans.version + 1,
		        plan       = EXCLUDED.plan,
		        last_error = '',
		        updated_at = EXCLUDED.updated_at
		  RETURNING status, version, created_at, updated_at`,
		userID, raw, now,
	).Scan(&outStatus, &outVersion, &outCreatedAt, &outUpdatedAt)
	if err != nil {
		return nil, fmt.Errorf("tradingplan.Save: upsert: %w", err)
	}

	return &Record{
		UserID:    userID,
		Status:    outStatus,
		Version:   outVersion,
		Plan:      plan,
		CreatedAt: outCreatedAt,
		UpdatedAt: outUpdatedAt,
	}, nil
}

// UpdatePlanContent replaces ONLY the JSONB plan blob (without
// bumping the version) and leaves status='active'. Used by the
// frontend's in-app editor when the user adds journal rows, edits a
// scorecard score, or tweaks an objective. The version field is
// reserved for full LLM regenerations so a comparison between
// version 1 and version 2 always represents a fresh AI pass, not a
// manual edit.
func (s *Store) UpdatePlanContent(ctx context.Context, userID string, plan *Plan) (*Record, error) {
	if plan == nil {
		return nil, errors.New("tradingplan.UpdatePlanContent: plan is nil")
	}
	plan.SchemaVersion = CurrentSchemaVersion

	raw, err := json.Marshal(plan)
	if err != nil {
		return nil, fmt.Errorf("tradingplan.UpdatePlanContent: marshal: %w", err)
	}

	now := time.Now().UTC()
	var (
		outStatus    Status
		outVersion   int
		outCreatedAt time.Time
		outUpdatedAt time.Time
	)
	err = s.pool.QueryRow(ctx,
		`UPDATE user_trading_plans
		    SET plan       = $2,
		        status     = 'active',
		        last_error = '',
		        updated_at = $3
		  WHERE user_id = $1
		  RETURNING status, version, created_at, updated_at`,
		userID, raw, now,
	).Scan(&outStatus, &outVersion, &outCreatedAt, &outUpdatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("tradingplan.UpdatePlanContent: %w", err)
	}

	return &Record{
		UserID:    userID,
		Status:    outStatus,
		Version:   outVersion,
		Plan:      plan,
		CreatedAt: outCreatedAt,
		UpdatedAt: outUpdatedAt,
	}, nil
}

// AutoFillJournal merges the user's manual-trade objective facts into
// the existing journal rows of the stored plan and persists the result
// ATOMICALLY under a row lock. It is the single source of truth for the
// journal auto-populate write path; the handler never does its own
// read-modify-write (which would race across concurrent loads).
//
// Concurrency: the row is locked with SELECT ... FOR UPDATE for the
// duration of the transaction, so two concurrent plan loads for the
// same user serialise here — the "claim the next blank row" decision and
// the persist are atomic, eliminating the double-bind / lost-update
// window.
//
// Semantics: this is an auto-fill, NOT a user edit, so it updates ONLY
// the plan blob and updated_at — status and version are left untouched.
// It is a no-op (returns the loaded plan, changed=false) when the user
// has no row, the row has no plan, or the merge changed nothing. loc
// renders the Date cell (nil -> UTC).
//
// Returns the effective plan (merged when changed, otherwise the loaded
// plan), whether it changed, and any error. ErrNotFound is returned
// when the user has no plan row so the caller can treat it as "nothing
// to fill".
func (s *Store) AutoFillJournal(
	ctx context.Context,
	userID string,
	facts []ManualTradeFact,
	loc *time.Location,
) (*Plan, mergeStats, error) {
	var zero mergeStats
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return nil, zero, fmt.Errorf("tradingplan.AutoFillJournal: begin: %w", err)
	}
	// Rollback is a no-op after a successful Commit; safe to always defer.
	defer func() { _ = tx.Rollback(ctx) }()

	var planRaw []byte
	err = tx.QueryRow(ctx,
		`SELECT plan FROM user_trading_plans WHERE user_id = $1 FOR UPDATE`,
		userID,
	).Scan(&planRaw)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, zero, ErrNotFound
		}
		return nil, zero, fmt.Errorf("tradingplan.AutoFillJournal: select for update: %w", err)
	}
	if len(planRaw) == 0 {
		// Row exists but no plan blob (e.g. status='generating'/'none').
		// Nothing to auto-fill; commit the (empty) tx to release the lock.
		if err := tx.Commit(ctx); err != nil {
			return nil, zero, fmt.Errorf("tradingplan.AutoFillJournal: commit: %w", err)
		}
		return nil, zero, nil
	}

	var plan Plan
	if err := json.Unmarshal(planRaw, &plan); err != nil {
		return nil, zero, fmt.Errorf("tradingplan.AutoFillJournal: unmarshal: %w", err)
	}

	stats := mergeManualTrades(&plan, facts, loc, time.Now().UTC())
	if !stats.changed() {
		// No objective cell changed (possibly only capped); release the
		// lock without a write. Stats are still returned so the caller
		// can surface a cap-hit (stats.Capped) even on a no-write pass.
		if err := tx.Commit(ctx); err != nil {
			return nil, zero, fmt.Errorf("tradingplan.AutoFillJournal: commit: %w", err)
		}
		return &plan, stats, nil
	}

	plan.SchemaVersion = CurrentSchemaVersion
	raw, err := json.Marshal(&plan)
	if err != nil {
		return nil, zero, fmt.Errorf("tradingplan.AutoFillJournal: marshal: %w", err)
	}

	// Update ONLY the plan blob + updated_at. status/version are an
	// auto-fill no-op (this is not a user edit nor an LLM regeneration).
	if _, err := tx.Exec(ctx,
		`UPDATE user_trading_plans
		    SET plan = $2, updated_at = $3
		  WHERE user_id = $1`,
		userID, raw, time.Now().UTC(),
	); err != nil {
		return nil, zero, fmt.Errorf("tradingplan.AutoFillJournal: update: %w", err)
	}

	if err := tx.Commit(ctx); err != nil {
		return nil, zero, fmt.Errorf("tradingplan.AutoFillJournal: commit: %w", err)
	}
	return &plan, stats, nil
}

// ReapStaleGenerating flips any row in status='generating' whose
// updated_at is older than `staleness` to status='failed' with a
// short user-safe message. This is the safety net for the case where
// the engine's fail-callback never lands (engine crash mid-flight,
// gateway downtime that outlasts the engine's 3-attempt retry, etc.):
// without it, the SPA renders an indefinite "generating" spinner.
//
// Returns the number of rows reaped so the operator can correlate
// reaper hits to engine outages. Idempotent and side-effect-free for
// rows that are not stale.
//
// The threshold is supplied by the caller rather than hard-coded so
// the wiring layer (the gateway main loop) owns the policy and tests
// can drive the boundary deterministically. 5 minutes is the
// production default; the engine's worst-case end-to-end (metering
// reserve + 3-attempt LLM retry with backoff + callback delivery)
// sits comfortably under 2 minutes, so 5 minutes never trips a
// legitimate in-flight job.
func (s *Store) ReapStaleGenerating(ctx context.Context, staleness time.Duration) (int64, error) {
	if staleness <= 0 {
		return 0, errors.New("tradingplan.ReapStaleGenerating: staleness must be > 0")
	}
	now := time.Now().UTC()
	cutoff := now.Add(-staleness)
	const message = "generation timed out; please retry"
	res, err := s.pool.Exec(ctx,
		`UPDATE user_trading_plans
		    SET status     = 'failed',
		        last_error = $1,
		        updated_at = $2
		  WHERE status     = 'generating'
		    AND updated_at < $3`,
		message, now, cutoff,
	)
	if err != nil {
		return 0, fmt.Errorf("tradingplan.ReapStaleGenerating: %w", err)
	}
	return res.RowsAffected(), nil
}

// Reset clears the plan and returns the user to status='none'. Used
// by the dashboard's "start over" affordance and on Trading System
// reset (the plan is derived from the system; clearing the system
// without clearing the plan would leave a stale workbook).
// Idempotent; safe to call on a user who never had a row.
func (s *Store) Reset(ctx context.Context, userID string) error {
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx,
		`INSERT INTO user_trading_plans (user_id, status, version, plan, last_error, created_at, updated_at)
		      VALUES ($1, 'none', 0, NULL, '', $2, $2)
		 ON CONFLICT (user_id) DO UPDATE
		    SET status     = 'none',
		        version    = 0,
		        plan       = NULL,
		        last_error = '',
		        updated_at = EXCLUDED.updated_at`,
		userID, now,
	)
	if err != nil {
		return fmt.Errorf("tradingplan.Reset: %w", err)
	}
	return nil
}
