package store

import (
	"context"
	"encoding/json"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
)

const auditInsertSQL = `
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

const auditWriteTimeout = 5 * time.Second

// AuditStore handles all PostgreSQL operations for the execution audit log.
// Writes are fire-and-forget with error logging and metrics; a failed
// audit write must never block or fail the execution pipeline.
type AuditStore struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

// NewAuditStore creates an audit store backed by the given pgx pool.
func NewAuditStore(pool *pgxpool.Pool) *AuditStore {
	return &AuditStore{
		pool: pool,
		log:  observability.Logger("audit_store"),
	}
}

// AuditEntry represents a single audit log row.
type AuditEntry struct {
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
func (s *AuditStore) Write(ctx context.Context, e *AuditEntry) {
	writeCtx, cancel := context.WithTimeout(ctx, auditWriteTimeout)
	defer cancel()

	detailsJSON := marshalDetails(e.Details, s.log)

	_, err := s.pool.Exec(writeCtx, auditInsertSQL,
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
