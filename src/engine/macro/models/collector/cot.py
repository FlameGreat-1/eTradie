from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.macro.models.provider.cot import COTPosition, COTPositionEnriched, TFFPosition


class COTDataSet(TimestampedModel):
    latest_positions: list[COTPositionEnriched] = []
    previous_positions: list[COTPosition] = []
    tff_positions: list[TFFPosition] = []
    report_date: date | None = None
    previous_report_date: date | None = None
    wow_shifts: dict[str, int] = Field(
        default_factory=dict,
        description="Currency -> week-over-week net change",
    )
    extremes_flagged: list[str] = Field(
        default_factory=list,
        description="Currencies at 52-week positioning extremes",
    )
    has_tff_data: bool = False
    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
