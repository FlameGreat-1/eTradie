from __future__ import annotations

import asyncio
import random
import time
from enum import StrEnum, unique
from typing import Any

import aiohttp

from engine.shared.exceptions import (
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    PROVIDER_ERRORS_TOTAL,
    PROVIDER_FETCH_DURATION,
    PROVIDER_FETCH_TOTAL,
)

logger = get_logger(__name__)

_NON_RETRYABLE_STATUS = frozenset({400, 401, 403, 404, 405, 422})


@unique
class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class _CircuitBreaker:
    __slots__ = (
        "_failure_count",
        "_failure_threshold",
        "_half_open_max",
        "_half_open_successes",
        "_last_failure_time",
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

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_successes = 0
        return self._state

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self._half_open_max:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN


class HttpClient:
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
    ) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max
        self._session: aiohttp.ClientSession | None = None
        self._circuit = _CircuitBreaker(
            failure_threshold=cb_failure_threshold,
            recovery_timeout=cb_recovery_timeout,
            half_open_max_calls=cb_half_open_max,
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    def _backoff_delay(self, attempt: int) -> float:
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
    ) -> dict[str, Any] | list[Any] | str:
        if self._circuit.state == CircuitState.OPEN:
            PROVIDER_ERRORS_TOTAL.labels(
                provider=provider_name, category=category, error_type="circuit_open",
            ).inc()
            raise ProviderUnavailableError(
                f"Circuit breaker OPEN for {provider_name}",
                details={"provider": provider_name, "url": url},
            )

        last_exc: Exception | None = None
        session = await self._get_session()

        for attempt in range(self._max_retries + 1):
            start = time.monotonic()
            try:
                async with session.request(
                    method, url, headers=headers, params=params, json=json_body,
                ) as resp:
                    elapsed = time.monotonic() - start
                    PROVIDER_FETCH_DURATION.labels(
                        provider=provider_name, category=category,
                    ).observe(elapsed)

                    if resp.status == 429:
                        PROVIDER_ERRORS_TOTAL.labels(
                            provider=provider_name, category=category, error_type="rate_limit",
                        ).inc()
                        retry_after = float(resp.headers.get("Retry-After", self._backoff_delay(attempt)))
                        logger.warning(
                            "rate_limited",
                            provider=provider_name,
                            retry_after=retry_after,
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    if resp.status in _NON_RETRYABLE_STATUS:
                        PROVIDER_FETCH_TOTAL.labels(
                            provider=provider_name, category=category, status="error",
                        ).inc()
                        self._circuit.record_failure()
                        body = await resp.text()
                        raise ProviderUnavailableError(
                            f"{provider_name} returned {resp.status}",
                            details={"status": resp.status, "body": body[:500]},
                        )

                    if resp.status >= 500:
                        body = await resp.text()
                        raise ProviderUnavailableError(
                            f"{provider_name} server error {resp.status}",
                            details={"status": resp.status, "body": body[:500]},
                        )

                    PROVIDER_FETCH_TOTAL.labels(
                        provider=provider_name, category=category, status="success",
                    ).inc()
                    self._circuit.record_success()

                    content_type = resp.headers.get("Content-Type", "")
                    if "json" in content_type or "javascript" in content_type:
                        return await resp.json()  # type: ignore[no-any-return]
                    return await resp.text()

            except asyncio.TimeoutError:
                elapsed = time.monotonic() - start
                PROVIDER_FETCH_DURATION.labels(
                    provider=provider_name, category=category,
                ).observe(elapsed)
                PROVIDER_ERRORS_TOTAL.labels(
                    provider=provider_name, category=category, error_type="timeout",
                ).inc()
                self._circuit.record_failure()
                last_exc = ProviderTimeoutError(
                    f"{provider_name} timed out after {self._timeout.total}s",
                    details={"url": url, "attempt": attempt},
                )

            except aiohttp.ClientError as exc:
                elapsed = time.monotonic() - start
                PROVIDER_FETCH_DURATION.labels(
                    provider=provider_name, category=category,
                ).observe(elapsed)
                PROVIDER_ERRORS_TOTAL.labels(
                    provider=provider_name, category=category, error_type="connection",
                ).inc()
                self._circuit.record_failure()
                last_exc = ProviderUnavailableError(
                    f"{provider_name} connection error: {exc}",
                    details={"url": url, "attempt": attempt},
                )

            except ProviderUnavailableError:
                raise

            if attempt < self._max_retries:
                delay = self._backoff_delay(attempt)
                logger.warning(
                    "retrying_request",
                    provider=provider_name,
                    attempt=attempt + 1,
                    delay=round(delay, 2),
                )
                await asyncio.sleep(delay)

        PROVIDER_FETCH_TOTAL.labels(
            provider=provider_name, category=category, status="exhausted",
        ).inc()
        raise last_exc or ProviderUnavailableError(  # type: ignore[misc]
            f"{provider_name} all retries exhausted",
            details={"url": url, "max_retries": self._max_retries},
        )

    async def get(
        self,
        url: str,
        *,
        provider_name: str = "unknown",
        category: str = "unknown",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | str:
        return await self.request(
            "GET", url,
            provider_name=provider_name,
            category=category,
            headers=headers,
            params=params,
        )

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def circuit_state(self) -> CircuitState:
        return self._circuit.state
