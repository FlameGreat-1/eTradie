from __future__ import annotations

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import MacroBias, TrendDirection


class CurrencyCOTAssessment(TimestampedModel):
    currency: Currency
    non_commercial_net: int
    wow_change: int
    wow_direction: TrendDirection
    is_extreme: bool = False
    extreme_type: str = ""
    percentile_rank: float = 0.0
    signal: MacroBias = MacroBias.NEUTRAL
    reversal_risk: bool = False
    evidence: str = ""


class COTAnalysis(TimestampedModel):
    assessments: list[CurrencyCOTAssessment] = []
    per_currency_signal: dict[str, MacroBias] = {}
    evidence_chain: list[str] = []
