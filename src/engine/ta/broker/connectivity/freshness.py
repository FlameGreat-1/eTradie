"""Tick freshness guard.

Rejects tick responses that are older than the configured threshold.
Called inline inside every get_tick_price() so a stale broker reply
does not silently flow into the execution / management bridges.

The guard is intentionally lightweight - no I/O, no state - so it
can be invoked on every tick without affecting the latency budget.

Audit ref: CHECKLIST Section 2 - 'Price feed validation layer
(anti-stale pricing detection)'.
"""

from __future__ import annotations

import time as _time
from dataclasses import dataclass
from datetime import UTC, datetime

from engine.shared.exceptions import ProviderStalePriceError
from engine.shared.metrics.prometheus import BROKER_TICK_STALE_TOTAL


@dataclass(frozen=True)
class TickFreshnessGuard:
    """Asserts a tick's timestamp is within max_age_seconds of now.

    Constructed with the broker provider name + account id so the
    Prometheus counter increments carry useful labels.
    """

    max_age_seconds: float
    provider: str
    account_id: str

    def assert_fresh(self, *, symbol: str, tick_unix_ts: int | float) -> None:
        """Raise ProviderStalePriceError when the tick is too old.

        Args:
            symbol: Used for the Prometheus label and the exception detail.
            tick_unix_ts: The broker-reported tick timestamp in Unix seconds.
                Accepts int (MT5 native) or float (epoch with decimals).

        Notes:
            - The check is one-sided: ticks that appear FROM THE FUTURE
              (broker clock skew) are accepted because every broker we
              integrate with returns UTC timestamps and the worst-case
              positive skew we have observed in production logs is
              <2 seconds, which is below any sensible max_age threshold.
            - max_age_seconds=0 disables the guard (returns immediately).
        """
        if self.max_age_seconds <= 0:
            return
        if tick_unix_ts <= 0:
            # Brokers occasionally return 0 for symbols whose session
            # has not opened yet. Treat as stale-by-session and let the
            # caller decide.
            BROKER_TICK_STALE_TOTAL.labels(
                provider=self.provider,
                account_id=self.account_id,
                symbol=symbol,
            ).inc()
            raise ProviderStalePriceError(
                f"Tick timestamp is zero or negative for {symbol} - session likely closed",
                details={
                    "symbol": symbol,
                    "tick_unix_ts": float(tick_unix_ts),
                    "reason": "stale_by_session",
                },
            )
        now_ts = _time.time()
        age = now_ts - float(tick_unix_ts)
        if age > self.max_age_seconds:
            BROKER_TICK_STALE_TOTAL.labels(
                provider=self.provider,
                account_id=self.account_id,
                symbol=symbol,
            ).inc()
            raise ProviderStalePriceError(
                f"Tick is {age:.1f}s old, exceeds max_age={self.max_age_seconds:.1f}s",
                details={
                    "symbol": symbol,
                    "age_seconds": age,
                    "max_age_seconds": self.max_age_seconds,
                    "tick_iso": datetime.fromtimestamp(
                        float(tick_unix_ts),
                        tz=UTC,
                    ).isoformat(),
                    "reason": "stale_by_age",
                },
            )
