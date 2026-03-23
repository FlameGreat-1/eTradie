package eod

import (
	"context"
	"fmt"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
	"time"
)

// executeClosure is a shared helper that calculates P&L, updates trade state,
// persists to journal, logs the event, and updates metrics after a forced EOD closure.
func executeClosure(
	ctx context.Context,
	repo *journal.Repository,
	transport *alertredis.Transport,
	log zerolog.Logger,
	trade *types.Trade,
	currentPrice float64,
	entryPrice float64,
	riskAmount float64,
	isLong bool,
	reason string,
	now time.Time,
	symbol string,
	style constants.TradingStyle,
) (bool, error) {

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

	// Determine outcome.
	outcome := string(constants.OutcomeBreakeven)
	if pnl > 0 {
		outcome = string(constants.OutcomeWin)
	} else if pnl < 0 {
		outcome = string(constants.OutcomeLoss)
	}

	// Update trade state.
	trade.Lock()
	trade.Status = constants.StatusClosed
	trade.RealizedPnL += pnl
	trade.ClosedAt = now
	trade.CurrentPrice = currentPrice
	tradeID := trade.TradeID
	slMoves := trade.SLMoves
	partials := trade.Partials
	trade.Unlock()

	// Persist close.
	if err := repo.UpdateTradeClose(ctx, tradeID, currentPrice, pnl, rMultiple, outcome, now, trade.DurationMinutes(), slMoves, partials); err != nil {
		log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_close_failed")
	}

	if err := repo.InsertEvent(ctx, &journal.TradeEvent{
		TradeID:     tradeID,
		EventType:   string(constants.EventEODClosure),
		Symbol:      symbol,
		Price:       currentPrice,
		RealizedPnL: pnl,
		RMultiple:   rMultiple,
		Reason:      reason,
		Timestamp:   now,
	}); err != nil {
		log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_event_failed")
	}

	observability.EODClosureTotal.WithLabelValues(symbol, string(style)).Inc()
	observability.TradeClosedTotal.WithLabelValues(symbol, outcome).Inc()

	if transport != nil {
		transport.Publish(ctx,
			alert.NewEvent(alert.SourceTradeManager, alert.TypeTradeClosed, alert.SeverityWarning,
				fmt.Sprintf("EOD Forced Close (%s) on %s at %.5f", style, symbol, currentPrice)).
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

	log.Info().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Str("style", string(style)).
		Float64("close_price", currentPrice).
		Float64("pnl", pnl).
		Float64("r_multiple", rMultiple).
		Str("reason", reason).
		Msg("eod_forced_close")

	return true, nil
}
