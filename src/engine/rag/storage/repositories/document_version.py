from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, update

from engine.rag.storage.schemas.document_version import DocumentVersionRow
from engine.shared.db.repositories.base_repository import BaseRepository


class DocumentVersionRepository(BaseRepository[DocumentVersionRow]):
    model = DocumentVersionRow
    _repo_name = "rag_document_version"

    async def get_by_document(
        self, document_id: UUID,
    ) -> Sequence[DocumentVersionRow]:
        stmt = (
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.version_number.desc())
        )
        return await self.execute_query(stmt)

    async def get_latest(
        self, document_id: UUID,
    ) -> Optional[DocumentVersionRow]:
        stmt = (
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.version_number.desc())
            .limit(1)
        )
        rows = await self.execute_query(stmt)
        return rows[0] if rows else None

    async def get_active(
        self, document_id: UUID,
    ) -> Optional[DocumentVersionRow]:
        stmt = (
            select(self.model)
            .where(
                self.model.document_id == document_id,
                self.model.status == "active",
            )
            .limit(1)
        )
        rows = await self.execute_query(stmt)
        return rows[0] if rows else None

    async def supersede(
        self, version_id: UUID, superseded_by: UUID,
    ) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == version_id)
            .values(
                status="superseded",
                superseded_at=datetime.now(UTC),
                superseded_by=superseded_by,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def activate(self, version_id: UUID) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == version_id)
            .values(status="active", published_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_by_checksum(
        self, document_id: UUID, checksum: str,
    ) -> Optional[DocumentVersionRow]:
        stmt = (
            select(self.model)
            .where(
                self.model.document_id == document_id,
                self.model.checksum == checksum,
            )
            .limit(1)
        )
        rows = await self.execute_query(stmt)
        return rows[0] if rows else None
