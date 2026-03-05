from __future__ import annotations

from engine.shared.models.base import TimestampedModel
from engine.shared.models.events import MacroBias, TrendDirection


class DXYAnalysis(TimestampedModel):
    current_value: float
    trend_direction: TrendDirection
    key_support_levels: list[float] = []
    key_resistance_levels: list[float] = []
    bias: MacroBias
    structure_summary: str = ""
    evidence_chain: list[str] = []
