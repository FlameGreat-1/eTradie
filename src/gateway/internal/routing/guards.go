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
//
// Guards split into two phases by data dependency:
//
//   - Pre-LLM (deterministic): MR-REJECT-001, -002, -008, -009.
//     These depend only on time, symbol, and macro calendar data.
//     Running them before the processor LLM lets the cycle
//     short-circuit on a guaranteed rejection without spending
//     ~168k input tokens on a call whose result will be discarded.
//
//   - Post-LLM (LLM-dependent): MR-REJECT-006 (counter-trend).
//     Needs ProcessorOutput.Direction, so it can only run after
//     the processor LLM returns.
//
// Each guard still runs exactly once per cycle; the split is a
// scheduling change, not a duplication.
type GuardEvaluator struct {
	log zerolog.Logger
}

// NewGuardEvaluator creates a GuardEvaluator.
func NewGuardEvaluator() *GuardEvaluator {
	return &GuardEvaluator{log: observability.Logger("guard_evaluator")}
}

// EvaluatePreLLM runs the 4 deterministic guards that do not need
// the processor LLM output. The returned result carries exactly 4
// checks in the canonical order (001, 002, 008, 009). Callers that
// want all 5 checks in the final result must merge this with the
// post-LLM result via MergeResults.
//
// This is the cycle's first hard gate: when the result rejects,
// processSymbol skips the LLM call entirely.
func (g *GuardEvaluator) EvaluatePreLLM(
	taResult *models.TASymbolResult,
	macroResult *models.MacroResult,
	traceID string,
) *models.GuardEvaluationResult {
	start := time.Now()

	checks := []models.GuardCheckResult{
		checkHighImpactEventProximity(taResult, macroResult),
		checkSessionRestriction(taResult),
		checkWeekendGapRisk(taResult),
		checkLowLiquidityHours(taResult),
	}

	result := aggregate(checks)

	elapsed := time.Since(start).Seconds()
	observability.GatewayGuardDuration.Observe(elapsed)

	g.log.Info().
		Str("phase", "pre_llm").
		Str("overall_verdict", string(result.OverallVerdict)).
		Strs("blocking_rules", result.BlockingRules).
		Int("checks_total", len(checks)).
		Float64("duration_ms", elapsed*1000).
		Str("trace_id", traceID).
		Msg("guard_evaluation_completed")

	return result
}

// EvaluatePostLLM runs only the LLM-dependent guards. Today that is
// MR-REJECT-006 (counter-trend) which needs ProcessorOutput.Direction.
// The returned result carries exactly 1 check.
func (g *GuardEvaluator) EvaluatePostLLM(
	processorOutput *models.ProcessorOutput,
	taResult *models.TASymbolResult,
	traceID string,
) *models.GuardEvaluationResult {
	start := time.Now()

	checks := []models.GuardCheckResult{
		checkCounterTrend(processorOutput, taResult),
	}

	result := aggregate(checks)

	elapsed := time.Since(start).Seconds()
	observability.GatewayGuardDuration.Observe(elapsed)

	g.log.Info().
		Str("phase", "post_llm").
		Str("overall_verdict", string(result.OverallVerdict)).
		Strs("blocking_rules", result.BlockingRules).
		Int("checks_total", len(checks)).
		Float64("duration_ms", elapsed*1000).
		Str("trace_id", traceID).
		Msg("guard_evaluation_completed")

	return result
}

