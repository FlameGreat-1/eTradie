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
from typing import Optional

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
            ``max_output_tokens=16384`` for the standard prompt.
    """

    provider: str
    model_id: str
    group: str
    supports_structured_output: bool
    is_thinking: bool
    default_reasoning_budget_tokens: Optional[int]


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

_GROUP_DEFAULT_REASONING_BUDGET: dict[str, Optional[int]] = {
    # Heavy-reasoning groups: cap thinking at ~50% of a 16k
    # max_output_tokens so visible output has the other 50%. The
    # operator can override via ProcessorConfig.reasoning_budget_tokens.
    "thinking": 8192,
    "pro": 8192,
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
                supports_structured_output=_PROVIDER_SUPPORTS_STRUCTURED_OUTPUT.get(
                    provider, False
                ),
                is_thinking=group in _THINKING_GROUPS,
                default_reasoning_budget_tokens=_GROUP_DEFAULT_REASONING_BUDGET.get(
                    group
                ),
            )

    return ModelCapabilities(
        provider=provider,
        model_id=model_id,
        group="unknown",
        supports_structured_output=_PROVIDER_SUPPORTS_STRUCTURED_OUTPUT.get(
            provider, False
        ),
        is_thinking=False,
        default_reasoning_budget_tokens=None,
    )
