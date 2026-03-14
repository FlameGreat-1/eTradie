"""Concrete ProcessorPort implementation.

The AnalysisProcessor is the single entry point for the gateway.
It implements ProcessorPort.process() and orchestrates the full
processor pipeline:

    ProcessorInput -> Prompt -> Claude API -> Parse -> Validate ->
    Map to ProcessorOutput -> Persist audit -> Return

This service is stateless. All dependencies are injected.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

import orjson

from engine.shared.exceptions import (
    ProcessorError,
    ProcessorInsufficientDataError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    PROCESSOR_RUN_DURATION,
    PROCESSOR_RUN_TOTAL,
)
from engine.processor.audit.logger import (
    build_analysis_record,
    build_audit_log_record,
    build_error_analysis_record,
)
from engine.processor.config import ProcessorConfig
from engine.processor.constants import PROCESSOR_NAME, ProcessorStatus
from engine.processor.llm.client import AnthropicClient, LLMResponse
from engine.processor.mapping.output_mapper import map_to_processor_output
from engine.processor.parsing.response_parser import parse_llm_response
from engine.processor.prompts.system_prompt import (
    build_system_prompt,
    build_user_message,
    compute_prompt_hash,
)
from engine.processor.storage.repositories.analysis_repository import AnalysisRepository
from engine.processor.storage.repositories.audit_repository import AuditRepository
from gateway.context.models import ProcessorInput, ProcessorOutput
from gateway.routing.processor_port import ProcessorPort

logger = get_logger(__name__)


class AnalysisProcessor(ProcessorPort):
    """Concrete implementation of the gateway's ProcessorPort.

    Receives the fully assembled context from the gateway, sends it
    to Claude for reasoning, parses and validates the response,
    maps it to the gateway's ProcessorOutput, and persists the
    audit trail.
    """

    def __init__(
        self,
        *,
        config: ProcessorConfig,
        llm_client: AnthropicClient,
        analysis_repo: Optional[AnalysisRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
    ) -> None:
        self._config = config
        self._llm = llm_client
        self._analysis_repo = analysis_repo
        self._audit_repo = audit_repo

    async def process(
        self,
        context: ProcessorInput,
        *,
        trace_id: Optional[str] = None,
    ) -> ProcessorOutput:
        """Process the assembled context and return a trade decision.

        This is the method the gateway calls. It implements the full
        processor pipeline with timeout, error handling, and audit.

        Args:
            context: Full TA + Macro + RAG context from gateway.
            trace_id: Distributed trace ID for correlation.

        Returns:
            ProcessorOutput for guard evaluation and routing.

        Raises:
            ProcessorError: On LLM call failure after retries.
            ProcessorInsufficientDataError: On insufficient context.
        """
        start = time.monotonic()
        symbol = context.symbol

        logger.info(
            "processor_started",
            extra={
                "symbol": symbol,
                "ta_keys": list(context.ta_analysis.keys()),
                "macro_keys": list(context.macro_analysis.keys()),
                "rag_keys": list(context.retrieved_knowledge.keys()),
                "trace_id": trace_id,
            },
        )

        try:
            async with asyncio.timeout(self._config.total_timeout_seconds):
                return await self._execute(context, trace_id=trace_id, start=start)

        except asyncio.TimeoutError:
            elapsed_ms = (time.monotonic() - start) * 1000
            PROCESSOR_RUN_TOTAL.labels(
                processor=PROCESSOR_NAME, status=ProcessorStatus.TIMEOUT,
            ).inc()
            PROCESSOR_RUN_DURATION.labels(
                processor=PROCESSOR_NAME,
            ).observe(elapsed_ms / 1000)

            await self._persist_error(
                pair=symbol,
                error_message=f"Processor timed out after {self._config.total_timeout_seconds}s",
                status=ProcessorStatus.TIMEOUT,
                duration_ms=elapsed_ms,
                trace_id=trace_id,
            )

            raise ProcessorError(
                f"Processor timed out after {self._config.total_timeout_seconds}s",
                details={"symbol": symbol, "trace_id": trace_id},
            )

        except ProcessorInsufficientDataError:
            elapsed_ms = (time.monotonic() - start) * 1000
            PROCESSOR_RUN_TOTAL.labels(
                processor=PROCESSOR_NAME, status=ProcessorStatus.INSUFFICIENT_DATA,
            ).inc()
            PROCESSOR_RUN_DURATION.labels(
                processor=PROCESSOR_NAME,
            ).observe(elapsed_ms / 1000)
            raise

        except ProcessorError:
            elapsed_ms = (time.monotonic() - start) * 1000
            PROCESSOR_RUN_TOTAL.labels(
                processor=PROCESSOR_NAME, status=ProcessorStatus.LLM_ERROR,
            ).inc()
            PROCESSOR_RUN_DURATION.labels(
                processor=PROCESSOR_NAME,
            ).observe(elapsed_ms / 1000)
            raise

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            PROCESSOR_RUN_TOTAL.labels(
                processor=PROCESSOR_NAME, status=ProcessorStatus.LLM_ERROR,
            ).inc()
            PROCESSOR_RUN_DURATION.labels(
                processor=PROCESSOR_NAME,
            ).observe(elapsed_ms / 1000)

            await self._persist_error(
                pair=symbol,
                error_message=str(exc),
                status=ProcessorStatus.LLM_ERROR,
                duration_ms=elapsed_ms,
                trace_id=trace_id,
            )

            raise ProcessorError(
                f"Processor failed: {exc}",
                details={"symbol": symbol, "trace_id": trace_id},
            ) from exc

    async def _execute(
        self,
        context: ProcessorInput,
        *,
        trace_id: Optional[str] = None,
        start: float,
    ) -> ProcessorOutput:
        """Core execution pipeline."""
        symbol = context.symbol

        # Step 1: Validate sufficient data
        self._validate_context(context, trace_id=trace_id)

        # Step 2: Build prompt
        system_prompt = build_system_prompt()
        user_message = build_user_message(context)
        prompt_hash = compute_prompt_hash(system_prompt, user_message)

        logger.debug(
            "processor_prompt_built",
            extra={
                "symbol": symbol,
                "user_message_length": len(user_message),
                "prompt_hash": prompt_hash,
                "trace_id": trace_id,
            },
        )

        # Step 3: Call Claude API
        llm_response: LLMResponse = await self._llm.call(
            system_prompt=system_prompt,
            user_message=user_message,
            trace_id=trace_id,
        )

        if self._config.log_raw_llm_response:
            logger.debug(
                "processor_raw_llm_response",
                extra={
                    "symbol": symbol,
                    "response_length": len(llm_response.text),
                    "trace_id": trace_id,
                },
            )

        # Step 4: Parse response into AnalysisOutput
        analysis_output, validation_warnings = parse_llm_response(
            llm_response.text,
            require_citations=self._config.require_citations,
            trace_id=trace_id,
        )

        # Step 5: Build raw response dict for audit
        try:
            raw_dict = orjson.loads(llm_response.text)
        except (orjson.JSONDecodeError, ValueError):
            raw_dict = {"raw_text": llm_response.text[:4096]}

        # Step 6: Map to gateway's ProcessorOutput
        processor_output = map_to_processor_output(
            analysis_output,
            raw_response=raw_dict,
        )

        elapsed_ms = (time.monotonic() - start) * 1000

        # Step 7: Determine status
        if analysis_output.direction == "NO SETUP":
            status = ProcessorStatus.NO_SETUP
        else:
            status = ProcessorStatus.SUCCESS

        PROCESSOR_RUN_TOTAL.labels(
            processor=PROCESSOR_NAME, status=status,
        ).inc()
        PROCESSOR_RUN_DURATION.labels(
            processor=PROCESSOR_NAME,
        ).observe(elapsed_ms / 1000)

        # Step 8: Persist audit trail
        if self._config.persist_audit_logs:
            await self._persist_success(
                analysis_output=analysis_output,
                llm_response=llm_response,
                prompt_hash=prompt_hash,
                validation_warnings=validation_warnings,
                raw_dict=raw_dict,
                elapsed_ms=elapsed_ms,
                trace_id=trace_id,
            )

        logger.info(
            "processor_completed",
            extra={
                "symbol": symbol,
                "analysis_id": analysis_output.analysis_id,
                "direction": analysis_output.direction,
                "grade": analysis_output.setup_grade,
                "score": analysis_output.confluence_score.score,
                "confidence": analysis_output.confidence,
                "proceed": analysis_output.proceed_to_module_b,
                "rr_ratio": analysis_output.rr_ratio,
                "duration_ms": round(elapsed_ms, 1),
                "input_tokens": llm_response.input_tokens,
                "output_tokens": llm_response.output_tokens,
                "warnings": validation_warnings,
                "trace_id": trace_id,
            },
        )

        return processor_output

    @staticmethod
    def _validate_context(
        context: ProcessorInput,
        *,
        trace_id: Optional[str] = None,
    ) -> None:
        """Validate that the context has sufficient data for analysis."""
        if not context.ta_analysis:
            raise ProcessorInsufficientDataError(
                "ProcessorInput has empty ta_analysis",
                details={"symbol": context.symbol, "trace_id": trace_id},
            )

        ta = context.ta_analysis
        has_candidates = (
            bool(ta.get("smc_candidates"))
            or bool(ta.get("snd_candidates"))
        )
        if not has_candidates:
            raise ProcessorInsufficientDataError(
                "ProcessorInput has no SMC or SnD candidates",
                details={"symbol": context.symbol, "trace_id": trace_id},
            )

        if not context.retrieved_knowledge:
            raise ProcessorInsufficientDataError(
                "ProcessorInput has empty retrieved_knowledge",
                details={"symbol": context.symbol, "trace_id": trace_id},
            )

    async def _persist_success(
        self,
        *,
        analysis_output: object,
        llm_response: LLMResponse,
        prompt_hash: str,
        validation_warnings: list[str],
        raw_dict: dict,
        elapsed_ms: float,
        trace_id: Optional[str],
    ) -> None:
        """Persist analysis record and audit log on success."""
        from engine.processor.models.analysis import AnalysisOutput as AO

        ao: AO = analysis_output  # type: ignore[assignment]

        try:
            record = build_analysis_record(
                ao,
                status="success" if ao.direction != "NO SETUP" else "no_setup",
                duration_ms=elapsed_ms,
                trace_id=trace_id,
                raw_output=raw_dict,
            )

            if self._analysis_repo:
                await self._analysis_repo.save_analysis(
                    analysis_id=record.analysis_id,
                    pair=record.pair,
                    direction=record.direction,
                    setup_grade=record.setup_grade,
                    confluence_score=record.confluence_score,
                    confidence=record.confidence,
                    proceed_to_module_b=record.proceed_to_module_b,
                    rr_ratio=record.rr_ratio,
                    entry_price_low=record.entry_price_low,
                    entry_price_high=record.entry_price_high,
                    stop_loss_price=record.stop_loss_price,
                    tp1_price=record.tp1_price,
                    tp2_price=record.tp2_price,
                    tp3_price=record.tp3_price,
                    trading_style=record.trading_style,
                    session=record.session,
                    status=record.status,
                    error_message=record.error_message,
                    duration_ms=record.duration_ms,
                    trace_id=record.trace_id,
                    raw_output=record.raw_output,
                )

            audit_record = build_audit_log_record(
                ao,
                llm_response,
                prompt_hash=prompt_hash,
                validation_passed=len(validation_warnings) == 0,
                validation_errors=validation_warnings,
                trace_id=trace_id,
            )

            if self._audit_repo:
                await self._audit_repo.save_audit_log(
                    analysis_id=audit_record.analysis_id,
                    pair=audit_record.pair,
                    timestamp=audit_record.timestamp,
                    retrieval_query_summary=audit_record.retrieval_query_summary,
                    retrieval_strategy=audit_record.retrieval_strategy,
                    retrieval_chunks_count=audit_record.retrieval_chunks_count,
                    retrieval_coverage=audit_record.retrieval_coverage,
                    retrieval_coverage_details=audit_record.retrieval_coverage_details,
                    retrieval_conflicts=audit_record.retrieval_conflicts,
                    retrieval_conflict_details=audit_record.retrieval_conflict_details,
                    llm_model=audit_record.llm_model,
                    llm_prompt_hash=audit_record.llm_prompt_hash,
                    llm_input_tokens=audit_record.llm_input_tokens,
                    llm_output_tokens=audit_record.llm_output_tokens,
                    llm_duration_ms=audit_record.llm_duration_ms,
                    llm_response=audit_record.llm_response,
                    citations=audit_record.citations,
                    final_direction=audit_record.final_direction,
                    final_grade=audit_record.final_grade,
                    final_confidence=audit_record.final_confidence,
                    final_proceed=audit_record.final_proceed,
                    validation_passed=audit_record.validation_passed,
                    validation_errors=audit_record.validation_errors,
                    trace_id=audit_record.trace_id,
                )

        except Exception as exc:
            logger.error(
                "processor_audit_persist_failed",
                extra={
                    "error": str(exc),
                    "analysis_id": ao.analysis_id,
                    "trace_id": trace_id,
                },
                exc_info=True,
            )

    async def _persist_error(
        self,
        *,
        pair: str,
        error_message: str,
        status: str,
        duration_ms: float,
        trace_id: Optional[str],
    ) -> None:
        """Persist an error analysis record."""
        try:
            record = build_error_analysis_record(
                pair=pair,
                error_message=error_message,
                status=status,
                duration_ms=duration_ms,
                trace_id=trace_id,
            )

            if self._analysis_repo:
                await self._analysis_repo.save_analysis(
                    analysis_id=record.analysis_id,
                    pair=record.pair,
                    direction=record.direction,
                    setup_grade=record.setup_grade,
                    confluence_score=record.confluence_score,
                    confidence=record.confidence,
                    proceed_to_module_b=record.proceed_to_module_b,
                    status=record.status,
                    error_message=record.error_message,
                    duration_ms=record.duration_ms,
                    trace_id=record.trace_id,
                )

        except Exception as exc:
            logger.error(
                "processor_error_persist_failed",
                extra={
                    "error": str(exc),
                    "pair": pair,
                    "trace_id": trace_id,
                },
                exc_info=True,
            )