// MergeResults combines a pre-LLM and a post-LLM result into the
// single GuardEvaluationResult the dashboard and audit log expect.
// Checks are emitted in the canonical order (001, 002, 006, 008,
// 009) regardless of the order the phases ran in, so consumers do
// not need to know about the split.
//
// Either argument may be nil: when the cycle short-circuits pre-LLM
// there is no post-LLM result, and EvaluatePreLLM still returns the
// full set of pre-LLM checks.
func MergeResults(pre, post *models.GuardEvaluationResult) *models.GuardEvaluationResult {
	if pre == nil && post == nil {
		return &models.GuardEvaluationResult{OverallVerdict: constants.VerdictPass}
	}

	byRule := make(map[constants.GuardRule]models.GuardCheckResult, 5)
	if pre != nil {
		for _, c := range pre.Checks {
			byRule[c.Rule] = c
		}
	}
	if post != nil {
		for _, c := range post.Checks {
			byRule[c.Rule] = c
		}
	}

	canonical := []constants.GuardRule{
		constants.RuleHighImpactEventProximity,
		constants.RuleSessionRestriction,
		constants.RuleCounterTrendNoChoch,
		constants.RuleWeekendGapRisk,
		constants.RuleLowLiquidityHours,
	}

	ordered := make([]models.GuardCheckResult, 0, len(canonical))
	for _, rule := range canonical {
		if c, ok := byRule[rule]; ok {
			ordered = append(ordered, c)
		}
	}

	return aggregateNoMetrics(ordered)
}

// Evaluate runs ALL guard checks in a single call (legacy API).
//
// Kept so any caller that does not need the pre/post split can still
// produce a complete GuardEvaluationResult in one step. New call
// sites should prefer EvaluatePreLLM + EvaluatePostLLM + MergeResults
// so the deterministic checks can short-circuit before the LLM call.
func (g *GuardEvaluator) Evaluate(
	processorOutput *models.ProcessorOutput,
	taResult *models.TASymbolResult,
	macroResult *models.MacroResult,
	traceID string,
) *models.GuardEvaluationResult {
	pre := g.EvaluatePreLLM(taResult, macroResult, traceID)
	post := g.EvaluatePostLLM(processorOutput, taResult, traceID)
	return MergeResults(pre, post)
}

// aggregate computes the OverallVerdict and BlockingRules slice for a
// set of check results AND bumps the per-rule Prometheus rejection
// counter. Used by EvaluatePreLLM and EvaluatePostLLM where each check
// runs for the first (and only) time in a cycle.
func aggregate(checks []models.GuardCheckResult) *models.GuardEvaluationResult {
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

	return &models.GuardEvaluationResult{
		Checks:         checks,
		OverallVerdict: overall,
		BlockingRules:  blocking,
	}
}

// aggregateNoMetrics computes OverallVerdict and BlockingRules WITHOUT
// touching Prometheus counters. Used by MergeResults to re-aggregate
// already-evaluated checks; the original aggregate call that produced
// each pre/post result has already incremented the per-rule counter
// exactly once, so re-counting here would double-count.
func aggregateNoMetrics(checks []models.GuardCheckResult) *models.GuardEvaluationResult {
	var blocking []string
	overall := constants.VerdictPass

	for _, check := range checks {
		if check.Verdict == constants.VerdictReject {
			overall = constants.VerdictReject
			blocking = append(blocking, string(check.Rule))
		} else if check.Verdict == constants.VerdictWarn && overall != constants.VerdictReject {
			overall = constants.VerdictWarn
		}
	}

	return &models.GuardEvaluationResult{
		Checks:         checks,
		OverallVerdict: overall,
		BlockingRules:  blocking,
	}
}

