from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.macro_output import MacroBiasOutputRow


class MacroBiasOutputRepository(BaseRepository[MacroBiasOutputRow]):
    model = MacroBiasOutputRow
    _repo_name = "macro_output"

    async def get_by_run_id(self, run_id: uuid.UUID) -> Sequence[MacroBiasOutputRow]:
        stmt = (
            select(self.model)
            .where(self.model.run_id == run_id)
            .order_by(self.model.currency)
        )
        return await self.execute_query(stmt)

    async def get_latest_by_currency(self, currency: str) -> MacroBiasOutputRow | None:
        stmt = (
            select(self.model)
            .where(self.model.currency == currency)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        result = await self.execute_query(stmt)
        return result[0] if result else None

    async def get_latest_run(self) -> Sequence[MacroBiasOutputRow]:
        latest_stmt = select(self.model.run_id).order_by(self.model.created_at.desc()).limit(1)
        result = await self._session.execute(latest_stmt)
        run_id = result.scalar_one_or_none()
        if run_id is None:
            return []
        return await self.get_by_run_id(run_id)

    async def get_history(
        self,
        *,
        since: datetime,
        currency: str | None = None,
        limit: int = 100,
    ) -> Sequence[MacroBiasOutputRow]:
        stmt = (
            select(self.model)
            .where(self.model.created_at >= since)
            .order_by(self.model.created_at.desc())
            .limit(limit)
        )
        if currency:
            stmt = stmt.where(self.model.currency == currency)
        return await self.execute_query(stmt)
