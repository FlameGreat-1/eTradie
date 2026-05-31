package takeprofit

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// Executor handles partial take-profit closures per Rulebook Section 8.3.
// When price reaches a TP level, the executor sends a partial close
// order to the broker for the configured percentage of the total lot.
type Executor struct {
	bp      broker.Port
	journal *journal.Repository
	log     zerolog.Logger
}

// NewExecutor creates a take-profit executor.
func NewExecutor(bp broker.Port, journal *journal.Repository) *Executor {
	return &Executor{
		bp:      bp,
		journal: journal,
		log:     observability.Logger("takeprofit"),
	}
}

// Evaluate checks if any TP levels have been hit and executes partial
// closes accordingly. Returns the event type if a TP was hit, or empty.
func (e *Executor) Evaluate(ctx context.Context, trade *types.Trade, checkPrice float64) (constants.EventType, error) {
	trade.RLock()
	tp1Hit := trade.TP1Hit
	tp2Hit := trade.TP2Hit
	tp3Hit := trade.TP3Hit
	tp1Price := trade.TP1Price
	tp2Price := trade.TP2Price
	tp3Price := trade.TP3Price
	tp1Pct := trade.TP1Pct
	tp2Pct := trade.TP2Pct
	tp3Pct := trade.TP3Pct
	totalLot := trade.TotalLotSize
	remaining := trade.RemainingLotSize
	brokerID := trade.BrokerOrderID
	tradeID := trade.TradeID
	symbol := trade.Symbol
	entryPrice := trade.EntryPrice
	riskAmount := trade.RiskAmount
	userID := trade.UserID
	trade.RUnlock()

	// TP3 check first (runner close - full close of remaining).
	if !tp3Hit && tp2Hit && tp3Price > 0 && trade.IsTP3Hit(checkPrice) {
		return e.executeTP(ctx, trade, brokerID, tradeID, symbol, entryPrice, checkPrice, riskAmount, remaining, "TP3", constants.EventTP3Hit, tp3Pct, true, userID)
	}

	// TP2 check.
	if !tp2Hit && tp1Hit && tp2Price > 0 && trade.IsTP2Hit(checkPrice) {
		closeVol := totalLot * float64(tp2Pct) / 100.0
		if closeVol > remaining {
			closeVol = remaining
		}
		return e.executeTP(ctx, trade, brokerID, tradeID, symbol, entryPrice, checkPrice, riskAmount, closeVol, "TP2", constants.EventTP2Hit, tp2Pct, false, userID)
	}

	// TP1 check.
	if !tp1Hit && tp1Price > 0 && trade.IsTP1Hit(checkPrice) {
		closeVol := totalLot * float64(tp1Pct) / 100.0
		if closeVol > remaining {
			closeVol = remaining
		}
		return e.executeTP(ctx, trade, brokerID, tradeID, symbol, entryPrice, checkPrice, riskAmount, closeVol, "TP1", constants.EventTP1Hit, tp1Pct, false, userID)
	}

	return "", nil
}

