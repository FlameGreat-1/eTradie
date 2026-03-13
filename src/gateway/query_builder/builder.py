"""RAG query builder orchestrator.

Translates TA + Macro outputs into the exact parameters that
RAGOrchestrator.retrieve_context() expects.
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
        """Build RAG query parameters for a single symbol."""
        ta_signals = extract_ta_signals(ta_result)
        macro_signals = extract_macro_signals(macro_result)

        query_text = build_query_text(ta_signals, macro_signals)
        strategy = self._select_strategy(ta_signals, macro_signals)

        params = RAGQueryParams(
            query_text=query_text,
            strategy=strategy,
            framework=ta_signals.framework,
            setup_family=ta_signals.setup_family,
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
                "direction": params.direction,
                "strategy": params.strategy,
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
        if macro.has_nfp or macro.has_cpi or macro.has_rate_decision:
            return "rule_first"

        if macro.high_impact_events_within_24h:
            return "rule_first"

        if ta.framework and ta.setup_family and ta.direction:
            return "scenario_first"

        if macro.macro_bias_usd and macro.macro_bias_usd != "NEUTRAL":
            return "macro_bias"

        return "hybrid"
