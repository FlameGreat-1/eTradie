from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select

from engine.rag.storage.schemas.retrieval_log import RetrievalLogRow
from engine.shared.db.repositories.base_repository import BaseRepository


class RetrievalLogRepository(BaseRepository[RetrievalLogRow]):
    model = RetrievalLogRow
    _repo_name = "rag_retrieval_log"

    async def get_by_strategy(
        self, strategy: str, *, limit: int = 50,
    ) -> Sequence[RetrievalLogRow]:
        stmt = (
            select(self.model)
            .where(self.model.strategy == strategy)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def get_by_trace_id(
        self, trace_id: str,
    ) -> Sequence[RetrievalLogRow]:
        stmt = (
            select(self.model)
            .where(self.model.trace_id == trace_id)
            .order_by(self.model.created_at.desc())
        )
        return await self.execute_query(stmt)

    async def get_recent(
        self, *, limit: int = 100,
    ) -> Sequence[RetrievalLogRow]:
        stmt = (
            select(self.model)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def get_by_coverage_result(
        self, coverage_result: str, *, since: datetime | None = None, limit: int = 50,
    ) -> Sequence[RetrievalLogRow]:
        stmt = select(self.model).where(self.model.coverage_result == coverage_result)
        if since:
            stmt = stmt.where(self.model.created_at >= since)
        stmt = stmt.order_by(self.model.created_at.desc()).limit(limit)
        return await self.execute_query(stmt)
