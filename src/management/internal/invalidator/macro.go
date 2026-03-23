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

// MacroEngine monitors macro condition changes that may invalidate
// or require adjustment of managed trades. Per Rulebook Section 5.4:
//   - Weekly COT alert flips: if COT positioning flips against the
//     trade direction, tighten SL or exit.
//   - High-impact news surprises: if an unexpected macro event moves
//     the market significantly, evaluate whether to exit immediately.
type MacroEngine struct {
	bp        broker.Port
	journal   *journal.Repository
	transport *alertredis.Transport
	log       zerolog.Logger
}

// NewMacroEngine creates a macro invalidation engine.
func NewMacroEngine(bp broker.Port, journal *journal.Repository, transport *alertredis.Transport) *MacroEngine {
	return &MacroEngine{
		bp:        bp,
		journal:   journal,
		transport: transport,
		log:       observability.Logger("invalidator_macro"),
	}
}

// EvaluateCOTFlip evaluates a COT positioning flip against the trade.
// If the COT signal changes direction against the trade, the SL is
// tightened to 50% of remaining risk or the trade is closed if already
// in loss territory.
func (e *MacroEngine) EvaluateCOTFlip(ctx context.Context, trade *types.Trade, cotDirection string, currentPrice float64) (bool, error) {
	trade.RLock()
	tradeID := trade.TradeID
	brokerID := trade.BrokerOrderID
	symbol := trade.Symbol
	direction := trade.Direction
	entryPrice := trade.EntryPrice
	currentSL := trade.StopLoss
	riskAmount := trade.RiskAmount
	isLong := trade.IsLong()
	status := trade.Status
	trade.RUnlock()

	if status == constants.StatusClosed {
		return false, nil
	}

	// Check if COT flip is against our direction.
	flipped := false
	if isLong && cotDirection == "BEARISH" {
		flipped = true
	} else if !isLong && cotDirection == "BULLISH" {
		flipped = true
	}

	if !flipped {
		return false, nil
	}

	// If the trade is already in loss territory, close immediately.
	var priceDiff float64
	if isLong {
		priceDiff = currentPrice - entryPrice
	} else {
		priceDiff = entryPrice - currentPrice
	}

	if priceDiff < 0 {
		// In loss territory with adverse COT — close immediately.
		if err := e.bp.ClosePosition(ctx, brokerID); err != nil {
			return false, fmt.Errorf("COT flip close: %w", err)
		}

		pnl := 0.0
		rMultiple := 0.0
		slDist := trade.SLDistanceFromEntry()
		if slDist > 0 && riskAmount > 0 {
			rMultiple = priceDiff / slDist
			pnl = rMultiple * riskAmount
		}

		outcome := string(constants.OutcomeLoss)
		now := time.Now().UTC()

		trade.Lock()
		trade.Status = constants.StatusClosed
		trade.RealizedPnL += pnl
		trade.ClosedAt = now
		slMoves := trade.SLMoves
		partials := trade.Partials
		trade.Unlock()

		if err := e.journal.UpdateTradeClose(ctx, tradeID, currentPrice, pnl, rMultiple, outcome, now, trade.DurationMinutes(), slMoves, partials); err != nil {
			e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_close_failed")
		}
		if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
			TradeID:     tradeID,
			EventType:   string(constants.EventCOTFlip),
			Symbol:      symbol,
			Price:       currentPrice,
			RealizedPnL: pnl,
			RMultiple:   rMultiple,
			Reason:      fmt.Sprintf("COT flip (%s) against %s trade in loss territory — closed", cotDirection, direction),
			Timestamp:   now,
		}); err != nil {
			e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_event_failed")
		}

		observability.InvalidationTotal.WithLabelValues(symbol, "COT_FLIP_CLOSE").Inc()
		observability.TradeClosedTotal.WithLabelValues(symbol, outcome).Inc()

		if e.transport != nil {
			e.transport.Publish(ctx,
				alert.NewEvent(alert.SourceTradeManager, alert.TypeTradeClosed, alert.SeverityWarning,
					fmt.Sprintf("Invalidated (Macro): COT Flip against %s trade on %s", direction, symbol)).
					WithSymbol(symbol).
					WithDetails(map[string]interface{}{
						"trade_id":   tradeID,
						"pnl":        pnl,
						"r_multiple": rMultiple,
						"outcome":    outcome,
					}),
			)
		}

		e.log.Warn().
			Str("trade_id", tradeID).
			Str("symbol", symbol).
			Float64("pnl", pnl).
			Msg("cot_flip_forced_close")

		return true, nil
	}

	// In profit territory — tighten SL to 50% of current distance.
	halfDist := priceDiff * 0.50
	var newSL float64
	if isLong {
		newSL = currentPrice - halfDist
	} else {
		newSL = currentPrice + halfDist
	}

	// Only tighten, never widen.
	shouldTighten := false
	if isLong && newSL > currentSL {
		shouldTighten = true
	} else if !isLong && newSL < currentSL {
		shouldTighten = true
	}

	if !shouldTighten {
		return false, nil
	}

	if err := e.bp.ModifyPosition(ctx, brokerID, newSL, 0); err != nil {
		return false, fmt.Errorf("COT tighten SL: %w", err)
	}

	trade.Lock()
	trade.StopLoss = newSL
	trade.SLMoves++
	trade.Unlock()

	if err := e.journal.UpdateTradeSL(ctx, tradeID, newSL); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_sl_update_failed")
	}
	if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
		TradeID:   tradeID,
		EventType: string(constants.EventSLTightened),
		Symbol:    symbol,
		Price:     currentPrice,
		NewSL:     newSL,
		Reason:    fmt.Sprintf("COT flip (%s) against %s — SL tightened to lock profit", cotDirection, direction),
		Timestamp: time.Now().UTC(),
	}); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_event_failed")
	}

	observability.InvalidationTotal.WithLabelValues(symbol, "COT_FLIP_TIGHTEN").Inc()

	if e.transport != nil {
		e.transport.Publish(ctx,
			alert.NewEvent(alert.SourceTradeManager, alert.TypeTrailingSLMoved, alert.SeverityInfo,
				fmt.Sprintf("Macro Caution: SL tightened on %s due to adverse COT flip", symbol)).
				WithSymbol(symbol).
				WithDetails(map[string]interface{}{
					"trade_id": tradeID,
					"new_sl":   newSL,
				}),
		)
	}

	e.log.Warn().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Float64("new_sl", newSL).
		Msg("cot_flip_sl_tightened")

	return true, nil
}
