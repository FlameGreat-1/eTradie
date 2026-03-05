from __future__ import annotations

from datetime import datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import EventImpact, EventType, SurpriseDirection


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
    release_time: datetime
    source: str = ""
