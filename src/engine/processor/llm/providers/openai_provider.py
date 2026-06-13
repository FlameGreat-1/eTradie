"""OpenAI GPT provider.

Decision-path uses the existing ``stream_call`` so the dashboard SSE
feed shape is preserved. Two production knobs are added without
changing the call shape:

  * ``response_format={'type': 'json_schema', 'json_schema': {...,
    'strict': true}}`` -- OpenAI's grammar-constrained JSON. Strict
    mode requires every property in ``required`` and
    ``additionalProperties=false`` everywhere; the schema compiler
    handles both transparently.

  * ``reasoning_effort`` (``low|medium|high``) -- only sent for
    o-series reasoning models (capability flag
    ``is_thinking=True``).
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from typing import Any

import openai

from engine.processor.config import ProcessorConfig
from engine.processor.constants import LLMProvider
from engine.processor.llm.capabilities import get_model_capabilities
from engine.processor.llm.client import LLMClient, LLMResponse
from engine.processor.llm.errors import (
    LLMRateLimitedError,
    LLMSafetyFilterError,
    LLMTransientError,
)
from engine.processor.llm.reasoning import resolve_reasoning_budget
from engine.processor.llm.schema_compiler import compile_for_openai
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    LLM_REQUEST_DURATION,
    LLM_REQUEST_TOTAL,
    LLM_TOKENS_USED,
)

logger = get_logger(__name__)

_RESPONSE_FORMAT_NAME = "AnalysisOutput"


def _translate_provider_error(exc: Exception) -> Exception:
    """Map an openai-sdk exception to a typed LLMError when possible."""
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "ratelimit" in name or "429" in msg or "rate limit" in msg:
        return LLMRateLimitedError(str(exc))
    if "content_policy" in msg or "safety" in msg or "policy violation" in msg:
        return LLMSafetyFilterError(str(exc))
    if "timeout" in name or "timeout" in msg or "connection" in msg or "unavailable" in msg or "internalserver" in name:
        return LLMTransientError(str(exc))
    return exc


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
        self._capabilities = get_model_capabilities(self.PROVIDER, config.model_name)

    def _build_request_kwargs(
        self,
        *,
        system_prompt: str,
        user_message: str,
        stream: bool,
        use_structured_output: bool = True,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._config.model_name,
            "max_tokens": self._config.max_output_tokens,
            "temperature": self._config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }

        # Schema enforcement is opt-in per call. Analysis path passes
        # use_structured_output=True (default) so the AnalysisOutput
        # strict json_schema is attached; non-analysis callers pass
        # False so the response shape is defined by the prompt alone.
        if use_structured_output and self._capabilities.supports_structured_output:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": _RESPONSE_FORMAT_NAME,
                    "schema": compile_for_openai(),
                    "strict": True,
                },
            }

        budget = resolve_reasoning_budget(
            operator_budget_tokens=getattr(self._config, "reasoning_budget_tokens", None),
            capabilities=self._capabilities,
        )
        if budget.effort is not None and self._capabilities.is_thinking:
            kwargs["reasoning_effort"] = budget.effort

        if stream:
            kwargs["stream"] = True
            kwargs["stream_options"] = {"include_usage": True}

        return kwargs

    async def call(
        self,
        *,
        system_prompt: str,
        user_message: str,
        trace_id: str | None = None,
        use_structured_output: bool = True,
    ) -> LLMResponse:
        model = self._config.model_name
        start = time.monotonic()

        try:
            response = await self._client.chat.completions.create(
                **self._build_request_kwargs(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    stream=False,
                    use_structured_output=use_structured_output,
                )
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            LLM_REQUEST_TOTAL.labels(provider=self.PROVIDER, model=model, status="error").inc()
            LLM_REQUEST_DURATION.labels(provider=self.PROVIDER, model=model).observe(elapsed_ms / 1000)
            logger.error(
                "llm_call_failed",
                extra={
                    "provider": "openai",
                    "model": model,
                    "error": str(exc),
                    "duration_ms": round(elapsed_ms, 1),
                    "trace_id": trace_id,
                },
            )
            raise _translate_provider_error(exc) from exc

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
            extra={
                "provider": "openai",
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
            provider=self.PROVIDER,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=elapsed_ms,
            stop_reason=stop_reason,
        )

    async def stream_call(
        self,
        *,
        system_prompt: str,
        user_message: str,
        trace_id: str | None = None,
        usage_out: dict[str, Any] | None = None,
        use_structured_output: bool = True,
    ) -> AsyncGenerator[str, None]:
        model = self._config.model_name

        try:
            response = await self._client.chat.completions.create(
                **self._build_request_kwargs(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    stream=True,
                    use_structured_output=use_structured_output,
                )
            )
            async for chunk in response:
                if usage_out is not None and getattr(chunk, "usage", None):
                    usage_out["input_tokens"] = chunk.usage.prompt_tokens
                    usage_out["output_tokens"] = chunk.usage.completion_tokens
                if chunk.choices:
                    choice = chunk.choices[0]
                    if usage_out is not None and getattr(choice, "finish_reason", None):
                        usage_out["finish_reason"] = choice.finish_reason
                    if choice.delta.content:
                        yield choice.delta.content
        except Exception as exc:
            logger.error(
                "llm_stream_call_failed",
                extra={
                    "provider": "openai",
                    "model": model,
                    "error": str(exc),
                    "trace_id": trace_id,
                },
            )
            raise _translate_provider_error(exc) from exc

    async def close(self) -> None:
        await self._client.close()

    def _record_metrics(self, model: str, inp: int, out: int, ms: float) -> None:
        LLM_REQUEST_TOTAL.labels(provider=self.PROVIDER, model=model, status="success").inc()
        LLM_REQUEST_DURATION.labels(provider=self.PROVIDER, model=model).observe(ms / 1000)
        LLM_TOKENS_USED.labels(provider=self.PROVIDER, model=model, token_type="input").inc(inp)  # nosec B106
        LLM_TOKENS_USED.labels(provider=self.PROVIDER, model=model, token_type="output").inc(out)  # nosec B106
