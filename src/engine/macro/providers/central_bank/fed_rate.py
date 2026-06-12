"""FRED-sourced central-bank policy-rate provider (Fed + ECB).

The RSS central-bank providers parse press-release headlines: they classify
tone (HAWKISH/DOVISH/NEUTRAL) and QE/QT, but an RSS title never carries the
numeric policy rate, so they can never construct a ``RateDecision``. That left
``rate_current`` / ``rate_previous`` / ``rate_change_bps`` permanently empty on
the CentralBankDataSet -- structured fields the LLM was meant to reason over
but never received.

This module closes that gap using the authoritative machine-readable series the
central banks publish through FRED, and goes one step further: instead of a
single latest decision it emits the FULL sequence of distinct rate changes over
a multi-year window (newest first). Each policy step becomes one
``RateDecision`` in the dataset's ``rate_decisions`` list, so the LLM can see
the entire hiking/cutting trajectory (e.g. 0.25 -> 5.50 across 2022-23, then a
cut cycle down to 3.75) and reason about where we are in the cycle, not just
the current level. The first element is always the current rate.

Series used:
  - Fed: ``DFEDTARU`` (target range upper limit -- the headline ceiling) and
    ``DFEDTARL`` (lower limit, logged for context).
  - ECB: ``ECBDFR`` (Deposit Facility Rate -- the rate markets watch for EUR).

These are daily series whose *level* only steps on a policy decision, so each
level transition in the series IS a real decision. Failure is non-fatal: the
CentralBankCollector skips a provider that raises, and a missing FRED key simply
yields no rate decisions, leaving the tone-only signal intact.

FRED API docs: https://fred.stlouisfed.org/docs/api/fred/
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.events import CentralBank, ProviderCategory
from engine.macro.models.provider.central_bank import RateDecision
from engine.macro.providers.base import BaseProvider

logger = get_logger(__name__)

# Fetch exactly 3 years of data. Using a time window instead of a raw observation
# limit correctly handles both daily and monthly series without pulling decades
# of data for monthly OECD series.
_LOOKBACK_YEARS = 3


class BaseFREDRateProvider(BaseProvider):
    """Emit the multi-year sequence of policy-rate decisions for one bank.

    Subclasses set ``bank``, ``provider_name``, the FRED ``upper_series`` (the
    headline rate), and optionally a ``lower_series`` (logged for range
    context, e.g. the Fed target-range floor). ECB has no range, so it sets
    ``lower_series = None``.

    ``fetch()`` returns a list of ``RateDecision`` ordered newest-first: one
    entry per distinct level change within the lookback window. An empty list
    is returned when the key is unset or the series has no usable data.
    """

    category = ProviderCategory.CENTRAL_BANK
    bank: CentralBank
    upper_series: str
    lower_series: Optional[str] = None

    def __init__(self, http_client: HttpClient, *, base_url: str, api_key: str) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def fetch(self) -> list[RateDecision]:
        start = time.monotonic()

        if not self._api_key:
            logger.warning(
                "fred_rate_api_key_missing",
                extra={
                    "provider": self.provider_name,
                    "action": "skipping - no FRED API key configured",
                },
            )
            return []

        try:
            upper = await self._fetch_series(self.upper_series)
            lower = (
                await self._fetch_series(self.lower_series) if self.lower_series else []
            )

            decisions = self._build_history(upper, lower)
            if not decisions:
                logger.warning(
                    "fred_rate_no_decisions",
                    extra={
                        "provider": self.provider_name,
                        "upper_points": len(upper),
                    },
                )
            self._record_success(time.monotonic() - start)
            return decisions
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error(
                "fred_rate_fetch_failed",
                extra={
                    "provider": self.provider_name,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            raise

    async def _fetch_series(self, series_id: str) -> list[tuple[datetime, float]]:
        """Return recent (date, level) observations for a FRED series, newest first.

        Missing observations (FRED encodes these as ".") are skipped. FRED's
        descending sort order is preserved so element 0 is the most recent
        reading.
        """
        obs_start = (
            datetime.now(UTC) - timedelta(days=365 * _LOOKBACK_YEARS)
        ).strftime("%Y-%m-%d")
        raw = await self._http.get(
            f"{self._base_url}/series/observations",
            provider_name=self.provider_name,
            category=self.category.value,
            params={
                "series_id": series_id,
                "api_key": self._api_key,
                "file_type": "json",
                "sort_order": "desc",
                "observation_start": obs_start,
            },
        )
        observations = raw.get("observations", []) if isinstance(raw, dict) else []

        points: list[tuple[datetime, float]] = []
        for obs in observations:
            value = self._parse_float(obs.get("value"))
            if value is None:
                continue
            points.append((self._parse_date(obs.get("date")), value))
        return points

    def _build_history(
        self,
        upper: list[tuple[datetime, float]],
        lower: list[tuple[datetime, float]],
    ) -> list[RateDecision]:
        """Compress a daily level series into its distinct rate decisions.

        The upper series is the headline rate. Walking newest -> oldest, every
        point where the level differs from the next-older level marks a
        decision: the new level took effect on that date. We emit one
        ``RateDecision`` per such transition with:
          - rate_current   = the level after the change,
          - rate_previous  = the level before the change,
          - rate_change_bps = (current - previous) * 100, rounded,
          - decision_date  = the first date the new level was observed.

        The list is newest-first, so element 0 is the current rate. When the
        oldest level in the window has no prior point, we still emit a final
        entry for it with rate_previous == rate_current and 0 bps so the LLM
        always has the earliest anchor level. A genuinely empty series yields
        an empty list.
        """
        if not upper:
            return []

        # Collapse the daily series to (effective_date, level) transitions.
        # upper is newest-first; iterate oldest-first to find the date each
        # level first took effect, then reverse to newest-first.
        oldest_first = list(reversed(upper))
        transitions: list[tuple[datetime, float]] = []
        for ts, level in oldest_first:
            if not transitions or transitions[-1][1] != level:
                transitions.append((ts, level))

        # transitions is now oldest-first, one entry per distinct level with
        # the date it began. Build decisions newest-first.
        decisions: list[RateDecision] = []
        for i in range(len(transitions) - 1, -1, -1):
            eff_date, level = transitions[i]
            if i > 0:
                prev_level = transitions[i - 1][1]
                change_bps = int(round((level - prev_level) * 100))
            else:
                # Oldest level in the window: no prior reference inside the
                # lookback. Anchor it with a zero-change self-reference.
                prev_level = level
                change_bps = 0
            decisions.append(
                RateDecision(
                    bank=self.bank,
                    rate_current=level,
                    rate_previous=prev_level,
                    rate_change_bps=change_bps,
                    decision_date=eff_date,
                )
            )

        current_lower = lower[0][1] if lower else None
        logger.info(
            "fred_rate_history_built",
            extra={
                "provider": self.provider_name,
                "bank": self.bank.value,
                "decisions": len(decisions),
                "rate_current": decisions[0].rate_current if decisions else None,
                "range_lower": current_lower,
            },
        )
        return decisions

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


class FedRateProvider(BaseFREDRateProvider):
    """US Federal Funds target rate from FRED.

    Uses the target *range* (the Fed has published a range, not a single point
    target, since December 2008). The upper limit is the headline ceiling
    quoted as "the Fed funds rate"; the lower limit is logged for context.
    """

    provider_name = "fed_rate"
    bank = CentralBank.FED
    upper_series = "DFEDTARU"
    lower_series = "DFEDTARL"


class ECBRateProvider(BaseFREDRateProvider):
    """ECB Deposit Facility Rate from FRED (series ECBDFR).

    The deposit facility rate is the ECB's effective policy floor and the rate
    markets track for the euro, so the Fed-ECB spread the LLM can now compute
    is the dominant macro driver of EURUSD. The ECB sets a single rate (no
    range), so there is no lower series.
    """

    provider_name = "ecb_rate"
    bank = CentralBank.ECB
    upper_series = "ECBDFR"
    lower_series = None


class BOERateProvider(BaseFREDRateProvider):
    """Bank of England official Bank Rate from FRED (series BOERUKM).

    The Bank Rate is the BoE's single policy rate (no range). Gives GBP pairs
    the UK-vs-US/EU rate differential.
    """

    provider_name = "boe_rate"
    bank = CentralBank.BOE
    upper_series = "BOERUKM"
    lower_series = None


class BOJRateProvider(BaseFREDRateProvider):
    """Bank of Japan policy rate from FRED (series IRSTCB01JPM156N).

    OECD-published immediate/policy interbank rate for Japan -- the standard
    machine-readable proxy for the BoJ's policy stance. Gives JPY pairs the
    Japan-vs-US/EU differential that, together with the carry dynamic, drives
    USDJPY. The BoJ sets a single rate, so there is no lower series.
    """

    provider_name = "boj_rate"
    bank = CentralBank.BOJ
    upper_series = "IRSTCB01JPM156N"
    lower_series = None


class RBARateProvider(BaseFREDRateProvider):
    """Reserve Bank of Australia cash rate from FRED (series IRSTCB01AUM156N).

    OECD-published central-bank policy rate for Australia. Gives AUD pairs the
    Australia-vs-US differential that drives AUDUSD. Single rate, no range.
    """

    provider_name = "rba_rate"
    bank = CentralBank.RBA
    upper_series = "IRSTCB01AUM156N"
    lower_series = None


class BOCRateProvider(BaseFREDRateProvider):
    """Bank of Canada policy rate from FRED (series IRSTCB01CAM156N).

    OECD-published central-bank policy rate for Canada. Gives CAD pairs the
    Canada-vs-US differential that drives USDCAD. Single rate, no range.
    """

    provider_name = "boc_rate"
    bank = CentralBank.BOC
    upper_series = "IRSTCB01CAM156N"
    lower_series = None


class RBNZRateProvider(BaseFREDRateProvider):
    """Reserve Bank of New Zealand Official Cash Rate from FRED
    (series IRSTCB01NZM156N).

    OECD-published central-bank policy rate for New Zealand. Gives NZD pairs
    the NZ-vs-US differential that drives NZDUSD. Single rate, no range.
    """

    provider_name = "rbnz_rate"
    bank = CentralBank.RBNZ
    upper_series = "IRSTCB01NZM156N"
    lower_series = None


class SNBRateProvider(BaseFREDRateProvider):
    """Swiss National Bank policy rate from FRED (series IRSTCB01CHM156N).

    OECD-published central-bank policy rate for Switzerland. Gives CHF pairs
    the Switzerland-vs-US differential that drives USDCHF. Single rate, no
    range.
    """

    provider_name = "snb_rate"
    bank = CentralBank.SNB
    upper_series = "IRSTCB01CHM156N"
    lower_series = None
