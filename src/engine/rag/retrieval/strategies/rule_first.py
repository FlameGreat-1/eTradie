from __future__ import annotations

from engine.rag.constants import DocumentType, RetrievalStrategy
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.retriever import Retriever


class RuleFirstStrategy:
    def __init__(self, *, retriever: Retriever) -> None:
        self._retriever = retriever

    @property
    def name(self) -> RetrievalStrategy:
        return RetrievalStrategy.RULE_FIRST

    async def execute(
        self,
        query_text: str,
        *,
        collection: str,
        top_k: int,
        framework: str | None = None,
        direction: str | None = None,
        timeframe: str | None = None,
        style: str | None = None,
        setup_family: str | None = None,
    ) -> list[RetrievedChunk]:
        rule_doc_types = [
            DocumentType.MASTER_RULEBOOK,
            DocumentType.TRADING_STYLE_RULES,
        ]
        rule_k = max(1, top_k * 2 // 3)
        rule_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=rule_k,
            doc_types=rule_doc_types,
            frameworks=[framework] if framework else None,
            setup_families=[setup_family] if setup_family else None,
            directions=[direction] if direction else None,
            timeframes=[timeframe] if timeframe else None,
            styles=[style] if style else None,
        )

        remaining_k = top_k - len(rule_chunks)
        if remaining_k > 0:
            seen_ids = {c.chunk_id for c in rule_chunks}
            supplemental = await self._retriever.retrieve(
                query_text,
                collection=collection,
                top_k=remaining_k + 5,
                frameworks=[framework] if framework else None,
                setup_families=[setup_family] if setup_family else None,
                directions=[direction] if direction else None,
                timeframes=[timeframe] if timeframe else None,
            )
            for chunk in supplemental:
                if chunk.chunk_id not in seen_ids and len(rule_chunks) < top_k:
                    rule_chunks.append(chunk)
                    seen_ids.add(chunk.chunk_id)

        return rule_chunks
