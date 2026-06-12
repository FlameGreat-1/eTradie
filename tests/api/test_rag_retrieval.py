"""Integration tests for real RAG retrieval against live ChromaDB.

These tests exercise the complete RAG pipeline:
  /internal/rag/retrieve -> RAGOrchestrator -> Embedding -> ChromaDB -> Reranker

The response is ContextBundle.model_dump(mode="json") which returns:
  - strategy_used: str (enum value)
  - retrieved_chunks: list[RetrievedChunk] (chunk_id, document_id, doc_type, content, score, rank, ...)
  - citations: list[Citation]
  - matched_scenarios: list[Scenario]
  - coverage_result: str ("SUFFICIENT" or "INSUFFICIENT")
  - conflict_result: str ("NONE_DETECTED" or "CONFLICTING_RULES_DETECTED")
  - coverage_gaps: list[str]
  - conflict_details: list[str]
  - total_chunks_considered: int
  - total_chunks_returned: int

Requires ChromaDB running in Docker with embeddings already loaded.
Run: pytest tests/api/test_rag_retrieval.py -v -m integration
"""

from __future__ import annotations

import pytest

from tests.api.conftest import CHROMA_AVAILABLE, skip_no_infra

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, skip_no_infra]

skip_no_chroma = pytest.mark.skipif(
    not CHROMA_AVAILABLE,
    reason="ChromaDB not available - RAG retrieval tests require real vector store",
)


