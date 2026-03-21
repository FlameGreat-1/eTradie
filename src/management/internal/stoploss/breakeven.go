package stoploss

import (
	"context"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// BreakevenEngine evaluates and executes break-even rules from
// Rulebook Section 9.1. It moves SL to entry + spread buffer
// when the appropriate conditions are met for each trading style.
type BreakevenEngine struct {
	bp      broker.Port
	journal *journal.Repository
	log     zerolog.Logger
}

// NewBreakevenEngine creates a break-even engine.
func NewBreakevenEngine(bp broker.Port, journal *journal.Repository) *BreakevenEngine {
	return &BreakevenEngine{
		bp:      bp,
		journal: journal,
		log:     observability.Logger("breakeven"),
	}
}

// Evaluate checks if the break-even condition is met and executes
// the SL move if conditions are satisfied. Returns true if BE was set.
func (e *BreakevenEngine) Evaluate(ctx context.Context, trade *types.Trade, checkPrice float64) (bool, error) {
	trade.RLock()
	if trade.BreakevenSet {
		trade.RUnlock()
		return false, nil
	}
	style := trade.TradingStyle
	tp1Price := trade.TP1Price
	entryPrice := trade.EntryPrice
	isLong := trade.IsLong()
	openedAt := trade.OpenedAt
	initialSL := trade.InitialSL
	trade.RUnlock()

	triggered := false

	switch style {
	case constants.StyleScalping:
		// Scalping exception: BE triggers at 60% of distance to TP1.
		distToTP1 := tp1Price - entryPrice
		if !isLong {
			distToTP1 = entryPrice - tp1Price
		}
		threshold := entryPrice + distToTP1*constants.ScalpBEThreshold
		if !isLong {
			threshold = entryPrice - distToTP1*constants.ScalpBEThreshold
		}
		if isLong && checkPrice >= threshold {
			triggered = true
		} else if !isLong && checkPrice <= threshold {
			triggered = true
		}

	case constants.StyleIntraday:
		// Standard: BE triggers when price reaches TP1.
		if isLong && checkPrice >= tp1Price {
			triggered = true
		} else if !isLong && checkPrice <= tp1Price {
			triggered = true
		}
		// Time-based exception: if TP1 not reached within 3 hours,
		// tighten SL to 50% of original risk.
		if !triggered && time.Since(openedAt) >= time.Duration(constants.IntradayBETimeoutHours)*time.Hour {
			return e.applyTimeTightening(ctx, trade, checkPrice, initialSL, entryPrice, isLong)
		}

	default:
		// Swing and Positional: standard TP1 trigger.
		if isLong && checkPrice >= tp1Price {
			triggered = true
		} else if !isLong && checkPrice <= tp1Price {
			triggered = true
		}
	}

	if !triggered {
		return false, nil
	}

	// Calculate new SL: entry + spread buffer (2-3 pips).
	// For BUY: SL = entry + buffer (above entry to lock in profit).
	// For SELL: SL = entry - buffer.
	bufferPips := constants.SpreadBufferPips
	newSL := entryPrice
	if isLong {
		newSL = entryPrice + bufferPips*0.0001 // Approximation; real pip size comes from instrument info.
	} else {
		newSL = entryPrice - bufferPips*0.0001
	}

	if err := e.bp.ModifyPosition(ctx, trade.BrokerOrderID, newSL, 0); err != nil {
		return false, err
	}

	// Update trade state.
	trade.Lock()
	trade.StopLoss = newSL
	trade.BreakevenSet = true
	trade.Status = constants.StatusBreakeven
	trade.SLMoves++
	trade.Unlock()

	// Persist.
	if err := e.journal.UpdateTradeSL(ctx, trade.TradeID, newSL); err != nil {
		e.log.Error().Err(err).Str("trade_id", trade.TradeID).Msg("journal_sl_update_failed")
	}
	if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
		TradeID:   trade.TradeID,
		EventType: string(constants.EventBreakevenSet),
		Symbol:    trade.Symbol,
		Price:     checkPrice,
		NewSL:     newSL,
		Reason:    "TP1 zone reached — SL moved to break-even",
		Timestamp: time.Now().UTC(),
	}); err != nil {
		e.log.Error().Err(err).Str("trade_id", trade.TradeID).Msg("journal_event_failed")
	}

	observability.BreakevenSetTotal.WithLabelValues(trade.Symbol).Inc()

	e.log.Info().
		Str("trade_id", trade.TradeID).
		Str("symbol", trade.Symbol).
		Float64("new_sl", newSL).
		Float64("trigger_price", checkPrice).
		Msg("breakeven_set")

	return true, nil
}

// applyTimeTightening handles the intraday 3-hour SL reduction rule.
func (e *BreakevenEngine) applyTimeTightening(ctx context.Context, trade *types.Trade, checkPrice, initialSL, entryPrice float64, isLong bool) (bool, error) {
	// Tighten SL to 50% of original risk distance.
	originalDist := entryPrice - initialSL
	if !isLong {
		originalDist = initialSL - entryPrice
	}
	halfDist := originalDist * constants.IntradaySLReductionPct

	var newSL float64
	if isLong {
		newSL = entryPrice - halfDist
	} else {
		newSL = entryPrice + halfDist
	}

	// Only tighten if the new SL is better than current.
	trade.RLock()
	currentSL := trade.StopLoss
	trade.RUnlock()

	tighten := false
	if isLong && newSL > currentSL {
		tighten = true
	} else if !isLong && newSL < currentSL {
		tighten = true
	}

	if !tighten {
		return false, nil
	}

	if err := e.bp.ModifyPosition(ctx, trade.BrokerOrderID, newSL, 0); err != nil {
		return false, err
	}

	trade.Lock()
	trade.StopLoss = newSL
	trade.SLMoves++
	trade.Unlock()

	if err := e.journal.UpdateTradeSL(ctx, trade.TradeID, newSL); err != nil {
		e.log.Error().Err(err).Str("trade_id", trade.TradeID).Msg("journal_sl_update_failed")
	}
	if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
		TradeID:   trade.TradeID,
		EventType: string(constants.EventSLTightened),
		Symbol:    trade.Symbol,
		Price:     checkPrice,
		NewSL:     newSL,
		Reason:    "3-hour intraday SL reduction — TP1 not reached",
		Timestamp: time.Now().UTC(),
	}); err != nil {
		e.log.Error().Err(err).Str("trade_id", trade.TradeID).Msg("journal_event_failed")
	}

	e.log.Info().
		Str("trade_id", trade.TradeID).
		Float64("new_sl", newSL).
		Msg("intraday_sl_tightened")

	return true, nil
}
