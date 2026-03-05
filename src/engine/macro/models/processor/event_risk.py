from __future__ import annotations

from datetime import datetime

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import EventImpact


class UpcomingEvent(TimestampedModel):
    event_name: str
    currency: Currency
    impact: EventImpact
    event_time: datetime
    minutes_until: int
    in_lockout_window: bool = False


class EventRiskAssessment(TimestampedModel):
    upcoming_high_impact: list[UpcomingEvent] = []
    lockout_active: bool = False
    lockout_currencies: list[Currency] = []
    next_high_impact_event: UpcomingEvent | None = None
    risk_level: EventImpact = EventImpact.LOW
    evidence_chain: list[str] = []
