from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, update

from engine.rag.storage.schemas.scenario import ScenarioRow
from engine.shared.db.repositories.base_repository import BaseRepository


class ScenarioRepository(BaseRepository[ScenarioRow]):
    model = ScenarioRow
    _repo_name = "rag_scenario"

    async def get_by_document(
        self, document_id: UUID,
    ) -> Sequence[ScenarioRow]:
        stmt = (
            select(self.model)
            .where(self.model.document_id == document_id)
            .order_by(self.model.created_at.asc())
        )
        return await self.execute_query(stmt)

    async def match(
        self,
        *,
        framework: Optional[str] = None,
        setup_family: Optional[str] = None,
        direction: Optional[str] = None,
        timeframe: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 10,
    ) -> Sequence[ScenarioRow]:
        stmt = select(self.model).where(self.model.is_active.is_(True))
        if framework:
            stmt = stmt.where(self.model.framework == framework)
        if setup_family:
            stmt = stmt.where(self.model.setup_family == setup_family)
        if direction:
            stmt = stmt.where(self.model.direction == direction)
        if timeframe:
            stmt = stmt.where(self.model.timeframe == timeframe)
        if outcome:
            stmt = stmt.where(self.model.outcome == outcome)
        stmt = stmt.order_by(self.model.created_at.desc()).limit(limit)
        return await self.execute_query(stmt)

    async def get_active(self) -> Sequence[ScenarioRow]:
        stmt = (
            select(self.model)
            .where(self.model.is_active.is_(True))
            .order_by(self.model.framework.asc(), self.model.setup_family.asc())
        )
        return await self.execute_query(stmt)

    async def deactivate(self, scenario_id: UUID) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id == scenario_id)
            .values(is_active=False)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def deactivate_by_document(
        self, document_id: UUID,
    ) -> int:
        stmt = (
            update(self.model)
            .where(
                self.model.document_id == document_id,
                self.model.is_active.is_(True),
            )
            .values(is_active=False)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount or 0
