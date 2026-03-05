from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.shared.models.events import EventImpact, MacroBias
from engine.macro.models.processor.currency_bias import CurrencyBiasScore
from engine.macro.models.processor.dxy import DXYAnalysis
from engine.macro.models.processor.event_risk import EventRiskAssessment


class COTSignalSummary(TimestampedModel):
    per_currency: dict[str, MacroBias] = {}
    extreme_currencies: list[str] = []
    reversal_risk_currencies: list[str] = []


class MacroBiasOutput(TimestampedModel):
    run_id: UUID
    run_timestamp: datetime
    currency_scores: list[CurrencyBiasScore] = []
    dxy_analysis: DXYAnalysis | None = None
    cot_summary: COTSignalSummary | None = None
    event_risk: EventRiskAssessment | None = None
    overall_risk_level: EventImpact = EventImpact.LOW
    data_snapshot_ids: dict[str, str] = Field(
        default_factory=dict,
        description="Source -> snapshot ID for reproducibility",
    )
    evidence_chain: list[str] = []
    rules_version: str = "1.0"
