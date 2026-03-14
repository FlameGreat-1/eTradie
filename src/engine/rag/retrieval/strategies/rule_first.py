from __future__ import annotations

from engine.rag.constants import DocumentType, RetrievalStrategy
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.retriever import Retriever


class RuleFirstStrategy:
    """Rule-boosted retrieval for high-impact event scenarios.

    The LLM processes everything together. This strategy gives rules a
    slight budget boost (not exclusive priority) because high-impact
    events make rejection rules especially critical. All other categories
    still receive substantial equal budgets.
    """

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
        all_frameworks: list[str] | None = None,
        all_setup_families: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        seen_ids: set = set()
        merged: list[RetrievedChunk] = []

        # Equal base budget per category, rules get a slight boost
        base_k = max(3, top_k // 4)
        rule_k = base_k + 3  # Slight boost for rules during high-impact events

        # Rules (master_rulebook + trading_style_rules)
        rule_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=rule_k,
            doc_types=[
                DocumentType.MASTER_RULEBOOK,
                DocumentType.TRADING_STYLE_RULES,
            ],
            styles=[style] if style else None,
        )
        for chunk in rule_chunks:
            if chunk.chunk_id not in seen_ids:
                merged.append(chunk)
                seen_ids.add(chunk.chunk_id)

        # Macro docs (equally important - LLM processes everything together)
        macro_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=base_k + 2,
            doc_types=[
                DocumentType.MACRO_TO_PRICE_GUIDE,
                DocumentType.DXY_FRAMEWORK,
                DocumentType.COT_INTERPRETATION_GUIDE,
            ],
            directions=[direction] if direction else None,
        )
        for chunk in macro_chunks:
            if chunk.chunk_id not in seen_ids:
                merged.append(chunk)
                seen_ids.add(chunk.chunk_id)

        # Framework-specific docs for each detected framework
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
        if framework and framework in framework_doc_map:
            frameworks_to_retrieve.add(framework)
        frameworks_to_retrieve.add("wyckoff")

        per_fw_k = max(2, base_k // max(1, len(frameworks_to_retrieve)))
        all_setup_fams = all_setup_families or ([setup_family] if setup_family else None)
        for fw in frameworks_to_retrieve:
            doc_type = framework_doc_map[fw]
            fw_chunks = await self._retriever.retrieve(
                query_text,
                collection=collection,
                top_k=per_fw_k + 1,
                doc_types=[doc_type],
                setup_families=all_setup_fams,
                directions=[direction] if direction else None,
                timeframes=[timeframe] if timeframe else None,
            )
            for chunk in fw_chunks:
                if chunk.chunk_id not in seen_ids:
                    merged.append(chunk)
                    seen_ids.add(chunk.chunk_id)

        merged.sort(key=lambda c: c.score, reverse=True)
        return merged
