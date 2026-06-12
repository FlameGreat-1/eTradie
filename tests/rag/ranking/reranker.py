"""Tests for Reranker (doc_type weighted reranking).

Production module: src/engine/rag/retrieval/reranker.py
"""

from uuid import uuid4

import pytest

from engine.config import RAGConfig
from engine.rag.constants import DocumentType
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.reranker import Reranker


def _make_chunk(
    doc_type: str = DocumentType.MASTER_RULEBOOK,
    score: float = 0.8,
    section: str | None = None,
    subsection: str | None = None,
) -> RetrievedChunk:
    """Build a RetrievedChunk matching the real model."""
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        doc_type=doc_type,
        content="Test content",
        score=score,
        rank=0,
        section=section,
        subsection=subsection,
        metadata={},
    )


@pytest.fixture
def rag_config() -> RAGConfig:
    return RAGConfig(
        enabled=False,
        embedding_provider="openai",
        embedding_model="text-embedding-3-large",
        openai_api_key="sk-test",
        chroma_host="localhost",
        chroma_port=8000,
        retrieval_top_k=10,
        rerank_enabled=True,
        rerank_top_k=5,
        ingest_on_startup=False,
    )


@pytest.fixture
def reranker(rag_config) -> Reranker:
    return Reranker(config=rag_config)


class TestDocTypeWeighting:
    def test_master_rulebook_boosted(self, reranker):
        """MASTER_RULEBOOK chunks get a 1.5x weight boost."""
        baseline = _make_chunk(doc_type=DocumentType.CHART_SCENARIO_LIBRARY, score=0.6)
        rulebook = _make_chunk(doc_type=DocumentType.MASTER_RULEBOOK, score=0.6)

        ranked = reranker.rerank([baseline, rulebook])

        # Rulebook: 0.70 * 1.5 = 1.05 (capped to 1.0)
        # Baseline: 0.85 * 1.0 = 0.85
        assert ranked[0].doc_type == DocumentType.MASTER_RULEBOOK
        assert ranked[1].doc_type == DocumentType.CHART_SCENARIO_LIBRARY

    def test_smc_framework_boosted(self, reranker):
        """SMC_FRAMEWORK chunks get a 1.3x weight boost."""
        baseline = _make_chunk(doc_type=DocumentType.CHART_SCENARIO_LIBRARY, score=0.5)
        smc = _make_chunk(doc_type=DocumentType.SMC_FRAMEWORK, score=0.5)

        ranked = reranker.rerank([baseline, smc])

        # SMC: 0.65 * 1.3 = 0.845
        # Baseline: 0.80 * 1.0 = 0.80
        assert ranked[0].doc_type == DocumentType.SMC_FRAMEWORK


class TestTruncation:
    def test_output_capped_to_top_k(self, reranker):
        """Output is capped to rerank_top_k."""
        chunks = [_make_chunk(score=0.9 - i * 0.05) for i in range(10)]
        ranked = reranker.rerank(chunks, top_k=3)
        assert len(ranked) == 3

    def test_preserves_score_ordering(self, reranker):
        """Output is sorted by weighted score descending."""
        chunks = [
            _make_chunk(score=0.5),
            _make_chunk(score=0.9),
            _make_chunk(score=0.7),
        ]
        ranked = reranker.rerank(chunks)
        scores = [c.score for c in ranked]
        assert scores == sorted(scores, reverse=True)


class TestSectionBonus:
    def test_section_adds_bonus(self, reranker):
        """Chunks with section metadata get a small score bonus."""
        no_section = _make_chunk(doc_type=DocumentType.CHART_SCENARIO_LIBRARY, score=0.80)
        with_section = _make_chunk(
            doc_type=DocumentType.CHART_SCENARIO_LIBRARY,
            score=0.80,
            section="rules",
            subsection="entry",
        )

        ranked = reranker.rerank([no_section, with_section])

        # with_section gets +0.02 (section) + 0.01 (subsection) = 0.83
        # no_section stays at 0.80
        assert ranked[0].section == "rules"


class TestRankAssignment:
    def test_ranks_are_sequential(self, reranker):
        """Reranked chunks have sequential rank values starting from 0."""
        chunks = [_make_chunk(score=0.9 - i * 0.1) for i in range(5)]
        ranked = reranker.rerank(chunks)
        ranks = [c.rank for c in ranked]
        assert ranks == list(range(len(ranked)))
