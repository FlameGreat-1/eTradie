from __future__ import annotations

import time

from engine.config import RAGConfig
from engine.rag.constants import DocumentType
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.mandatory import MandatoryRequirements
from engine.shared.logging import get_logger
from engine.shared.metrics import RAG_RERANK_DURATION

logger = get_logger(__name__)

# Weights aligned with master_rulebook.md knowledge hierarchy.
# The LLM processes everything together so all doc types matter,
# but the master rulebook is the sole source of truth (highest weight).
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
        mandatory: MandatoryRequirements | None = None,
    ) -> list[RetrievedChunk]:
        """Rerank chunks by weighted score, never limiting below mandatory total.

        The output floor is the MAXIMUM of:
        - The configured rerank_top_k (default 25)
        - The sum of all mandatory per-doc-type minimums

        This ensures the reranker NEVER outputs fewer chunks than the
        mandatory requirements demand. The knowledge base is the LLM's
        brain and the reranker must not limit what the LLM needs.

        After the initial top-k selection, mandatory minimums are enforced
        by swapping in chunks from the overflow pool if any doc_type fell
        below its required minimum.
        """
        start = time.monotonic()

        configured_top_k = top_k or self._top_k

        # The output floor is at least the mandatory total so the reranker
        # never limits what the LLM needs.
        mandatory_total = (
            sum(mandatory.doc_type_min_chunks.values()) if mandatory else 0
        )
        effective_top_k = max(configured_top_k, mandatory_total)

        scored = [
            (chunk, self._compute_weighted_score(chunk))
            for chunk in chunks
        ]

        scored.sort(key=lambda x: x[1], reverse=True)

        # Initial selection: top-k by score (floor = mandatory total)
        selected = scored[:effective_top_k]
        overflow = scored[effective_top_k:]

        # Enforce mandatory minimums: if any doc_type is below its
        # required minimum in the selected set, pull in the best
        # chunks of that doc_type from the overflow pool.
        if mandatory and overflow:
            selected = self._enforce_mandatory_minimums(
                selected, overflow, mandatory,
            )

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
            for new_rank, (chunk, weighted_score) in enumerate(selected)
        ]

        elapsed = time.monotonic() - start
        RAG_RERANK_DURATION.labels(strategy=strategy).observe(elapsed)

        logger.info(
            "rerank_completed",
            strategy=strategy,
            input_count=len(chunks),
            output_count=len(reranked),
            configured_top_k=configured_top_k,
            mandatory_total=mandatory_total,
            effective_top_k=effective_top_k,
            elapsed_s=round(elapsed, 5),
        )

        return reranked

    @staticmethod
    def _enforce_mandatory_minimums(
        selected: list[tuple[RetrievedChunk, float]],
        overflow: list[tuple[RetrievedChunk, float]],
        mandatory: MandatoryRequirements,
    ) -> list[tuple[RetrievedChunk, float]]:
        """Ensure selected chunks satisfy mandatory per-doc-type minimums.

        For each doc_type that is below its mandatory minimum in the
        selected set, find the highest-scoring chunks of that doc_type
        in the overflow and ADD them to the selected set. This may
        increase the total beyond effective_top_k, which is correct
        because mandatory requirements take precedence over size limits.
        """
        # Count per doc_type in selected
        counts: dict[str, int] = {}
        for chunk, _ in selected:
            counts[chunk.doc_type] = counts.get(chunk.doc_type, 0) + 1

        # Identify deficits
        needed: dict[str, int] = {}
        for doc_type, min_required in mandatory.doc_type_min_chunks.items():
            current = counts.get(doc_type, 0)
            if current < min_required:
                needed[doc_type] = min_required - current

        if not needed:
            return selected

        # Collect overflow chunks grouped by doc_type (already sorted by score)
        overflow_by_type: dict[str, list[tuple[RetrievedChunk, float]]] = {}
        for item in overflow:
            dt = item[0].doc_type
            if dt in needed:
                overflow_by_type.setdefault(dt, []).append(item)

        # Add mandatory chunks from overflow directly (do NOT remove
        # existing chunks - mandatory requirements take precedence)
        to_add: list[tuple[RetrievedChunk, float]] = []
        for doc_type, deficit in needed.items():
            available = overflow_by_type.get(doc_type, [])
            to_add.extend(available[:deficit])

        if not to_add:
            return selected

        result = list(selected)
        result.extend(to_add)
        result.sort(key=lambda x: x[1], reverse=True)

        logger.debug(
            "mandatory_minimums_enforced",
            deficits=needed,
            added=len(to_add),
            total_after=len(result),
        )

        return result

    def _compute_weighted_score(self, chunk: RetrievedChunk) -> float:
        base_score = chunk.score
        doc_weight = _DOC_TYPE_WEIGHTS.get(chunk.doc_type, 1.0)

        section_bonus = 0.0
        if chunk.section:
            section_bonus = 0.02
        if chunk.subsection:
            section_bonus += 0.01

        return min(1.0, base_score * doc_weight + section_bonus)
