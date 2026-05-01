from __future__ import annotations

import abc
import time
from typing import Any

from engine.shared.logging import get_logger
from engine.shared.models.events import (
    CBTone,
    CentralBank,
    EventType,
    MonetaryPolicyAction,
    ProviderCategory,
)
from engine.shared.rss import RSSParser
from engine.shared.rss.parser import RSSEntry
from engine.macro.models.provider.central_bank import (
    CentralBankSpeech,
    ForwardGuidance,
    MeetingMinutes,
    RateDecision,
)
from engine.macro.providers.base import BaseProvider

logger = get_logger(__name__)

_HAWKISH_KEYWORDS = frozenset(
    {
        "rate hike",
        "tightening",
        "inflation concern",
        "hawkish",
        "restrictive",
        "above target",
        "price stability",
        "rate increase",
    }
)
_DOVISH_KEYWORDS = frozenset(
    {
        "rate cut",
        "easing",
        "accommodative",
        "dovish",
        "slowdown",
        "below target",
        "support growth",
        "rate reduction",
        "stimulus",
    }
)
_QE_KEYWORDS = frozenset(
    {
        "quantitative easing",
        "asset purchase",
        "bond buying",
        "balance sheet expansion",
        "reinvestment",
        "purchase programme",
        "purchase program",
        "mbs purchase",
    }
)
_QT_KEYWORDS = frozenset(
    {
        "quantitative tightening",
        "balance sheet reduction",
        "runoff",
        "roll-off",
        "tapering",
        "wind down",
        "balance sheet normalization",
        "shrinking balance sheet",
    }
)


def classify_tone(text: str) -> CBTone:
    lower = text.lower()
    hawk_score = sum(1 for kw in _HAWKISH_KEYWORDS if kw in lower)
    dove_score = sum(1 for kw in _DOVISH_KEYWORDS if kw in lower)
    if hawk_score > dove_score:
        return CBTone.HAWKISH
    if dove_score > hawk_score:
        return CBTone.DOVISH
    return CBTone.NEUTRAL


def compute_tone_score(text: str) -> float:
    """Compute a numeric tone score from text.

    Returns a float between 0.0 and 1.0:
    - 0.0 = strongly dovish
    - 0.5 = neutral
    - 1.0 = strongly hawkish

    The score is based on keyword density: the ratio of hawkish
    keywords to total (hawkish + dovish) keywords found.
    """
    lower = text.lower()
    hawk_count = sum(1 for kw in _HAWKISH_KEYWORDS if kw in lower)
    dove_count = sum(1 for kw in _DOVISH_KEYWORDS if kw in lower)
    total = hawk_count + dove_count
    if total == 0:
        return 0.5
    return round(hawk_count / total, 3)


def classify_policy_action(text: str) -> MonetaryPolicyAction:
    lower = text.lower()
    if any(kw in lower for kw in _QT_KEYWORDS):
        return MonetaryPolicyAction.QT
    if any(kw in lower for kw in _QE_KEYWORDS):
        return MonetaryPolicyAction.QE
    return MonetaryPolicyAction.NONE


def classify_event_type(title: str) -> EventType:
    lower = title.lower()
    if any(kw in lower for kw in ("rate", "interest", "monetary policy decision")):
        return EventType.RATE_DECISION
    if any(
        kw in lower for kw in ("speech", "remarks", "testimony", "press conference")
    ):
        return EventType.CB_SPEECH
    if any(kw in lower for kw in ("minutes", "account")):
        return EventType.MEETING_MINUTES
    if any(kw in lower for kw in ("guidance", "outlook", "projection", "forecast")):
        return EventType.FORWARD_GUIDANCE
    return EventType.CB_SPEECH


class BaseCentralBankProvider(BaseProvider, abc.ABC):
    category = ProviderCategory.CENTRAL_BANK
    bank: CentralBank
    feed_url: str

    def __init__(self, rss_parser: RSSParser) -> None:
        super().__init__()
        self._rss = rss_parser

    async def fetch(
        self,
    ) -> list[CentralBankSpeech | RateDecision | ForwardGuidance | MeetingMinutes]:
        start = time.monotonic()
        try:
            entries = await self._rss.fetch_and_parse(
                self.feed_url,
                provider_name=self.provider_name,
                category=self.category.value,
            )
            results = [self._parse_entry(e) for e in entries]
            self._record_success(time.monotonic() - start)
            return results
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error(
                "cb_provider_fetch_failed", provider=self.provider_name, error=str(exc)
            )
            raise

    def _parse_entry(
        self, entry: RSSEntry
    ) -> CentralBankSpeech | RateDecision | ForwardGuidance | MeetingMinutes:
        event_type = classify_event_type(entry.title)

        if event_type == EventType.FORWARD_GUIDANCE:
            return ForwardGuidance(
                bank=self.bank,
                title=entry.title,
                guidance_date=entry.published_at,
                source_url=entry.link,
            )

        if event_type == EventType.MEETING_MINUTES:
            return MeetingMinutes(
                bank=self.bank,
                title=entry.title,
                meeting_date=entry.published_at,
                release_date=entry.published_at,
                source_url=entry.link,
            )

        return CentralBankSpeech(
            bank=self.bank,
            event_type=event_type,
            title=entry.title,
            speech_date=entry.published_at,
            source_url=entry.link,
        )
