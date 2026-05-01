package monitoring

import (
	"context"
	"fmt"
	"time"

	"github.com/flamegreat-1/etradie/src/alert"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// runWorker is the per-trade monitoring goroutine. It polls the live
// tick feed and evaluates all sub-engines on every tick.
func (m *Manager) runWorker(ctx context.Context, trade *types.Trade) {
	defer m.wg.Done()

	tradeID := trade.TradeID
	symbol := trade.Symbol

	m.log.Info().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Str("user_id", trade.UserID).
		Msg("monitoring_worker_started")

	ticker := time.NewTicker(time.Duration(m.tickPollMs) * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			m.log.Info().Str("trade_id", tradeID).Msg("monitoring_worker_stopped")
			return

		case <-ticker.C:
			trade.RLock()
			status := trade.Status
			currentToken := trade.AuthToken
			trade.RUnlock()

			if status == constants.StatusClosed {
				m.log.Info().Str("trade_id", tradeID).Msg("trade_closed_worker_exiting")
				m.RemoveTrade(tradeID)
				return
			}

			// Build a fresh auth context on every tick cycle using the
			// trade's current AuthToken. This is critical because:
			// - Service tokens are set on startup for restored trades
			// - User session tokens replace service tokens on login
			//   via RefreshUserTradeTokens
			// - The worker must always use the most recent token
			// Go contexts are immutable, so we cannot update a frozen
			// authCtx created once at worker start.
			authCtx := auth.InjectTokenIntoContext(ctx, currentToken)

			// Read tick price from the shared cache. The cache is populated
			// by a single poller per symbol, eliminating redundant HTTP calls.
			// With 3,000 trades on 30 symbols, this is 30 HTTP calls/sec
			// instead of 3,000.
			tick := m.tickCache.GetTickPrice(symbol)
			if tick == nil {
				// Cache not yet populated (first poll hasn't completed).
				// Skip this cycle; the cache will be ready on the next tick.
				continue
			}

			checkPrice := trade.PriceForCheck(tick.Bid, tick.Ask)

			// Update current price.
			trade.Lock()
			trade.CurrentPrice = checkPrice

			// Update observability metrics
			if trade.EntryPrice > 0 {
				var pnlDist float64
				if trade.IsLong() {
					pnlDist = checkPrice - trade.EntryPrice
				} else {
					pnlDist = trade.EntryPrice - checkPrice
				}
				trade.UnrealizedPnL = pnlDist * trade.RemainingLotSize // Rough approximation without pip value
			}
			trade.Unlock()

			// === Evaluation order (priority-based) ===

			// 1. Check SL hit first (highest priority - protect capital).
			if trade.IsSLHit(checkPrice) {
				m.handleSLHit(authCtx, trade, checkPrice)
				m.RemoveTrade(tradeID)
				return
			}

			// 2. Check TP hits (lock profit).
			tpEvent, err := m.tp.Evaluate(authCtx, trade, checkPrice)
			if err != nil {
				m.log.Error().Err(err).Str("trade_id", tradeID).Msg("tp_eval_failed")
			}
			if tpEvent != "" {
				m.publishTPEvent(authCtx, trade, tpEvent, checkPrice)

				// Check if fully closed after TP3.
				trade.RLock()
				closed := trade.Status == constants.StatusClosed
				trade.RUnlock()
				if closed {
					m.RemoveTrade(tradeID)
					return
				}
			}

			// 3. Evaluate break-even (after TP check since TP1 triggers BE).
			beMoved, err := m.be.Evaluate(authCtx, trade, checkPrice)
			if err != nil {
				m.log.Error().Err(err).Str("trade_id", tradeID).Msg("be_eval_failed")
			}
			if beMoved {
				m.publishEvent(authCtx, trade, constants.EventBreakevenSet, checkPrice,
					"SL moved to break-even")
			}

			// 4. Evaluate trailing stop (only after BE is set).
			trailMoved, err := m.trail.Evaluate(authCtx, trade, checkPrice)
			if err != nil {
				m.log.Error().Err(err).Str("trade_id", tradeID).Msg("trail_eval_failed")
			}
			if trailMoved {
				m.publishEvent(authCtx, trade, constants.EventTrailingSLMoved, checkPrice,
					"Trailing SL adjusted")
			}
		}
	}
}

