package routing

import (
	"context"
	"fmt"
	"strings"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/billing/store"
	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/ports"
)

// RouteResult holds the outcome of routing a processor decision.
type RouteResult struct {
	Outcome         constants.CycleOutcome
	GuardResult     *models.GuardEvaluationResult
	ExecutionResult map[string]interface{}
}

// Router routes processor decisions through guards to execution.
type Router struct {
	guards     *GuardEvaluator
	execution  ports.ExecutionPort
	transport  *alertredis.Transport
	usageStore *store.UsageStore
	log        zerolog.Logger
}

// NewRouter creates a DecisionRouter.
func NewRouter(
	guards *GuardEvaluator,
	execution ports.ExecutionPort,
	transport *alertredis.Transport,
	usageStore *store.UsageStore,
) *Router {
	return &Router{
		guards:     guards,
		execution:  execution,
		transport:  transport,
		usageStore: usageStore,
		log:        observability.Logger("decision_router"),
	}
}

// RoutePreLLM evaluates the deterministic (LLM-independent) guards
// and short-circuits the cycle when any of them reject. The
// orchestrator calls this BEFORE the processor LLM so a guaranteed
// rejection (e.g. Asian session restriction on XAUUSD) skips the
// ~168k-token LLM call entirely.
//
// Returns:
//   - On reject: RouteResult with OutcomeRejectedByGuard and the
//     pre-LLM GuardEvaluationResult. The caller MUST NOT call the
//     processor LLM or the post-LLM Route after a reject.
//   - On pass/warn: RouteResult with OutcomeTradeApproved as a
//     placeholder outcome (the cycle has not actually been approved
//     yet — the LLM and post-LLM guards still need to run). The
//     caller threads the GuardResult into Route so the deterministic
//     checks are not re-evaluated.
func (r *Router) RoutePreLLM(
	ctx context.Context,
	symbol string,
	taResult *models.TASymbolResult,
	macroResult *models.MacroResult,
	traceID string,
) *RouteResult {
	preResult := r.guards.EvaluatePreLLM(taResult, macroResult, traceID)

	// Publish warning-level checks (e.g. low-liquidity WARN) even when
	// the overall verdict is non-blocking. Mirrors the post-LLM Route
	// branch so the dashboard sees identical warning fan-out behaviour
	// regardless of which phase produced the WARN.
	for _, check := range preResult.Checks {
		if check.Verdict == constants.VerdictWarn && r.transport != nil {
			r.transport.Publish(ctx,
				alert.NewEvent(alert.SourceGateway, alert.TypeGuardWarning, alert.SeverityWarning,
					fmt.Sprintf("Guard warning [%s]: %s", check.Rule, check.Reason)).
					WithUserID(auth.UserIDFromContext(ctx)).
					WithSymbol(symbol).
					WithTraceID(traceID).
					WithDetails(map[string]interface{}{
						"rule":     string(check.Rule),
						"reason":   check.Reason,
						"metadata": check.Metadata,
					}),
			)
		}
	}

	if preResult.IsApproved() {
		// Not actually approved yet — the cycle must still run the LLM
		// and the post-LLM guard. The orchestrator interprets the nil
		// outcome here as "proceed".
		return &RouteResult{GuardResult: preResult}
	}

	// Deterministic rejection: bump the same counters and publish the
	// same TypeGuardRejected alert that the post-LLM Route emits, so
	// the dashboard cannot tell which phase produced the rejection.
	observability.GatewayNoSetupTotal.WithLabelValues("guard_rejection").Inc()
	observability.GatewayStageErrors.WithLabelValues(constants.StageGuardEvaluation.String(), "rejected").Inc()

	r.log.Warn().
		Str("symbol", symbol).
		Str("phase", "pre_llm").
		Strs("blocking_rules", preResult.BlockingRules).
		Str("trace_id", traceID).
		Msg("route_guard_rejected")

	var reasons []string
	for _, check := range preResult.Checks {
		if check.Verdict == constants.VerdictReject {
			reasons = append(reasons, check.Reason)
		}
	}

	if r.transport != nil {
		r.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeGuardRejected, alert.SeverityWarning,
				fmt.Sprintf("Trade rejected by guards: %s", strings.Join(preResult.BlockingRules, ", "))).
				WithUserID(auth.UserIDFromContext(ctx)).
				WithSymbol(symbol).
				WithTraceID(traceID).
				WithDetails(map[string]interface{}{
					"blocking_rules": preResult.BlockingRules,
					"reasons":        reasons,
					"phase":          "pre_llm",
				}),
		)
	}

	return &RouteResult{
		Outcome:     constants.OutcomeRejectedByGuard,
		GuardResult: preResult,
	}
}

