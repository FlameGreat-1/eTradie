"""Reasoning-budget abstraction across providers.

Thinking-capable models (Gemini 2.5/3.x with native thinking,
Anthropic Opus extended thinking, OpenAI o-series) share their
``max_output_tokens`` budget between hidden reasoning tokens and the
visible response. With a heavy prompt and a strict output schema the
model can spend nearly the entire budget on thinking and emit only a
few hundred visible tokens before the provider terminates the
response with MAX_TOKENS.

Every provider exposes a knob for this but with different
semantics:

  * Gemini: ``thinking_config=ThinkingConfig(thinking_budget=N)``
            where ``N`` is a token count; ``0`` disables thinking;
            ``-1`` lets the provider decide.
  * Anthropic: ``thinking={"type": "enabled", "budget_tokens": N}``
            on supported SKUs.
  * OpenAI o-series: ``reasoning_effort: "low"|"medium"|"high"`` --
            an ordinal, not a token count.
  * Self-hosted: no standard.

The ``ReasoningBudget`` value object below is the single shape
``service.py`` and each provider implementation read from. The
provider implementations translate it into their native knob inside
their own module so the rest of the codebase never touches a
provider-specific reasoning parameter.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.processor.llm.capabilities import ModelCapabilities


@dataclass(frozen=True)
class ReasoningBudget:
    """Operator-facing reasoning budget, normalized to tokens.

    The ``effort`` field is populated only for ordinal-only providers
    (OpenAI o-series) and is derived from ``budget_tokens`` so the
    operator only ever configures one knob.
    """

    budget_tokens: int | None
    effort: str | None  # "low" | "medium" | "high" | None

    @property
    def is_active(self) -> bool:
        """True when a non-None reasoning constraint should be sent."""
        return self.budget_tokens is not None or self.effort is not None


def _budget_to_effort(budget_tokens: int) -> str:
    """Translate a token budget to OpenAI's ordinal effort scale.

    The OpenAI o-series API only accepts ``low|medium|high``. The
    mapping here is conservative: ``low`` for caps under ~4k thinking
    tokens, ``medium`` for ~4k-12k, ``high`` for above. It is
    deterministic so the operator's single knob produces consistent
    behaviour across providers without surprising drift.
    """
    if budget_tokens <= 4096:
        return "low"
    if budget_tokens <= 12288:
        return "medium"
    return "high"


def resolve_reasoning_budget(
    *,
    operator_budget_tokens: int | None,
    capabilities: ModelCapabilities,
) -> ReasoningBudget:
    """Pick the active reasoning budget for this call.

    Resolution order:
      1. Operator-supplied ``reasoning_budget_tokens`` from
         ``ProcessorConfig``. Wins if set (even to 0, which means
         "disable thinking").
      2. Capability-driven default from ``MODEL_CATALOG.group`` for
         thinking-capable models.
      3. ``None`` -- send no reasoning knob; the provider runs in its
         native default mode.

    Returns a ``ReasoningBudget`` whose fields are either both None
    (no constraint) or aligned (``budget_tokens`` set with ``effort``
    derived).
    """
    if operator_budget_tokens is not None:
        if operator_budget_tokens <= 0:
            # Operator explicitly disabled thinking.
            return ReasoningBudget(budget_tokens=0, effort="low")
        return ReasoningBudget(
            budget_tokens=operator_budget_tokens,
            effort=_budget_to_effort(operator_budget_tokens),
        )

    if capabilities.is_thinking and capabilities.default_reasoning_budget_tokens is not None:
        default = capabilities.default_reasoning_budget_tokens
        return ReasoningBudget(
            budget_tokens=default,
            effort=_budget_to_effort(default),
        )

    return ReasoningBudget(budget_tokens=None, effort=None)
