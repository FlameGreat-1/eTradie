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
    # Consensus forecast, prior release, and (post-event) actual, as published
    # by the calendar feed. Kept as free-form strings because feeds mix units
    # and suffixes ("95K", "4.3%", "-1.61B"). Empty string when the feed omits
    # the field (e.g. actual before the event prints).
    forecast: str = ""
    previous: str = ""
    actual: str = ""
    source: str = ""
