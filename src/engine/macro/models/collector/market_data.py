from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.macro.models.provider.market_data import IntermarketSnapshot


class MarketDataSet(TimestampedModel):
    snapshots: list[IntermarketSnapshot] = []
    latest: IntermarketSnapshot | None = None
    sources: list[str] = []
    # Interpreted cross-asset signals (yield-curve slope/inversion, VIX regime,
    # iron-ore/dairy commodity-currency proxies). Populated by the intermarket
    # collector so the same signals it persists to the DB also reach the cache,
    # the durable snapshot, the gateway extractor, and the LLM. Left None by the
    # DXY collector, which shares this model but has no correlation signals.
    correlation_signals: dict[str, Any] | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
