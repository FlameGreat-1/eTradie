package audit

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/execution/internal/constants"
	"github.com/flamegreat/etradie/src/execution/internal/models"
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

// Logger writes immutable audit entries to PostgreSQL.
type Logger struct {
	pool *pgxpool.Pool
	log  zerolog.Logger
}

// NewLogger creates an audit logger backed by the given pgx pool.
func NewLogger(pool *pgxpool.Pool) *Logger {
	return &Logger{
		pool: pool,
		log:  observability.Logger("audit_logger"),
	}
}

// LogValidationPassed records a successful validation.
func (l *Logger) LogValidationPassed(ctx context.Context, req *models.TradeRequest) {
	l.write(ctx, constants.ActionValidationPassed, req.Symbol, string(req.Direction),
		"", req.AnalysisID, req.TraceID, "", 0, 0, 0, 0, 0,
		req.Grade, string(req.TradingStyle), req.Session, req.RRRatio,
		req.ConfluenceScore, 0, "", nil)
}

// LogValidationRejected records a failed validation with the check that failed.
func (l *Logger) LogValidationRejected(ctx context.Context, req *models.TradeRequest, result models.ValidationResult) {
	l.write(ctx, constants.ActionValidationRejected, req.Symbol, string(req.Direction),
		"", req.AnalysisID, req.TraceID, "", 0, 0, 0, 0, 0,
		req.Grade, string(req.TradingStyle), req.Session, req.RRRatio,
		req.ConfluenceScore, int32(result.FailedCheck), result.Reason, nil)
}

// LogOrderPlaced records a limit order placement or watcher arming.
func (l *Logger) LogOrderPlaced(ctx context.Context, order *models.Order) {
	action := constants.ActionLimitOrderPlaced
	if order.ExecutionMode == constants.ModeInstant {
		action = constants.ActionWatcherArmed
	}

	details := map[string]interface{}{
		"tp1_price":    order.TP1Price,
		"tp1_pct":      order.TP1Pct,
		"tp2_price":    order.TP2Price,
		"tp2_pct":      order.TP2Pct,
		"tp3_price":    order.TP3Price,
		"tp3_pct":      order.TP3Pct,
		"sl_pips":      order.SLDistancePips,
		"pip_value":    order.PipValue,
		"balance":      order.AccountBalance,
		"ttl_candles":  order.TTLCandles,
		"broker_order": order.BrokerOrderID,
		"watcher_id":   order.WatcherID,
	}

	l.write(ctx, action, order.Symbol, string(order.Direction),
		order.OrderID, order.AnalysisID, "", string(order.ExecutionMode),
		order.EntryPrice, order.StopLoss, order.LotSize, order.RiskAmount,
		order.RiskPercent, order.Grade, string(order.TradingStyle),
		order.Session, order.RRRatio, order.Confluence, 0, "", details)
}

// LogOrderCancelled records an order cancellation.
func (l *Logger) LogOrderCancelled(ctx context.Context, orderID, symbol, reason, traceID string) {
	l.write(ctx, constants.ActionOrderCancelled, symbol, "",
		orderID, "", traceID, "", 0, 0, 0, 0, 0,
		"", "", "", 0, 0, 0, reason, nil)
}

func (l *Logger) write(
	ctx context.Context,
	action constants.AuditAction,
	symbol, direction, orderID, analysisID, traceID, execMode string,
	entryPrice, stopLoss, lotSize, riskAmount, riskPercent float64,
	grade, tradingStyle, session string,
	rrRatio, confluenceScore float64,
	rejectionCheck int32, rejectionReason string,
	details map[string]interface{},
) {
	writeCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	var detailsJSON []byte
	if details != nil {
		var err error
		detailsJSON, err = json.Marshal(details)
		if err != nil {
			l.log.Error().Err(err).Str("action", string(action)).Msg("audit_details_marshal_failed")
			detailsJSON = []byte("{}")
		}
	} else {
		detailsJSON = []byte("{}")
	}

	_, err := l.pool.Exec(writeCtx, insertSQL,
		time.Now().UTC(),
		string(action),
		symbol,
		direction,
		orderID,
		analysisID,
		traceID,
		execMode,
		entryPrice,
		stopLoss,
		lotSize,
		riskAmount,
		riskPercent,
		grade,
		tradingStyle,
		session,
		rrRatio,
		confluenceScore,
		rejectionCheck,
		rejectionReason,
		detailsJSON,
	)

	if err != nil {
		l.log.Error().
			Err(err).
			Str("action", string(action)).
			Str("symbol", symbol).
			Str("order_id", orderID).
			Str("analysis_id", analysisID).
			Msg("audit_write_failed")
		return
	}

	l.log.Debug().
		Str("action", string(action)).
		Str("symbol", symbol).
		Str("order_id", orderID).
		Msg("audit_entry_written")
}

// CreateTable returns the SQL to create the execution_audit_logs table.
func CreateTable() string {
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
