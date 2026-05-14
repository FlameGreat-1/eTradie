package tradingsystem

// SchemaSQL returns the idempotent DDL for the trading-system tables.
// Mirrors the pattern used by src/auth, src/consent, and src/support:
// every statement is safe to re-run on a populated production database.
//
// One row per user. Status is the lifecycle discriminator; profile is
// the JSONB payload (NULL until status='active'). Version increments
// each time the user regenerates their system so the engine and the
// audit log can correlate decisions to a specific profile snapshot.
func SchemaSQL() string {
	return `
CREATE TABLE IF NOT EXISTS user_trading_systems (
    user_id     TEXT PRIMARY KEY REFERENCES auth_users(id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'none',
    version     INTEGER NOT NULL DEFAULT 0,
    profile     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT user_trading_systems_status_chk
        CHECK (status IN ('none', 'skipped', 'active')),
    CONSTRAINT user_trading_systems_active_has_profile_chk
        CHECK (status <> 'active' OR profile IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_user_trading_systems_status
    ON user_trading_systems (status);

CREATE INDEX IF NOT EXISTS idx_user_trading_systems_updated_at
    ON user_trading_systems (updated_at DESC);
`
}
