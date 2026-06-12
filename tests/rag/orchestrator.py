"""Tests for RAGOrchestrator (retrieval pipeline coordination).

Production module: src/engine/rag/orchestrator.py

The RAGOrchestrator requires async dependencies (UoW factory, vector store,
embedding provider, audit service) that need real or mock infrastructure.
These tests verify the import chain, constructor signature, and model
structure. Full integration tests are deferred to the integration phase.
"""

from engine.rag.constants import (
    ConflictResult,
    CoverageResult,
    RetrievalStrategy,
)
from engine.rag.models.context_bundle import ContextBundle


class TestRAGOrchestratorImports:
    def test_orchestrator_importable(self):
        """RAGOrchestrator can be imported without side effects."""
        from engine.rag.orchestrator import RAGOrchestrator

        assert RAGOrchestrator is not None

    def test_retriever_importable(self):
        from engine.rag.retrieval.retriever import Retriever

        assert Retriever is not None

    def test_reranker_importable(self):
        from engine.rag.retrieval.reranker import Reranker

        assert Reranker is not None

    def test_scenario_matcher_importable(self):
        from engine.rag.scenarios.matcher import ScenarioMatcher

        assert ScenarioMatcher is not None


class TestContextBundleModel:
    def test_default_fields(self):
        """ContextBundle has correct default values."""
        bundle = ContextBundle(
            strategy_used=RetrievalStrategy.HYBRID,
        )
        assert bundle.strategy_used == RetrievalStrategy.HYBRID
        assert bundle.retrieved_chunks == ()
        assert bundle.citations == ()
        assert bundle.matched_scenarios == ()
        assert bundle.coverage_result == CoverageResult.INSUFFICIENT
        assert bundle.conflict_result == ConflictResult.NONE_DETECTED
        assert bundle.coverage_gaps == ()
        assert bundle.conflict_details == ()
        assert bundle.total_chunks_considered == 0
        assert bundle.total_chunks_returned == 0

    def test_has_timestamps(self):
        """ContextBundle inherits TimestampedModel (id + created_at)."""
        bundle = ContextBundle(
            strategy_used=RetrievalStrategy.RULE_FIRST,
        )
        assert bundle.id is not None
        assert bundle.created_at is not None


class TestRetrievalStrategyEnum:
    def test_all_strategies_exist(self):
        assert RetrievalStrategy.HYBRID
        assert RetrievalStrategy.RULE_FIRST
        assert RetrievalStrategy.SCENARIO_FIRST
        assert RetrievalStrategy.MACRO_BIAS
