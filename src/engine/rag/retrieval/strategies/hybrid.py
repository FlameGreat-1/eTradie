from __future__ import annotations

from engine.rag.constants import DocumentType, RetrievalStrategy
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.retriever import Retriever


class HybridStrategy:
    def __init__(self, *, retriever: Retriever) -> None:
        self._retriever = retriever

    @property
    def name(self) -> RetrievalStrategy:
        return RetrievalStrategy.HYBRID

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
        style: str | None = None,
        setup_family: str | None = None,
    ) -> list[RetrievedChunk]:
        rule_k = max(1, top_k // 3)
        framework_k = max(1, top_k // 3)
        scenario_k = max(1, top_k - rule_k - framework_k)

        rule_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=rule_k + 3,
            doc_types=[
                DocumentType.MASTER_RULEBOOK,
                DocumentType.TRADING_STYLE_RULES,
            ],
            styles=[style] if style else None,
        )

        framework_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=framework_k + 3,
            frameworks=[framework] if framework else None,
            setup_families=[setup_family] if setup_family else None,
            directions=[direction] if direction else None,
            timeframes=[timeframe] if timeframe else None,
        )

        scenario_chunks = await self._retriever.retrieve(
            query_text,
            collection=scenario_collection,
            top_k=scenario_k + 3,
            frameworks=[framework] if framework else None,
            setup_families=[setup_family] if setup_family else None,
            directions=[direction] if direction else None,
            timeframes=[timeframe] if timeframe else None,
        )

        seen_ids: set = set()
        merged: list[RetrievedChunk] = []

        for source in [rule_chunks, framework_chunks, scenario_chunks]:
            for chunk in source:
                if chunk.chunk_id not in seen_ids:
                    merged.append(chunk)
                    seen_ids.add(chunk.chunk_id)

        merged.sort(key=lambda c: c.score, reverse=True)
        return merged[:top_k]
