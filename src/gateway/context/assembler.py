"""Context assembler.

Builds the final ProcessorInput payload by combining TA output,
Macro output, and RAG-retrieved knowledge into a single structured
context for the Processor LLM.
"""

from __future__ import annotations

from typing import Optional

from engine.rag.models.context_bundle import ContextBundle
from engine.shared.logging import get_logger
from gateway.context.models import MacroResult, ProcessorInput, TASymbolResult

logger = get_logger(__name__)


class ContextAssembler:
    """Assembles the final LLM context payload."""

    def assemble(
        self,
        *,
        symbol: str,
        ta_result: TASymbolResult,
        macro_result: MacroResult,
        rag_bundle: ContextBundle,
        trace_id: Optional[str] = None,
    ) -> ProcessorInput:
        """Build ProcessorInput from all pipeline outputs."""
        ta_analysis = self._build_ta_section(ta_result)
        macro_analysis = self._build_macro_section(macro_result)
        retrieved_knowledge = self._build_rag_section(rag_bundle)

        metadata = {
            "symbol": symbol,
            "htf_timeframes": ta_result.htf_timeframes,
            "ltf_timeframes": ta_result.ltf_timeframes,
            "overall_trend": ta_result.overall_trend,
            "rag_strategy": rag_bundle.strategy_used.value,
            "rag_coverage": rag_bundle.coverage_result.value,
            "rag_conflict": rag_bundle.conflict_result.value,
            "rag_chunks_returned": rag_bundle.total_chunks_returned,
            "macro_datasets_available": macro_result.available_datasets,
            "trace_id": trace_id,
        }

        if rag_bundle.coverage_gaps:
            metadata["coverage_gaps"] = list(rag_bundle.coverage_gaps)
        if rag_bundle.conflict_details:
            metadata["conflict_details"] = list(rag_bundle.conflict_details)

        payload = ProcessorInput(
            symbol=symbol,
            ta_analysis=ta_analysis,
            macro_analysis=macro_analysis,
            retrieved_knowledge=retrieved_knowledge,
            metadata=metadata,
        )

        logger.debug(
            "context_assembled",
            extra={
                "symbol": symbol,
                "ta_smc_count": len(ta_result.smc_candidates),
                "ta_snd_count": len(ta_result.snd_candidates),
                "macro_datasets": len(macro_result.available_datasets),
                "rag_chunks": rag_bundle.total_chunks_returned,
                "rag_scenarios": len(rag_bundle.matched_scenarios),
                "trace_id": trace_id,
            },
        )

        return payload

    @staticmethod
    def _build_ta_section(ta: TASymbolResult) -> dict:
        """Build the technical_analysis section of the context."""
        return {
            "symbol": ta.symbol,
            "htf_timeframes": ta.htf_timeframes,
            "ltf_timeframes": ta.ltf_timeframes,
            "status": ta.status,
            "smc_candidates": ta.smc_candidates,
            "snd_candidates": ta.snd_candidates,
            "snapshots": ta.snapshots,
            "alignment": ta.alignment,
            "overall_trend": ta.overall_trend,
        }

    @staticmethod
    def _build_macro_section(macro: MacroResult) -> dict:
        """Build the macro_analysis section of the context."""
        return {
            "central_bank": macro.central_bank,
            "cot": macro.cot,
            "economic": macro.economic,
            "news": macro.news,
            "calendar": macro.calendar,
            "dxy": macro.dxy,
            "intermarket": macro.intermarket,
            "sentiment": macro.sentiment,
            "datasets_available": macro.available_datasets,
            "collection_errors": macro.errors,
        }

    @staticmethod
    def _build_rag_section(bundle: ContextBundle) -> dict:
        """Build the retrieved_knowledge section of the context."""
        chunks_data = []
        for chunk in bundle.retrieved_chunks:
            chunks_data.append({
                "content": chunk.content,
                "score": chunk.score,
                "metadata": chunk.metadata if hasattr(chunk, "metadata") else {},
                "document_id": str(chunk.document_id) if hasattr(chunk, "document_id") else None,
            })

        citations_data = []
        for citation in bundle.citations:
            citations_data.append({
                "rule_id": citation.rule_id if hasattr(citation, "rule_id") else None,
                "document_title": citation.document_title if hasattr(citation, "document_title") else None,
                "section": citation.section if hasattr(citation, "section") else None,
                "content_preview": citation.content_preview if hasattr(citation, "content_preview") else None,
            })

        scenarios_data = []
        for scenario in bundle.matched_scenarios:
            scenarios_data.append({
                "scenario_id": scenario.scenario_id if hasattr(scenario, "scenario_id") else None,
                "description": scenario.description if hasattr(scenario, "description") else None,
                "outcome": scenario.outcome if hasattr(scenario, "outcome") else None,
            })

        return {
            "strategy_used": bundle.strategy_used.value,
            "chunks": chunks_data,
            "citations": citations_data,
            "matched_scenarios": scenarios_data,
            "coverage_result": bundle.coverage_result.value,
            "conflict_result": bundle.conflict_result.value,
            "coverage_gaps": list(bundle.coverage_gaps),
            "conflict_details": list(bundle.conflict_details),
        }
