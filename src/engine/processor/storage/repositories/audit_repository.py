from typing import Any
"""Repository for persisting analysis audit logs.

Extends BaseRepository. Audit logs are append-only and immutable.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.processor.storage.schemas.processor_schema import AnalysisAuditLogRow
from engine.shared.db.repositories.base_repository import BaseRepository
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Hard limit for retrieval_strategy after migration 0023 widened the
# column to VARCHAR(128). Mirrored here so the writer can truncate
# defensively and emit a structured warning, rather than letting
# asyncpg raise StringDataRightTruncationError mid-transaction and
# nuke the entire audit-log INSERT (which would silently drop the
# audit row even though the trade analysis itself succeeded).
_RETRIEVAL_STRATEGY_MAX_LEN = 128


class AuditRepository(BaseRepository[AnalysisAuditLogRow]):
    """Persists and queries analysis audit logs."""

    model = AnalysisAuditLogRow
    _repo_name = "analysis_audit_log"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def save_audit_log(
        self,
        *,
        user_id: str,
        analysis_id: str,
        pair: str,
        timestamp: object,
        retrieval_query_summary: str = "",
        retrieval_strategy: str | None = None,
        retrieval_chunks_count: int = 0,
        retrieval_coverage: bool = False,
        retrieval_coverage_details: str = "",
        retrieval_conflicts: bool = False,
        retrieval_conflict_details: str = "",
        llm_model: str = "",
        llm_prompt_hash: str = "",
        llm_input_tokens: int = 0,
        llm_output_tokens: int = 0,
        llm_duration_ms: float = 0.0,
        llm_response: dict[str, Any] | None = None,
        citations: list[Any] | None = None,
        final_direction: str = "",
        final_grade: str = "",
        final_confidence: str = "",
        final_proceed: str = "",
        validation_passed: bool = False,
        validation_errors: list[Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        """Append an immutable audit log entry."""
        # Defensive truncation: retrieval_strategy is sourced from the
        # LLM's free-text self-report. Migration 0023 widened the
        # column to 128 chars after observing 37-char Gemini values
        # that overflowed the original VARCHAR(32). Future model
        # upgrades could emit even longer values, so cap here and
        # log a structured warning instead of letting asyncpg raise
        # StringDataRightTruncationError and abort the INSERT.
        if retrieval_strategy is not None and len(retrieval_strategy) > _RETRIEVAL_STRATEGY_MAX_LEN:
            logger.warning(
                "audit_retrieval_strategy_truncated",
                extra={
                    "analysis_id": analysis_id,
                    "trace_id": trace_id,
                    "original_length": len(retrieval_strategy),
                    "truncated_length": _RETRIEVAL_STRATEGY_MAX_LEN,
                },
            )
            retrieval_strategy = retrieval_strategy[:_RETRIEVAL_STRATEGY_MAX_LEN]

        row = AnalysisAuditLogRow(
            user_id=user_id,
            analysis_id=analysis_id,
            pair=pair,
            timestamp=timestamp,
            retrieval_query_summary=retrieval_query_summary,
            retrieval_strategy=retrieval_strategy,
            retrieval_chunks_count=retrieval_chunks_count,
            retrieval_coverage=retrieval_coverage,
            retrieval_coverage_details=retrieval_coverage_details,
            retrieval_conflicts=retrieval_conflicts,
            retrieval_conflict_details=retrieval_conflict_details,
            llm_model=llm_model,
            llm_prompt_hash=llm_prompt_hash,
            llm_input_tokens=llm_input_tokens,
            llm_output_tokens=llm_output_tokens,
            llm_duration_ms=llm_duration_ms,
            llm_response=llm_response or {},
            citations=citations or [],
            final_direction=final_direction,
            final_grade=final_grade,
            final_confidence=final_confidence,
            final_proceed=final_proceed,
            validation_passed=validation_passed,
            validation_errors=validation_errors or [],
            trace_id=trace_id,
        )
        await self.add(row)

    async def get_by_analysis_id(
        self,
        analysis_id: str,
        user_id: str,
    ) -> Sequence[AnalysisAuditLogRow]:
        """Retrieve audit logs for a specific analysis, scoped to user."""
        stmt = (
            select(AnalysisAuditLogRow)
            .where(
                AnalysisAuditLogRow.user_id == user_id,
                AnalysisAuditLogRow.analysis_id == analysis_id,
            )
            .order_by(AnalysisAuditLogRow.created_at.desc())
        )
        return await self.execute_query(stmt)
