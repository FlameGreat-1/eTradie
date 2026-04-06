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
import time
from datetime import UTC, datetime, timedelta
from typing import AsyncGenerator
from uuid import uuid4

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Deterministic JWT secret for tests. Must be set in env_overrides
# so the Python engine's auth module can verify tokens we generate.
TEST_JWT_SECRET = "test-secret-key-for-jwt-signing-must-be-long-enough-64chars-ok"
TEST_JWT_ISSUER = "etradie"


def _make_test_jwt(
    user_id: str = "test-user-001",
    username: str = "testuser",
    role: str = "etradie",
    expires_in: int = 3600,
) -> str:
    """Generate a valid JWT token for test requests.

    Args:
        user_id: The sub claim (user ID).
        username: The username claim.
        role: 'admin' or 'etradie' (regular user).
        expires_in: Token lifetime in seconds.

    Returns:
        Encoded JWT string.
    """
    now = int(time.time())
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iss": TEST_JWT_ISSUER,
        "iat": now,
        "exp": now + expires_in,
    }
    return pyjwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://etradie:etradie_dev@localhost:5432/etradie",
)
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_CHROMA_HOST = os.getenv("CHROMA_HOST") or os.getenv("RAG_CHROMA_HOST") or "localhost"
_CHROMA_PORT = int(os.getenv("CHROMA_PORT") or os.getenv("RAG_CHROMA_PORT") or "8000")
_CHROMA_AUTH_TOKEN = os.getenv("RAG_CHROMA_AUTH_TOKEN", "") or os.getenv("CHROMA_SERVER_AUTH_CREDENTIALS", "")


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


def _check_chroma() -> tuple[bool, str]:
    """Check ChromaDB availability and return (available, working_host).

    Inside Docker the service hostname is 'chromadb' (from docker-compose).
    Locally it may be 'localhost'. Tries the env var host first, then
    common Docker/local fallbacks.

    ChromaDB may have token authentication enabled (docker-compose sets
    CHROMA_SERVER_AUTHN_PROVIDER). The auth token is read from
    RAG_CHROMA_AUTH_TOKEN to match the app's RAGConfig.chroma_auth_token.
    """
    import httpx

    # Candidate hosts: env var first, then Docker service name, then localhost.
    hosts = [_CHROMA_HOST]
    if _CHROMA_HOST != "chromadb":
        hosts.append("chromadb")
    if _CHROMA_HOST != "localhost":
        hosts.append("localhost")

    # Build auth headers if token is configured.
    headers = {}
    if _CHROMA_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {_CHROMA_AUTH_TOKEN}"

    for host in hosts:
        try:
            resp = httpx.get(
                f"http://{host}:{_CHROMA_PORT}/api/v2/heartbeat",
                headers=headers,
                timeout=3,
            )
            if resp.status_code == 200:
                return True, host
        except Exception:
            continue
    return False, _CHROMA_HOST


DB_AVAILABLE = _check_db()
REDIS_AVAILABLE = _check_redis()
CHROMA_AVAILABLE, _CHROMA_HOST = _check_chroma()

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

    # Build environment overrides. Start with infrastructure URLs,
    # then pass through ALL existing env vars so the test app uses
    # the exact same configuration as the running Docker services.
    env_overrides = {
        "DATABASE_URL": _DB_URL,
        "REDIS_URL": _REDIS_URL,
        "APP_ENV": "testing",
        "APP_LOG_LEVEL": "ERROR",
        "JSON_LOGS": "false",
        # JWT auth: deterministic secret so tests can generate valid tokens.
        "AUTH_JWT_SECRET": TEST_JWT_SECRET,
        "AUTH_ISSUER": TEST_JWT_ISSUER,
        # RAG: connect to real ChromaDB with existing embeddings.
        # Do NOT re-ingest on startup (data already loaded).
        "RAG_ENABLED": "true" if CHROMA_AVAILABLE else "false",
        "RAG_INGEST_ON_STARTUP": "false",
        "RAG_CHROMA_HOST": _CHROMA_HOST,
        "RAG_CHROMA_PORT": str(_CHROMA_PORT),
        "RAG_CHROMA_AUTH_TOKEN": _CHROMA_AUTH_TOKEN,
    }

    # Pass through ALL RAG_ prefixed env vars from the environment.
    # This ensures the test uses whatever embedding provider is
    # currently configured (sentence_transformers or openai).
    # Critical: RAG_EMBEDDING_PROVIDER, RAG_EMBEDDING_MODEL,
    # RAG_EMBEDDING_DIMENSIONS must match the ChromaDB collections.
    for key, val in os.environ.items():
        if key.startswith("RAG_") and key not in env_overrides:
            env_overrides[key] = val

    # Pass through all API keys and processor config from environment.
    # This supports both sentence_transformers (no key needed) and
    # openai (needs RAG_OPENAI_API_KEY) embedding providers.
    for key in [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "NEWSAPI_API_KEY",
        "TWELVEDATA_API_KEY",
        "TRADINGECONOMICS_API_KEY",
        "FRED_API_KEY",
        "PROCESSOR_LLM_PROVIDER",
        "PROCESSOR_MODEL_NAME",
        "PROCESSOR_ANTHROPIC_API_KEY",
        "PROCESSOR_OPENAI_API_KEY",
        "PROCESSOR_GEMINI_API_KEY",
        "PROCESSOR_TEMPERATURE",
        "PROCESSOR_MAX_OUTPUT_TOKENS",
    ]:
        val = os.getenv(key, "")
        if val:
            env_overrides[key] = val

    # Ensure at least a placeholder for required keys in testing mode.
    # Settings validator skips key checks for APP_ENV=testing.
    if "ANTHROPIC_API_KEY" not in env_overrides and "PROCESSOR_ANTHROPIC_API_KEY" not in env_overrides:
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

            # Create processor tables (analysis_outputs, analysis_audit_logs,
            # llm_connections) if they don't exist.
            from engine.processor.storage.schemas.processor_schema import ProcessorBase
            async with container.db.engine.begin() as conn:
                await conn.run_sync(ProcessorBase.metadata.create_all)

            # Seed an active LLM connection for the test user so
            # per-user processor resolution works in endpoint tests.
            # Uses the same provider/model from the env-var processor
            # config so the LLM client can be built without errors.
            from engine.processor.storage.repositories.llm_connection_repository import LLMConnectionRepository
            test_user_id = "user-001"  # matches _user_headers JWT sub claim
            async with container.db.session() as session:
                repo = LLMConnectionRepository(session)
                existing = await repo.get_active(user_id=test_user_id)
                if existing is None:
                    cfg = container.processor_config
                    await repo.create(
                        user_id=test_user_id,
                        provider=cfg.llm_provider,
                        model_name=cfg.model_name,
                        api_key=cfg.get_active_api_key() or "sk-test-placeholder",
                        temperature=cfg.temperature,
                        max_output_tokens=cfg.max_output_tokens,
                        activate=True,
                    )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                # Attach container to client for seed data access.
                client._container = container  # type: ignore[attr-defined]
                # Attach default auth headers for convenience.
                client._admin_headers = {"Authorization": f"Bearer {_make_test_jwt(user_id='admin-001', username='admin', role='admin')}"}  # type: ignore[attr-defined]
                client._user_headers = {"Authorization": f"Bearer {_make_test_jwt(user_id='user-001', username='testuser', role='etradie')}"}  # type: ignore[attr-defined]
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
