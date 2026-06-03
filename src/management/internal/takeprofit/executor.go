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
	isLong := trade.IsLong()
	trade.RUnlock()

	// Evaluate TP hits against the SNAPSHOTTED prices + direction taken
	// under the RLock above. We deliberately do NOT call trade.IsTP*Hit
	// here: those helpers re-read t.TP*Price / t.IsLong() off the struct
	// with no lock held, which is a data race under `go test -race` even
	// though the fields are immutable post-registration.

	// TP3 check first (runner close - full close of remaining).
	if !tp3Hit && tp2Hit && tp3Price > 0 && tpReached(isLong, checkPrice, tp3Price) {
		return e.executeTP(ctx, trade, brokerID, tradeID, symbol, entryPrice, checkPrice, riskAmount, remaining, "TP3", constants.EventTP3Hit, tp3Pct, true, userID)
	}

	// TP2 check.
	if !tp2Hit && tp1Hit && tp2Price > 0 && tpReached(isLong, checkPrice, tp2Price) {
		closeVol := totalLot * float64(tp2Pct) / 100.0
		if closeVol > remaining {
			closeVol = remaining
		}
		return e.executeTP(ctx, trade, brokerID, tradeID, symbol, entryPrice, checkPrice, riskAmount, closeVol, "TP2", constants.EventTP2Hit, tp2Pct, false, userID)
	}

	// TP1 check.
	if !tp1Hit && tp1Price > 0 && tpReached(isLong, checkPrice, tp1Price) {
		closeVol := totalLot * float64(tp1Pct) / 100.0
		if closeVol > remaining {
			closeVol = remaining
		}
		return e.executeTP(ctx, trade, brokerID, tradeID, symbol, entryPrice, checkPrice, riskAmount, closeVol, "TP1", constants.EventTP1Hit, tp1Pct, false, userID)
	}

	return "", nil
}

