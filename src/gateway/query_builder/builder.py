"""RAG query builder orchestrator.

Translates TA + Macro outputs into the exact parameters that
RAGOrchestrator.retrieve_context() expects.

The query_text contains ALL signals (no limits) for semantic search.
The filter parameters (framework, setup_family, direction, timeframe)
are used for metadata filtering in the vector store.

The mandatory_requirements tell the RAG orchestrator which doc_types
MUST have chunks in the result, ensuring comprehensive coverage.
"""

from __future__ import annotations

from typing import Optional

from engine.rag.retrieval.mandatory import (
    MandatoryRequirements,
    compute_mandatory_requirements,
)
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
    symbol: Optional[str] = None
    all_frameworks: list[str] = []
    all_setup_families: list[str] = []
    has_smc_candidates: bool = False
    has_snd_candidates: bool = False
    has_macro_data: bool = False
    has_cot_data: bool = False
    has_rate_decision: bool = False
    has_high_impact_event: bool = False
    has_dxy_data: bool = False


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
        All frameworks and setup families are passed so the RAG can
        retrieve from every relevant document.
        """
        ta_signals = extract_ta_signals(ta_result)
        macro_signals = extract_macro_signals(macro_result)

        query_text = build_query_text(ta_signals, macro_signals)
        strategy = self._select_strategy(ta_signals, macro_signals)

        # RAGOrchestrator accepts a single setup_family for metadata filtering.
        # Pass the primary (first) family. ALL families are in all_setup_families.
        primary_setup_family = (
            ta_signals.setup_families[0] if ta_signals.setup_families else None
        )

        # Determine all frameworks that have candidates
        all_frameworks = self._collect_all_frameworks(ta_signals, macro_signals)

        # Determine macro presence flags
        has_macro = bool(macro_signals.fed_tone or macro_signals.ecb_tone
                         or macro_signals.boe_tone or macro_signals.boj_tone
                         or macro_signals.macro_bias_usd)
        has_cot = (macro_signals.cot_net_eur is not None
                   or macro_signals.cot_net_gbp is not None
                   or macro_signals.cot_net_jpy is not None
                   or macro_signals.cot_net_aud is not None
                   or macro_signals.cot_net_cad is not None
                   or macro_signals.cot_net_nzd is not None
                   or macro_signals.cot_net_chf is not None)
        has_dxy = macro_signals.dxy_value is not None
        has_high_impact = bool(macro_signals.high_impact_events_within_24h)

        params = RAGQueryParams(
            query_text=query_text,
            strategy=strategy,
            framework=ta_signals.framework,
            setup_family=primary_setup_family,
            direction=ta_signals.direction,
            timeframe=ta_signals.htf_timeframe,
            style=style,
            symbol=ta_result.symbol,
            all_frameworks=all_frameworks,
            all_setup_families=ta_signals.setup_families,
            has_smc_candidates=ta_signals.has_bms or ta_signals.has_order_block or ta_signals.has_fvg or ta_signals.has_liquidity_sweep,
            has_snd_candidates=ta_signals.has_qml or ta_signals.has_sr_flip or ta_signals.has_rs_flip,
            has_macro_data=has_macro,
            has_cot_data=has_cot,
            has_rate_decision=macro_signals.has_rate_decision or macro_signals.has_rate_change,
            has_high_impact_event=has_high_impact,
            has_dxy_data=has_dxy,
        )

        logger.debug(
            "rag_query_built",
            extra={
                "symbol": ta_result.symbol,
                "query_text_length": len(query_text),
                "framework": params.framework,
                "setup_family": params.setup_family,
                "all_frameworks": all_frameworks,
                "all_setup_families": ta_signals.setup_families,
                "direction": params.direction,
                "strategy": params.strategy,
                "patterns_count": len(ta_signals.patterns_detected),
                "has_smc": params.has_smc_candidates,
                "has_snd": params.has_snd_candidates,
                "has_macro": params.has_macro_data,
                "has_cot": params.has_cot_data,
                "has_dxy": params.has_dxy_data,
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

    @staticmethod
    def _collect_all_frameworks(
        ta: TASignals,
        macro: MacroSignals,
    ) -> list[str]:
        """Collect ALL frameworks that are relevant to this analysis.

        This ensures the RAG retrieves from every framework document
        that has detected signals, not just the primary one.
        """
        frameworks: set[str] = set()

        # TA frameworks
        if ta.has_bms or ta.has_choch or ta.has_sms or ta.has_order_block or ta.has_fvg or ta.has_liquidity_sweep or ta.has_inducement_cleared or ta.has_displacement:
            frameworks.add("smc")
        if ta.has_qml or ta.has_sr_flip or ta.has_rs_flip or ta.has_mpl or ta.has_fakeout or ta.has_marubozu or ta.has_compression:
            frameworks.add("snd")

        # Wyckoff is always relevant for phase context
        frameworks.add("wyckoff")

        # Macro frameworks
        if macro.dxy_value is not None or macro.dxy_trend:
            frameworks.add("dxy")
        if any(v is not None for v in [
            macro.cot_net_eur, macro.cot_net_gbp, macro.cot_net_jpy,
            macro.cot_net_aud, macro.cot_net_cad, macro.cot_net_nzd,
            macro.cot_net_chf,
        ]):
            frameworks.add("cot")
        if macro.fed_tone or macro.ecb_tone or macro.boe_tone or macro.boj_tone:
            frameworks.add("macro")

        return sorted(frameworks)
