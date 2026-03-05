from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy import select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.calendar import CalendarEventRow


class CalendarRepository(BaseRepository[CalendarEventRow]):
    model = CalendarEventRow
    _repo_name = "calendar"

    async def get_upcoming(
        self,
        *,
        from_time: datetime,
        hours_ahead: int = 48,
        impact: str | None = None,
    ) -> Sequence[CalendarEventRow]:
        until = from_time + timedelta(hours=hours_ahead)
        stmt = (
            select(self.model)
            .where(
                self.model.event_time >= from_time,
                self.model.event_time <= until,
            )
            .order_by(self.model.event_time.asc())
        )
        if impact:
            stmt = stmt.where(self.model.impact == impact)
        return await self.execute_query(stmt)

    async def get_high_impact_within_window(
        self,
        *,
        center_time: datetime,
        window_minutes: int = 30,
    ) -> Sequence[CalendarEventRow]:
        start = center_time - timedelta(minutes=window_minutes)
        end = center_time + timedelta(minutes=window_minutes)
        stmt = (
            select(self.model)
            .where(
                self.model.event_time >= start,
                self.model.event_time <= end,
                self.model.impact == "HIGH",
            )
            .order_by(self.model.event_time.asc())
        )
        return await self.execute_query(stmt)

    async def get_by_currency(
        self,
        currency: str,
        *,
        from_time: datetime,
        limit: int = 50,
    ) -> Sequence[CalendarEventRow]:
        stmt = (
            select(self.model)
            .where(
                self.model.currency == currency,
                self.model.event_time >= from_time,
            )
            .order_by(self.model.event_time.asc())
            .limit(limit)
        )
        return await self.execute_query(stmt)
