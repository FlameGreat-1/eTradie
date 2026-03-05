from __future__ import annotations

from datetime import datetime

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import EventImpact, RiskSentiment


class NewsItem(TimestampedModel):
    headline: str
    source: str
    url: str = ""
    summary: str = ""
    currencies_mentioned: list[Currency] = []
    impact: EventImpact = EventImpact.MEDIUM
    sentiment: RiskSentiment = RiskSentiment.NEUTRAL
    published_at: datetime
    dedupe_hash: str = ""
