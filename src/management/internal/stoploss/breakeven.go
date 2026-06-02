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
	bp          broker.Port
	journal     *journal.Repository
	log         zerolog.Logger
	lastAttempt map[string]time.Time
}

// NewBreakevenEngine creates a break-even engine.
func NewBreakevenEngine(bp broker.Port, journal *journal.Repository) *BreakevenEngine {
	return &BreakevenEngine{
		bp:          bp,
		journal:     journal,
		log:         observability.Logger("breakeven"),
		lastAttempt: make(map[string]time.Time),
	}
}

// Evaluate checks if the break-even condition is met and executes
// the SL move if conditions are satisfied. Returns true if BE was set.
func (e *BreakevenEngine) Evaluate(ctx context.Context, trade *types.Trade, checkPrice float64) (bool, error) {
	if last, ok := e.lastAttempt[trade.TradeID]; ok && time.Since(last) < 10*time.Second {
		return false, nil // Throttle ZMQ requests if MT5 is rejecting us
	}
	e.lastAttempt[trade.TradeID] = time.Now()

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
	userID := trade.UserID
	symbol := trade.Symbol
	digits := trade.Digits
	tradePoint := trade.Point // Read broker point
	trade.RUnlock()

	// EM-C2 self-heal: a trade restored from a pre-migration row (or a
	// reconciler-imported one) can have Point==0. Fetch the real point +
	// digits from the broker symbol_info ONCE, stamp + persist them so
	// BE/trailing math runs on the correct scale instead of a hardcoded
	// FX fallback. (The /internal/broker/position response carries no
	// point/digits, so symbol_info is the correct source.)
	if tradePoint <= 0 {
		if si, serr := e.bp.GetSymbolInfo(ctx, symbol); serr == nil && si != nil && si.Point > 0 {
			tradePoint = si.Point
			trade.Lock()
			trade.Point = si.Point
			if si.Digits > 0 {
				trade.Digits = si.Digits
				digits = si.Digits
			}
			trade.Unlock()
			if err := e.journal.UpdateTradePointDigits(ctx, userID, trade.TradeID, si.Point, si.Digits); err != nil {
				e.log.Error().Err(err).Str("trade_id", trade.TradeID).Msg("journal_point_self_heal_failed")
			}
		}
	}

	// Canonical pip size (synthetic/digits-aware). Falls back to the FX
	// 5-digit convention only when the broker point is genuinely unknown.
	pipSize := constants.PipSize(symbol, tradePoint, digits)
	if pipSize <= 0 {
		if tradePoint > 0 {
			pipSize = tradePoint * 10
		} else {
			pipSize = 0.0001 * 10
		}
	}
	// pointForFallback is the raw point used only for the no-SL/no-TP
	// synthesized target below; keep it non-zero for safety.
	pointForFallback := tradePoint
	if pointForFallback <= 0 {
		pointForFallback = 0.0001
	}

	triggered := false

	// If TP1 is exactly 0.0 (e.g. manual trade with no TP), we must synthesize a target
	// to avoid instant triggering. A standard conservative move is 1:1 against the InitialSL,
	// or simply a fixed point threshold if InitialSL is also 0.0.
	if tp1Price == 0.0 {
		if initialSL > 0.0 {
			if isLong {
				tp1Price = entryPrice + (entryPrice - initialSL)
			} else {
				tp1Price = entryPrice - (initialSL - entryPrice)
			}
		} else {
			// No SL and no TP. Default to a 500 point move.
			if isLong {
				tp1Price = entryPrice + 500*pointForFallback
			} else {
				tp1Price = entryPrice - 500*pointForFallback
			}
		}
	}

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
		newSL = entryPrice + bufferPips*pipSize
	} else {
		newSL = entryPrice - bufferPips*pipSize
	}

	if err := e.bp.ModifyPosition(ctx, trade.BrokerOrderID, newSL, 0); err != nil {
		return false, err
	}

	// Update trade state. Snapshot the post-mutation runtime values under
	// the same write lock so the durable runtime row matches memory.
	trade.Lock()
	trade.StopLoss = newSL
	trade.BreakevenSet = true
	trade.Status = constants.StatusBreakeven
	trade.SLMoves++
	snapRemaining := trade.RemainingLotSize
	snapTP1Hit := trade.TP1Hit
	snapTP2Hit := trade.TP2Hit
	snapTP3Hit := trade.TP3Hit
	trade.Unlock()

	// Persist the SL move (records the sl_adjustments counter).
	if err := e.journal.UpdateTradeSL(ctx, userID, trade.TradeID, newSL); err != nil {
		e.log.Error().Err(err).Str("trade_id", trade.TradeID).Msg("journal_sl_update_failed")
	}

	// Persist the break-even flag + SL so a restart restores BreakevenSet
	// (audit EM-C1): trailing only activates after break-even, so a lost
	// flag silently disables trailing on the restored trade.
	if err := e.journal.UpdateTradeRuntime(ctx, userID, trade.TradeID, snapRemaining, newSL, snapTP1Hit, snapTP2Hit, snapTP3Hit, true); err != nil {
		e.log.Error().Err(err).Str("trade_id", trade.TradeID).Msg("journal_runtime_update_failed")
	}
	if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
		UserID:    userID,
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

	userID := trade.UserID
	if err := e.journal.UpdateTradeSL(ctx, userID, trade.TradeID, newSL); err != nil {
		e.log.Error().Err(err).Str("trade_id", trade.TradeID).Msg("journal_sl_update_failed")
	}
	if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
		UserID:    userID,
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
