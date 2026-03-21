"""Root conftest.py for the eTradie Engine test suite.

Provides shared fixtures used across all test modules. Every fixture
matches the real production class signatures in src/engine/ exactly.

Fixture categories:
    - Configuration (Settings, TAConfig, RAGConfig, ProcessorConfig)
    - Infrastructure mocks (FakeRedis, mock HttpClient, mock DB)
    - Domain helpers (candle factories are in tests/factories.py)
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fakeredis.aioredis import FakeRedis

from engine.config import Settings, TAConfig, RAGConfig
from engine.ta.constants import Timeframe


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Configuration fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def settings(monkeypatch) -> Settings:
    """Minimal valid Settings for testing (matches real Settings model)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/etradie_test")
    monkeypatch.setenv("APP_ENV", "testing")
    return Settings()


@pytest.fixture
def ta_config() -> TAConfig:
    """TAConfig with default timeframes (matches real TAConfig model)."""
    return TAConfig(
        enabled=True,
        primary_broker="mt5",
        fallback_broker="twelve_data",
        htf_timeframes=[Timeframe.W1, Timeframe.D1, Timeframe.H4, Timeframe.H1],
        ltf_timeframes=[Timeframe.M30, Timeframe.M15, Timeframe.M5, Timeframe.M1],
        candle_lookback_periods=500,
        backfill_on_startup=False,
    )


@pytest.fixture
def rag_config() -> RAGConfig:
    """RAGConfig with test-safe defaults (matches real RAGConfig model)."""
    return RAGConfig(
        enabled=False,
        embedding_provider="openai",
        embedding_model="text-embedding-3-large",
        openai_api_key="sk-test-fake-key",
        chroma_host="localhost",
        chroma_port=8000,
        retrieval_top_k=10,
        rerank_enabled=False,
        ingest_on_startup=False,
    )


# ---------------------------------------------------------------------------
# Infrastructure mocks
# ---------------------------------------------------------------------------

@pytest.fixture
async def fake_redis() -> AsyncGenerator[FakeRedis, None]:
    """In-memory Redis replacement for cache tests."""
    redis = FakeRedis(decode_responses=False)
    yield redis
    await redis.aclose()


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Mock HttpClient with async get/post/request/close methods."""
    client = MagicMock()
    client.get = AsyncMock(return_value={"status": "ok"})
    client.post = AsyncMock(return_value={"status": "ok"})
    client.request = AsyncMock(return_value={"status": "ok"})
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_db() -> MagicMock:
    """Mock DatabaseManager with async session context managers."""
    db = MagicMock()
    db.health_check = AsyncMock(return_value=True)
    db.close = AsyncMock()

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    db.session = MagicMock(return_value=mock_session)
    db.read_session = MagicMock(return_value=mock_session)
    return db


@pytest.fixture
def mock_broker() -> AsyncMock:
    """Mock BrokerBase with all abstract methods as AsyncMock.

    Matches the real BrokerBase interface:
        get_capabilities, fetch_candles, fetch_latest_candle,
        get_symbol_info, validate_symbol, health_check
    """
    broker = AsyncMock()
    broker.broker_id = "mt5"
    broker.health_check = AsyncMock(return_value=True)
    broker.shutdown = AsyncMock()
    return broker
