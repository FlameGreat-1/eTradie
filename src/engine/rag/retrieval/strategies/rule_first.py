from __future__ import annotations

from engine.rag.constants import DocumentType, RetrievalStrategy
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.retriever import Retriever


class RuleFirstStrategy:
    """Rule-prioritised retrieval for high-impact event scenarios.

    Allocates the majority of budget to rulebook chunks (rejection rules,
    risk rules, event rules) then fills remaining budget with framework
    and macro knowledge.
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

        # Primary: Rules (master_rulebook + trading_style_rules)
        rule_k = max(3, top_k // 2)
        rule_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=rule_k,
            doc_types=[
                DocumentType.MASTER_RULEBOOK,
                DocumentType.TRADING_STYLE_RULES,
            ],
            frameworks=[framework] if framework else None,
            setup_families=all_setup_families or ([setup_family] if setup_family else None),
            directions=[direction] if direction else None,
            timeframes=[timeframe] if timeframe else None,
            styles=[style] if style else None,
        )
        for chunk in rule_chunks:
            if chunk.chunk_id not in seen_ids:
                merged.append(chunk)
                seen_ids.add(chunk.chunk_id)

        # Secondary: Macro docs (critical during high-impact events)
        macro_k = max(2, top_k // 4)
        macro_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=macro_k + 2,
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

        # Tertiary: Framework-specific docs for each detected framework
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

        per_fw_k = max(2, top_k // (len(frameworks_to_retrieve) + 4)) if frameworks_to_retrieve else 0
        for fw in frameworks_to_retrieve:
            doc_type = framework_doc_map[fw]
            fw_chunks = await self._retriever.retrieve(
                query_text,
                collection=collection,
                top_k=per_fw_k + 1,
                doc_types=[doc_type],
                setup_families=all_setup_families or ([setup_family] if setup_family else None),
                directions=[direction] if direction else None,
                timeframes=[timeframe] if timeframe else None,
            )
            for chunk in fw_chunks:
                if chunk.chunk_id not in seen_ids:
                    merged.append(chunk)
                    seen_ids.add(chunk.chunk_id)

        merged.sort(key=lambda c: c.score, reverse=True)
        return merged
