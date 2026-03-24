from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import func, select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.cot import COTReportRow


class COTRepository(BaseRepository[COTReportRow]):
    model = COTReportRow
    _repo_name = "cot"

    async def get_latest_by_currency(self, currency: str) -> COTReportRow | None:
        stmt = (
            select(self.model)
            .where(self.model.currency == currency)
            .order_by(self.model.report_date.desc())
            .limit(1)
        )
        result = await self.execute_query(stmt)
        return result[0] if result else None

    async def get_latest_all_currencies(self) -> Sequence[COTReportRow]:
        subq = (
            select(
                self.model.currency,
                func.max(self.model.report_date).label("max_date"),
            )
            .group_by(self.model.currency)
            .subquery()
        )
        stmt = select(self.model).join(
            subq,
            (self.model.currency == subq.c.currency)
            & (self.model.report_date == subq.c.max_date),
        )
        return await self.execute_query(stmt)

    async def get_wow_pair(
        self,
        currency: str,
    ) -> tuple[COTReportRow | None, COTReportRow | None]:
        stmt = (
            select(self.model)
            .where(self.model.currency == currency)
            .order_by(self.model.report_date.desc())
            .limit(2)
        )
        rows = await self.execute_query(stmt)
        current = rows[0] if len(rows) > 0 else None
        previous = rows[1] if len(rows) > 1 else None
        return current, previous

    async def get_history(
        self,
        currency: str,
        limit: int = 52,
    ) -> Sequence[COTReportRow]:
        stmt = (
            select(self.model)
            .where(self.model.currency == currency)
            .order_by(self.model.report_date.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def get_52_week_net_range(self, currency: str) -> tuple[int, int]:
        stmt = (
            select(
                func.min(self.model.non_commercial_net),
                func.max(self.model.non_commercial_net),
            )
            .where(self.model.currency == currency)
            .order_by(self.model.report_date.desc())
            .limit(52)
        )
        result = await self._session.execute(
            select(
                func.min(COTReportRow.non_commercial_net),
                func.max(COTReportRow.non_commercial_net),
            ).where(
                COTReportRow.currency == currency,
                COTReportRow.report_date >= func.current_date() - 365,
            )
        )
        row = result.one_or_none()
        if row and row[0] is not None and row[1] is not None:
            return int(row[0]), int(row[1])
        return 0, 0

    async def get_previous_net(self, currency: str, current_date: date) -> int | None:
        stmt = (
            select(self.model.non_commercial_net)
            .where(
                self.model.currency == currency,
                self.model.report_date < current_date,
            )
            .order_by(self.model.report_date.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        val = result.scalar_one_or_none()
        return int(val) if val is not None else None
