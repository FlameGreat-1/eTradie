from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.intermarket import IntermarketSnapshotRow


class IntermarketRepository(BaseRepository[IntermarketSnapshotRow]):
    model = IntermarketSnapshotRow
    _repo_name = "intermarket"

    async def get_latest(self, user_id: str) -> IntermarketSnapshotRow | None:
        stmt = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(self.model.snapshot_at.desc())
            .limit(1)
        )
        result = await self.execute_query(stmt)
        return result[0] if result else None

    async def get_daily_history(
        self,
        user_id: str,
        *,
        since: datetime,
        limit: int = 30,
    ) -> Sequence[IntermarketSnapshotRow]:
        stmt = (
            select(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.snapshot_at >= since,
            )
            .order_by(self.model.snapshot_at.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def upsert_snapshot(
        self,
        user_id: str,
        *,
        snapshot_data: dict[str, Any],
    ) -> None:
        """Upsert an intermarket snapshot with deduplication.

        Deduplication key: (user_id, snapshot_at).
        On conflict, updates all market data fields.
        """
        row = {"user_id": user_id, **snapshot_data}
        await self.bulk_upsert(
            [row],
            index_elements=["user_id", "snapshot_at"],
            update_fields=[
                "gold_price", "silver_price", "oil_price",
                "iron_ore", "dairy_gdt", "copper", "natural_gas",
                "us2y_yield", "us10y_yield", "us30y_yield",
                "dxy_value", "sp500", "vix",
                "correlation_signals_json",
            ],
        )
