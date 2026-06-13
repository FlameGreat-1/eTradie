package pipeline

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"strings"
	"sync"
	"time"

	goredis "github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"
	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/protobuf/encoding/protojson"

	executionv1 "github.com/flamegreat-1/etradie/proto/execution/v1"
	"github.com/flamegreat-1/etradie/src/alert"
	alertredis "github.com/flamegreat-1/etradie/src/alert/redis"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/collectors"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
	ctxpkg "github.com/flamegreat-1/etradie/src/gateway/internal/context"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/ports"
	"github.com/flamegreat-1/etradie/src/gateway/internal/pulse"
	"github.com/flamegreat-1/etradie/src/gateway/internal/querybuilder"
	"github.com/flamegreat-1/etradie/src/gateway/internal/routing"
)

// Orchestrator runs the full analysis pipeline.
type Orchestrator struct {
	cfg            *config.Config
	taCollector    *collectors.TACollector
	macroCollector *collectors.MacroCollector
	queryBuilder   *querybuilder.Builder
	assembler      *ctxpkg.Assembler
	processor      ports.ProcessorPort
	router         *routing.Router
	engineHTTP     *infra.EngineHTTPClient
	transport      *alertredis.Transport
	execution      ports.ExecutionPort
	redisRaw       *goredis.Client // For pulse broadcasting; nil disables.
	log            zerolog.Logger
}

// NewOrchestrator creates a PipelineOrchestrator.
func NewOrchestrator(
	cfg *config.Config,
	taCollector *collectors.TACollector,
	macroCollector *collectors.MacroCollector,
	queryBuilder *querybuilder.Builder,
	assembler *ctxpkg.Assembler,
	processor ports.ProcessorPort,
	router *routing.Router,
	engineHTTP *infra.EngineHTTPClient,
	transport *alertredis.Transport,
	execution ports.ExecutionPort,
	opts ...OrchestratorOption,
) *Orchestrator {
	o := &Orchestrator{
		cfg:            cfg,
		taCollector:    taCollector,
		macroCollector: macroCollector,
		queryBuilder:   queryBuilder,
		assembler:      assembler,
		processor:      processor,
		router:         router,
		engineHTTP:     engineHTTP,
		transport:      transport,
		execution:      execution,
		log:            observability.Logger("orchestrator"),
	}
	for _, opt := range opts {
		opt(o)
	}
	return o
}

// OrchestratorOption configures optional Orchestrator dependencies.
type OrchestratorOption func(*Orchestrator)

// WithRedisRaw enables pulse broadcasting via the given Redis client.
// When not set, the Orchestrator operates normally but without
// emitting real-time status updates to the user's SSE channel.
func WithRedisRaw(client *goredis.Client) OrchestratorOption {
	return func(o *Orchestrator) {
		o.redisRaw = client
	}
}

// RunCycle executes a complete analysis cycle with retry support.
// On timeout or transient failure, the cycle is retried up to
// cfg.MaxCycleRetries times with exponential backoff.
// Panics are recovered but NOT retried (they indicate bugs).
func (o *Orchestrator) RunCycle(ctx context.Context, symbols []string, traceID string) []*models.GatewayOutput {
	var outputs []*models.GatewayOutput

	for attempt := 0; attempt <= o.cfg.MaxCycleRetries; attempt++ {
		if attempt > 0 {
			// Exponential backoff with cap before retrying.
			delay := o.cfg.RetryBackoffBaseSeconds * math.Pow(2, float64(attempt-1))
			if delay > 30.0 {
				delay = 30.0
			}
			o.log.Warn().
				Int("attempt", attempt+1).
				Int("max_retries", o.cfg.MaxCycleRetries).
				Float64("backoff_seconds", delay).
				Strs("symbols", symbols).
				Msg("cycle_retrying")

			o.transport.Publish(ctx,
				alert.NewEvent(alert.SourceGateway, alert.TypeCycleRetrying, alert.SeverityWarning,
					fmt.Sprintf("Cycle retrying attempt %d/%d after %.1fs backoff",
						attempt+1, o.cfg.MaxCycleRetries+1, delay)).
					WithUserID(auth.UserIDFromContext(ctx)).
					WithTraceID(traceID).
					WithDetails(map[string]interface{}{
						"attempt":     attempt + 1,
						"max_retries": o.cfg.MaxCycleRetries,
						"backoff":     delay,
						"symbols":     symbols,
					}),
			)

			select {
			case <-ctx.Done():
				// Parent context cancelled (e.g. shutdown), do not retry.
				o.log.Info().Msg("cycle_retry_cancelled_parent_context_done")
				return outputs
			case <-time.After(time.Duration(delay * float64(time.Second))):
				// Backoff elapsed, proceed with retry.
			}
		}

		result, shouldRetry := o.runSingleAttempt(ctx, symbols, traceID, attempt)
		outputs = result

		if !shouldRetry {
			return outputs
		}
		// shouldRetry is true: loop continues if attempts remain.
	}

	// All retries exhausted. outputs contains the last attempt's result.
	o.log.Error().
		Int("total_attempts", o.cfg.MaxCycleRetries+1).
		Strs("symbols", symbols).
		Msg("cycle_all_retries_exhausted")

	return outputs
}

