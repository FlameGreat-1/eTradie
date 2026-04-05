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

	// Inject the user's auth token into the worker context so all
	// downstream broker HTTP calls are authenticated. The token was
	// captured from the original gRPC request and stored on the Trade
	// struct by the gRPC server. This follows the same pattern as
	// Execution's watcher/manager.go.
	authCtx := auth.InjectTokenIntoContext(ctx, trade.AuthToken)

	m.log.Info().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Str("user_id", trade.UserID).
		Msg("monitoring_worker_started")

	ticker := time.NewTicker(time.Duration(m.tickPollMs) * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-authCtx.Done():
			m.log.Info().Str("trade_id", tradeID).Msg("monitoring_worker_stopped")
			return

		case <-ticker.C:
			trade.RLock()
			status := trade.Status
			trade.RUnlock()

			if status == constants.StatusClosed {
				m.log.Info().Str("trade_id", tradeID).Msg("trade_closed_worker_exiting")
				m.RemoveTrade(tradeID)
				return
			}

			tick, err := m.bp.GetTickPrice(authCtx, symbol)
			if err != nil {
				m.log.Error().Err(err).Str("trade_id", tradeID).Msg("tick_poll_failed")
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

			// 1. Check SL hit first (highest priority — protect capital).
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

	// Calculate P&L.
	pnl := 0.0
	rMultiple := 0.0
	slDist := trade.SLDistanceFromEntry()
	if slDist > 0 && riskAmount > 0 {
		var priceDist float64
		if isLong {
			priceDist = closePrice - entryPrice
		} else {
			priceDist = entryPrice - closePrice
		}
		rMultiple = priceDist / slDist
		pnl = rMultiple * riskAmount
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
			fmt.Sprintf("SL hit on %s \u2014 trade closed at %.5f (%.2fR)", symbol, closePrice, rMultiple)).
			WithSymbol(symbol).
			WithDetails(map[string]interface{}{
				"trade_id":   tradeID,
				"pnl":        pnl,
				"r_multiple": rMultiple,
				"outcome":    outcome,
			}),
	)

	m.log.Warn().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Float64("close_price", closePrice).
		Float64("pnl", pnl).
		Float64("r", rMultiple).
		Msg("sl_hit_trade_closed")
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