// MR-REJECT-001: No entries within the news lockout window of a
// high-impact economic-calendar event (NFP, CPI, PPI, FED rate
// decision, etc.) that affects one of the symbol's currencies.
//
// This is the DECISION-TIME gate. Because the trade's activation can
// be delayed (a LIMIT order rests at the broker for its TTL; an
// INSTANT watcher polls until price enters the zone), the same
// currency-scoped evaluation is re-run at fire time
// (RunConfirmationPulseWithParams) and at LIMIT placement / TTL time
// (CheckNewsWindow RPC). Here the trading style is not yet known
// (pre-LLM), so the normal lockout window is used; the wider
// scalping window is enforced later where the style is known.
func checkHighImpactEventProximity(ta *models.TASymbolResult, macro *models.MacroResult) models.GuardCheckResult {
	// 24/7 markets have no fiat calendar exposure; the orchestrator
	// also passes a nil macro for them. EvaluateNewsWindow returns
	// "no exposure" for such symbols, so they pass without needing a
	// calendar.
	if Is247Market(ta.Symbol) {
		return models.GuardCheckResult{
			Rule: constants.RuleHighImpactEventProximity, Verdict: constants.VerdictPass,
			Reason: "News proximity does not apply to 24/7 markets",
		}
	}

	var calendar map[string]interface{}
	if macro != nil {
		calendar = macro.Calendar
	}

	status := EvaluateNewsWindow(calendar, ta.Symbol, time.Now().UTC(), constants.HighImpactEventLockoutMinutes)

	if !status.DataAvailable {
		// Fail closed (N3): a non-24/7 symbol with no calendar data
		// must not trade blind into a possible high-impact event.
		return models.GuardCheckResult{
			Rule:     constants.RuleHighImpactEventProximity,
			Verdict:  constants.VerdictReject,
			Reason:   status.Reason,
			Metadata: map[string]interface{}{"data_available": false},
		}
	}

	if status.Locked {
		return models.GuardCheckResult{
			Rule:    constants.RuleHighImpactEventProximity,
			Verdict: constants.VerdictReject,
			Reason:  status.Reason,
			Metadata: map[string]interface{}{
				"event_name":    status.EventName,
				"currency":      status.Currency,
				"minutes_until": status.MinutesUntil,
			},
		}
	}

	return models.GuardCheckResult{
		Rule: constants.RuleHighImpactEventProximity, Verdict: constants.VerdictPass,
		Reason: "No high-impact events within lockout window",
	}
}

// MR-REJECT-002: No entries during Asian session for non-Asian pairs.
func checkSessionRestriction(ta *models.TASymbolResult) models.GuardCheckResult {
	if Is247Market(ta.Symbol) {
		return models.GuardCheckResult{
			Rule: constants.RuleSessionRestriction, Verdict: constants.VerdictPass,
			Reason: "Session restrictions do not apply to 24/7 markets",
		}
	}

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
		Rule:     constants.RuleSessionRestriction,
		Verdict:  constants.VerdictReject,
		Reason:   fmt.Sprintf("Asian session restriction: %s should not be traded 00:00-07:00 UTC", symbol),
		Metadata: map[string]interface{}{"hour_utc": hour, "symbol": symbol},
	}
}

// MR-REJECT-006: Counter-trend without CHoCH = NO SETUP.
func checkCounterTrend(processor *models.ProcessorOutput, ta *models.TASymbolResult) models.GuardCheckResult {
	if processor == nil || !processor.TradeValid {
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
		Rule:     constants.RuleCounterTrendNoChoch,
		Verdict:  constants.VerdictReject,
		Reason:   "Counter-trend trade without any CHoCH across timeframes - rejected per MR-REJECT-006",
		Metadata: map[string]interface{}{"trend": trend, "direction": direction, "htf_timeframes": ta.HTFTimeframes},
	}
}

// MR-REJECT-008: No new entries close to market close on Friday.
func checkWeekendGapRisk(ta *models.TASymbolResult) models.GuardCheckResult {
	if Is247Market(ta.Symbol) {
		return models.GuardCheckResult{
			Rule: constants.RuleWeekendGapRisk, Verdict: constants.VerdictPass,
			Reason: "Weekend gap risk does not apply to 24/7 markets",
		}
	}

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
func checkLowLiquidityHours(ta *models.TASymbolResult) models.GuardCheckResult {
	if Is247Market(ta.Symbol) {
		return models.GuardCheckResult{
			Rule: constants.RuleLowLiquidityHours, Verdict: constants.VerdictPass,
			Reason: "Low liquidity hours do not apply to 24/7 markets",
		}
	}

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
