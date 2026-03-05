from __future__ import annotations

from datetime import datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.macro.models.provider.market_data import IntermarketSnapshot


class MarketDataSet(TimestampedModel):
    snapshots: list[IntermarketSnapshot] = []
    latest: IntermarketSnapshot | None = None
    sources: list[str] = []
    collected_at: datetime = Field(default_factory=lambda: __import__("datetime").datetime.now(__import__("datetime").UTC))
