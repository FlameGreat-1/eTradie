"""EA clock-skew monitor.

The MT5 broker reports tick times as server time (the broker's
clock). The engine compares them against datetime.utcnow() inside
TickFreshnessGuard (Section 2). Any sustained clock skew between
the broker server and the engine causes spurious 'stale_by_age'
rejections.

This monitor periodically queries EA_CLOCK and maintains a sliding
window of (engine_now - server_time) samples. The median offset is
exposed as 'skew_seconds' so TickFreshnessGuard can correct for it.

Why median: a single bad sample (e.g. a request that took 500ms in
flight) would push the mean badly. Median is robust to outliers and
is the right statistic for clock skew over a window of 16 samples.

Audit ref: CHECKLIST Section 4 - 'Time synchronization (critical
for trading logic)'.
"""

from __future__ import annotations

import statistics
import threading
import time as _time
from collections import deque
from dataclasses import dataclass
from typing import Any

from engine.shared.exceptions import EAClockSkewError
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    BROKER_EA_CLOCK_SKEW_SAMPLES_TOTAL,
    BROKER_EA_CLOCK_SKEW_SECONDS,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class EAClockSample:
    """One EA_CLOCK reply."""

    server_time: int  # broker server time (TimeCurrent on MT)
    ea_local_time: int  # host UTC clock (TimeLocal on MT)
    tick_time: int  # latest tick time on the EA's chart symbol

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> EAClockSample:
        return cls(
            server_time=int(raw.get("server_time", 0) or 0),
            ea_local_time=int(raw.get("ea_local_time", 0) or 0),
            tick_time=int(raw.get("tick_time", 0) or 0),
        )


class ClockSkewMonitor:
    """Tracks engine-vs-EA clock skew over a sliding window.

    Construct per (provider, account_id). Thread-safe.
    """

    def __init__(
        self,
        *,
        provider: str,
        account_id: str,
        window_size: int = 16,
        max_acceptable_skew_secs: float = 10.0,
    ) -> None:
        if window_size < 3:
            raise ValueError("window_size must be >= 3 for a useful median")
        if max_acceptable_skew_secs <= 0:
            raise ValueError("max_acceptable_skew_secs must be > 0")
        self.provider = provider
        self.account_id = account_id or "unknown"
        self._window: deque[float] = deque(maxlen=window_size)
        self._lock = threading.Lock()
        self._max_skew = max_acceptable_skew_secs

    def sample(self, engine_now_unix: float, sample: EAClockSample) -> float:
        """Record one sample. Returns the new median skew in seconds.

        skew = engine_now - server_time. Positive skew means the
        engine clock is ahead of the broker; negative means behind.
        """
        if sample.server_time <= 0:
            # Broker did not have a tick yet - cannot compute a useful skew.
            return self.skew_seconds()
        skew = float(engine_now_unix - sample.server_time)
        with self._lock:
            self._window.append(skew)
            current = statistics.median(self._window)
        BROKER_EA_CLOCK_SKEW_SAMPLES_TOTAL.labels(
            provider=self.provider,
            account_id=self.account_id,
        ).inc()
        BROKER_EA_CLOCK_SKEW_SECONDS.labels(
            provider=self.provider,
            account_id=self.account_id,
        ).set(current)
        if abs(current) > self._max_skew:
            logger.warning(
                "clock_skew_above_threshold",
                extra={
                    "provider": self.provider,
                    "account_id": self.account_id,
                    "skew_secs": current,
                    "max_acceptable": self._max_skew,
                    "window_size": len(self._window),
                },
            )
        return current

    def skew_seconds(self) -> float:
        """Return the current median skew. 0.0 when no samples yet."""
        with self._lock:
            if not self._window:
                return 0.0
            return statistics.median(self._window)

    def now_compensated(self, engine_now_unix: float | None = None) -> float:
        """Return engine_now minus the current median skew.

        TickFreshnessGuard.assert_fresh passes the result of this
        method as its 'now' so that 'age = now - tick_time' uses a
        broker-clock-aligned 'now'.
        """
        base = engine_now_unix if engine_now_unix is not None else _time.time()
        return base - self.skew_seconds()

    def is_degraded(self) -> bool:
        return abs(self.skew_seconds()) > self._max_skew

    def assert_within_tolerance(self) -> None:
        """Raise EAClockSkewError when skew exceeds the threshold.

        Optional checkpoint for callers that prefer fail-fast over
        silent degradation.
        """
        skew = self.skew_seconds()
        if abs(skew) > self._max_skew:
            raise EAClockSkewError(
                f"EA clock skew {skew:.2f}s exceeds maximum {self._max_skew:.2f}s",
                details={
                    "provider": self.provider,
                    "account_id": self.account_id,
                    "skew_secs": skew,
                    "max_acceptable": self._max_skew,
                },
            )
