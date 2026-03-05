from __future__ import annotations

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import MacroBias, RiskSentiment


class CurrencyNewsImpact(TimestampedModel):
    currency: Currency
    sentiment_score: float
    headline_count: int
    dominant_sentiment: RiskSentiment
    signal: MacroBias
    key_headlines: list[str] = []


class NewsAnalysis(TimestampedModel):
    overall_sentiment: RiskSentiment = RiskSentiment.NEUTRAL
    per_currency_impact: list[CurrencyNewsImpact] = []
    per_currency_signal: dict[str, MacroBias] = {}
    evidence_chain: list[str] = []
