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
--
-- LLM-token columns (additive to the original schema; existing rows
-- migrate cleanly via DEFAULT 0):
--   llm_input_tokens_today / llm_output_tokens_today
--     Daily counters, reset by the existing daily-reset path in
--     GetOrUpdateUsage (DATE(last_reset_at) < CURRENT_DATE).
--   llm_input_tokens_month / llm_output_tokens_month
--     Monthly counters, reset by the reconciler on subscription
--     period-end renewal via UsageStore.MonthlyReset.
--   llm_quota_blocked_count_today / llm_quota_blocked_count_month
--     Audit counters: how often this user hit a 429 due to quota.
--   monthly_window_start
--     The wall-clock start of the active monthly window. Used by the
--     SPA usage panel to show "resets on YYYY-MM-DD".
--   llm_last_metered_at
--     Timestamp of the last successful Commit. Cheap freshness
--     indicator for operator dashboards.
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

ALTER TABLE billing_usage ADD COLUMN IF NOT EXISTS llm_input_tokens_today        BIGINT NOT NULL DEFAULT 0;
ALTER TABLE billing_usage ADD COLUMN IF NOT EXISTS llm_output_tokens_today       BIGINT NOT NULL DEFAULT 0;
ALTER TABLE billing_usage ADD COLUMN IF NOT EXISTS llm_input_tokens_month        BIGINT NOT NULL DEFAULT 0;
ALTER TABLE billing_usage ADD COLUMN IF NOT EXISTS llm_output_tokens_month       BIGINT NOT NULL DEFAULT 0;
ALTER TABLE billing_usage ADD COLUMN IF NOT EXISTS llm_quota_blocked_count_today INT    NOT NULL DEFAULT 0;
ALTER TABLE billing_usage ADD COLUMN IF NOT EXISTS llm_quota_blocked_count_month INT    NOT NULL DEFAULT 0;
ALTER TABLE billing_usage ADD COLUMN IF NOT EXISTS monthly_window_start          TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE billing_usage ADD COLUMN IF NOT EXISTS llm_last_metered_at           TIMESTAMPTZ;
ALTER TABLE billing_usage ADD COLUMN IF NOT EXISTS soft_cap_notified_at          TIMESTAMPTZ;

