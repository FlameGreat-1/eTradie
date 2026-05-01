from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.shared.models.events import EventType, MonetaryPolicyAction
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.central_bank import CentralBankDataSet, PolicyAction
from engine.macro.models.provider.central_bank import (
    CentralBankSpeech,
    ForwardGuidance,
    MeetingMinutes,
    RateDecision,
)
from engine.macro.providers.central_bank.base import compute_tone_score

logger = get_logger(__name__)


class CentralBankCollector(BaseCollector):
    """Collect central bank events from all registered CB providers.

    Categorizes events into speeches, rate decisions, meeting minutes,
    and forward guidance. Computes tone_score for each event and
    extracts rate_current/rate_previous from rate decisions.
    """

    collector_name = "central_bank"
    cache_namespace = "cb"
    cache_model = CentralBankDataSet

    async def _do_collect(self) -> CentralBankDataSet:
        all_events = []
        banks_reporting = []
        policy_actions: list[PolicyAction] = []

        for provider in self._providers:
            try:
                events = await provider.fetch()
                all_events.extend(events)
                bank = getattr(provider, "bank", None)
                if bank and bank not in banks_reporting:
                    banks_reporting.append(bank)
            except Exception:
                logger.warning("cb_provider_skipped", provider=provider.provider_name)

        # Categorize events by type for the dataset
        speeches: list[CentralBankSpeech] = []
        rate_decisions: list[RateDecision] = []
        meeting_minutes: list[MeetingMinutes] = []
        forward_guidance: list[ForwardGuidance] = []

        for event in all_events:
            if isinstance(event, RateDecision):
                rate_decisions.append(event)
            elif isinstance(event, MeetingMinutes):
                meeting_minutes.append(event)
            elif isinstance(event, ForwardGuidance):
                forward_guidance.append(event)
            elif isinstance(event, CentralBankSpeech):
                speeches.append(event)
            else:
                # Fallback: treat as speech if type is unknown
                speeches.append(event)

        # Upsert with deduplication: bank + title + timestamp = one row.
        async with self._db.session() as session:
            from engine.macro.storage.repositories.central_bank.event import (
                CentralBankRepository,
            )

            repo = CentralBankRepository(session)
            rows = []
            for event in all_events:
                policy_action_val = getattr(
                    event, "monetary_policy_action", MonetaryPolicyAction.NONE
                )
                balance_sheet_dir = ""
                if policy_action_val == MonetaryPolicyAction.QE:
                    balance_sheet_dir = "EXPANDING"
                elif policy_action_val == MonetaryPolicyAction.QT:
                    balance_sheet_dir = "CONTRACTING"

                if policy_action_val != MonetaryPolicyAction.NONE:
                    bank_val = getattr(event, "bank", None)
                    if bank_val:
                        policy_actions.append(
                            PolicyAction(
                                bank=bank_val,
                                action=policy_action_val,
                                description=getattr(event, "title", ""),
                                detected_at=datetime.now(UTC),
                            )
                        )

                # Determine event timestamp from the appropriate date field
                event_ts = (
                    getattr(event, "decision_date", None)
                    or getattr(event, "speech_date", None)
                    or getattr(event, "release_date", None)
                    or getattr(event, "guidance_date", None)
                    or datetime.now(UTC)
                )

                # Compute numeric tone score from event text
                event_text = (
                    f"{getattr(event, 'title', '')} "
                    f"{getattr(event, 'summary', '')} "
                    f"{getattr(event, 'statement_summary', '')}"
                )
                tone_score = compute_tone_score(event_text)

                # Extract rate values from RateDecision events
                rate_current = (
                    event.rate_current
                    if isinstance(event, RateDecision)
                    else None
                )
                rate_previous = (
                    event.rate_previous
                    if isinstance(event, RateDecision)
                    else None
                )

                rows.append(
                    {
                        "bank": event.bank.value if hasattr(event, "bank") else "",
                        "event_type": (
                            event.event_type.value
                            if hasattr(event, "event_type")
                            else EventType.CB_SPEECH.value
                        ),
                        "title": getattr(event, "title", ""),
                        "content": getattr(event, "summary", ""),
                        "speaker": getattr(event, "speaker", ""),
                        "tone": (
                            event.tone.value if hasattr(event, "tone") else "NEUTRAL"
                        ),
                        "tone_score": tone_score,
                        "policy_action": (
                            policy_action_val.value if policy_action_val else "NONE"
                        ),
                        "balance_sheet_direction": balance_sheet_dir,
                        "rate_current": rate_current,
                        "rate_previous": rate_previous,
                        "source_url": getattr(event, "source_url", ""),
                        "event_timestamp": event_ts,
                    }
                )

            if rows:
                await repo.bulk_upsert(
                    rows,
                    index_elements=[
                        "bank", "title", "event_timestamp",
                    ],
                    update_fields=[
                        "content", "speaker", "tone", "tone_score",
                        "policy_action", "balance_sheet_direction",
                        "rate_current", "rate_previous",
                        "source_url", "event_type",
                    ],
                )

        dataset = CentralBankDataSet(
            rate_decisions=rate_decisions,
            speeches=speeches,
            meeting_minutes=meeting_minutes,
            forward_guidance=forward_guidance,
            policy_actions=policy_actions,
            banks_reporting=banks_reporting,
            collected_at=datetime.now(UTC),
        )

        await self._cache.set(
            self.cache_namespace,
            self._cache_key(),
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(all_events))
        return dataset

    async def _read_from_db(self):
        # We don't read from DB during analysis because assembling the dataset
        # from the DB is expensive and not strictly required if we have an empty fallback.
        # However, to be complete, if there's no cache, we return an empty dataset.
        return None

    def _empty_dataset(self):
        return CentralBankDataSet(
            rate_decisions=[],
            speeches=[],
            meeting_minutes=[],
            forward_guidance=[],
            policy_actions=[],
            banks_reporting=[],
            collected_at=datetime.now(UTC),
        )
