"""Parse raw LLM JSON text into the canonical AnalysisOutput model.

Handles JSON extraction from potentially noisy LLM output,
Pydantic validation, and error recovery. Records parse metrics
via shared Prometheus counters.
"""

from __future__ import annotations

import re
from typing import Optional

import orjson
from pydantic import ValidationError

from engine.shared.exceptions import ProcessorError
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    TRADE_PLAN_GENERATED_TOTAL,
    TRADE_PLAN_VALIDATION_FAILURES,
)
from engine.processor.constants import MAX_LLM_RESPONSE_LENGTH
from engine.processor.models.analysis import AnalysisOutput
from engine.processor.parsing.validators import validate_analysis_output

logger = get_logger(__name__)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(\{.*?})\s*```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"(\{.*})", re.DOTALL)


def parse_llm_response(
    raw_text: str,
    *,
    require_citations: bool = True,
    trace_id: Optional[str] = None,
) -> tuple[AnalysisOutput, list[str]]:
    """Parse raw LLM text into AnalysisOutput.

    Args:
        raw_text: Raw text response from the LLM.
        require_citations: Whether to enforce citation presence.
        trace_id: Distributed trace ID for correlation.

    Returns:
        Tuple of (parsed AnalysisOutput, list of validation warnings).
        Warnings are non-fatal issues that were auto-corrected or noted.

    Raises:
        ProcessorError: On unrecoverable parse or validation failure.
    """
    if not raw_text or not raw_text.strip():
        TRADE_PLAN_GENERATED_TOTAL.labels(status="parse_error").inc()
        raise ProcessorError(
            "LLM returned empty response",
            details={"trace_id": trace_id},
        )

    if len(raw_text) > MAX_LLM_RESPONSE_LENGTH:
        TRADE_PLAN_GENERATED_TOTAL.labels(status="parse_error").inc()
        raise ProcessorError(
            f"LLM response exceeds {MAX_LLM_RESPONSE_LENGTH} chars ({len(raw_text)})",
            details={"response_length": len(raw_text), "trace_id": trace_id},
        )

    json_str = _extract_json(raw_text)

    try:
        raw_dict = orjson.loads(json_str)
    except (orjson.JSONDecodeError, ValueError) as exc:
        TRADE_PLAN_GENERATED_TOTAL.labels(status="parse_error").inc()
        raise ProcessorError(
            f"Failed to parse LLM JSON: {exc}",
            details={"trace_id": trace_id, "raw_preview": raw_text[:500]},
        ) from exc

    if not isinstance(raw_dict, dict):
        TRADE_PLAN_GENERATED_TOTAL.labels(status="parse_error").inc()
        raise ProcessorError(
            f"LLM response is not a JSON object (got {type(raw_dict).__name__})",
            details={"trace_id": trace_id},
        )

    try:
        output = AnalysisOutput.model_validate(raw_dict)
    except ValidationError as exc:
        TRADE_PLAN_GENERATED_TOTAL.labels(status="validation_error").inc()
        error_details = []
        for err in exc.errors():
            loc = ".".join(str(l) for l in err["loc"])
            error_details.append(f"{loc}: {err['msg']}")
            TRADE_PLAN_VALIDATION_FAILURES.labels(rule=f"schema_{loc}").inc()

        raise ProcessorError(
            f"LLM response failed schema validation: {'; '.join(error_details[:5])}",
            details={
                "validation_errors": error_details,
                "trace_id": trace_id,
            },
        ) from exc

    validation_errors = validate_analysis_output(
        output, require_citations=require_citations,
    )

    warnings: list[str] = []
    fatal_errors: list[str] = []

    for err in validation_errors:
        TRADE_PLAN_VALIDATION_FAILURES.labels(rule=_error_to_rule(err)).inc()
        if _is_fatal_validation_error(err):
            fatal_errors.append(err)
        else:
            warnings.append(err)

    if fatal_errors:
        TRADE_PLAN_GENERATED_TOTAL.labels(status="validation_error").inc()
        raise ProcessorError(
            f"Analysis output failed validation: {'; '.join(fatal_errors[:5])}",
            details={
                "fatal_errors": fatal_errors,
                "warnings": warnings,
                "trace_id": trace_id,
            },
        )

    status = "no_setup" if output.direction == "NO SETUP" else "success"
    TRADE_PLAN_GENERATED_TOTAL.labels(status=status).inc()

    logger.info(
        "llm_response_parsed",
        extra={
            "analysis_id": output.analysis_id,
            "pair": output.pair,
            "direction": output.direction,
            "grade": output.setup_grade,
            "score": output.confluence_score.score,
            "warnings_count": len(warnings),
            "trace_id": trace_id,
        },
    )

    return output, warnings


def _extract_json(raw_text: str) -> str:
    """Extract JSON object from potentially noisy LLM output.

    Tries in order:
    1. Direct parse (clean JSON)
    2. Markdown code block extraction
    3. First { to last } extraction
    """
    stripped = raw_text.strip()

    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    match = _JSON_BLOCK_RE.search(stripped)
    if match:
        return match.group(1).strip()

    match = _JSON_OBJECT_RE.search(stripped)
    if match:
        return match.group(1).strip()

    return stripped


def _is_fatal_validation_error(error: str) -> bool:
    """Determine if a validation error is fatal (blocks processing)."""
    fatal_patterns = [
        "analysis_id is empty",
        "pair is empty",
        "direction",
        "entry_zone has null bounds",
        "stop_loss.price is null",
        "take_profits is empty",
        "rr_ratio is null",
        "proceed_to_module_b is YES but",
    ]
    error_lower = error.lower()
    return any(p.lower() in error_lower for p in fatal_patterns)


def _error_to_rule(error: str) -> str:
    """Convert a validation error message to a short rule label for metrics."""
    if "confluence_score" in error:
        return "confluence_score_bounds"
    if "rr_ratio" in error:
        return "rr_ratio_minimum"
    if "entry_zone" in error:
        return "entry_zone_invalid"
    if "stop_loss" in error:
        return "stop_loss_invalid"
    if "take_profits" in error:
        return "take_profits_invalid"
    if "direction" in error:
        return "direction_consistency"
    if "grade" in error or "setup_grade" in error:
        return "grade_consistency"
    if "proceed" in error:
        return "proceed_consistency"
    if "rag_sources" in error or "citation" in error:
        return "citations_missing"
    if "reasoning" in error:
        return "reasoning_invalid"
    return "other"
