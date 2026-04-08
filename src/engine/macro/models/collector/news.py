from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.macro.models.provider.news import NewsItem


class NewsDataSet(TimestampedModel):
    items: list[NewsItem] = []
    sources: list[str] = []
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
