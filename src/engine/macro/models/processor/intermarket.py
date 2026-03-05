from __future__ import annotations

from engine.shared.models.base import TimestampedModel
from engine.shared.models.events import MacroBias, RiskSentiment, TrendDirection


class CorrelationSignal(TimestampedModel):
    asset: str
    current_value: float
    trend: TrendDirection
    correlation_with_usd: float
    implication: str = ""


class IntermarketAnalysis(TimestampedModel):
    risk_sentiment: RiskSentiment = RiskSentiment.NEUTRAL
    gold_signal: CorrelationSignal | None = None
    oil_signal: CorrelationSignal | None = None
    bond_signal: CorrelationSignal | None = None
    per_currency_signal: dict[str, MacroBias] = {}
    evidence_chain: list[str] = []
