package eod

import (
	"context"
	"sync"
	"time"

	"github.com/rs/zerolog"

	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/management/internal/broker"
	"github.com/flamegreat-1/etradie/src/management/internal/constants"
	"github.com/flamegreat-1/etradie/src/management/internal/journal"
	"github.com/flamegreat-1/etradie/src/management/internal/observability"
	"github.com/flamegreat-1/etradie/src/management/pkg/types"
)

// EvalFunc is a function that evaluates a trade for EOD closure.
type EvalFunc func(ctx context.Context, trade *types.Trade, currentPrice float64) (bool, error)

// Scheduler runs end-of-period checks at regular intervals for all
// active trades. It fires a goroutine that wakes up every minute to
// check if any temporal rules should trigger based on the trade style.
type Scheduler struct {
	intraday *Intraday
	scalping *Scalping
	swing    *Swing

	getTrades func() []*types.Trade
	getPrice  func(ctx context.Context, symbol string) (float64, error)
	interval  time.Duration
	cancel    context.CancelFunc
	wg        sync.WaitGroup
	log       zerolog.Logger
}

// NewScheduler creates an EOD scheduler with all style-specific evaluators.
func NewScheduler(
	bp broker.Port,
	journal *journal.Repository,
	transport *alertredis.Transport,
	getTrades func() []*types.Trade,
	getPrice func(ctx context.Context, symbol string) (float64, error),
) *Scheduler {
	return &Scheduler{
		intraday:  NewIntraday(bp, journal, transport),
		scalping:  NewScalping(bp, journal, transport),
		swing:     NewSwing(bp, journal, transport),
		getTrades: getTrades,
		getPrice:  getPrice,
		interval:  1 * time.Minute,
		log:       observability.Logger("eod_scheduler"),
	}
}

// Start begins the background EOD scheduling loop.
func (s *Scheduler) Start() {
	ctx, cancel := context.WithCancel(context.Background())
	s.cancel = cancel

	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		s.log.Info().Msg("eod_scheduler_started")

		ticker := time.NewTicker(s.interval)
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				s.log.Info().Msg("eod_scheduler_stopped")
				return
			case <-ticker.C:
				s.runChecks(ctx)
			}
		}
	}()
}

// Shutdown stops the scheduler and waits for completion.
func (s *Scheduler) Shutdown() {
	if s.cancel != nil {
		s.cancel()
	}
	s.wg.Wait()
}

func (s *Scheduler) runChecks(ctx context.Context) {
	trades := s.getTrades()
	if len(trades) == 0 {
		return
	}

	for _, trade := range trades {
		trade.RLock()
		style := trade.TradingStyle
		trade.RUnlock()

		price, err := s.getPrice(ctx, trade.Symbol)
		if err != nil {
			s.log.Error().Err(err).Str("symbol", trade.Symbol).Msg("eod_price_fetch_failed")
			continue
		}

		var closed bool
		switch style {
		case constants.StyleIntraday:
			closed, err = s.intraday.Evaluate(ctx, trade, price)
		case constants.StyleScalping:
			closed, err = s.scalping.Evaluate(ctx, trade, price)
		case constants.StyleSwing:
			closed, err = s.swing.Evaluate(ctx, trade, price)
		}

		if err != nil {
			s.log.Error().Err(err).Str("trade_id", trade.TradeID).Msg("eod_eval_failed")
			continue
		}
		if closed {
			s.log.Info().Str("trade_id", trade.TradeID).Msg("eod_trade_closed")
		}
	}
}
