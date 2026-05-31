package validator

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/flamegreat-1/etradie/src/execution/internal/broker"
	"github.com/flamegreat-1/etradie/src/execution/internal/config"
	"github.com/flamegreat-1/etradie/src/execution/internal/constants"
	"github.com/flamegreat-1/etradie/src/execution/internal/models"
	"github.com/flamegreat-1/etradie/src/execution/internal/state"
)

// check4NewsLockout intentionally passes: news protection is owned by
// the gateway, which holds the economic calendar (Module B has no
// calendar access). The protection is enforced at three points, so
// re-checking the same instant here would be redundant:
//
//  1. Decision time: gateway guard MR-REJECT-001 (checkHighImpact-
//     EventProximity) rejects an entry whose currencies face a HIGH-
//     impact event within the lockout window, and fails closed when
//     calendar data is missing. A trade only reaches Execution after
//     passing this gate.
//  2. INSTANT fire time: the watcher's ConfirmSetup call re-runs the
//     gateway news evaluation before every market-order fire, so an
//     INSTANT order never fires into news no matter how long the
//     watcher polled.
//  3. LIMIT lifetime: the watcher's TTL loop calls the gateway
//     CheckNewsWindow RPC each tick and cancels the resting limit
//     order before it can fill into an approaching event.
//
// This slot is retained (check number 4) so the validator numbering
// matches the rulebook; it adds no per-call work.
func check4NewsLockout(
	_ context.Context,
	_ *models.TradeRequest,
	_ *config.Config,
	_ *RuntimeParams,
	_ *state.Manager,
	_ broker.Port,
	_ time.Time,
) models.ValidationResult {
	return pass()
}

// is247Market determines if the symbol represents a 24/7 trading instrument (Synthetics, Crypto).
func is247Market(symbol string) bool {
	s := strings.ToUpper(symbol)
	return strings.Contains(s, "CRASH") ||
		strings.Contains(s, "BOOM") ||
		strings.Contains(s, "VOLATILITY") ||
		strings.Contains(s, "STEP") ||
		strings.Contains(s, "JUMP") ||
		strings.Contains(s, "BTC") ||
		strings.Contains(s, "ETH")
}

// check5SessionFilter rejects execution when the current UTC time
// does not fall within any enabled trading session. If no session
// window is active, the trade is rejected.
func check5SessionFilter(
	_ context.Context,
	req *models.TradeRequest,
	cfg *config.Config,
	_ *RuntimeParams,
	_ *state.Manager,
	_ broker.Port,
	now time.Time,
) models.ValidationResult {
	if is247Market(req.Symbol) {
		return pass()
	}

	hour := now.Hour()

	// Find which session window the current hour falls into.
	var activeSession string
	for _, s := range constants.Sessions {
		if hour >= s.StartHour && hour < s.EndHour {
			activeSession = s.Name
			break
		}
	}

	// No session window is active at this hour: reject.
	if activeSession == "" {
		return reject(
			constants.CheckSessionFilter,
			fmt.Sprintf("no trading session active at %d:00 UTC", hour),
		)
	}

	// A session is active but not enabled in config: reject.
	if !cfg.IsSessionEnabled(activeSession) {
		return reject(
			constants.CheckSessionFilter,
			fmt.Sprintf("session %s is disabled (hour %d UTC)", activeSession, hour),
		)
	}

	return pass()
}

// check6SamePairPosition rejects if there is already an open position
// or pending order on the same symbol for this user.
func check6SamePairPosition(
	_ context.Context,
	req *models.TradeRequest,
	_ *config.Config,
	_ *RuntimeParams,
	sm *state.Manager,
	_ broker.Port,
	_ time.Time,
) models.ValidationResult {
	if sm.HasPositionOnPair(req.UserID, req.Symbol) {
		return reject(
			constants.CheckSamePairPosition,
			fmt.Sprintf("existing position or pending order on %s", req.Symbol),
		)
	}
	return pass()
}

// check7CorrelatedExposure rejects if there is an open position or
// pending order on any pair in the same correlation group for this user.
// Correlation groups are defined in constants.CorrelatedPairGroups.
// The gateway defines MR-REJECT-005 but does not implement it;
// Module B is the single owner of this check.
func check7CorrelatedExposure(
	_ context.Context,
	req *models.TradeRequest,
	_ *config.Config,
	_ *RuntimeParams,
	sm *state.Manager,
	_ broker.Port,
	_ time.Time,
) models.ValidationResult {
	if sm.HasCorrelatedExposure(req.UserID, req.Symbol) {
		return reject(
			constants.CheckCorrelatedExposure,
			fmt.Sprintf("correlated pair exposure: position exists in same group as %s", req.Symbol),
		)
	}
	return pass()
}

