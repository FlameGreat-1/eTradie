"""Provider-native JSON schema compilation from ``AnalysisOutput``.

Pydantic's ``model_json_schema()`` emits draft-07 with ``$ref`` and
``$defs``. Each LLM provider accepts a different subset:

  * Gemini ``response_schema``: a subset of OpenAPI 3.0. No ``$ref``,
    no ``$defs`` -- everything must be inlined. ``Optional[X]`` must
    be expressed via ``nullable: true``. ``additionalProperties`` is
    not honoured.

  * OpenAI ``response_format={"type": "json_schema", "strict": true}``:
    standard JSON Schema with constraints. Every property must be
    listed in ``required``; ``additionalProperties`` must be
    explicitly ``false``.

  * Anthropic ``tools[].input_schema``: standard JSON Schema. ``$ref``
    is allowed. ``additionalProperties`` defaults work fine.

This module is the single place where the schema-shape differences
are absorbed. The compiled schema is cached per provider at module
load to amortise the cost across every analysis cycle.

The ``AnalysisOutput`` Pydantic model in ``models/analysis.py`` is the
single source of truth. Nothing here mutates it. We only read from
its ``.model_json_schema()`` output.
"""
from __future__ import annotations

import copy
from functools import lru_cache
from typing import Any

from engine.processor.constants import LLMProvider
from engine.processor.models.analysis import AnalysisOutput

_PROVIDER_GEMINI = LLMProvider.GEMINI
_PROVIDER_OPENAI = LLMProvider.OPENAI
_PROVIDER_ANTHROPIC = LLMProvider.ANTHROPIC
_PROVIDER_SELF_HOSTED = LLMProvider.SELF_HOSTED

# Maximum schema depth Gemini accepts before refusing the request.
# The AnalysisOutput nesting is well under this; we validate anyway
# so a future field addition that explodes nesting fails CI not prod.
_MAX_SCHEMA_DEPTH = 12


def _measure_depth(node: Any, depth: int = 0) -> int:
    """Maximum nesting depth of a JSON Schema fragment."""
    if not isinstance(node, dict):
        return depth
    deepest = depth
    for key in ("properties", "items", "allOf", "anyOf", "oneOf"):
        if key in node:
            child = node[key]
            if isinstance(child, dict):
                deepest = max(deepest, _measure_depth(child, depth + 1))
            elif isinstance(child, list):
                for item in child:
                    deepest = max(deepest, _measure_depth(item, depth + 1))
    return deepest


