"""Repository for persisting analysis audit logs.

Extends BaseRepository. Audit logs are append-only and immutable.
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.shared.logging import get_logger
from engine.processor.storage.schemas.processor_schema import AnalysisAuditLogRow

logger = get_logger(__name__)


class AuditRepository(BaseRepository[AnalysisAuditLogRow]):
    """Persists and queries analysis audit logs."""

    model = AnalysisAuditLogRow
    _repo_name = "analysis_audit_log"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def save_audit_log(
        self,
        *,
        analysis_id: str,
        pair: str,
        timestamp: object,
        retrieval_query_summary: str = "",
        retrieval_strategy: Optional[str] = None,
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
        llm_response: Optional[dict] = None,
        citations: Optional[list] = None,
        final_direction: str = "",
        final_grade: str = "",
        final_confidence: str = "",
        final_proceed: str = "",
        validation_passed: bool = False,
        validation_errors: Optional[list] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        """Append an immutable audit log entry."""
        row = AnalysisAuditLogRow(
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
    ) -> Sequence[AnalysisAuditLogRow]:
        """Retrieve audit logs for a specific analysis."""
        stmt = (
            select(AnalysisAuditLogRow)
            .where(AnalysisAuditLogRow.analysis_id == analysis_id)
            .order_by(AnalysisAuditLogRow.created_at.desc())
        )
        return await self.execute_query(stmt)
