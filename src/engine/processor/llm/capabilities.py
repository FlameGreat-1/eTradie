"""Per-(provider, model) capability lookup.

Every decision in the LLM layer that depends on which model is being
called flows through this module. There are no hardcoded model-name
string matches anywhere else; the ``MODEL_CATALOG`` defined in
``constants.py`` is the single source of truth for which models are
thinking-capable, which support native structured output, and what
default reasoning budget to use when the operator has not set one.

This indirection is the reason we can support arbitrary user-supplied
model strings (per ``ProcessorConfig.model_name``) without breaking:
an unknown model falls back to a permissive default profile that
works via the existing free-text path.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.processor.constants import MODEL_CATALOG, LLMProvider


@dataclass(frozen=True)
class ModelCapabilities:
    """What a particular (provider, model) supports.

    Attributes:
        provider: One of ``LLMProvider`` values. Drives which native
            structured-output knob is used.
        model_id: The model id as it appears on the provider API.
        group: ``MODEL_CATALOG`` group label
            (``thinking|pro|balanced|flash|efficient|legacy|unknown``).
        supports_structured_output: True when the provider+model
            accepts a native schema-enforcement parameter on the
            chat/generate call. Self-hosted defaults to False because
            implementations vary; the openai-compatible client probes
            per-call and falls back transparently.
        is_thinking: True for models that share ``max_output_tokens``
            between hidden reasoning and visible output (Gemini
            thinking/pro, Anthropic Opus with extended thinking,
            OpenAI o-series). Drives whether a reasoning-budget knob
            is meaningful.
        default_reasoning_budget_tokens: Suggested cap on hidden
            reasoning tokens when the operator has not explicitly
            set ``ProcessorConfig.reasoning_budget_tokens``. Sized
            so visible output has room to land inside
            ``max_output_tokens=32768`` for the standard prompt (the
            production default; see ``config.py``).
    """

    provider: str
    model_id: str
    group: str
    supports_structured_output: bool
    is_thinking: bool
    default_reasoning_budget_tokens: int | None


# Provider-level baseline: when the (provider, model) is not present
# in MODEL_CATALOG we assume the same defaults as the catalog's most
# common group for that provider. This keeps unknown user-supplied
# model strings working through the free-text fallback path.
_PROVIDER_SUPPORTS_STRUCTURED_OUTPUT: dict[str, bool] = {
    LLMProvider.ANTHROPIC: True,
    LLMProvider.OPENAI: True,
    LLMProvider.GEMINI: True,
    # Self-hosted endpoints vary: vLLM has guided_json, Ollama has
    # ``format``, LM Studio supports ``response_format`` on recent
    # builds, llama.cpp has nothing. Default False; the openai-
    # compatible client probes per-call and falls back transparently.
    LLMProvider.SELF_HOSTED: False,
}

_GROUP_DEFAULT_REASONING_BUDGET: dict[str, int | None] = {
    # Heavy-reasoning groups: capability-driven fallback used when the
    # operator has NOT set ProcessorConfig.reasoning_budget_tokens.
    # 12288 matches the operator default in config.py so both layers
    # agree on one number, and it sits at the OpenAI o-series
    # reasoning_effort='medium' boundary (<=12288 -> medium,
    # >12288 -> high) per reasoning.py's ordinal translator. A caller
    # that bypasses the operator default still gets 'medium' on
    # o-series, not 'high' -- preserves intent across both layers.
    #
    # The current max_output_tokens default is 32768 (see config.py),
    # leaving ~20480 for visible output after this 12288 thinking
    # budget. Several multiples of the real p99 visible output.
    #
    # If more thinking room is wanted in production, raise the
    # operator default in config.py rather than this fallback; the
    # operator value wins per resolve_reasoning_budget's resolution
    # order. Leaving the fallback at the medium boundary keeps a
    # caller that explicitly drops the operator knob from silently
    # upgrading to 'high'.
    "thinking": 12288,
    "pro": 12288,
    # Balanced / non-thinking-by-default groups: no reasoning cap is
    # applied; the provider runs in its native mode.
    "balanced": None,
    "flash": None,
    "efficient": None,
    "legacy": None,
    "unknown": None,
}

_THINKING_GROUPS = {"thinking", "pro"}


def get_model_capabilities(provider: str, model_id: str) -> ModelCapabilities:
    """Look up capabilities for a (provider, model).

    Args:
        provider: One of the ``LLMProvider`` string values.
        model_id: The model id the user picked from the dashboard
            (or the platform default). Arbitrary strings are tolerated.

    Returns:
        A populated ``ModelCapabilities``. Unknown models fall back to
        a permissive default that still works through the existing
        free-text path.
    """
    for entry in MODEL_CATALOG:
        if entry["provider"] == provider and entry["id"] == model_id:
            group = entry["group"]
            return ModelCapabilities(
                provider=provider,
                model_id=model_id,
                group=group,
                supports_structured_output=_PROVIDER_SUPPORTS_STRUCTURED_OUTPUT.get(provider, False),
                is_thinking=group in _THINKING_GROUPS,
                default_reasoning_budget_tokens=_GROUP_DEFAULT_REASONING_BUDGET.get(group),
            )

    return ModelCapabilities(
        provider=provider,
        model_id=model_id,
        group="unknown",
        supports_structured_output=_PROVIDER_SUPPORTS_STRUCTURED_OUTPUT.get(provider, False),
        is_thinking=False,
        default_reasoning_budget_tokens=None,
    )
