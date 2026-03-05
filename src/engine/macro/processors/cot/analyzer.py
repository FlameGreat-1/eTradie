from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.shared.models.events import MacroBias, TrendDirection
from engine.macro.models.processor.cot import COTAnalysis, CurrencyCOTAssessment
from engine.macro.processors.base import BaseProcessor
from engine.macro.storage.repositories.cot.report import COTRepository

logger = get_logger(__name__)

_EXTREME_PERCENTILE_THRESHOLD = 90.0


class COTProcessor(BaseProcessor):
    processor_name = "cot"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _do_process(self) -> COTAnalysis:
        repo = COTRepository(self._session)
        assessments: list[CurrencyCOTAssessment] = []
        per_currency: dict[str, MacroBias] = {}
        evidence: list[str] = []

        for currency in Currency:
            current, previous = await repo.get_wow_pair(currency.value)
            if current is None:
                continue

            wow_change = 0
            if previous is not None:
                wow_change = current.non_commercial_net - previous.non_commercial_net

            if wow_change > 0:
                wow_dir = TrendDirection.UP
            elif wow_change < 0:
                wow_dir = TrendDirection.DOWN
            else:
                wow_dir = TrendDirection.SIDEWAYS

            history = await repo.get_history(currency.value, limit=52)
            is_extreme = False
            extreme_type = ""
            percentile = 50.0
            if len(history) >= 10:
                nets = sorted([r.non_commercial_net for r in history])
                rank = sum(1 for n in nets if n <= current.non_commercial_net)
                percentile = (rank / len(nets)) * 100
                if percentile >= _EXTREME_PERCENTILE_THRESHOLD:
                    is_extreme = True
                    extreme_type = "EXTREME_LONG"
                elif percentile <= (100 - _EXTREME_PERCENTILE_THRESHOLD):
                    is_extreme = True
                    extreme_type = "EXTREME_SHORT"

            reversal_risk = is_extreme
            if is_extreme:
                signal = MacroBias.NEUTRAL
            elif current.non_commercial_net > 0 and wow_change > 0:
                signal = MacroBias.BULLISH
            elif current.non_commercial_net < 0 and wow_change < 0:
                signal = MacroBias.BEARISH
            else:
                signal = MacroBias.NEUTRAL

            per_currency[currency.value] = signal
            evidence.append(
                f"{currency.value}: net={current.non_commercial_net}, "
                f"wow={wow_change:+d}, percentile={percentile:.0f}%, "
                f"extreme={is_extreme}"
            )

            assessments.append(CurrencyCOTAssessment(
                currency=currency,
                non_commercial_net=current.non_commercial_net,
                wow_change=wow_change,
                wow_direction=wow_dir,
                is_extreme=is_extreme,
                extreme_type=extreme_type,
                percentile_rank=percentile,
                signal=signal,
                reversal_risk=reversal_risk,
                evidence=evidence[-1],
            ))

        return COTAnalysis(
            assessments=assessments,
            per_currency_signal=per_currency,
            evidence_chain=evidence,
        )
