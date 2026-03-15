package pipeline

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/rs/zerolog"

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

// RunCycle executes a complete analysis cycle.
func (o *Orchestrator) RunCycle(ctx context.Context, symbols []string, traceID string) []*models.GatewayOutput {
	tracker := NewCycleTracker(traceID)
	observability.GatewayActiveCycles.Inc()

	o.log.Info().
		Str("cycle_id", tracker.CycleID()).
		Strs("symbols", symbols).
		Str("trace_id", tracker.TraceID()).
		Msg("cycle_started")

	var outputs []*models.GatewayOutput

	func() {
		defer func() {
			if r := recover(); r != nil {
				observability.LogPanicRecovery(o.log, r, "run_cycle")
				tracker.Fail(fmt.Sprintf("panic: %v", r), "unhandled", false)
				observability.GatewayStageErrors.WithLabelValues("cycle", "panic").Inc()
				outputs = append(outputs, buildErrorOutput(tracker))
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
			} else {
				tracker.Fail(err.Error(), "unhandled", false)
				observability.GatewayStageErrors.WithLabelValues("cycle", "error").Inc()
				o.log.Error().
					Str("cycle_id", tracker.CycleID()).
					Err(err).
					Str("phase_reached", tracker.Phase().String()).
					Str("trace_id", tracker.TraceID()).
					Msg("cycle_unhandled_error")
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
		Str("trace_id", tracker.TraceID()).
		Msg("cycle_finished")

	return outputs
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

	parallelCtx, parallelCancel := context.WithTimeout(ctx, time.Duration(o.cfg.TAMacroParallelTimeoutSeconds)*time.Second)
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
		return nil, fmt.Errorf("TA collection failed: %w", taErr)
	}
	if macroErr != nil {
		return nil, fmt.Errorf("Macro collection failed: %w", macroErr)
	}

	if !taResult.HasCandidates() {
		tracker.Complete(constants.OutcomeInsufficientData)
		o.log.Info().
			Str("cycle_id", tracker.CycleID()).
			Int("symbols_analysed", len(taResult.SymbolResults)).
			Str("trace_id", traceID).
			Msg("cycle_no_candidates")
		return []*models.GatewayOutput{buildNoDataOutput(tracker)}, nil
	}

	// Phase 2-6: Process each symbol that has candidates.
	var outputs []*models.GatewayOutput
	for i := range taResult.SymbolResults {
		sr := &taResult.SymbolResults[i]
		if sr.Status != "success" {
			continue
		}
		if len(sr.SMCCandidates) == 0 && len(sr.SnDCandidates) == 0 {
			continue
		}
		output := o.processSymbol(ctx, tracker, sr, macroResult)
		outputs = append(outputs, output)
	}

	if len(outputs) == 0 {
		tracker.Complete(constants.OutcomeNoSetup)
		return []*models.GatewayOutput{buildNoDataOutput(tracker)}, nil
	}

	if len(outputs) == 1 {
		tracker.Complete(outputs[0].CycleOutcome)
	} else {
		tracker.Complete(constants.OutcomeNoSetup)
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
	tracker.TransitionTo(constants.PhaseBuildingQuery)
	phaseStart := time.Now()
	queryParams := o.queryBuilder.Build(symResult, macroResult, "", traceID)
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseBuildingQuery.String()).Observe(time.Since(phaseStart).Seconds())

	// Phase 3: RAG retrieval.
	tracker.TransitionTo(constants.PhaseRetrievingRAG)
	phaseStart = time.Now()

	ragCtx, ragCancel := context.WithTimeout(ctx, time.Duration(o.cfg.RAGTimeoutSeconds)*time.Second)
	defer ragCancel()

	ragBundle, err := o.retrieveRAG(ragCtx, queryParams, traceID)
	ragElapsed := time.Since(phaseStart).Seconds()
	observability.GatewayRAGDuration.Observe(ragElapsed)
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseRetrievingRAG.String()).Observe(ragElapsed)

	if err != nil {
		observability.GatewayStageErrors.WithLabelValues(constants.StageRAGRetrieval.String(), "error").Inc()
		return buildSymbolErrorOutput(tracker, symbol, err)
	}

	// Phase 4: Assemble context.
	tracker.TransitionTo(constants.PhaseAssemblingCtx)
	phaseStart = time.Now()
	processorInput := o.assembler.Assemble(symbol, symResult, macroResult, ragBundle, traceID)
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseAssemblingCtx.String()).Observe(time.Since(phaseStart).Seconds())

	// Phase 5: Processor LLM.
	tracker.TransitionTo(constants.PhaseProcessingLLM)
	phaseStart = time.Now()

	procCtx, procCancel := context.WithTimeout(ctx, time.Duration(o.cfg.ProcessorTimeoutSeconds)*time.Second)
	defer procCancel()

	processorOutput, err := o.processor.Process(procCtx, processorInput)
	procElapsed := time.Since(phaseStart).Seconds()
	observability.GatewayProcessorDuration.Observe(procElapsed)
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseProcessingLLM.String()).Observe(procElapsed)

	if err != nil {
		observability.GatewayStageErrors.WithLabelValues(constants.StageProcessorLLM.String(), "error").Inc()
		return buildSymbolErrorOutput(tracker, symbol, err)
	}

	// Phase 6: Guards + Routing.
	tracker.TransitionTo(constants.PhaseEvaluatingGuards)
	phaseStart = time.Now()

	routeResult := o.router.Route(ctx, processorOutput, symResult, macroResult, traceID)
	observability.GatewayPhaseDuration.WithLabelValues(constants.PhaseEvaluatingGuards.String()).Observe(time.Since(phaseStart).Seconds())

	return &models.GatewayOutput{
		CycleStatus:     constants.StatusCompleted,
		CycleOutcome:    routeResult.Outcome,
		PhaseReached:    constants.PhaseCompleted,
		Symbol:          symbol,
		ProcessorOutput: processorOutput,
		GuardResult:     routeResult.GuardResult,
		DurationMs:      tracker.ElapsedMs(),
		TraceID:         traceID,
	}
}

func (o *Orchestrator) retrieveRAG(
	ctx context.Context,
	params *models.RAGQueryParams,
	traceID string,
) (map[string]interface{}, error) {
	resp, err := o.engineClient.RetrieveRAG(ctx, &enginev1.RetrieveRAGRequest{
		QueryText:          params.QueryText,
		Strategy:           params.Strategy,
		Framework:          params.Framework,
		SetupFamily:        params.SetupFamily,
		Direction:          params.Direction,
		Timeframe:          params.Timeframe,
		Style:              params.Style,
		Symbol:             params.Symbol,
		AllFrameworks:      params.AllFrameworks,
		AllSetupFamilies:   params.AllSetupFamilies,
		HasSmcCandidates:   params.HasSMCCandidates,
		HasSndCandidates:   params.HasSnDCandidates,
		HasMacroData:       params.HasMacroData,
		HasCotData:         params.HasCOTData,
		HasRateDecision:    params.HasRateDecision,
		HasHighImpactEvent: params.HasHighImpactEvent,
		HasDxyData:         params.HasDXYData,
		TraceId:            traceID,
	})
	if err != nil {
		return nil, fmt.Errorf("RAG retrieval failed: %w", err)
	}

	var bundle map[string]interface{}
	if len(resp.GetContextBundleJson()) > 0 {
		if err := json.Unmarshal(resp.GetContextBundleJson(), &bundle); err != nil {
			return nil, fmt.Errorf("RAG bundle unmarshal: %w", err)
		}
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
