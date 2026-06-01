from __future__ import annotations

from typing import Any

from sqlalchemy import select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.intermarket import IntermarketSnapshotRow


class IntermarketRepository(BaseRepository[IntermarketSnapshotRow]):
    model = IntermarketSnapshotRow
    _repo_name = "intermarket"

    async def get_latest(self) -> IntermarketSnapshotRow | None:
        stmt = (
            select(self.model)
            .order_by(self.model.snapshot_at.desc())
            .limit(1)
        )
        result = await self.execute_query(stmt)
        return result[0] if result else None

    async def upsert_snapshot(
        self,
        *,
        snapshot_data: dict[str, Any],
    ) -> None:
        """Upsert an intermarket snapshot with deduplication.

        Deduplication key: (snapshot_at).
        On conflict, updates all market data fields.
        """
        row = {**snapshot_data}
        await self.bulk_upsert(
            [row],
            index_elements=["snapshot_at"],
            update_fields=[
                "gold_price", "silver_price", "oil_price",
                "iron_ore", "dairy_gdt", "copper", "natural_gas",
                "us2y_yield", "us10y_yield", "us30y_yield",
                "dxy_value", "sp500", "vix",
                "correlation_signals_json",
            ],
        )
