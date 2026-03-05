from __future__ import annotations

from datetime import datetime

from engine.shared.models.base import TimestampedModel


class IntermarketSnapshot(TimestampedModel):
    dxy_value: float | None = None
    gold_price: float | None = None
    silver_price: float | None = None
    oil_price: float | None = None
    us2y_yield: float | None = None
    us10y_yield: float | None = None
    us30y_yield: float | None = None
    sp500: float | None = None
    vix: float | None = None
    snapshot_at: datetime
    source: str = ""
