from __future__ import annotations

from datetime import datetime

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import EventImpact, RiskSentiment


class NewsItem(TimestampedModel):
    headline: str
    source: str
    currencies_mentioned: list[Currency] = []
    published_at: datetime
    impact: EventImpact = EventImpact.LOW
    dedupe_hash: str = ""
