package audit

import (
	"context"
	"encoding/json"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/execution/internal/observability"
)

const insertSQL = `
INSERT INTO execution_audit_logs (
    timestamp, action, symbol, direction, order_id, analysis_id,
    trace_id, execution_mode, entry_price, stop_loss, lot_size,
    risk_amount, risk_percent, grade, trading_style, session,
    rr_ratio, confluence_score, rejection_check, rejection_reason,
    details
) VALUES (
    $1, $2, $3, $4, $5, $6,
    $7, $8, $9, $10, $11,
    $12, $13, $14, $15, $16,
    $17, $18, $19, $20,
    $21
)`

const writeTimeout = 5 * time.Second

// Store handles all PostgreSQL operations for the execution audit log.
// Writes are fire-and-forget with error logging and metrics; a failed
// audit write must never block or fail the execution pipeline.
type Store struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

// NewStore creates an audit store backed by the given pgx pool.
func NewStore(pool *pgxpool.Pool) *Store {
	return &Store{
		pool: pool,
		log:  observability.Logger("audit_store"),
	}
}

// Entry represents a single audit log row.
type Entry struct {
	Action          string
	Symbol          string
	Direction       string
	OrderID         string
	AnalysisID      string
	TraceID         string
	ExecutionMode   string
	EntryPrice      float64
	StopLoss        float64
	LotSize         float64
	RiskAmount      float64
	RiskPercent     float64
	Grade           string
	TradingStyle    string
	Session         string
	RRRatio         float64
	ConfluenceScore float64
	RejectionCheck  int32
	RejectionReason string
	Details         map[string]interface{}
}

// Write persists an audit entry to PostgreSQL.
func (s *Store) Write(ctx context.Context, e *Entry) {
	writeCtx, cancel := context.WithTimeout(ctx, writeTimeout)
	defer cancel()

	detailsJSON := marshalDetails(e.Details, s.log)

	_, err := s.pool.Exec(writeCtx, insertSQL,
		time.Now().UTC(),
		e.Action,
		e.Symbol,
		e.Direction,
		e.OrderID,
		e.AnalysisID,
		e.TraceID,
		e.ExecutionMode,
		e.EntryPrice,
		e.StopLoss,
		e.LotSize,
		e.RiskAmount,
		e.RiskPercent,
		e.Grade,
		e.TradingStyle,
		e.Session,
		e.RRRatio,
		e.ConfluenceScore,
		e.RejectionCheck,
		e.RejectionReason,
		detailsJSON,
	)

	if err != nil {
		observability.AuditWriteFailures.Inc()
		s.log.Error().
			Err(err).
			Str("action", e.Action).
			Str("symbol", e.Symbol).
			Str("order_id", e.OrderID).
			Str("analysis_id", e.AnalysisID).
			Msg("audit_write_failed")
		return
	}

	s.log.Debug().
		Str("action", e.Action).
		Str("symbol", e.Symbol).
		Str("order_id", e.OrderID).
		Msg("audit_entry_written")
}

// CreateTableSQL returns the DDL for the execution_audit_logs table.
func CreateTableSQL() string {
	return `
CREATE TABLE IF NOT EXISTS execution_audit_logs (
    id              BIGSERIAL PRIMARY KEY,
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

CREATE INDEX IF NOT EXISTS idx_exec_audit_symbol ON execution_audit_logs (symbol);
CREATE INDEX IF NOT EXISTS idx_exec_audit_analysis_id ON execution_audit_logs (analysis_id);
CREATE INDEX IF NOT EXISTS idx_exec_audit_action ON execution_audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_exec_audit_timestamp ON execution_audit_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_exec_audit_order_id ON execution_audit_logs (order_id);
`
}

func marshalDetails(details map[string]interface{}, log zerolog.Logger) []byte {
	if details == nil {
		return []byte("{}")
	}
	b, err := json.Marshal(details)
	if err != nil {
		log.Error().Err(err).Msg("audit_details_marshal_failed")
		return []byte("{}")
	}
	return b
}
