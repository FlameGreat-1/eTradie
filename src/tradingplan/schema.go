package tradingplan

// SchemaSQL returns the idempotent DDL for the trading-plan table.
// Mirrors the pattern used by src/tradingsystem, src/auth, src/consent
// and src/support: every statement is safe to re-run on a populated
// production database.
//
// One row per user. Status is the lifecycle discriminator; plan is
// the JSONB payload (NULL while status='generating' for the very
// first attempt, and preserved across retries on failure). Version
// increments each time the user regenerates a successful plan so the
// audit log can correlate downloads to a specific snapshot.
//
// Foreign key: ON DELETE CASCADE against auth_users — when a user
// account is deleted we drop their plan with it. This matches the
// FK policy on user_trading_systems and keeps GDPR Article 17
// (right to erasure) honour-able with a single DELETE statement on
// the auth row.
func SchemaSQL() string {
	return `
CREATE TABLE IF NOT EXISTS user_trading_plans (
    user_id     TEXT PRIMARY KEY REFERENCES auth_users(id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'none',
    version     INTEGER NOT NULL DEFAULT 0,
    plan        JSONB,
    last_error  TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT user_trading_plans_status_chk
        CHECK (status IN ('none', 'generating', 'failed', 'active')),
    CONSTRAINT user_trading_plans_active_has_plan_chk
        CHECK (status <> 'active' OR plan IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_user_trading_plans_status
    ON user_trading_plans (status);

CREATE INDEX IF NOT EXISTS idx_user_trading_plans_updated_at
    ON user_trading_plans (updated_at DESC);
`
}
