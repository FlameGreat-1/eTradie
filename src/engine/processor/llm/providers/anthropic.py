"""Anthropic Claude provider.

Decision-path uses the existing ``stream_call`` so the dashboard SSE
feed shape is preserved. Schema enforcement uses forced tool-use:

  * ``tools=[{name: 'emit_analysis', input_schema:
    <compiled_for_anthropic>}]`` -- declares a single tool whose
    input matches AnalysisOutput.
  * ``tool_choice={type: 'tool', name: 'emit_analysis'}`` -- forces
    the model to invoke that tool. The tool input deltas stream as
    ``input_json_delta`` events whose ``partial_json`` field is the
    progressive JSON of the AnalysisOutput.

We yield those ``partial_json`` strings as the SSE chunks so the
dashboard's existing regex that scans the partial JSON for
``explainable_reasoning`` keeps working byte-for-byte.

``thinking={'type': 'enabled', 'budget_tokens': N}`` is sent only
for thinking-capable SKUs (Opus 4.x with extended thinking enabled).
"""

from __future__ import annotations

import time
from typing import Any, AsyncGenerator, Optional

import anthropic
import orjson

from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    LLM_REQUEST_DURATION,
    LLM_REQUEST_TOTAL,
    LLM_TOKENS_USED,
)
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
from engine.processor.llm.schema_compiler import compile_for_anthropic

logger = get_logger(__name__)

_TOOL_NAME = "emit_analysis"
_TOOL_DESCRIPTION = (
    "Emit the final structured trade analysis. You MUST call this tool exactly "
    "once with the complete analysis as the input. Do not produce any other "
    "text or tool calls. The input must conform exactly to the schema."
)


