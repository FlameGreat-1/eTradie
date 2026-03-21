package routing

import (
	"fmt"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/querybuilder"
)

// GuardEvaluator evaluates all post-processor guard rules.
type GuardEvaluator struct {
	log zerolog.Logger
}

// NewGuardEvaluator creates a GuardEvaluator.
func NewGuardEvaluator() *GuardEvaluator {
	return &GuardEvaluator{log: observability.Logger("guard_evaluator")}
}

// Evaluate runs all guard checks and returns the aggregated result.
func (g *GuardEvaluator) Evaluate(
	processorOutput *models.ProcessorOutput,
	taResult *models.TASymbolResult,
	macroResult *models.MacroResult,
	traceID string,
) *models.GuardEvaluationResult {
	start := time.Now()

	checks := []models.GuardCheckResult{
		checkNewsProximity(macroResult),
		checkSessionRestriction(taResult),
		checkCounterTrend(processorOutput, taResult),
		checkWeekendGapRisk(),
		checkLowLiquidityHours(),
	}

	var blocking []string
	overall := constants.VerdictPass

	for _, check := range checks {
		if check.Verdict == constants.VerdictReject {
			overall = constants.VerdictReject
			blocking = append(blocking, string(check.Rule))
			observability.GatewayGuardRejections.WithLabelValues(string(check.Rule)).Inc()
		} else if check.Verdict == constants.VerdictWarn && overall != constants.VerdictReject {
			overall = constants.VerdictWarn
		}
	}

	elapsed := time.Since(start).Seconds()
	observability.GatewayGuardDuration.Observe(elapsed)

	result := &models.GuardEvaluationResult{
		Checks:         checks,
		OverallVerdict: overall,
		BlockingRules:  blocking,
	}

	g.log.Info().
		Str("overall_verdict", string(overall)).
		Strs("blocking_rules", blocking).
		Int("checks_total", len(checks)).
		Float64("duration_ms", elapsed*1000).
		Str("trace_id", traceID).
		Msg("guard_evaluation_completed")

	return result
}

// MR-REJECT-001: No entries within NewsLockoutMinutes of high-impact news.
func checkNewsProximity(macro *models.MacroResult) models.GuardCheckResult {
	if macro.Calendar == nil {
		return models.GuardCheckResult{
			Rule: constants.RuleNewsProximity, Verdict: constants.VerdictPass,
			Reason: "No calendar data available",
		}
	}

	now := time.Now().UTC()
	events := querybuilder.GetSliceOfMapsExported(macro.Calendar, "events")

	for _, event := range events {
		impact := strings.ToUpper(querybuilder.GetStrDefaultExported(event, "impact", ""))
		if impact != "HIGH" {
			continue
		}
		eventTimeStr := querybuilder.GetStrDefaultExported(event, "event_time", "")
		if eventTimeStr == "" {
			continue
		}
		eventTime, err := time.Parse(time.RFC3339, strings.Replace(eventTimeStr, "Z", "+00:00", 1))
		if err != nil {
			eventTime, err = time.Parse("2006-01-02T15:04:05", eventTimeStr)
			if err != nil {
				continue
			}
			eventTime = eventTime.UTC()
		}

		minutesUntil := eventTime.Sub(now).Minutes()
		if minutesUntil >= 0 && minutesUntil <= float64(constants.NewsLockoutMinutes) {
			eventName := querybuilder.GetStrDefaultExported(event, "event_name", "unknown")
			return models.GuardCheckResult{
				Rule:    constants.RuleNewsProximity,
				Verdict: constants.VerdictReject,
				Reason: fmt.Sprintf(
					"High-impact event '%s' in %d minutes (lockout: %dmin)",
					eventName, int(minutesUntil), constants.NewsLockoutMinutes,
				),
				Metadata: map[string]interface{}{"event_name": eventName, "minutes_until": minutesUntil},
			}
		}
	}

	return models.GuardCheckResult{
		Rule: constants.RuleNewsProximity, Verdict: constants.VerdictPass,
		Reason: "No high-impact events within lockout window",
	}
}

// MR-REJECT-002: No entries during Asian session for non-Asian pairs.
func checkSessionRestriction(ta *models.TASymbolResult) models.GuardCheckResult {
	now := time.Now().UTC()
	hour := now.Hour()
	isAsian := hour >= 0 && hour < 7

	if !isAsian {
		return models.GuardCheckResult{
			Rule: constants.RuleSessionRestriction, Verdict: constants.VerdictPass,
			Reason: fmt.Sprintf("Current hour %d UTC is outside Asian session", hour),
		}
	}

	symbol := strings.ToUpper(ta.Symbol)
	if strings.Contains(symbol, "JPY") || strings.Contains(symbol, "AUD") || strings.Contains(symbol, "NZD") {
		return models.GuardCheckResult{
			Rule: constants.RuleSessionRestriction, Verdict: constants.VerdictPass,
			Reason: fmt.Sprintf("%s is active during Asian session", symbol),
		}
	}

	return models.GuardCheckResult{
		Rule:    constants.RuleSessionRestriction,
		Verdict: constants.VerdictReject,
		Reason:  fmt.Sprintf("Asian session restriction: %s should not be traded 00:00-07:00 UTC", symbol),
		Metadata: map[string]interface{}{"hour_utc": hour, "symbol": symbol},
	}
}

