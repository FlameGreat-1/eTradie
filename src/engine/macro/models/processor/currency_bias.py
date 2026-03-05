from __future__ import annotations

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import MacroBias


class BiasContribution(TimestampedModel):
    factor: str
    signal: MacroBias
    weight: float
    weighted_score: float
    evidence: str = ""


class CurrencyBiasScore(TimestampedModel):
    currency: Currency
    bias: MacroBias
    score: float
    contributions: list[BiasContribution] = []
    evidence_chain: list[str] = []
