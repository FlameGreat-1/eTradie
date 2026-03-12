from __future__ import annotations

import time
from uuid import UUID

from engine.config import RAGConfig
from engine.rag.constants import RetrievalStrategy
from engine.rag.embeddings.base import BaseEmbeddingProvider
from engine.rag.models.context_bundle import ContextBundle
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.assembler import assemble_context_bundle
from engine.rag.retrieval.citations import build_citations
from engine.rag.retrieval.conflicts import detect_conflicts
from engine.rag.retrieval.coverage import check_coverage
from engine.rag.retrieval.reranker import Reranker
from engine.rag.retrieval.retriever import Retriever
from engine.rag.retrieval.strategies.hybrid import HybridStrategy
from engine.rag.retrieval.strategies.macro_bias import MacroBiasStrategy
from engine.rag.retrieval.strategies.rule_first import RuleFirstStrategy
from engine.rag.retrieval.strategies.scenario_first import ScenarioFirstStrategy
from engine.rag.scenarios.matcher import ScenarioMatcher
from engine.rag.services.audit import AuditService
from engine.rag.storage.uow import RAGUnitOfWorkFactory
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class RAGOrchestrator:
    def __init__(
        self,
        *,
        config: RAGConfig,
        retriever: Retriever,
        reranker: Reranker,
        scenario_matcher: ScenarioMatcher,
        audit_service: AuditService,
        uow_factory: RAGUnitOfWorkFactory,
    ) -> None:
        self._config = config
        self._retriever = retriever
        self._reranker = reranker
        self._scenario_matcher = scenario_matcher
        self._audit = audit_service
        self._uow = uow_factory

        self._rule_first = RuleFirstStrategy(retriever=retriever)
        self._scenario_first = ScenarioFirstStrategy(retriever=retriever)
        self._macro_bias = MacroBiasStrategy(retriever=retriever)
        self._hybrid = HybridStrategy(retriever=retriever)

    async def retrieve_context(
        self,
        query_text: str,
        *,
        strategy: str | None = None,
        framework: str | None = None,
        setup_family: str | None = None,
        direction: str | None = None,
        timeframe: str | None = None,
        style: str | None = None,
        trace_id: str | None = None,
    ) -> ContextBundle:
        start = time.monotonic()
        effective_strategy = strategy or self._config.retrieval_default_strategy
        top_k = self._config.retrieval_top_k

        chunks = await self._execute_strategy(
            query_text,
            strategy=effective_strategy,
            top_k=top_k,
            framework=framework,
            setup_family=setup_family,
            direction=direction,
            timeframe=timeframe,
            style=style,
        )

        total_candidates = len(chunks)

        if self._config.rerank_enabled:
            chunks = self._reranker.rerank(
                chunks, strategy=effective_strategy,
            )

        version_map = await self._build_version_map(chunks)
        citations = build_citations(chunks, version_map=version_map)

        scenarios = await self._scenario_matcher.match(
            framework=framework,
            setup_family=setup_family,
            direction=direction,
            timeframe=timeframe,
        )

        elapsed_ms = (time.monotonic() - start) * 1000

        coverage = check_coverage(
            chunks,
            config=self._config,
            required_framework=framework,
            strategy=effective_strategy,
        )
        conflict_result, conflict_details = detect_conflicts(chunks)

        bundle = assemble_context_bundle(
            strategy=RetrievalStrategy(effective_strategy),
            chunks=chunks,
            citations=citations,
            scenarios=scenarios,
            coverage_result=coverage.result,
            conflict_result=conflict_result,
            coverage_gaps=list(coverage.gaps),
            conflict_details=conflict_details,
            total_candidates=total_candidates,
        )

        retrieval_log_id = await self._audit.log_retrieval(
            query_text=query_text,
            strategy=effective_strategy,
            filters_applied={
                "framework": framework,
                "setup_family": setup_family,
                "direction": direction,
                "timeframe": timeframe,
                "style": style,
            },
            total_candidates=total_candidates,
            chunks_returned=len(chunks),
            score_threshold=self._config.retrieval_score_threshold,
            coverage_result=bundle.coverage_result,
            conflict_result=bundle.conflict_result,
            duration_ms=elapsed_ms,
            trace_id=trace_id,
        )

        await self._audit.log_citations(
            retrieval_log_id=retrieval_log_id,
            citations=citations,
        )

        logger.info(
            "rag_retrieval_completed",
            strategy=effective_strategy,
            chunks=len(chunks),
            scenarios=len(scenarios),
            citations=len(citations),
            elapsed_ms=round(elapsed_ms, 1),
            trace_id=trace_id,
        )

        return bundle

    async def _execute_strategy(
        self,
        query_text: str,
        *,
        strategy: str,
        top_k: int,
        framework: str | None,
        setup_family: str | None,
        direction: str | None,
        timeframe: str | None,
        style: str | None,
    ) -> list[RetrievedChunk]:
        doc_collection = self._config.collection_documents
        scenario_collection = self._config.collection_scenarios

        if strategy == RetrievalStrategy.RULE_FIRST:
            return await self._rule_first.execute(
                query_text,
                collection=doc_collection,
                top_k=top_k,
                framework=framework,
                direction=direction,
                timeframe=timeframe,
                style=style,
                setup_family=setup_family,
            )

        if strategy == RetrievalStrategy.SCENARIO_FIRST:
            return await self._scenario_first.execute(
                query_text,
                collection=doc_collection,
                scenario_collection=scenario_collection,
                top_k=top_k,
                framework=framework,
                direction=direction,
                timeframe=timeframe,
                setup_family=setup_family,
            )

        if strategy == RetrievalStrategy.MACRO_BIAS:
            return await self._macro_bias.execute(
                query_text,
                collection=doc_collection,
                top_k=top_k,
                style=style,
                direction=direction,
            )

        return await self._hybrid.execute(
            query_text,
            collection=doc_collection,
            scenario_collection=scenario_collection,
            top_k=top_k,
            framework=framework,
            direction=direction,
            timeframe=timeframe,
            style=style,
            setup_family=setup_family,
        )

    async def _build_version_map(
        self, chunks: list[RetrievedChunk],
    ) -> dict[UUID, UUID]:
        version_map: dict[UUID, UUID] = {}
        seen_doc_ids: set[UUID] = set()

        async with self._uow() as uow:
            for chunk in chunks:
                if chunk.document_id in seen_doc_ids:
                    continue
                seen_doc_ids.add(chunk.document_id)

                active = await uow.version_repo.get_active(chunk.document_id)
                if active:
                    version_map[chunk.document_id] = active.id

        return version_map