// MR-REJECT-006: Counter-trend without CHoCH = NO SETUP.
func checkCounterTrend(processor *models.ProcessorOutput, ta *models.TASymbolResult) models.GuardCheckResult {
	if !processor.TradeValid {
		return models.GuardCheckResult{
			Rule: constants.RuleCounterTrendNoChoch, Verdict: constants.VerdictPass,
			Reason: "Trade not valid, guard not applicable",
		}
	}

	trend := ta.OverallTrend
	if trend == "" {
		trend = "NEUTRAL"
	}
	direction := strings.ToUpper(processor.Direction)

	isCounter := (trend == "BULLISH" && (direction == "SHORT" || direction == "BEARISH" || direction == "SELL")) ||
		(trend == "BEARISH" && (direction == "LONG" || direction == "BULLISH" || direction == "BUY"))

	if !isCounter {
		return models.GuardCheckResult{
			Rule: constants.RuleCounterTrendNoChoch, Verdict: constants.VerdictPass,
			Reason: "Trade aligns with overall multi-TF trend",
		}
	}

	totalChoch := 0
	for tf, snapshot := range ta.Snapshots {
		chochEvents, ok := snapshot["choch_events"]
		if !ok || chochEvents == nil {
			continue
		}

		switch v := chochEvents.(type) {
		case map[string]interface{}:
			if count, ok := v["count"]; ok {
				switch c := count.(type) {
				case float64:
					totalChoch += int(c)
				case int:
					totalChoch += c
				case int64:
					totalChoch += int(c)
				}
			}
		case float64:
			totalChoch += int(v)
		case int:
			totalChoch += v
		case int64:
			totalChoch += int(v)
		case []interface{}:
			totalChoch += len(v)
		default:
			// Unknown format: log for investigation but do not reject.
			// Silently returning 0 here could incorrectly reject valid
			// counter-trend trades with CHoCH confirmation.
			log := observability.Logger("guard_evaluator")
			log.Warn().
				Str("timeframe", tf).
				Str("symbol", ta.Symbol).
				Str("type", fmt.Sprintf("%T", chochEvents)).
				Msg("choch_events_unexpected_format")
		}
	}

	if totalChoch > 0 {
		return models.GuardCheckResult{
			Rule:     constants.RuleCounterTrendNoChoch,
			Verdict:  constants.VerdictWarn,
			Reason:   "Counter-trend trade with CHoCH detected across timeframes - proceed with caution",
			Metadata: map[string]interface{}{"total_choch_count": totalChoch},
		}
	}

	return models.GuardCheckResult{
		Rule:    constants.RuleCounterTrendNoChoch,
		Verdict: constants.VerdictReject,
		Reason:  "Counter-trend trade without any CHoCH across timeframes - rejected per MR-REJECT-006",
		Metadata: map[string]interface{}{"trend": trend, "direction": direction, "htf_timeframes": ta.HTFTimeframes},
	}
}

// MR-REJECT-008: No new entries close to market close on Friday.
func checkWeekendGapRisk() models.GuardCheckResult {
	now := time.Now().UTC()

	if now.Weekday() == time.Friday && now.Hour() >= 20 {
		return models.GuardCheckResult{
			Rule: constants.RuleWeekendGapRisk, Verdict: constants.VerdictReject,
			Reason:   "Friday after 20:00 UTC - weekend gap risk",
			Metadata: map[string]interface{}{"day": "Friday", "hour": now.Hour()},
		}
	}

	if now.Weekday() == time.Saturday || now.Weekday() == time.Sunday {
		return models.GuardCheckResult{
			Rule: constants.RuleWeekendGapRisk, Verdict: constants.VerdictReject,
			Reason:   "Weekend - market closed",
			Metadata: map[string]interface{}{"day": now.Weekday().String()},
		}
	}

	return models.GuardCheckResult{
		Rule: constants.RuleWeekendGapRisk, Verdict: constants.VerdictPass,
		Reason: "Not in weekend gap risk window",
	}
}

// MR-REJECT-009: Warn during known low-liquidity hours.
func checkLowLiquidityHours() models.GuardCheckResult {
	now := time.Now().UTC()
	hour := now.Hour()

	if hour >= 21 || hour < 1 {
		return models.GuardCheckResult{
			Rule:     constants.RuleLowLiquidityHours,
			Verdict:  constants.VerdictWarn,
			Reason:   fmt.Sprintf("Low liquidity period: %d:00 UTC", hour),
			Metadata: map[string]interface{}{"hour_utc": hour},
		}
	}

	return models.GuardCheckResult{
		Rule: constants.RuleLowLiquidityHours, Verdict: constants.VerdictPass,
		Reason: fmt.Sprintf("Normal liquidity hours: %d:00 UTC", hour),
	}
}
