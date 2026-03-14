"""Post-parse validation rules for AnalysisOutput.

Enforces Rulebook constraints that the LLM must satisfy.
Returns a list of validation error strings. Empty list = valid.
Pure functions with no I/O or side effects.
"""

from __future__ import annotations

from engine.processor.constants import (
    CONFLUENCE_REJECT_THRESHOLD,
    CONFLUENCE_SCORE_MAX,
    CONFLUENCE_SCORE_MIN,
    MAX_CITATIONS,
    MAX_EVIDENCE_ITEMS,
    MAX_REASONING_LENGTH,
    MAX_TAKE_PROFIT_LEVELS,
    MIN_RR_INTRADAY,
    MIN_RR_POSITIONAL,
    MIN_RR_SCALPING,
    MIN_RR_SWING,
)
from engine.processor.models.analysis import AnalysisOutput


def validate_analysis_output(
    output: AnalysisOutput,
    *,
    require_citations: bool = True,
) -> list[str]:
    """Run all validation rules and return error messages."""
    errors: list[str] = []

    errors.extend(_validate_identity(output))
    errors.extend(_validate_direction_consistency(output))
    errors.extend(_validate_confluence_score(output))
    errors.extend(_validate_grade_consistency(output))
    errors.extend(_validate_trade_construction(output))
    errors.extend(_validate_rr_ratio(output))
    errors.extend(_validate_proceed_consistency(output))
    errors.extend(_validate_reasoning(output))
    errors.extend(_validate_tp_structure(output))

    if require_citations:
        errors.extend(_validate_citations(output))

    return errors


def _validate_identity(o: AnalysisOutput) -> list[str]:
    errors: list[str] = []
    if not o.analysis_id:
        errors.append("analysis_id is empty")
    if not o.pair:
        errors.append("pair is empty")
    if not o.trading_style:
        errors.append("trading_style is empty")
    return errors


def _validate_direction_consistency(o: AnalysisOutput) -> list[str]:
    errors: list[str] = []
    valid_directions = {"LONG", "SHORT", "NO SETUP"}
    if o.direction not in valid_directions:
        errors.append(f"direction '{o.direction}' not in {valid_directions}")

    if o.direction == "NO SETUP":
        if o.setup_grade not in ("REJECT", "B"):
            errors.append(
                f"direction is NO SETUP but setup_grade is '{o.setup_grade}' (expected REJECT)"
            )
        if o.proceed_to_module_b == "YES":
            errors.append("direction is NO SETUP but proceed_to_module_b is YES")
    return errors


def _validate_confluence_score(o: AnalysisOutput) -> list[str]:
    errors: list[str] = []
    score = o.confluence_score.score
    if score < CONFLUENCE_SCORE_MIN or score > CONFLUENCE_SCORE_MAX:
        errors.append(
            f"confluence_score {score} outside bounds [{CONFLUENCE_SCORE_MIN}, {CONFLUENCE_SCORE_MAX}]"
        )
    return errors


def _validate_grade_consistency(o: AnalysisOutput) -> list[str]:
    errors: list[str] = []
    valid_grades = {"A+", "A", "B", "REJECT"}
    if o.setup_grade not in valid_grades:
        errors.append(f"setup_grade '{o.setup_grade}' not in {valid_grades}")

    score = o.confluence_score.score
    if score < CONFLUENCE_REJECT_THRESHOLD and o.setup_grade != "REJECT":
        errors.append(
            f"confluence_score {score} < {CONFLUENCE_REJECT_THRESHOLD} but grade is '{o.setup_grade}' (expected REJECT)"
        )
    return errors


