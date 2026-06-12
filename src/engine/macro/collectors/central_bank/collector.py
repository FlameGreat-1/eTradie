from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.central_bank import CentralBankDataSet
from engine.macro.models.provider.central_bank import RateDecision

logger = get_logger(__name__)


class CentralBankCollector(BaseCollector):
    """Collect central bank rate decisions from all registered FRED CB providers."""

    collector_name = "central_bank"
    cache_namespace = "cb"
    cache_model = CentralBankDataSet

    async def _do_collect(self) -> CentralBankDataSet:
        all_events = []
        banks_reporting = []
        rate_decisions: list[RateDecision] = []

        for provider in self._providers:
            try:
                events = await provider.fetch()
                all_events.extend(events)
                bank = getattr(provider, "bank", None)
                if bank and bank not in banks_reporting:
                    banks_reporting.append(bank)
            except Exception:
                logger.warning("cb_provider_skipped", provider=provider.provider_name)

        for event in all_events:
            if isinstance(event, RateDecision):
                rate_decisions.append(event)

        # Upsert with deduplication: bank + title + timestamp = one row.
        async with self._db.session() as session:
            from engine.macro.storage.repositories.central_bank.event import (
                CentralBankRepository,
            )

            repo = CentralBankRepository(session)
            rows = []
            for event in rate_decisions:
                # Determine event timestamp from the appropriate date field
                event_ts = getattr(event, "decision_date", datetime.now(UTC))

                rows.append(
                    {
                        "bank": event.bank.value if hasattr(event, "bank") else "",
                        "event_type": event.event_type.value,
                        "title": getattr(event, "title", ""),
                        "content": "",
                        "speaker": "",
                        "tone": "NEUTRAL",
                        "tone_score": 0.5,
                        "policy_action": "NONE",
                        "balance_sheet_direction": "",
                        "rate_current": event.rate_current,
                        "rate_previous": event.rate_previous,
                        "rate_change_bps": event.rate_change_bps,
                        "source_url": getattr(event, "source_url", ""),
                        "event_timestamp": event_ts,
                    }
                )

            if rows:
                await repo.bulk_upsert(
                    rows,
                    index_elements=[
                        "bank",
                        "title",
                        "event_timestamp",
                    ],
                    update_fields=[
                        "content",
                        "speaker",
                        "tone",
                        "tone_score",
                        "policy_action",
                        "balance_sheet_direction",
                        "rate_current",
                        "rate_previous",
                        "rate_change_bps",
                        "source_url",
                        "event_type",
                    ],
                )

        dataset = CentralBankDataSet(
            rate_decisions=rate_decisions,
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

    def _empty_dataset(self) -> CentralBankDataSet:
        return CentralBankDataSet(
            rate_decisions=[],
            banks_reporting=[],
            collected_at=datetime.now(UTC),
        )
