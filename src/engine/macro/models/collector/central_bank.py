from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.shared.models.events import CentralBank
from engine.macro.models.provider.central_bank import RateDecision


class CentralBankDataSet(TimestampedModel):
    rate_decisions: list[RateDecision] = []
    banks_reporting: list[CentralBank] = []
    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