def _validate_trade_construction(o: AnalysisOutput) -> list[str]:
    """When a trade is approved, entry/SL/TP must be populated."""
    errors: list[str] = []
    if o.direction in ("LONG", "SHORT"):
        if o.entry_zone.low is None or o.entry_zone.high is None:
            errors.append("trade approved but entry_zone has null bounds")
        if o.stop_loss.price is None:
            errors.append("trade approved but stop_loss.price is null")
        if not o.take_profits:
            errors.append("trade approved but take_profits is empty")
        if o.entry_zone.low is not None and o.entry_zone.high is not None:
            if o.entry_zone.low > o.entry_zone.high:
                errors.append(
                    f"entry_zone.low ({o.entry_zone.low}) > entry_zone.high ({o.entry_zone.high})"
                )
            if o.entry_zone.low <= 0:
                errors.append(f"entry_zone.low ({o.entry_zone.low}) must be positive")
        if o.stop_loss.price is not None and o.stop_loss.price <= 0:
            errors.append(f"stop_loss.price ({o.stop_loss.price}) must be positive")
    return errors


def _validate_rr_ratio(o: AnalysisOutput) -> list[str]:
    """R:R must meet minimum for the active trading style."""
    errors: list[str] = []
    if o.direction not in ("LONG", "SHORT"):
        return errors

    if o.rr_ratio is None:
        errors.append("trade approved but rr_ratio is null")
        return errors

    if o.rr_ratio <= 0:
        errors.append(f"rr_ratio ({o.rr_ratio}) must be positive")
        return errors

    style = o.trading_style.upper()
    min_rr_map = {
        "SCALPING": MIN_RR_SCALPING,
        "INTRADAY": MIN_RR_INTRADAY,
        "SWING": MIN_RR_SWING,
        "POSITIONAL": MIN_RR_POSITIONAL,
    }
    min_rr = min_rr_map.get(style, MIN_RR_INTRADAY)

    if o.rr_ratio < min_rr:
        errors.append(
            f"rr_ratio {o.rr_ratio} below minimum {min_rr} for style {style}"
        )
    return errors


def _validate_proceed_consistency(o: AnalysisOutput) -> list[str]:
    errors: list[str] = []
    if o.proceed_to_module_b == "YES":
        if o.setup_grade not in ("A+", "A"):
            errors.append(
                f"proceed_to_module_b is YES but grade is '{o.setup_grade}' (requires A+ or A)"
            )
        if o.direction == "NO SETUP":
            errors.append("proceed_to_module_b is YES but direction is NO SETUP")
    return errors


def _validate_reasoning(o: AnalysisOutput) -> list[str]:
    errors: list[str] = []
    if not o.explainable_reasoning:
        errors.append("explainable_reasoning is empty")
    elif len(o.explainable_reasoning) > MAX_REASONING_LENGTH:
        errors.append(
            f"explainable_reasoning exceeds {MAX_REASONING_LENGTH} chars"
        )
    return errors


def _validate_tp_structure(o: AnalysisOutput) -> list[str]:
    """TP levels must sum to 100% and not exceed max count."""
    errors: list[str] = []
    if o.direction not in ("LONG", "SHORT"):
        return errors

    if len(o.take_profits) > MAX_TAKE_PROFIT_LEVELS:
        errors.append(
            f"take_profits has {len(o.take_profits)} levels (max {MAX_TAKE_PROFIT_LEVELS})"
        )

    total_pct = sum(tp.size_pct for tp in o.take_profits)
    if o.take_profits and total_pct != 100:
        errors.append(f"take_profits size_pct sum is {total_pct} (expected 100)")

    for i, tp in enumerate(o.take_profits):
        if tp.level is not None and tp.level <= 0:
            errors.append(f"take_profits[{i}].level ({tp.level}) must be positive")
    return errors


def _validate_citations(o: AnalysisOutput) -> list[str]:
    errors: list[str] = []
    if not o.rag_sources:
        errors.append("rag_sources is empty (citations required)")
    if len(o.rag_sources) > MAX_CITATIONS:
        errors.append(
            f"rag_sources has {len(o.rag_sources)} items (max {MAX_CITATIONS})"
        )
    return errors
