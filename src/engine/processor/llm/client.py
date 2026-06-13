"""Abstract LLM client interface and response model.

The processor depends on this abstract interface, NOT on any
concrete provider. Concrete implementations live in llm/providers/.
This follows the Dependency Inversion Principle.

Structured-output contract:

    Every provider implementation supports a native schema-
    enforcement knob (OpenAI ``response_format=json_schema``,
    Gemini ``response_schema``, Anthropic forced ``tool_choice``,
    self-hosted OpenAI-compatible ``response_format``). Historically
    that knob was always engaged for the ``AnalysisOutput`` schema
    owned by the analysis processor.

    The ``use_structured_output`` parameter on ``call()`` and
    ``stream_call()`` lets a non-analysis caller (Trading Plan
    generator, Performance Review generator, future workbook
    generators) opt out of that enforcement. When False the
    provider sends a plain text/JSON completion request and trusts
    the caller's system prompt to define the response schema. The
    provider does not inspect, validate, or coerce the response
    shape on this path.

    Default is True so the analysis processor (and any external
    caller that already worked) keeps its strict-JSON guarantee
    byte-for-byte. Only callers that own a different wire schema
    should pass False.
"""

from __future__ import annotations

import abc
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMResponse:
    """Raw response from any LLM API call."""

    text: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    duration_ms: float
    stop_reason: str | None = None


class LLMClient(abc.ABC):
    """Abstract interface for LLM providers.

    Every provider (Anthropic, OpenAI, Gemini, self-hosted)
    implements this interface. The processor service and retry
    logic depend only on this abstraction.
    """

    @abc.abstractmethod
    async def call(
        self,
        *,
        system_prompt: str,
        user_message: str,
        trace_id: str | None = None,
        use_structured_output: bool = True,
    ) -> LLMResponse:
        """Send a prompt and return the raw response.

        Args:
            system_prompt: The system message defining LLM behavior.
            user_message: The user message with context payload.
            trace_id: Distributed trace ID for correlation.
            use_structured_output: When True (default), the provider
                applies its native schema-enforcement knob configured
                for ``AnalysisOutput``. When False, the provider
                sends a plain text-completion request and the caller's
                system prompt is the sole authority on the response
                schema. Non-analysis callers MUST pass False; passing
                True from a Trading Plan or Performance Review path
                will force the model to emit an ``AnalysisOutput``
                JSON object regardless of what the prompt asks for.

        Returns:
            LLMResponse with raw text and token counts.

        Raises:
            Any provider-specific exception (handled by retry layer).
        """
        ...

    @abc.abstractmethod
    async def stream_call(
        self,
        *,
        system_prompt: str,
        user_message: str,
        trace_id: str | None = None,
        usage_out: dict[str, Any] | None = None,
        use_structured_output: bool = True,
    ) -> AsyncGenerator[str, None]:
        """Send a prompt and yield the raw text chunks as they arrive.

        Args:
            system_prompt: The system message defining LLM behavior.
            user_message: The user message with context payload.
            trace_id: Distributed trace ID for correlation.
            usage_out: Optional mutable dict the provider populates
                with ``input_tokens`` / ``output_tokens`` / ``finish_reason``
                from the stream's usage metadata.
            use_structured_output: Same semantics as ``call()``. The
                analysis path (which is the only current ``stream_call``
                consumer) keeps the default True so SSE consumers
                continue to see grammar-constrained partial JSON.

        Yields:
            str: Token chunks from the provider.
        """
        yield ""

    @abc.abstractmethod
    async def close(self) -> None:
        """Release provider resources (HTTP connections, etc.)."""
        ...
