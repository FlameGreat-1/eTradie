from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.shared.models.events import MacroBias, SurpriseDirection, TrendDirection
from engine.macro.models.processor.economic_release import (
    EconomicReleaseAnalysis,
    IndicatorAssessment,
)
from engine.macro.processors.base import BaseProcessor
from engine.macro.storage.repositories.economic.release import EconomicReleaseRepository

logger = get_logger(__name__)


class EconomicReleaseProcessor(BaseProcessor):
    processor_name = "economic_release"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _do_process(self) -> EconomicReleaseAnalysis:
        repo = EconomicReleaseRepository(self._session)
        since = datetime.now(UTC) - timedelta(days=30)
        assessments: list[IndicatorAssessment] = []
        per_currency: dict[str, MacroBias] = {}
        evidence: list[str] = []

        for currency in Currency:
            releases = await repo.get_by_currency(currency.value, since=since, limit=20)
            if not releases:
                continue

            beat_count = sum(1 for r in releases if r.surprise_direction == SurpriseDirection.BEAT.value)
            miss_count = sum(1 for r in releases if r.surprise_direction == SurpriseDirection.MISS.value)
            total = len(releases)

            if total == 0:
                continue

            beat_ratio = beat_count / total
            if beat_ratio > 0.6:
                signal = MacroBias.BULLISH
                trend = TrendDirection.UP
            elif beat_ratio < 0.4:
                signal = MacroBias.BEARISH
                trend = TrendDirection.DOWN
            else:
                signal = MacroBias.NEUTRAL
                trend = TrendDirection.SIDEWAYS

            per_currency[currency.value] = signal
            evidence.append(f"{currency.value}: {beat_count} beats, {miss_count} misses out of {total}")

            for r in releases[:5]:
                assessments.append(IndicatorAssessment(
                    currency=currency,
                    indicator_name=r.indicator_name,
                    surprise_direction=SurpriseDirection(r.surprise_direction),
                    trend_direction=trend,
                    impact_score=1.0 if r.impact == "HIGH" else 0.5,
                    evidence=f"actual={r.actual}, forecast={r.forecast}, surprise={r.surprise}",
                ))

        return EconomicReleaseAnalysis(
            assessments=assessments,
            per_currency_signal=per_currency,
            evidence_chain=evidence,
        )
