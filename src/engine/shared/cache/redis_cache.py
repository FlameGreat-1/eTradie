from __future__ import annotations

import asyncio
import time
from typing import Any, Optional
from urllib.parse import urlparse

import orjson
import redis.asyncio as aioredis
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError,
    RedisError,
)

from engine.shared.exceptions import (
    CacheConnectionError,
    CacheError,
    CacheTimeoutError,
    CacheValidationError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    CACHE_OPERATIONS_TOTAL,
    CACHE_OPERATION_DURATION,
    CACHE_VALUE_SIZE,
)

logger = get_logger(__name__)

# Security: Maximum cache value size (10MB) to prevent memory exhaustion
MAX_CACHE_VALUE_SIZE = 10 * 1024 * 1024

# Maximum key/namespace length to prevent abuse
MAX_KEY_LENGTH = 256
MAX_NAMESPACE_LENGTH = 64


class RedisCache:
    """
    Production-grade Redis cache client with error handling and observability.
    
    Provides:
    - Namespaced key management
    - Automatic serialization/deserialization
    - Connection pooling with health monitoring
    - Retry logic for transient failures
    - Comprehensive metrics and logging
    - Input validation and security controls
    """

    def __init__(
        self,
        *,
        url: str,
        max_connections: int = 20,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        operation_timeout: float = 3.0,
        key_prefix: str = "etradie",
        max_retries: int = 3,
    ) -> None:
        self._validate_connection_url(url)
        
        self._key_prefix = key_prefix
        self._operation_timeout = operation_timeout
        self._max_retries = max_retries
        
        self._pool = aioredis.ConnectionPool.from_url(
            url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=False,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        self._client = aioredis.Redis(connection_pool=self._pool)
        
        logger.info(
            "redis_cache_initialized",
            extra={
                "max_connections": max_connections,
                "socket_timeout": socket_timeout,
                "operation_timeout": operation_timeout,
            },
        )

    @staticmethod
    def _validate_connection_url(url: str) -> None:
        """Validate Redis connection URL format."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or parsed.scheme not in ("redis", "rediss"):
                raise ValueError(f"Invalid Redis scheme: {parsed.scheme}")
            if not parsed.hostname:
                raise ValueError("Missing Redis hostname")
        except Exception as e:
            logger.error("invalid_redis_url", extra={"error": str(e)})
            raise CacheConnectionError(f"Invalid Redis URL: {e}") from e

    def _validate_namespace(self, namespace: str) -> None:
        """Validate namespace format and length."""
        if not namespace:
            raise CacheValidationError("Namespace cannot be empty")
        
        if len(namespace) > MAX_NAMESPACE_LENGTH:
            raise CacheValidationError(
                f"Namespace exceeds maximum length of {MAX_NAMESPACE_LENGTH}"
            )
        
        if not namespace.replace("_", "").replace("-", "").isalnum():
            raise CacheValidationError(
                "Namespace must contain only alphanumeric characters, hyphens, and underscores"
            )

    def _validate_key(self, key: str) -> None:
        """Validate key format and length."""
        if not key:
            raise CacheValidationError("Key cannot be empty")
        
        if len(key) > MAX_KEY_LENGTH:
            raise CacheValidationError(
                f"Key exceeds maximum length of {MAX_KEY_LENGTH}"
            )
        
        # Prevent key injection attacks
        if any(char in key for char in ("\n", "\r", " ")):
            raise CacheValidationError("Key contains invalid characters")

    def _make_key(self, namespace: str, key: str) -> str:
        """
        Construct namespaced cache key with validation.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            
        Returns:
            Full cache key
            
        Raises:
            CacheValidationError: On invalid namespace or key
        """
        self._validate_namespace(namespace)
        self._validate_key(key)
        return f"{self._key_prefix}:{namespace}:{key}"

    def _observe_operation(
        self,
        operation: str,
        status: str,
        start: float,
        value_size: Optional[int] = None,
    ) -> None:
        """Record cache operation metrics."""
        duration = time.monotonic() - start
        
        CACHE_OPERATIONS_TOTAL.labels(
            operation=operation,
            status=status,
        ).inc()
        
        CACHE_OPERATION_DURATION.labels(operation=operation).observe(duration)
        
        if value_size is not None:
            CACHE_VALUE_SIZE.labels(operation=operation).observe(value_size)

    async def _execute_with_retry(
        self,
        operation: str,
        func,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute Redis operation with exponential backoff retry.
        
        Args:
            operation: Operation name for logging
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Operation result
            
        Raises:
            CacheTimeoutError: On timeout
            CacheConnectionError: On connection failures
            CacheError: On other Redis errors
        """
        last_error = None
        base_delay = 0.1
        
        for attempt in range(self._max_retries):
            try:
                async with asyncio.timeout(self._operation_timeout):
                    return await func(*args, **kwargs)
                    
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    "cache_operation_timeout",
                    extra={
                        "operation": operation,
                        "attempt": attempt + 1,
                        "timeout": self._operation_timeout,
                    },
                )
                
            except (RedisConnectionError, RedisTimeoutError) as e:
                last_error = e
                logger.warning(
                    "cache_connection_error",
                    extra={
                        "operation": operation,
                        "attempt": attempt + 1,
                        "error": str(e),
                    },
                )
            
            if attempt < self._max_retries - 1:
                # Exponential backoff with jitter
                delay = base_delay * (2 ** attempt) * (1 + time.monotonic() % 0.1)
                await asyncio.sleep(delay)
        
        # All retries exhausted
        if isinstance(last_error, asyncio.TimeoutError):
            raise CacheTimeoutError(
                f"{operation} exceeded timeout of {self._operation_timeout}s"
            ) from last_error
        elif isinstance(last_error, (RedisConnectionError, RedisTimeoutError)):
            raise CacheConnectionError(f"{operation} connection failed") from last_error
        else:
            raise CacheError(f"{operation} failed after {self._max_retries} retries") from last_error

    async def get(
        self,
        namespace: str,
        key: str,
        *,
        trace_id: Optional[str] = None,
    ) -> Any | None:
        """
        Retrieve value from cache.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            trace_id: Optional trace ID for correlation
            
        Returns:
            Cached value or None if not found
            
        Raises:
            CacheValidationError: On invalid namespace or key
            CacheTimeoutError: On timeout
            CacheConnectionError: On connection failures
        """
        start = time.monotonic()
        full_key = self._make_key(namespace, key)
        
        try:
            raw: bytes | None = await self._execute_with_retry(
                "get",
                self._client.get,
                full_key,
            )
            
            if raw is None:
                self._observe_operation("get", "miss", start)
                logger.debug(
                    "cache_miss",
                    extra={
                        "namespace": namespace,
                        "key": key,
                        "trace_id": trace_id,
                    },
                )
                return None
            
            value = orjson.loads(raw)
            self._observe_operation("get", "hit", start, value_size=len(raw))
            
            logger.debug(
                "cache_hit",
                extra={
                    "namespace": namespace,
                    "key": key,
                    "size_bytes": len(raw),
                    "trace_id": trace_id,
                },
            )
            
            return value
            
        except (CacheValidationError, CacheTimeoutError, CacheConnectionError):
            self._observe_operation("get", "error", start)
            raise
            
        except RedisError as e:
            self._observe_operation("get", "error", start)
            logger.error(
                "cache_get_redis_error",
                extra={
                    "namespace": namespace,
                    "key": key,
                    "error": str(e),
                    "trace_id": trace_id,
                },
            )
            raise CacheError(f"Redis error during get: {e}") from e
            
        except Exception as e:
            self._observe_operation("get", "error", start)
            logger.exception(
                "cache_get_unexpected_error",
                extra={
                    "namespace": namespace,
                    "key": key,
                    "trace_id": trace_id,
                },
            )
            raise CacheError(f"Unexpected error during get: {e}") from e

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: int,
        *,
        trace_id: Optional[str] = None,
    ) -> bool:
        """
        Store value in cache with TTL.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl_seconds: Time-to-live in seconds
            trace_id: Optional trace ID for correlation
            
        Returns:
            True on success, False on failure
            
        Raises:
            CacheValidationError: On invalid namespace, key, or value size
            CacheTimeoutError: On timeout
            CacheConnectionError: On connection failures
        """
        start = time.monotonic()
        full_key = self._make_key(namespace, key)
        
        if ttl_seconds <= 0:
            raise CacheValidationError("TTL must be positive")
        
        try:
            raw = orjson.dumps(value)
            
            # Security: Validate value size
            if len(raw) > MAX_CACHE_VALUE_SIZE:
                raise CacheValidationError(
                    f"Value size {len(raw)} exceeds maximum of {MAX_CACHE_VALUE_SIZE} bytes"
                )
            
            await self._execute_with_retry(
                "set",
                self._client.set,
                full_key,
                raw,
                ex=ttl_seconds,
            )
            
            self._observe_operation("set", "success", start, value_size=len(raw))
            
            logger.debug(
                "cache_set_success",
                extra={
                    "namespace": namespace,
                    "key": key,
                    "size_bytes": len(raw),
                    "ttl_seconds": ttl_seconds,
                    "trace_id": trace_id,
                },
            )
            
            return True
            
        except (CacheValidationError, CacheTimeoutError, CacheConnectionError):
            self._observe_operation("set", "error", start)
            raise
            
        except RedisError as e:
            self._observe_operation("set", "error", start)
            logger.error(
                "cache_set_redis_error",
                extra={
                    "namespace": namespace,
                    "key": key,
                    "error": str(e),
                    "trace_id": trace_id,
                },
            )
            return False
            
        except Exception as e:
            self._observe_operation("set", "error", start)
            logger.exception(
                "cache_set_unexpected_error",
                extra={
                    "namespace": namespace,
                    "key": key,
                    "trace_id": trace_id,
                },
            )
            return False

    async def delete(
        self,
        namespace: str,
        key: str,
        *,
        trace_id: Optional[str] = None,
    ) -> bool:
        """
        Delete value from cache.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            trace_id: Optional trace ID for correlation
            
        Returns:
            True on success, False on failure
            
        Raises:
            CacheValidationError: On invalid namespace or key
        """
        start = time.monotonic()
        full_key = self._make_key(namespace, key)
        
        try:
            await self._execute_with_retry(
                "delete",
                self._client.delete,
                full_key,
            )
            
            self._observe_operation("delete", "success", start)
            
            logger.debug(
                "cache_delete_success",
                extra={
                    "namespace": namespace,
                    "key": key,
                    "trace_id": trace_id,
                },
            )
            
            return True
            
        except (CacheValidationError, CacheTimeoutError, CacheConnectionError):
            self._observe_operation("delete", "error", start)
            raise
            
        except Exception as e:
            self._observe_operation("delete", "error", start)
            logger.error(
                "cache_delete_error",
                extra={
                    "namespace": namespace,
                    "key": key,
                    "error": str(e),
                    "trace_id": trace_id,
                },
            )
            return False

    async def health_check(self) -> bool:
        """
        Check Redis connectivity with retry logic.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            result = await self._execute_with_retry(
                "health_check",
                self._client.ping,
            )
            logger.debug("cache_health_check_passed")
            return bool(result)
            
        except Exception as e:
            logger.error(
                "cache_health_check_failed",
                extra={"error": str(e)},
            )
            return False

    async def close(self) -> None:
        """Gracefully close Redis connections."""
        try:
            await self._client.aclose()
            await self._pool.disconnect()
            logger.info("redis_cache_closed")
        except Exception:
            logger.exception("redis_cache_close_failed")
            raise
