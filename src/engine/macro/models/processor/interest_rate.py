from __future__ import annotations

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import CBTone, CentralBank, MacroBias


class BankToneAssessment(TimestampedModel):
    bank: CentralBank
    tone: CBTone
    latest_rate: float
    rate_direction: str
    evidence: list[str] = []


class RateDifferential(TimestampedModel):
    base_currency: Currency
    quote_currency: Currency
    differential_bps: int
    favors: Currency
    signal: MacroBias


class InterestRateAnalysis(TimestampedModel):
    bank_assessments: list[BankToneAssessment] = []
    differentials: list[RateDifferential] = []
    per_currency_signal: dict[str, MacroBias] = {}
    evidence_chain: list[str] = []
