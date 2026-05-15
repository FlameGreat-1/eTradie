package invalidator

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// NewsEngine executes the deterministic risk-off protocol before
// high-impact macro news events. If a Tier-1 event is scheduled within
// the 5-15 minute pre-news window, it aggressively moves SL to breakeven
// (if in profit) or cuts risk by 50% (if in loss) to protect against
// catastrophic slippage during the news spike.
type NewsEngine struct {
	bp        broker.Port
	journal   *journal.Repository
	transport *alertredis.Transport
	rdb       *redis.Client
	log       zerolog.Logger
}

// NewNewsEngine creates a pre-news protection engine.
func NewNewsEngine(bp broker.Port, journal *journal.Repository, transport *alertredis.Transport, rdb *redis.Client) *NewsEngine {
	return &NewsEngine{
		bp:        bp,
		journal:   journal,
		transport: transport,
		rdb:       rdb,
		log:       observability.Logger("invalidator_news"),
	}
}

// StartPolling initiates a 1-minute background loop that natively checks Redis for upcoming news.
func (e *NewsEngine) StartPolling(ctx context.Context, getTrades func() []*types.Trade, getPrice func(context.Context, string) (float64, error)) {
	ticker := time.NewTicker(1 * time.Minute)
	e.log.Info().Msg("news_polling_engine_started")

	go func() {
		for {
			select {
			case <-ctx.Done():
				ticker.Stop()
				e.log.Info().Msg("news_polling_engine_stopped")
				return
			case <-ticker.C:
				e.pollCalendar(ctx, getTrades, getPrice)
			}
		}
	}()
}

func (e *NewsEngine) pollCalendar(ctx context.Context, getTrades func() []*types.Trade, getPrice func(context.Context, string) (float64, error)) {
	if e.rdb == nil {
		return
	}

	rawJSON, err := e.rdb.Get(ctx, "etradie:calendar:latest").Result()
	if err != nil {
		if err != redis.Nil {
			e.log.Error().Err(err).Msg("failed_to_fetch_calendar_cache")
		}
		return
	}

	var dataset struct {
		Events []struct {
			EventName string    `json:"event_name"`
			Impact    string    `json:"impact"`
			EventTime time.Time `json:"event_time"`
		} `json:"events"`
	}

	if err := json.Unmarshal([]byte(rawJSON), &dataset); err != nil {
		e.log.Error().Err(err).Msg("failed_to_parse_calendar_cache")
		return
	}

	now := time.Now().UTC()
	for _, evt := range dataset.Events {
		if evt.Impact == "HIGH" && evt.EventTime.After(now) {
			timeToEvent := evt.EventTime.Sub(now)

			// Fast threshold check: Is it between 4 and 16 minutes from dropping?
			if timeToEvent >= 4*time.Minute && timeToEvent <= 16*time.Minute {
				trades := getTrades()
				for _, t := range trades {
					// Snapshot status + build identity-bearing ctx in one
					// RLock window so concurrent token / identity
					// refreshes do not race against this read. Without the
					// lock the previous code raced with
					// RefreshUserTradeIdentity, and any reader of t.* was
					// formally undefined.
					t.RLock()
					isActive := t.Status == constants.StatusActive
					var tradeCtx context.Context
					if isActive {
						tradeCtx = t.IdentityCtx(ctx)
					}
					symbol := t.Symbol
					t.RUnlock()

					if !isActive {
						continue
					}
					price, err := getPrice(tradeCtx, symbol)
					if err == nil {
						e.EvaluatePreNewsRiskOff(tradeCtx, t, evt.EventName, timeToEvent, price)
					}
				}
			}
		}
	}
}