def _translate_provider_error(exc: Exception) -> Exception:
    """Map an anthropic-sdk exception to a typed LLMError when possible."""
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "ratelimit" in name or "429" in msg or "rate limit" in msg:
        return LLMRateLimitedError(str(exc))
    if "safety" in msg or "policy" in msg or "refus" in msg:
        return LLMSafetyFilterError(str(exc))
    if (
        "timeout" in name
        or "timeout" in msg
        or "connection" in msg
        or "overloaded" in msg
        or "unavailable" in msg
        or "529" in msg
        or " 500" in msg
        or " 502" in msg
        or " 503" in msg
    ):
        return LLMTransientError(str(exc))
    return exc


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
        self._capabilities = get_model_capabilities(self.PROVIDER, config.model_name)

    def _build_request_kwargs(
        self,
        *,
        system_prompt: str,
        user_message: str,
        use_structured_output: bool = True,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._config.model_name,
            "max_tokens": self._config.max_output_tokens,
            "temperature": self._config.temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }

        # Schema enforcement is opt-in per call. The analysis path
        # passes use_structured_output=True (the default) so the
        # AnalysisOutput tool is forced; non-analysis callers (Trading
        # Plan, Performance Review) pass False so the model is free
        # to follow the schema defined in their own system prompt.
        if use_structured_output and self._capabilities.supports_structured_output:
            kwargs["tools"] = [
                {
                    "name": _TOOL_NAME,
                    "description": _TOOL_DESCRIPTION,
                    "input_schema": compile_for_anthropic(),
                }
            ]
            kwargs["tool_choice"] = {"type": "tool", "name": _TOOL_NAME}

        budget = resolve_reasoning_budget(
            operator_budget_tokens=getattr(
                self._config, "reasoning_budget_tokens", None
            ),
            capabilities=self._capabilities,
        )
        if (
            budget.is_active
            and self._capabilities.is_thinking
            and budget.budget_tokens is not None
            and budget.budget_tokens > 0
        ):
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": budget.budget_tokens,
            }

        return kwargs

    @staticmethod
    def _extract_text_from_message(message: Any) -> str:
        """Pull the AnalysisOutput JSON out of the completed message.

        When forced tool use is active the response has no top-level
        text block; the structured output is the ``input`` field of
        the ``tool_use`` content block. We serialise it to JSON so
        downstream parsing is unchanged.
        """
        if not getattr(message, "content", None):
            return ""
        for block in message.content:
            block_type = getattr(block, "type", None)
            if block_type == "tool_use" and getattr(block, "name", "") == _TOOL_NAME:
                return orjson.dumps(getattr(block, "input", {})).decode()
            if block_type == "text" and getattr(block, "text", None):
                return block.text
        return ""

    async def call(
        self,
        *,
        system_prompt: str,
        user_message: str,
        trace_id: Optional[str] = None,
        use_structured_output: bool = True,
    ) -> LLMResponse:
        model = self._config.model_name
        start = time.monotonic()

        try:
            response = await self._client.messages.create(
                **self._build_request_kwargs(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    use_structured_output=use_structured_output,
                )
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            LLM_REQUEST_TOTAL.labels(
                provider=self.PROVIDER, model=model, status="error"
            ).inc()
            LLM_REQUEST_DURATION.labels(provider=self.PROVIDER, model=model).observe(
                elapsed_ms / 1000
            )
            logger.error(
                "llm_call_failed",
                extra={
                    "provider": "anthropic",
                    "model": model,
                    "error": str(exc),
                    "duration_ms": round(elapsed_ms, 1),
                    "trace_id": trace_id,
                },
            )
            raise _translate_provider_error(exc) from exc

        elapsed_ms = (time.monotonic() - start) * 1000
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        text = self._extract_text_from_message(response)
        stop_reason = response.stop_reason

        self._record_metrics(model, input_tokens, output_tokens, elapsed_ms)
        self._log_completion(
            model,
            input_tokens,
            output_tokens,
            elapsed_ms,
            stop_reason,
            len(text),
            trace_id,
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
        trace_id: Optional[str] = None,
        usage_out: Optional[dict] = None,
        use_structured_output: bool = True,
    ) -> AsyncGenerator[str, None]:
        model = self._config.model_name
        kwargs = self._build_request_kwargs(
            system_prompt=system_prompt,
            user_message=user_message,
            use_structured_output=use_structured_output,
        )
        # tool_forced derives from whether _build_request_kwargs
        # attached the tools array. When use_structured_output is
        # False the array is absent and we stream raw text_delta
        # events; the SSE consumer then sees a plain text/JSON
        # stream instead of input_json_delta partials.
        tool_forced = "tools" in kwargs

        try:
            async with self._client.messages.stream(**kwargs) as stream:
                if tool_forced:
                    async for event in stream:
                        event_type = getattr(event, "type", "")
                        if event_type == "content_block_delta":
                            delta = getattr(event, "delta", None)
                            if delta is None:
                                continue
                            delta_type = getattr(delta, "type", "")
                            if delta_type == "input_json_delta":
                                partial = getattr(delta, "partial_json", "")
                                if partial:
                                    yield partial
                            elif delta_type == "text_delta":
                                text_piece = getattr(delta, "text", "")
                                if text_piece:
                                    yield text_piece
                else:
                    async for text in stream.text_stream:
                        yield text

                # Authoritative finish metadata from the completed
                # message. Anthropic stop_reason values:
                #   end_turn / stop_sequence / max_tokens / tool_use
                final_message = await stream.get_final_message()
                if usage_out is not None and final_message is not None:
                    if getattr(final_message, "usage", None):
                        usage_out["input_tokens"] = final_message.usage.input_tokens
                        usage_out["output_tokens"] = final_message.usage.output_tokens
                    if getattr(final_message, "stop_reason", None):
                        usage_out["finish_reason"] = final_message.stop_reason
        except Exception as exc:
            logger.error(
                "llm_stream_call_failed",
                extra={
                    "provider": "anthropic",
                    "model": model,
                    "error": str(exc),
                    "trace_id": trace_id,
                },
            )
            raise _translate_provider_error(exc) from exc

    async def close(self) -> None:
        await self._client.close()

    def _record_metrics(self, model: str, inp: int, out: int, ms: float) -> None:
        LLM_REQUEST_TOTAL.labels(
            provider=self.PROVIDER, model=model, status="success"
        ).inc()
        LLM_REQUEST_DURATION.labels(provider=self.PROVIDER, model=model).observe(
            ms / 1000
        )
        LLM_TOKENS_USED.labels(
            provider=self.PROVIDER, model=model, token_type="input"
        ).inc(inp)
        LLM_TOKENS_USED.labels(
            provider=self.PROVIDER, model=model, token_type="output"
        ).inc(out)

    @staticmethod
    def _log_completion(
        model: str,
        inp: int,
        out: int,
        ms: float,
        stop: str | None,
        length: int,
        trace_id: str | None,
    ) -> None:
        logger.info(
            "llm_call_completed",
            extra={
                "provider": "anthropic",
                "model": model,
                "input_tokens": inp,
                "output_tokens": out,
                "duration_ms": round(ms, 1),
                "stop_reason": stop,
                "response_length": length,
                "trace_id": trace_id,
            },
        )
