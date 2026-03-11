from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import delete, select, update

from engine.rag.storage.schemas.chunk import ChunkRow
from engine.shared.db.repositories.base_repository import BaseRepository


class ChunkRepository(BaseRepository[ChunkRow]):
    model = ChunkRow
    _repo_name = "rag_chunk"

    async def get_by_document_version(
        self, document_version_id: UUID,
    ) -> Sequence[ChunkRow]:
        stmt = (
            select(self.model)
            .where(self.model.document_version_id == document_version_id)
            .order_by(self.model.chunk_index.asc())
        )
        return await self.execute_query(stmt)

    async def get_by_document(
        self, document_id: UUID,
    ) -> Sequence[ChunkRow]:
        stmt = (
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.chunk_index.asc())
        )
        return await self.execute_query(stmt)

    async def get_pending_embedding(
        self, *, limit: int = 100,
    ) -> Sequence[ChunkRow]:
        stmt = (
            select(self.model)
            .where(self.model.embedding_status == "pending")
            .order_by(self.model.created_at.asc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def set_embedding_status(
        self, chunk_ids: list[UUID], status: str,
    ) -> None:
        if not chunk_ids:
            return
        stmt = (
            update(self.model)
            .where(self.model.id.in_(chunk_ids))
            .values(embedding_status=status)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_by_content_hash(
        self, content_hash: str,
    ) -> Sequence[ChunkRow]:
        stmt = select(self.model).where(self.model.content_hash == content_hash)
        return await self.execute_query(stmt)

    async def delete_by_document_version(
        self, document_version_id: UUID,
    ) -> int:
        stmt = (
            delete(self.model)
            .where(self.model.document_version_id == document_version_id)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount or 0

    async def get_by_doc_type(
        self, doc_type: str, *, embedding_status: str | None = None,
    ) -> Sequence[ChunkRow]:
        stmt = select(self.model).where(self.model.doc_type == doc_type)
        if embedding_status:
            stmt = stmt.where(self.model.embedding_status == embedding_status)
        return await self.execute_query(stmt)
