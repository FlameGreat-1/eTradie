package pipeline

import (
	"context"
	"fmt"
	"math"
	"sync"
	"time"

	"github.com/rs/zerolog"
	"go.opentelemetry.io/otel/attribute"

	"github.com/flamegreat/etradie/src/gateway/internal/collectors"
	"github.com/flamegreat/etradie/src/gateway/internal/config"
	"github.com/flamegreat/etradie/src/gateway/internal/constants"
	ctxpkg "github.com/flamegreat/etradie/src/gateway/internal/context"
	"github.com/flamegreat/etradie/src/gateway/internal/infra"
	"github.com/flamegreat/etradie/src/gateway/internal/models"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
	"github.com/flamegreat/etradie/src/gateway/internal/ports"
	"github.com/flamegreat/etradie/src/gateway/internal/querybuilder"
	"github.com/flamegreat/etradie/src/gateway/internal/routing"
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
) *Orchestrator {
	return &Orchestrator{
		cfg:            cfg,
		taCollector:    taCollector,
		macroCollector: macroCollector,
		queryBuilder:   queryBuilder,
		assembler:      assembler,
		processor:      processor,
		router:         router,
		engineHTTP:     engineHTTP,
		log:            observability.Logger("orchestrator"),
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

	o.log.Info().
		Str("cycle_id", tracker.CycleID()).
		Strs("symbols", symbols).
		Int("attempt", attempt+1).
		Str("trace_id", tracker.TraceID()).
		Msg("cycle_started")

	panicked := false

	func() {
		defer func() {
			if r := recover(); r != nil {
				observability.LogPanicRecovery(o.log, r, "run_cycle")
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

	o.log.Info().
		Str("cycle_id", tracker.CycleID()).
		Str("status", status).
		Str("outcome", outcome).
		Float64("duration_ms", tracker.ElapsedMs()).
		Int("outputs_count", len(outputs)).
		Int("attempt", attempt+1).
		Bool("will_retry", shouldRetry).
		Str("trace_id", tracker.TraceID()).
		Msg("cycle_finished")

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

	// Phase 1: Parallel TA + Macro collection.
	tracker.TransitionTo(constants.PhaseCollectParallel)
	phaseStart := time.Now()

	collectCtx, collectSpan := observability.StartSpan(ctx, "pipeline.collect_parallel",
		attribute.StringSlice("symbols", symbols),
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
		taResult, taErr = o.taCollector.Collect(parallelCtx, symbols, traceID)
	}()
	go func() {
		defer wg.Done()
		macroResult, macroErr = o.macroCollector.Collect(parallelCtx, traceID)
	}()
	wg.Wait()

	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseCollectParallel.String()).Observe(time.Since(phaseStart).Seconds())

	if taErr != nil {
		observability.SetSpanError(collectSpan, taErr)
		collectSpan.End()
		return nil, fmt.Errorf("TA collection failed: %w", taErr)
	}
	if macroErr != nil {
		observability.SetSpanError(collectSpan, macroErr)
		collectSpan.End()
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

			output := o.processSymbol(ctx, tracker, symResult, macroResult)

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

func (o *Orchestrator) processSymbol(
	ctx context.Context,
	tracker *CycleTracker,
	symResult *models.TASymbolResult,
	macroResult *models.MacroResult,
) *models.GatewayOutput {
	traceID := tracker.TraceID()
	symbol := symResult.Symbol

	// Phase 2: Build RAG query.
	phaseStart := time.Now()
	qbCtx, qbSpan := observability.StartSpan(ctx, "pipeline.build_query",
		attribute.String("symbol", symbol),
	)
	queryParams := o.queryBuilder.Build(symResult, macroResult, "", traceID)
	qbSpan.End()
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseBuildingQuery.String()).Observe(time.Since(phaseStart).Seconds())
	_ = qbCtx // context not needed downstream for query building

	// Phase 3: RAG retrieval.
	phaseStart = time.Now()

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
		return buildSymbolErrorOutput(tracker, symbol, err)
	}
	ragSpan.End()

	// Phase 4: Assemble context.
	phaseStart = time.Now()
	_, asmSpan := observability.StartSpan(ctx, "pipeline.assemble_context",
		attribute.String("symbol", symbol),
	)
	processorInput := o.assembler.Assemble(symbol, symResult, macroResult, ragBundle, traceID)
	asmSpan.End()
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseAssemblingCtx.String()).Observe(time.Since(phaseStart).Seconds())

	// Phase 5: Processor LLM.
	phaseStart = time.Now()

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
		observability.GatewayStageErrors.WithLabelValues(constants.StageProcessorLLM.String(), "error").Inc()
		return buildSymbolErrorOutput(tracker, symbol, err)
	}
	procSpan.End()

	// Phase 6: Guards + Routing.
	phaseStart = time.Now()
	routeCtx, routeSpan := observability.StartSpan(ctx, "pipeline.guards_and_routing",
		attribute.String("symbol", symbol),
		attribute.Bool("trade_valid", processorOutput.TradeValid),
	)

	routeResult := o.router.Route(routeCtx, processorOutput, symResult, macroResult, traceID)
	routeSpan.End()
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseEvaluatingGuards.String()).Observe(time.Since(phaseStart).Seconds())

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
		"trace_id":              traceID,
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
	return &models.GatewayOutput{
		CycleStatus:  constants.StatusCompleted,
		CycleOutcome: constants.OutcomeInsufficientData,
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
