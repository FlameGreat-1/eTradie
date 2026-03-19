package takeprofit

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/management/internal/broker"
	"github.com/flamegreat/etradie/src/management/internal/constants"
	"github.com/flamegreat/etradie/src/management/internal/journal"
	"github.com/flamegreat/etradie/src/management/internal/observability"
	"github.com/flamegreat/etradie/src/management/pkg/types"
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
	trade.RUnlock()

	// TP3 check first (runner close - full close of remaining).
	if !tp3Hit && tp2Hit && tp3Price > 0 && trade.IsTP3Hit(checkPrice) {
		return e.executeTP(ctx, trade, brokerID, tradeID, symbol, entryPrice, checkPrice, riskAmount, remaining, "TP3", constants.EventTP3Hit, tp3Pct, true)
	}

	// TP2 check.
	if !tp2Hit && tp1Hit && tp2Price > 0 && trade.IsTP2Hit(checkPrice) {
		closeVol := totalLot * float64(tp2Pct) / 100.0
		if closeVol > remaining {
			closeVol = remaining
		}
		return e.executeTP(ctx, trade, brokerID, tradeID, symbol, entryPrice, checkPrice, riskAmount, closeVol, "TP2", constants.EventTP2Hit, tp2Pct, false)
	}

	// TP1 check.
	if !tp1Hit && tp1Price > 0 && trade.IsTP1Hit(checkPrice) {
		closeVol := totalLot * float64(tp1Pct) / 100.0
		if closeVol > remaining {
			closeVol = remaining
		}
		return e.executeTP(ctx, trade, brokerID, tradeID, symbol, entryPrice, checkPrice, riskAmount, closeVol, "TP1", constants.EventTP1Hit, tp1Pct, false)
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

	// Estimate realized P&L for this partial.
	// For a BUY: pnl = (closePrice - entryPrice) * closeVol * pipValue
	// Since we don't have exact pip value here, we use a proportional
	// estimate based on the risk_amount and the R-multiple.
	// actual_pnl will be reconciled from the broker in the journal.
	pnlEstimate := 0.0
	rMultiple := 0.0
	if riskAmount > 0 {
		slDist := trade.SLDistanceFromEntry()
		if slDist > 0 {
			priceDist := closePrice - entryPrice
			if !trade.IsLong() {
				priceDist = entryPrice - closePrice
			}
			rMultiple = priceDist / slDist
			// Scale by the partial's proportion of total risk.
			pnlEstimate = rMultiple * riskAmount * (closeVol / trade.TotalLotSize)
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
	trade.RealizedPnL += pnlEstimate
	trade.Partials++
	if trade.RemainingLotSize <= 0.001 {
		trade.RemainingLotSize = 0
		trade.Status = constants.StatusClosed
	}
	trade.Unlock()

	// Persist partial.
	if err := e.journal.UpdateTradePartial(ctx, tradeID, pnlEstimate); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_partial_failed")
	}

	if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
		TradeID:      tradeID,
		EventType:    string(eventType),
		Symbol:       symbol,
		Price:        closePrice,
		ClosedVolume: closeVol,
		RealizedPnL:  pnlEstimate,
		RMultiple:    rMultiple,
		Reason:       fmt.Sprintf("%s hit at %.5f — closed %.2f lots (%d%%)", label, closePrice, closeVol, tpPct),
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
		Float64("pnl_estimate", pnlEstimate).
		Float64("r_multiple", rMultiple).
		Msg("tp_partial_close_executed")

	return eventType, nil
}