// runSingleAttempt executes one cycle attempt. Returns the outputs and
// whether the caller should retry (true = retryable failure).
func (o *Orchestrator) runSingleAttempt(
	ctx context.Context,
	symbols []string,
	traceID string,
	attempt int,
) (outputs []*models.GatewayOutput, shouldRetry bool) {
	tracker := NewCycleTracker(traceID)
	observability.GatewayActiveCycles.Inc()

	// Create a scoped logger with trace_id and cycle_id bound for the
	// entire cycle execution. Every log line within this attempt
	// automatically includes both IDs for log correlation.
	cycleLog := observability.WithTraceID(o.log, tracker.TraceID())
	cycleLog = observability.WithCycleID(cycleLog, tracker.CycleID())

	cycleLog.Info().
		Strs("symbols", symbols).
		Int("attempt", attempt+1).
		Msg("cycle_started")

	o.transport.Publish(ctx,
		alert.NewEvent(alert.SourceGateway, alert.TypeCycleStarted, alert.SeverityInfo,
			fmt.Sprintf("Analysis cycle started for %s (attempt %d)",
				strings.Join(symbols, ", "), attempt+1)).
			WithUserID(auth.UserIDFromContext(ctx)).
			WithTraceID(tracker.TraceID()).
			WithDetails(map[string]interface{}{
				"symbols":  symbols,
				"attempt":  attempt + 1,
				"cycle_id": tracker.CycleID(),
				"interval": o.cfg.CycleIntervalSeconds,
			}),
	)

	panicked := false

	func() {
		defer func() {
			if r := recover(); r != nil {
				observability.LogPanicRecovery(cycleLog, r, "run_cycle")
				tracker.Fail(fmt.Sprintf("panic: %v", r), "unhandled", false)
				observability.GatewayStageErrors.WithLabelValues("cycle", "panic").Inc()
				outputs = append(outputs, buildErrorOutput(tracker))
				panicked = true
			}
		}()

		cycleCtx, cancel := context.WithTimeout(ctx, time.Duration(o.cfg.CycleTimeoutSeconds)*time.Second)
		defer cancel()

		result, err := o.executePipeline(cycleCtx, tracker, symbols)
		if err != nil {
			// Parent (inbound request) cancelled -> the client/proxy has
			// gone away. Do NOT retry (that would replay a full,
			// money-spending cycle for a caller that is no longer
			// listening) and do NOT publish a user-facing CYCLE_FAILED
			// alert (there is no user to receive it). This is distinct
			// from the cycle's OWN budget elapsing (cycleCtx
			// DeadlineExceeded with a live parent), which is handled
			// below and remains retryable.
			if ctx.Err() != nil {
				tracker.Fail(
					"Cycle cancelled by caller (client/proxy disconnected)",
					"client_cancelled", false,
				)
				observability.GatewayStageErrors.WithLabelValues("cycle", "cancelled").Inc()
				o.log.Info().
					Str("cycle_id", tracker.CycleID()).
					Str("phase_reached", tracker.Phase().String()).
					Str("trace_id", tracker.TraceID()).
					Msg("cycle_cancelled_by_caller")
				shouldRetry = false
				if len(result) > 0 {
					outputs = append(outputs, result...)
				}
				outputs = append(outputs, buildErrorOutput(tracker))
				return
			}
			if cycleCtx.Err() == context.DeadlineExceeded {
				tracker.Fail(
					fmt.Sprintf("Cycle timed out after %ds", o.cfg.CycleTimeoutSeconds),
					"cycle_timeout", true,
				)
				observability.GatewayStageErrors.WithLabelValues("cycle", "timeout").Inc()
				o.log.Error().
					Str("cycle_id", tracker.CycleID()).
					Int("timeout_seconds", o.cfg.CycleTimeoutSeconds).
					Str("phase_reached", tracker.Phase().String()).
					Str("trace_id", tracker.TraceID()).
					Msg("cycle_timed_out")
				shouldRetry = true

				o.transport.Publish(ctx,
					alert.NewEvent(alert.SourceGateway, alert.TypeCycleFailed, alert.SeverityError,
						fmt.Sprintf("Cycle timed out after %ds (phase: %s)",
							o.cfg.CycleTimeoutSeconds, tracker.Phase().String())).
						WithUserID(auth.UserIDFromContext(ctx)).
						WithTraceID(tracker.TraceID()).
						WithDetails(map[string]interface{}{
							"error":         fmt.Sprintf("timeout after %ds", o.cfg.CycleTimeoutSeconds),
							"phase_reached": tracker.Phase().String(),
							"duration_ms":   tracker.ElapsedMs(),
							"cycle_id":      tracker.CycleID(),
						}),
				)
			} else {
				tracker.Fail(err.Error(), "unhandled", false)
				observability.GatewayStageErrors.WithLabelValues("cycle", "error").Inc()
				o.log.Error().
					Str("cycle_id", tracker.CycleID()).
					Err(err).
					Str("phase_reached", tracker.Phase().String()).
					Str("trace_id", tracker.TraceID()).
					Msg("cycle_unhandled_error")
				shouldRetry = true

				o.transport.Publish(ctx,
					alert.NewEvent(alert.SourceGateway, alert.TypeCycleFailed, alert.SeverityError,
						fmt.Sprintf("Cycle failed: %s (phase: %s)",
							err.Error(), tracker.Phase().String())).
						WithUserID(auth.UserIDFromContext(ctx)).
						WithTraceID(tracker.TraceID()).
						WithDetails(map[string]interface{}{
							"error":         err.Error(),
							"phase_reached": tracker.Phase().String(),
							"duration_ms":   tracker.ElapsedMs(),
							"cycle_id":      tracker.CycleID(),
						}),
				)
			}
			// Preserve any partial results from the pipeline, then append the error.
			if len(result) > 0 {
				outputs = append(outputs, result...)
			}
			outputs = append(outputs, buildErrorOutput(tracker))
			return
		}
		outputs = result
	}()

	observability.GatewayActiveCycles.Dec()
	elapsedS := tracker.ElapsedMs() / 1000
	observability.GatewayCycleDuration.Observe(elapsedS)

	state := tracker.ToState()
	status := string(state.Status)
	outcome := string(state.Outcome)
	if outcome == "" {
		outcome = "unknown"
	}
	observability.GatewayCycleTotal.WithLabelValues(status, outcome).Inc()

	cycleLog.Info().
		Str("status", status).
		Str("outcome", outcome).
		Float64("duration_ms", tracker.ElapsedMs()).
		Int("outputs_count", len(outputs)).
		Int("attempt", attempt+1).
		Bool("will_retry", shouldRetry).
		Msg("cycle_finished")

	// Publish CYCLE_COMPLETED for successful completions (not retrying).
	if !shouldRetry && state.Status == constants.StatusCompleted {
		var processedSymbols []string
		for _, out := range outputs {
			if out.Symbol != "" {
				processedSymbols = append(processedSymbols, out.Symbol)
			}
		}
		o.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeCycleCompleted, alert.SeverityInfo,
				fmt.Sprintf("Cycle completed: %s (%.0fms)", outcome, tracker.ElapsedMs())).
				WithUserID(auth.UserIDFromContext(ctx)).
				WithTraceID(tracker.TraceID()).
				WithDetails(map[string]interface{}{
					"outcome":           outcome,
					"duration_ms":       tracker.ElapsedMs(),
					"symbols_processed": processedSymbols,
					"outputs_count":     len(outputs),
					"cycle_id":          tracker.CycleID(),
				}),
		)
	}

	// Never retry panics - they indicate bugs, not transient failures.
	if panicked {
		shouldRetry = false
	}

	return outputs, shouldRetry
}

