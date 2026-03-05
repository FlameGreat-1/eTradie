from __future__ import annotations

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import MacroBias, SurpriseDirection, TrendDirection


class IndicatorAssessment(TimestampedModel):
    currency: Currency
    indicator_name: str
    surprise_direction: SurpriseDirection
    trend_direction: TrendDirection
    impact_score: float
    evidence: str = ""


class EconomicReleaseAnalysis(TimestampedModel):
    assessments: list[IndicatorAssessment] = []
    per_currency_signal: dict[str, MacroBias] = {}
    evidence_chain: list[str] = []
