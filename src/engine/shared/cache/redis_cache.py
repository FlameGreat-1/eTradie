from __future__ import annotations

from typing import Any

import orjson
import redis.asyncio as aioredis

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import CACHE_OPERATIONS_TOTAL

logger = get_logger(__name__)


class RedisCache:
    def __init__(
        self,
        *,
        url: str,
        max_connections: int = 20,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        key_prefix: str = "etradie",
    ) -> None:
        self._key_prefix = key_prefix
        self._pool = aioredis.ConnectionPool.from_url(
            url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=False,
        )
        self._client = aioredis.Redis(connection_pool=self._pool)

    def _make_key(self, namespace: str, key: str) -> str:
        return f"{self._key_prefix}:{namespace}:{key}"

    async def get(self, namespace: str, key: str) -> Any | None:
        full_key = self._make_key(namespace, key)
        try:
            raw: bytes | None = await self._client.get(full_key)  # type: ignore[assignment]
            if raw is None:
                CACHE_OPERATIONS_TOTAL.labels(operation="get", status="miss").inc()
                return None
            CACHE_OPERATIONS_TOTAL.labels(operation="get", status="hit").inc()
            return orjson.loads(raw)
        except Exception:
            CACHE_OPERATIONS_TOTAL.labels(operation="get", status="error").inc()
            logger.exception("cache_get_error", key=full_key)
            return None

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: int,
    ) -> bool:
        full_key = self._make_key(namespace, key)
        try:
            raw = orjson.dumps(value)
            await self._client.set(full_key, raw, ex=ttl_seconds)
            CACHE_OPERATIONS_TOTAL.labels(operation="set", status="success").inc()
            return True
        except Exception:
            CACHE_OPERATIONS_TOTAL.labels(operation="set", status="error").inc()
            logger.exception("cache_set_error", key=full_key)
            return False

    async def delete(self, namespace: str, key: str) -> bool:
        full_key = self._make_key(namespace, key)
        try:
            await self._client.delete(full_key)
            CACHE_OPERATIONS_TOTAL.labels(operation="delete", status="success").inc()
            return True
        except Exception:
            CACHE_OPERATIONS_TOTAL.labels(operation="delete", status="error").inc()
            logger.exception("cache_delete_error", key=full_key)
            return False

    async def health_check(self) -> bool:
        try:
            result = await self._client.ping()
            return bool(result)
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
        await self._pool.disconnect()