func (o *Orchestrator) executePipeline(
	ctx context.Context,
	tracker *CycleTracker,
	symbols []string,
) ([]*models.GatewayOutput, error) {
	traceID := tracker.TraceID()

	// Phase 0: Pre-Pipeline State Filtering & Event-Driven Invalidation
	// Check execution state to prevent redundant analysis for symbols with active trades.
	// For pending orders, validate if the setup still exists; if not, cancel it.
	var filteredSymbols []string
	activeSymbolsMap := make(map[string]bool)

	if o.execution != nil {
		if execState, err := o.execution.GetState(ctx, traceID); err == nil {
			// 1. Filter symbols with open positions (active trades under Management).
			if openPositions, ok := execState["open_positions"].([]*executionv1.OpenPosition); ok {
				for _, op := range openPositions {
					activeSymbolsMap[strings.ToUpper(op.GetSymbol())] = true
				}
			}

			// 2. Filter symbols with pending orders (limit orders or instant-mode watchers).
			// Pending order invalidation is handled by Execution's own watcher, which
			// calls RunConfirmationPulseWithParams with the full structural parameters
			// (OB bounds, direction, LTF/HTF timeframes) needed for the lightweight
			// /internal/ta/confirm_ltf endpoint. That watcher automatically cancels
			// stale orders when the Python engine reports invalidation.
			//
			// We do NOT re-validate pending orders here because:
			//   a) RunConfirmationPulse without LTFConfirmParams falls back to the
			//      full TA pipeline (~5-10s), defeating the zero-waste goal.
			//   b) The PendingOrder proto does not carry the OB/direction/timeframe
			//      params needed for the lightweight fast-path.
			//   c) Execution's watcher already handles this with ~100ms latency.
			if pendingOrders, ok := execState["pending_orders"].([]*executionv1.PendingOrder); ok {
				for _, po := range pendingOrders {
					activeSymbolsMap[strings.ToUpper(po.GetSymbol())] = true
				}
			}
		} else {
			o.log.Warn().Err(err).Str("trace_id", traceID).Msg("failed_to_fetch_execution_state_for_filtering")
		}
	}

	var skippedSymbols []string
	for _, sym := range symbols {
		if activeSymbolsMap[strings.ToUpper(sym)] {
			skippedSymbols = append(skippedSymbols, sym)
		} else {
			filteredSymbols = append(filteredSymbols, sym)
		}
	}

	if len(skippedSymbols) > 0 {
		o.log.Info().
			Strs("skipped_symbols", skippedSymbols).
			Str("trace_id", traceID).
			Msg("phase0_filtered_active_trades")
	}

	if len(filteredSymbols) == 0 {
		tracker.Complete(constants.OutcomeNoSetup)
		o.log.Info().
			Str("cycle_id", tracker.CycleID()).
			Str("trace_id", traceID).
			Msg("cycle_all_symbols_filtered")
		return []*models.GatewayOutput{buildNoDataOutput(tracker)}, nil
	}

	// Phase 1: Parallel TA + Macro collection.
	tracker.TransitionTo(constants.PhaseCollectParallel)
	phaseStart := time.Now()

	// Create a pulse publisher for this user's SSE channel.
	userID := auth.UserIDFromContext(ctx)
	var p *pulse.Publisher
	if o.redisRaw != nil && userID != "" {
		p = pulse.NewPublisher(o.redisRaw, userID, strings.Join(filteredSymbols, ","), o.log)
		p.Emit(ctx, "LOADING", "Preparing scheduled analysis cycle", "gateway", false)
	}

	collectCtx, collectSpan := observability.StartSpan(ctx, "pipeline.collect_parallel",
		attribute.StringSlice("symbols", filteredSymbols),
		attribute.String("trace_id", traceID),
	)

	parallelCtx, parallelCancel := context.WithTimeout(collectCtx, time.Duration(o.cfg.TAMacroParallelTimeoutSeconds)*time.Second)
	defer parallelCancel()

	var taResult *models.TAResult
	var macroResult *models.MacroResult
	var taErr, macroErr error
	var wg sync.WaitGroup

	wg.Add(2)
	go func() {
		defer wg.Done()
		if p != nil {
			p.Emit(parallelCtx, "SHARDING", "Collecting TA candle data", "ta", false)
		}
		taResult, taErr = o.taCollector.Collect(parallelCtx, filteredSymbols, traceID, false)
	}()
	go func() {
		defer wg.Done()
		if p != nil {
			p.Emit(parallelCtx, "CLAUDING", "Collecting macro intelligence", "macro", false)
		}
		macroResult, macroErr = o.macroCollector.Collect(parallelCtx, traceID)
	}()
	wg.Wait()

	if p != nil {
		// Settle the gateway LOADING row (source="gateway") opened above.
		// It is distinct from the engine's per-symbol LOADING row
		// (source="ta"); without this it would stay active forever.
		p.Emit(ctx, "LOADING", "Analysis cycle initialised", "gateway", true)
		// On a cache hit the engine HTTP call was skipped, so its
		// granular pulses never fired. Tell the user the truth (served
		// from cache) rather than implying a full sweep ran. On a cache
		// miss the engine already streamed the granular feed and the
		// normal completion marker is accurate.
		taMsg := "TA data collection complete"
		if taResult != nil && taResult.FromCache {
			taMsg = "TA served from cache (fresh)"
		}
		macroMsg := "Macro intelligence complete"
		if macroResult != nil && macroResult.FromCache {
			macroMsg = "Macro served from cache (fresh)"
		}
		p.Emit(ctx, "SHARDING", taMsg, "ta", true)
		p.Emit(ctx, "CLAUDING", macroMsg, "macro", true)
	}

	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseCollectParallel.String()).Observe(time.Since(phaseStart).Seconds())

	if taErr != nil {
		observability.SetSpanError(collectSpan, taErr)
		collectSpan.End()

		o.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeTACollectionFailed, alert.SeverityError,
				fmt.Sprintf("TA collection failed: %s", taErr.Error())).
				WithUserID(auth.UserIDFromContext(ctx)).
				WithTraceID(traceID).
				WithDetail("error", taErr.Error()),
		)

		return nil, fmt.Errorf("TA collection failed: %w", taErr)
	}
	if macroErr != nil {
		observability.SetSpanError(collectSpan, macroErr)
		collectSpan.End()

		o.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeMacroCollectionFailed, alert.SeverityError,
				fmt.Sprintf("Macro collection failed: %s", macroErr.Error())).
				WithUserID(auth.UserIDFromContext(ctx)).
				WithTraceID(traceID).
				WithDetail("error", macroErr.Error()),
		)

		return nil, fmt.Errorf("Macro collection failed: %w", macroErr)
	}
	collectSpan.End()

	if !taResult.HasCandidates() {
		tracker.Complete(constants.OutcomeInsufficientData)
		successful := taResult.SuccessfulSymbols()
		o.log.Info().
			Str("cycle_id", tracker.CycleID()).
			Int("symbols_analysed", len(taResult.SymbolResults)).
			Strs("successful_symbols", successful).
			Str("trace_id", traceID).
			Msg("cycle_no_candidates")
		return []*models.GatewayOutput{buildNoDataOutput(tracker)}, nil
	}

	// Phase 2-6: Process symbols with candidates concurrently,
	// bounded by MaxConcurrentSymbols.
	var candidateResults []models.TASymbolResult
	for i := range taResult.SymbolResults {
		sr := &taResult.SymbolResults[i]
		if sr.Status != "success" {
			continue
		}
		if len(sr.SMCCandidates) == 0 && len(sr.SnDCandidates) == 0 {
			continue
		}
		candidateResults = append(candidateResults, *sr)
	}

	if len(candidateResults) == 0 {
		tracker.Complete(constants.OutcomeNoSetup)
		return []*models.GatewayOutput{buildNoDataOutput(tracker)}, nil
	}

	// Process symbols concurrently with bounded parallelism.
	var (
		outputsMu sync.Mutex
		outputs   []*models.GatewayOutput
		symWg     sync.WaitGroup
		sem       = make(chan struct{}, o.cfg.MaxConcurrentSymbols)
	)

	for idx := range candidateResults {
		sr := &candidateResults[idx]

		// Check if the cycle context is already cancelled before launching.
		if ctx.Err() != nil {
			o.log.Warn().
				Str("symbol", sr.Symbol).
				Str("trace_id", traceID).
				Msg("cycle_context_cancelled_skipping_symbol")
			break
		}

		symWg.Add(1)
		go func(symResult *models.TASymbolResult) {
			defer symWg.Done()

			// Acquire semaphore slot (bounded concurrency).
			select {
			case sem <- struct{}{}:
				// Slot acquired.
			case <-ctx.Done():
				// Cycle timed out while waiting for a slot.
				o.log.Warn().
					Str("symbol", symResult.Symbol).
					Str("trace_id", traceID).
					Msg("cycle_timeout_waiting_for_semaphore")
				return
			}
			defer func() { <-sem }()

			output := o.processSymbol(ctx, tracker, symResult, macroResult, userID)

			outputsMu.Lock()
			outputs = append(outputs, output)
			outputsMu.Unlock()
		}(sr)
	}

	symWg.Wait()

	if len(outputs) == 0 {
		tracker.Complete(constants.OutcomeNoSetup)
		return []*models.GatewayOutput{buildNoDataOutput(tracker)}, nil
	}

	// Determine overall outcome from collected outputs.
	if len(outputs) == 1 {
		tracker.Complete(outputs[0].CycleOutcome)
	} else {
		// With multiple symbols, use the best outcome.
		bestOutcome := constants.OutcomeNoSetup
		for _, out := range outputs {
			if out.CycleOutcome == constants.OutcomeTradeApproved {
				bestOutcome = constants.OutcomeTradeApproved
				break
			}
		}
		tracker.Complete(bestOutcome)
	}
	return outputs, nil
}

