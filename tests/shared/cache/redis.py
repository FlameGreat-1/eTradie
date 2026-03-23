import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import ConnectionError, TimeoutError

from engine.shared.cache.redis_cache import MAX_CACHE_VALUE_SIZE, RedisCache
from engine.shared.exceptions import CacheConnectionError, CacheTimeoutError, CacheValidationError


@pytest.fixture
def mock_pool():
    with patch("redis.asyncio.ConnectionPool.from_url") as mock:
        yield mock


@pytest.fixture
def mock_redis_client():
    with patch("redis.asyncio.Redis") as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def cache(mock_pool, mock_redis_client):
    return RedisCache(url="redis://localhost:6379/0", max_retries=1)


def test_url_validation_success():
    """Valid Redis URLs should pass."""
    RedisCache(url="redis://localhost:6379/1")
    RedisCache(url="rediss://localhost:6379/1")


def test_url_validation_failure():
    """Invalid URLs must raise CacheConnectionError."""
    with pytest.raises(CacheConnectionError):
        RedisCache(url="http://localhost:6379")


@pytest.mark.asyncio
async def test_get_success(cache, mock_redis_client):
    """Cache hit string returns JSON parsed dictionary."""
    mock_redis_client.get.return_value = b'{"hello": "world"}'
    
    result = await cache.get("test_ns", "test_key")
    
    # Prefix defaults to 'etradie'
    mock_redis_client.get.assert_called_once_with("etradie:test_ns:test_key")
    assert result == {"hello": "world"}


@pytest.mark.asyncio
async def test_get_miss(cache, mock_redis_client):
    """Cache miss returns None without error."""
    mock_redis_client.get.return_value = None
    result = await cache.get("test_ns", "test_key")
    assert result is None


@pytest.mark.asyncio
async def test_get_namespace_validation(cache):
    """Invalid namespaces fail validation immediately."""
    with pytest.raises(CacheValidationError):
        await cache.get("", "key")
    with pytest.raises(CacheValidationError):
        await cache.get("namespace_too_long_" * 10, "key")
    with pytest.raises(CacheValidationError):
        await cache.get("invalid/chars", "key")


@pytest.mark.asyncio
async def test_get_key_validation(cache):
    """Invalid keys fail validation immediately."""
    with pytest.raises(CacheValidationError):
        await cache.get("ns", "")
    with pytest.raises(CacheValidationError):
        await cache.get("ns", "key with space")


@pytest.mark.asyncio
async def test_set_success(cache, mock_redis_client):
    """Valid dictionary value persists correctly."""
    mock_redis_client.set.return_value = True
    
    result = await cache.set("ns", "key", {"foo": "bar"}, ttl_seconds=60)
    
    mock_redis_client.set.assert_called_once_with(
        "etradie:ns:key",
        b'{"foo":"bar"}',
        ex=60,
    )
    assert result is True


@pytest.mark.asyncio
async def test_set_value_size_limit(cache):
    """Values exceeding 10MB limit fail validation."""
    large_string = "a" * (MAX_CACHE_VALUE_SIZE + 1)
    with pytest.raises(CacheValidationError, match="exceeds maximum"):
        await cache.set("ns", "key", large_string, 60)


@pytest.mark.asyncio
async def test_set_ttl_validation(cache):
    """Negative TTLs are rejected."""
    with pytest.raises(CacheValidationError, match="positive"):
        await cache.set("ns", "key", "val", -1)


@pytest.mark.asyncio
async def test_delete_success(cache, mock_redis_client):
    "Delete operates against correct key."
    mock_redis_client.delete.return_value = 1
    
    result = await cache.delete("ns", "key")
    
    mock_redis_client.delete.assert_called_once_with("etradie:ns:key")
    assert result is True


@pytest.mark.asyncio
async def test_health_check_success(cache, mock_redis_client):
    """Ping success means healthy."""
    mock_redis_client.ping.return_value = True
    assert await cache.health_check() is True


@pytest.mark.asyncio
async def test_health_check_failure(cache, mock_redis_client):
    """Ping failure means unhealthy."""
    mock_redis_client.ping.side_effect = ConnectionError("Disconnected")
    assert await cache.health_check() is False


@pytest.mark.asyncio
async def test_retry_on_timeout(cache, mock_redis_client):
    """Cache operations must retry transient errors."""
    cache = RedisCache(url="redis://localhost:6379/0", max_retries=2)
    
    # First fails with timeout, second succeeds
    mock_redis_client.get.side_effect = [TimeoutError("Timeout"), b'{"success": true}']
    
    result = await cache.get("ns", "key")
    
    assert mock_redis_client.get.call_count == 2
    assert result == {"success": True}


@pytest.mark.asyncio
async def test_exhausted_retries(cache, mock_redis_client):
    """Exhausted retries eventually raise connection error."""
    cache = RedisCache(url="redis://localhost:6379/0", max_retries=2)
    
    # Always fail
    mock_redis_client.get.side_effect = ConnectionError("Offline")
    
    with pytest.raises(CacheConnectionError):
        await cache.get("ns", "key")
    
    assert mock_redis_client.get.call_count == 2


@pytest.mark.asyncio
async def test_close(cache, mock_redis_client):
    """Graceful shutdown should close pool and client."""
    cache._pool.disconnect = AsyncMock()
    await cache.close()
    
    mock_redis_client.aclose.assert_called_once()
    cache._pool.disconnect.assert_called_once()
