from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.central_bank import CentralBankEventRow


class CentralBankRepository(BaseRepository[CentralBankEventRow]):
    model = CentralBankEventRow
    _repo_name = "central_bank"

    async def get_latest_by_bank(self, bank: str, limit: int = 10) -> Sequence[CentralBankEventRow]:
        stmt = (
            select(self.model)
            .where(self.model.bank == bank)
            .order_by(self.model.event_timestamp.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def get_by_date_range(
        self,
        start: datetime,
        end: datetime,
        *,
        bank: str | None = None,
    ) -> Sequence[CentralBankEventRow]:
        stmt = (
            select(self.model)
            .where(
                self.model.event_timestamp >= start,
                self.model.event_timestamp <= end,
            )
            .order_by(self.model.event_timestamp.desc())
        )
        if bank:
            stmt = stmt.where(self.model.bank == bank)
        return await self.execute_query(stmt)

    async def get_rate_decisions(
        self,
        bank: str,
        limit: int = 5,
    ) -> Sequence[CentralBankEventRow]:
        stmt = (
            select(self.model)
            .where(
                self.model.bank == bank,
                self.model.event_type == "RATE_DECISION",
            )
            .order_by(self.model.event_timestamp.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)
