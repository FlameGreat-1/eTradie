from __future__ import annotations

from engine.rag.constants import DocumentType, RetrievalStrategy
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.retriever import Retriever


class MacroBiasStrategy:
    """Macro-boosted retrieval for strong macro signal scenarios.

    The LLM processes everything together. This strategy gives macro docs
    a slight budget boost because strong macro signals need thorough
    macro-to-price translation rules. All other categories still receive
    substantial equal budgets.
    """

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
        all_frameworks: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        seen_ids: set = set()
        merged: list[RetrievedChunk] = []

        # Equal base budget per category, macro gets a slight boost
        base_k = max(3, top_k // 4)
        macro_k = base_k + 3

        # Macro docs
        macro_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=macro_k,
            doc_types=[
                DocumentType.MACRO_TO_PRICE_GUIDE,
                DocumentType.DXY_FRAMEWORK,
                DocumentType.COT_INTERPRETATION_GUIDE,
            ],
            styles=[style] if style else None,
            directions=[direction] if direction else None,
        )
        for chunk in macro_chunks:
            if chunk.chunk_id not in seen_ids:
                merged.append(chunk)
                seen_ids.add(chunk.chunk_id)

        # Rules
        rule_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=base_k + 2,
            doc_types=[
                DocumentType.MASTER_RULEBOOK,
                DocumentType.TRADING_STYLE_RULES,
            ],
        )
        for chunk in rule_chunks:
            if chunk.chunk_id not in seen_ids:
                merged.append(chunk)
                seen_ids.add(chunk.chunk_id)

        # Framework-specific docs for detected frameworks
        framework_doc_map = {
            "smc": DocumentType.SMC_FRAMEWORK,
            "snd": DocumentType.SND_RULEBOOK,
            "wyckoff": DocumentType.WYCKOFF_GUIDE,
        }
        frameworks_to_retrieve = set()
        if all_frameworks:
            for fw in all_frameworks:
                if fw in framework_doc_map:
                    frameworks_to_retrieve.add(fw)
        frameworks_to_retrieve.add("wyckoff")

        per_fw_k = max(2, base_k // max(1, len(frameworks_to_retrieve)))
        for fw in frameworks_to_retrieve:
            doc_type = framework_doc_map[fw]
            fw_chunks = await self._retriever.retrieve(
                query_text,
                collection=collection,
                top_k=per_fw_k + 1,
                doc_types=[doc_type],
                directions=[direction] if direction else None,
            )
            for chunk in fw_chunks:
                if chunk.chunk_id not in seen_ids:
                    merged.append(chunk)
                    seen_ids.add(chunk.chunk_id)

        merged.sort(key=lambda c: c.score, reverse=True)
        return merged
