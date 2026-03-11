from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select

from engine.rag.storage.schemas.citation_log import AnalysisCitationRow
from engine.shared.db.repositories.base_repository import BaseRepository


class CitationLogRepository(BaseRepository[AnalysisCitationRow]):
    model = AnalysisCitationRow
    _repo_name = "rag_citation_log"

    async def get_by_retrieval(
        self, retrieval_log_id: UUID,
    ) -> Sequence[AnalysisCitationRow]:
        stmt = (
            select(self.model)
            .where(self.model.retrieval_log_id == retrieval_log_id)
            .order_by(self.model.relevance_score.desc())
        )
        return await self.execute_query(stmt)

    async def get_by_document(
        self, document_id: UUID, *, limit: int = 100,
    ) -> Sequence[AnalysisCitationRow]:
        stmt = (
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def get_by_chunk(
        self, chunk_id: UUID,
    ) -> Sequence[AnalysisCitationRow]:
        stmt = (
            select(self.model)
            .where(self.model.chunk_id == chunk_id)
            .order_by(self.model.created_at.desc())
        )
        return await self.execute_query(stmt)

    async def get_by_doc_type(
        self, doc_type: str, *, limit: int = 100,
    ) -> Sequence[AnalysisCitationRow]:
        stmt = (
            select(self.model)
            .where(self.model.doc_type == doc_type)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)