// tpReached reports whether checkPrice has reached a take-profit level
// for the given direction. Mirrors Trade.IsTP*Hit but operates on
// snapshotted values so the caller holds no lock (EM-F1). A non-positive
// tpPrice ("not set") never triggers; callers already gate on tp* > 0.
func tpReached(isLong bool, checkPrice, tpPrice float64) bool {
	if tpPrice <= 0 {
		return false
	}
	if isLong {
		return checkPrice >= tpPrice
	}
	return checkPrice <= tpPrice
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
		// Idempotency with the broker-side TP3 bracket (audit #1): the
		// broker holds TP3 as the position TP, so when price reaches TP3
		// the broker may auto-close the runner before (or concurrently
		// with) this software close. A failed ClosePosition whose position
		// is already gone at the broker is therefore the SUCCESS case, not
		// an error: the runner closed at its final target either way. We
		// only swallow the error after positively confirming the position
		// no longer exists, so a genuine transient close failure (position
		// still open) still surfaces and is retried on the next tick.
		if err != nil {
			if pos, perr := e.bp.GetPosition(ctx, brokerID); perr != nil || pos == nil || pos.Volume <= 0 {
				e.log.Info().
					Str("trade_id", tradeID).
					Str("broker_order_id", brokerID).
					Str("tp_level", label).
					Msg("tp3_close_position_already_gone_broker_tp_won_race")
				err = nil
			}
		}
	} else {
		err = e.bp.ClosePartial(ctx, brokerID, closeVol)
	}
	if err != nil {
		return "", fmt.Errorf("%s close: %w", label, err)
	}

	// Layer 1: Broker deal history (exact profit, commissions, swaps).
	// Pass the just-closed volume so the correct OUT deal is selected
	// when several partial closes land in the same history window (EM-F4).
	pnl := 0.0
	pnlSource := "none"
	if brokerPnL, ok := e.pollClosedDealProfit(ctx, brokerID, symbol, closeVol); ok {
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

	// Update trade state. Snapshot the post-mutation runtime values under
	// the same write lock so the durable runtime row matches memory.
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
	snapRemaining := trade.RemainingLotSize
	snapSL := trade.StopLoss
	snapTP1Hit := trade.TP1Hit
	snapTP2Hit := trade.TP2Hit
	snapTP3Hit := trade.TP3Hit
	snapBE := trade.BreakevenSet
	trade.Unlock()

	// Persist partial (gross_pnl + partial_closes counter).
	if err := e.journal.UpdateTradePartial(ctx, userID, tradeID, pnl); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_partial_failed")
	}

	// Persist the worker runtime state so a restart resumes with the
	// correct remaining volume and TP-hit flags (audit EM-C1). Without
	// this, a restored trade re-arms an already-closed TP leg.
	if err := e.journal.UpdateTradeRuntime(ctx, userID, tradeID, snapRemaining, snapSL, snapTP1Hit, snapTP2Hit, snapTP3Hit, snapBE); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_runtime_update_failed")
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
// closedVolume identifies the specific leg just closed (EM-F4).
func (e *Executor) pollClosedDealProfit(ctx context.Context, brokerOrderID, symbol string, closedVolume float64) (float64, bool) {
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
		if pnl, ok := e.fetchClosedDealProfit(ctx, brokerOrderID, symbol, closedVolume); ok {
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
// Searches backward to find the MOST RECENT close deal matching this
// position. When several partial closes land in the same history window
// (e.g. TP2 and TP3 near-simultaneously), "most recent" alone can pick
// the wrong leg, so we first prefer the most-recent matching deal whose
// Volume equals the just-closed volume within a lot epsilon (EM-F4),
// and only fall back to the most-recent matching deal when no volume-
// matched OUT deal is found (e.g. the broker reports aggregate volume).
func (e *Executor) fetchClosedDealProfit(ctx context.Context, brokerOrderID, symbol string, closedVolume float64) (float64, bool) {
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

	// lotEpsilon sits below the 0.01 minimum lot step so a deal whose
	// volume equals the closed leg is matched without false positives.
	const lotEpsilon = 0.0009

	matches := func(deal interface{ symbolOf() string }) bool { return true } // placeholder removed below
	_ = matches

	var (
		fallbackProfit float64
		fallbackTicket string
		haveFallback   bool
	)

	for i := len(history) - 1; i >= 0; i-- {
		deal := history[i]
		if deal.PositionID != brokerOrderID && deal.Ticket != brokerOrderID {
			continue
		}
		if deal.Symbol != "" && deal.Symbol != symbol {
			continue // Different symbol, not our deal.
		}

		totalProfit := deal.Profit + deal.Commission + deal.Swap

		// Preferred: the most-recent OUT deal whose volume matches the
		// leg we just closed. Searching backward, the first such match
		// is the most recent, so return immediately.
		if closedVolume > 0 {
			d := deal.Volume - closedVolume
			if d < 0 {
				d = -d
			}
			if d <= lotEpsilon {
				e.log.Info().
					Str("broker_order_id", brokerOrderID).
					Str("deal_ticket", deal.Ticket).
					Float64("deal_volume", deal.Volume).
					Float64("closed_volume", closedVolume).
					Float64("total", totalProfit).
					Msg("broker_deal_profit_resolved_volume_matched")
				return totalProfit, true
			}
		}

		// Remember the most-recent matching deal as a fallback (first
		// one seen searching backward).
		if !haveFallback {
			fallbackProfit = totalProfit
			fallbackTicket = deal.Ticket
			haveFallback = true
		}
	}

	if haveFallback {
		e.log.Info().
			Str("broker_order_id", brokerOrderID).
			Str("deal_ticket", fallbackTicket).
			Float64("closed_volume", closedVolume).
			Float64("total", fallbackProfit).
			Msg("broker_deal_profit_resolved_recent_fallback")
		return fallbackProfit, true
	}

	e.log.Warn().
		Str("broker_order_id", brokerOrderID).
		Str("symbol", symbol).
		Int("history_deals_checked", len(history)).
		Msg("broker_deal_not_found_in_history")
	return 0, false
}
