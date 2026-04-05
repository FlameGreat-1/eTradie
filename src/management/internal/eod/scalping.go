package eod

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog"

	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

type Scalping struct {
	bp        broker.Port
	journal   *journal.Repository
	transport *alertredis.Transport
	log       zerolog.Logger
}

func NewScalping(bp broker.Port, journal *journal.Repository, transport *alertredis.Transport) *Scalping {
	return &Scalping{
		bp:        bp,
		journal:   journal,
		transport: transport,
		log:       observability.Logger("eod_scalping"),
	}
}

func (p *Scalping) Evaluate(ctx context.Context, trade *types.Trade, currentPrice float64) (bool, error) {
	trade.RLock()
	style := trade.TradingStyle
	openedAt := trade.OpenedAt
	brokerID := trade.BrokerOrderID
	symbol := trade.Symbol
	status := trade.Status
	entryPrice := trade.EntryPrice
	riskAmount := trade.RiskAmount
	isLong := trade.IsLong()
	userID := trade.UserID
	trade.RUnlock()

	if status == constants.StatusClosed || style != constants.StyleScalping {
		return false, nil
	}

	now := time.Now().UTC()
	elapsed := now.Sub(openedAt)

	// 2-hour hard limit from entry.
	if elapsed >= time.Duration(constants.ScalpMaxDurationMinutes)*time.Minute {
		reason := fmt.Sprintf("Scalping time limit: %d minutes elapsed (max %d)", int(elapsed.Minutes()), constants.ScalpMaxDurationMinutes)

		if err := p.bp.ClosePosition(ctx, brokerID); err != nil {
			return false, fmt.Errorf("scalping close: %w", err)
		}

		return executeClosure(ctx, p.journal, p.transport, p.log, trade, userID, currentPrice, entryPrice, riskAmount, isLong, reason, now, symbol, style)
	}

	return false, nil
}
