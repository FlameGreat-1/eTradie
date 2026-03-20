from unittest.mock import MagicMock

from engine.config import RAGConfig
from engine.rag.models import ContextBundle, RetrievedChunk
from engine.rag.orchestrator import RAGOrchestrator


def make_chunk(doc_id: str, category: str, section: str = "") -> RetrievedChunk:
    return RetrievedChunk(
        doc_id=doc_id,
        chunk_id=f"{doc_id}_c1",
        content=f"Content for {doc_id}",
        section=section,
        category=category,
        score=0.9,
    )


def test_orchestrator_compiles_bundle_from_components():
    """Test full RAG assembly pipeline."""
    config = RAGConfig(retrieval_top_k=25)
    
    mock_retriever = MagicMock()
    mock_reranker = MagicMock()
    mock_matcher = MagicMock()
    
    orch = RAGOrchestrator(
        config=config,
        retriever=mock_retriever,
        reranker=mock_reranker,
        scenario_matcher=mock_matcher
    )
    
    # Setup mock returns
    mock_retriever.retrieve.return_value = [
        make_chunk("r1", "rulebook", "rules"),
        make_chunk("m1", "macro"),
    ]
    
    mock_reranker.rerank.side_effect = lambda chunks, query, top_k: chunks
    mock_matcher.match.return_value = []
    
    bundle = orch.retrieve_context(
        pair="EURUSD",
        ta_data={"trend": "BULLISH"},
        macro_data={"bias": "BULLISH"}
    )
    
    assert isinstance(bundle, ContextBundle)
    assert bundle.strategy_used in ("RULE_FIRST", "HYBRID", "MACRO_BIAS")
    assert len(bundle.chunks) == 2
    assert bundle.chunks[0].doc_id == "r1"
    
    # Assert retriever was called
    mock_retriever.retrieve.assert_called()


def test_orchestrator_gap_filling():
    """Test orchestrator specifically fetches missing mandatory categories."""
    config = RAGConfig(retrieval_top_k=25)
    
    mock_retriever = MagicMock()
    mock_reranker = MagicMock()
    mock_matcher = MagicMock()
    
    orch = RAGOrchestrator(
        config=config,
        retriever=mock_retriever,
        reranker=mock_reranker,
        scenario_matcher=mock_matcher
    )
    
    # Initial retrieval only gets macro data, NO rules
    def mock_retrieve(query, top_k, filter_category=None):
        if filter_category == "rulebook":
            return [make_chunk("gap_r1", "rulebook", "rules")]
        return [make_chunk("m1", "macro", "")]
        
    mock_retriever.retrieve.side_effect = mock_retrieve
    mock_reranker.rerank.side_effect = lambda chunks, query, top_k: chunks
    mock_matcher.match.return_value = []
    
    bundle = orch.retrieve_context(
        pair="EURUSD",
        ta_data={"trend": "BULLISH"},
        macro_data={"bias": "BULLISH"}
    )
    
    # The orchestrator should have seen the gap in 'rulebook' and filled it
    categories = [c.category for c in bundle.chunks]
    assert "macro" in categories
    assert "rulebook" in categories
    
    # verify it actually called retrieve again with the filter
    assert mock_retriever.retrieve.call_count > 1