func (m *Manager) handleSLHit(ctx context.Context, trade *types.Trade, closePrice float64) {
	trade.RLock()
	tradeID := trade.TradeID
	userID := trade.UserID
	brokerID := trade.BrokerOrderID
	symbol := trade.Symbol
	entryPrice := trade.EntryPrice
	riskAmount := trade.RiskAmount
	isLong := trade.IsLong()
	trade.RUnlock()

	// Close position at broker.
	if err := m.bp.ClosePosition(ctx, brokerID); err != nil {
		m.log.Error().Err(err).Str("trade_id", tradeID).Msg("sl_hit_close_failed")
		return
	}

	// Wait slightly to ensure the deal propagates in broker history before querying
	time.Sleep(500 * time.Millisecond)

	// --- P&L Calculation (layered) ---
	pnl := 0.0
	rMultiple := 0.0
	pnlSource := "none"

	// Always compute price distance and R-multiple for journal enrichment.
	var priceDist float64
	if isLong {
		priceDist = closePrice - entryPrice
	} else {
		priceDist = entryPrice - closePrice
	}
	slDist := trade.SLDistanceFromEntry()
	if slDist > 0 {
		rMultiple = priceDist / slDist
	}

	// Layer 1: Broker deal history (most accurate, works for all instruments).
	if brokerPnL, ok := m.fetchClosedDealProfit(ctx, brokerID, symbol); ok {
		pnl = brokerPnL
		pnlSource = "broker_history"
	}

	// Layer 2: R-multiple system (fallback).
	if pnlSource == "none" && slDist > 0 && riskAmount > 0 {
		pnl = rMultiple * riskAmount
		pnlSource = "r_multiple"
	}

	if pnlSource == "none" {
		m.log.Warn().
			Str("trade_id", tradeID).
			Str("symbol", symbol).
			Float64("entry", entryPrice).
			Float64("close", closePrice).
			Float64("risk_amount", riskAmount).
			Msg("internal_sl_pnl_unavailable")
	}

	outcome := string(constants.OutcomeLoss)
	if pnl >= 0 {
		outcome = string(constants.OutcomeBreakeven)
	}

	now := time.Now().UTC()

	trade.Lock()
	trade.Status = constants.StatusClosed
	trade.RealizedPnL += pnl
	trade.ClosedAt = now
	slMoves := trade.SLMoves
	partials := trade.Partials
	trade.Unlock()

	if err := m.journal.UpdateTradeClose(ctx, userID, tradeID, closePrice, pnl, rMultiple, outcome, now, trade.DurationMinutes(), slMoves, partials); err != nil {
		m.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_close_failed")
	}

	if err := m.journal.InsertEvent(ctx, &journal.TradeEvent{
		UserID:      userID,
		TradeID:     tradeID,
		EventType:   string(constants.EventSLHit),
		Symbol:      symbol,
		Price:       closePrice,
		RealizedPnL: pnl,
		RMultiple:   rMultiple,
		Reason:      fmt.Sprintf("Stop loss hit at %.5f", closePrice),
		Timestamp:   now,
	}); err != nil {
		m.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_event_failed")
	}

	observability.TradeClosedTotal.WithLabelValues(symbol, outcome).Inc()

	m.transport.Publish(ctx,
		alert.NewEvent(alert.SourceTradeManager, alert.TypeTradeClosed, alert.SeverityWarning,
			fmt.Sprintf("SL hit on %s — trade closed at %.5f (%.2fR, $%.2f)", symbol, closePrice, rMultiple, pnl)).
			WithSymbol(symbol).
			WithDetails(map[string]interface{}{
				"trade_id":   tradeID,
				"pnl":        pnl,
				"r_multiple": rMultiple,
				"outcome":    outcome,
				"pnl_source": pnlSource,
			}),
	)

	m.log.Warn().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Float64("close_price", closePrice).
		Float64("pnl", pnl).
		Float64("r", rMultiple).
		Str("pnl_source", pnlSource).
		Msg("sl_hit_trade_closed")
}

