from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.macro.storage.schemas.snapshot import MacroSnapshotRow


class MacroSnapshotRepository(BaseRepository[MacroSnapshotRow]):
    """Durable last-good snapshot of each macro collector's dataset.

    One row per collector namespace. The scheduler writer upserts the
    collector's final ``model_dump(mode="json")`` after every successful
    collection; the analysis reader reads it back on a Redis cache miss
    so the macro section is always served from the last good enriched
    value (never empty) without any external API call.
    """

    model = MacroSnapshotRow
    _repo_name = "macro_snapshot"

    async def get_payload(self, namespace: str) -> dict[str, Any] | None:
        """Return the last persisted dataset JSON for a namespace, or None."""
        stmt = (
            select(self.model.payload)
            .where(self.model.namespace == namespace)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row if isinstance(row, dict) else None

    async def upsert_payload(
        self,
        namespace: str,
        payload: dict[str, Any],
        collected_at: datetime,
    ) -> None:
        """Persist the latest dataset JSON for a namespace (idempotent).

        Deduplicates on the unique(namespace) constraint, so there is
        exactly one live row per collector and the table stays tiny.
        """
        await self.bulk_upsert(
            [
                {
                    "namespace": namespace,
                    "payload": payload,
                    "collected_at": collected_at,
                    "updated_at": datetime.now(collected_at.tzinfo),
                }
            ],
            index_elements=["namespace"],
            update_fields=["payload", "collected_at", "updated_at"],
        )
