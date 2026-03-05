from __future__ import annotations

import time
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import Select, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import DB_QUERY_DURATION

logger = get_logger(__name__)

ModelT = TypeVar("ModelT", bound=DeclarativeBase)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]
    _repo_name: str = "base"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _observe(self, operation: str, start: float) -> None:
        DB_QUERY_DURATION.labels(
            repository=self._repo_name, operation=operation,
        ).observe(time.monotonic() - start)

    async def get_by_id(self, record_id: Any) -> ModelT | None:
        start = time.monotonic()
        result = await self._session.get(self.model, record_id)
        self._observe("get_by_id", start)
        return result

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelT]:
        start = time.monotonic()
        stmt = select(self.model).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        self._observe("list_all", start)
        return result.scalars().all()

    async def add(self, instance: ModelT) -> ModelT:
        start = time.monotonic()
        self._session.add(instance)
        await self._session.flush()
        self._observe("add", start)
        return instance

    async def add_many(self, instances: Sequence[ModelT]) -> int:
        start = time.monotonic()
        self._session.add_all(instances)
        await self._session.flush()
        self._observe("add_many", start)
        return len(instances)

    async def upsert(
        self,
        values: dict[str, Any],
        *,
        index_elements: list[str],
        update_fields: list[str] | None = None,
    ) -> None:
        start = time.monotonic()
        stmt = pg_insert(self.model).values(**values)
        if update_fields:
            update_dict = {f: stmt.excluded[f] for f in update_fields}
            stmt = stmt.on_conflict_do_update(
                index_elements=index_elements,
                set_=update_dict,
            )
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
        await self._session.execute(stmt)
        await self._session.flush()
        self._observe("upsert", start)

    async def bulk_upsert(
        self,
        rows: list[dict[str, Any]],
        *,
        index_elements: list[str],
        update_fields: list[str] | None = None,
    ) -> int:
        if not rows:
            return 0
        start = time.monotonic()
        stmt = pg_insert(self.model).values(rows)
        if update_fields:
            update_dict = {f: stmt.excluded[f] for f in update_fields}
            stmt = stmt.on_conflict_do_update(
                index_elements=index_elements,
                set_=update_dict,
            )
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
        result = await self._session.execute(stmt)
        await self._session.flush()
        self._observe("bulk_upsert", start)
        return result.rowcount  # type: ignore[return-value]

    async def delete_by_id(self, record_id: Any) -> bool:
        start = time.monotonic()
        stmt = delete(self.model).where(self.model.id == record_id)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        await self._session.flush()
        self._observe("delete_by_id", start)
        return (result.rowcount or 0) > 0

    async def count(self, stmt: Select[Any] | None = None) -> int:
        start = time.monotonic()
        if stmt is None:
            count_stmt = select(func.count()).select_from(self.model)
        else:
            count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await self._session.execute(count_stmt)
        self._observe("count", start)
        return result.scalar_one()

    async def execute_query(self, stmt: Select[Any]) -> Sequence[ModelT]:
        start = time.monotonic()
        result = await self._session.execute(stmt)
        self._observe("execute_query", start)
        return result.scalars().all()
