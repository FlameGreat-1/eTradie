from __future__ import annotations

from uuid import UUID

from engine.rag.storage.repositories.scenario import ScenarioRepository
from engine.rag.storage.schemas.scenario import ScenarioRow
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class ScenarioIndexer:
    def __init__(self, *, scenario_repo: ScenarioRepository) -> None:
        self._repo = scenario_repo

    async def index_scenario(
        self,
        *,
        document_id: UUID,
        framework: str,
        setup_family: str,
        direction: str,
        timeframe: str,
        outcome: str,
        title: str,
        explanation_text: str,
        image_refs: list[str] | None = None,
        confluence_tags: list[str] | None = None,
        style_tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ScenarioRow:
        row = ScenarioRow(
            document_id=document_id,
            framework=framework,
            setup_family=setup_family,
            direction=direction,
            timeframe=timeframe,
            outcome=outcome,
            title=title,
            explanation_text=explanation_text,
            image_refs=image_refs or [],
            confluence_tags=confluence_tags or [],
            style_tags=style_tags or [],
            linked_chunk_ids=[],
            metadata=metadata or {},
            is_active=True,
        )
        created = await self._repo.create(row)

        logger.info(
            "scenario_indexed",
            scenario_id=str(created.id),
            framework=framework,
            setup_family=setup_family,
            direction=direction,
        )

        return created

    async def deactivate_for_document(
        self, document_id: UUID,
    ) -> int:
        count = await self._repo.deactivate_by_document(document_id)
        logger.info(
            "scenarios_deactivated",
            document_id=str(document_id),
            count=count,
        )
        return count

    async def get_active_count(self) -> int:
        active = await self._repo.get_active()
        return len(active)
