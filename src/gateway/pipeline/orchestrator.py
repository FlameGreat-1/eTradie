"""Main analysis cycle orchestrator.

Runs the full pipeline: TA+Macro parallel -> QueryBuilder -> RAG ->
ContextAssembly -> Processor -> Guards -> Router.

Handles timeouts, retries, and panic recovery at every phase boundary.
This is the single entry point for the gateway's core workflow.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from engine.rag.orchestrator import RAGOrchestrator
from engine.shared.logging import get_logger
from gateway.collectors.macro_collector import MacroCollector
from gateway.collectors.ta_collector import TACollector
from gateway.config import GatewayConfig
from gateway.constants import (
    CycleOutcome,
    CyclePhase,
    CycleStatus,
    PipelineStage,
)
from gateway.context.assembler import ContextAssembler
from gateway.context.models import (
    GatewayOutput,
    MacroResult,
    ProcessorOutput,
    TAResult,
    TASymbolResult,
)
from gateway.observability.metrics import (
    GATEWAY_ACTIVE_CYCLES,
    GATEWAY_CYCLE_DURATION,
    GATEWAY_CYCLE_TOTAL,
    GATEWAY_PHASE_DURATION,
    GATEWAY_PROCESSOR_DURATION,
    GATEWAY_RAG_DURATION,
    GATEWAY_STAGE_ERRORS,
)
from gateway.pipeline.cycle import CycleTracker
from gateway.query_builder.builder import QueryBuilder
from gateway.routing.processor_port import ProcessorPort
from gateway.routing.router import DecisionRouter

logger = get_logger(__name__)


class PipelineOrchestrator:
    """Orchestrates the full analysis cycle."""

    def __init__(
        self,
        *,
        config: GatewayConfig,
        ta_collector: TACollector,
        macro_collector: MacroCollector,
        query_builder: QueryBuilder,
        rag_orchestrator: RAGOrchestrator,
        context_assembler: ContextAssembler,
        processor: ProcessorPort,
        router: DecisionRouter,
    ) -> None:
        self._config = config
        self._ta_collector = ta_collector
        self._macro_collector = macro_collector
        self._query_builder = query_builder
        self._rag = rag_orchestrator
        self._assembler = context_assembler
        self._processor = processor
        self._router = router

    async def run_cycle(
        self,
        *,
        symbols: Optional[list[str]] = None,
        trace_id: Optional[str] = None,
    ) -> list[GatewayOutput]:
        """Execute a complete analysis cycle.

        Args:
            symbols: User-selected symbols from dashboard. If None,
                     falls back to default_symbols from TAConfig.
            trace_id: Distributed trace ID for correlation.

        Returns a list of GatewayOutput, one per symbol that had candidates.
        """
        tracker = CycleTracker(trace_id=trace_id)
        GATEWAY_ACTIVE_CYCLES.inc()

        logger.info(
            "cycle_started",
            extra={
                "cycle_id": tracker.cycle_id,
                "symbols_override": symbols,
                "trace_id": tracker.trace_id,
            },
        )

        outputs: list[GatewayOutput] = []

        try:
            async with asyncio.timeout(self._config.cycle_timeout_seconds):
                outputs = await self._execute_pipeline(tracker, symbols=symbols)

        except asyncio.TimeoutError:
            tracker.fail(
                f"Cycle timed out after {self._config.cycle_timeout_seconds}s",
                stage="cycle_timeout",
                timed_out=True,
            )
            GATEWAY_STAGE_ERRORS.labels(
                stage="cycle", error_type="timeout",
            ).inc()
            logger.error(
                "cycle_timed_out",
                extra={
                    "cycle_id": tracker.cycle_id,
                    "timeout_seconds": self._config.cycle_timeout_seconds,
                    "phase_reached": tracker.phase.value,
                    "trace_id": tracker.trace_id,
                },
            )
            outputs.append(self._build_error_output(tracker))

        except Exception as exc:
            tracker.fail(str(exc), stage="unhandled")
            GATEWAY_STAGE_ERRORS.labels(
                stage="cycle", error_type=type(exc).__name__,
            ).inc()
            logger.error(
                "cycle_unhandled_error",
                extra={
                    "cycle_id": tracker.cycle_id,
                    "error": str(exc),
                    "phase_reached": tracker.phase.value,
                    "trace_id": tracker.trace_id,
                },
                exc_info=True,
            )
            outputs.append(self._build_error_output(tracker))

        finally:
            GATEWAY_ACTIVE_CYCLES.dec()
            elapsed_s = tracker.elapsed_ms / 1000
            GATEWAY_CYCLE_DURATION.observe(elapsed_s)

            state = tracker.to_state()
            status = state.status.value
            outcome = state.outcome.value if state.outcome else "unknown"
            GATEWAY_CYCLE_TOTAL.labels(status=status, outcome=outcome).inc()

            logger.info(
                "cycle_finished",
                extra={
                    "cycle_id": tracker.cycle_id,
                    "status": status,
                    "outcome": outcome,
                    "duration_ms": round(tracker.elapsed_ms, 1),
                    "phase_durations": state.phase_durations_ms,
                    "outputs_count": len(outputs),
                    "trace_id": tracker.trace_id,
                },
            )

        return outputs

    async def _execute_pipeline(
        self,
        tracker: CycleTracker,
        *,
        symbols: Optional[list[str]] = None,
    ) -> list[GatewayOutput]:
        """Core pipeline execution."""
        trace_id = tracker.trace_id

        # Phase 1: Parallel TA + Macro collection
        tracker.transition_to(CyclePhase.COLLECTING_PARALLEL)
        phase_start = time.monotonic()

        try:
            async with asyncio.timeout(self._config.ta_macro_parallel_timeout_seconds):
                ta_result, macro_result = await asyncio.gather(
                    self._ta_collector.collect(symbols=symbols, trace_id=trace_id),
                    self._macro_collector.collect(trace_id=trace_id),
                )
        except asyncio.TimeoutError:
            tracker.fail(
                "TA+Macro parallel collection timed out",
                stage=PipelineStage.TA_COLLECTOR,
                timed_out=True,
            )
            raise

        GATEWAY_PHASE_DURATION.labels(phase=CyclePhase.COLLECTING_PARALLEL).observe(
            time.monotonic() - phase_start,
        )

        # Check if we have any candidates to process
        if not ta_result.has_candidates:
            tracker.complete(CycleOutcome.INSUFFICIENT_DATA)
            logger.info(
                "cycle_no_candidates",
                extra={
                    "cycle_id": tracker.cycle_id,
                    "symbols_analysed": len(ta_result.symbol_results),
                    "trace_id": trace_id,
                },
            )
            return [self._build_no_data_output(tracker)]

        # Phase 2-6: Process each symbol that has candidates
        outputs: list[GatewayOutput] = []

        for sym_result in ta_result.symbol_results:
            if sym_result.status != "success":
                continue
            if not sym_result.smc_candidates and not sym_result.snd_candidates:
                continue

            output = await self._process_symbol(
                tracker=tracker,
                sym_result=sym_result,
                macro_result=macro_result,
            )
            outputs.append(output)

        if not outputs:
            tracker.complete(CycleOutcome.NO_SETUP)
            return [self._build_no_data_output(tracker)]

        tracker.complete(
            outputs[0].cycle_outcome if len(outputs) == 1 else CycleOutcome.NO_SETUP,
        )
        return outputs

    async def _process_symbol(
        self,
        *,
        tracker: CycleTracker,
        sym_result: TASymbolResult,
        macro_result: MacroResult,
    ) -> GatewayOutput:
        """Process a single symbol through RAG -> Processor -> Guards -> Router."""
        trace_id = tracker.trace_id
        symbol = sym_result.symbol

        try:
            # Phase 2: Build RAG query
            tracker.transition_to(CyclePhase.BUILDING_QUERY)
            phase_start = time.monotonic()

            query_params = self._query_builder.build(
                sym_result, macro_result, trace_id=trace_id,
            )

            GATEWAY_PHASE_DURATION.labels(phase=CyclePhase.BUILDING_QUERY).observe(
                time.monotonic() - phase_start,
            )

            # Phase 3: RAG retrieval
            tracker.transition_to(CyclePhase.RETRIEVING_RAG)
            phase_start = time.monotonic()

            try:
                async with asyncio.timeout(self._config.rag_timeout_seconds):
                    rag_bundle = await self._rag.retrieve_context(
                        query_params.query_text,
                        strategy=query_params.strategy,
                        framework=query_params.framework,
                        setup_family=query_params.setup_family,
                        direction=query_params.direction,
                        timeframe=query_params.timeframe,
                        style=query_params.style,
                        trace_id=trace_id,
                    )
            except asyncio.TimeoutError:
                GATEWAY_STAGE_ERRORS.labels(
                    stage=PipelineStage.RAG_RETRIEVAL, error_type="timeout",
                ).inc()
                raise

            rag_elapsed = time.monotonic() - phase_start
            GATEWAY_RAG_DURATION.observe(rag_elapsed)
            GATEWAY_PHASE_DURATION.labels(phase=CyclePhase.RETRIEVING_RAG).observe(rag_elapsed)

            # Phase 4: Assemble context
            tracker.transition_to(CyclePhase.ASSEMBLING_CONTEXT)
            phase_start = time.monotonic()

            processor_input = self._assembler.assemble(
                symbol=symbol,
                ta_result=sym_result,
                macro_result=macro_result,
                rag_bundle=rag_bundle,
                trace_id=trace_id,
            )

            GATEWAY_PHASE_DURATION.labels(phase=CyclePhase.ASSEMBLING_CONTEXT).observe(
                time.monotonic() - phase_start,
            )

            # Phase 5: Processor LLM
            tracker.transition_to(CyclePhase.PROCESSING_LLM)
            phase_start = time.monotonic()

            try:
                async with asyncio.timeout(self._config.processor_timeout_seconds):
                    processor_output = await self._processor.process(
                        processor_input, trace_id=trace_id,
                    )
            except asyncio.TimeoutError:
                GATEWAY_STAGE_ERRORS.labels(
                    stage=PipelineStage.PROCESSOR_LLM, error_type="timeout",
                ).inc()
                raise

            proc_elapsed = time.monotonic() - phase_start
            GATEWAY_PROCESSOR_DURATION.observe(proc_elapsed)
            GATEWAY_PHASE_DURATION.labels(phase=CyclePhase.PROCESSING_LLM).observe(proc_elapsed)

            # Phase 6: Guards + Routing
            tracker.transition_to(CyclePhase.EVALUATING_GUARDS)
            phase_start = time.monotonic()

            outcome, guard_result, execution_result = await self._router.route(
                processor_output=processor_output,
                ta_result=sym_result,
                macro_result=macro_result,
                trace_id=trace_id,
            )

            GATEWAY_PHASE_DURATION.labels(phase=CyclePhase.EVALUATING_GUARDS).observe(
                time.monotonic() - phase_start,
            )

            return GatewayOutput(
                cycle_status=CycleStatus.COMPLETED,
                cycle_outcome=outcome,
                phase_reached=CyclePhase.COMPLETED,
                symbol=symbol,
                processor_output=processor_output,
                guard_result=guard_result,
                duration_ms=tracker.elapsed_ms,
                trace_id=trace_id,
            )

        except asyncio.TimeoutError as exc:
            GATEWAY_STAGE_ERRORS.labels(
                stage=tracker.phase.value, error_type="timeout",
            ).inc()
            logger.error(
                "symbol_processing_timeout",
                extra={
                    "symbol": symbol,
                    "phase": tracker.phase.value,
                    "trace_id": trace_id,
                },
            )
            return GatewayOutput(
                cycle_status=CycleStatus.TIMED_OUT,
                cycle_outcome=CycleOutcome.PIPELINE_ERROR,
                phase_reached=tracker.phase,
                symbol=symbol,
                duration_ms=tracker.elapsed_ms,
                trace_id=trace_id,
                error=f"Timeout in phase {tracker.phase.value}",
                error_stage=tracker.phase.value,
            )

        except Exception as exc:
            GATEWAY_STAGE_ERRORS.labels(
                stage=tracker.phase.value, error_type=type(exc).__name__,
            ).inc()
            logger.error(
                "symbol_processing_failed",
                extra={
                    "symbol": symbol,
                    "phase": tracker.phase.value,
                    "error": str(exc),
                    "trace_id": trace_id,
                },
                exc_info=True,
            )
            return GatewayOutput(
                cycle_status=CycleStatus.FAILED,
                cycle_outcome=CycleOutcome.PIPELINE_ERROR,
                phase_reached=tracker.phase,
                symbol=symbol,
                duration_ms=tracker.elapsed_ms,
                trace_id=trace_id,
                error=str(exc),
                error_stage=tracker.phase.value,
            )

    @staticmethod
    def _build_error_output(tracker: CycleTracker) -> GatewayOutput:
        state = tracker.to_state()
        return GatewayOutput(
            cycle_status=state.status,
            cycle_outcome=state.outcome or CycleOutcome.PIPELINE_ERROR,
            phase_reached=state.phase,
            duration_ms=tracker.elapsed_ms,
            trace_id=tracker.trace_id,
            error=state.error,
            error_stage=state.error_stage,
        )

    @staticmethod
    def _build_no_data_output(tracker: CycleTracker) -> GatewayOutput:
        return GatewayOutput(
            cycle_status=CycleStatus.COMPLETED,
            cycle_outcome=CycleOutcome.INSUFFICIENT_DATA,
            phase_reached=CyclePhase.COMPLETED,
            duration_ms=tracker.elapsed_ms,
            trace_id=tracker.trace_id,
        )
