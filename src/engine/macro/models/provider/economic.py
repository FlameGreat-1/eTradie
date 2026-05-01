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
    previous: float | None = None
    release_time: datetime
    source: str = ""