// Route runs the post-LLM (counter-trend) guard, merges its result
// with the pre-LLM result the orchestrator already evaluated, and
// routes the decision to the execution engine when the final verdict
// approves the trade.
//
// preLLMResult MUST be the GuardResult returned by RoutePreLLM for
// this cycle. Passing nil is allowed and triggers a fresh full
// evaluation — kept only for backward compatibility with any test
// or caller that has not been migrated yet; production call sites
// always supply the pre-LLM result.
func (r *Router) Route(
	ctx context.Context,
	processorOutput *models.ProcessorOutput,
	taResult *models.TASymbolResult,
	macroResult *models.MacroResult,
	preLLMResult *models.GuardEvaluationResult,
	traceID string,
) *RouteResult {
	// Step 1: If processor says NO SETUP, respect it.
	if !processorOutput.TradeValid {
		reason := processorOutput.Reasoning
		if reason == "" {
			reason = "Processor determined no valid setup"
		}
		observability.GatewayNoSetupTotal.WithLabelValues("processor_no_setup").Inc()

		r.log.Info().
			Str("symbol", taResult.Symbol).
			Str("reason", reason).
			Strs("rejection_rules", processorOutput.RejectionRules).
			Str("trace_id", traceID).
			Msg("route_no_setup")

		return &RouteResult{Outcome: constants.OutcomeNoSetup}
	}

	// Step 2: Run post-LLM guard (counter-trend) and combine with the
	// pre-LLM result the orchestrator already produced. When the caller
	// did not supply a pre-LLM result (legacy path), fall back to a
	// full evaluation so behaviour stays correct.
	var guardResult *models.GuardEvaluationResult
	if preLLMResult != nil {
		postResult := r.guards.EvaluatePostLLM(processorOutput, taResult, traceID)
		guardResult = MergeResults(preLLMResult, postResult)
	} else {
		guardResult = r.guards.Evaluate(processorOutput, taResult, macroResult, traceID)
	}

	// Publish guard warnings produced by the post-LLM phase. Pre-LLM
	// warnings were already published in RoutePreLLM, so re-emitting
	// them here would double-toast the dashboard. We compare against
	// the pre-LLM checks by Rule to find the new warnings only.
	preWarnRules := make(map[constants.GuardRule]struct{})
	if preLLMResult != nil {
		for _, c := range preLLMResult.Checks {
			if c.Verdict == constants.VerdictWarn {
				preWarnRules[c.Rule] = struct{}{}
			}
		}
	}
	for _, check := range guardResult.Checks {
		if check.Verdict != constants.VerdictWarn {
			continue
		}
		if _, alreadyPublished := preWarnRules[check.Rule]; alreadyPublished {
			continue
		}
		if r.transport == nil {
			continue
		}
		r.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeGuardWarning, alert.SeverityWarning,
				fmt.Sprintf("Guard warning [%s]: %s", check.Rule, check.Reason)).
				WithUserID(auth.UserIDFromContext(ctx)).
				WithSymbol(taResult.Symbol).
				WithDirection(processorOutput.Direction).
				WithTraceID(traceID).
				WithDetails(map[string]interface{}{
					"rule":     string(check.Rule),
					"reason":   check.Reason,
					"metadata": check.Metadata,
				}),
		)
	}

	// Step 3: If guards reject, block execution.
	if !guardResult.IsApproved() {
		observability.GatewayNoSetupTotal.WithLabelValues("guard_rejection").Inc()
		observability.GatewayStageErrors.WithLabelValues(constants.StageGuardEvaluation.String(), "rejected").Inc()

		r.log.Warn().
			Str("symbol", taResult.Symbol).
			Strs("blocking_rules", guardResult.BlockingRules).
			Str("trace_id", traceID).
			Msg("route_guard_rejected")

		// Collect rejection reasons.
		var reasons []string
		for _, check := range guardResult.Checks {
			if check.Verdict == constants.VerdictReject {
				reasons = append(reasons, check.Reason)
			}
		}

		if r.transport != nil {
			r.transport.Publish(ctx,
				alert.NewEvent(alert.SourceGateway, alert.TypeGuardRejected, alert.SeverityWarning,
					fmt.Sprintf("Trade rejected by guards: %s", strings.Join(guardResult.BlockingRules, ", "))).
					WithUserID(auth.UserIDFromContext(ctx)).
					WithSymbol(taResult.Symbol).
					WithDirection(processorOutput.Direction).
					WithTraceID(traceID).
					WithDetails(map[string]interface{}{
						"blocking_rules": guardResult.BlockingRules,
						"reasons":        reasons,
						"confidence":     processorOutput.Confidence,
						"grade":          processorOutput.Grade,
					}),
			)
		}

		return &RouteResult{
			Outcome:     constants.OutcomeRejectedByGuard,
			GuardResult: guardResult,
		}
	}

	// Step 4: Route to execution engine (Module B).
	execResult := r.executeTrade(ctx, taResult.Symbol, processorOutput, traceID)

	symbol := taResult.Symbol
	if symbol == "" {
		symbol = "unknown"
	}
	direction := processorOutput.Direction
	if direction == "" {
		direction = "unknown"
	}
	observability.GatewayTradeRouted.WithLabelValues(symbol, direction).Inc()

	r.log.Info().
		Str("symbol", taResult.Symbol).
		Str("direction", processorOutput.Direction).
		Float64("confidence", processorOutput.Confidence).
		Str("grade", processorOutput.Grade).
		Str("guard_verdict", string(guardResult.OverallVerdict)).
		Str("trace_id", traceID).
		Msg("route_trade_approved")

	if r.transport != nil {
		r.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeTradeRouted, alert.SeverityInfo,
				fmt.Sprintf("Trade routed to execution: %s %s (grade: %s, confidence: %.1f%%)",
					symbol, direction, processorOutput.Grade, processorOutput.Confidence*100)).
				WithUserID(auth.UserIDFromContext(ctx)).
				WithSymbol(symbol).
				WithDirection(direction).
				WithTraceID(traceID).
				WithDetails(map[string]interface{}{
					"confidence":       processorOutput.Confidence,
					"grade":            processorOutput.Grade,
					"trading_style":    processorOutput.TradingStyle,
					"guard_verdict":    string(guardResult.OverallVerdict),
					"analysis_id":      processorOutput.AnalysisID,
					"execution_result": execResult,
				}),
		)
	}

	return &RouteResult{
		Outcome:         constants.OutcomeTradeApproved,
		GuardResult:     guardResult,
		ExecutionResult: execResult,
	}
}

