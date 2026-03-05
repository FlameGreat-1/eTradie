from __future__ import annotations

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import MacroBias


class CurrencySentiment(TimestampedModel):
    currency: Currency
    institutional_long_pct: float
    institutional_short_pct: float
    positioning_lean: MacroBias
    signal: MacroBias
    evidence: str = ""


class SentimentAnalysis(TimestampedModel):
    per_currency: list[CurrencySentiment] = []
    per_currency_signal: dict[str, MacroBias] = {}
    evidence_chain: list[str] = []
