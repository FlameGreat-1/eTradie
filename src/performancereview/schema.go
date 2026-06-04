package performancereview

// SchemaSQL returns the idempotent DDL for the performance-review
// table. Mirrors the convention used by src/tradingsystem,
// src/tradingplan, src/auth, src/consent and src/support: every
// statement is safe to re-run on a populated production database.
//
// Design notes:
//
//   - Primary key is (user_id, period, period_start). One row per
//     window per user. A regenerate of the SAME window overwrites
//     the row via ON CONFLICT (so the SPA never sees duplicates).
//     Two DIFFERENT windows (last week and the week before) are
//     stored as two rows, which is exactly the history we want.
//
//   - period_end is a check-constrained range so the daily cron job
//     cannot accidentally write a row whose start is after its end.
//
//   - status is a CHECK-constrained enum mirroring the Go Status
//     constants. A future status (e.g. 'archived') requires a
//     migration plus a Go-side constant bump - the constraint is
//     deliberately strict so silent drift cannot land.
//
//   - last_error defaults to '' rather than NULL so handler code can
//     always read the column without coalescing.
//
//   - ON DELETE CASCADE against auth_users: when a user is deleted
//     we drop all their reviews with them (GDPR right-to-erasure
//     stays a one-statement operation, identical to tradingplan).
//
//   - Indexes:
//       * primary (user_id, period, period_start)        -> upsert path
//       * idx_perf_reviews_user_period_updated_desc      -> latest()
//       * idx_perf_reviews_user_status                   -> retry sweeps
//       * idx_perf_reviews_user_updated                  -> history pagination
func SchemaSQL() string {
	return `
-- Idempotent migration: add journal_mode column to pre-existing tables that
-- were created before this column was introduced. CREATE TABLE IF NOT EXISTS
-- will NOT add new columns to an existing table, so we must do it explicitly.
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'user_performance_reviews'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_performance_reviews' AND column_name = 'journal_mode'
    ) THEN
        ALTER TABLE user_performance_reviews
            ADD COLUMN journal_mode TEXT NOT NULL DEFAULT 'system';
        ALTER TABLE user_performance_reviews
            ADD CONSTRAINT user_performance_reviews_mode_chk
            CHECK (journal_mode IN ('system', 'manual'));
    END IF;
END $$;

-- Idempotent migration: update unique constraint to include journal_mode
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'user_performance_reviews'
    ) THEN
        ALTER TABLE user_performance_reviews
            DROP CONSTRAINT IF EXISTS user_performance_reviews_uniq_window;
        ALTER TABLE user_performance_reviews
            ADD CONSTRAINT user_performance_reviews_uniq_window
            UNIQUE (user_id, period, period_start, journal_mode);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS user_performance_reviews (
    id           BIGSERIAL    PRIMARY KEY,
    user_id      TEXT         NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    period       TEXT         NOT NULL,
    period_start TIMESTAMPTZ  NOT NULL,
    period_end   TIMESTAMPTZ  NOT NULL,
    status       TEXT         NOT NULL DEFAULT 'generating',
    review       JSONB,
    last_error   TEXT         NOT NULL DEFAULT '',
    journal_mode TEXT         NOT NULL DEFAULT 'system',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT user_performance_reviews_period_chk
        CHECK (period IN ('weekly', 'monthly')),
    CONSTRAINT user_performance_reviews_status_chk
        CHECK (status IN ('generating', 'ready', 'failed')),
    CONSTRAINT user_performance_reviews_mode_chk
        CHECK (journal_mode IN ('system', 'manual')),
    CONSTRAINT user_performance_reviews_window_chk
        CHECK (period_end >= period_start),
    CONSTRAINT user_performance_reviews_ready_has_review_chk
        CHECK (status <> 'ready' OR review IS NOT NULL),
    CONSTRAINT user_performance_reviews_uniq_window
        UNIQUE (user_id, period, period_start, journal_mode)
);

CREATE INDEX IF NOT EXISTS idx_perf_reviews_user_period_updated_desc
    ON user_performance_reviews (user_id, period, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_perf_reviews_user_status
    ON user_performance_reviews (user_id, status);

CREATE INDEX IF NOT EXISTS idx_perf_reviews_user_updated
    ON user_performance_reviews (user_id, updated_at DESC);
`
}
