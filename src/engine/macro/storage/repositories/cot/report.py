from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import select

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
                self.model.report_date,
            )
            .distinct(self.model.currency)
            .order_by(self.model.currency, self.model.report_date.desc())
            .subquery()
        )
        stmt = (
            select(self.model)
            .join(
                subq,
                (self.model.currency == subq.c.currency)
                & (self.model.report_date == subq.c.report_date),
            )
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
