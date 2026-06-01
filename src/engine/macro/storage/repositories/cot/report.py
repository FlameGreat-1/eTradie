from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import func, select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.cot import COTReportRow


class COTRepository(BaseRepository[COTReportRow]):
    model = COTReportRow
    _repo_name = "cot"

    async def get_52_week_net_range(
        self, currency: str,
    ) -> tuple[int, int]:
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

    async def get_previous_net(
        self, currency: str, current_date: date,
    ) -> int | None:
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
