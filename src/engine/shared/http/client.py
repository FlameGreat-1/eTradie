from __future__ import annotations

import asyncio
import random
import time
from asyncio import Lock
from enum import StrEnum, unique
from typing import Any, Optional
from urllib.parse import urlparse

import aiohttp

from engine.shared.exceptions import (
    HttpClientError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    PROVIDER_ERRORS_TOTAL,
    PROVIDER_FETCH_DURATION,
    PROVIDER_FETCH_TOTAL,
    PROVIDER_RESPONSE_SIZE,
)

logger = get_logger(__name__)

# Security: Non-retryable HTTP status codes
_NON_RETRYABLE_STATUS = frozenset({400, 401, 403, 404, 405, 422})

# Security: Maximum response size (50MB) to prevent memory exhaustion
MAX_RESPONSE_SIZE = 50 * 1024 * 1024

# Security: Sensitive headers to sanitize in logs
_SENSITIVE_HEADERS = frozenset({
    "authorization",
    "api-key",
    "x-api-key",
    "cookie",
    "set-cookie",
    "proxy-authorization",
})


@unique
class CircuitState(StrEnum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class _CircuitBreaker:
    """
    Thread-safe circuit breaker implementation.
    
    Provides:
    - Automatic failure detection and recovery
    - Half-open state for gradual recovery
    - Configurable thresholds and timeouts
    """
    
    __slots__ = (
        "_failure_count",
        "_failure_threshold",
        "_half_open_max",
        "_half_open_successes",
        "_last_failure_time",
        "_lock",
        "_recovery_timeout",
        "_state",
    )

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max = half_open_max_calls
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_successes = 0
        self._last_failure_time: float = 0.0
        self._lock = Lock()  # Thread safety

    @property
    async def state(self) -> CircuitState:
        """Get current circuit state with automatic recovery check."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_successes = 0
                    logger.info(
                        "circuit_breaker_half_open",
                        extra={"recovery_timeout": self._recovery_timeout},
                    )
            return self._state

    async def record_success(self) -> None:
        """Record successful request."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self._half_open_max:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info("circuit_breaker_closed")
            else:
                self._failure_count = 0

    async def record_failure(self) -> None:
        """Record failed request."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_opened",
                    extra={
                        "failure_count": self._failure_count,
                        "threshold": self._failure_threshold,
                    },
                )


class HttpClient:
    """
    Production-grade HTTP client with resilience patterns.
    
    Provides:
    - Circuit breaker for fault isolation
    - Exponential backoff with jitter
    - Rate limit handling
    - Request/response size validation
    - Comprehensive metrics and logging
    - Trace context propagation
    """

    def __init__(
        self,
        *,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_max: float = 60.0,
        cb_failure_threshold: int = 5,
        cb_recovery_timeout: int = 60,
        cb_half_open_max: int = 3,
        max_response_size: int = MAX_RESPONSE_SIZE,
    ) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max
        self._max_response_size = max_response_size
        self._session: aiohttp.ClientSession | None = None
        self._circuit = _CircuitBreaker(
            failure_threshold=cb_failure_threshold,
            recovery_timeout=cb_recovery_timeout,
            half_open_max_calls=cb_half_open_max,
        )
        
        logger.info(
            "http_client_initialized",
            extra={
                "timeout_seconds": timeout_seconds,
                "max_retries": max_retries,
                "max_response_size": max_response_size,
            },
        )

    @staticmethod
    def _validate_url(url: str) -> None:
        """
        Validate URL format and security.
        
        Args:
            url: URL to validate
            
        Raises:
            ProviderValidationError: On invalid URL
        """
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme:
                raise ValueError("Missing URL scheme")
            
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Unsupported scheme: {parsed.scheme}")
            
            if not parsed.netloc:
                raise ValueError("Missing URL hostname")
            
            # Security: Prevent SSRF to internal networks
            if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
                logger.warning(
                    "localhost_url_detected",
                    extra={"url": url},
                )
                
        except Exception as e:
            raise ProviderValidationError(f"Invalid URL: {e}") from e

    @staticmethod
    def _sanitize_headers(headers: dict[str, str] | None) -> dict[str, str]:
        """
        Sanitize headers for logging (remove sensitive values).
        
        Args:
            headers: Request headers
            
        Returns:
            Sanitized headers safe for logging
        """
        if not headers:
            return {}
        
        return {
            k: "***REDACTED***" if k.lower() in _SENSITIVE_HEADERS else v
            for k, v in headers.items()
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                connector=aiohttp.TCPConnector(limit=100, limit_per_host=30),
            )
        return self._session

    def _backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter.
        
        Args:
            attempt: Retry attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = min(self._backoff_base * (2 ** attempt), self._backoff_max)
        jitter = random.uniform(0, delay * 0.5)  # noqa: S311
        return delay + jitter

    async def request(
        self,
        method: str,
        url: str,
        *,
        provider_name: str = "unknown",
        category: str = "unknown",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        trace_id: Optional[str] = None,
        timeout_override: Optional[int] = None,
    ) -> dict[str, Any] | list[Any] | str:
        """
        Execute HTTP request with retry logic and circuit breaker.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Target URL
            provider_name: Provider identifier for metrics/logging
            category: Request category for metrics/logging
            headers: Optional request headers
            params: Optional query parameters
            json_body: Optional JSON request body
            trace_id: Optional trace ID for distributed tracing
            timeout_override: Optional timeout override in seconds
            
        Returns:
            Response data (JSON dict/list or text string)
            
        Raises:
            ProviderValidationError: On invalid URL or parameters
            ProviderUnavailableError: On circuit breaker open or non-retryable errors
            ProviderTimeoutError: On timeout
            ProviderRateLimitError: On rate limit exhaustion
        """
        # Input validation
        self._validate_url(url)
        
        # Check circuit breaker state
        circuit_state = await self._circuit.state
        if circuit_state == CircuitState.OPEN:
            PROVIDER_ERRORS_TOTAL.labels(
                provider=provider_name,
                category=category,
                error_type="circuit_open",
            ).inc()
            
            logger.error(
                "circuit_breaker_open",
                extra={
                    "provider": provider_name,
                    "url": url,
                    "trace_id": trace_id,
                },
            )
            
            raise ProviderUnavailableError(
                f"Circuit breaker OPEN for {provider_name}",
                details={
                    "provider": provider_name,
                    "url": url,
                    "circuit_state": circuit_state,
                },
            )

        last_exc: Exception | None = None
        session = await self._get_session()
        
        # Apply timeout override if provided
        timeout = (
            aiohttp.ClientTimeout(total=timeout_override)
            if timeout_override
            else self._timeout
        )

        for attempt in range(self._max_retries + 1):
            start = time.monotonic()
            
            try:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    timeout=timeout,
                ) as resp:
                    elapsed = time.monotonic() - start
                    
                    # Record latency metric
                    PROVIDER_FETCH_DURATION.labels(
                        provider=provider_name,
                        category=category,
                    ).observe(elapsed)
                    
                    # Handle rate limiting (429)
                    if resp.status == 429:
                        await self._handle_rate_limit(
                            resp,
                            provider_name,
                            category,
                            attempt,
                            trace_id,
                        )
                        continue
                    
                    # Handle non-retryable errors (4xx)
                    if resp.status in _NON_RETRYABLE_STATUS:
                        await self._handle_non_retryable_error(
                            resp,
                            provider_name,
                            category,
                            url,
                            trace_id,
                        )
                    
                    # Handle server errors (5xx)
                    if resp.status >= 500:
                        await self._handle_server_error(
                            resp,
                            provider_name,
                            category,
                            url,
                            attempt,
                            trace_id,
                        )
                        # Don't raise here, let retry logic handle it
                        last_exc = ProviderUnavailableError(
                            f"{provider_name} server error {resp.status}",
                            details={
                                "status": resp.status,
                                "url": url,
                                "attempt": attempt,
                            },
                        )
                        
                        if attempt < self._max_retries:
                            delay = self._backoff_delay(attempt)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise last_exc
                    
                    # Success path
                    response_data = await self._parse_response(
                        resp,
                        provider_name,
                        category,
                        trace_id,
                    )
                    
                    # Record success metrics
                    PROVIDER_FETCH_TOTAL.labels(
                        provider=provider_name,
                        category=category,
                        status="success",
                    ).inc()
                    
                    await self._circuit.record_success()
                    
                    logger.debug(
                        "http_request_success",
                        extra={
                            "provider": provider_name,
                            "category": category,
                            "method": method,
                            "url": url,
                            "status": resp.status,
                            "duration_ms": round(elapsed * 1000, 2),
                            "attempt": attempt + 1,
                            "trace_id": trace_id,
                        },
                    )
                    
                    return response_data

            except asyncio.TimeoutError:
                elapsed = time.monotonic() - start
                
                PROVIDER_FETCH_DURATION.labels(
                    provider=provider_name,
                    category=category,
                ).observe(elapsed)
                
                PROVIDER_ERRORS_TOTAL.labels(
                    provider=provider_name,
                    category=category,
                    error_type="timeout",
                ).inc()
                
                await self._circuit.record_failure()
                
                logger.warning(
                    "http_request_timeout",
                    extra={
                        "provider": provider_name,
                        "url": url,
                        "timeout_seconds": timeout.total,
                        "attempt": attempt + 1,
                        "trace_id": trace_id,
                    },
                )
                
                last_exc = ProviderTimeoutError(
                    f"{provider_name} timed out after {timeout.total}s",
                    details={
                        "url": url,
                        "attempt": attempt,
                        "timeout": timeout.total,
                    },
                )

            except aiohttp.ClientError as exc:
                elapsed = time.monotonic() - start
                
                PROVIDER_FETCH_DURATION.labels(
                    provider=provider_name,
                    category=category,
                ).observe(elapsed)
                
                PROVIDER_ERRORS_TOTAL.labels(
                    provider=provider_name,
                    category=category,
                    error_type="connection",
                ).inc()
                
                await self._circuit.record_failure()
                
                logger.warning(
                    "http_connection_error",
                    extra={
                        "provider": provider_name,
                        "url": url,
                        "error": str(exc),
                        "attempt": attempt + 1,
                        "trace_id": trace_id,
                    },
                )
                
                last_exc = ProviderUnavailableError(
                    f"{provider_name} connection error: {exc}",
                    details={
                        "url": url,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )

            except (ProviderUnavailableError, ProviderValidationError):
                # Don't retry on these
                raise

            except Exception as exc:
                # Unexpected error
                elapsed = time.monotonic() - start
                
                PROVIDER_ERRORS_TOTAL.labels(
                    provider=provider_name,
                    category=category,
                    error_type="unexpected",
                ).inc()
                
                await self._circuit.record_failure()
                
                logger.exception(
                    "http_unexpected_error",
                    extra={
                        "provider": provider_name,
                        "url": url,
                        "attempt": attempt + 1,
                        "trace_id": trace_id,
                    },
                )
                
                raise HttpClientError(
                    f"Unexpected error during {provider_name} request: {exc}",
                    details={"url": url, "attempt": attempt},
                ) from exc

            # Retry logic
            if attempt < self._max_retries:
                delay = self._backoff_delay(attempt)
                
                logger.warning(
                    "retrying_request",
                    extra={
                        "provider": provider_name,
                        "url": url,
                        "attempt": attempt + 1,
                        "max_retries": self._max_retries,
                        "delay_seconds": round(delay, 2),
                        "trace_id": trace_id,
                    },
                )
                
                await asyncio.sleep(delay)

        # All retries exhausted
        PROVIDER_FETCH_TOTAL.labels(
            provider=provider_name,
            category=category,
            status="exhausted",
        ).inc()
        
        logger.error(
            "http_retries_exhausted",
            extra={
                "provider": provider_name,
                "url": url,
                "max_retries": self._max_retries,
                "trace_id": trace_id,
            },
        )
        
        raise last_exc or ProviderUnavailableError(
            f"{provider_name} all retries exhausted",
            details={
                "url": url,
                "max_retries": self._max_retries,
            },
        )

    async def _handle_rate_limit(
        self,
        resp: aiohttp.ClientResponse,
        provider_name: str,
        category: str,
        attempt: int,
        trace_id: Optional[str],
    ) -> None:
        """Handle 429 rate limit response."""
        PROVIDER_ERRORS_TOTAL.labels(
            provider=provider_name,
            category=category,
            error_type="rate_limit",
        ).inc()
        
        retry_after = float(
            resp.headers.get("Retry-After", self._backoff_delay(attempt))
        )
        
        logger.warning(
            "rate_limited",
            extra={
                "provider": provider_name,
                "retry_after_seconds": retry_after,
                "attempt": attempt + 1,
                "trace_id": trace_id,
            },
        )
        
        await asyncio.sleep(retry_after)

    async def _handle_non_retryable_error(
        self,
        resp: aiohttp.ClientResponse,
        provider_name: str,
        category: str,
        url: str,
        trace_id: Optional[str],
    ) -> None:
        """Handle non-retryable 4xx errors."""
        PROVIDER_FETCH_TOTAL.labels(
            provider=provider_name,
            category=category,
            status="error",
        ).inc()
        
        await self._circuit.record_failure()
        
        body = await resp.text()
        
        logger.error(
            "http_non_retryable_error",
            extra={
                "provider": provider_name,
                "url": url,
                "status": resp.status,
                "body_preview": body[:500],
                "trace_id": trace_id,
            },
        )
        
        raise ProviderUnavailableError(
            f"{provider_name} returned {resp.status}",
            details={
                "status": resp.status,
                "body": body[:500],
                "url": url,
            },
        )

    async def _handle_server_error(
        self,
        resp: aiohttp.ClientResponse,
        provider_name: str,
        category: str,
        url: str,
        attempt: int,
        trace_id: Optional[str],
    ) -> None:
        """Handle 5xx server errors."""
        await self._circuit.record_failure()
        
        body = await resp.text()
        
        logger.warning(
            "http_server_error",
            extra={
                "provider": provider_name,
                "url": url,
                "status": resp.status,
                "body_preview": body[:500],
                "attempt": attempt + 1,
                "trace_id": trace_id,
            },
        )

    async def _parse_response(
        self,
        resp: aiohttp.ClientResponse,
        provider_name: str,
        category: str,
        trace_id: Optional[str],
    ) -> dict[str, Any] | list[Any] | str:
        """
        Parse HTTP response with size validation.
        
        Args:
            resp: aiohttp response object
            provider_name: Provider name for logging
            category: Category for logging
            trace_id: Trace ID for logging
            
        Returns:
            Parsed response data
            
        Raises:
            ProviderValidationError: On response size limit exceeded
        """
        content_length = resp.headers.get("Content-Length")
        
        if content_length and int(content_length) > self._max_response_size:
            raise ProviderValidationError(
                f"Response size {content_length} exceeds maximum {self._max_response_size}",
                details={
                    "provider": provider_name,
                    "content_length": content_length,
                    "max_size": self._max_response_size,
                },
            )
        
        content_type = resp.headers.get("Content-Type", "")
        
        if "json" in content_type or "javascript" in content_type:
            data = await resp.json()
            response_size = len(str(data))
        else:
            data = await resp.text()
            response_size = len(data)
        
        # Security: Validate actual response size
        if response_size > self._max_response_size:
            raise ProviderValidationError(
                f"Response size {response_size} exceeds maximum {self._max_response_size}",
                details={
                    "provider": provider_name,
                    "response_size": response_size,
                    "max_size": self._max_response_size,
                },
            )
        
        # Record response size metric
        PROVIDER_RESPONSE_SIZE.labels(
            provider=provider_name,
            category=category,
        ).observe(response_size)
        
        return data  # type: ignore[return-value]

    async def get(
        self,
        url: str,
        *,
        provider_name: str = "unknown",
        category: str = "unknown",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        trace_id: Optional[str] = None,
        timeout_override: Optional[int] = None,
    ) -> dict[str, Any] | list[Any] | str:
        """
        Execute HTTP GET request.
        
        Args:
            url: Target URL
            provider_name: Provider identifier
            category: Request category
            headers: Optional request headers
            params: Optional query parameters
            trace_id: Optional trace ID
            timeout_override: Optional timeout override
            
        Returns:
            Response data
        """
        return await self.request(
            "GET",
            url,
            provider_name=provider_name,
            category=category,
            headers=headers,
            params=params,
            trace_id=trace_id,
            timeout_override=timeout_override,
        )

    async def post(
        self,
        url: str,
        *,
        provider_name: str = "unknown",
        category: str = "unknown",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        trace_id: Optional[str] = None,
        timeout_override: Optional[int] = None,
    ) -> dict[str, Any] | list[Any] | str:
        """
        Execute HTTP POST request.
        
        Args:
            url: Target URL
            provider_name: Provider identifier
            category: Request category
            headers: Optional request headers
            params: Optional query parameters
            json_body: Optional JSON request body
            trace_id: Optional trace ID
            timeout_override: Optional timeout override
            
        Returns:
            Response data
        """
        return await self.request(
            "POST",
            url,
            provider_name=provider_name,
            category=category,
            headers=headers,
            params=params,
            json_body=json_body,
            trace_id=trace_id,
            timeout_override=timeout_override,
        )

    async def close(self) -> None:
        """Gracefully close HTTP session."""
        try:
            if self._session and not self._session.closed:
                await self._session.close()
                logger.info("http_client_closed")
        except Exception:
            logger.exception("http_client_close_failed")
            raise

    @property
    async def circuit_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return await self._circuit.state
