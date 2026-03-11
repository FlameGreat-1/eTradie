from __future__ import annotations

from uuid import UUID

from engine.rag.models.citation import Citation
from engine.rag.storage.repositories.citation_log import CitationLogRepository
from engine.rag.storage.repositories.retrieval_log import RetrievalLogRepository
from engine.rag.storage.schemas.citation_log import AnalysisCitationRow
from engine.rag.storage.schemas.retrieval_log import RetrievalLogRow
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    def __init__(
        self,
        *,
        retrieval_log_repo: RetrievalLogRepository,
        citation_log_repo: CitationLogRepository,
    ) -> None:
        self._retrieval_log_repo = retrieval_log_repo
        self._citation_log_repo = citation_log_repo

    async def log_retrieval(
        self,
        *,
        query_text: str,
        strategy: str,
        filters_applied: dict,
        total_candidates: int,
        chunks_returned: int,
        score_threshold: float,
        coverage_result: str,
        conflict_result: str,
        duration_ms: float,
        trace_id: str | None = None,
    ) -> UUID:
        row = RetrievalLogRow(
            query_text=query_text,
            strategy=strategy,
            filters_applied=filters_applied,
            total_candidates=total_candidates,
            chunks_returned=chunks_returned,
            score_threshold=score_threshold,
            coverage_result=coverage_result,
            conflict_result=conflict_result,
            duration_ms=duration_ms,
            trace_id=trace_id,
        )
        created = await self._retrieval_log_repo.create(row)
        return created.id

    async def log_citations(
        self,
        *,
        retrieval_log_id: UUID,
        citations: list[Citation],
    ) -> int:
        count = 0
        for citation in citations:
            row = AnalysisCitationRow(
                retrieval_log_id=retrieval_log_id,
                chunk_id=citation.chunk_id,
                document_id=citation.document_id,
                document_version_id=citation.document_version_id,
                doc_type=citation.doc_type,
                section=citation.section,
                subsection=citation.subsection,
                scenario_id=citation.scenario_id,
                relevance_score=citation.relevance_score,
                excerpt=citation.excerpt,
            )
            await self._citation_log_repo.create(row)
            count += 1

        logger.info(
            "citations_logged",
            retrieval_log_id=str(retrieval_log_id),
            count=count,
        )
        return count
