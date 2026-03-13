"""RAG query builder orchestrator.

Translates TA + Macro outputs into the exact parameters that
RAGOrchestrator.retrieve_context() expects.

The query_text contains ALL signals (no limits) for semantic search.
The filter parameters (framework, setup_family, direction, timeframe)
are used for metadata filtering in the vector store.
"""

from __future__ import annotations

from typing import Optional

from engine.shared.logging import get_logger
from engine.shared.models.base import FrozenModel
from gateway.context.models import MacroResult, TASymbolResult
from gateway.query_builder.macro_extractor import MacroSignals, extract_macro_signals
from gateway.query_builder.query_text import build_query_text
from gateway.query_builder.ta_extractor import TASignals, extract_ta_signals

logger = get_logger(__name__)


class RAGQueryParams(FrozenModel):
    """Parameters for RAGOrchestrator.retrieve_context()."""

    query_text: str
    strategy: Optional[str] = None
    framework: Optional[str] = None
    setup_family: Optional[str] = None
    direction: Optional[str] = None
    timeframe: Optional[str] = None
    style: Optional[str] = None


class QueryBuilder:
    """Builds RAG query parameters from TA and Macro outputs."""

    def build(
        self,
        ta_result: TASymbolResult,
        macro_result: MacroResult,
        *,
        style: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> RAGQueryParams:
        """Build RAG query parameters for a single symbol.

        The query_text includes ALL signals for semantic search.
        The filter params use the primary values for metadata filtering.
        """
        ta_signals = extract_ta_signals(ta_result)
        macro_signals = extract_macro_signals(macro_result)

        query_text = build_query_text(ta_signals, macro_signals)
        strategy = self._select_strategy(ta_signals, macro_signals)

        # RAGOrchestrator accepts a single setup_family for metadata filtering.
        # Pass the primary (first) family. ALL families are already in query_text.
        primary_setup_family = (
            ta_signals.setup_families[0] if ta_signals.setup_families else None
        )

        params = RAGQueryParams(
            query_text=query_text,
            strategy=strategy,
            framework=ta_signals.framework,
            setup_family=primary_setup_family,
            direction=ta_signals.direction,
            timeframe=ta_signals.htf_timeframe,
            style=style,
        )

        logger.debug(
            "rag_query_built",
            extra={
                "symbol": ta_result.symbol,
                "query_text_length": len(query_text),
                "framework": params.framework,
                "setup_family": params.setup_family,
                "all_setup_families": ta_signals.setup_families,
                "direction": params.direction,
                "strategy": params.strategy,
                "patterns_count": len(ta_signals.patterns_detected),
                "trace_id": trace_id,
            },
        )

        return params

    @staticmethod
    def _select_strategy(
        ta: TASignals,
        macro: MacroSignals,
    ) -> Optional[str]:
        """Select the optimal RAG retrieval strategy based on signals.

        - hybrid (default): balanced retrieval across all buckets
        - macro_bias: when macro signals are strong and potentially conflicting
        - rule_first: when we need rejection rules (high-impact events)
        - scenario_first: when pattern is clear and we need scenario matches
        """
        # High-impact events demand rule retrieval first
        if macro.has_nfp or macro.has_cpi or macro.has_rate_decision:
            return "rule_first"

        if macro.high_impact_events_within_24h:
            return "rule_first"

        # Rate change is a major macro event
        if macro.has_rate_change:
            return "rule_first"

        # Clear pattern with setup families -> scenario matching
        if ta.framework and ta.setup_families and ta.direction:
            return "scenario_first"

        # Strong macro bias -> macro-weighted retrieval
        if macro.macro_bias_usd and macro.macro_bias_usd != "NEUTRAL":
            return "macro_bias"

        return "hybrid"