// check8MaxConcurrentTrades queues the trade if the maximum number
// of concurrent open positions has been reached for this user. Uses
// RuntimeParams from the settings store so dashboard changes take
// effect immediately.
func check8MaxConcurrentTrades(
	_ context.Context,
	req *models.TradeRequest,
	_ *config.Config,
	params *RuntimeParams,
	sm *state.Manager,
	_ broker.Port,
	_ time.Time,
) models.ValidationResult {
	count := sm.OpenPositionCount(req.UserID)
	if count >= params.MaxConcurrentTrades {
		return queue(
			constants.CheckMaxConcurrentTrades,
			fmt.Sprintf("at max concurrent trades: %d/%d", count, params.MaxConcurrentTrades),
		)
	}
	return pass()
}

// check9DailyLossLimit locks execution when the daily realized loss
// exceeds the configured percentage of account balance for this user.
// The current loss percentage is read from state.Manager (broker +
// PostgreSQL). The limit threshold is read from RuntimeParams
// (settings store) so dashboard changes take effect immediately.
func check9DailyLossLimit(
	_ context.Context,
	req *models.TradeRequest,
	_ *config.Config,
	params *RuntimeParams,
	sm *state.Manager,
	_ broker.Port,
	_ time.Time,
) models.ValidationResult {
	loss := sm.DailyLossPercent(req.UserID)
	if loss >= params.DailyLossLimitPct {
		return lock(
			constants.CheckDailyLossLimit,
			fmt.Sprintf("daily loss %.2f%% exceeds limit %.2f%%", loss, params.DailyLossLimitPct),
		)
	}
	return pass()
}

// check10WeeklyDrawdown pauses execution when the weekly realized
// drawdown exceeds the configured percentage of account balance for
// this user. The current drawdown percentage is read from
// state.Manager (broker + PostgreSQL). The limit threshold is read
// from RuntimeParams (settings store) so dashboard changes take
// effect immediately.
func check10WeeklyDrawdown(
	_ context.Context,
	req *models.TradeRequest,
	_ *config.Config,
	params *RuntimeParams,
	sm *state.Manager,
	_ broker.Port,
	_ time.Time,
) models.ValidationResult {
	dd := sm.WeeklyDrawdownPercent(req.UserID)
	if dd >= params.WeeklyDrawdownPct {
		return pause(
			constants.CheckWeeklyDrawdown,
			fmt.Sprintf("weekly drawdown %.2f%% exceeds limit %.2f%%", dd, params.WeeklyDrawdownPct),
		)
	}
	return pass()
}

// check11Spread rejects if the live spread exceeds the configured
// multiplier of the average spread for the instrument.
func check11Spread(
	ctx context.Context,
	req *models.TradeRequest,
	cfg *config.Config,
	_ *RuntimeParams,
	_ *state.Manager,
	bp broker.Port,
	_ time.Time,
) models.ValidationResult {
	brokerCtx, cancel := context.WithTimeout(ctx, time.Duration(cfg.BrokerTimeoutMs)*time.Millisecond)
	defer cancel()

	info, err := bp.GetInstrumentInfo(brokerCtx, req.Symbol)
	if err != nil {
		return reject(
			constants.CheckSpread,
			fmt.Sprintf("failed to get instrument info for %s: %v", req.Symbol, err),
		)
	}

	if info.AvgSpread <= 0 {
		// No average spread data available; allow trade through.
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

// check12MinRR rejects if the risk-reward ratio from the processor
// output is below the minimum required for the trading style.
func check12MinRR(
	_ context.Context,
	req *models.TradeRequest,
	_ *config.Config,
	_ *RuntimeParams,
	_ *state.Manager,
	_ broker.Port,
	_ time.Time,
) models.ValidationResult {
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

// check13WeekendDayFilter rejects entries on weekends, Monday before
// London Open, and Friday after the style-specific cutoff hour.
func check13WeekendDayFilter(
	_ context.Context,
	req *models.TradeRequest,
	_ *config.Config,
	_ *RuntimeParams,
	_ *state.Manager,
	_ broker.Port,
	now time.Time,
) models.ValidationResult {
	if is247Market(req.Symbol) {
		return pass()
	}

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
