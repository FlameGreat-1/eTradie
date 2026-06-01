"""Fed funds target-rate provider sourced from FRED.

The central-bank RSS providers (fed_rss.py and siblings) parse press-release
headlines: they can classify tone (HAWKISH/DOVISH/NEUTRAL) and QE/QT, but an
RSS title never carries the numeric policy rate, so they can never construct a
``RateDecision``. That left ``rate_current`` / ``rate_previous`` /
``rate_change_bps`` permanently empty on the CentralBankDataSet -- structured
fields the LLM was meant to reason over but never received.

This provider closes that gap using the authoritative machine-readable source
the Fed itself publishes through FRED:

  - ``DFEDTARU`` -- Federal Funds Target Range, Upper Limit (the headline
    ceiling, e.g. 3.75 for a 3.50-3.75 range).
  - ``DFEDTARL`` -- Federal Funds Target Range, Lower Limit (e.g. 3.50).

These are daily series whose *level* only moves on an FOMC decision, so the
most recent change in the upper-limit series is, by construction, the latest
rate decision. We fetch a short recent window of each, find the two most
recent distinct levels, and emit a single ``RateDecision`` carrying the
current rate, the previous rate, and the basis-point change.

Only the United States is covered: the other central banks do not expose an
equivalent free, structured target-rate series, so they continue to provide
tone/QE-QT from their RSS feeds. Treated as a central-bank provider (not an
economic-data provider) because its output is a ``RateDecision`` consumed by
the CentralBankCollector, which the gateway forwards to the LLM untouched.

FRED API docs: https://fred.stlouisfed.org/docs/api/fred/
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.events import CentralBank, ProviderCategory
from engine.macro.models.provider.central_bank import RateDecision
from engine.macro.providers.base import BaseProvider

logger = get_logger(__name__)

# Federal Funds target *range* series. The Fed has published a target range
# (rather than a single point target) since December 2008; the upper limit is
# the headline ceiling quoted as "the Fed funds rate".
_SERIES_UPPER = "DFEDTARU"
_SERIES_LOWER = "DFEDTARL"

# Observations to pull per series. The series are daily and only step on an
# FOMC decision, so a ~140-day window comfortably spans at least two distinct
# levels (FOMC meets eight times a year, roughly every 6-7 weeks) while
# keeping the payload tiny.
_OBSERVATION_LIMIT = "140"


class FedRateProvider(BaseProvider):
    """Fetch the current FOMC target rate + latest change from FRED.

    Emits a list containing a single ``RateDecision`` (or an empty list when
    the data is unavailable / the API key is unset). Failure is non-fatal:
    the CentralBankCollector skips a provider that raises, and a missing key
    simply yields no rate decision, leaving the tone-only signal intact.
    """

    provider_name = "fed_rate"
    category = ProviderCategory.CENTRAL_BANK
    bank = CentralBank.FED

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> list[RateDecision]:
        start = time.monotonic()

        if not self._api_key:
            logger.warning(
                "fed_rate_api_key_missing",
                extra={"action": "skipping FedRateProvider - no FRED API key configured"},
            )
            return []

        try:
            upper = await self._fetch_series(_SERIES_UPPER)
            lower = await self._fetch_series(_SERIES_LOWER)

            decision = self._build_rate_decision(upper, lower)
            if decision is None:
                logger.warning(
                    "fed_rate_no_decision",
                    extra={
                        "upper_points": len(upper),
                        "lower_points": len(lower),
                    },
                )
                self._record_success(time.monotonic() - start)
                return []

            self._record_success(time.monotonic() - start)
            return [decision]
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error(
                "fed_rate_fetch_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            raise

    async def _fetch_series(self, series_id: str) -> list[tuple[datetime, float]]:
        """Return recent (date, level) observations for a FRED series, newest first.

        Missing/placeholder observations (FRED encodes these as ".") are
        skipped. The list preserves FRED's descending sort order so the first
        element is the most recent reading.
        """
        raw = await self._http.get(
            f"{self._base_url}/series/observations",
            provider_name=self.provider_name,
            category=self.category.value,
            params={
                "series_id": series_id,
                "api_key": self._api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": _OBSERVATION_LIMIT,
            },
        )
        observations = raw.get("observations", []) if isinstance(raw, dict) else []

        points: list[tuple[datetime, float]] = []
        for obs in observations:
            value = self._parse_float(obs.get("value"))
            if value is None:
                continue
            ts = self._parse_date(obs.get("date"))
            points.append((ts, value))
        return points

    def _build_rate_decision(
        self,
        upper: list[tuple[datetime, float]],
        lower: list[tuple[datetime, float]],
    ) -> RateDecision | None:
        """Derive the latest RateDecision from the upper/lower target-range series.

        The upper limit is the headline rate. ``rate_current`` is the most
        recent level; ``rate_previous`` is the most recent *distinct* prior
        level; ``rate_change_bps`` is the move between them, expressed in
        basis points (1 percentage point = 100 bps). ``decision_date`` is the
        date the current level first took effect (the changeover date), which
        is the actual FOMC decision date for that level.

        Returns ``None`` when there are not enough observations to establish a
        current level (e.g. an empty series response).
        """
        if not upper:
            return None

        current_level = upper[0][1]

        # Walk back to the first observation whose level differs from the
        # current one: that boundary is the most recent rate change. The
        # observation *just after* the boundary (chronologically the first
        # day at the new level) carries the decision's effective date.
        previous_level: float | None = None
        decision_date = upper[0][0]
        for i in range(1, len(upper)):
            ts, level = upper[i]
            if level != current_level:
                previous_level = level
                # upper[i-1] is the first day at the current level.
                decision_date = upper[i - 1][0]
                break

        # No change within the window: the rate has been flat. Report the
        # current level with a zero-bps change and no distinct previous level
        # so the LLM still receives the authoritative current rate.
        if previous_level is None:
            previous_level = current_level
            change_bps = 0
        else:
            change_bps = int(round((current_level - previous_level) * 100))

        # Annotate the current level with its range lower bound when available
        # (logged for operator visibility; the LLM consumes the numeric
        # rate_current/rate_previous which track the headline upper limit).
        lower_level = lower[0][1] if lower else None
        logger.info(
            "fed_rate_decision_built",
            extra={
                "rate_current": current_level,
                "rate_previous": previous_level,
                "rate_change_bps": change_bps,
                "range_lower": lower_level,
                "decision_date": decision_date.isoformat(),
            },
        )

        return RateDecision(
            bank=self.bank,
            rate_current=current_level,
            rate_previous=previous_level,
            rate_change_bps=change_bps,
            decision_date=decision_date,
        )

    @staticmethod
    def _parse_float(val: Any) -> float | None:
        if val is None or val == "" or val == ".":
            return None
        try:
            return float(str(val).replace(",", ""))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_date(val: Any) -> datetime:
        try:
            return datetime.fromisoformat(str(val)).replace(tzinfo=UTC)
        except (ValueError, TypeError):
            return datetime.now(UTC)
