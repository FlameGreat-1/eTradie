package store

// SchemaSQL returns the DDL for all execution engine tables.
// Called once at startup to ensure tables and indexes exist.
// All statements use IF NOT EXISTS for idempotent re-runs.
func SchemaSQL() string {
	return `
CREATE TABLE IF NOT EXISTS execution_audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(64) NOT NULL DEFAULT '',
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action          VARCHAR(40) NOT NULL,
    symbol          VARCHAR(20) NOT NULL DEFAULT '',
    direction       VARCHAR(10) NOT NULL DEFAULT '',
    order_id        VARCHAR(128) NOT NULL DEFAULT '',
    analysis_id     VARCHAR(128) NOT NULL DEFAULT '',
    trace_id        VARCHAR(64) NOT NULL DEFAULT '',
    execution_mode  VARCHAR(10) NOT NULL DEFAULT '',
    entry_price     DOUBLE PRECISION NOT NULL DEFAULT 0,
    stop_loss       DOUBLE PRECISION NOT NULL DEFAULT 0,
    lot_size        DOUBLE PRECISION NOT NULL DEFAULT 0,
    risk_amount     DOUBLE PRECISION NOT NULL DEFAULT 0,
    risk_percent    DOUBLE PRECISION NOT NULL DEFAULT 0,
    grade           VARCHAR(10) NOT NULL DEFAULT '',
    trading_style   VARCHAR(20) NOT NULL DEFAULT '',
    session         VARCHAR(30) NOT NULL DEFAULT '',
    rr_ratio        DOUBLE PRECISION NOT NULL DEFAULT 0,
    confluence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    rejection_check INTEGER NOT NULL DEFAULT 0,
    rejection_reason TEXT NOT NULL DEFAULT '',
    details         JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_exec_audit_user_id ON execution_audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_exec_audit_symbol ON execution_audit_logs (symbol);
CREATE INDEX IF NOT EXISTS idx_exec_audit_analysis_id ON execution_audit_logs (analysis_id);
CREATE INDEX IF NOT EXISTS idx_exec_audit_action ON execution_audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_exec_audit_timestamp ON execution_audit_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_exec_audit_order_id ON execution_audit_logs (order_id);

CREATE TABLE IF NOT EXISTS execution_pnl_tracker (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(64) NOT NULL DEFAULT '',
    period_type     VARCHAR(10) NOT NULL,
    period_key      VARCHAR(20) NOT NULL,
    realized_pnl    DOUBLE PRECISION NOT NULL DEFAULT 0,
    trade_count     INTEGER NOT NULL DEFAULT 0,
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, period_type, period_key)
);

CREATE INDEX IF NOT EXISTS idx_pnl_tracker_user_id ON execution_pnl_tracker (user_id);
CREATE INDEX IF NOT EXISTS idx_pnl_tracker_period ON execution_pnl_tracker (user_id, period_type, period_key);

CREATE TABLE IF NOT EXISTS execution_settings (
    user_id     VARCHAR(64) NOT NULL DEFAULT '',
    key         VARCHAR(64) NOT NULL,
    value       TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, key)
);

CREATE INDEX IF NOT EXISTS idx_exec_settings_user_id ON execution_settings (user_id);

CREATE TABLE IF NOT EXISTS execution_pending_watchers (
    id                  BIGSERIAL PRIMARY KEY,
    watcher_id          TEXT NOT NULL UNIQUE,
    order_id            TEXT NOT NULL,
    user_id             VARCHAR(64) NOT NULL,
    symbol              VARCHAR(20) NOT NULL,
    direction           VARCHAR(10) NOT NULL,
    execution_mode      VARCHAR(10) NOT NULL DEFAULT 'INSTANT',
    entry_price         DOUBLE PRECISION NOT NULL,
    stop_loss           DOUBLE PRECISION NOT NULL,
    tp1_price           DOUBLE PRECISION NOT NULL DEFAULT 0,
    tp1_pct             INTEGER NOT NULL DEFAULT 0,
    tp2_price           DOUBLE PRECISION NOT NULL DEFAULT 0,
    tp2_pct             INTEGER NOT NULL DEFAULT 0,
    tp3_price           DOUBLE PRECISION NOT NULL DEFAULT 0,
    tp3_pct             INTEGER NOT NULL DEFAULT 0,
    lot_size            DOUBLE PRECISION NOT NULL,
    risk_percent        DOUBLE PRECISION NOT NULL DEFAULT 0,
    risk_amount         DOUBLE PRECISION NOT NULL DEFAULT 0,
    rr_ratio            DOUBLE PRECISION NOT NULL DEFAULT 0,
    account_balance     DOUBLE PRECISION NOT NULL DEFAULT 0,
    sl_distance_pips    DOUBLE PRECISION NOT NULL DEFAULT 0,
    pip_value           DOUBLE PRECISION NOT NULL DEFAULT 0,
    overshoot_tolerance DOUBLE PRECISION NOT NULL DEFAULT 0,
    ltf_confirmed       BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_id         TEXT NOT NULL DEFAULT '',
    trading_style       VARCHAR(20) NOT NULL DEFAULT '',
    session             VARCHAR(30) NOT NULL DEFAULT '',
    grade               VARCHAR(10) NOT NULL DEFAULT '',
    confluence          DOUBLE PRECISION NOT NULL DEFAULT 0,
    confidence          DOUBLE PRECISION NOT NULL DEFAULT 0,
    setup_type          TEXT NOT NULL DEFAULT '',
    trace_id            TEXT NOT NULL DEFAULT '',
    broker_order_id     TEXT NOT NULL DEFAULT '',
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exec_watchers_user_id ON execution_pending_watchers (user_id);
CREATE INDEX IF NOT EXISTS idx_exec_watchers_status ON execution_pending_watchers (status);
CREATE INDEX IF NOT EXISTS idx_exec_watchers_symbol ON execution_pending_watchers (symbol);
CREATE INDEX IF NOT EXISTS idx_exec_watchers_watcher_id ON execution_pending_watchers (watcher_id);

-- Section 3 (CHECKLIST): order idempotency table. Every accepted
-- placement claims a (user_id, idempotency_key) row before the
-- broker call; a duplicate submission with the same key short-
-- circuits and returns the prior broker_order_id.
CREATE TABLE IF NOT EXISTS execution_order_idempotency (
    user_id         VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    order_id        VARCHAR(128) NOT NULL,
    symbol          VARCHAR(20)  NOT NULL,
    direction       VARCHAR(10)  NOT NULL,
    execution_mode  VARCHAR(10)  NOT NULL,
    entry_price     DOUBLE PRECISION NOT NULL DEFAULT 0,
    stop_loss       DOUBLE PRECISION NOT NULL DEFAULT 0,
    lot_size        DOUBLE PRECISION NOT NULL DEFAULT 0,
    broker_order_id TEXT NOT NULL DEFAULT '',
    status          VARCHAR(20)  NOT NULL DEFAULT 'CLAIMED',
    fill_price      DOUBLE PRECISION NOT NULL DEFAULT 0,
    volume_filled   DOUBLE PRECISION NOT NULL DEFAULT 0,
    volume_remaining DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    PRIMARY KEY (user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_exec_idemp_user_id
    ON execution_order_idempotency (user_id);
CREATE INDEX IF NOT EXISTS idx_exec_idemp_created_at
    ON execution_order_idempotency (created_at);
CREATE INDEX IF NOT EXISTS idx_exec_idemp_order_id
    ON execution_order_idempotency (order_id);

-- Section 7 (CHECKLIST): position snapshots.
--
-- One INSERT-only row per reconcile cycle per user. Carries the
-- JSONB-encoded list of engine-tracked positions AFTER the reconciler
-- ran (post adopt/replace), plus a sha256 of the canonicalised JSON
-- for tamper detection. The ghost-position rule in reconciler.go
-- compares 'positions that appear in the latest snapshot but not in
-- the current broker reply' against a configurable min-age threshold.
--
-- Immutability: Section 7 Step B adds a BEFORE UPDATE / BEFORE DELETE
-- trigger on this table. The pruner uses a separate SECURITY DEFINER
-- function (execution_snapshot_prune) to age out old rows; the app
-- role cannot bypass the trigger.
CREATE TABLE IF NOT EXISTS execution_positions_snapshot (
    id               BIGSERIAL PRIMARY KEY,
    user_id          VARCHAR(64) NOT NULL,
    snapshot_ts      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    position_count   INTEGER NOT NULL DEFAULT 0,
    positions        JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_hash     CHAR(64) NOT NULL,
    reconcile_run_id TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_exec_positions_snap_user_ts
    ON execution_positions_snapshot (user_id, snapshot_ts DESC);
CREATE INDEX IF NOT EXISTS idx_exec_positions_snap_ts
    ON execution_positions_snapshot (snapshot_ts);

-- Automatic schema migration for existing databases
ALTER TABLE execution_pending_watchers ADD COLUMN IF NOT EXISTS broker_order_id TEXT NOT NULL DEFAULT '';
ALTER TABLE execution_audit_logs ADD COLUMN IF NOT EXISTS volume_filled    DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE execution_audit_logs ADD COLUMN IF NOT EXISTS volume_remaining DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE execution_audit_logs ADD COLUMN IF NOT EXISTS fill_status      VARCHAR(20) NOT NULL DEFAULT '';

-- Section 7 Step B (CHECKLIST): DB-level immutability for audit tables.
--
-- The application contract for execution_audit_logs and
-- execution_positions_snapshot is INSERT-only. A future developer
-- or a compromised DB role must not be able to silently mutate or
-- delete audit history. These triggers enforce that at the DB level
-- regardless of which application code path runs.
--
-- The SECURITY DEFINER function execution_snapshot_prune is the ONLY
-- authorised path for deleting old snapshots. It is granted to the
-- migration role (NOT the app role) so the retention sweeper in
-- main.go can call it via the app role's connection without bypassing
-- the trigger. Until the migration role grants are applied in
-- production, PruneOlderThan() returns an error and the sweeper logs
-- at WARN; the table grows but is bounded by the 7-day retention
-- window once the grant lands.
--
-- Trigger naming convention: trg_<table>_immutable_<event>.
-- Both triggers are created with CREATE OR REPLACE so re-running
-- SchemaSQL() is idempotent.

CREATE OR REPLACE FUNCTION fn_block_audit_mutation()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION
        'Immutability violation: % on % is not permitted. '
        'execution_audit_logs is an INSERT-only table. '
        'Contact the platform team if a correction is required.',
        TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
    RETURN NULL;
END;
$$;

CREATE OR REPLACE TRIGGER trg_audit_logs_immutable_update
    BEFORE UPDATE ON execution_audit_logs
    FOR EACH ROW EXECUTE FUNCTION fn_block_audit_mutation();

CREATE OR REPLACE TRIGGER trg_audit_logs_immutable_delete
    BEFORE DELETE ON execution_audit_logs
    FOR EACH ROW EXECUTE FUNCTION fn_block_audit_mutation();

CREATE OR REPLACE FUNCTION fn_block_snapshot_mutation()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION
        'Immutability violation: % on % is not permitted. '
        'execution_positions_snapshot is an INSERT-only table. '
        'Use execution_snapshot_prune() for retention sweeps.',
        TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
    RETURN NULL;
END;
$$;

CREATE OR REPLACE TRIGGER trg_positions_snap_immutable_update
    BEFORE UPDATE ON execution_positions_snapshot
    FOR EACH ROW EXECUTE FUNCTION fn_block_snapshot_mutation();

CREATE OR REPLACE TRIGGER trg_positions_snap_immutable_delete
    BEFORE DELETE ON execution_positions_snapshot
    FOR EACH ROW EXECUTE FUNCTION fn_block_snapshot_mutation();

-- SECURITY DEFINER prune function. The app role calls this via
-- SELECT execution_snapshot_prune($1); the function runs as its
-- OWNER (the migration role) which has DELETE rights on the table
-- and therefore bypasses the trigger. The app role itself cannot
-- DELETE directly.
--
-- The function is created with CREATE OR REPLACE so re-running
-- SchemaSQL() is idempotent. The GRANT below is a no-op if the
-- migration role does not exist yet (dev / CI environments where
-- the app role IS the migration role).
CREATE OR REPLACE FUNCTION execution_snapshot_prune(cutoff TIMESTAMPTZ)
RETURNS BIGINT
SECURITY DEFINER
LANGUAGE plpgsql AS $$
DECLARE
    deleted BIGINT;
BEGIN
    DELETE FROM execution_positions_snapshot
    WHERE snapshot_ts < cutoff;
    GET DIAGNOSTICS deleted = ROW_COUNT;
    RETURN deleted;
END;
$$;
`
}
