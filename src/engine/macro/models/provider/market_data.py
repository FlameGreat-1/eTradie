from __future__ import annotations

from datetime import datetime

from engine.shared.models.base import TimestampedModel
from engine.shared.models.events import DXYMomentum


class IntermarketSnapshot(TimestampedModel):
    dxy_value: float | None = None
    dxy_momentum: DXYMomentum | None = None
    gold_price: float | None = None
    silver_price: float | None = None
    oil_price: float | None = None
    iron_ore: float | None = None
    dairy_gdt: float | None = None
    copper: float | None = None
    natural_gas: float | None = None
    us2y_yield: float | None = None
    us10y_yield: float | None = None
    us30y_yield: float | None = None
    sp500: float | None = None
    vix: float | None = None
    snapshot_at: datetime
    source: str = ""
