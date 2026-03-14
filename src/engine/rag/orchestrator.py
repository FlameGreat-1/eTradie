from __future__ import annotations

import time
from uuid import UUID

from engine.config import RAGConfig
from engine.rag.constants import RetrievalStrategy
from engine.rag.models.context_bundle import ContextBundle
from engine.rag.models.retrieval import RetrievedChunk
from engine.rag.retrieval.assembler import assemble_context_bundle
from engine.rag.retrieval.citations import build_citations
from engine.rag.retrieval.conflicts import detect_conflicts
from engine.rag.retrieval.coverage import check_coverage
from engine.rag.retrieval.gap_filler import GapFiller
from engine.rag.retrieval.mandatory import (
    MandatoryRequirements,
    compute_mandatory_requirements,
)
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
        self._gap_filler = GapFiller(retriever=retriever)

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
        symbol: str | None = None,
        all_frameworks: list[str] | None = None,
        all_setup_families: list[str] | None = None,
        has_smc_candidates: bool = False,
        has_snd_candidates: bool = False,
        has_macro_data: bool = False,
        has_cot_data: bool = False,
        has_rate_decision: bool = False,
        has_high_impact_event: bool = False,
        has_dxy_data: bool = False,
    ) -> ContextBundle:
        start = time.monotonic()
        effective_strategy = strategy or self._config.retrieval_default_strategy
        top_k = self._config.retrieval_top_k

        # Compute mandatory requirements from signals
        mandatory = compute_mandatory_requirements(
            symbol=symbol,
            has_smc_candidates=has_smc_candidates,
            has_snd_candidates=has_snd_candidates,
            has_macro_data=has_macro_data,
            has_cot_data=has_cot_data,
            has_rate_decision=has_rate_decision,
            has_high_impact_event=has_high_impact_event,
            has_dxy_data=has_dxy_data,
            style=style,
        )

        # Phase 1: Primary strategy retrieval
        chunks = await self._execute_strategy(
            query_text,
            strategy=effective_strategy,
            top_k=top_k,
            framework=framework,
            setup_family=setup_family,
            direction=direction,
            timeframe=timeframe,
            style=style,
            all_frameworks=all_frameworks,
            all_setup_families=all_setup_families,
        )

        total_candidates = len(chunks)

        # Phase 2: Gap filling - ensure mandatory doc_types are covered
        chunks = await self._gap_filler.fill_gaps(
            chunks,
            mandatory,
            query_text=query_text,
            doc_collection=self._config.collection_documents,
            scenario_collection=self._config.collection_scenarios,
            direction=direction,
            timeframe=timeframe,
            style=style,
        )

        total_after_gaps = len(chunks)

        # Phase 3: Reranking (applied to the full set including gap fills)
        # Pass mandatory requirements so the reranker preserves gap-filled
        # chunks that meet mandatory minimums instead of truncating them.
        if self._config.rerank_enabled:
            chunks = self._reranker.rerank(
                chunks, strategy=effective_strategy, mandatory=mandatory,
            )

        version_map = await self._build_version_map(chunks)
        citations = build_citations(chunks, version_map=version_map)

        # Scenario matching uses ALL setup families, not just primary
        effective_setup_families = all_setup_families or (
            [setup_family] if setup_family else []
        )
        scenarios = await self._match_scenarios(
            framework=framework,
            setup_families=effective_setup_families,
            direction=direction,
            timeframe=timeframe,
            all_frameworks=all_frameworks,
        )

        elapsed_ms = (time.monotonic() - start) * 1000

        coverage = check_coverage(
            chunks,
            config=self._config,
            required_framework=framework,
            strategy=effective_strategy,
            mandatory=mandatory,
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
                "symbol": symbol,
                "all_frameworks": all_frameworks,
                "all_setup_families": all_setup_families,
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
            chunks_from_primary=total_candidates,
            chunks_from_gap_fill=total_after_gaps - total_candidates,
            scenarios=len(scenarios),
            citations=len(citations),
            coverage=coverage.result,
            mandatory_doc_types=len(mandatory.force_doc_types),
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
        all_frameworks: list[str] | None = None,
        all_setup_families: list[str] | None = None,
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
                all_frameworks=all_frameworks,
                all_setup_families=all_setup_families,
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
                all_frameworks=all_frameworks,
                all_setup_families=all_setup_families,
            )

        if strategy == RetrievalStrategy.MACRO_BIAS:
            return await self._macro_bias.execute(
                query_text,
                collection=doc_collection,
                top_k=top_k,
                style=style,
                direction=direction,
                all_frameworks=all_frameworks,
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
            all_frameworks=all_frameworks,
            all_setup_families=all_setup_families,
        )

    async def _match_scenarios(
        self,
        *,
        framework: str | None,
        setup_families: list[str],
        direction: str | None,
        timeframe: str | None,
        all_frameworks: list[str] | None,
    ) -> list:
        """Match scenarios across ALL setup families and frameworks.

        Instead of matching only the primary setup_family, this iterates
        through all detected families and frameworks to find the most
        relevant scenario examples for the LLM.
        """
        from engine.rag.models.scenario import Scenario

        all_scenarios: list[Scenario] = []
        seen_ids: set = set()

        # Match using primary framework + each setup family
        frameworks_to_try = [framework] if framework else []
        if all_frameworks:
            for fw in all_frameworks:
                if fw not in frameworks_to_try:
                    frameworks_to_try.append(fw)

        families_to_try = setup_families if setup_families else [None]

        for fw in (frameworks_to_try or [None]):
            for family in families_to_try:
                matched = await self._scenario_matcher.match(
                    framework=fw,
                    setup_family=family,
                    direction=direction,
                    timeframe=timeframe,
                    limit=3,
                )
                for scenario in matched:
                    if scenario.id not in seen_ids:
                        all_scenarios.append(scenario)
                        seen_ids.add(scenario.id)

        # Cap total scenarios to avoid excessive token usage
        return all_scenarios[:8]

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
