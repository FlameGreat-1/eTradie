from __future__ import annotations

from engine.rag.models.scenario import Scenario
from engine.rag.storage.uow import RAGUnitOfWorkFactory
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class ScenarioMatcher:
    def __init__(self, *, uow_factory: RAGUnitOfWorkFactory) -> None:
        self._uow = uow_factory

    async def match(
        self,
        *,
        framework: str | None = None,
        setup_family: str | None = None,
        direction: str | None = None,
        timeframe: str | None = None,
        outcome: str | None = None,
        limit: int = 5,
    ) -> list[Scenario]:
        async with self._uow() as uow:
            rows = await uow.scenario_repo.match(
                framework=framework,
                setup_family=setup_family,
                direction=direction,
                timeframe=timeframe,
                outcome=outcome,
                limit=limit,
            )

        scenarios: list[Scenario] = []
        for row in rows:
            scenarios.append(Scenario(
                id=row.id,
                document_id=row.document_id,
                framework=row.framework,
                setup_family=row.setup_family,
                direction=row.direction,
                timeframe=row.timeframe,
                outcome=row.outcome,
                title=row.title,
                explanation_text=row.explanation_text,
                image_refs=tuple(row.image_refs) if isinstance(row.image_refs, list) else (),
                confluence_tags=frozenset(row.confluence_tags) if isinstance(row.confluence_tags, list) else frozenset(),
                style_tags=frozenset(row.style_tags) if isinstance(row.style_tags, list) else frozenset(),
                linked_chunk_ids=tuple(),
                metadata=row.metadata if isinstance(row.metadata, dict) else {},
                is_active=row.is_active,
                notes=row.notes,
            ))

        logger.info(
            "scenario_match",
            framework=framework,
            setup_family=setup_family,
            direction=direction,
            matched=len(scenarios),
        )

        return scenarios