@skip_no_chroma
class TestRAGRetrieval:
    """Tests the real /internal/rag/retrieve endpoint against live ChromaDB.

    Every test sends a POST to the Python engine's internal RAG endpoint,
    which triggers the full pipeline:
    1. Embedding the query text (sentence_transformers or openai)
    2. Vector search against real ChromaDB collections
    3. Gap filling for mandatory doc_types
    4. Reranking with rule_weighted scorer
    5. Coverage and conflict analysis
    6. ContextBundle assembly and model_dump(mode="json")
    """

    async def test_rag_retrieve_smc_query(self, app_client):
        """SMC turtle soup query returns relevant knowledge chunks."""
        resp = await app_client.post(
            "/internal/rag/retrieve",
            json={
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
            },
        )

        assert resp.status_code == 200, f"RAG retrieve failed: {resp.text}"
        data = resp.json()

        # ContextBundle.model_dump() field names.
        assert "retrieved_chunks" in data, f"Response should contain 'retrieved_chunks', got keys: {list(data.keys())}"
        assert "strategy_used" in data
        assert "coverage_result" in data
        assert "conflict_result" in data
        assert "total_chunks_returned" in data
        assert "total_chunks_considered" in data

        # Strategy should be the one we requested.
        assert data["strategy_used"] == "hybrid"

        # Coverage result is a StrEnum (lowercase values from rag/constants.py).
        assert data["coverage_result"] in ("sufficient", "insufficient", "partial"), (
            f"Unexpected coverage_result: {data['coverage_result']}"
        )

        # Conflict result is a StrEnum (lowercase values from rag/constants.py).
        assert data["conflict_result"] in (
            "none_detected",
            "conflict_found",
        ), f"Unexpected conflict_result: {data['conflict_result']}"

        # With real embeddings loaded, we should get chunks.
        chunks = data["retrieved_chunks"]
        assert isinstance(chunks, list), "retrieved_chunks should be a list"
        assert len(chunks) > 0, "Real ChromaDB with loaded embeddings should return chunks for SMC query"

        # Verify RetrievedChunk structure.
        chunk = chunks[0]
        assert "content" in chunk, "chunk should have 'content'"
        assert len(chunk["content"]) > 0, "chunk content should not be empty"
        assert "score" in chunk, "chunk should have 'score'"
        assert isinstance(chunk["score"], (int, float)), "score should be numeric"
        assert 0.0 <= chunk["score"] <= 1.0, "score should be between 0 and 1"
        assert "doc_type" in chunk, "chunk should have 'doc_type'"
        assert "chunk_id" in chunk, "chunk should have 'chunk_id'"
        assert "document_id" in chunk, "chunk should have 'document_id'"
        assert "rank" in chunk, "chunk should have 'rank'"

        # total_chunks_returned should match the actual chunk count.
        assert data["total_chunks_returned"] == len(chunks)

        # Citations should be present (may be empty if no version map).
        assert "citations" in data
        assert isinstance(data["citations"], list)

        # Matched scenarios should be present.
        assert "matched_scenarios" in data
        assert isinstance(data["matched_scenarios"], list)

    async def test_rag_retrieve_snd_query(self, app_client):
        """SnD QML query returns relevant knowledge chunks."""
        resp = await app_client.post(
            "/internal/rag/retrieve",
            json={
                "query_text": "GBPUSD bearish supply demand QML baseline short H4 previous levels fakeout",
                "strategy": "hybrid",
                "framework": "snd",
                "symbol": "GBPUSD",
                "direction": "short",
                "has_smc_candidates": False,
                "has_snd_candidates": True,
                "trace_id": "test-rag-snd-001",
            },
        )

        assert resp.status_code == 200, f"RAG retrieve failed: {resp.text}"
        data = resp.json()

        assert "retrieved_chunks" in data
        chunks = data["retrieved_chunks"]
        assert isinstance(chunks, list)
        assert len(chunks) > 0, "Real ChromaDB should return chunks for SnD query"

    async def test_rag_retrieve_macro_enriched(self, app_client):
        """Query with macro signal flags exercises enriched retrieval."""
        resp = await app_client.post(
            "/internal/rag/retrieve",
            json={
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
            },
        )

        assert resp.status_code == 200, f"RAG retrieve failed: {resp.text}"
        data = resp.json()

        assert "retrieved_chunks" in data
        assert data["strategy_used"] == "macro_bias"
        chunks = data["retrieved_chunks"]
        assert isinstance(chunks, list)
        assert len(chunks) > 0, "macro_bias strategy should return chunks with enriched signals"

    async def test_rag_retrieve_with_all_signal_flags(self, app_client):
        """Send all 19 boolean/string signal fields from the Go contract.

        Verifies the Python InternalRAGRequest Pydantic model accepts
        every field the Go orchestrator.retrieveRAG() sends, and the
        RAGOrchestrator.retrieve_context() processes them correctly.
        """
        resp = await app_client.post(
            "/internal/rag/retrieve",
            json={
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
            },
        )

        # The endpoint must accept all fields without validation error.
        assert resp.status_code == 200, f"RAG should accept all signal flags, got {resp.status_code}: {resp.text}"
        data = resp.json()

        # Verify full ContextBundle structure.
        assert "retrieved_chunks" in data
        assert "strategy_used" in data
        assert "coverage_result" in data
        assert "conflict_result" in data
        assert "citations" in data
        assert "matched_scenarios" in data
        assert "total_chunks_returned" in data
        assert "total_chunks_considered" in data
        assert "coverage_gaps" in data
        assert "conflict_details" in data

    async def test_rag_retrieve_scenario_strategy(self, app_client):
        """Tests scenario_first strategy against real scenario collection."""
        resp = await app_client.post(
            "/internal/rag/retrieve",
            json={
                "query_text": "EURUSD H4 bullish turtle soup long entry at liquidity sweep",
                "strategy": "scenario_first",
                "framework": "smc",
                "symbol": "EURUSD",
                "direction": "long",
                "has_smc_candidates": True,
                "trace_id": "test-rag-scenario-001",
            },
        )

        assert resp.status_code == 200, f"RAG scenario retrieve failed: {resp.text}"
        data = resp.json()

        assert data["strategy_used"] == "scenario_first"
        assert "retrieved_chunks" in data
        assert "matched_scenarios" in data

    async def test_rag_retrieve_rule_first_strategy(self, app_client):
        """Tests rule_first strategy against real document collection."""
        resp = await app_client.post(
            "/internal/rag/retrieve",
            json={
                "query_text": "risk management position sizing 1 percent rule stop loss",
                "strategy": "rule_first",
                "framework": "smc",
                "symbol": "EURUSD",
                "direction": "long",
                "has_smc_candidates": True,
                "trace_id": "test-rag-rule-first-001",
            },
        )

        assert resp.status_code == 200, f"RAG rule_first failed: {resp.text}"
        data = resp.json()

        assert data["strategy_used"] == "rule_first"
        assert "retrieved_chunks" in data
        chunks = data["retrieved_chunks"]
        assert len(chunks) > 0, "rule_first strategy should return rulebook chunks"

    async def test_rag_retrieve_empty_query_handled(self, app_client):
        """Empty query_text is handled gracefully (not a panic)."""
        resp = await app_client.post(
            "/internal/rag/retrieve",
            json={
                "query_text": "",
                "trace_id": "test-rag-empty-001",
            },
        )

        # Pydantic validation may reject empty query_text (422),
        # or the orchestrator may return empty results (200).
        # Either is acceptable; a 500 panic is NOT.
        assert resp.status_code in (200, 422), (
            f"Empty query should return 200 or 422, got {resp.status_code}: {resp.text}"
        )
