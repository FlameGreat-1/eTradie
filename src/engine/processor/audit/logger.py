"""Build audit records from processor state.

Constructs AnalysisRecord and AuditLogRecord from the processor's
internal data for Postgres persistence. Pure data transformation
with no I/O.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from engine.processor.llm.client import LLMResponse
from engine.processor.models.analysis import AnalysisOutput
from engine.processor.models.audit import AnalysisRecord, AuditLogRecord


def build_analysis_record(
    output: AnalysisOutput,
    *,
    status: str = "success",
    error_message: Optional[str] = None,
    duration_ms: float = 0.0,
    trace_id: Optional[str] = None,
    raw_output: Optional[dict] = None,
) -> AnalysisRecord:
    """Build an AnalysisRecord from a validated AnalysisOutput."""
    tp_prices = [None, None, None]
    for i, tp in enumerate(output.take_profits[:3]):
        tp_prices[i] = tp.level

    llm_provider = ""
    llm_model = ""
    if raw_output:
        llm_provider = raw_output.get("_llm_provider", "")
        llm_model = raw_output.get("_llm_model", "")

    return AnalysisRecord(
        analysis_id=output.analysis_id,
        pair=output.pair,
        direction=output.direction,
        setup_grade=output.setup_grade,
        confluence_score=output.confluence_score.score,
        confidence=output.confidence,
        proceed_to_module_b=output.proceed_to_module_b,
        rr_ratio=output.rr_ratio,
        entry_price_low=output.entry_zone.low,
        entry_price_high=output.entry_zone.high,
        stop_loss_price=output.stop_loss.price,
        tp1_price=tp_prices[0],
        tp2_price=tp_prices[1],
        tp3_price=tp_prices[2],
        trading_style=output.trading_style,
        session=output.session,
        llm_provider=llm_provider,
        llm_model=llm_model,
        status=status,
        error_message=error_message,
        duration_ms=duration_ms,
        trace_id=trace_id,
        raw_output=raw_output or {},
    )


def build_audit_log_record(
    output: AnalysisOutput,
    llm_response: LLMResponse,
    *,
    prompt_hash: str,
    validation_passed: bool,
    validation_errors: list[str],
    trace_id: Optional[str] = None,
) -> AuditLogRecord:
    """Build an AuditLogRecord from processor state."""
    citations = []
    for src in output.rag_sources:
        citations.append({
            "doc_id": src.doc_id,
            "chunk_id": src.chunk_id,
            "section": src.section,
            "relevance_score": src.relevance_score,
        })

    retrieval = output.audit.retrieval
    coverage_result = output.audit.retrieval.strategy_used or ""

    return AuditLogRecord(
        analysis_id=output.analysis_id,
        pair=output.pair,
        timestamp=output.timestamp,
        retrieval_query_summary=retrieval.query_summary,
        retrieval_strategy=retrieval.strategy_used,
        retrieval_chunks_count=retrieval.top_k,
        retrieval_coverage=bool(retrieval.chunks_returned),
        retrieval_coverage_details=f"{len(retrieval.chunks_returned)} chunks returned",
        retrieval_conflicts=False,
        retrieval_conflict_details="",
        llm_model=llm_response.model,
        llm_prompt_hash=prompt_hash,
        llm_input_tokens=llm_response.input_tokens,
        llm_output_tokens=llm_response.output_tokens,
        llm_duration_ms=llm_response.duration_ms,
        llm_response={},
        citations=citations,
        final_direction=output.direction,
        final_grade=output.setup_grade,
        final_confidence=output.confidence,
        final_proceed=output.proceed_to_module_b,
        validation_passed=validation_passed,
        validation_errors=validation_errors,
        trace_id=trace_id,
    )


def build_error_analysis_record(
    *,
    pair: str,
    error_message: str,
    status: str,
    duration_ms: float = 0.0,
    trace_id: Optional[str] = None,
) -> AnalysisRecord:
    """Build an AnalysisRecord for a failed processor invocation."""
    now = datetime.now(UTC)
    return AnalysisRecord(
        analysis_id=f"error_{pair}_{now.strftime('%Y%m%d_%H%M%S')}",
        pair=pair,
        direction="NO SETUP",
        setup_grade="REJECT",
        confluence_score=0.0,
        confidence="NO SETUP",
        proceed_to_module_b="NO",
        trading_style="",
        session="",
        status=status,
        error_message=error_message,
        duration_ms=duration_ms,
        trace_id=trace_id,
    )
