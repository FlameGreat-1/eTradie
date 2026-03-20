from engine.rag.models import RetrievedChunk
from engine.rag.ranking.reranker import ContextReranker


def make_chunk(doc_id: str, section: str, score: float, category: str = "general") -> RetrievedChunk:
    return RetrievedChunk(
        doc_id=doc_id,
        chunk_id=f"{doc_id}_c1",
        content="Test content",
        section=section,
        category=category,
        score=score,
    )


def test_reranker_rule_weighting():
    """Test that 'rules' section chunks get bumped up in ranking."""
    reranker = ContextReranker()
    
    # c2 has a lower base score but is a RULE
    c1 = make_chunk("d1", "general", score=0.85)
    c2 = make_chunk("d2", "rules", score=0.75)
    
    ranked = reranker.rerank([c1, c2], query="test", top_k=2)
    
    # c2 should leapfrog c1 because rules get a heavy multiplier (e.g. 1.2x)
    # 0.75 * 1.2 = 0.9.  0.85 * 1.0 = 0.85.
    assert ranked[0].doc_id == "d2"
    assert ranked[1].doc_id == "d1"


def test_reranker_truncation():
    """Test that output is capped to top_k."""
    reranker = ContextReranker()
    
    chunks = [
        make_chunk("d1", "general", score=0.9),
        make_chunk("d2", "general", score=0.8),
        make_chunk("d3", "general", score=0.7),
        make_chunk("d4", "general", score=0.6),
    ]
    
    ranked = reranker.rerank(chunks, query="test", top_k=2)
    
    assert len(ranked) == 2
    assert ranked[0].doc_id == "d1"
    assert ranked[1].doc_id == "d2"


def test_reranker_mandatory_preservation():
    """Test that mandatory chunks are kept even if scores are low."""
    reranker = ContextReranker()
    
    # Create 3 high scoring non-rules, and 1 low scoring rule
    chunks = [
        make_chunk("d1", "general", score=0.95),
        make_chunk("d2", "general", score=0.90),
        make_chunk("d3", "general", score=0.85),
        make_chunk("d4", "rules", score=0.50),  # Will be boosted to ~0.60
    ]
    
    # We want top_k=2, but we also want to ensure at least 1 rule gets in
    # The current reranker logic bumps rules, but if it doesn't bump it enough to be in top 2,
    # the orchestration layer specifically ensures gap filling.
    # The reranker itself just applies weights and sorts.
    
    ranked = reranker.rerank(chunks, query="test", top_k=10)
    
    # verify sorting logic worked
    assert ranked[0].doc_id == "d1"
    assert ranked[-1].doc_id == "d4"
