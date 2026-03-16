package store

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/execution/internal/observability"
)

const (
	pnlWriteTimeout = 3 * time.Second
	pnlReadTimeout  = 3 * time.Second

	periodDaily  = "DAILY"
	periodWeekly = "WEEKLY"
)

const upsertPnLSQL = `
INSERT INTO execution_pnl_tracker (period_type, period_key, realized_pnl, trade_count, last_updated)
VALUES ($1, $2, $3, 1, NOW())
ON CONFLICT (period_type, period_key)
DO UPDATE SET
    realized_pnl = execution_pnl_tracker.realized_pnl + EXCLUDED.realized_pnl,
    trade_count  = execution_pnl_tracker.trade_count + 1,
    last_updated = NOW()
`

const selectPnLSQL = `
SELECT COALESCE(realized_pnl, 0), COALESCE(trade_count, 0)
FROM execution_pnl_tracker
WHERE period_type = $1 AND period_key = $2
`

// PnLSnapshot holds the current P&L state loaded from the database.
type PnLSnapshot struct {
	DailyPnL       float64
	DailyTrades    int
	WeeklyPnL      float64
	WeeklyTrades   int
	DailyPeriodKey string
	WeeklyPeriodKey string
}

// PnLStore handles PostgreSQL persistence for realized P&L tracking.
// Ensures daily/weekly loss limits survive service restarts.
type PnLStore struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

// NewPnLStore creates a P&L store backed by the given pgx pool.
func NewPnLStore(pool *pgxpool.Pool) *PnLStore {
	return &PnLStore{
		pool: pool,
		log:  observability.Logger("pnl_store"),
	}
}

// LoadCurrent reads the current day and week P&L from PostgreSQL.
// Called at startup and after day/week boundary resets to restore
// accurate counters. Returns zero values if no rows exist yet.
func (s *PnLStore) LoadCurrent(ctx context.Context) (*PnLSnapshot, error) {
	readCtx, cancel := context.WithTimeout(ctx, pnlReadTimeout)
	defer cancel()

	now := time.Now().UTC()
	dailyKey := DailyPeriodKey(now)
	weeklyKey := WeeklyPeriodKey(now)

	snap := &PnLSnapshot{
		DailyPeriodKey:  dailyKey,
		WeeklyPeriodKey: weeklyKey,
	}

	// Load daily.
	row := s.pool.QueryRow(readCtx, selectPnLSQL, periodDaily, dailyKey)
	if err := row.Scan(&snap.DailyPnL, &snap.DailyTrades); err != nil {
		// No row = first trade of the day; zero values are correct.
		snap.DailyPnL = 0
		snap.DailyTrades = 0
	}

	// Load weekly.
	row = s.pool.QueryRow(readCtx, selectPnLSQL, periodWeekly, weeklyKey)
	if err := row.Scan(&snap.WeeklyPnL, &snap.WeeklyTrades); err != nil {
		snap.WeeklyPnL = 0
		snap.WeeklyTrades = 0
	}

	s.log.Info().
		Str("daily_key", dailyKey).
		Float64("daily_pnl", snap.DailyPnL).
		Int("daily_trades", snap.DailyTrades).
		Str("weekly_key", weeklyKey).
		Float64("weekly_pnl", snap.WeeklyPnL).
		Int("weekly_trades", snap.WeeklyTrades).
		Msg("pnl_loaded_from_db")

	return snap, nil
}

// RecordPnL atomically increments both daily and weekly realized P&L
// in a single database transaction. Called by the state manager when
// Module C reports a closed trade.
func (s *PnLStore) RecordPnL(ctx context.Context, amount float64) error {
	writeCtx, cancel := context.WithTimeout(ctx, pnlWriteTimeout)
	defer cancel()

	now := time.Now().UTC()
	dailyKey := DailyPeriodKey(now)
	weeklyKey := WeeklyPeriodKey(now)

	tx, err := s.pool.Begin(writeCtx)
	if err != nil {
		s.log.Error().Err(err).Msg("pnl_record_begin_tx_failed")
		return fmt.Errorf("pnl record: begin tx: %w", err)
	}
	defer tx.Rollback(writeCtx)

	if _, err := tx.Exec(writeCtx, upsertPnLSQL, periodDaily, dailyKey, amount); err != nil {
		s.log.Error().Err(err).Str("period_key", dailyKey).Msg("pnl_record_daily_failed")
		return fmt.Errorf("pnl record daily: %w", err)
	}

	if _, err := tx.Exec(writeCtx, upsertPnLSQL, periodWeekly, weeklyKey, amount); err != nil {
		s.log.Error().Err(err).Str("period_key", weeklyKey).Msg("pnl_record_weekly_failed")
		return fmt.Errorf("pnl record weekly: %w", err)
	}

	if err := tx.Commit(writeCtx); err != nil {
		s.log.Error().Err(err).Msg("pnl_record_commit_failed")
		return fmt.Errorf("pnl record: commit: %w", err)
	}

	s.log.Debug().
		Float64("amount", amount).
		Str("daily_key", dailyKey).
		Str("weekly_key", weeklyKey).
		Msg("pnl_recorded")

	return nil
}

// DailyPeriodKey returns the period key for daily P&L tracking.
// Format: "2026-03-15" (ISO date).
func DailyPeriodKey(t time.Time) string {
	return t.UTC().Format("2006-01-02")
}

// WeeklyPeriodKey returns the period key for weekly P&L tracking.
// Format: "2026-W11" (ISO week). Resets every Monday 00:00 UTC.
func WeeklyPeriodKey(t time.Time) string {
	year, week := t.UTC().ISOWeek()
	return fmt.Sprintf("%d-W%02d", year, week)
}