func (r *Router) executeTrade(
	ctx context.Context,
	symbol string,
	decision *models.ProcessorOutput,
	traceID string,
) map[string]interface{} {
	claims := auth.ClaimsFromContext(ctx)
	if claims != nil && claims.Role != "admin" && claims.Tier == "free" {
		r.log.Info().
			Str("symbol", symbol).
			Str("direction", decision.Direction).
			Str("trace_id", traceID).
			Msg("execution_blocked_for_free_tier")

		// Use the dedicated SUBSCRIPTION_REQUIRED event with SeverityInfo.
		// This is an upsell, not an error or a routed-trade outcome, so
		// reusing TypeTradeRouted/Warning here historically misled the
		// SPA into invalidating execution-state queries for an event
		// that does not move execution state at all. The new event maps
		// to ['billing'] + ['auth', 'me'] invalidations in eventMap.ts.
		if r.transport != nil {
			r.transport.Publish(ctx,
				alert.NewEvent(alert.SourceGateway, alert.TypeSubscriptionRequired, alert.SeverityInfo,
					fmt.Sprintf("Trade execution blocked for %s: Upgrade to Pro tier to unlock execution.", symbol)).
					WithUserID(claims.UserID).
					WithSymbol(symbol).
					WithDirection(decision.Direction).
					WithTraceID(traceID).
					WithDetails(map[string]interface{}{
						"reason":        "Free tier does not support trade execution.",
						"required_tier": "pro_byok",
						"feature":       "automated_execution",
					}),
			)
		}

		return map[string]interface{}{
			"status":        "blocked",
			"reason":        "Trade execution is not available on the Free tier. Upgrade to Pro.",
			"error_code":    "tier_required",
			"required_tier": "pro_byok",
			"feature":       "automated_execution",
		}
	}

	if r.execution == nil {
		r.log.Info().
			Str("symbol", symbol).
			Str("direction", decision.Direction).
			Str("trace_id", traceID).
			Msg("execution_engine_not_available")
		return map[string]interface{}{"status": "pending", "reason": "execution_engine_not_implemented"}
	}

	// Kill-switch primary gate (CHECKLIST Section 8). Defense-in-depth:
	// block routing here so a halted user/platform does not even reach
	// the broker round-trip. Analysis has already run; only placement is
	// blocked. The execution validator's check0KillSwitch is the
	// AUTHORITATIVE enforcement point, so this gate fails OPEN on a read
	// error (proceed to Execute) rather than converting an execution
	// blip into a routing outage. The empty targetUserID makes the
	// execution server resolve the caller from the forwarded JWT.
	if globalHalted, userHalted, err := r.execution.HaltState(ctx, ""); err != nil {
		r.log.Warn().
			Err(err).
			Str("symbol", symbol).
			Str("trace_id", traceID).
			Msg("kill_switch_state_read_failed_failing_open_to_validator_backstop")
	} else if globalHalted || userHalted {
		scope := "user"
		reason := "Execution is halted for your account (kill switch engaged)."
		if globalHalted {
			scope = "global"
			reason = "Execution is halted platform-wide by an administrator (kill switch engaged)."
		}

		observability.GatewayExecutionHaltedTotal.WithLabelValues(scope).Inc()

		r.log.Warn().
			Str("symbol", symbol).
			Str("direction", decision.Direction).
			Str("scope", scope).
			Str("trace_id", traceID).
			Msg("execution_blocked_by_kill_switch")

		if r.transport != nil {
			r.transport.Publish(ctx,
				alert.NewEvent(alert.SourceGateway, alert.TypeExecutionHalted, alert.SeverityCritical,
					fmt.Sprintf("Trade blocked for %s: %s", symbol, reason)).
					WithUserID(auth.UserIDFromContext(ctx)).
					WithSymbol(symbol).
					WithDirection(decision.Direction).
					WithTraceID(traceID).
					WithDetails(map[string]interface{}{
						"scope":  scope,
						"reason": reason,
					}),
			)
		}

		return map[string]interface{}{
			"status": "halted",
			"scope":  scope,
			"reason": reason,
		}
	}

	if r.usageStore != nil && claims != nil {
		_ = r.usageStore.IncrementMetric(ctx, claims.UserID, "execution_attempts", 1)
	}

	result, err := r.execution.Execute(ctx, decision)
	if err != nil {
		observability.GatewayStageErrors.WithLabelValues(constants.StageDecisionRouting.String(), "execution_error").Inc()
		r.log.Error().
			Str("symbol", symbol).
			Err(err).
			Str("trace_id", traceID).
			Msg("execution_failed")

		if r.transport != nil {
			r.transport.Publish(ctx,
				alert.NewEvent(alert.SourceGateway, alert.TypeExecutionCallFailed, alert.SeverityError,
					fmt.Sprintf("Execution call failed for %s: %s", symbol, err.Error())).
					WithUserID(auth.UserIDFromContext(ctx)).
					WithSymbol(symbol).
					WithDirection(decision.Direction).
					WithTraceID(traceID).
					WithDetail("error", err.Error()),
			)
		}

		return map[string]interface{}{"status": "error", "reason": err.Error()}
	}
	return result
}