-- ────────────────────────────────────────────────────────────────────────────
-- LLM token reservations.
--
-- Workflow:
--   1. Engine reserves a provisional debit BEFORE calling the LLM. The
--      input cost is the caller's estimated_input_tokens (counted via
--      the model's tokenizer); the output cost is bounded by
--      max_output_tokens (the cap the LLM provider will honour).
--      Reservation row is inserted with status='held'.
--   2. After the LLM call returns with the real usage numbers, the
--      engine Commits the reservation. The store transitions
--      status='committed', subtracts (max_output - actual_output) from
--      the over-reservation, and stamps llm_last_metered_at.
--   3. If the LLM call fails (after retries are exhausted), the engine
--      Refunds the reservation: status='refunded', the provisional
--      input AND the provisional output debits are rolled back via
--      GREATEST(0, …) clamps in usage.go.
--   4. Reservations whose expires_at has elapsed AND remain 'held'
--      are reaped by the reconciler janitor and treated as Refund
--      (the LLM probably never ran or the engine crashed).
--
-- The status column is constrained to the three lifecycle values so a
-- bad UPDATE cannot silently break the invariant.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS billing_llm_reservations (
    id                       TEXT PRIMARY KEY,
    user_id                  TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    tier                     TEXT NOT NULL,
    provider                 TEXT NOT NULL,
    model                    TEXT NOT NULL,
    estimated_input_tokens   BIGINT NOT NULL,
    max_output_tokens        BIGINT NOT NULL,
    actual_input_tokens      BIGINT,
    actual_output_tokens     BIGINT,
    status                   TEXT NOT NULL DEFAULT 'held'
                             CHECK (status IN ('held', 'committed', 'refunded')),
    trace_id                 TEXT NOT NULL DEFAULT '',
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    settled_at               TIMESTAMPTZ,
    expires_at               TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_billing_llm_reservations_user_created
    ON billing_llm_reservations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_billing_llm_reservations_status_expires
    ON billing_llm_reservations(status, expires_at)
    WHERE status = 'held';

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

-- Payment-event metadata (additive; populated only on events the
-- provider links to a real money movement). Industry-standard SaaS
-- invoice history reads these columns directly without any join.
--   amount_cents : integer minor units (e.g. 999 = $9.99). Avoids the
--                  rounding hazards of FLOAT for money. Nullable so
--                  non-financial events (tier changes, paused, etc.)
--                  do not pollute aggregates.
--   currency     : ISO-4217 alphabetic, uppercase. NULL iff amount_cents
--                  is NULL — enforced at write time by the applier.
--   invoice_url  : direct provider-hosted PDF link (Paddle invoice_url,
--                  Lemon Squeezy urls.invoice_url). We never proxy
--                  this through our backend; users click straight
--                  through to the Merchant of Record.
--   card_brand   : lower-case provider value ('visa', 'mastercard', ...).
--                  Display-only; PCI scope stays with the MoR.
--   card_last4   : 4-digit string. We NEVER store PAN.
--   card_exp_*   : month 1..12, year four-digit. Both nullable.
ALTER TABLE billing_subscription_events ADD COLUMN IF NOT EXISTS amount_cents   BIGINT;
ALTER TABLE billing_subscription_events ADD COLUMN IF NOT EXISTS currency       TEXT;
ALTER TABLE billing_subscription_events ADD COLUMN IF NOT EXISTS invoice_url    TEXT;
ALTER TABLE billing_subscription_events ADD COLUMN IF NOT EXISTS card_brand     TEXT;
ALTER TABLE billing_subscription_events ADD COLUMN IF NOT EXISTS card_last4     TEXT;
ALTER TABLE billing_subscription_events ADD COLUMN IF NOT EXISTS card_exp_month SMALLINT;
ALTER TABLE billing_subscription_events ADD COLUMN IF NOT EXISTS card_exp_year  SMALLINT;

CREATE INDEX IF NOT EXISTS idx_billing_subscription_events_user
    ON billing_subscription_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_billing_subscription_events_provider_event
    ON billing_subscription_events(provider, event_id);

-- Drives the user-facing Invoice History feed:
--   WHERE user_id = $1 AND event_name = ANY($2) ORDER BY created_at DESC
-- The partial predicate keeps the index small (only ~5 event types
-- count as 'financial' across both providers); the leading user_id
-- column means every per-user query is a single index seek.
CREATE INDEX IF NOT EXISTS idx_billing_subscription_events_user_event_name
    ON billing_subscription_events(user_id, event_name, created_at DESC);

-- Latest card snapshot per user. Populated by the applier from any
-- event that carries card metadata; overwrites previous values so the
-- Payment Methods card always renders the active method without a
-- separate "payment_methods" table. NULL until the first event with
-- card metadata lands (which is correct for free users — they have
-- never paid, so there is no card).
ALTER TABLE billing_subscriptions ADD COLUMN IF NOT EXISTS card_brand     TEXT;
ALTER TABLE billing_subscriptions ADD COLUMN IF NOT EXISTS card_last4     TEXT;
ALTER TABLE billing_subscriptions ADD COLUMN IF NOT EXISTS card_exp_month SMALLINT;
ALTER TABLE billing_subscriptions ADD COLUMN IF NOT EXISTS card_exp_year  SMALLINT;

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

-- ────────────────────────────────────────────────────────────────────────────
-- Customer-portal access audit trail.
--
-- Compliance: SOC 2 CC6.1 and PCI-DSS 10.2.5 both require an immutable
-- log of every authenticated access to subscription-management surfaces.
-- This table is the trail. One row per /api/v1/billing/portal request
-- (success OR failure). Append-only by convention; no UPDATE/DELETE
-- path exists in the codebase.
--
-- Retention is operator-driven: many regulated SaaS deployments keep
-- this table for 12-24 months. There is no janitor on this table by
-- design — deletion is a deliberate compliance decision, not a
-- background task.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS billing_portal_access_events (
    id           BIGSERIAL PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    provider     TEXT,
    client_ip    TEXT,
    user_agent   TEXT,
    status       TEXT NOT NULL,
    error        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_billing_portal_access_events_user_created
    ON billing_portal_access_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_billing_portal_access_events_created
    ON billing_portal_access_events(created_at DESC);
`
}
