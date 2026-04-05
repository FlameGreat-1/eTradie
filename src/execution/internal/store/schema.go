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
`
}
