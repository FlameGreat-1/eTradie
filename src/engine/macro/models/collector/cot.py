from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.macro.models.provider.cot import COTPosition


class COTDataSet(TimestampedModel):
    latest_positions: list[COTPosition] = []
    previous_positions: list[COTPosition] = []
    report_date: date | None = None
    collected_at: datetime = Field(default_factory=lambda: __import__("datetime").datetime.now(__import__("datetime").UTC))