func (e *Executor) executeTP(
	ctx context.Context,
	trade *types.Trade,
	brokerID, tradeID, symbol string,
	entryPrice, closePrice, riskAmount, closeVol float64,
	label string,
	eventType constants.EventType,
	tpPct int32,
	fullClose bool,
	userID string,
) (constants.EventType, error) {

	var err error
	if fullClose {
		err = e.bp.ClosePosition(ctx, brokerID)
	} else {
		err = e.bp.ClosePartial(ctx, brokerID, closeVol)
	}
	if err != nil {
		return "", fmt.Errorf("%s partial close: %w", label, err)
	}

	// Layer 1: Broker deal history (exact profit, commissions, swaps)
	pnl := 0.0
	pnlSource := "none"
	if brokerPnL, ok := e.pollClosedDealProfit(ctx, brokerID, symbol); ok {
		pnl = brokerPnL
		pnlSource = "broker_history"
	}

	// Calculate R-multiple and estimate fallback
	rMultiple := 0.0
	if riskAmount > 0 {
		slDist := trade.SLDistanceFromEntry()
		if slDist > 0 {
			priceDist := closePrice - entryPrice
			if !trade.IsLong() {
				priceDist = entryPrice - closePrice
			}
			rMultiple = priceDist / slDist
			
			// Layer 2: R-multiple estimate fallback
			if pnlSource == "none" {
				pnl = rMultiple * riskAmount * (closeVol / trade.TotalLotSize)
				pnlSource = "r_multiple"
			}
		}
	}

	// Update trade state.
	trade.Lock()
	switch eventType {
	case constants.EventTP1Hit:
		trade.TP1Hit = true
	case constants.EventTP2Hit:
		trade.TP2Hit = true
	case constants.EventTP3Hit:
		trade.TP3Hit = true
	}
	trade.RemainingLotSize -= closeVol
	trade.RealizedPnL += pnl
	trade.Partials++
	if trade.RemainingLotSize <= 0.001 {
		trade.RemainingLotSize = 0
		trade.Status = constants.StatusClosed
	}
	trade.Unlock()

	// Persist partial.
	if err := e.journal.UpdateTradePartial(ctx, userID, tradeID, pnl); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_partial_failed")
	}

	// Compute the REALIZED percentage from the actual closed volume
	// so the journal entry stays self-consistent with the lot amount
	// on the same row, even when the LLM-emitted tpPct values drift
	// (e.g. a 40/40/50=130 plan produces clamped closeVol on TP2/TP3).
	realizedPct := 0.0
	if trade.TotalLotSize > 0 {
		realizedPct = closeVol / trade.TotalLotSize * 100.0
	}

	if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
		UserID:       userID,
		TradeID:      tradeID,
		EventType:    string(eventType),
		Symbol:       symbol,
		Price:        closePrice,
		ClosedVolume: closeVol,
		RealizedPnL:  pnl,
		RMultiple:    rMultiple,
		Reason:       fmt.Sprintf("%s hit at %.5f — closed %.2f lots (%.1f%% realized, %d%% intended)", label, closePrice, closeVol, realizedPct, tpPct),
		Timestamp:    time.Now().UTC(),
	}); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_event_failed")
	}

	observability.PartialCloseTotal.WithLabelValues(symbol, label).Inc()

	e.log.Info().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Str("tp_level", label).
		Float64("close_price", closePrice).
		Float64("volume_closed", closeVol).
		Float64("pnl", pnl).
		Float64("r_multiple", rMultiple).
		Str("pnl_source", pnlSource).
		Msg("tp_partial_close_executed")

	return eventType, nil
}

// pollClosedDealProfit polls the broker deal history until the closed
// deal for brokerOrderID is found or the deadline is reached.
func (e *Executor) pollClosedDealProfit(ctx context.Context, brokerOrderID, symbol string) (float64, bool) {
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
		if pnl, ok := e.fetchClosedDealProfit(ctx, brokerOrderID, symbol); ok {
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
// Searches backward to find the MOST RECENT close deal matching this position.
// This is critical because a position might have multiple partial
// closes (multiple OUT deals). By searching backward, we grab the
// one that was just executed.
func (e *Executor) fetchClosedDealProfit(ctx context.Context, brokerOrderID, symbol string) (float64, bool) {
	if brokerOrderID == "" {
		return 0, false
	}

	history, err := e.bp.GetHistory(ctx, 1) // last 1 day of deals
	if err != nil {
		e.log.Warn().Err(err).
			Str("broker_order_id", brokerOrderID).
			Msg("broker_history_fetch_failed_for_pnl")
		return 0, false
	}

	for i := len(history) - 1; i >= 0; i-- {
		deal := history[i]
		if deal.PositionID == brokerOrderID || deal.Ticket == brokerOrderID {
			if deal.Symbol != "" && deal.Symbol != symbol {
				continue // Different symbol, not our deal
			}
			totalProfit := deal.Profit + deal.Commission + deal.Swap
			e.log.Info().
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

	e.log.Warn().
		Str("broker_order_id", brokerOrderID).
		Str("symbol", symbol).
		Int("history_deals_checked", len(history)).
		Msg("broker_deal_not_found_in_history")
	return 0, false
}
