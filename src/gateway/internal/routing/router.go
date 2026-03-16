package routing

import (
	"context"
	"fmt"
	"strings"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/alert"
	alertredis "github.com/flamegreat/etradie/src/alert/redis"
	"github.com/flamegreat/etradie/src/gateway/internal/constants"
	"github.com/flamegreat/etradie/src/gateway/internal/models"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
	"github.com/flamegreat/etradie/src/gateway/internal/ports"
)

// RouteResult holds the outcome of routing a processor decision.
type RouteResult struct {
	Outcome         constants.CycleOutcome
	GuardResult     *models.GuardEvaluationResult
	ExecutionResult map[string]interface{}
}

// Router routes processor decisions through guards to execution.
type Router struct {
	guards    *GuardEvaluator
	execution ports.ExecutionPort
	transport *alertredis.Transport
	log       zerolog.Logger
}

// NewRouter creates a DecisionRouter.
func NewRouter(guards *GuardEvaluator, execution ports.ExecutionPort, transport *alertredis.Transport) *Router {
	return &Router{
		guards:    guards,
		execution: execution,
		transport: transport,
		log:       observability.Logger("decision_router"),
	}
}

// Route routes the processor decision through guards to execution.
func (r *Router) Route(
	ctx context.Context,
	processorOutput *models.ProcessorOutput,
	taResult *models.TASymbolResult,
	macroResult *models.MacroResult,
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
			Str("symbol", processorOutput.Symbol).
			Str("reason", reason).
			Strs("rejection_rules", processorOutput.RejectionRules).
			Str("trace_id", traceID).
			Msg("route_no_setup")

		return &RouteResult{Outcome: constants.OutcomeNoSetup}
	}

	// Step 2: Run post-processor guards.
	guardResult := r.guards.Evaluate(processorOutput, taResult, macroResult, traceID)

	// Publish guard warnings (non-blocking checks that passed but flagged).
	for _, check := range guardResult.Checks {
		if check.Verdict == constants.VerdictWarn {
			r.transport.Publish(ctx,
				alert.NewEvent(alert.SourceGateway, alert.TypeGuardWarning, alert.SeverityWarning,
					fmt.Sprintf("Guard warning [%s]: %s", check.Rule, check.Reason)).
					WithSymbol(processorOutput.Symbol).
					WithDirection(processorOutput.Direction).
					WithTraceID(traceID).
					WithDetails(map[string]interface{}{
						"rule":     string(check.Rule),
						"reason":   check.Reason,
						"metadata": check.Metadata,
					}),
			)
		}
	}

	// Step 3: If guards reject, block execution.
	if !guardResult.IsApproved() {
		observability.GatewayNoSetupTotal.WithLabelValues("guard_rejection").Inc()
		observability.GatewayStageErrors.WithLabelValues(constants.StageGuardEvaluation.String(), "rejected").Inc()

		r.log.Warn().
			Str("symbol", processorOutput.Symbol).
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

		r.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeGuardRejected, alert.SeverityWarning,
				fmt.Sprintf("Trade rejected by guards: %s", strings.Join(guardResult.BlockingRules, ", "))).
				WithSymbol(processorOutput.Symbol).
				WithDirection(processorOutput.Direction).
				WithTraceID(traceID).
				WithDetails(map[string]interface{}{
					"blocking_rules": guardResult.BlockingRules,
					"reasons":        reasons,
					"confidence":     processorOutput.Confidence,
					"grade":          processorOutput.Grade,
				}),
		)

		return &RouteResult{
			Outcome:     constants.OutcomeRejectedByGuard,
			GuardResult: guardResult,
		}
	}

	// Step 4: Route to execution engine (Module B).
	execResult := r.executeTrade(ctx, processorOutput, traceID)

	symbol := processorOutput.Symbol
	if symbol == "" {
		symbol = "unknown"
	}
	direction := processorOutput.Direction
	if direction == "" {
		direction = "unknown"
	}
	observability.GatewayTradeRouted.WithLabelValues(symbol, direction).Inc()

	r.log.Info().
		Str("symbol", processorOutput.Symbol).
		Str("direction", processorOutput.Direction).
		Float64("confidence", processorOutput.Confidence).
		Str("grade", processorOutput.Grade).
		Str("guard_verdict", string(guardResult.OverallVerdict)).
		Str("trace_id", traceID).
		Msg("route_trade_approved")

	r.transport.Publish(ctx,
		alert.NewEvent(alert.SourceGateway, alert.TypeTradeRouted, alert.SeverityInfo,
			fmt.Sprintf("Trade routed to execution: %s %s (grade: %s, confidence: %.1f%%)",
				symbol, direction, processorOutput.Grade, processorOutput.Confidence*100)).
			WithSymbol(symbol).
			WithDirection(direction).
			WithTraceID(traceID).
			WithDetails(map[string]interface{}{
				"confidence":       processorOutput.Confidence,
				"grade":            processorOutput.Grade,
				"trading_style":    processorOutput.TradingStyle,
				"guard_verdict":    string(guardResult.OverallVerdict),
				"analysis_id":     processorOutput.AnalysisID,
				"execution_result": execResult,
			}),
	)

	return &RouteResult{
		Outcome:         constants.OutcomeTradeApproved,
		GuardResult:     guardResult,
		ExecutionResult: execResult,
	}
}

func (r *Router) executeTrade(
	ctx context.Context,
	decision *models.ProcessorOutput,
	traceID string,
) map[string]interface{} {
	if r.execution == nil {
		r.log.Info().
			Str("symbol", decision.Symbol).
			Str("direction", decision.Direction).
			Str("trace_id", traceID).
			Msg("execution_engine_not_available")
		return map[string]interface{}{"status": "pending", "reason": "execution_engine_not_implemented"}
	}

	result, err := r.execution.Execute(ctx, decision)
	if err != nil {
		observability.GatewayStageErrors.WithLabelValues(constants.StageDecisionRouting.String(), "execution_error").Inc()
		r.log.Error().
			Str("symbol", decision.Symbol).
			Err(err).
			Str("trace_id", traceID).
			Msg("execution_failed")

		r.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeExecutionCallFailed, alert.SeverityError,
				fmt.Sprintf("Execution call failed for %s: %s", decision.Symbol, err.Error())).
				WithSymbol(decision.Symbol).
				WithDirection(decision.Direction).
				WithTraceID(traceID).
				WithDetail("error", err.Error()),
		)

		return map[string]interface{}{"status": "error", "reason": err.Error()}
	}
	return result
}
