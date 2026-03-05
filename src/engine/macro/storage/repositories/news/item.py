from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import delete, select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.news import NewsItemRow


class NewsRepository(BaseRepository[NewsItemRow]):
    model = NewsItemRow
    _repo_name = "news"

    async def get_recent(
        self,
        *,
        since: datetime,
        impact: str | None = None,
        limit: int = 100,
    ) -> Sequence[NewsItemRow]:
        stmt = (
            select(self.model)
            .where(self.model.published_at >= since)
            .order_by(self.model.published_at.desc())
            .limit(limit)
        )
        if impact:
            stmt = stmt.where(self.model.impact == impact)
        return await self.execute_query(stmt)

    async def exists_by_hash(self, dedupe_hash: str) -> bool:
        stmt = select(self.model.id).where(self.model.dedupe_hash == dedupe_hash).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def purge_older_than(self, cutoff: datetime) -> int:
        stmt = delete(self.model).where(self.model.published_at < cutoff)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount or 0
