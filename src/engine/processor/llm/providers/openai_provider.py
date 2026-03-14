"""OpenAI GPT provider."""

from __future__ import annotations

import time
from typing import Optional

import openai

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


class OpenAIClient(LLMClient):
    """OpenAI GPT client via the openai SDK."""

    PROVIDER = LLMProvider.OPENAI

    def __init__(self, config: ProcessorConfig) -> None:
        self._config = config
        self._client = openai.AsyncOpenAI(
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

        response = await self._client.chat.completions.create(
            model=model,
            max_tokens=self._config.max_output_tokens,
            temperature=self._config.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        elapsed_ms = (time.monotonic() - start) * 1000
        choice = response.choices[0] if response.choices else None
        text = choice.message.content or "" if choice else ""
        stop_reason = choice.finish_reason if choice else None
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        self._record_metrics(model, input_tokens, output_tokens, elapsed_ms)
        logger.info(
            "llm_call_completed",
            extra={"provider": "openai", "model": model, "input_tokens": input_tokens, "output_tokens": output_tokens,
                   "duration_ms": round(elapsed_ms, 1), "stop_reason": stop_reason, "response_length": len(text), "trace_id": trace_id},
        )

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
