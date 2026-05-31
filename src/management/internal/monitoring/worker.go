package monitoring

import (
	"context"
	"fmt"
	"time"

	"github.com/flamegreat-1/etradie/src/alert"
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

	// Separate, slower ticker to poll the broker for real P&L data.
	// The broker's GetPosition returns exact Profit/Swap/Commission
	// that accounts for contract size, pip value, and all instrument
	// specifics. This replaces the inaccurate local approximation.
	positionTicker := time.NewTicker(2 * time.Second)
	defer positionTicker.Stop()

	for {
		select {
		case <-ctx.Done():
			m.log.Info().Str("trade_id", tradeID).Msg("monitoring_worker_stopped")
			return

		case <-positionTicker.C:
			// Poll broker for the real, authoritative P&L data.
			// This runs every 2s (independent of the fast tick loop)
			// and updates UnrealizedPnL, Swap, Commission from the
			// broker's actual position state — the same source the
			// Chart UI uses, ensuring perfect parity.
			trade.RLock()
			pAuthCtx := trade.IdentityCtx(ctx)
			brokerID := trade.BrokerOrderID
			trade.RUnlock()

			pos, err := m.bp.GetPosition(pAuthCtx, brokerID)
			if err == nil && pos != nil {
				trade.Lock()
				trade.UnrealizedPnL = pos.Profit
				trade.Swap = pos.Swap
				trade.Commission = pos.Commission
				// Also update current price from position data as a
				// secondary source (the fast tick loop is primary).
				if pos.CurrentPrice > 0 {
					trade.CurrentPrice = pos.CurrentPrice
				}
				trade.Unlock()
			}

		case <-ticker.C:
			trade.RLock()
			status := trade.Status
			trade.RUnlock()

			if status == constants.StatusClosed {
				m.log.Info().Str("trade_id", tradeID).Msg("trade_closed_worker_exiting")
				m.RemoveTrade(tradeID)
				return
			}

			// Build a fresh auth context AND snapshot the user-id for the
			// tick-cache lookup under the same RLock window. Trade.UserID
			// is in principle immutable after RegisterTrade, but we still
			// read it under the lock to be consistent with the identity
			// fields that DO get refreshed via RefreshUserTradeIdentity.
			trade.RLock()
			authCtx := trade.IdentityCtx(ctx)
			userID := trade.UserID
			trade.RUnlock()

			// Read tick price from the per-(user, symbol) cache. The cache
			// has a dedicated poller for this user's quotes on this symbol,
			// authenticated with that user's broker connection on the
			// engine side. No cross-tenant price contamination.
			tick := m.tickCache.GetTickPrice(userID, symbol)
			if tick == nil {
				// Cache not yet populated (first poll hasn't completed).
				// Skip this cycle; the cache will be ready on the next tick.
				continue
			}

			checkPrice := trade.PriceForCheck(tick.Bid, tick.Ask)

			// Guard against zero/missing Ask price. MT5 sometimes
			// broadcasts "half-ticks" where only the Bid changes,
			// leaving Ask as 0. For SELL trades PriceForCheck returns
			// the Ask, so a zero value would corrupt the PnL display
			// and cause it to flicker on/off. Skip these ticks.
			if checkPrice <= 0 {
				continue
			}

			// Update current price from the fast tick loop.
			trade.Lock()
			trade.CurrentPrice = checkPrice
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

	// Layer 1: Broker deal history (exact profit, commissions, swaps).
	if brokerPnL, ok := m.pollClosedDealProfit(ctx, brokerID, symbol); ok {
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

// pollClosedDealProfit polls the broker deal history until the closed
// deal for brokerOrderID is found or the deadline is reached. Polling
// avoids a fixed sleep whose duration is a timing assumption: MT5 deal
// history propagation is non-deterministic and varies by broker.
func (m *Manager) pollClosedDealProfit(ctx context.Context, brokerOrderID, symbol string) (float64, bool) {
	const (
		maxAttempts  = 5
		pollInterval = 200 * time.Millisecond
	)
	for i := 0; i < maxAttempts; i++ {
		if i > 0 {
			select {
			case <-time.After(pollInterval):
			case <-ctx.Done():
				return 0, false
			}
		}
		if pnl, ok := m.fetchClosedDealProfit(ctx, brokerOrderID, symbol); ok {
			return pnl, true
		}
	}
	return 0, false
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
