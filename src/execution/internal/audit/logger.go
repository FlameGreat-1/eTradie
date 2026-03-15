package audit

import (
	"context"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/execution/internal/constants"
	"github.com/flamegreat/etradie/src/execution/internal/models"
	"github.com/flamegreat/etradie/src/execution/internal/observability"
	"github.com/flamegreat/etradie/src/execution/internal/store"
)

// Logger orchestrates audit logging by delegating database writes
// to store.AuditStore and structured logging to zerolog.
type Logger struct {
	auditStore *store.AuditStore
	log        zerolog.Logger
}

// NewLogger creates an audit logger backed by the given audit store.
func NewLogger(auditStore *store.AuditStore) *Logger {
	return &Logger{
		auditStore: auditStore,
		log:        observability.Logger("audit_logger"),
	}
}

// LogValidationPassed records a successful validation.
func (l *Logger) LogValidationPassed(ctx context.Context, req *models.TradeRequest) {
	l.auditStore.Write(ctx, &store.AuditEntry{
		Action:          string(constants.ActionValidationPassed),
		Symbol:          req.Symbol,
		Direction:       string(req.Direction),
		AnalysisID:      req.AnalysisID,
		TraceID:         req.TraceID,
		Grade:           req.Grade,
		TradingStyle:    string(req.TradingStyle),
		Session:         req.Session,
		RRRatio:         req.RRRatio,
		ConfluenceScore: req.ConfluenceScore,
	})
}

// LogValidationRejected records a failed validation with the check that failed.
func (l *Logger) LogValidationRejected(ctx context.Context, req *models.TradeRequest, result models.ValidationResult) {
	l.auditStore.Write(ctx, &store.AuditEntry{
		Action:          string(constants.ActionValidationRejected),
		Symbol:          req.Symbol,
		Direction:       string(req.Direction),
		AnalysisID:      req.AnalysisID,
		TraceID:         req.TraceID,
		Grade:           req.Grade,
		TradingStyle:    string(req.TradingStyle),
		Session:         req.Session,
		RRRatio:         req.RRRatio,
		ConfluenceScore: req.ConfluenceScore,
		RejectionCheck:  int32(result.FailedCheck),
		RejectionReason: result.Reason,
	})
}

// LogLotSizeCalculated records the full sizing calculation breakdown.
func (l *Logger) LogLotSizeCalculated(ctx context.Context, req *models.TradeRequest, sizing *models.SizingResult) {
	l.auditStore.Write(ctx, &store.AuditEntry{
		Action:       string(constants.ActionLotSizeCalculated),
		Symbol:       req.Symbol,
		Direction:    string(req.Direction),
		AnalysisID:   req.AnalysisID,
		TraceID:      req.TraceID,
		LotSize:      sizing.LotSize,
		RiskAmount:   sizing.RiskAmount,
		RiskPercent:  req.RiskPercentage,
		Grade:        req.Grade,
		TradingStyle: string(req.TradingStyle),
		Details: map[string]interface{}{
			"account_balance":  sizing.AccountBalance,
			"sl_distance_pips": sizing.SLDistancePips,
			"pip_value":        sizing.PipValue,
			"pip_size":         sizing.PipSize,
			"entry_price":      req.EntryPrice(),
			"stop_loss":        req.StopLoss,
		},
	})
}

// LogOrderPlaced records a limit order placement or watcher arming.
func (l *Logger) LogOrderPlaced(ctx context.Context, order *models.Order) {
	action := constants.ActionLimitOrderPlaced
	if order.ExecutionMode == constants.ModeInstant {
		action = constants.ActionWatcherArmed
	}

	l.auditStore.Write(ctx, &store.AuditEntry{
		Action:          string(action),
		Symbol:          order.Symbol,
		Direction:       string(order.Direction),
		OrderID:         order.OrderID,
		AnalysisID:      order.AnalysisID,
		ExecutionMode:   string(order.ExecutionMode),
		EntryPrice:      order.EntryPrice,
		StopLoss:        order.StopLoss,
		LotSize:         order.LotSize,
		RiskAmount:      order.RiskAmount,
		RiskPercent:     order.RiskPercent,
		Grade:           order.Grade,
		TradingStyle:    string(order.TradingStyle),
		Session:         order.Session,
		RRRatio:         order.RRRatio,
		ConfluenceScore: order.Confluence,
		Details: map[string]interface{}{
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
		},
	})
}

// LogOrderCancelled records an order cancellation.
func (l *Logger) LogOrderCancelled(ctx context.Context, orderID, symbol, reason, traceID string) {
	l.auditStore.Write(ctx, &store.AuditEntry{
		Action:          string(constants.ActionOrderCancelled),
		Symbol:          symbol,
		OrderID:         orderID,
		TraceID:         traceID,
		RejectionReason: reason,
	})
}
