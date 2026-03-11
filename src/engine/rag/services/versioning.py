from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from engine.rag.storage.repositories.document import DocumentRepository
from engine.rag.storage.repositories.document_version import DocumentVersionRepository
from engine.rag.storage.repositories.reembed_queue import ReembedQueueRepository
from engine.shared.exceptions import RAGVersioningError
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class VersioningService:
    def __init__(
        self,
        *,
        document_repo: DocumentRepository,
        version_repo: DocumentVersionRepository,
        reembed_repo: ReembedQueueRepository,
    ) -> None:
        self._document_repo = document_repo
        self._version_repo = version_repo
        self._reembed_repo = reembed_repo

    async def activate_version(
        self, document_id: UUID, version_id: UUID,
    ) -> None:
        current_active = await self._version_repo.get_active(document_id)

        if current_active and current_active.id != version_id:
            await self._version_repo.supersede(
                current_active.id, superseded_by=version_id,
            )
            logger.info(
                "version_superseded",
                document_id=str(document_id),
                old_version=str(current_active.id),
                new_version=str(version_id),
            )

        await self._version_repo.activate(version_id)
        await self._document_repo.set_active_version(document_id, version_id)

        await self._reembed_repo.enqueue(
            document_id=document_id,
            document_version_id=version_id,
            reason="version_activated",
        )

        logger.info(
            "version_activated",
            document_id=str(document_id),
            version_id=str(version_id),
        )

    async def get_active_version_id(
        self, document_id: UUID,
    ) -> UUID | None:
        active = await self._version_repo.get_active(document_id)
        return active.id if active else None
