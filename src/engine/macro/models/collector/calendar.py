from __future__ import annotations

from datetime import datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.macro.models.provider.calendar import CalendarEvent


class CalendarDataSet(TimestampedModel):
    events: list[CalendarEvent] = []
    sources: list[str] = []
    collected_at: datetime = Field(default_factory=lambda: __import__("datetime").datetime.now(__import__("datetime").UTC))
