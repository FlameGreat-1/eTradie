package store

// SchemaSQL returns the DDL for billing tables.
// Executed once at service startup. All statements are idempotent.
func SchemaSQL() string {
	return `
-- ────────────────────────────────────────────────────────────────────────────
-- Subscriptions: one row per user. Canonical source of tier/status.
-- event_timestamp guards against out-of-order webhook delivery.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS billing_subscriptions (
    user_id                     TEXT PRIMARY KEY REFERENCES auth_users(id) ON DELETE CASCADE,
    tier                        TEXT NOT NULL DEFAULT 'free',
    status                      TEXT NOT NULL DEFAULT 'active',
    payment_provider            TEXT,
    provider_customer_id        TEXT,
    provider_subscription_id    TEXT,
    current_period_end          TIMESTAMPTZ,
    event_timestamp             TIMESTAMPTZ NOT NULL DEFAULT '1970-01-01T00:00:00Z',
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Idempotent migration for older databases that pre-date event_timestamp.
ALTER TABLE billing_subscriptions
    ADD COLUMN IF NOT EXISTS event_timestamp TIMESTAMPTZ NOT NULL DEFAULT '1970-01-01T00:00:00Z';

CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_tier ON billing_subscriptions(tier);
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_status ON billing_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_provider_customer
    ON billing_subscriptions(payment_provider, provider_customer_id)
    WHERE provider_customer_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_provider_subscription
    ON billing_subscriptions(payment_provider, provider_subscription_id)
    WHERE provider_subscription_id IS NOT NULL;

-- ────────────────────────────────────────────────────────────────────────────
-- Usage: per-user counters with atomic daily reset.
-- Scanned and incremented from the gateway and engine.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS billing_usage (
    user_id              TEXT PRIMARY KEY REFERENCES auth_users(id) ON DELETE CASCADE,
    analyses_today       INT NOT NULL DEFAULT 0,
    llm_tokens_used      BIGINT NOT NULL DEFAULT 0,
    execution_attempts   INT NOT NULL DEFAULT 0,
    watcher_count        INT NOT NULL DEFAULT 0,
    ta_cycles_used       INT NOT NULL DEFAULT 0,
    macro_cycles_used    INT NOT NULL DEFAULT 0,
    monthly_usage_window TIMESTAMPTZ,
    last_analysis_at     TIMESTAMPTZ,
    last_reset_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ────────────────────────────────────────────────────────────────────────────
-- Webhook idempotency: one row per (provider, event_id) actually processed.
-- INSERT with ON CONFLICT DO NOTHING is the cheap dedupe primitive.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS processed_webhook_events (
    provider     TEXT NOT NULL,
    event_id     TEXT NOT NULL,
    event_name   TEXT NOT NULL,
    received_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (provider, event_id)
);

CREATE INDEX IF NOT EXISTS idx_processed_webhook_events_received_at
    ON processed_webhook_events(received_at);

-- ────────────────────────────────────────────────────────────────────────────
-- Subscription audit trail: append-only history of every transition.
-- Operators / support need to answer "what was this user's tier on date X?".
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS billing_subscription_events (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    provider            TEXT NOT NULL,
    event_name          TEXT NOT NULL,
    event_id            TEXT NOT NULL,
    previous_tier       TEXT,
    new_tier            TEXT NOT NULL,
    previous_status     TEXT,
    new_status          TEXT NOT NULL,
    event_timestamp     TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_billing_subscription_events_user
    ON billing_subscription_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_billing_subscription_events_provider_event
    ON billing_subscription_events(provider, event_id);

-- ────────────────────────────────────────────────────────────────────────────
-- Checkout-intent idempotency: short-lived (user_id, provider, tier) cache
-- that defeats double-click and navigation-race double-charges. A repeat
-- request within the TTL returns the SAME provider checkout URL so the
-- user lands on the same checkout page instead of creating a second
-- provider subscription. Pruned by the reconciler janitor pass.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS billing_checkout_intents (
    user_id      TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    provider     TEXT NOT NULL,
    tier         TEXT NOT NULL,
    checkout_url TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, provider, tier)
);

CREATE INDEX IF NOT EXISTS idx_billing_checkout_intents_expires_at
    ON billing_checkout_intents(expires_at);
`
}
