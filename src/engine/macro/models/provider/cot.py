from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency
from engine.shared.models.events import COTSignalStrength


class COTPosition(TimestampedModel):
    currency: Currency
    contract_name: str
    non_commercial_long: int
    non_commercial_short: int
    non_commercial_net: int = Field(description="long - short")
    commercial_long: int
    commercial_short: int
    commercial_net: int
    open_interest: int
    report_date: date


class COTPositionEnriched(COTPosition):
    wow_change: int = Field(default=0, description="Week-over-week net change")
    percentile_rank: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Current net position as percentile of 52-week range",
    )
    extreme_flag: bool = Field(
        default=False,
        description="True when percentile_rank >= 90 or <= 10",
    )
    signal_strength: COTSignalStrength = COTSignalStrength.NEUTRAL
    commercial_vs_speculator_divergence: bool = Field(
        default=False,
        description="True when commercials and speculators are positioned opposite",
    )


class TFFPosition(TimestampedModel):
    currency: Currency
    contract_name: str
    leveraged_long: int
    leveraged_short: int
    leveraged_net: int = Field(description="leveraged long - short")
    asset_manager_long: int = 0
    asset_manager_short: int = 0
    asset_manager_net: int = 0
    report_date: date


class COTReport(TimestampedModel):
    report_date: date
    release_timestamp: datetime
    positions: list[COTPosition]
    tff_positions: list[TFFPosition] = []
