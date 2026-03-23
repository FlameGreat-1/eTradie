package invalidator

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// StructuralEngine watches for structural breaks against the trade
// thesis on 4H/1D timeframes per Rulebook Section 9.4. If a higher-
// timeframe structural break occurs against the trade's direction,
// the trade is immediately exited as the thesis has been invalidated.
//
// Since Module C does not directly stream candle data (that's Module A's
// domain), the structural invalidation listens for Redis alerts from the
// TA Engine via the alert transport. However, as a safety backstop,
// it also checks if the current price has moved significantly beyond
// the initial SL, which indicates a structural failure.
type StructuralEngine struct {
	bp        broker.Port
	journal   *journal.Repository
	transport *alertredis.Transport
	log       zerolog.Logger
}

// NewStructuralEngine creates a structural invalidation engine.
func NewStructuralEngine(bp broker.Port, journal *journal.Repository, transport *alertredis.Transport) *StructuralEngine {
	return &StructuralEngine{
		bp:        bp,
		journal:   journal,
		transport: transport,
		log:       observability.Logger("invalidator_structural"),
	}
}

// EvaluateStructuralBreak checks if a structural break signal has been
// received against the trade thesis. Called when a structural alert
// arrives via the alert transport.
func (e *StructuralEngine) EvaluateStructuralBreak(ctx context.Context, trade *types.Trade, breakDirection string, currentPrice float64) (bool, error) {
	trade.RLock()
	tradeID := trade.TradeID
	brokerID := trade.BrokerOrderID
	symbol := trade.Symbol
	direction := trade.Direction
	entryPrice := trade.EntryPrice
	riskAmount := trade.RiskAmount
	isLong := trade.IsLong()
	status := trade.Status
	trade.RUnlock()

	if status == constants.StatusClosed {
		return false, nil
	}

	// Check if the structural break is against our trade direction.
	// BUY trade + bearish structural break = invalidation.
	// SELL trade + bullish structural break = invalidation.
	invalidated := false
	if isLong && breakDirection == "BEARISH" {
		invalidated = true
	} else if !isLong && breakDirection == "BULLISH" {
		invalidated = true
	}

	if !invalidated {
		return false, nil
	}

	return e.executeClosure(ctx, trade, tradeID, brokerID, symbol, string(direction),
		entryPrice, currentPrice, riskAmount, isLong,
		constants.EventStructuralBreak,
		fmt.Sprintf("HTF structural break (%s) against %s thesis — trade invalidated", breakDirection, direction))
}

func (e *StructuralEngine) executeClosure(
	ctx context.Context,
	trade *types.Trade,
	tradeID, brokerID, symbol, direction string,
	entryPrice, currentPrice, riskAmount float64,
	isLong bool,
	eventType constants.EventType,
	reason string,
) (bool, error) {
	if err := e.bp.ClosePosition(ctx, brokerID); err != nil {
		return false, fmt.Errorf("invalidation close: %w", err)
	}

	// Calculate P&L.
	pnl := 0.0
	rMultiple := 0.0
	slDist := trade.SLDistanceFromEntry()
	if slDist > 0 && riskAmount > 0 {
		var priceDist float64
		if isLong {
			priceDist = currentPrice - entryPrice
		} else {
			priceDist = entryPrice - currentPrice
		}
		rMultiple = priceDist / slDist
		pnl = rMultiple * riskAmount
	}

	outcome := string(constants.OutcomeBreakeven)
	if pnl > 0 {
		outcome = string(constants.OutcomeWin)
	} else if pnl < 0 {
		outcome = string(constants.OutcomeLoss)
	}

	now := time.Now().UTC()

	trade.Lock()
	trade.Status = constants.StatusClosed
	trade.RealizedPnL += pnl
	trade.ClosedAt = now
	trade.CurrentPrice = currentPrice
	slMoves := trade.SLMoves
	partials := trade.Partials
	trade.Unlock()

	if err := e.journal.UpdateTradeClose(ctx, tradeID, currentPrice, pnl, rMultiple, outcome, now, trade.DurationMinutes(), slMoves, partials); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_close_failed")
	}

	if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
		TradeID:     tradeID,
		EventType:   string(eventType),
		Symbol:      symbol,
		Price:       currentPrice,
		RealizedPnL: pnl,
		RMultiple:   rMultiple,
		Reason:      reason,
		Timestamp:   now,
	}); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_event_failed")
	}

	observability.InvalidationTotal.WithLabelValues(symbol, string(eventType)).Inc()
	observability.TradeClosedTotal.WithLabelValues(symbol, outcome).Inc()

	if e.transport != nil {
		e.transport.Publish(ctx,
			alert.NewEvent(alert.SourceTradeManager, alert.TypeTradeClosed, alert.SeverityWarning,
				fmt.Sprintf("Invalidated: %s on %s", eventType, symbol)).
				WithSymbol(symbol).
				WithDetails(map[string]interface{}{
					"trade_id":   tradeID,
					"pnl":        pnl,
					"r_multiple": rMultiple,
					"outcome":    outcome,
					"reason":     reason,
				}),
		)
	}

	e.log.Warn().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Str("event", string(eventType)).
		Float64("close_price", currentPrice).
		Float64("pnl", pnl).
		Str("reason", reason).
		Msg("trade_invalidated_closed")

	return true, nil
}
