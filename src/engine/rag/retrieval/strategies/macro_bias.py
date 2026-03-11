from __future__ import annotations

from engine.rag.constants import DocumentType, RetrievalStrategy
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.retriever import Retriever


class MacroBiasStrategy:
    def __init__(self, *, retriever: Retriever) -> None:
        self._retriever = retriever

    @property
    def name(self) -> RetrievalStrategy:
        return RetrievalStrategy.MACRO_BIAS

    async def execute(
        self,
        query_text: str,
        *,
        collection: str,
        top_k: int,
        style: str | None = None,
        direction: str | None = None,
    ) -> list[RetrievedChunk]:
        macro_doc_types = [
            DocumentType.MACRO_TO_PRICE_GUIDE,
            DocumentType.DXY_FRAMEWORK,
            DocumentType.COT_INTERPRETATION_GUIDE,
        ]
        macro_k = max(1, top_k * 2 // 3)
        macro_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=macro_k,
            doc_types=macro_doc_types,
            styles=[style] if style else None,
            directions=[direction] if direction else None,
        )

        remaining_k = top_k - len(macro_chunks)
        if remaining_k > 0:
            seen_ids = {c.chunk_id for c in macro_chunks}
            rule_chunks = await self._retriever.retrieve(
                query_text,
                collection=collection,
                top_k=remaining_k + 5,
                doc_types=[DocumentType.MASTER_RULEBOOK],
            )
            for chunk in rule_chunks:
                if chunk.chunk_id not in seen_ids and len(macro_chunks) < top_k:
                    macro_chunks.append(chunk)
                    seen_ids.add(chunk.chunk_id)

        return macro_chunks
