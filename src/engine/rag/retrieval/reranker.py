from __future__ import annotations

import time

from engine.config import RAGConfig
from engine.rag.constants import DocumentType
from engine.rag.models.retrieval import RetrievedChunk
from engine.shared.logging import get_logger
from engine.shared.metrics import RAG_RERANK_DURATION

logger = get_logger(__name__)

# Weights aligned with master_rulebook.md knowledge hierarchy:
# - MASTER_RULEBOOK is the sole source of truth (highest)
# - SMC/SND are primary entry frameworks
# - MACRO is MANDATORY per Section 4 confluence requirements
# - DXY is MANDATORY for all USD pairs per Section 2.2
# - SCENARIOS are critical reasoning examples per ALIGNMENT.md
# - COT is PREFERRED confluence factor
# - WYCKOFF is contextual confirmation (not primary)
# - STYLE rules are operational (always relevant but not directional)
_DOC_TYPE_WEIGHTS: dict[str, float] = {
    DocumentType.MASTER_RULEBOOK: 1.5,
    DocumentType.SMC_FRAMEWORK: 1.3,
    DocumentType.SND_RULEBOOK: 1.3,
    DocumentType.MACRO_TO_PRICE_GUIDE: 1.25,
    DocumentType.DXY_FRAMEWORK: 1.2,
    DocumentType.CHART_SCENARIO_LIBRARY: 1.2,
    DocumentType.COT_INTERPRETATION_GUIDE: 1.15,
    DocumentType.WYCKOFF_GUIDE: 1.1,
    DocumentType.TRADING_STYLE_RULES: 1.1,
}


class Reranker:
    def __init__(self, *, config: RAGConfig) -> None:
        self._config = config
        self._top_k = config.rerank_top_k

    def rerank(
        self,
        chunks: list[RetrievedChunk],
        *,
        strategy: str = "rule_weighted",
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:

        start = time.monotonic()

        effective_top_k = top_k or self._top_k

        scored = [
            (chunk, self._compute_weighted_score(chunk))
            for chunk in chunks
        ]

        scored.sort(key=lambda x: x[1], reverse=True)

        reranked = [
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                doc_type=chunk.doc_type,
                content=chunk.content,
                score=weighted_score,
                rank=new_rank,
                section=chunk.section,
                subsection=chunk.subsection,
                metadata=chunk.metadata,
            )
            for new_rank, (chunk, weighted_score) in enumerate(scored[:effective_top_k])
        ]

        elapsed = time.monotonic() - start
        RAG_RERANK_DURATION.labels(strategy=strategy).observe(elapsed)

        logger.info(
            "rerank_completed",
            strategy=strategy,
            input_count=len(chunks),
            output_count=len(reranked),
            elapsed_s=round(elapsed, 5),
        )

        return reranked

    def _compute_weighted_score(self, chunk: RetrievedChunk) -> float:
        base_score = chunk.score
        doc_weight = _DOC_TYPE_WEIGHTS.get(chunk.doc_type, 1.0)

        section_bonus = 0.0
        if chunk.section:
            section_bonus = 0.02
        if chunk.subsection:
            section_bonus += 0.01

        return min(1.0, base_score * doc_weight + section_bonus)
