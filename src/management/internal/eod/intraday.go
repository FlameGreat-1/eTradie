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

type Intraday struct {
	bp        broker.Port
	journal   *journal.Repository
	transport *alertredis.Transport
	log       zerolog.Logger
}

func NewIntraday(bp broker.Port, journal *journal.Repository, transport *alertredis.Transport) *Intraday {
	return &Intraday{
		bp:        bp,
		journal:   journal,
		transport: transport,
		log:       observability.Logger("eod_intraday"),
	}
}

func (p *Intraday) Evaluate(ctx context.Context, trade *types.Trade, currentPrice float64) (bool, error) {
	trade.RLock()
	style := trade.TradingStyle
	brokerID := trade.BrokerOrderID
	symbol := trade.Symbol
	status := trade.Status
	entryPrice := trade.EntryPrice
	riskAmount := trade.RiskAmount
	isLong := trade.IsLong()
	trade.RUnlock()

	if status == constants.StatusClosed || style != constants.StyleIntraday {
		return false, nil
	}

	now := time.Now().UTC()

	// 16:30 UTC hard close. No overnight holds.
	if now.Hour() > constants.IntradayEODHour ||
		(now.Hour() == constants.IntradayEODHour && now.Minute() >= constants.IntradayEODMinute) {

		reason := fmt.Sprintf("Intraday EOD: %02d:%02d UTC closure enforced", constants.IntradayEODHour, constants.IntradayEODMinute)

		if err := p.bp.ClosePosition(ctx, brokerID); err != nil {
			return false, fmt.Errorf("intraday close: %w", err)
		}

		return executeClosure(ctx, p.journal, p.transport, p.log, trade, currentPrice, entryPrice, riskAmount, isLong, reason, now, symbol, style)
	}

	return false, nil
}
