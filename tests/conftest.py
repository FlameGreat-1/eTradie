import asyncio
from typing import AsyncGenerator

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import AsyncClient

from engine.config import ProcessorConfig, RAGConfig, Settings, TAConfig
from engine.main import create_app
from engine.shared.http.client import HttpClient


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/test",
        redis_url="redis://localhost:6379/1",
        api_rate_limit_per_minute=60,
        api_environment="testing",
        security_api_key="test_api_key",
    )


@pytest.fixture
def ta_config() -> TAConfig:
    return TAConfig()


@pytest.fixture
def rag_config() -> RAGConfig:
    return RAGConfig(
        vector_store_url="http://localhost:8000",
        embedding_provider="local",
        embedding_model="test-model",
    )


@pytest.fixture
def processor_config() -> ProcessorConfig:
    return ProcessorConfig(
        llm_provider="anthropic",
        anthropic_api_key="sk-ant-test-key",
        model_name="claude-sonnet-test",
    )


@pytest.fixture
async def mock_redis() -> AsyncGenerator[FakeRedis, None]:
    redis = FakeRedis(decode_responses=False)
    yield redis
    await redis.aclose()


@pytest.fixture
def mock_http_client() -> HttpClient:
    # This will be patched to use aioresponses where needed
    return HttpClient(max_retries=0)


@pytest.fixture
async def app_client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    # Override app container dependencies with mocks in individual tests if needed
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
