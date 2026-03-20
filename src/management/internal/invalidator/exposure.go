package invalidator

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/alert"
	alertredis "github.com/flamegreat/etradie/src/alert/redis"
	"github.com/flamegreat/etradie/src/management/internal/broker"
	"github.com/flamegreat/etradie/src/management/internal/constants"
	"github.com/flamegreat/etradie/src/management/internal/journal"
	"github.com/flamegreat/etradie/src/management/internal/observability"
	"github.com/flamegreat/etradie/src/management/pkg/types"
)

// ExposureEngine handles correlation shock protection.
// If an active trade completely hits its stop loss, this engine instantly
// sweeps other open, correlated trades and tightens their risk by 50%
// to mathematically limit a cascading sequential account drawdown.
type ExposureEngine struct {
	bp        broker.Port
	journal   *journal.Repository
	transport *alertredis.Transport
	rdb       *redis.Client
	log       zerolog.Logger
}

// NewExposureEngine creates an exposure invalidation engine.
func NewExposureEngine(bp broker.Port, journal *journal.Repository, transport *alertredis.Transport, rdb *redis.Client) *ExposureEngine {
	return &ExposureEngine{
		bp:        bp,
		journal:   journal,
		transport: transport,
		rdb:       rdb,
		log:       observability.Logger("invalidator_exposure"),
	}
}

// EvaluateCorrelationShock evaluates an active trade to see if it needs
// protective tightening after a correlated twin trade was stopped out.
func (e *ExposureEngine) EvaluateCorrelationShock(ctx context.Context, trade *types.Trade, stoppedSymbol string, currentPrice float64) (bool, error) {
	trade.RLock()
	tradeID := trade.TradeID
	brokerID := trade.BrokerOrderID
	symbol := trade.Symbol
	currentSL := trade.StopLoss
	isLong := trade.IsLong()
	status := trade.Status
	trade.RUnlock()

	if status == constants.StatusClosed {
		return false, nil
	}
	if symbol == stoppedSymbol {
		return false, nil // don't evaluate the trade that just stopped out
	}

	isCorrelated := false

	// Dynamically load Enterprise correlation config from Redis
	// Example payload: {"groups": {"USD_QUOTE": ["EURUSD", "GBPUSD"], "USD_BASE": ["USDJPY"]}}
	const correlationKey = "etradie:correlation:config"
	if e.rdb != nil {
		rawConfig, err := e.rdb.Get(ctx, correlationKey).Result()
		if err == nil && rawConfig != "" {
			var config struct {
				Groups map[string][]string `json:"groups"`
			}
			if err := json.Unmarshal([]byte(rawConfig), &config); err == nil {
				// Search matrix for both symbols
				for _, pairs := range config.Groups {
					hasSymbol := false
					hasStopped := false
					for _, p := range pairs {
						if p == symbol {
							hasSymbol = true
						}
						if p == stoppedSymbol {
							hasStopped = true
						}
					}
					if hasSymbol && hasStopped {
						isCorrelated = true
						break
					}
				}
			} else {
				e.log.Error().Err(err).Msg("failed_to_parse_redis_correlation_matrix")
			}
		} else if err != redis.Nil {
			e.log.Error().Err(err).Msg("failed_to_fetch_correlation_config")
		}
	}

	if !isCorrelated {
		return false, nil
	}

	// Protective Action: tighten current stop loss by 50% of the distance to price.
	distToSL := currentPrice - currentSL
	if !isLong {
		distToSL = currentSL - currentPrice
	}

	halfDist := distToSL * 0.50
	var newSL float64
	if isLong {
		newSL = currentPrice - halfDist
	} else {
		newSL = currentPrice + halfDist
	}

	// Guarantee tightening ONLY.
	shouldTighten := false
	if isLong && newSL > currentSL {
		shouldTighten = true
	} else if !isLong && newSL < currentSL {
		shouldTighten = true
	}

	if !shouldTighten {
		return false, nil
	}

	if err := e.bp.ModifyPosition(ctx, brokerID, newSL, 0); err != nil {
		return false, fmt.Errorf("correlation shock SL mod: %w", err)
	}

	trade.Lock()
	trade.StopLoss = newSL
	trade.SLMoves++
	trade.Unlock()

	reason := fmt.Sprintf("Correlation shock protection: %s hits SL — tightening %s by 50%%", stoppedSymbol, symbol)

	if err := e.journal.UpdateTradeSL(ctx, tradeID, newSL); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_sl_update_failed")
	}
	if err := e.journal.InsertEvent(ctx, &journal.TradeEvent{
		TradeID:   tradeID,
		EventType: string(constants.EventCorrelationProtection),
		Symbol:    symbol,
		Price:     currentPrice,
		NewSL:     newSL,
		Reason:    reason,
		Timestamp: time.Now().UTC(),
	}); err != nil {
		e.log.Error().Err(err).Str("trade_id", tradeID).Msg("journal_event_failed")
	}

	observability.InvalidationTotal.WithLabelValues(symbol, "CORRELATION_PROTECT").Inc()

	if e.transport != nil {
		e.transport.Publish(ctx,
			alert.NewEvent(alert.SourceTradeManager, alert.TypeTrailingSLMoved, alert.SeverityWarning, reason).
				WithSymbol(symbol).
				WithDetails(map[string]interface{}{
					"trade_id":      tradeID,
					"new_sl":        newSL,
					"trigger_event": stoppedSymbol + " stopped out",
				}),
		)
	}

	e.log.Info().
		Str("trade_id", tradeID).
		Str("symbol", symbol).
		Str("stopped_symbol", stoppedSymbol).
		Float64("new_sl", newSL).
		Msg("correlation_shock_protection_executed")

	return true, nil
}
