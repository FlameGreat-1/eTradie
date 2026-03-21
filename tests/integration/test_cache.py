"""Integration tests for RedisCache against real Redis."""

import asyncio
import time

import pytest

from tests.integration.conftest import skip_no_redis

pytestmark = [pytest.mark.integration, skip_no_redis]


@pytest.mark.asyncio
async def test_health_check(redis_cache):
    """RedisCache.health_check() returns True with live Redis."""
    result = await redis_cache.health_check()
    assert result is True


@pytest.mark.asyncio
async def test_set_and_get(redis_cache):
    """Set a value and retrieve it."""
    await redis_cache.set("integration", "test_key_1", {"hello": "world"}, ttl_seconds=30)
    result = await redis_cache.get("integration", "test_key_1")
    assert result == {"hello": "world"}

    # Cleanup
    await redis_cache.delete("integration", "test_key_1")


@pytest.mark.asyncio
async def test_get_miss_returns_none(redis_cache):
    """Cache miss returns None."""
    result = await redis_cache.get("integration", "nonexistent_key_xyz")
    assert result is None


@pytest.mark.asyncio
async def test_delete(redis_cache):
    """Delete removes the key."""
    await redis_cache.set("integration", "delete_me", {"temp": True}, ttl_seconds=30)
    deleted = await redis_cache.delete("integration", "delete_me")
    assert deleted is True

    result = await redis_cache.get("integration", "delete_me")
    assert result is None


@pytest.mark.asyncio
async def test_ttl_expiration(redis_cache):
    """Value expires after TTL."""
    await redis_cache.set("integration", "expires_fast", {"ttl": 1}, ttl_seconds=1)

    # Should exist immediately.
    result = await redis_cache.get("integration", "expires_fast")
    assert result == {"ttl": 1}

    # Wait for expiration.
    await asyncio.sleep(1.5)

    result = await redis_cache.get("integration", "expires_fast")
    assert result is None


@pytest.mark.asyncio
async def test_complex_nested_data(redis_cache):
    """Complex nested dict round-trips correctly through JSON serialization."""
    data = {
        "symbol": "EURUSD",
        "analysis": {
            "smc_candidates": [
                {"pattern": "TURTLE_SOUP_LONG", "entry": 1.1000, "sl": 1.0950},
            ],
            "alignment": {"htf": "BULLISH", "ltf": "BULLISH"},
        },
        "scores": [8.5, 7.2, 9.0],
        "active": True,
        "count": 42,
    }

    await redis_cache.set("integration", "complex_data", data, ttl_seconds=30)
    result = await redis_cache.get("integration", "complex_data")

    assert result["symbol"] == "EURUSD"
    assert result["analysis"]["smc_candidates"][0]["pattern"] == "TURTLE_SOUP_LONG"
    assert result["scores"] == [8.5, 7.2, 9.0]
    assert result["active"] is True
    assert result["count"] == 42

    # Cleanup
    await redis_cache.delete("integration", "complex_data")


@pytest.mark.asyncio
async def test_overwrite_existing_key(redis_cache):
    """Setting the same key overwrites the previous value."""
    await redis_cache.set("integration", "overwrite_me", {"v": 1}, ttl_seconds=30)
    await redis_cache.set("integration", "overwrite_me", {"v": 2}, ttl_seconds=30)

    result = await redis_cache.get("integration", "overwrite_me")
    assert result == {"v": 2}

    # Cleanup
    await redis_cache.delete("integration", "overwrite_me")


@pytest.mark.asyncio
async def test_namespace_validation(redis_cache):
    """Invalid namespaces are rejected."""
    from engine.shared.exceptions import CacheValidationError

    with pytest.raises(CacheValidationError):
        await redis_cache.get("", "key")

    with pytest.raises(CacheValidationError):
        await redis_cache.get("invalid/chars", "key")
