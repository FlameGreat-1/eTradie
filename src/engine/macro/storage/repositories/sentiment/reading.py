from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.sentiment import SentimentReadingRow


class SentimentRepository(BaseRepository[SentimentReadingRow]):
    model = SentimentReadingRow
    _repo_name = "sentiment"

    async def get_latest_by_currency(
        self, currency: str,
    ) -> SentimentReadingRow | None:
        stmt = (
            select(self.model)
            .where(
                self.model.currency == currency,
            )
            .order_by(self.model.collected_at.desc())
            .limit(1)
        )
        result = await self.execute_query(stmt)
        return result[0] if result else None

    async def get_all_latest(
        self,
    ) -> Sequence[SentimentReadingRow]:
        """Get the most recent sentiment reading for each currency."""
        stmt = (
            select(self.model)
            .order_by(self.model.currency.asc())
        )
        return await self.execute_query(stmt)
