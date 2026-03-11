from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from engine.rag.storage.uow import RAGUnitOfWorkFactory
from engine.shared.exceptions import RAGVersioningError
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class VersioningService:
    def __init__(
        self,
        *,
        uow_factory: RAGUnitOfWorkFactory,
    ) -> None:
        self._uow = uow_factory

    async def activate_version(
        self, document_id: UUID, version_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            current_active = await uow.version_repo.get_active(document_id)

            if current_active and current_active.id != version_id:
                await uow.version_repo.supersede(
                    current_active.id, superseded_by=version_id,
                )
                logger.info(
                    "version_superseded",
                    document_id=str(document_id),
                    old_version=str(current_active.id),
                    new_version=str(version_id),
                )

            await uow.version_repo.activate(version_id)
            await uow.document_repo.set_active_version(document_id, version_id)

            await uow.reembed_queue_repo.enqueue(
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
        async with self._uow() as uow:
            active = await uow.version_repo.get_active(document_id)
            return active.id if active else None