// ConfirmationResult holds the outcome of a targeted TA confirmation pulse.
type ConfirmationResult struct {
	Confirmed       bool
	LTFConfirmation bool
	Reason          string
}

// LTFConfirmParams holds the candidate's structural parameters needed
// for the lightweight LTF confirmation check. Extracted from the
// candidate_id fingerprint or from the Order object.
type LTFConfirmParams struct {
	Symbol       string
	Direction    string
	LTFTimeframe string
	OBUpper      float64
	OBLower      float64
	EntryPrice   float64

	// Invalidation layer fields. When provided, the Python engine runs
	// HTF invalidation checks (OB mitigation, opposing BMS, SL blown)
	// against the exact approved candidate before LTF confirmation.
	StopLoss     float64 // The approved candidate's stop loss level
	HTFTimeframe string  // The HTF timeframe the OB was detected on (e.g. "H4")
}

// RunConfirmationPulse performs a lightweight LTF-only confirmation
// check for a single symbol. Calls the Python engine's dedicated
// /internal/ta/confirm_ltf endpoint which fetches only LTF candles
// and runs only the 7 LTF confirmation checks.
//
// This is the critical fast-path for instant order execution.
// Latency: ~50-200ms (vs 3-10s for full pipeline).
//
// Falls back to the full pipeline if the lightweight endpoint fails.
func (o *Orchestrator) RunConfirmationPulse(
	ctx context.Context,
	symbol string,
	analysisID string,
	traceID string,
) *ConfirmationResult {
	return o.RunConfirmationPulseWithParams(ctx, symbol, analysisID, traceID, nil)
}

// RunConfirmationPulseWithParams performs the lightweight LTF confirmation
// with explicit candidate parameters. When params is non-nil, the
// lightweight endpoint is called directly. When nil, falls back to
// the full pipeline.
func (o *Orchestrator) RunConfirmationPulseWithParams(
	ctx context.Context,
	symbol string,
	analysisID string,
	traceID string,
	params *LTFConfirmParams,
) *ConfirmationResult {
	pulseLog := observability.WithTraceID(o.log, traceID)

	pulseLog.Info().
		Str("symbol", symbol).
		Str("analysis_id", analysisID).
		Bool("has_ltf_params", params != nil).
		Msg("confirmation_pulse_started")

	start := time.Now()

	// News lockout (fire-time, N1): an INSTANT watcher fires a market
	// order the moment this returns Confirmed=true, which may be far
	// later than the decision-time guard ran. Re-check news proximity
	// here against the symbol's own currencies so the irreversible
	// market order never lands inside a high-impact event window. The
	// wider (scalping) window is used unconditionally: extra caution at
	// the fire moment is correct and needs no per-order style on the
	// wire. A non-24/7 symbol with no calendar data fails closed.
	if !routing.Is247Market(symbol) {
		var calendar map[string]interface{}
		if macro, mErr := o.macroCollector.Collect(ctx, traceID); mErr == nil && macro != nil {
			calendar = macro.Calendar
		} else if mErr != nil {
			pulseLog.Warn().Err(mErr).Str("symbol", symbol).Msg("confirmation_pulse_macro_collect_failed_failing_closed")
		}
		news := routing.EvaluateNewsWindow(calendar, symbol, time.Now().UTC(), constants.NewsLockoutMinutesScalping)
		if news.Locked {
			pulseLog.Warn().
				Str("symbol", symbol).
				Str("analysis_id", analysisID).
				Str("reason", news.Reason).
				Bool("data_available", news.DataAvailable).
				Msg("confirmation_pulse_blocked_by_news_lockout")
			return &ConfirmationResult{
				Confirmed:       false,
				LTFConfirmation: false,
				Reason:          "News lockout: " + news.Reason,
			}
		}
	}

	// Kill switch (fire-time): an INSTANT watcher fires the moment this
	// returns Confirmed=true, so a halt engaged after arming must block
	// the confirmation here too. The empty target resolves the caller
	// from the forwarded JWT. Fail-safe: on a read error we fall through
	// (the execution validator and the watcher fire gate stay
	// authoritative) rather than convert a read blip into a stuck order.
	if o.execution != nil {
		if globalHalted, userHalted, herr := o.execution.HaltState(ctx, ""); herr != nil {
			pulseLog.Warn().Err(herr).Str("symbol", symbol).Msg("confirmation_pulse_halt_read_failed_failing_open")
		} else if globalHalted || userHalted {
			scope := "user"
			if globalHalted {
				scope = "global"
			}
			pulseLog.Warn().
				Str("symbol", symbol).
				Str("analysis_id", analysisID).
				Str("scope", scope).
				Msg("confirmation_pulse_blocked_by_kill_switch")
			return &ConfirmationResult{
				Confirmed:       false,
				LTFConfirmation: false,
				Reason:          "Execution halted (" + scope + " kill switch)",
			}
		}
	}

	// Fast path: call lightweight LTF confirmation endpoint
	if params != nil {
		result := o.runLightweightConfirmation(ctx, params, traceID, pulseLog)
		if result != nil {
			elapsed := time.Since(start).Milliseconds()
			pulseLog.Info().
				Str("symbol", symbol).
				Bool("confirmed", result.Confirmed).
				Str("reason", result.Reason).
				Int64("duration_ms", elapsed).
				Str("path", "lightweight").
				Msg("confirmation_pulse_completed")
			return result
		}
		// Lightweight endpoint failed, fall through to full pipeline
		pulseLog.Warn().
			Str("symbol", symbol).
			Msg("lightweight_confirmation_failed_falling_back_to_full_pipeline")
	}

	// Fallback: full pipeline (slow path)
	taResult, err := o.taCollector.Collect(ctx, []string{symbol}, traceID, true)
	if err != nil {
		pulseLog.Error().
			Err(err).
			Str("symbol", symbol).
			Msg("confirmation_pulse_ta_failed")
		return &ConfirmationResult{
			Confirmed: false,
			Reason:    fmt.Sprintf("TA collection failed: %s", err.Error()),
		}
	}

	if !taResult.HasCandidates() {
		pulseLog.Info().
			Str("symbol", symbol).
			Msg("confirmation_pulse_no_candidates")
		return &ConfirmationResult{
			Confirmed: false,
			Reason:    "TA returned no candidates for symbol",
		}
	}

	// Search for the matching candidate across all results.
	for i := range taResult.SymbolResults {
		sr := &taResult.SymbolResults[i]
		if sr.Status != "success" || !strings.EqualFold(sr.Symbol, symbol) {
			continue
		}

		for _, cand := range sr.SMCCandidates {
			if matchesCandidate(cand, analysisID) {
				ltfConfirmed := getBoolField(cand, "ltf_confirmation")
				elapsed := time.Since(start).Milliseconds()
				pulseLog.Info().
					Str("symbol", symbol).
					Str("analysis_id", analysisID).
					Bool("ltf_confirmed", ltfConfirmed).
					Int64("duration_ms", elapsed).
					Str("framework", "SMC").
					Str("path", "full_pipeline").
					Msg("confirmation_pulse_candidate_found")
				return &ConfirmationResult{
					Confirmed:       ltfConfirmed,
					LTFConfirmation: ltfConfirmed,
					Reason:          condReason(ltfConfirmed, "SMC LTF confirmation met", "SMC LTF confirmation not yet met"),
				}
			}
		}

		for _, cand := range sr.SnDCandidates {
			if matchesCandidate(cand, analysisID) {
				ltfConfirmed := getBoolField(cand, "ltf_confirmation")
				elapsed := time.Since(start).Milliseconds()
				pulseLog.Info().
					Str("symbol", symbol).
					Str("analysis_id", analysisID).
					Bool("ltf_confirmed", ltfConfirmed).
					Int64("duration_ms", elapsed).
					Str("framework", "SnD").
					Str("path", "full_pipeline").
					Msg("confirmation_pulse_candidate_found")
				return &ConfirmationResult{
					Confirmed:       ltfConfirmed,
					LTFConfirmation: ltfConfirmed,
					Reason:          condReason(ltfConfirmed, "SnD LTF confirmation met", "SnD LTF confirmation not yet met"),
				}
			}
		}
	}

	pulseLog.Warn().
		Str("symbol", symbol).
		Str("analysis_id", analysisID).
		Int("smc_candidates_total", taResult.TotalSMCCandidates()).
		Int("snd_candidates_total", taResult.TotalSnDCandidates()).
		Msg("confirmation_pulse_candidate_not_found")

	return &ConfirmationResult{
		Confirmed: false,
		Reason:    fmt.Sprintf("candidate %s not found in TA results", analysisID),
	}
}

