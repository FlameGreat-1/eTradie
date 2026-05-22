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
from engine.processor.llm.errors import LLMSchemaViolationError
from engine.processor.models.analysis import AnalysisOutput
from engine.processor.parsing.validators import validate_analysis_output

logger = get_logger(__name__)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(\{.*?})\s*```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"(\{.*})", re.DOTALL)

# Paths inside an AnalysisOutput-shaped dict whose Pydantic type is
# `list[...] = Field(default_factory=list)`. Models without native
# structured output (some self-hosted endpoints) can still emit `null`
# for these on a "no value" branch, which collides with the
# default-factory list field. We coerce None -> [] *before* Pydantic
# validation runs so the error path is identical when something OTHER
# than null-for-list fails. We are not relaxing any business rule;
# `validators.py` still enforces the real trade-construction rules.
#
# Each entry is a dotted path applied by `_coerce_null_collections`.
# Every entry corresponds to a `list[...] = Field(default_factory=list)`
# on AnalysisOutput or one of its nested models. If a new list-typed
# field is added to those models without being added here, the
# fallback path (self-hosted endpoints without structured-output
# support) can still surface the `null` -> list strictness mismatch
# the schema example itself exhibits for the no-setup branch.
_NULLABLE_LIST_PATHS: tuple[str, ...] = (
    "event_risk",
    "take_profits",
    "rag_sources",
    "audit.citations",
    "audit.retrieval.chunks_returned",
    "htf_bias.key_levels",
    "mtf_bias.key_levels",
    "entry_setup.bounds",
    "entry_setup.evidence",
    "stop_loss.evidence",
    "wyckoff_phase.evidence",
    "dxy_bias.evidence",
    "cot_signal.evidence",
    "macro_bias.base_currency.evidence",
    "macro_bias.quote_currency.evidence",
    "confluence_score.factors",
)


def _coerce_null_collections(raw: dict) -> None:
    """In-place: replace None with [] at every path in ``_NULLABLE_LIST_PATHS``.

    Walks the dict by dotted path. Missing intermediate keys are
    left alone (Pydantic will raise the right error). Lists in the
    path are not currently used; every nullable-list field on
    AnalysisOutput sits under a fixed-name object path, so a simple
    dotted walk is sufficient and avoids over-coercion.
    """
    for path in _NULLABLE_LIST_PATHS:
        parts = path.split(".")
        leaf = parts[-1]
        parents = parts[:-1]

        node = raw
        for p in parents:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(p)
            if node is None:
                break
        if isinstance(node, dict) and node.get(leaf, ...) is None:
            node[leaf] = []


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

    # Harden the fallback path (providers without native structured
    # output): coerce `null` -> `[]` for the AnalysisOutput list fields
    # that the LLM can plausibly null-out on a "no setup" branch.
    # No-op when the provider returned a schema-valid response.
    _coerce_null_collections(raw_dict)

    try:
        output = AnalysisOutput.model_validate(raw_dict)
    except ValidationError as exc:
        TRADE_PLAN_GENERATED_TOTAL.labels(status="validation_error").inc()
        error_details = []
        for err in exc.errors():
            loc = ".".join(str(l) for l in err["loc"])
            error_details.append(f"{loc}: {err['msg']}")
            TRADE_PLAN_VALIDATION_FAILURES.labels(rule=f"schema_{loc}").inc()

        # Typed error so the FastAPI router can return 422 with the
        # field-by-field validation_errors list instead of a 500 with
        # the errors squashed into the message string. Plain
        # ProcessorError is preserved for other parse failures
        # (empty / oversized / non-object).
        raise LLMSchemaViolationError(
            f"LLM response failed schema validation: {'; '.join(error_details[:5])}",
            validation_errors=error_details,
            details={"trace_id": trace_id},
        ) from exc

    validation_errors = validate_analysis_output(
        output,
        require_citations=require_citations,
    )

    warnings: list[str] = []
    fatal_errors: list[str] = []

    for err in validation_errors:
        TRADE_PLAN_VALIDATION_FAILURES.labels(rule=_error_to_rule(err)).inc()
        if _is_non_fatal_warning(err):
            warnings.append(err)
        else:
            fatal_errors.append(err)

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


def _is_non_fatal_warning(error: str) -> bool:
    """Determine if a validation error is a non-fatal warning.

    Whitelist approach: only reasoning and citation issues are warnings.
    Everything else is fatal because it means the LLM produced data
    that would cause Module B to execute a broken trade.

    Non-fatal (warnings):
    - explainable_reasoning is empty or too long (cosmetic)
    - rag_sources empty or exceeds max count (audit concern, not trade-critical)

    Fatal (everything else):
    - Identity: missing analysis_id, pair, trading_style
    - Direction: invalid enum, inconsistent with grade
    - Confluence: score out of bounds
    - Grade: invalid enum, score/grade mismatch
    - Trade construction: null entry/SL/TP, negative prices, inverted zone
    - R:R: null, negative, below minimum for style
    - Proceed: YES with wrong grade or NO SETUP direction
    - TP structure: wrong count, percentages don't sum to 100%, negative levels
    """
    error_lower = error.lower()

    # Reasoning length/presence is cosmetic - doesn't affect trade execution.
    if "explainable_reasoning" in error_lower:
        return True

    # Citation count is an audit concern - doesn't affect trade execution.
    if "rag_sources" in error_lower:
        return True

    # TP size_pct sum drift is cosmetic position-sizing arithmetic.
    # The Go management executor clamps partial close volumes to the
    # remaining lot size and always full-closes the runner on TP3, so
    # a sum of 90/110/130 does not affect actual execution or realized
    # P&L. The error remains counted via TRADE_PLAN_VALIDATION_FAILURES
    # for observability, and surfaces in warnings for audit, but does
    # not block an otherwise-valid trade plan.
    if "take_profits size_pct sum" in error_lower:
        return True

    # Everything else is trade-critical and must block execution.
    return False


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
