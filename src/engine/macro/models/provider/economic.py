from __future__ import annotations

from datetime import datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import EventImpact, EventType, InflationType, SurpriseDirection


class EconomicRelease(TimestampedModel):
    currency: Currency
    indicator: EventType
    indicator_name: str
    actual: float | None = None
    forecast: float | None = None
    previous: float | None = None
    surprise: float | None = Field(default=None, description="actual - forecast")
    surprise_direction: SurpriseDirection = SurpriseDirection.INLINE
    impact: EventImpact = EventImpact.MEDIUM
    inflation_type: InflationType | None = Field(
        default=None,
        description="CORE or HEADLINE for CPI/PCE/PPI releases, None for non-inflation",
    )
    release_time: datetime
    source: str = ""
