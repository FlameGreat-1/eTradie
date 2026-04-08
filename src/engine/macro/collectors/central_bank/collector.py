from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.shared.models.events import MonetaryPolicyAction
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.central_bank import CentralBankDataSet, PolicyAction
from engine.macro.storage.schemas.central_bank import CentralBankEventRow

logger = get_logger(__name__)


class CentralBankCollector(BaseCollector):
    collector_name = "central_bank"
    cache_namespace = "cb"

    async def _do_collect(self, user_id: str) -> CentralBankDataSet:
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

        # Upsert with deduplication: same user + bank + title + timestamp = one row.
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

                event_ts = (
                    getattr(event, "speech_date", None)
                    or getattr(event, "guidance_date", None)
                    or datetime.now(UTC)
                )

                rows.append(
                    {
                        "user_id": user_id,
                        "bank": event.bank.value if hasattr(event, "bank") else "",
                        "event_type": (
                            event.event_type.value
                            if hasattr(event, "event_type")
                            else "CB_SPEECH"
                        ),
                        "title": getattr(event, "title", ""),
                        "content": getattr(event, "summary", ""),
                        "speaker": getattr(event, "speaker", ""),
                        "tone": (
                            event.tone.value if hasattr(event, "tone") else "NEUTRAL"
                        ),
                        "policy_action": (
                            policy_action_val.value if policy_action_val else "NONE"
                        ),
                        "balance_sheet_direction": balance_sheet_dir,
                        "source_url": getattr(event, "source_url", ""),
                        "event_timestamp": event_ts,
                    }
                )

            if rows:
                await repo.bulk_upsert(
                    rows,
                    index_elements=[
                        "user_id", "bank", "title", "event_timestamp",
                    ],
                    update_fields=[
                        "content", "speaker", "tone", "policy_action",
                        "balance_sheet_direction", "source_url", "event_type",
                    ],
                )

        dataset = CentralBankDataSet(
            speeches=[e for e in all_events if hasattr(e, "speech_date")],
            forward_guidance=[e for e in all_events if hasattr(e, "guidance_date")],
            policy_actions=policy_actions,
            banks_reporting=banks_reporting,
            collected_at=datetime.now(UTC),
        )

        await self._cache.set(
            self.cache_namespace,
            self._user_cache_key(user_id),
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(all_events))
        return dataset
