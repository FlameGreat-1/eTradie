"""Map AnalysisOutput to the gateway's ProcessorOutput.

The gateway's ProcessorOutput is a simpler model used for guard
evaluation and execution routing. This mapper bridges the rich
AnalysisOutput (full Rulebook schema) to the gateway contract.

Single responsibility: model translation. No business logic.
"""

from __future__ import annotations

from engine.processor.constants import (
    RISK_PERCENT_A,
    RISK_PERCENT_A_PLUS,
    RISK_PERCENT_B,
)
from engine.processor.models.analysis import AnalysisOutput
from gateway.context.models import ProcessorOutput


def map_to_processor_output(
    analysis: AnalysisOutput,
    *,
    raw_response: dict | None = None,
) -> ProcessorOutput:
    """Map AnalysisOutput to the gateway's ProcessorOutput.

    Args:
        analysis: The validated canonical analysis output.
        raw_response: The raw LLM response dict for audit.

    Returns:
        ProcessorOutput compatible with the gateway's routing layer.
    """
    trade_valid = (
        analysis.direction in ("LONG", "SHORT")
        and analysis.setup_grade in ("A+", "A", "B")
        and analysis.proceed_to_module_b == "YES"
    )

    confidence_float = _confidence_to_float(analysis.confidence)
    risk_pct = _grade_to_risk_percent(analysis.setup_grade)

    entry_price = None
    if analysis.entry_zone.low is not None and analysis.entry_zone.high is not None:
        entry_price = (analysis.entry_zone.low + analysis.entry_zone.high) / 2

    take_profit = None
    if analysis.take_profits:
        last_tp = analysis.take_profits[-1]
        if last_tp.level is not None:
            take_profit = last_tp.level

    rejection_rules: list[str] = []
    if not trade_valid and analysis.direction == "NO SETUP":
        for factor in analysis.confluence_score.factors:
            if not factor.present and factor.value == 0:
                rejection_rules.append(f"missing_{factor.name}")

    return ProcessorOutput(
        trade_valid=trade_valid,
        direction=analysis.direction if analysis.direction != "NO SETUP" else None,
        symbol=analysis.pair,
        confidence=confidence_float,
        grade=analysis.setup_grade,
        risk_percentage=risk_pct if trade_valid else None,
        reasoning=analysis.explainable_reasoning,
        entry_price=entry_price,
        stop_loss=analysis.stop_loss.price,
        take_profit=take_profit,
        rejection_rules=rejection_rules,
        raw_response=raw_response or {},
    )


def _confidence_to_float(confidence: str) -> float:
    """Map confidence string to a 0.0-1.0 float."""
    mapping = {
        "HIGH": 0.85,
        "MEDIUM": 0.60,
        "LOW": 0.35,
        "NO SETUP": 0.0,
    }
    return mapping.get(confidence.upper(), 0.0)


def _grade_to_risk_percent(grade: str) -> float:
    """Map setup grade to risk percentage per Rulebook Section 6.2."""
    mapping = {
        "A+": RISK_PERCENT_A_PLUS,
        "A": RISK_PERCENT_A,
        "B": RISK_PERCENT_B,
        "REJECT": 0.0,
    }
    return mapping.get(grade, 0.0)
