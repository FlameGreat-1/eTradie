from __future__ import annotations


from datetime import datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.shared.models.events import CBTone, CentralBank, EventType, MonetaryPolicyAction


class RateDecision(TimestampedModel):
    bank: CentralBank
    event_type: EventType = EventType.RATE_DECISION
    rate_current: float
    rate_previous: float
    rate_change_bps: int = Field(description="Basis points change")
    decision_date: datetime
