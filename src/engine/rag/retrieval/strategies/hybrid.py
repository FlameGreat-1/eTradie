from __future__ import annotations

from engine.rag.constants import DocumentType, RetrievalStrategy
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.retriever import Retriever


class HybridStrategy:
    """Four-bucket retrieval strategy aligned with ALIGNMENT.md architecture.

    Retrieves from 4 categories simultaneously:
    1. Core rules (master_rulebook, trading_style_rules)
    2. Framework-specific chunks (smc, snd, wyckoff based on TA output)
    3. Macro/cross-framework chunks (macro_to_price, dxy, cot)
    4. Scenario examples (chart_scenario_library)

    This ensures the LLM always receives all four knowledge layers
    needed for correct reasoning per ALIGNMENT.md Section 4.
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
    ) -> list[RetrievedChunk]:
        # Allocate budget across 4 buckets
        rule_k = max(1, top_k // 4)
        framework_k = max(1, top_k // 4)
        macro_k = max(1, top_k // 4)
        scenario_k = max(1, top_k - rule_k - framework_k - macro_k)

        # Bucket 1: Core rules (master_rulebook + trading_style_rules)
        rule_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=rule_k + 2,
            doc_types=[
                DocumentType.MASTER_RULEBOOK,
                DocumentType.TRADING_STYLE_RULES,
            ],
            styles=[style] if style else None,
        )

        # Bucket 2: Framework-specific (SMC, SnD, Wyckoff based on TA output)
        framework_chunks = await self._retriever.retrieve(
            query_text,
            collection=collection,
            top_k=framework_k + 2,
            doc_types=[
                DocumentType.SMC_FRAMEWORK,
                DocumentType.SND_RULEBOOK,
                DocumentType.WYCKOFF_GUIDE,
            ],
            frameworks=[framework] if framework else None,
            setup_families=[setup_family] if setup_family else None,
            directions=[direction] if direction else None,
            timeframes=[timeframe] if timeframe else None,
        )

        # Bucket 3: Macro/cross-framework (DXY, COT, macro-to-price)
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

        # Bucket 4: Scenario examples
        scenario_chunks = await self._retriever.retrieve(
            query_text,
            collection=scenario_collection,
            top_k=scenario_k + 2,
            frameworks=[framework] if framework else None,
            setup_families=[setup_family] if setup_family else None,
            directions=[direction] if direction else None,
            timeframes=[timeframe] if timeframe else None,
        )

        # Merge with deduplication, preserving bucket priority order
        seen_ids: set = set()
        merged: list[RetrievedChunk] = []

        for source in [rule_chunks, framework_chunks, macro_chunks, scenario_chunks]:
            for chunk in source:
                if chunk.chunk_id not in seen_ids:
                    merged.append(chunk)
                    seen_ids.add(chunk.chunk_id)

        merged.sort(key=lambda c: c.score, reverse=True)
        return merged[:top_k]