// HandleExternalClose finalizes a trade that vanished from the broker
// (e.g. manually closed on MT5 app or broker-side SL/TP hit).
//
// P&L is calculated using a layered approach:
//
//  1. Primary: Query broker deal history for the exact profit. MT5
//     records the precise result including commission, swap, and correct
//     contract sizing for ALL instrument types (forex, synthetics, indices).
//
//  2. Fallback: R-multiple system (requires both slDist and riskAmount
//     from the analysis pipeline). Only available for trades placed via
//     Module B; reconciled/manual trades have riskAmount = 0.
//
// R-multiple is always computed when slDist > 0 for journal enrichment.
func (m *Manager) HandleExternalClose(ctx context.Context, trade *types.Trade) {
	trade.RLock()
	tradeID := trade.TradeID
	userID := trade.UserID
	symbol := trade.Symbol
	entryPrice := trade.EntryPrice
	riskAmount := trade.RiskAmount
	isLong := trade.IsLong()
	closePrice := trade.CurrentPrice // Last known tick before position vanished
	brokerOrderID := trade.BrokerOrderID
	trade.RUnlock()

	// --- P&L Calculation (layered) ---
	pnl := 0.0
	rMultiple := 0.0
	pnlSource := "none"

	// Always compute price distance and R-multiple for journal enrichment.
	var priceDist float64
	if isLong {
		priceDist = closePrice - entryPrice
	} else {
		priceDist = entryPrice - closePrice
	}
	slDist := trade.SLDistanceFromEntry()
	if slDist > 0 {
		rMultiple = priceDist / slDist
	}

	// Layer 1: Broker deal history (most accurate, works for all instruments).
	if brokerPnL, ok := m.fetchClosedDealProfit(ctx, brokerOrderID, symbol); ok {
		pnl = brokerPnL
		pnlSource = "broker_history"
	}

	// Layer 2: R-multiple system (when risk data is available from analysis pipeline).
	if pnlSource == "none" && slDist > 0 && riskAmount > 0 {
		pnl = rMultiple * riskAmount
		pnlSource = "r_multiple"
	}

	if pnlSource == "none" {
		m.log.Warn().
			Str("trade_id", tradeID).
			Str("symbol", symbol).
			Float64("entry", entryPrice).
			Float64("close", closePrice).
			Float64("risk_amount", riskAmount).
			Msg("external_close_pnl_unavailable")
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
	slMoves := trade.SLMoves
	partials := trade.Partials
	trade.Unlock()

	if err := m.journal.UpdateTradeClose(ctx, userID, tradeID, closePrice, pnl, rMultiple, outcome, now, trade.DurationMinutes(), slMoves, partials); err != nil {
		m.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_close_failed")
	}

	if err := m.journal.InsertEvent(ctx, &journal.TradeEvent{
		UserID:      userID,
		TradeID:     tradeID,
		EventType:   string(constants.EventExternalClose),
		Symbol:      symbol,
		Price:       closePrice,
		RealizedPnL: pnl,
		RMultiple:   rMultiple,
		Reason:      "Externally closed on broker",
		Timestamp:   now,
	}); err != nil {
		m.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_event_failed")
	}

	observability.TradeClosedTotal.WithLabelValues(symbol, outcome).Inc()

	m.transport.Publish(ctx,
		alert.NewEvent(alert.SourceTradeManager, alert.TypeTradeClosed, alert.SeverityInfo,
			fmt.Sprintf("External close on %s — trade closed at %.5f (%.2fR, $%.2f)", symbol, closePrice, rMultiple, pnl)).
			WithSymbol(symbol).
			WithUserID(userID).
			WithDetails(map[string]interface{}{
				"trade_id":   tradeID,
				"pnl":        pnl,
				"r_multiple": rMultiple,
				"outcome":    outcome,
				"pnl_source": pnlSource,
			}),
	)

	m.log.Info().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Float64("pnl", pnl).
		Float64("r_multiple", rMultiple).
		Str("outcome", outcome).
		Str("pnl_source", pnlSource).
		Msg("external_close_processed")

	// Crucial: Remove the trade from active management so it disappears from the Active Trades UI.
	m.RemoveTrade(tradeID)
}

// fetchClosedDealProfit queries the broker's deal history to find the
// actual P&L for a closed position. MT5 records the exact profit
// including commission and swap for all instrument types, so this is
// the most accurate P&L source.
//
// Returns (totalProfit, true) if found, or (0, false) if the deal was
// not found in history or the query failed.
func (m *Manager) fetchClosedDealProfit(ctx context.Context, brokerOrderID, symbol string) (float64, bool) {
	if brokerOrderID == "" {
		return 0, false
	}

	history, err := m.bp.GetHistory(ctx, 1) // last 1 day of deals
	if err != nil {
		m.log.Warn().Err(err).
			Str("broker_order_id", brokerOrderID).
			Msg("broker_history_fetch_failed_for_pnl")
		return 0, false
	}

	// Search backward to find the MOST RECENT close deal matching this position.
	// This is critical because a position might have multiple partial
	// closes (multiple OUT deals). By searching backward, we grab the
	// one that was just executed.
	for i := len(history) - 1; i >= 0; i-- {
		deal := history[i]
		if deal.PositionID == brokerOrderID || deal.Ticket == brokerOrderID {
			if deal.Symbol != "" && deal.Symbol != symbol {
				continue // Different symbol, not our deal
			}
			totalProfit := deal.Profit + deal.Commission + deal.Swap
			m.log.Info().
				Str("broker_order_id", brokerOrderID).
				Str("deal_ticket", deal.Ticket).
				Float64("profit", deal.Profit).
				Float64("commission", deal.Commission).
				Float64("swap", deal.Swap).
				Float64("total", totalProfit).
				Msg("broker_deal_profit_resolved")
			return totalProfit, true
		}
	}

	m.log.Warn().
		Str("broker_order_id", brokerOrderID).
		Str("symbol", symbol).
		Int("history_deals_checked", len(history)).
		Msg("broker_deal_not_found_in_history")
	return 0, false
}

func (m *Manager) publishTPEvent(ctx context.Context, trade *types.Trade, event constants.EventType, price float64) {
	trade.RLock()
	symbol := trade.Symbol
	tradeID := trade.TradeID
	trade.RUnlock()

	alertType := alert.TypePartialClose
	if event == constants.EventTP3Hit {
		alertType = alert.TypeTradeClosed
	}

	m.transport.Publish(ctx,
		alert.NewEvent(alert.SourceTradeManager, alertType, alert.SeverityInfo,
			fmt.Sprintf("%s on %s at %.5f", event, symbol, price)).
			WithSymbol(symbol).
			WithDetails(map[string]interface{}{
				"trade_id": tradeID,
				"event":    string(event),
				"price":    price,
			}),
	)
}

func (m *Manager) publishEvent(ctx context.Context, trade *types.Trade, event constants.EventType, price float64, message string) {
	trade.RLock()
	symbol := trade.Symbol
	tradeID := trade.TradeID
	trade.RUnlock()

	alertType := alert.TypeBreakevenSet
	if event == constants.EventTrailingSLMoved {
		alertType = alert.TypeTrailingSLMoved
	}

	m.transport.Publish(ctx,
		alert.NewEvent(alert.SourceTradeManager, alertType, alert.SeverityInfo,
			fmt.Sprintf("%s \u2014 %s on %s", message, event, symbol)).
			WithSymbol(symbol).
			WithDetails(map[string]interface{}{
				"trade_id": tradeID,
				"event":    string(event),
				"price":    price,
			}),
	)
}
