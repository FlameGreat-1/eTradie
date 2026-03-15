package validator

import (
	"context"
	"fmt"
	"time"

	"github.com/flamegreat/etradie/src/execution/internal/broker"
	"github.com/flamegreat/etradie/src/execution/internal/config"
	"github.com/flamegreat/etradie/src/execution/internal/constants"
	"github.com/flamegreat/etradie/src/execution/internal/models"
	"github.com/flamegreat/etradie/src/execution/internal/state"
)

func check4NewsLockout(_ *models.TradeRequest, _ *config.Config, _ *state.Manager, _ broker.Port) models.ValidationResult {
	// Gateway guard MR-REJECT-001 already evaluated news proximity
	// during analysis. Execution happens within seconds of guard pass.
	// Module B trusts the gateway's evaluation.
	return pass()
}

func check5SessionFilter(_ *models.TradeRequest, cfg *config.Config, _ *state.Manager, _ broker.Port) models.ValidationResult {
	now := time.Now().UTC()
	hour := now.Hour()

	var currentSession string
	for _, s := range constants.Sessions {
		if hour >= s.StartHour && hour < s.EndHour {
			currentSession = s.Name
			break
		}
	}

	if currentSession == "" {
		return pass()
	}

	if !cfg.IsSessionEnabled(currentSession) {
		return reject(
			constants.CheckSessionFilter,
			fmt.Sprintf("session %s is disabled (hour %d UTC)", currentSession, hour),
		)
	}

	return pass()
}

func check6SamePairPosition(req *models.TradeRequest, _ *config.Config, sm *state.Manager, _ broker.Port) models.ValidationResult {
	if sm.HasPositionOnPair(req.Symbol) {
		return reject(
			constants.CheckSamePairPosition,
			fmt.Sprintf("existing position or pending order on %s", req.Symbol),
		)
	}
	return pass()
}

func check7CorrelatedExposure(req *models.TradeRequest, _ *config.Config, sm *state.Manager, _ broker.Port) models.ValidationResult {
	if sm.HasCorrelatedExposure(req.Symbol) {
		return reject(
			constants.CheckCorrelatedExposure,
			fmt.Sprintf("correlated pair exposure: position exists in same group as %s", req.Symbol),
		)
	}
	return pass()
}

func check8MaxConcurrentTrades(_ *models.TradeRequest, cfg *config.Config, sm *state.Manager, _ broker.Port) models.ValidationResult {
	count := sm.OpenPositionCount()
	if count >= cfg.MaxConcurrentTrades {
		return queue(
			constants.CheckMaxConcurrentTrades,
			fmt.Sprintf("at max concurrent trades: %d/%d", count, cfg.MaxConcurrentTrades),
		)
	}
	return pass()
}

func check9DailyLossLimit(_ *models.TradeRequest, cfg *config.Config, sm *state.Manager, _ broker.Port) models.ValidationResult {
	loss := sm.DailyLossPercent()
	if loss >= cfg.DailyLossLimitPct {
		return lock(
			constants.CheckDailyLossLimit,
			fmt.Sprintf("daily loss %.2f%% exceeds limit %.2f%%", loss, cfg.DailyLossLimitPct),
		)
	}
	return pass()
}

func check10WeeklyDrawdown(_ *models.TradeRequest, cfg *config.Config, sm *state.Manager, _ broker.Port) models.ValidationResult {
	dd := sm.WeeklyDrawdownPercent()
	if dd >= cfg.WeeklyDrawdownPct {
		return pause(
			constants.CheckWeeklyDrawdown,
			fmt.Sprintf("weekly drawdown %.2f%% exceeds limit %.2f%%", dd, cfg.WeeklyDrawdownPct),
		)
	}
	return pass()
}

func check11Spread(req *models.TradeRequest, cfg *config.Config, _ *state.Manager, bp broker.Port) models.ValidationResult {
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(cfg.BrokerTimeoutMs)*time.Millisecond)
	defer cancel()

	info, err := bp.GetInstrumentInfo(ctx, req.Symbol)
	if err != nil {
		return reject(
			constants.CheckSpread,
			fmt.Sprintf("failed to get instrument info for %s: %v", req.Symbol, err),
		)
	}

	if info.AvgSpread <= 0 {
		return pass()
	}

	multiplier := cfg.SpreadMultiplierNormal
	if req.TradingStyle == constants.StyleScalping {
		multiplier = cfg.SpreadMultiplierScalping
	}

	threshold := info.AvgSpread * multiplier
	if info.Spread > threshold {
		return reject(
			constants.CheckSpread,
			fmt.Sprintf("spread %.5f exceeds %.1fx average (threshold %.5f) for %s",
				info.Spread, multiplier, threshold, req.Symbol),
		)
	}

	return pass()
}

func check12MinRR(req *models.TradeRequest, _ *config.Config, _ *state.Manager, _ broker.Port) models.ValidationResult {
	minRR, ok := constants.MinRRByStyle[req.TradingStyle]
	if !ok {
		minRR = constants.MinRRByStyle[constants.StyleIntraday]
	}

	if req.RRRatio < minRR {
		return reject(
			constants.CheckMinRR,
			fmt.Sprintf("R:R %.2f below minimum %.2f for %s", req.RRRatio, minRR, req.TradingStyle),
		)
	}

	return pass()
}

func check13WeekendDayFilter(req *models.TradeRequest, _ *config.Config, _ *state.Manager, _ broker.Port) models.ValidationResult {
	now := time.Now().UTC()
	weekday := now.Weekday()
	hour := now.Hour()

	if weekday == time.Saturday || weekday == time.Sunday {
		return reject(
			constants.CheckWeekendDayFilter,
			fmt.Sprintf("no entries on %s", weekday),
		)
	}

	if weekday == time.Monday && hour < constants.MondayNoEntryBeforeHour {
		return reject(
			constants.CheckWeekendDayFilter,
			fmt.Sprintf("Monday before %d:00 UTC - gap risk", constants.MondayNoEntryBeforeHour),
		)
	}

	if weekday == time.Friday {
		cutoff, ok := constants.FridayCutoffHourByStyle[req.TradingStyle]
		if ok && hour >= cutoff {
			return reject(
				constants.CheckWeekendDayFilter,
				fmt.Sprintf("Friday after %d:00 UTC for %s style", cutoff, req.TradingStyle),
			)
		}
	}

	return pass()
}
