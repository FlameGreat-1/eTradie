from __future__ import annotations

from engine.rag.constants import DocumentType, RetrievalStrategy
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.retriever import Retriever


class HybridStrategy:
    """Equal-weight multi-bucket retrieval for comprehensive knowledge coverage.

    The LLM processes TA + Macro + RAG knowledge ALL TOGETHER in a single
    pass. It does not analyze TA separately from macro. Therefore every
    knowledge category receives EQUAL retrieval budget.

    Retrieves from all categories with equal weight:
    1. Core rules (master_rulebook, trading_style_rules)
    2. Framework-specific chunks for EACH detected framework
    3. Macro/cross-framework chunks (macro_to_price, dxy, cot)
    4. Scenario examples (chart_scenario_library)
    """

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
        all_frameworks: list[str] | None = None,
        all_setup_families: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        # Equal budget per category - no prioritization
        per_category_k = max(3, top_k // 4)

        seen_ids: set = set()
        merged: list[RetrievedChunk] = []

        # Category 1: Core rules (master_rulebook + trading_style_rules)
        rule_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=per_category_k + 2,
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

        # Category 2: Framework-specific chunks for EACH detected framework
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
        # Always include wyckoff for phase context
        frameworks_to_retrieve.add("wyckoff")

        per_fw_k = max(2, per_category_k // max(1, len(frameworks_to_retrieve)))
        all_setup_fams = all_setup_families or (
            [setup_family] if setup_family else None
        )

        for fw in frameworks_to_retrieve:
            doc_type = framework_doc_map[fw]
            fw_chunks = await self._retriever.retrieve(
                query_text,
                collection=collection,
                top_k=per_fw_k + 2,
                doc_types=[doc_type],
                setup_families=all_setup_fams,
                directions=[direction] if direction else None,
                timeframes=[timeframe] if timeframe else None,
            )
            for chunk in fw_chunks:
                if chunk.chunk_id not in seen_ids:
                    merged.append(chunk)
                    seen_ids.add(chunk.chunk_id)

        # Category 3: Macro/cross-framework (DXY, COT, macro-to-price)
        macro_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=per_category_k + 2,
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

        # Category 4: Scenario examples
        scenario_chunks = await self._retriever.retrieve(
            query_text,
            collection=scenario_collection,
            top_k=per_category_k + 2,
            frameworks=[framework] if framework else None,
            setup_families=all_setup_fams,
            directions=[direction] if direction else None,
            timeframes=[timeframe] if timeframe else None,
        )
        for chunk in scenario_chunks:
            if chunk.chunk_id not in seen_ids:
                merged.append(chunk)
                seen_ids.add(chunk.chunk_id)

        merged.sort(key=lambda c: c.score, reverse=True)
        return merged
