from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.dxy import DXYSnapshotRow


class DXYRepository(BaseRepository[DXYSnapshotRow]):
    model = DXYSnapshotRow
    _repo_name = "dxy"

    async def get_latest(self, user_id: str) -> DXYSnapshotRow | None:
        stmt = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(self.model.analyzed_at.desc())
            .limit(1)
        )
        result = await self.execute_query(stmt)
        return result[0] if result else None

    async def get_history(
        self,
        user_id: str,
        *,
        since: datetime,
        limit: int = 100,
    ) -> Sequence[DXYSnapshotRow]:
        stmt = (
            select(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.analyzed_at >= since,
            )
            .order_by(self.model.analyzed_at.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def upsert_snapshot(
        self,
        user_id: str,
        *,
        value: float,
        momentum: str,
        analyzed_at: datetime,
    ) -> None:
        """Upsert a DXY snapshot with deduplication.

        Deduplication key: (user_id, analyzed_at).
        On conflict, updates value and momentum.
        """
        await self.bulk_upsert(
            [
                {
                    "user_id": user_id,
                    "value": value,
                    "momentum": momentum,
                    "analyzed_at": analyzed_at,
                }
            ],
            index_elements=["user_id", "analyzed_at"],
            update_fields=["value", "momentum"],
        )
