"""Exponential-backoff reconnect policy with full jitter.

Shared between ZmqClient and MetaApiClient so the reconnect behaviour
is identical across providers (an operator-visible promise: 'every
broker disconnect is retried at the same cadence').

Design
------
- Full jitter (not equal jitter, not no-jitter) per the AWS
  architecture-blog 'Exponential Backoff And Jitter' paper. Spreads
  retry storms across a 0..delay window when many connections (e.g.
  N user mt-node Pods) lose the broker simultaneously.
- Caller-controlled max attempts. The library does NOT retry forever
  - infinite retries would mask permanent misconfiguration
  (bad password, deleted account) from the dashboard.
- Cancellation-safe. asyncio.sleep is the only blocking primitive;
  a CancelledError unwinds cleanly without leaving the policy in a
  half-state.
- Pure logic, no side effects. Caller drives the retry loop; this
  module only computes the next delay and tracks the attempt counter.
  Makes unit testing trivial (no event loop, no mocking).
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import BROKER_RECONNECT_ATTEMPTS_TOTAL

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class ReconnectPolicy:
    """Immutable policy values. Caller drives the loop.

    Attributes:
        base_secs: First retry delay in seconds (before jitter).
        cap_secs: Hard ceiling on any individual delay.
        max_attempts: Stop retrying after this many failures. The
            attempt counter starts at 1 for the first retry; an
            attempt of `max_attempts + 1` is treated as exhausted.
        provider: Used for Prometheus labels only. Free-form string.
        account_id: Same.
    """

    base_secs: float = 1.0
    cap_secs: float = 30.0
    max_attempts: int = 10
    provider: str = "unknown"
    account_id: str = "unknown"

    def next_delay(self, attempt: int) -> float:
        """Return the next sleep duration in seconds.

        attempt is 1-indexed. The exponential schedule is
        `min(cap, base * 2 ** (attempt - 1))` and the returned value
        is sampled uniformly from [0, schedule] (full jitter).
        """
        if attempt < 1:
            return 0.0
        schedule = min(self.cap_secs, self.base_secs * (2 ** (attempt - 1)))
        return random.uniform(0.0, schedule)  # nosec B311

    def exhausted(self, attempt: int) -> bool:
        return attempt > self.max_attempts

    async def run_with_retry(
        self,
        coro_factory: Callable[[], Awaitable[T]],
        *,
        retry_on: tuple[type[BaseException], ...],
        operation_label: str,
    ) -> T:
        """Drive a coroutine factory with exponential backoff.

        Each attempt invokes coro_factory() (a NEW coroutine; an
        already-awaited coroutine cannot be replayed). If it raises
        one of retry_on, the policy sleeps next_delay(attempt) and
        retries. After max_attempts failures, re-raises the last
        exception unchanged.
        """
        last_exc: BaseException | None = None
        attempt = 0
        while True:
            attempt += 1
            if self.exhausted(attempt):
                logger.error(
                    "reconnect_policy_exhausted",
                    extra={
                        "provider": self.provider,
                        "account_id": self.account_id,
                        "operation": operation_label,
                        "attempts": attempt - 1,
                    },
                )
                if last_exc is not None:
                    raise last_exc
                raise RuntimeError(f"ReconnectPolicy exhausted with no exception captured (op={operation_label})")
            try:
                return await coro_factory()
            except retry_on as exc:
                last_exc = exc
                BROKER_RECONNECT_ATTEMPTS_TOTAL.labels(
                    provider=self.provider,
                    account_id=self.account_id,
                ).inc()
                delay = self.next_delay(attempt)
                logger.warning(
                    "reconnect_policy_retry",
                    extra={
                        "provider": self.provider,
                        "account_id": self.account_id,
                        "operation": operation_label,
                        "attempt": attempt,
                        "sleep_secs": delay,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
                await asyncio.sleep(delay)
