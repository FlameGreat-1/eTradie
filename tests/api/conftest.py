"""Fixtures for dashboard API integration tests.

Provides a real FastAPI app with:
- Real PostgreSQL (analysis_outputs + analysis_audit_logs tables)
- Real Redis cache
- Real ChromaDB (embeddings already loaded in Docker)
- Mocked external services (TA broker, Processor LLM) that require
  live connections not available in test environment
- httpx.AsyncClient for making requests
- Seed data for query/filter tests

Tests are skipped automatically if infrastructure is not available.
Run with: pytest tests/api/ -v -m integration
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://etradie:etradie_dev@localhost:5432/etradie",
)
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
_CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))


def _check_db() -> bool:
    try:
        import asyncio
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


def _check_redis() -> bool:
    try:
        import redis
        r = redis.from_url(_REDIS_URL, socket_timeout=2)
        r.ping()
        r.close()
        return True
    except Exception:
        return False


def _check_chroma() -> bool:
    try:
        import httpx
        resp = httpx.get(f"http://{_CHROMA_HOST}:{_CHROMA_PORT}/api/v1/heartbeat", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


DB_AVAILABLE = _check_db()
REDIS_AVAILABLE = _check_redis()
CHROMA_AVAILABLE = _check_chroma()

skip_no_infra = pytest.mark.skipif(
    not (DB_AVAILABLE and REDIS_AVAILABLE),
    reason="PostgreSQL and/or Redis not available",
)


@pytest_asyncio.fixture
async def app_client() -> AsyncGenerator[AsyncClient, None]:
    """Create a real FastAPI app with real infrastructure and return
    an httpx.AsyncClient connected to it.

    Uses real PostgreSQL, Redis, and ChromaDB (if available).
    Mocks only:
    - MT5 broker client (no live MT5 terminal in test environment)
    - Scheduler (not started, no background jobs)
    """
    if not DB_AVAILABLE:
        pytest.skip("PostgreSQL not available")
    if not REDIS_AVAILABLE:
        pytest.skip("Redis not available")

    # Build environment overrides. Read real keys from environment
    # so the app connects to real infrastructure.
    env_overrides = {
        "DATABASE_URL": _DB_URL,
        "REDIS_URL": _REDIS_URL,
        "APP_ENV": "testing",
        "APP_LOG_LEVEL": "ERROR",
        "JSON_LOGS": "false",
        # RAG: connect to real ChromaDB with existing embeddings.
        # Do NOT re-ingest on startup (data already loaded).
        "RAG_ENABLED": "true" if CHROMA_AVAILABLE else "false",
        "RAG_INGEST_ON_STARTUP": "false",
        "RAG_CHROMA_HOST": _CHROMA_HOST,
        "RAG_CHROMA_PORT": str(_CHROMA_PORT),
        # Processor config (real provider for config endpoint tests).
        "PROCESSOR_LLM_PROVIDER": "anthropic",
        "PROCESSOR_MODEL_NAME": "claude-sonnet-4-20250514",
    }

    # Pass through real API keys from environment if they exist.
    # These are needed for RAG embeddings and processor LLM.
    for key in [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "RAG_OPENAI_API_KEY",
        "NEWSAPI_API_KEY",
        "TWELVEDATA_API_KEY",
        "TRADINGECONOMICS_API_KEY",
        "FRED_API_KEY",
    ]:
        val = os.getenv(key, "")
        if val:
            env_overrides[key] = val

    # Ensure at least a placeholder for required keys in testing mode.
    # Settings validator skips key checks for APP_ENV=testing.
    if "ANTHROPIC_API_KEY" not in env_overrides:
        env_overrides["ANTHROPIC_API_KEY"] = "sk-test-placeholder"

    from unittest.mock import patch
    with patch.dict(os.environ, env_overrides):
        # Clear cached settings so they pick up test env vars.
        from engine.config import get_settings, get_rag_config
        get_settings.cache_clear()
        get_rag_config.cache_clear()

        from engine.main import create_app
        app = create_app()

        # Ensure tables exist.
        async with app.router.lifespan_context(app):
            container = app.state.container

            # Create processor tables if they don't exist.
            from engine.processor.storage.schemas.processor_schema import ProcessorBase
            async with container.db.engine.begin() as conn:
                await conn.run_sync(ProcessorBase.metadata.create_all)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                # Attach container to client for seed data access.
                client._container = container  # type: ignore[attr-defined]
                yield client


@pytest_asyncio.fixture
async def seeded_client(app_client: AsyncClient) -> AsyncClient:
    """app_client with seed analysis data inserted for query tests.

    Inserts 5 analysis rows with varying pairs, grades, statuses,
    and providers for testing filters, pagination, and stats.
    """
    container = app_client._container  # type: ignore[attr-defined]

    now = datetime.now(UTC)
    seed_rows = [
        {
            "analysis_id": f"TEST-SEED-{uuid4().hex[:8]}",
            "pair": "EURUSD",
            "direction": "LONG",
            "setup_grade": "A",
            "confluence_score": 8.5,
            "confidence": "0.87",
            "proceed_to_module_b": "YES",
            "rr_ratio": 3.0,
            "trading_style": "INTRADAY",
            "session": "LONDON_NY_OVERLAP",
            "llm_provider": "anthropic",
            "llm_model": "claude-sonnet-4-20250514",
            "status": "success",
            "duration_ms": 2500.0,
            "raw_output": {"trade_valid": True, "direction": "LONG"},
        },
        {
            "analysis_id": f"TEST-SEED-{uuid4().hex[:8]}",
            "pair": "EURUSD",
            "direction": "",
            "setup_grade": "REJECT",
            "confluence_score": 3.0,
            "confidence": "0.25",
            "proceed_to_module_b": "NO",
            "trading_style": "",
            "session": "",
            "llm_provider": "anthropic",
            "llm_model": "claude-sonnet-4-20250514",
            "status": "no_setup",
            "duration_ms": 1800.0,
            "raw_output": {"trade_valid": False},
        },
        {
            "analysis_id": f"TEST-SEED-{uuid4().hex[:8]}",
            "pair": "GBPUSD",
            "direction": "SHORT",
            "setup_grade": "B",
            "confluence_score": 7.0,
            "confidence": "0.72",
            "proceed_to_module_b": "YES",
            "rr_ratio": 2.0,
            "trading_style": "SWING",
            "session": "LONDON_OPEN",
            "llm_provider": "openai",
            "llm_model": "gpt-4o",
            "status": "success",
            "duration_ms": 3200.0,
            "raw_output": {"trade_valid": True, "direction": "SHORT"},
        },
        {
            "analysis_id": f"TEST-SEED-{uuid4().hex[:8]}",
            "pair": "USDJPY",
            "direction": "LONG",
            "setup_grade": "A",
            "confluence_score": 9.0,
            "confidence": "0.92",
            "proceed_to_module_b": "YES",
            "rr_ratio": 4.0,
            "trading_style": "INTRADAY",
            "session": "TOKYO_OPEN",
            "llm_provider": "anthropic",
            "llm_model": "claude-sonnet-4-20250514",
            "status": "success",
            "duration_ms": 2100.0,
            "raw_output": {"trade_valid": True, "direction": "LONG"},
        },
        {
            "analysis_id": f"TEST-SEED-{uuid4().hex[:8]}",
            "pair": "EURUSD",
            "direction": "",
            "setup_grade": "",
            "confluence_score": 0.0,
            "confidence": "0.0",
            "proceed_to_module_b": "NO",
            "trading_style": "",
            "session": "",
            "llm_provider": "anthropic",
            "llm_model": "claude-sonnet-4-20250514",
            "status": "llm_error",
            "error_message": "LLM provider timeout after 60s",
            "duration_ms": 60000.0,
            "raw_output": {},
        },
    ]

    from engine.processor.storage.schemas.processor_schema import AnalysisOutputRow

    async with container.db.session() as session:
        for i, row_data in enumerate(seed_rows):
            row = AnalysisOutputRow(
                id=uuid4(),
                created_at=now - timedelta(hours=len(seed_rows) - i),
                **row_data,
            )
            session.add(row)
        await session.commit()

    # Store seed IDs on the client for assertions.
    app_client._seed_analysis_ids = [r["analysis_id"] for r in seed_rows]  # type: ignore[attr-defined]
    app_client._seed_count = len(seed_rows)  # type: ignore[attr-defined]

    return app_client
