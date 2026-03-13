"""Gap filler for mandatory retrieval requirements.

After the primary retrieval strategy runs, this module checks whether
the mandatory requirements are satisfied. For any doc_type that has
fewer chunks than required, it runs targeted supplemental retrievals
to fill the gaps.

This ensures the LLM always receives comprehensive knowledge coverage
regardless of which retrieval strategy was selected or how semantic
similarity scores distributed across documents.
"""

from __future__ import annotations

from engine.rag.constants import DocumentType
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.mandatory import MandatoryRequirements
from engine.rag.retrieval.retriever import Retriever
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class GapFiller:
    """Fills retrieval gaps to satisfy mandatory requirements."""

    def __init__(self, *, retriever: Retriever) -> None:
        self._retriever = retriever

    async def fill_gaps(
        self,
        existing_chunks: list[RetrievedChunk],
        requirements: MandatoryRequirements,
        *,
        query_text: str,
        doc_collection: str,
        scenario_collection: str,
        direction: str | None = None,
        timeframe: str | None = None,
        style: str | None = None,
    ) -> list[RetrievedChunk]:
        """Check existing chunks against requirements and fill any gaps.

        Returns the original chunks plus any supplemental chunks needed
        to satisfy the mandatory minimums. Deduplicates by chunk_id.
        """
        # Count chunks per doc_type in existing results
        existing_counts: dict[str, int] = {}
        existing_ids: set = set()
        for chunk in existing_chunks:
            existing_counts[chunk.doc_type] = (
                existing_counts.get(chunk.doc_type, 0) + 1
            )
            existing_ids.add(chunk.chunk_id)

        # Identify gaps: doc_types that need more chunks
        gaps: dict[str, int] = {}
        for doc_type, min_required in requirements.doc_type_min_chunks.items():
            current = existing_counts.get(doc_type, 0)
            if current < min_required:
                gaps[doc_type] = min_required - current

        if not gaps:
            logger.debug(
                "no_retrieval_gaps",
                existing_chunks=len(existing_chunks),
                doc_types_covered=len(existing_counts),
            )
            return existing_chunks

        logger.info(
            "filling_retrieval_gaps",
            gaps={dt: deficit for dt, deficit in gaps.items()},
            existing_chunks=len(existing_chunks),
        )

        supplemental: list[RetrievedChunk] = []

        for doc_type, deficit in gaps.items():
            collection = (
                scenario_collection
                if doc_type == DocumentType.CHART_SCENARIO_LIBRARY
                else doc_collection
            )

            # Retrieve extra chunks for this specific doc_type.
            # Request more than the deficit to have candidates after
            # deduplication and score filtering.
            fetch_k = deficit + 3

            # Build targeted filters based on the doc_type
            frameworks_filter = self._frameworks_for_doc_type(
                doc_type, requirements,
            )

            try:
                extra_chunks = await self._retriever.retrieve(
                    query_text,
                    collection=collection,
                    top_k=fetch_k,
                    doc_types=[doc_type],
                    frameworks=frameworks_filter,
                    directions=[direction] if direction else None,
                    timeframes=[timeframe] if timeframe else None,
                    styles=[style] if style else None,
                    score_threshold=0.10,  # Lower threshold for mandatory fills
                )
            except Exception:
                logger.warning(
                    "gap_fill_retrieval_failed",
                    doc_type=doc_type,
                    deficit=deficit,
                    exc_info=True,
                )
                continue

            added = 0
            for chunk in extra_chunks:
                if chunk.chunk_id not in existing_ids and added < deficit:
                    supplemental.append(chunk)
                    existing_ids.add(chunk.chunk_id)
                    added += 1

            logger.debug(
                "gap_filled",
                doc_type=doc_type,
                deficit=deficit,
                added=added,
                candidates=len(extra_chunks),
            )

        if supplemental:
            logger.info(
                "gap_fill_completed",
                supplemental_chunks=len(supplemental),
                total_after_fill=len(existing_chunks) + len(supplemental),
            )

        return existing_chunks + supplemental

    @staticmethod
    def _frameworks_for_doc_type(
        doc_type: str,
        requirements: MandatoryRequirements,
    ) -> list[str] | None:
        """Determine framework filter for a specific doc_type retrieval.

        For framework-specific documents, we do NOT filter by framework
        because the doc_type itself already constrains to the right
        document. Adding a framework filter would exclude chunks that
        don't have the framework metadata tag set.
        """
        # These doc types are not framework-specific
        non_framework_types = {
            DocumentType.MASTER_RULEBOOK,
            DocumentType.TRADING_STYLE_RULES,
            DocumentType.CHART_SCENARIO_LIBRARY,
        }
        if doc_type in non_framework_types:
            return None

        # For framework docs, the doc_type filter is sufficient
        return None
