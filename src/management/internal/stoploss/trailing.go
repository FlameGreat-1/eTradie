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

// TrailingEngine implements a style-adaptive, high-water-mark trailing
// stop. After break-even is set, it moves SL behind price by protecting
// a configurable FRACTION of the favourable move from entry, tightening
// only (never widening) and tightening further once TP1 is hit.
//
// DELIBERATE CONTRACT DECISION (audit EM-H2):
// Rulebook Section 9.2 (STYLE-MGMT-002) specifies a SWING-based trail
// (trail behind the last swing low/high on the style's timeframe). Module
// C does not receive candle/swing structure today (that is Module A's
// domain and is not streamed here), so a genuinely swing-based trail
// would require a new structural data feed into Module C. Rather than
// claim swing behaviour we do not implement, this engine's CONTRACT is
// the fractional model below; it is the standard institutional fallback
// when swing data is not streamed in real time. Upgrading to a true
// swing trail (feed the candle-closed alert's swing levels into Module C)
// is a tracked future enhancement, not a silent gap.
//
// Fractional model:
//   - BUY:  newSL = price - (1-fraction) * (price - entry)
//   - SELL: newSL = price + (1-fraction) * (entry - price)
// where fraction is trailFractionForStyle(style, tp1Hit). Higher fraction
// = tighter trail = more locked profit.
type TrailingEngine struct {
	bp          broker.Port
	journal     *journal.Repository
	log         zerolog.Logger
	lastAttempt map[string]time.Time
}

// NewTrailingEngine creates a trailing stop engine.
func NewTrailingEngine(bp broker.Port, journal *journal.Repository) *TrailingEngine {
	return &TrailingEngine{
		bp:          bp,
		journal:     journal,
		log:         observability.Logger("trailing"),
		lastAttempt: make(map[string]time.Time),
	}
}

// Evaluate checks if the trailing stop should be tightened based on
// the current price relative to the trade's progress. Returns true
// if the SL was adjusted.
func (e *TrailingEngine) Evaluate(ctx context.Context, trade *types.Trade, checkPrice float64) (bool, error) {
	if last, ok := e.lastAttempt[trade.TradeID]; ok && time.Since(last) < 10*time.Second {
		return false, nil // Throttle ZMQ requests if MT5 is rejecting us
	}
	e.lastAttempt[trade.TradeID] = time.Now()

	trade.RLock()
	if !trade.BreakevenSet {
		trade.RUnlock()
		return false, nil // Trailing only activates after break-even.
	}
	style := trade.TradingStyle
	isLong := trade.IsLong()
	entryPrice := trade.EntryPrice
	currentSL := trade.StopLoss
	tradeID := trade.TradeID
	brokerID := trade.BrokerOrderID
	symbol := trade.Symbol
	tp1Hit := trade.TP1Hit
	userID := trade.UserID
	trade.RUnlock()

	// Get the trailing config for this style to ensure it's supported.
	_, ok := constants.TrailConfigByStyle[style]
	if !ok {
		return false, nil
	}

	// The timeframe determines how aggressively we trail. Shorter TF
	// (e.g., 15M for scalping) means tighter stops. We approximate this
	// with a trailFraction: the fraction of the total move we protect.

	trailFraction := e.trailFractionForStyle(style, tp1Hit)

	// Calculate the potential new SL based on price progress.
	var newSL float64
	if isLong {
		// For BUY: trail below price. newSL = price - (fraction * total_move)
		totalMove := checkPrice - entryPrice
		if totalMove <= 0 {
			return false, nil // Price hasn't moved beyond entry.
		}
		newSL = checkPrice - totalMove*(1.0-trailFraction)
	} else {
		// For SELL: trail above price.
		totalMove := entryPrice - checkPrice
		if totalMove <= 0 {
			return false, nil
		}
		newSL = checkPrice + totalMove*(1.0-trailFraction)
	}

	// Only tighten — never widen the SL.
	shouldUpdate := false
	if isLong && newSL > currentSL {
		shouldUpdate = true
	} else if !isLong && newSL < currentSL {
		shouldUpdate = true
	}

	if !shouldUpdate {
		return false, nil
	}

	// Execute the modification at the broker. Preserve the broker's
	// FINAL-target TP (TP3) on the SL move; passing 0 would clear the
	// broker take-profit (TRADE_ACTION_SLTP tp=0).
	if err := e.bp.ModifyPosition(ctx, brokerID, newSL, trade.BrokerTakeProfit()); err != nil {
		return false, err
	}

	// Update trade state.
	trade.Lock()
	trade.StopLoss = newSL
	trade.Status = constants.StatusTrailing
	trade.SLMoves++
	trade.Unlock()

	// Persist.
	if err := e.journal.UpdateTradeSL(ctx, userID, tradeID, newSL); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_sl_update_failed")
	}
	if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
		UserID:    userID,
		TradeID:   tradeID,
		EventType: string(constants.EventTrailingSLMoved),
		Symbol:    symbol,
		Price:     checkPrice,
		NewSL:     newSL,
		Reason:    "Trailing SL moved — price progress locked in",
		Timestamp: time.Now().UTC(),
	}); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_event_failed")
	}

	observability.TrailingSLMovedTotal.WithLabelValues(symbol).Inc()

	e.log.Info().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Float64("new_sl", newSL).
		Float64("check_price", checkPrice).
		Str("style", string(style)).
		Msg("trailing_sl_moved")

	return true, nil
}

// trailFractionForStyle returns what fraction of the move from entry
// should be protected by the trailing stop. Higher = tighter trail.
//
// Rulebook Section 9.2 mappings:
// Scalping (15M swings)  → aggressive trail, protect 60% of move.
// Intraday (1H-4H swings) → moderate trail, protect 50%.
// Swing (4H-1D swings)   → wide trail, protect 40%.
// Positional (1D-1W)     → widest trail, protect 30%.
//
// After TP1 is hit, the trail tightens by 10% to lock more profit.
func (e *TrailingEngine) trailFractionForStyle(style constants.TradingStyle, tp1Hit bool) float64 {
	base := 0.50 // Default

	switch style {
	case constants.StyleScalping:
		base = 0.60
	case constants.StyleIntraday:
		base = 0.50
	case constants.StyleSwing:
		base = 0.40
	case constants.StylePositional:
		base = 0.30
	}

	if tp1Hit {
		base += 0.10
	}

	return base
}
