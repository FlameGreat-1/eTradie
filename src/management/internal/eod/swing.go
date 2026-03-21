package eod

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
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
)

type Swing struct {
	bp        broker.Port
	journal   *journal.Repository
	transport *alertredis.Transport
	log       zerolog.Logger
}

func NewSwing(bp broker.Port, journal *journal.Repository, transport *alertredis.Transport) *Swing {
	return &Swing{
		bp:        bp,
		journal:   journal,
		transport: transport,
		log:       observability.Logger("eod_swing"),
	}
}

func (p *Swing) Evaluate(ctx context.Context, trade *types.Trade, currentPrice float64) (bool, error) {
	trade.RLock()
	style := trade.TradingStyle
	brokerID := trade.BrokerOrderID
	symbol := trade.Symbol
	status := trade.Status
	entryPrice := trade.EntryPrice
	riskAmount := trade.RiskAmount
	isLong := trade.IsLong()
	trade.RUnlock()

	if status == constants.StatusClosed || style != constants.StyleSwing {
		return false, nil
	}

	now := time.Now().UTC()

	// Friday 16:00 UTC: evaluate weekend carry risk.
	if now.Weekday() == time.Weekday(constants.SwingWeekendDay) {
		if now.Hour() >= constants.SwingWeekendHour {
			
			// Close if not in sufficient profit to justify weekend risk.
			slDist := trade.SLDistanceFromEntry()
			var priceDist float64
			if isLong {
				priceDist = currentPrice - entryPrice
			} else {
				priceDist = entryPrice - currentPrice
			}
			
			if slDist > 0 {
				currentR := priceDist / slDist
				if currentR < 1.0 { // Rule: close if unrealized P&L < 1R.
					reason := fmt.Sprintf("Weekend carry risk: trade at %.2fR, below 1R threshold for Friday hold", currentR)
					
					if err := p.bp.ClosePosition(ctx, brokerID); err != nil {
						return false, fmt.Errorf("swing weekend close: %w", err)
					}

					return executeClosure(ctx, p.journal, p.transport, p.log, trade, currentPrice, entryPrice, riskAmount, isLong, reason, now, symbol, style)
				}
			}
		}
	}

	return false, nil
}
