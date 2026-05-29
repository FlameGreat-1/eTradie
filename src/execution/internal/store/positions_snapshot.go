package store

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

// PositionSnapshotStore persists per-user engine-position views into
// execution_positions_snapshot. Each snapshot is INSERT-only; the
// table's BEFORE UPDATE/DELETE trigger (added in Section 7 Step B)
// blocks mutation from the app role.
//
// Used by the reconciler (write) and by the Step B replay endpoint
// (read).
//
// Audit ref: CHECKLIST Section 7.
type PositionSnapshotStore struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

// NewPositionSnapshotStore constructs a snapshot store backed by the
// given pgx pool.
func NewPositionSnapshotStore(pool *pgxpool.Pool) *PositionSnapshotStore {
	return &PositionSnapshotStore{
		pool: pool,
		log:  observability.Logger("position_snapshot_store"),
	}
}

// SnapshotRow is the in-process representation of one persisted
// snapshot. positions is the deserialised JSON payload.
type SnapshotRow struct {
	ID             int64
	UserID         string
	SnapshotTS     time.Time
	PositionCount  int
	Positions      []models.Position
	ContentHash    string
	ReconcileRunID string
}

// WriteSnapshot persists a snapshot of the user's current positions.
//
// The positions slice is canonicalised by sorting on OrderID before
// serialisation so the content_hash is deterministic regardless of
// broker reply order. The hash is the sha256 of the canonicalised
// JSON bytes; it lives in the row for tamper detection (a future
// audit pass can recompute it and compare).
//
// reconcileRunID is an opaque label the reconciler can attach to
// correlate snapshots from the same cycle across users; pass ""
// when not used.
//
// The whole operation is bounded by a 5s context timeout. The caller
// (reconciler) logs the error and continues; a snapshot write must
// NEVER block the reconcile cycle.
func (s *PositionSnapshotStore) WriteSnapshot(
	ctx context.Context,
	userID string,
	positions []models.Position,
	reconcileRunID string,
) error {
	if userID == "" {
		return fmt.Errorf("snapshot user_id must not be empty")
	}

	// Canonicalise to make content_hash stable.
	canonical := make([]models.Position, len(positions))
	copy(canonical, positions)
	sort.Slice(canonical, func(i, j int) bool {
		return canonical[i].OrderID < canonical[j].OrderID
	})

	jsonBytes, err := json.Marshal(canonical)
	if err != nil {
		s.log.Warn().Err(err).Str("user_id", userID).Msg("snapshot_marshal_failed")
		return fmt.Errorf("snapshot marshal for %s: %w", userID, err)
	}

	sum := sha256.Sum256(jsonBytes)
	hash := hex.EncodeToString(sum[:])

	writeCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	_, err = s.pool.Exec(writeCtx, `
		INSERT INTO execution_positions_snapshot
		  (user_id, snapshot_ts, position_count, positions, content_hash, reconcile_run_id)
		VALUES ($1, $2, $3, $4::jsonb, $5, $6)
	`,
		userID,
		time.Now().UTC(),
		len(canonical),
		jsonBytes,
		hash,
		reconcileRunID,
	)
	if err != nil {
		s.log.Warn().Err(err).Str("user_id", userID).Msg("snapshot_insert_failed")
		return fmt.Errorf("snapshot insert for %s: %w", userID, err)
	}
	return nil
}

// LatestSnapshot returns the most recent snapshot for the user.
//
// Returns (nil, nil) when no snapshot exists (typical on first boot
// or for a brand-new user) so callers can branch without nil-error
// checks. Any other error is returned wrapped.
func (s *PositionSnapshotStore) LatestSnapshot(
	ctx context.Context, userID string,
) (*SnapshotRow, error) {
	if userID == "" {
		return nil, fmt.Errorf("snapshot user_id must not be empty")
	}
	row := s.pool.QueryRow(ctx, `
		SELECT id, user_id, snapshot_ts, position_count, positions, content_hash, reconcile_run_id
		FROM execution_positions_snapshot
		WHERE user_id = $1
		ORDER BY snapshot_ts DESC
		LIMIT 1
	`, userID)

	var (
		r     SnapshotRow
		rawJS []byte
	)
	err := row.Scan(
		&r.ID,
		&r.UserID,
		&r.SnapshotTS,
		&r.PositionCount,
		&rawJS,
		&r.ContentHash,
		&r.ReconcileRunID,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, fmt.Errorf("latest snapshot for %s: %w", userID, err)
	}
	if err := json.Unmarshal(rawJS, &r.Positions); err != nil {
		return nil, fmt.Errorf("unmarshal latest snapshot positions for %s: %w", userID, err)
	}
	return &r, nil
}

