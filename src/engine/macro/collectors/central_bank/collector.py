from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.cache import RedisCache
from engine.shared.db import DatabaseManager
from engine.shared.logging import get_logger
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.central_bank import CentralBankDataSet
from engine.macro.providers.base import BaseProvider
from engine.macro.storage.schemas.central_bank import CentralBankEventRow

logger = get_logger(__name__)


class CentralBankCollector(BaseCollector):
    collector_name = "central_bank"
    cache_namespace = "cb"

    async def _do_collect(self) -> CentralBankDataSet:
        all_events = []
        banks_reporting = []

        for provider in self._providers:
            try:
                events = await provider.fetch()
                all_events.extend(events)
                bank = getattr(provider, "bank", None)
                if bank and bank not in banks_reporting:
                    banks_reporting.append(bank)
            except Exception:
                logger.warning("cb_provider_skipped", provider=provider.provider_name)

        async with self._db.session() as session:
            for event in all_events:
                row = CentralBankEventRow(
                    bank=event.bank.value if hasattr(event, "bank") else "",
                    event_type=event.event_type.value if hasattr(event, "event_type") else "CB_SPEECH",
                    title=getattr(event, "title", ""),
                    content=getattr(event, "summary", ""),
                    speaker=getattr(event, "speaker", ""),
                    tone=event.tone.value if hasattr(event, "tone") else "NEUTRAL",
                    source_url=getattr(event, "source_url", ""),
                    event_timestamp=getattr(event, "speech_date", None)
                        or getattr(event, "guidance_date", None)
                        or datetime.now(UTC),
                )
                session.add(row)

        dataset = CentralBankDataSet(
            speeches=[e for e in all_events if hasattr(e, "speech_date")],
            forward_guidance=[e for e in all_events if hasattr(e, "guidance_date")],
            banks_reporting=banks_reporting,
            collected_at=datetime.now(UTC),
        )

        await self._cache.set(
            self.cache_namespace, "latest",
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(all_events))
        return dataset