// CheckNewsWindow reports whether `symbol` must be locked out now
// because a high-impact event affecting one of its currencies
// activates within the style-aware lockout window. Backs the
// GatewayService.CheckNewsWindow RPC used by the execution watcher's
// LIMIT TTL loop. Reuses the cached macro calendar and the shared
// evaluator so policy is identical to the decision-time guard and the
// INSTANT fire-time gate.
func (o *Orchestrator) CheckNewsWindow(
	ctx context.Context,
	symbol string,
	tradingStyle string,
	traceID string,
) routing.NewsWindowStatus {
	if routing.Is247Market(symbol) {
		return routing.NewsWindowStatus{Locked: false, DataAvailable: true, Reason: "Symbol has no fiat calendar exposure"}
	}

	var calendar map[string]interface{}
	if macro, err := o.macroCollector.Collect(ctx, traceID); err == nil && macro != nil {
		calendar = macro.Calendar
	} else if err != nil {
		o.log.Warn().Err(err).Str("symbol", symbol).Str("trace_id", traceID).Msg("check_news_window_macro_collect_failed_failing_closed")
	}

	lockout := routing.LockoutMinutesForStyle(tradingStyle)
	return routing.EvaluateNewsWindow(calendar, symbol, time.Now().UTC(), lockout)
}

// runLightweightConfirmation calls the Python engine's dedicated
// /internal/ta/confirm_ltf endpoint. Returns nil if the call fails
// (caller should fall back to full pipeline).
func (o *Orchestrator) runLightweightConfirmation(
	ctx context.Context,
	params *LTFConfirmParams,
	traceID string,
	log zerolog.Logger,
) *ConfirmationResult {
	reqBody := map[string]interface{}{
		"symbol":        params.Symbol,
		"direction":     params.Direction,
		"ltf_timeframe": params.LTFTimeframe,
		"ob_upper":      params.OBUpper,
		"ob_lower":      params.OBLower,
		"entry_price":   params.EntryPrice,
		"trace_id":      traceID,
	}

	// Attach invalidation layer fields when available.
	if params.StopLoss > 0 {
		reqBody["stop_loss"] = params.StopLoss
	}
	if params.HTFTimeframe != "" {
		reqBody["htf_timeframe"] = params.HTFTimeframe
	}

	resp, err := o.engineHTTP.PostJSON(ctx, "/internal/ta/confirm_ltf", reqBody)
	if err != nil {
		log.Warn().
			Err(err).
			Str("symbol", params.Symbol).
			Msg("lightweight_ltf_confirmation_http_failed")
		return nil
	}

	confirmed := getBoolField(resp, "confirmed")
	errMsg, _ := resp["error"].(string)

	if errMsg != "" {
		log.Warn().
			Str("symbol", params.Symbol).
			Str("error", errMsg).
			Msg("lightweight_ltf_confirmation_returned_error")
		return nil
	}

	// Extract individual check results for logging
	checks, _ := resp["checks"].(map[string]interface{})
	durationMs, _ := resp["duration_ms"].(float64)

	log.Info().
		Str("symbol", params.Symbol).
		Bool("confirmed", confirmed).
		Float64("engine_duration_ms", durationMs).
		Interface("checks", checks).
		Msg("lightweight_ltf_confirmation_result")

	// Check if the setup was invalidated by the HTF layer.
	invalidated := getBoolField(resp, "invalidated")
	if invalidated {
		invReason, _ := resp["invalidation_reason"].(string)
		if invReason == "" {
			invReason = "Setup invalidated on HTF"
		}
		log.Warn().
			Str("symbol", params.Symbol).
			Str("invalidation_reason", invReason).
			Msg("lightweight_confirmation_setup_invalidated")
		return &ConfirmationResult{
			Confirmed:       false,
			LTFConfirmation: false,
			Reason:          invReason,
		}
	}

	reason := "LTF confirmation not yet met"
	if confirmed {
		reason = "LTF confirmation met (lightweight fast-path)"
	}

	return &ConfirmationResult{
		Confirmed:       confirmed,
		LTFConfirmation: confirmed,
		Reason:          reason,
	}
}

func getBoolField(m map[string]interface{}, key string) bool {
	v, ok := m[key]
	if !ok || v == nil {
		return false
	}
	b, ok := v.(bool)
	if ok {
		return b
	}
	// JSON numbers: some JSON decoders produce float64 for booleans.
	if f, ok := v.(float64); ok {
		return f != 0
	}
	return false
}

func getFloat64Field(m map[string]interface{}, key string) float64 {
	v, ok := m[key]
	if !ok || v == nil {
		return 0
	}
	if f, ok := v.(float64); ok {
		return f
	}
	// Integers from some sources
	if i, ok := v.(int); ok {
		return float64(i)
	}
	return 0
}

