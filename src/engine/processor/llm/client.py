"""Anthropic Claude API client.

Sends the system prompt + user message to Claude and returns the
raw text response. Tracks tokens, latency, and errors via the
shared Prometheus metrics already defined in shared/metrics/prometheus.py.

This client is stateless. Configuration and retry logic are injected.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import anthropic

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    LLM_REQUEST_DURATION,
    LLM_REQUEST_TOTAL,
    LLM_TOKENS_USED,
)
from engine.processor.config import ProcessorConfig
from engine.processor.constants import LLM_PROVIDER
from engine.processor.llm.retry import retry_llm_call

logger = get_logger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    """Raw response from the LLM API call."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: float
    stop_reason: Optional[str] = None


class AnthropicClient:
    """Stateless Claude API client."""

    def __init__(self, config: ProcessorConfig) -> None:
        self._config = config
        self._client = anthropic.AsyncAnthropic(
            api_key=config.anthropic_api_key.get_secret_value(),
            timeout=float(config.llm_timeout_seconds),
            max_retries=0,  # retries handled by our retry_llm_call
        )

    async def call(
        self,
        *,
        system_prompt: str,
        user_message: str,
        trace_id: Optional[str] = None,
    ) -> LLMResponse:
        """Send a prompt to Claude and return the raw response.

        Retry logic wraps the actual API call. Metrics are recorded
        for every attempt (success or failure) via the retry layer
        and here on success.

        Args:
            system_prompt: The system message defining LLM behavior.
            user_message: The user message with context payload.
            trace_id: Distributed trace ID for correlation.

        Returns:
            LLMResponse with raw text and token counts.

        Raises:
            ProcessorError: On all failures after retries exhausted.
        """
        model = self._config.model_name

        async def _do_call() -> LLMResponse:
            start = time.monotonic()

            response = await self._client.messages.create(
                model=model,
                max_tokens=self._config.max_output_tokens,
                temperature=self._config.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            elapsed_ms = (time.monotonic() - start) * 1000

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            text = response.content[0].text if response.content else ""
            stop_reason = response.stop_reason

            LLM_REQUEST_TOTAL.labels(
                provider=LLM_PROVIDER, model=model, status="success",
            ).inc()
            LLM_REQUEST_DURATION.labels(
                provider=LLM_PROVIDER, model=model,
            ).observe(elapsed_ms / 1000)
            LLM_TOKENS_USED.labels(
                provider=LLM_PROVIDER, model=model, token_type="input",
            ).inc(input_tokens)
            LLM_TOKENS_USED.labels(
                provider=LLM_PROVIDER, model=model, token_type="output",
            ).inc(output_tokens)

            logger.info(
                "llm_call_completed",
                extra={
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "duration_ms": round(elapsed_ms, 1),
                    "stop_reason": stop_reason,
                    "response_length": len(text),
                    "trace_id": trace_id,
                },
            )

            return LLMResponse(
                text=text,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=elapsed_ms,
                stop_reason=stop_reason,
            )

        return await retry_llm_call(
            _do_call,
            config=self._config,
            trace_id=trace_id,
        )
