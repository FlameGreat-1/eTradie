from __future__ import annotations

from datetime import UTC, datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import select, update

from engine.rag.storage.schemas.reembed_queue import ReembedQueueRow
from engine.shared.db.repositories.base_repository import BaseRepository


class ReembedQueueRepository(BaseRepository[ReembedQueueRow]):
    model = ReembedQueueRow
    _repo_name = "rag_reembed_queue"

    async def get_pending(self, *, limit: int = 50) -> Sequence[ReembedQueueRow]:
        stmt = (
            select(self.model)
            .where(
                self.model.status.in_(["pending", "retrying"]),
                self.model.retry_count < self.model.max_retries,
            )
            .order_by(self.model.created_at.asc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def get_by_document(
        self, document_id: UUID,
    ) -> Sequence[ReembedQueueRow]:
        stmt = (
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.created_at.desc())
        )
        return await self.execute_query(stmt)

    async def mark_processing(self, queue_id: UUID) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == queue_id)
            .values(status="running")
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def mark_completed(self, queue_id: UUID) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == queue_id)
            .values(status="completed", processed_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def mark_failed(
        self, queue_id: UUID, *, error_message: str,
    ) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == queue_id)
            .values(
                status="failed",
                error_message=error_message,
                retry_count=self.model.retry_count + 1,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def enqueue(
        self,
        *,
        document_id: UUID,
        document_version_id: UUID | None = None,
        chunk_id: UUID | None = None,
        reason: str,
    ) -> ReembedQueueRow:
        row = ReembedQueueRow(
            document_id=document_id,
            document_version_id=document_version_id,
            chunk_id=chunk_id,
            reason=reason,
            status="pending",
        )
        self._session.add(row)
        await self._session.flush()
        return row
