from __future__ import annotations

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency


class SentimentReading(TimestampedModel):
    currency: Currency
    source: str = ""
    long_percentage: float = 50.0
    short_percentage: float = 50.0
    net_positioning: float = 0.0