func getStringField(m map[string]interface{}, key string) string {
	v, ok := m[key]
	if !ok || v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

// matchesCandidate checks if a candidate map matches the given analysisID.
// Priority: candidate_id > analysis_id > id > structural fingerprint.
func matchesCandidate(cand map[string]interface{}, analysisID string) bool {
	// Primary: candidate_id (deterministic fingerprint from TA engine)
	if candID, _ := cand["candidate_id"].(string); candID != "" && candID == analysisID {
		return true
	}
	// Fallback: analysis_id
	if candID, _ := cand["analysis_id"].(string); candID != "" && candID == analysisID {
		return true
	}
	// Fallback: id
	if candID, _ := cand["id"].(string); candID != "" && candID == analysisID {
		return true
	}
	// Structural fingerprint match: the analysisID may be a candidate_id
	// format (SYMBOL_PATTERN_DIRECTION_PRICE). Reconstruct from candidate
	// fields and compare.
	fingerprint := buildCandidateFingerprint(cand)
	if fingerprint != "" && fingerprint == analysisID {
		return true
	}
	return false
}

// buildCandidateFingerprint reconstructs the deterministic fingerprint
// from a candidate's structural fields. Matches the Python candidate_id
// format: SYMBOL_PATTERN_DIRECTION_ENTRYPRICE(4dp)
func buildCandidateFingerprint(cand map[string]interface{}) string {
	symbol, _ := cand["symbol"].(string)
	pattern, _ := cand["pattern"].(string)
	direction, _ := cand["direction"].(string)
	entryPrice, _ := cand["entry_price"].(float64)

	if symbol == "" || pattern == "" || direction == "" || entryPrice == 0 {
		return ""
	}

	return fmt.Sprintf("%s_%s_%s_%.4f", symbol, pattern, direction, entryPrice)
}

func condReason(cond bool, ifTrue, ifFalse string) string {
	if cond {
		return ifTrue
	}
	return ifFalse
}

// isInsufficientData reports whether a processor error represents the
// engine's benign "insufficient_data" condition (empty RAG retrieval,
// empty TA, or no SMC/SnD candidates) rather than a genuine LLM failure.
//
// The engine's /internal/processor/process handler returns HTTP 400 with
// the JSON contract body {"error":"insufficient_data", ...}. The gateway's
// EngineHTTPClient embeds that (redacted, truncated) body into the error
// string. The token "insufficient_data" is the engine-side contract value,
// is short and non-sensitive (so it survives redaction + the 200-char
// truncation), and never appears in genuine LLM-failure errors (timeout,
// provider quota, schema violation, truncation), so the match is
// deterministic with no false positives.
func isInsufficientData(err error) bool {
	if err == nil {
		return false
	}
	return strings.Contains(strings.ToLower(err.Error()), "insufficient_data")
}

func (o *Orchestrator) processSymbol(
	ctx context.Context,
	tracker *CycleTracker,
	symResult *models.TASymbolResult,
	macroResult *models.MacroResult,
	userID string,
) *models.GatewayOutput {
	traceID := tracker.TraceID()
	symbol := symResult.Symbol

	// Per-symbol pulse publisher for the Thinking Terminal. nil when
	// pulse broadcasting is disabled or the user is unknown; pulse.Emit
	// is nil-safe so every call below is a no-op in that case.
	var sp *pulse.Publisher
	if o.redisRaw != nil && userID != "" {
		sp = pulse.NewPublisher(o.redisRaw, userID, symbol, o.log)
	}

	effectiveMacroResult := macroResult
	if routing.Is247Market(symbol) {
		effectiveMacroResult = nil
	}

	// Phase 2: Build RAG query.
	phaseStart := time.Now()
	_, qbSpan := observability.StartSpan(ctx, "pipeline.build_query",
		attribute.String("symbol", symbol),
	)
	queryParams := o.queryBuilder.Build(symResult, effectiveMacroResult, "", traceID)
	qbSpan.End()
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseBuildingQuery.String()).Observe(time.Since(phaseStart).Seconds())

	// Phase 3: RAG retrieval.
	phaseStart = time.Now()

	sp.Emit(ctx, "GERMINATING", "Retrieving rulebook knowledge", "rag", false)

	ragCtx, ragCancel := context.WithTimeout(ctx, time.Duration(o.cfg.RAGTimeoutSeconds)*time.Second)
	defer ragCancel()
	ragCtx, ragSpan := observability.StartSpan(ragCtx, "pipeline.rag_retrieval",
		attribute.String("symbol", symbol),
		attribute.String("strategy", queryParams.Strategy),
	)

	ragBundle, err := o.retrieveRAG(ragCtx, queryParams, traceID)
	ragElapsed := time.Since(phaseStart).Seconds()
	observability.GatewayRAGDuration.Observe(ragElapsed)
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseRetrievingRAG.String()).Observe(ragElapsed)

	if err != nil {
		observability.SetSpanError(ragSpan, err)
		ragSpan.End()
		observability.GatewayStageErrors.WithLabelValues(constants.StageRAGRetrieval.String(), "error").Inc()

		o.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeRAGRetrievalFailed, alert.SeverityError,
				fmt.Sprintf("RAG retrieval failed for %s: %s", symbol, err.Error())).
				WithUserID(auth.UserIDFromContext(ctx)).
				WithSymbol(symbol).
				WithTraceID(traceID).
				WithDetail("error", err.Error()),
		)

		return buildSymbolErrorOutput(tracker, symbol, err)
	}
	ragSpan.End()

	// Phase 4: Assemble context.
	phaseStart = time.Now()
	_, asmSpan := observability.StartSpan(ctx, "pipeline.assemble_context",
		attribute.String("symbol", symbol),
	)
	processorInput := o.assembler.Assemble(symbol, symResult, effectiveMacroResult, ragBundle, traceID)
	asmSpan.End()
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseAssemblingCtx.String()).Observe(time.Since(phaseStart).Seconds())

	// Phase 4b: Pre-LLM deterministic guards.
	//
	// The 4 LLM-independent guards (MR-REJECT-001/002/008/009) run here
	// so a guaranteed rejection (e.g. Asian session restriction on a
	// non-Asian pair) short-circuits the cycle before spending ~168k
	// input tokens on a processor LLM call whose result will be
	// discarded. The pre-LLM result is threaded into router.Route
	// after the LLM completes so the deterministic checks are NOT
	// re-evaluated; only the LLM-dependent MR-REJECT-006 runs there.
	phaseStart = time.Now()
	preLLMRoute := o.router.RoutePreLLM(ctx, symbol, symResult, effectiveMacroResult, traceID)
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseEvaluatingGuards.String()).Observe(time.Since(phaseStart).Seconds())
	if preLLMRoute.Outcome == constants.OutcomeRejectedByGuard {
		// Publish ANALYSIS_COMPLETE with trade_valid=false so the SPA
		// surfaces the rejected cycle in the analysis feed exactly
		// like a post-LLM guard rejection.
		o.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeAnalysisComplete, alert.SeverityInfo,
				fmt.Sprintf("Analysis complete for %s: rejected by pre-LLM guards", symbol)).
				WithUserID(auth.UserIDFromContext(ctx)).
				WithSymbol(symbol).
				WithTraceID(traceID).
				WithDetails(map[string]interface{}{
					"trade_valid":    false,
					"blocking_rules": preLLMRoute.GuardResult.BlockingRules,
					"phase":          "pre_llm",
				}),
		)

		// Fire-and-forget runcycle debug dump. Only TA + macro + RAG
		// payloads carry data; processor_data and execution_request are
		// omitted because no LLM call ran and no execution request was
		// built. The engine handler accepts nil/empty values for those
		// fields and writes only the populated files.
		go func() { // #nosec G118
			debugCtx, debugCancel := context.WithTimeout(context.Background(), 10*time.Second) // #nosec G114 -- intentionally detached from request context; this is fire-and-forget debug persistence.
			defer debugCancel()
			if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
				debugCtx = auth.InjectTokenIntoContext(debugCtx, rawToken)
			}
			debugBody := map[string]interface{}{
				"symbol":     symbol,
				"ta_data":    processorInput.TAAnalysis,
				"macro_data": processorInput.MacroAnalysis,
				"rag_data":   processorInput.RetrievedKnowledge,
				"trace_id":   traceID,
			}
			if _, debugErr := o.engineHTTP.PostJSON(debugCtx, "/internal/debug/runcycle", debugBody); debugErr != nil {
				o.log.Debug().
					Err(debugErr).
					Str("symbol", symbol).
					Str("trace_id", traceID).
					Msg("debug_runcycle_output_failed")
			}
		}()

		return &models.GatewayOutput{
			CycleStatus:  constants.StatusCompleted,
			CycleOutcome: constants.OutcomeRejectedByGuard,
			PhaseReached: constants.PhaseCompleted,
			Symbol:       symbol,
			GuardResult:  preLLMRoute.GuardResult,
			DurationMs:   tracker.ElapsedMs(),
			TraceID:      traceID,
		}
	}

	// Phase 5: Processor LLM.
	phaseStart = time.Now()

	sp.Emit(ctx, "REASONING", "Engaging AI processor", "processor", false)

	procCtx, procCancel := context.WithTimeout(ctx, time.Duration(o.cfg.ProcessorTimeoutSeconds)*time.Second)
	defer procCancel()
	procCtx, procSpan := observability.StartSpan(procCtx, "pipeline.processor_llm",
		attribute.String("symbol", symbol),
	)

	processorOutput, err := o.processor.Process(procCtx, processorInput)
	procElapsed := time.Since(phaseStart).Seconds()
	observability.GatewayProcessorDuration.Observe(procElapsed)
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseProcessingLLM.String()).Observe(procElapsed)

	if err != nil {
		observability.SetSpanError(procSpan, err)
		procSpan.End()

		// Insufficient-data is a benign, expected per-symbol condition
		// (empty RAG retrieval, empty TA, or no SMC/SnD candidates), NOT
		// an LLM failure: the engine returns HTTP 400 with the stable
		// contract value {"error":"insufficient_data"} and the LLM is
		// never called. Surfacing it as PROCESSOR_LLM_FAILED/SeverityError
		// and marking the symbol PIPELINE_ERROR mislabels a no-data result,
		// over-alarms the user, and pollutes the failure metrics. Route it
		// like the pre-LLM guard path: an informational ANALYSIS_COMPLETE
		// (trade_valid=false) plus a benign OutcomeInsufficientData output.
		// The engine independently counts the precise reason via
		// etradie_processor_insufficient_data_total{reason}.
		if isInsufficientData(err) {
			observability.GatewayNoSetupTotal.WithLabelValues("insufficient_data").Inc()

			o.transport.Publish(ctx,
				alert.NewEvent(alert.SourceGateway, alert.TypeAnalysisComplete, alert.SeverityInfo,
					fmt.Sprintf("Analysis complete for %s: insufficient data (no setup)", symbol)).
					WithUserID(auth.UserIDFromContext(ctx)).
					WithSymbol(symbol).
					WithTraceID(traceID).
					WithDetails(map[string]interface{}{
						"trade_valid": false,
						"reason":      "insufficient_data",
					}),
			)

			o.log.Info().
				Str("symbol", symbol).
				Str("trace_id", traceID).
				Msg("processor_insufficient_data_no_setup")

			return &models.GatewayOutput{
				CycleStatus:  constants.StatusCompleted,
				CycleOutcome: constants.OutcomeInsufficientData,
				PhaseReached: constants.PhaseCompleted,
				Symbol:       symbol,
				DurationMs:   tracker.ElapsedMs(),
				TraceID:      traceID,
			}
		}

		observability.GatewayStageErrors.WithLabelValues(constants.StageProcessorLLM.String(), "error").Inc()

		o.transport.Publish(ctx,
			alert.NewEvent(alert.SourceGateway, alert.TypeProcessorLLMFailed, alert.SeverityError,
				fmt.Sprintf("Processor LLM failed for %s: %s", symbol, err.Error())).
				WithUserID(auth.UserIDFromContext(ctx)).
				WithSymbol(symbol).
				WithTraceID(traceID).
				WithDetail("error", err.Error()),
		)

		return buildSymbolErrorOutput(tracker, symbol, err)
	}
	procSpan.End()

	// Inject candidate structural parameters into processorOutput for Execution.
	// The LLM does not return these directly (to save tokens/prompt complexity),
	// so we extract them from the matching TA candidate here.
	if processorOutput.TradeValid && processorOutput.AnalysisID != "" {
		for _, cand := range symResult.SMCCandidates {
			if matchesCandidate(cand, processorOutput.AnalysisID) {
				processorOutput.LTFTimeframe = getStringField(cand, "ltf_timeframe")
				processorOutput.HTFTimeframe = getStringField(cand, "htf_timeframe")
				processorOutput.OBUpper = getFloat64Field(cand, "order_block_upper")
				processorOutput.OBLower = getFloat64Field(cand, "order_block_lower")
				break
			}
		}
		for _, cand := range symResult.SnDCandidates {
			if matchesCandidate(cand, processorOutput.AnalysisID) {
				processorOutput.LTFTimeframe = getStringField(cand, "ltf_timeframe")
				processorOutput.HTFTimeframe = getStringField(cand, "htf_timeframe")

				// SnDCandidate carries its zone as supply_zone_* (bearish)
				// or demand_zone_* (bullish); a candidate populates only
				// one. Resolve supply-first to mirror the Python model's
				// to_technical_candidate() so the LTF fast-path receives
				// real bounds instead of zeros.
				upper := getFloat64Field(cand, "supply_zone_upper")
				if upper == 0 {
					upper = getFloat64Field(cand, "demand_zone_upper")
				}
				lower := getFloat64Field(cand, "supply_zone_lower")
				if lower == 0 {
					lower = getFloat64Field(cand, "demand_zone_lower")
				}

				processorOutput.OBUpper = upper
				processorOutput.OBLower = lower
				break
			}
		}
	}

	// Publish ANALYSIS_COMPLETE: processor returned a decision for this symbol.
	analysisMsg := fmt.Sprintf("Analysis complete for %s: trade_valid=%t", symbol, processorOutput.TradeValid)
	analysisDetails := map[string]interface{}{
		"trade_valid": processorOutput.TradeValid,
		"confidence":  processorOutput.Confidence,
		"grade":       processorOutput.Grade,
	}
	if processorOutput.TradeValid {
		analysisMsg = fmt.Sprintf("Analysis complete for %s: %s %s (grade: %s, confidence: %.1f%%)",
			symbol, processorOutput.Direction, processorOutput.Symbol,
			processorOutput.Grade, processorOutput.Confidence*100)
		analysisDetails["direction"] = processorOutput.Direction
		analysisDetails["trading_style"] = processorOutput.TradingStyle
	}
	o.transport.Publish(ctx,
		alert.NewEvent(alert.SourceGateway, alert.TypeAnalysisComplete, alert.SeverityInfo, analysisMsg).
			WithUserID(auth.UserIDFromContext(ctx)).
			WithSymbol(symbol).
			WithDirection(processorOutput.Direction).
			WithTraceID(traceID).
			WithDetails(analysisDetails),
	)

	// Fire-and-forget: persist pipeline data to /output/runcycle/ for debugging.
	// Runs in a background goroutine so it NEVER blocks the pipeline.
	// Uses processorInput (assembled TA + Macro + RAG) plus processorOutput.
	go func() { // #nosec G118
		debugCtx, debugCancel := context.WithTimeout(context.Background(), 10*time.Second) // #nosec G114 -- intentionally detached from request context; this is fire-and-forget debug persistence.
		defer debugCancel()

		// Carry the auth token so the engine can authenticate the request.
		if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
			debugCtx = auth.InjectTokenIntoContext(debugCtx, rawToken)
		}

		// Build the processor output as a map for JSON serialization.
		procMap := map[string]interface{}{
			"trade_valid":      processorOutput.TradeValid,
			"direction":        processorOutput.Direction,
			"symbol":           processorOutput.Symbol,
			"confidence":       processorOutput.Confidence,
			"grade":            processorOutput.Grade,
			"reasoning":        processorOutput.Reasoning,
			"rejection_rules":  processorOutput.RejectionRules,
			"raw_response":     processorOutput.RawResponse,
			"trading_style":    processorOutput.TradingStyle,
			"session":          processorOutput.Session,
			"confluence_score": processorOutput.ConfluenceScore,
			"analysis_id":      processorOutput.AnalysisID,
			"execution_mode":   processorOutput.ExecutionMode,
			"ltf_confirmed":    processorOutput.LTFConfirmed,
			"setup_type":       processorOutput.SetupType,
		}
		if processorOutput.EntryPrice != nil {
			procMap["entry_price"] = *processorOutput.EntryPrice
		}
		if processorOutput.StopLoss != nil {
			procMap["stop_loss"] = *processorOutput.StopLoss
		}
		if processorOutput.TakeProfit != nil {
			procMap["take_profit"] = *processorOutput.TakeProfit
		}
		if processorOutput.RRRatio != nil {
			procMap["rr_ratio"] = *processorOutput.RRRatio
		}
		if processorOutput.RiskPercentage != nil {
			procMap["risk_percentage"] = *processorOutput.RiskPercentage
		}

		// EXACTLY what the execution receives:
		execReq := infra.BuildExecuteRequest(processorOutput)
		var execMap map[string]interface{}
		if execJs, err := (protojson.MarshalOptions{UseProtoNames: true, EmitUnpopulated: true}).Marshal(execReq); err == nil {
			_ = json.Unmarshal(execJs, &execMap)
		}

		debugBody := map[string]interface{}{
			"symbol":            symbol,
			"ta_data":           processorInput.TAAnalysis,
			"macro_data":        processorInput.MacroAnalysis,
			"rag_data":          processorInput.RetrievedKnowledge,
			"processor_data":    procMap,
			"execution_request": execMap,
			"trace_id":          traceID,
		}

		_, debugErr := o.engineHTTP.PostJSON(debugCtx, "/internal/debug/runcycle", debugBody)
		if debugErr != nil {
			o.log.Debug().
				Err(debugErr).
				Str("symbol", symbol).
				Str("trace_id", traceID).
				Msg("debug_runcycle_output_failed")
		} else {
			o.log.Debug().
				Str("symbol", symbol).
				Str("trace_id", traceID).
				Msg("debug_runcycle_output_saved")
		}
	}()

	// Phase 6: Guards + Routing.
	phaseStart = time.Now()
	sp.Emit(ctx, "ACTIONING", "Evaluating guards & routing decision", "processor", false)
	routeCtx, routeSpan := observability.StartSpan(ctx, "pipeline.guards_and_routing",
		attribute.String("symbol", symbol),
		attribute.Bool("trade_valid", processorOutput.TradeValid),
	)

	routeResult := o.router.Route(routeCtx, processorOutput, symResult, macroResult, preLLMRoute.GuardResult, traceID)
	routeSpan.End()
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseEvaluatingGuards.String()).Observe(time.Since(phaseStart).Seconds())

	// Terminal ACTIONING marker reporting the REAL pipeline outcome
	// after routing/execution ran. Without this the terminal appeared
	// to end at "Evaluating guards & routing decision" with no sign of
	// the decision. The outcome string is the gateway's own
	// constants.Outcome* value (trade_approved / rejected_by_guard /
	// no_setup / insufficient_data / pipeline_error).
	sp.Emit(ctx, "ACTIONING", fmt.Sprintf("Cycle complete: %s", routeResult.Outcome), "processor", true)

	return &models.GatewayOutput{
		CycleStatus:     constants.StatusCompleted,
		CycleOutcome:    routeResult.Outcome,
		PhaseReached:    constants.PhaseCompleted,
		Symbol:          symbol,
		ProcessorOutput: processorOutput,
		GuardResult:     routeResult.GuardResult,
		ExecutionResult: routeResult.ExecutionResult,
		DurationMs:      tracker.ElapsedMs(),
		TraceID:         traceID,
	}
}