def _inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve every ``$ref`` against ``$defs`` and inline it.

    Pydantic emits ``{"$ref": "#/$defs/SomeModel"}`` for nested
    models. Gemini refuses ``$ref`` outright, so we walk the tree
    once at compile time and substitute the referenced fragment in
    place. The resulting schema has no ``$defs`` / no ``$ref`` and is
    safe to send to any provider.
    """
    defs = schema.get("$defs", {})

    def _resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node and len(node) == 1:
                ref = node["$ref"]
                if not ref.startswith("#/$defs/"):
                    return node
                name = ref[len("#/$defs/") :]
                target = defs.get(name)
                if target is None:
                    return node
                return _resolve(copy.deepcopy(target))
            return {k: _resolve(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [_resolve(item) for item in node]
        return node

    inlined = _resolve(schema)
    if isinstance(inlined, dict) and "$defs" in inlined:
        inlined.pop("$defs", None)
    return inlined


def _normalize_optional_to_nullable(node: Any) -> Any:
    """Rewrite ``anyOf: [{type: X}, {type: "null"}]`` to ``{type: X, nullable: true}``.

    Pydantic encodes ``Optional[X]`` as a two-element ``anyOf``
    containing the concrete type and ``null``. Gemini does not
    understand ``anyOf`` reliably; it expects the OpenAPI-style
    ``nullable: true`` flag. We canonicalise to the OpenAPI form
    which Gemini accepts and which OpenAI/Anthropic also tolerate.
    """
    if isinstance(node, dict):
        any_of = node.get("anyOf")
        if isinstance(any_of, list) and len(any_of) == 2:
            non_null = [s for s in any_of if isinstance(s, dict) and s.get("type") != "null"]
            has_null = any(isinstance(s, dict) and s.get("type") == "null" for s in any_of)
            if len(non_null) == 1 and has_null:
                inner = copy.deepcopy(non_null[0])
                inner["nullable"] = True
                merged = {k: v for k, v in node.items() if k != "anyOf"}
                merged.update(inner)
                return {k: _normalize_optional_to_nullable(v) for k, v in merged.items()}
        return {k: _normalize_optional_to_nullable(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_normalize_optional_to_nullable(item) for item in node]
    return node


def _strip_metadata(node: Any) -> Any:
    """Remove keys that add no semantic value at the provider boundary.

    ``title`` is always derived from the class name and adds no
    semantic value. ``description`` is kept because it materially
    helps the model pick the right enum value.
    """
    if isinstance(node, dict):
        return {k: _strip_metadata(v) for k, v in node.items() if k != "title"}
    if isinstance(node, list):
        return [_strip_metadata(item) for item in node]
    return node


def _force_required_and_no_additional(node: Any) -> Any:
    """OpenAI strict mode: every property must be in ``required`` and
    ``additionalProperties`` must be ``false``.

    Applied only when compiling for OpenAI. Destructive on
    ``required`` (overwrites any partial list) which is exactly what
    strict mode demands.
    """
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            node = dict(node)
            node["required"] = list(node["properties"].keys())
            node["additionalProperties"] = False
        return {k: _force_required_and_no_additional(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_force_required_and_no_additional(item) for item in node]
    return node


def _drop_additional_properties(node: Any) -> Any:
    """Strip ``additionalProperties`` entries. Used for Gemini."""
    if isinstance(node, dict):
        return {k: _drop_additional_properties(v) for k, v in node.items() if k != "additionalProperties"}
    if isinstance(node, list):
        return [_drop_additional_properties(item) for item in node]
    return node


def _base_schema() -> dict[str, Any]:
    """Inline + Optional-normalise the AnalysisOutput schema.

    Produced once and reused across providers. Each provider then
    applies its own final pass to the deepcopy of this base.
    """
    raw = AnalysisOutput.model_json_schema()
    inlined = _inline_refs(raw)
    normalised = _normalize_optional_to_nullable(inlined)
    stripped = _strip_metadata(normalised)
    depth = _measure_depth(stripped)
    if depth > _MAX_SCHEMA_DEPTH:
        raise ValueError(
            f"AnalysisOutput schema nesting depth {depth} exceeds the "
            f"safe provider limit of {_MAX_SCHEMA_DEPTH}. Flatten a "
            f"nested model before adding more layers."
        )
    return stripped


@lru_cache(maxsize=1)
def compile_for_gemini() -> dict[str, Any]:
    """Schema shape Gemini's ``response_schema`` accepts.

    Returned as a dict so the schema is identical across google-genai
    SDK versions and so we can post-process it (strip
    ``additionalProperties`` which Gemini ignores).
    """
    schema = copy.deepcopy(_base_schema())
    return _drop_additional_properties(schema)


@lru_cache(maxsize=1)
def compile_for_openai() -> dict[str, Any]:
    """Schema shape OpenAI ``response_format`` (strict) accepts.

    Strict mode requires every property in ``required`` and
    ``additionalProperties: false`` at every level.
    """
    schema = copy.deepcopy(_base_schema())
    return _force_required_and_no_additional(schema)


@lru_cache(maxsize=1)
def compile_for_anthropic() -> dict[str, Any]:
    """Schema shape Anthropic ``tools[].input_schema`` accepts."""
    return copy.deepcopy(_base_schema())


@lru_cache(maxsize=1)
def compile_for_openai_compatible() -> dict[str, Any]:
    """Schema shape self-hosted OpenAI-compatible endpoints accept.

    vLLM (guided_json), LM Studio, and recent text-generation-inference
    builds accept the same shape OpenAI does but typically without
    strict-mode enforcement. We send the unmodified base schema so it
    works on the widest set of backends; servers that don't accept
    structured output will raise and the caller falls back to the
    hardened free-text parser.
    """
    return copy.deepcopy(_base_schema())


def compile_schema(provider: str) -> dict[str, Any]:
    """Return the cached, provider-shaped schema for ``AnalysisOutput``.

    Args:
        provider: One of the ``LLMProvider`` string values.

    Raises:
        ValueError: For an unknown provider. Callers can also catch
            this and fall back to the free-text path.
    """
    if provider == _PROVIDER_GEMINI:
        return compile_for_gemini()
    if provider == _PROVIDER_OPENAI:
        return compile_for_openai()
    if provider == _PROVIDER_ANTHROPIC:
        return compile_for_anthropic()
    if provider == _PROVIDER_SELF_HOSTED:
        return compile_for_openai_compatible()
    raise ValueError(f"Unknown provider for schema compilation: {provider!r}")
