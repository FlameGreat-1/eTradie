from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, update

from engine.rag.storage.schemas.document import DocumentRow
from engine.shared.db.repositories.base_repository import BaseRepository


class DocumentRepository(BaseRepository[DocumentRow]):
    model = DocumentRow
    _repo_name = "rag_document"

    async def get_by_source_path(self, source_path: str) -> Optional[DocumentRow]:
        stmt = select(self.model).where(self.model.source_path == source_path)
        rows = await self.execute_query(stmt)
        return rows[0] if rows else None

    async def get_by_doc_type(
        self, doc_type: str, *, status: Optional[str] = None,
    ) -> Sequence[DocumentRow]:
        stmt = select(self.model).where(self.model.doc_type == doc_type)
        if status:
            stmt = stmt.where(self.model.status == status)
        return await self.execute_query(stmt)

    async def get_active_documents(self) -> Sequence[DocumentRow]:
        stmt = (
            select(self.model)
            .where(self.model.status == "active")
            .order_by(self.model.doc_type.asc())
        )
        return await self.execute_query(stmt)

    async def set_active_version(
        self, document_id: UUID, version_id: UUID,
    ) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == document_id)
            .values(active_version_id=version_id, status="active")
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def set_status(self, document_id: UUID, status: str) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == document_id)
            .values(status=status)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_active_doc_types(self) -> Sequence[str]:
        stmt = (
            select(self.model.doc_type)
            .where(self.model.status == "active")
            .distinct()
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]
