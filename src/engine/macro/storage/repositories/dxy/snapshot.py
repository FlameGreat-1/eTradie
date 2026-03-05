from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.dxy import DXYSnapshotRow


class DXYRepository(BaseRepository[DXYSnapshotRow]):
    model = DXYSnapshotRow
    _repo_name = "dxy"

    async def get_latest(self) -> DXYSnapshotRow | None:
        stmt = select(self.model).order_by(self.model.analyzed_at.desc()).limit(1)
        result = await self.execute_query(stmt)
        return result[0] if result else None

    async def get_history(
        self,
        *,
        since: datetime,
        limit: int = 100,
    ) -> Sequence[DXYSnapshotRow]:
        stmt = (
            select(self.model)
            .where(self.model.analyzed_at >= since)
            .order_by(self.model.analyzed_at.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)