// EvaluatePreNewsRiskOff checks if a trade needs protection before a news event.
// timeToEvent is the duration until the high-impact event drops.
func (e *NewsEngine) EvaluatePreNewsRiskOff(ctx context.Context, trade *types.Trade, eventName string, timeToEvent time.Duration, currentPrice float64) (bool, error) {
	trade.RLock()
	tradeID := trade.TradeID
	brokerID := trade.BrokerOrderID
	symbol := trade.Symbol
	style := trade.TradingStyle
	entryPrice := trade.EntryPrice
	currentSL := trade.StopLoss
	isLong := trade.IsLong()
	status := trade.Status
	userID := trade.UserID
	trade.RUnlock()

	if status == constants.StatusClosed {
		return false, nil
	}

	// Only active Intraday and Scalping trades are aggressively managed before news.
	// Swing and Positional trades usually have stops wide enough to absorb spikes.
	if style != constants.StyleScalping && style != constants.StyleIntraday {
		return false, nil
	}

	// We only act if the event is strictly within the 5 to 15-minute protection window.
	// We use 16m and 4m as fuzzy bounds to handle polling jitter.
	if timeToEvent > 16*time.Minute || timeToEvent < 4*time.Minute {
		return false, nil
	}

	// Determine if the trade is currently in profit or loss.
	var priceDiff float64
	if isLong {
		priceDiff = currentPrice - entryPrice
	} else {
		priceDiff = entryPrice - currentPrice
	}

	inProfit := priceDiff > 0
	var newSL float64
	reason := ""

	if inProfit {
		// Move to Break-Even + Spread Buffer to lock in a risk-free state.
		bufferSize := constants.SpreadBufferPips * 0.0001
		if isLong {
			newSL = entryPrice + bufferSize
		} else {
			newSL = entryPrice - bufferSize
		}
		reason = fmt.Sprintf("Pre-News risk-off (%s in %dm) — securing Break-Even", eventName, int(timeToEvent.Minutes()))
	} else {
		// Cut prevailing risk by 50% by tightening the SL closer to current price.
		// Original risk distance = dist(entry, currentSL)
		// We want to halve the distance from current price to the SL.
		distToSL := currentPrice - currentSL
		if !isLong {
			distToSL = currentSL - currentPrice
		}

		halfDist := distToSL * 0.50
		if isLong {
			newSL = currentPrice - halfDist
		} else {
			newSL = currentPrice + halfDist
		}
		reason = fmt.Sprintf("Pre-News risk-off (%s in %dm) — halving risk exposure", eventName, int(timeToEvent.Minutes()))
	}

	// Enforce tightening only (never artificially widen a stop loss).
	shouldTighten := false
	if isLong && newSL > currentSL {
		shouldTighten = true
	} else if !isLong && newSL < currentSL {
		shouldTighten = true
	}

	if !shouldTighten {
		return false, nil
	}

	// Execute broker modification.
	if err := e.bp.ModifyPosition(ctx, brokerID, newSL, 0); err != nil {
		return false, fmt.Errorf("news risk-off SL mod: %w", err)
	}

	trade.Lock()
	trade.StopLoss = newSL
	trade.SLMoves++
	trade.Unlock()

	// Persist changes.
	if e.journal != nil {
		if err := e.journal.UpdateTradeSL(ctx, userID, tradeID, newSL); err != nil {
			e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_sl_update_failed")
		}
	}
	if e.journal != nil {
		if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
			UserID:    userID,
			TradeID:   tradeID,
			EventType: string(constants.EventNewsProtection),
			Symbol:    symbol,
			Price:     currentPrice,
			NewSL:     newSL,
			Reason:    reason,
			Timestamp: time.Now().UTC(),
		}); err != nil {
			e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_event_failed")
		}
	}

	observability.InvalidationTotal.WithLabelValues(symbol, "NEWS_PROTECT").Inc()

	if e.transport != nil {
		e.transport.Publish(ctx,
			alert.NewEvent(alert.SourceTradeManager, alert.TypeTrailingSLMoved, alert.SeverityWarning, reason).
				WithSymbol(symbol).
				WithDetails(map[string]interface{}{
					"trade_id": tradeID,
					"new_sl":   newSL,
				}),
		)
	}

	e.log.Info().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Str("event_name", eventName).
		Float64("new_sl", newSL).
		Msg("pre_news_risk_off_executed")

	return true, nil
}
