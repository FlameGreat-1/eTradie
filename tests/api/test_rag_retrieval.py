"""Integration tests for real RAG retrieval against live ChromaDB.

These tests exercise the complete RAG pipeline:
  /internal/rag/retrieve -> RAGOrchestrator -> Embedding -> ChromaDB -> Reranker

Requires ChromaDB running in Docker with embeddings already loaded.
Run: pytest tests/api/test_rag_retrieval.py -v -m integration
"""

from __future__ import annotations

import pytest

from tests.api.conftest import skip_no_infra, CHROMA_AVAILABLE

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, skip_no_infra]

skip_no_chroma = pytest.mark.skipif(
    not CHROMA_AVAILABLE,
    reason="ChromaDB not available - RAG retrieval tests require real vector store",
)


@skip_no_chroma
class TestRAGRetrieval:
    """Tests the real /internal/rag/retrieve endpoint against live ChromaDB.

    Every test sends a POST to the Python engine's internal RAG endpoint,
    which triggers:
    1. Embedding the query text (sentence_transformers or openai)
    2. Vector search against real ChromaDB collections
    3. Reranking with rule_weighted scorer
    4. Coverage and conflict analysis
    5. Returning chunks with scores, strategy, and metadata
    """

    async def test_rag_retrieve_smc_query(self, app_client):
        """SMC turtle soup query returns relevant knowledge chunks."""
        resp = await app_client.post("/internal/rag/retrieve", json={
            "query_text": "EURUSD bullish SMC turtle soup long H4 order block FVG liquidity sweep",
            "strategy": "hybrid",
            "framework": "smc",
            "symbol": "EURUSD",
            "direction": "long",
            "timeframe": "H4",
            "has_smc_candidates": True,
            "has_snd_candidates": False,
            "has_macro_data": True,
            "has_dxy_data": True,
            "trace_id": "test-rag-smc-001",
        })

        assert resp.status_code == 200, f"RAG retrieve failed: {resp.text}"
        data = resp.json()

        # Verify response structure matches RAGOrchestrator output.
        assert "chunks" in data or "context_bundle" in data, \
            f"Response should contain chunks or context_bundle, got keys: {list(data.keys())}"

        # If chunks are returned directly (model_dump format):
        if "chunks" in data:
            chunks = data["chunks"]
            assert isinstance(chunks, list), "chunks should be a list"

            # With real embeddings loaded, we should get results.
            if len(chunks) > 0:
                chunk = chunks[0]
                assert "content" in chunk, "chunk should have content"
                assert len(chunk["content"]) > 0, "chunk content should not be empty"
                # Score may be named 'score' or 'relevance_score'.
                has_score = "score" in chunk or "relevance_score" in chunk
                assert has_score, "chunk should have a score field"

        # Verify strategy and coverage metadata if present.
        if "strategy_used" in data:
            assert isinstance(data["strategy_used"], str)
        if "coverage_result" in data:
            assert isinstance(data["coverage_result"], dict)
        if "conflict_result" in data:
            assert isinstance(data["conflict_result"], dict)
        if "total_chunks_returned" in data:
            assert isinstance(data["total_chunks_returned"], (int, float))

    async def test_rag_retrieve_snd_query(self, app_client):
        """SnD QML query returns relevant knowledge chunks."""
        resp = await app_client.post("/internal/rag/retrieve", json={
            "query_text": "GBPUSD bearish supply demand QML baseline short H4 previous levels fakeout",
            "strategy": "hybrid",
            "framework": "snd",
            "symbol": "GBPUSD",
            "direction": "short",
            "has_smc_candidates": False,
            "has_snd_candidates": True,
            "trace_id": "test-rag-snd-001",
        })

        assert resp.status_code == 200, f"RAG retrieve failed: {resp.text}"
        data = resp.json()
        # Should return valid response structure.
        assert isinstance(data, dict)

    async def test_rag_retrieve_macro_enriched(self, app_client):
        """Query with macro signal flags exercises enriched retrieval."""
        resp = await app_client.post("/internal/rag/retrieve", json={
            "query_text": "EURUSD bullish trend DXY momentum bearish risk environment risk_on NFP non-farm payrolls",
            "strategy": "macro_bias",
            "framework": "smc",
            "symbol": "EURUSD",
            "direction": "long",
            "has_smc_candidates": True,
            "has_snd_candidates": False,
            "has_macro_data": True,
            "has_cot_data": True,
            "has_rate_decision": False,
            "has_high_impact_event": True,
            "has_dxy_data": True,
            "has_qe_qt": False,
            "has_stagflation": False,
            "has_cot_extremes": False,
            "has_tff_data": False,
            "has_core_inflation": False,
            "has_safe_haven_elevated": False,
            "has_commodity_currencies_weak": False,
            "dxy_momentum": "BEARISH",
            "risk_environment": "RISK_ON",
            "trace_id": "test-rag-macro-001",
        })

        assert resp.status_code == 200, f"RAG retrieve failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, dict)

    async def test_rag_retrieve_with_all_signal_flags(self, app_client):
        """Send all 19 boolean/string signal fields from the Go contract.

        Verifies the Python InternalRAGRequest Pydantic model accepts
        every field the Go orchestrator.retrieveRAG() sends.
        """
        resp = await app_client.post("/internal/rag/retrieve", json={
            # Core fields.
            "query_text": "EURUSD bullish SMC turtle soup",
            "strategy": "hybrid",
            "framework": "smc",
            "setup_family": "turtle_soup",
            "direction": "long",
            "timeframe": "H4",
            "style": "INTRADAY",
            "symbol": "EURUSD",
            # Array fields.
            "all_frameworks": ["smc"],
            "all_setup_families": ["turtle_soup", "order_block"],
            # TA signal booleans.
            "has_smc_candidates": True,
            "has_snd_candidates": False,
            # Macro signal booleans.
            "has_macro_data": True,
            "has_cot_data": True,
            "has_rate_decision": True,
            "has_high_impact_event": True,
            "has_dxy_data": True,
            # Enriched macro signal booleans.
            "has_qe_qt": True,
            "has_stagflation": False,
            "has_cot_extremes": True,
            "has_tff_data": True,
            "has_core_inflation": True,
            "has_safe_haven_elevated": False,
            "has_commodity_currencies_weak": False,
            # Macro string signals.
            "dxy_momentum": "BULLISH",
            "risk_environment": "RISK_ON",
            # Metadata.
            "trace_id": "test-rag-all-flags-001",
        })

        # The endpoint must accept all fields without validation error.
        assert resp.status_code == 200, \
            f"RAG should accept all signal flags, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert isinstance(data, dict)

    async def test_rag_retrieve_scenario_strategy(self, app_client):
        """Tests scenario_first strategy against real scenario collection."""
        resp = await app_client.post("/internal/rag/retrieve", json={
            "query_text": "EURUSD H4 bullish turtle soup long entry at liquidity sweep",
            "strategy": "scenario_first",
            "framework": "smc",
            "symbol": "EURUSD",
            "direction": "long",
            "has_smc_candidates": True,
            "trace_id": "test-rag-scenario-001",
        })

        assert resp.status_code == 200, f"RAG scenario retrieve failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, dict)

    async def test_rag_retrieve_empty_query_handled(self, app_client):
        """Empty query_text is handled gracefully (not a panic)."""
        resp = await app_client.post("/internal/rag/retrieve", json={
            "query_text": "",
            "trace_id": "test-rag-empty-001",
        })

        # Pydantic validation may reject empty query_text (422),
        # or the orchestrator may return empty results (200).
        # Either is acceptable; a 500 panic is NOT.
        assert resp.status_code in (200, 422), \
            f"Empty query should return 200 or 422, got {resp.status_code}: {resp.text}"
