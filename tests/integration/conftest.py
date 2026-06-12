"""Integration test fixtures with real PostgreSQL and Redis.

These fixtures connect to actual infrastructure. Tests are skipped
automatically if the services are not available.

Required environment variables:
    DATABASE_URL: PostgreSQL connection string (asyncpg)
    REDIS_URL: Redis connection string

Run integration tests:
    pytest tests/integration/ -v -m integration

Skip integration tests:
    pytest tests/ -v -m "not integration"
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://etradie:etradie_dev@localhost:5432/etradie",
)
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _check_db_available() -> bool:
    """Check if PostgreSQL is reachable (sync check at import time)."""
    try:
        import asyncpg

        async def _ping():
            url = _DB_URL.replace("postgresql+asyncpg://", "postgresql://")
            conn = await asyncpg.connect(url, timeout=3)
            await conn.close()

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_ping())
        finally:
            loop.close()
        return True
    except Exception:
        return False


def _check_redis_available() -> bool:
    """Check if Redis is reachable."""
    try:
        import redis

        r = redis.from_url(_REDIS_URL, socket_timeout=2)
        r.ping()
        r.close()
        return True
    except Exception:
        return False


DB_AVAILABLE = _check_db_available()
REDIS_AVAILABLE = _check_redis_available()

skip_no_db = pytest.mark.skipif(not DB_AVAILABLE, reason="PostgreSQL not available")
skip_no_redis = pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")


@pytest_asyncio.fixture
async def db_manager() -> AsyncGenerator:
    """Real DatabaseManager connected to PostgreSQL."""
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL not available")

    from engine.shared.db.connection import DatabaseManager

    mgr = DatabaseManager(
        url=_DB_URL,
        pool_size=2,
        max_overflow=2,
        pool_timeout=10,
        pool_recycle=300,
        echo=False,
    )
    yield mgr
    await mgr.close()


@pytest_asyncio.fixture
async def db_session(db_manager):
    """Async DB session with automatic rollback after each test."""

    async with db_manager.session() as session:
        yield session
        # Session auto-commits on success; rollback on exception.
        # For test isolation, we rely on each test cleaning up its own data
        # or using unique identifiers.


@pytest_asyncio.fixture
async def redis_cache() -> AsyncGenerator:
    """Real RedisCache connected to Redis."""
    if not REDIS_AVAILABLE:
        pytest.skip("Redis not available")

    from engine.shared.cache.redis_cache import RedisCache

    cache = RedisCache(
        url=_REDIS_URL,
        max_connections=5,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
    )
    yield cache
    await cache.close()
