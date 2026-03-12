from __future__ import annotations

from engine.rag.constants import DocumentType, RetrievalStrategy
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.retriever import Retriever


class ScenarioFirstStrategy:
    def __init__(self, *, retriever: Retriever) -> None:
        self._retriever = retriever

    @property
    def name(self) -> RetrievalStrategy:
        return RetrievalStrategy.SCENARIO_FIRST

    async def execute(
        self,
        query_text: str,
        *,
        collection: str,
        scenario_collection: str,
        top_k: int,
        framework: str | None = None,
        direction: str | None = None,
        timeframe: str | None = None,
        setup_family: str | None = None,
    ) -> list[RetrievedChunk]:
        scenario_k = max(1, top_k // 2)
        scenario_chunks = await self._retriever.retrieve(
            query_text,
            collection=scenario_collection,
            top_k=scenario_k,
            frameworks=[framework] if framework else None,
            setup_families=[setup_family] if setup_family else None,
            directions=[direction] if direction else None,
            timeframes=[timeframe] if timeframe else None,
        )

        remaining_k = top_k - len(scenario_chunks)
        if remaining_k > 0:
            seen_ids = {c.chunk_id for c in scenario_chunks}
            rule_chunks = await self._retriever.retrieve(
                query_text,
                collection=collection,
                top_k=remaining_k + 5,
                doc_types=[
                    DocumentType.MASTER_RULEBOOK,
                    DocumentType.TRADING_STYLE_RULES,
                ],
                frameworks=[framework] if framework else None,
                setup_families=[setup_family] if setup_family else None,
                directions=[direction] if direction else None,
                timeframes=[timeframe] if timeframe else None,
            )
            for chunk in rule_chunks:
                if chunk.chunk_id not in seen_ids and len(scenario_chunks) < top_k:
                    scenario_chunks.append(chunk)
                    seen_ids.add(chunk.chunk_id)

        return scenario_chunks
