from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.intermarket import IntermarketSnapshotRow


class IntermarketRepository(BaseRepository[IntermarketSnapshotRow]):
    model = IntermarketSnapshotRow
    _repo_name = "intermarket"

    async def get_latest(self) -> IntermarketSnapshotRow | None:
        stmt = select(self.model).order_by(self.model.snapshot_at.desc()).limit(1)
        result = await self.execute_query(stmt)
        return result[0] if result else None

    async def get_daily_history(
        self,
        *,
        since: datetime,
        limit: int = 30,
    ) -> Sequence[IntermarketSnapshotRow]:
        stmt = (
            select(self.model)
            .where(self.model.snapshot_at >= since)
            .order_by(self.model.snapshot_at.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)
