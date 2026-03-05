from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.logging import get_logger
from engine.shared.models.events import CBTone, CentralBank, MacroBias
from engine.macro.models.processor.interest_rate import (
    BankToneAssessment,
    InterestRateAnalysis,
)
from engine.macro.processors.base import BaseProcessor
from engine.macro.storage.repositories.central_bank.event import CentralBankRepository

logger = get_logger(__name__)

_BANK_CURRENCY = {
    CentralBank.FED: "USD",
    CentralBank.ECB: "EUR",
    CentralBank.BOE: "GBP",
    CentralBank.BOJ: "JPY",
}


class InterestRateProcessor(BaseProcessor):
    processor_name = "interest_rate"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _do_process(self) -> InterestRateAnalysis:
        repo = CentralBankRepository(self._session)
        assessments = []
        per_currency: dict[str, MacroBias] = {}
        evidence: list[str] = []

        for bank in CentralBank:
            events = await repo.get_latest_by_bank(bank.value, limit=10)
            if not events:
                continue

            hawk_count = sum(1 for e in events if e.tone == CBTone.HAWKISH.value)
            dove_count = sum(1 for e in events if e.tone == CBTone.DOVISH.value)

            if hawk_count > dove_count:
                tone = CBTone.HAWKISH
                signal = MacroBias.BULLISH
            elif dove_count > hawk_count:
                tone = CBTone.DOVISH
                signal = MacroBias.BEARISH
            else:
                tone = CBTone.NEUTRAL
                signal = MacroBias.NEUTRAL

            rate_decisions = await repo.get_rate_decisions(bank.value, limit=2)
            latest_rate = rate_decisions[0].rate_current if rate_decisions and rate_decisions[0].rate_current else 0.0
            rate_dir = "unchanged"
            if len(rate_decisions) >= 2 and rate_decisions[0].rate_current and rate_decisions[1].rate_current:
                if rate_decisions[0].rate_current > rate_decisions[1].rate_current:
                    rate_dir = "rising"
                elif rate_decisions[0].rate_current < rate_decisions[1].rate_current:
                    rate_dir = "falling"

            currency = _BANK_CURRENCY.get(bank, "")
            per_currency[currency] = signal
            evidence.append(f"{bank.value}: tone={tone.value}, rate={latest_rate}, direction={rate_dir}")

            assessments.append(BankToneAssessment(
                bank=bank,
                tone=tone,
                latest_rate=latest_rate,
                rate_direction=rate_dir,
                evidence=[f"hawk={hawk_count}, dove={dove_count} from last 10 events"],
            ))

        return InterestRateAnalysis(
            bank_assessments=assessments,
            per_currency_signal=per_currency,
            evidence_chain=evidence,
        )
