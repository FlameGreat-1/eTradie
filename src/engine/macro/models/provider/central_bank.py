from __future__ import annotations

from datetime import datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.shared.models.events import CBTone, CentralBank, EventType


class RateDecision(TimestampedModel):
    bank: CentralBank
    event_type: EventType = EventType.RATE_DECISION
    rate_current: float
    rate_previous: float
    rate_change_bps: int = Field(description="Basis points change")
    tone: CBTone
    statement_summary: str = ""
    decision_date: datetime


class CentralBankSpeech(TimestampedModel):
    bank: CentralBank
    event_type: EventType = EventType.CB_SPEECH
    speaker: str
    title: str
    summary: str = ""
    tone: CBTone
    speech_date: datetime
    source_url: str = ""


class MeetingMinutes(TimestampedModel):
    bank: CentralBank
    event_type: EventType = EventType.MEETING_MINUTES
    title: str
    summary: str = ""
    tone: CBTone
    hawkish_count: int = 0
    dovish_count: int = 0
    meeting_date: datetime
    release_date: datetime
    source_url: str = ""


class ForwardGuidance(TimestampedModel):
    bank: CentralBank
    event_type: EventType = EventType.FORWARD_GUIDANCE
    title: str
    summary: str = ""
    tone: CBTone
    rate_path_signal: str = ""
    guidance_date: datetime
    source_url: str = ""
