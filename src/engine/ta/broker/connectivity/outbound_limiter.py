"""Per-connection outbound rate limiter (engine -> EA / engine -> MetaAPI).

A token bucket. Tokens refill at ``rate_per_second`` up to ``burst_size``.
Every outbound command costs ``weight`` tokens (default 1). When the
bucket is empty, ``acquire`` either blocks (up to the deadline) or, in
the ``try_acquire`` variant, immediately reports unavailability.

Used by ZmqClient and MetaApiClient at every outbound command boundary
so a misbehaving analysis loop cannot flood one user's EA. The bucket
is keyed per (provider, account_id) by construction site - one limiter
instance per broker client.

All state is in-process. Across multiple engine replicas, each replica
holds its own bucket; this is by design because each replica has its
own ZMQ REQ socket to the EA. The combined ceiling is
``replicas * rate_per_second`` which is bounded by the engine HPA.

Audit ref: CHECKLIST Section 5 - 'Rate limits prevent EA flooding'.
"""
from __future__ import annotations

import asyncio
import time as _time
from dataclasses import dataclass
from typing import Optional

from engine.shared.exceptions import OutboundRateLimitExceededError
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    BROKER_OUTBOUND_LIMIT_TOTAL,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class _LimitDecision:
    allowed: bool
    waited_secs: float
    reason: str  # "allowed" | "throttled" | "exhausted"


class OutboundRateLimiter:
    """Token bucket for one (provider, account_id) pair.

    Thread-safety: protected by an asyncio.Lock. Safe under FastAPI
    concurrency. NOT safe across processes - one limiter per process
    per (provider, account_id).
    """

    def __init__(
        self,
        *,
        provider: str,
        account_id: str,
        rate_per_second: float,
        burst_size: int,
    ) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be > 0")
        if burst_size <= 0:
            raise ValueError("burst_size must be > 0")
        self.provider = provider
        self.account_id = account_id or "unknown"
        self.rate = float(rate_per_second)
        self.burst = int(burst_size)
        self._tokens = float(burst_size)
        self._last_refill = _time.monotonic()
        self._lock = asyncio.Lock()

    def _refill_locked(self, now: float) -> None:
        """Refill tokens based on elapsed time. Caller must hold the lock."""
        elapsed = max(0.0, now - self._last_refill)
        if elapsed <= 0:
            return
        self._tokens = min(float(self.burst), self._tokens + elapsed * self.rate)
        self._last_refill = now

    async def try_acquire(self, weight: int = 1) -> bool:
        """Non-blocking acquire. Returns True when a token was taken,
        False when the bucket is empty. Caller is expected to retry,
        sleep, or fail-fast based on its policy.
        """
        if weight <= 0:
            raise ValueError("weight must be > 0")
        async with self._lock:
            self._refill_locked(_time.monotonic())
            if self._tokens >= float(weight):
                self._tokens -= float(weight)
                BROKER_OUTBOUND_LIMIT_TOTAL.labels(
                    provider=self.provider,
                    account_id=self.account_id,
                    result="allowed",
                ).inc()
                return True
            BROKER_OUTBOUND_LIMIT_TOTAL.labels(
                provider=self.provider,
                account_id=self.account_id,
                result="throttled",
            ).inc()
            return False

    async def acquire(
        self,
        *,
        weight: int = 1,
        deadline_secs: Optional[float] = None,
    ) -> _LimitDecision:
        """Blocking acquire. Waits up to ``deadline_secs`` for a token.

        When ``deadline_secs`` is None or 0, behaviour is identical to
        try_acquire (one-shot). When set, blocks in ~10ms slices,
        re-checking the bucket. Returns a decision describing the
        outcome.
        """
        if weight <= 0:
            raise ValueError("weight must be > 0")

        start = _time.monotonic()
        deadline = start + (deadline_secs or 0.0)

        while True:
            async with self._lock:
                now = _time.monotonic()
                self._refill_locked(now)
                if self._tokens >= float(weight):
                    self._tokens -= float(weight)
                    BROKER_OUTBOUND_LIMIT_TOTAL.labels(
                        provider=self.provider,
                        account_id=self.account_id,
                        result="allowed",
                    ).inc()
                    return _LimitDecision(
                        allowed=True,
                        waited_secs=now - start,
                        reason="allowed",
                    )
                # Compute exact time we'd have enough tokens at the
                # configured rate, so we can sleep accurately rather
                # than polling.
                deficit = float(weight) - self._tokens
                wait_for = deficit / self.rate

            if deadline_secs is None or deadline_secs <= 0:
                BROKER_OUTBOUND_LIMIT_TOTAL.labels(
                    provider=self.provider,
                    account_id=self.account_id,
                    result="exhausted",
                ).inc()
                return _LimitDecision(
                    allowed=False,
                    waited_secs=0.0,
                    reason="exhausted",
                )

            now = _time.monotonic()
            remaining = deadline - now
            if remaining <= 0:
                BROKER_OUTBOUND_LIMIT_TOTAL.labels(
                    provider=self.provider,
                    account_id=self.account_id,
                    result="exhausted",
                ).inc()
                return _LimitDecision(
                    allowed=False,
                    waited_secs=now - start,
                    reason="exhausted",
                )

            # Cap the per-iteration wait so we re-check on a reasonable
            # cadence; this also bounds the impact of a clock jump.
            await asyncio.sleep(min(wait_for, remaining, 0.05))

    async def raise_if_exhausted(
        self,
        *,
        weight: int = 1,
        deadline_secs: Optional[float] = None,
    ) -> None:
        """Convenience: acquire-or-raise.

        Raises OutboundRateLimitExceededError when no token is available
        within the deadline. The exception subclasses ProviderError so
        existing 'except ProviderError' returns HTTP 429 cleanly.
        """
        decision = await self.acquire(weight=weight, deadline_secs=deadline_secs)
        if not decision.allowed:
            logger.warning(
                "outbound_rate_limit_exhausted",
                extra={
                    "provider": self.provider,
                    "account_id": self.account_id,
                    "rate": self.rate,
                    "burst": self.burst,
                    "waited_secs": decision.waited_secs,
                },
            )
            raise OutboundRateLimitExceededError(
                f"outbound rate limit exceeded for {self.provider}/{self.account_id}",
                details={
                    "provider": self.provider,
                    "account_id": self.account_id,
                    "rate_per_second": self.rate,
                    "burst_size": self.burst,
                },
            )
