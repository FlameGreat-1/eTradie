from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

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

    async def get_recent_values(
        self,
        limit: int = 20,
    ) -> Sequence[DXYSnapshotRow]:
        """Get recent DXY snapshots for trend and key level analysis."""
        stmt = select(self.model).order_by(self.model.analyzed_at.desc()).limit(limit)
        return await self.execute_query(stmt)

    async def upsert_snapshot(
        self,
        *,
        value: float,
        trend_direction: str,
        momentum: str,
        key_levels_json: dict[str, Any],
        divergence_signals_json: dict[str, Any],
        bias: str,
        analyzed_at: datetime,
    ) -> None:
        """Upsert a DXY snapshot with deduplication.

        Deduplication key: (analyzed_at).
        On conflict, updates all analytical fields.
        """
        await self.bulk_upsert(
            [
                {
                    "value": value,
                    "trend_direction": trend_direction,
                    "momentum": momentum,
                    "key_levels_json": key_levels_json,
                    "divergence_signals_json": divergence_signals_json,
                    "bias": bias,
                    "analyzed_at": analyzed_at,
                }
            ],
            index_elements=["analyzed_at"],
            update_fields=[
                "value",
                "trend_direction",
                "momentum",
                "key_levels_json",
                "divergence_signals_json",
                "bias",
            ],
        )