// SnapshotsBetween returns every snapshot for the user within the
// inclusive timestamp range, ordered chronologically.
//
// Caller is responsible for bounding the range; the store does NOT
// cap. The Section 7 Step B replay endpoint is the primary consumer.
func (s *PositionSnapshotStore) SnapshotsBetween(
	ctx context.Context, userID string, from, to time.Time,
) ([]*SnapshotRow, error) {
	if userID == "" {
		return nil, fmt.Errorf("snapshot user_id must not be empty")
	}
	rows, err := s.pool.Query(ctx, `
		SELECT id, user_id, snapshot_ts, position_count, positions, content_hash, reconcile_run_id
		FROM execution_positions_snapshot
		WHERE user_id = $1 AND snapshot_ts BETWEEN $2 AND $3
		ORDER BY snapshot_ts ASC
	`, userID, from, to)
	if err != nil {
		return nil, fmt.Errorf("snapshots between for %s: %w", userID, err)
	}
	defer rows.Close()

	out := make([]*SnapshotRow, 0)
	for rows.Next() {
		var (
			r     SnapshotRow
			rawJS []byte
		)
		if err := rows.Scan(
			&r.ID,
			&r.UserID,
			&r.SnapshotTS,
			&r.PositionCount,
			&rawJS,
			&r.ContentHash,
			&r.ReconcileRunID,
		); err != nil {
			return nil, fmt.Errorf("scan snapshot row for %s: %w", userID, err)
		}
		if err := json.Unmarshal(rawJS, &r.Positions); err != nil {
			return nil, fmt.Errorf("unmarshal snapshot positions for %s: %w", userID, err)
		}
		out = append(out, &r)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate snapshot rows for %s: %w", userID, err)
	}
	return out, nil
}

// PruneOlderThan deletes snapshots strictly older than cutoff.
//
// Step B's BEFORE DELETE trigger blocks the app role from issuing
// raw DELETE statements on this table. Pruning therefore runs
// through a SECURITY DEFINER function (execution_snapshot_prune)
// that Step B installs. Until Step B lands the SECURITY DEFINER
// function does not yet exist; this method then returns the
// underlying SQL error and the caller (retention sweeper goroutine
// in main.go) logs and continues.
//
// Returns the number of rows that WOULD be pruned, i.e. the count
// observed by the candidate SELECT. The actual DELETE happens via
// the function call; reporting the candidate count gives the
// operator a consistent metric across function-installed and
// function-missing windows.
func (s *PositionSnapshotStore) PruneOlderThan(
	ctx context.Context, cutoff time.Time,
) (int64, error) {
	row := s.pool.QueryRow(ctx, `
		SELECT COUNT(*) FROM execution_positions_snapshot WHERE snapshot_ts < $1
	`, cutoff)
	var count int64
	if err := row.Scan(&count); err != nil {
		return 0, fmt.Errorf("count prune candidates: %w", err)
	}
	if count == 0 {
		return 0, nil
	}
	if _, err := s.pool.Exec(ctx, `SELECT execution_snapshot_prune($1)`, cutoff); err != nil {
		s.log.Warn().
			Err(err).
			Time("cutoff", cutoff).
			Int64("candidates", count).
			Msg("snapshot_prune_failed_function_missing_until_step_b")
		return 0, fmt.Errorf("snapshot prune via function: %w", err)
	}
	return count, nil
}
