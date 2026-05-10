package store

// SchemaSQL returns the DDL for billing tables.
// Called once at startup.
func SchemaSQL() string {
	return `
CREATE TABLE IF NOT EXISTS billing_subscriptions (
    user_id                     TEXT PRIMARY KEY REFERENCES auth_users(id) ON DELETE CASCADE,
    tier                        TEXT NOT NULL DEFAULT 'free',
    status                      TEXT NOT NULL DEFAULT 'active',
    payment_provider            TEXT,
    provider_customer_id        TEXT,
    provider_subscription_id    TEXT,
    current_period_end          TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_tier ON billing_subscriptions(tier);
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_status ON billing_subscriptions(status);

CREATE TABLE IF NOT EXISTS billing_usage (
    user_id             TEXT PRIMARY KEY REFERENCES auth_users(id) ON DELETE CASCADE,
    analyses_today      INT NOT NULL DEFAULT 0,
    llm_tokens_used     BIGINT NOT NULL DEFAULT 0,
    execution_attempts  INT NOT NULL DEFAULT 0,
    watcher_count       INT NOT NULL DEFAULT 0,
    ta_cycles_used      INT NOT NULL DEFAULT 0,
    macro_cycles_used   INT NOT NULL DEFAULT 0,
    monthly_usage_window TIMESTAMPTZ,
    last_analysis_at    TIMESTAMPTZ,
    last_reset_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Idempotent migration for existing databases.
ALTER TABLE billing_usage ADD COLUMN IF NOT EXISTS last_analysis_at TIMESTAMPTZ;
`
}
