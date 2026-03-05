from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.economic import EconomicReleaseRow


class EconomicReleaseRepository(BaseRepository[EconomicReleaseRow]):
    model = EconomicReleaseRow
    _repo_name = "economic_release"

    async def get_latest_by_indicator(
        self,
        currency: str,
        indicator: str,
        limit: int = 5,
    ) -> Sequence[EconomicReleaseRow]:
        stmt = (
            select(self.model)
            .where(
                self.model.currency == currency,
                self.model.indicator == indicator,
            )
            .order_by(self.model.release_time.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def get_by_currency(
        self,
        currency: str,
        *,
        since: datetime | None = None,
        limit: int = 50,
    ) -> Sequence[EconomicReleaseRow]:
        stmt = (
            select(self.model)
            .where(self.model.currency == currency)
            .order_by(self.model.release_time.desc())
            .limit(limit)
        )
        if since:
            stmt = stmt.where(self.model.release_time >= since)
        return await self.execute_query(stmt)

    async def get_recent_high_impact(
        self,
        since: datetime,
    ) -> Sequence[EconomicReleaseRow]:
        stmt = (
            select(self.model)
            .where(
                self.model.release_time >= since,
                self.model.impact == "HIGH",
            )
            .order_by(self.model.release_time.desc())
        )
        return await self.execute_query(stmt)