func (o *Orchestrator) retrieveRAG(
	ctx context.Context,
	params *models.RAGQueryParams,
	traceID string,
) (map[string]interface{}, error) {
	reqBody := map[string]interface{}{
		"query_text":            params.QueryText,
		"strategy":              params.Strategy,
		"framework":             params.Framework,
		"setup_family":          params.SetupFamily,
		"direction":             params.Direction,
		"timeframe":             params.Timeframe,
		"style":                 params.Style,
		"symbol":                params.Symbol,
		"all_frameworks":        params.AllFrameworks,
		"all_setup_families":    params.AllSetupFamilies,
		"has_smc_candidates":    params.HasSMCCandidates,
		"has_snd_candidates":    params.HasSnDCandidates,
		"has_macro_data":        params.HasMacroData,
		"has_cot_data":          params.HasCOTData,
		"has_rate_decision":     params.HasRateDecision,
		"has_high_impact_event": params.HasHighImpactEvent,
		"has_dxy_data":          params.HasDXYData,

		// Enriched macro signal fields — match Python InternalRAGRequest.
		"has_qe_qt":                     params.HasQEQT,
		"has_stagflation":               params.HasStagflation,
		"has_cot_extremes":              params.HasCOTExtremes,
		"has_tff_data":                  params.HasTFFData,
		"has_core_inflation":            params.HasCoreInflation,
		"has_safe_haven_elevated":       params.HasSafeHavenElevated,
		"has_commodity_currencies_weak": params.HasCommodityCurrenciesWeak,
		"dxy_momentum":                  params.DXYMomentum,
		"risk_environment":              params.RiskEnvironment,

		"trace_id": traceID,
	}

	bundle, err := o.engineHTTP.PostJSON(ctx, "/internal/rag/retrieve", reqBody)
	if err != nil {
		return nil, fmt.Errorf("RAG retrieval failed: %w", err)
	}
	if bundle == nil {
		bundle = make(map[string]interface{})
	}
	return bundle, nil
}

