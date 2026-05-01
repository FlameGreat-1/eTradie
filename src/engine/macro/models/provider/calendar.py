from __future__ import annotations

from datetime import datetime

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import EventImpact


class CalendarEvent(TimestampedModel):
    event_name: str
    currency: Currency
    event_time: datetime
    impact: EventImpact = EventImpact.LOW
    source: str = ""
