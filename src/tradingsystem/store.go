package tradingsystem

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// ErrNotFound is returned by Get when no row exists for the given user.
// Callers map this to a 404 (or treat it as Status='none' depending on
// the endpoint contract); it is exported so tests can match on it.
var ErrNotFound = errors.New("tradingsystem: no record")

// Store handles persistence of user trading systems in PostgreSQL.
type Store struct {
	pool *pgxpool.Pool
}

// NewStore creates a Store backed by the given connection pool. The
// pool is shared with the rest of the gateway (auth, billing, consent,
// support) so we inherit the same lifecycle and metrics surface.
func NewStore(pool *pgxpool.Pool) *Store {
	return &Store{pool: pool}
}

// Get returns the full record (including profile) for the given user.
// Returns ErrNotFound when no row exists.
func (s *Store) Get(ctx context.Context, userID string) (*Record, error) {
	var (
		rec        Record
		profileRaw []byte
	)
	rec.UserID = userID
	err := s.pool.QueryRow(ctx,
		`SELECT status, version, profile, created_at, updated_at
		   FROM user_trading_systems
		  WHERE user_id = $1`, userID,
	).Scan(&rec.Status, &rec.Version, &profileRaw, &rec.CreatedAt, &rec.UpdatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("tradingsystem.Get: %w", err)
	}

	if len(profileRaw) > 0 {
		var p Profile
		if err := json.Unmarshal(profileRaw, &p); err != nil {
			return nil, fmt.Errorf("tradingsystem.Get: unmarshal profile: %w", err)
		}
		rec.Profile = &p
	}
	return &rec, nil
}

// GetStatus returns the lightweight projection used by the dashboard
// onboarding checklist. Does NOT hydrate the JSONB profile column so
// it stays cheap on every page load.
func (s *Store) GetStatus(ctx context.Context, userID string) (*StatusView, error) {
	var (
		status     Status
		version    int
		updatedAt  time.Time
		hasProfile bool
	)
	err := s.pool.QueryRow(ctx,
		`SELECT status, version, updated_at, profile IS NOT NULL
		   FROM user_trading_systems
		  WHERE user_id = $1`, userID,
	).Scan(&status, &version, &updatedAt, &hasProfile)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			// No row: status='none' with a nil UpdatedAt so the JSON
			// response omits the field entirely (rather than emitting
			// the Go zero-value 0001-01-01T00:00:00Z).
			return &StatusView{
				Status:     StatusNone,
				Version:    0,
				UpdatedAt:  nil,
				HasProfile: false,
			}, nil
		}
		return nil, fmt.Errorf("tradingsystem.GetStatus: %w", err)
	}
	return &StatusView{
		Status:     status,
		Version:    version,
		UpdatedAt:  &updatedAt,
		HasProfile: hasProfile,
	}, nil
}

// Save upserts an ACTIVE profile for the user, bumping the version
// counter. This is the only path that ever writes the profile column;
// Skip and Reset use their own narrow statements so we never
// accidentally clobber a profile on a status-only update.
func (s *Store) Save(ctx context.Context, userID string, profile *Profile) (*Record, error) {
	if profile == nil {
		return nil, errors.New("tradingsystem.Save: profile is nil")
	}
	profile.SchemaVersion = CurrentSchemaVersion

	raw, err := json.Marshal(profile)
	if err != nil {
		return nil, fmt.Errorf("tradingsystem.Save: marshal: %w", err)
	}

	now := time.Now().UTC()
	var (
		outStatus    Status
		outVersion   int
		outCreatedAt time.Time
		outUpdatedAt time.Time
	)
	err = s.pool.QueryRow(ctx,
		`INSERT INTO user_trading_systems (user_id, status, version, profile, created_at, updated_at)
		      VALUES ($1, 'active', 1, $2, $3, $3)
		 ON CONFLICT (user_id) DO UPDATE
		    SET status     = 'active',
		        version    = user_trading_systems.version + 1,
		        profile    = EXCLUDED.profile,
		        updated_at = EXCLUDED.updated_at
		  RETURNING status, version, created_at, updated_at`,
		userID, raw, now,
	).Scan(&outStatus, &outVersion, &outCreatedAt, &outUpdatedAt)
	if err != nil {
		return nil, fmt.Errorf("tradingsystem.Save: upsert: %w", err)
	}

	return &Record{
		UserID:    userID,
		Status:    outStatus,
		Version:   outVersion,
		Profile:   profile,
		CreatedAt: outCreatedAt,
		UpdatedAt: outUpdatedAt,
	}, nil
}

// Skip records that the user explicitly declined to build a profile.
// Does NOT touch the profile column: a user who built a profile, then
// later decided to skip onboarding for a fresh round, keeps their old
// profile and we just flip the status. Reset (below) is the explicit
// path that nukes the profile.
func (s *Store) Skip(ctx context.Context, userID string) (*StatusView, error) {
	now := time.Now().UTC()
	var (
		outStatus    Status
		outVersion   int
		outUpdatedAt time.Time
		hasProfile   bool
	)
	err := s.pool.QueryRow(ctx,
		`INSERT INTO user_trading_systems (user_id, status, version, profile, created_at, updated_at)
		      VALUES ($1, 'skipped', 0, NULL, $2, $2)
		 ON CONFLICT (user_id) DO UPDATE
		    SET status     = CASE
		                       WHEN user_trading_systems.status = 'active' THEN 'active'
		                       ELSE 'skipped'
		                     END,
		        updated_at = EXCLUDED.updated_at
		  RETURNING status, version, updated_at, profile IS NOT NULL`,
		userID, now,
	).Scan(&outStatus, &outVersion, &outUpdatedAt, &hasProfile)
	if err != nil {
		return nil, fmt.Errorf("tradingsystem.Skip: %w", err)
	}
	return &StatusView{
		Status:     outStatus,
		Version:    outVersion,
		UpdatedAt:  &outUpdatedAt,
		HasProfile: hasProfile,
	}, nil
}

// Reset clears the profile and returns the user to status='none'. Used
// by the dashboard's "start over" affordance. Idempotent; safe to call
// on a user who never had a row.
func (s *Store) Reset(ctx context.Context, userID string) error {
	now := time.Now().UTC()
	_, err := s.pool.Exec(ctx,
		`INSERT INTO user_trading_systems (user_id, status, version, profile, created_at, updated_at)
		      VALUES ($1, 'none', 0, NULL, $2, $2)
		 ON CONFLICT (user_id) DO UPDATE
		    SET status     = 'none',
		        version    = 0,
		        profile    = NULL,
		        updated_at = EXCLUDED.updated_at`,
		userID, now,
	)
	if err != nil {
		return fmt.Errorf("tradingsystem.Reset: %w", err)
	}
	return nil
}
