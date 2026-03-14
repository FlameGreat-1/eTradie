"""Abstract LLM client interface and response model.

The processor depends on this abstract interface, NOT on any
concrete provider. Concrete implementations live in llm/providers/.
This follows the Dependency Inversion Principle.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LLMResponse:
    """Raw response from any LLM API call."""

    text: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    duration_ms: float
    stop_reason: Optional[str] = None


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
        trace_id: Optional[str] = None,
    ) -> LLMResponse:
        """Send a prompt and return the raw response.

        Args:
            system_prompt: The system message defining LLM behavior.
            user_message: The user message with context payload.
            trace_id: Distributed trace ID for correlation.

        Returns:
            LLMResponse with raw text and token counts.

        Raises:
            Any provider-specific exception (handled by retry layer).
        """
        ...

    @abc.abstractmethod
    async def close(self) -> None:
        """Release provider resources (HTTP connections, etc.)."""
        ...
