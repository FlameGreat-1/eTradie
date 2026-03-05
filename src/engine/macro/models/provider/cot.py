from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.shared.models.currency import Currency


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


class COTReport(TimestampedModel):
    report_date: date
    release_timestamp: datetime
    positions: list[COTPosition]