func buildErrorOutput(tracker *CycleTracker) *models.GatewayOutput {
	state := tracker.ToState()
	outcome := state.Outcome
	if outcome == "" {
		outcome = constants.OutcomePipelineError
	}
	return &models.GatewayOutput{
		CycleStatus:  state.Status,
		CycleOutcome: outcome,
		PhaseReached: state.Phase,
		DurationMs:   tracker.ElapsedMs(),
		TraceID:      tracker.TraceID(),
		Error:        state.Error,
		ErrorStage:   state.ErrorStage,
	}
}

func buildNoDataOutput(tracker *CycleTracker) *models.GatewayOutput {
	// Read the outcome from the tracker so the output matches what was
	// recorded by the caller (OutcomeInsufficientData vs OutcomeNoSetup).
	outcome := tracker.Outcome()
	if outcome == "" {
		outcome = constants.OutcomeInsufficientData
	}
	return &models.GatewayOutput{
		CycleStatus:  constants.StatusCompleted,
		CycleOutcome: outcome,
		PhaseReached: constants.PhaseCompleted,
		DurationMs:   tracker.ElapsedMs(),
		TraceID:      tracker.TraceID(),
	}
}

func buildSymbolErrorOutput(tracker *CycleTracker, symbol string, err error) *models.GatewayOutput {
	return &models.GatewayOutput{
		CycleStatus:  constants.StatusFailed,
		CycleOutcome: constants.OutcomePipelineError,
		PhaseReached: tracker.Phase(),
		Symbol:       symbol,
		DurationMs:   tracker.ElapsedMs(),
		TraceID:      tracker.TraceID(),
		Error:        err.Error(),
		ErrorStage:   tracker.Phase().String(),
	}
}
