"""Anthropic Claude provider."""

from __future__ import annotations

import time
from typing import Optional

import anthropic

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    LLM_REQUEST_DURATION,
    LLM_REQUEST_TOTAL,
    LLM_TOKENS_USED,
)
from engine.processor.config import ProcessorConfig
from engine.processor.constants import LLMProvider
from engine.processor.llm.client import LLMClient, LLMResponse

logger = get_logger(__name__)


class AnthropicClient(LLMClient):
    """Claude API client via the anthropic SDK."""

    PROVIDER = LLMProvider.ANTHROPIC

    def __init__(self, config: ProcessorConfig) -> None:
        self._config = config
        self._client = anthropic.AsyncAnthropic(
            api_key=config.get_active_api_key(),
            timeout=float(config.llm_timeout_seconds),
            max_retries=0,
        )

    async def call(
        self,
        *,
        system_prompt: str,
        user_message: str,
        trace_id: Optional[str] = None,
    ) -> LLMResponse:
        model = self._config.model_name
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

        self._record_metrics(model, input_tokens, output_tokens, elapsed_ms)
        self._log_completion(model, input_tokens, output_tokens, elapsed_ms, stop_reason, len(text), trace_id)

        return LLMResponse(
            text=text,
            model=model,
            provider=self.PROVIDER,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=elapsed_ms,
            stop_reason=stop_reason,
        )

    async def close(self) -> None:
        await self._client.close()

    def _record_metrics(self, model: str, inp: int, out: int, ms: float) -> None:
        LLM_REQUEST_TOTAL.labels(provider=self.PROVIDER, model=model, status="success").inc()
        LLM_REQUEST_DURATION.labels(provider=self.PROVIDER, model=model).observe(ms / 1000)
        LLM_TOKENS_USED.labels(provider=self.PROVIDER, model=model, token_type="input").inc(inp)
        LLM_TOKENS_USED.labels(provider=self.PROVIDER, model=model, token_type="output").inc(out)

    @staticmethod
    def _log_completion(model: str, inp: int, out: int, ms: float, stop: str | None, length: int, trace_id: str | None) -> None:
        logger.info(
            "llm_call_completed",
            extra={"provider": "anthropic", "model": model, "input_tokens": inp, "output_tokens": out,
                   "duration_ms": round(ms, 1), "stop_reason": stop, "response_length": length, "trace_id": trace_id},
        )
