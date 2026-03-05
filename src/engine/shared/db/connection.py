from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import DB_CONNECTION_POOL_SIZE

logger = get_logger(__name__)


class DatabaseManager:
    def __init__(
        self,
        *,
        url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        echo: bool = False,
    ) -> None:
        self._engine: AsyncEngine = create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,
            echo=echo,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @asynccontextmanager
    async def read_session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session

    async def health_check(self) -> bool:
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            logger.exception("db_health_check_failed")
            return False

    def update_pool_metrics(self) -> None:
        pool = self._engine.pool
        if pool is not None:
            DB_CONNECTION_POOL_SIZE.labels(state="checked_in").set(pool.checkedin())
            DB_CONNECTION_POOL_SIZE.labels(state="checked_out").set(pool.checkedout())
            DB_CONNECTION_POOL_SIZE.labels(state="overflow").set(pool.overflow())

    async def close(self) -> None:
        await self._engine.dispose()
        logger.info("db_connection_closed")
