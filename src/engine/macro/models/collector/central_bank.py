from __future__ import annotations

from datetime import datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.shared.models.events import CentralBank
from engine.macro.models.provider.central_bank import (
    CentralBankSpeech,
    ForwardGuidance,
    MeetingMinutes,
    RateDecision,
)


class CentralBankDataSet(TimestampedModel):
    rate_decisions: list[RateDecision] = []
    speeches: list[CentralBankSpeech] = []
    meeting_minutes: list[MeetingMinutes] = []
    forward_guidance: list[ForwardGuidance] = []
    banks_reporting: list[CentralBank] = []
    collected_at: datetime = Field(default_factory=lambda: __import__("datetime").datetime.now(__import__("datetime").UTC))
