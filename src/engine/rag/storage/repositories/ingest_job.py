from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, update

from engine.rag.storage.schemas.ingest_job import IngestJobRow
from engine.shared.db.repositories.base_repository import BaseRepository


class IngestJobRepository(BaseRepository[IngestJobRow]):
    model = IngestJobRow
    _repo_name = "rag_ingest_job"

    async def get_by_document(
        self, document_id: UUID,
    ) -> Sequence[IngestJobRow]:
        stmt = (
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.created_at.desc())
        )
        return await self.execute_query(stmt)

    async def get_pending(self, *, limit: int = 20) -> Sequence[IngestJobRow]:
        stmt = (
            select(self.model)
            .where(self.model.status.in_(["pending", "retrying"]))
            .order_by(self.model.created_at.asc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def get_latest_for_document(
        self, document_id: UUID,
    ) -> Optional[IngestJobRow]:
        stmt = (
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        rows = await self.execute_query(stmt)
        return rows[0] if rows else None

    async def mark_running(self, job_id: UUID) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == job_id)
            .values(status="running", started_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        chunks_created: int,
        embeddings_created: int,
    ) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == job_id)
            .values(
                status="completed",
                completed_at=datetime.now(UTC),
                chunks_created=chunks_created,
                embeddings_created=embeddings_created,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def mark_failed(
        self, job_id: UUID, *, error_message: str,
    ) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == job_id)
            .values(status="failed", error_message=error_message)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def mark_retrying(self, job_id: UUID) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == job_id)
            .values(
                status="retrying",
                retry_count=self.model.retry_count + 1,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_retriable(self, *, limit: int = 10) -> Sequence[IngestJobRow]:
        stmt = (
            select(self.model)
            .where(
                self.model.status == "retrying",
                self.model.retry_count < self.model.max_retries,
            )
            .order_by(self.model.created_at.asc())
            .limit(limit)
        )
        return await self.execute_query(stmt)
