"""OpenAI-compatible self-hosted provider.

Works with any endpoint that implements the OpenAI chat completions
API: vLLM, Ollama, LM Studio, text-generation-inference, LocalAI, etc.

Because structured-output support varies wildly across these backends,
the client tries ``response_format`` first; if the server rejects the
parameter we transparently retry without it and latch a per-instance
flag so subsequent calls skip the rejection round-trip. ``service.py``
reads ``structured_output_active`` to decide whether to engage the
strict path or the hardened free-text parser.
"""

from __future__ import annotations

import time
from typing import Any, AsyncGenerator, Optional

import openai

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
    LLMTransientError,
)
from engine.processor.llm.schema_compiler import compile_for_openai_compatible

logger = get_logger(__name__)

_RESPONSE_FORMAT_NAME = "AnalysisOutput"

_UNSUPPORTED_RESPONSE_FORMAT_HINTS = (
    "response_format",
    "json_schema",
    "not supported",
    "unsupported parameter",
    "invalid parameter",
    "unknown parameter",
    "unrecognized argument",
    "does not support",
)


def _is_unsupported_response_format(exc: Exception) -> bool:
    """Return True when the server rejected the response_format param."""
    msg = str(exc).lower()
    if "response_format" not in msg and "json_schema" not in msg:
        return False
    return any(hint in msg for hint in _UNSUPPORTED_RESPONSE_FORMAT_HINTS)


def _translate_provider_error(exc: Exception) -> Exception:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "ratelimit" in name or "429" in msg or "rate limit" in msg:
        return LLMRateLimitedError(str(exc))
    if (
        "timeout" in name
        or "timeout" in msg
        or "connection" in msg
        or "unavailable" in msg
    ):
        return LLMTransientError(str(exc))
    return exc


class OpenAICompatibleClient(LLMClient):
    """Client for any OpenAI-compatible self-hosted endpoint."""

    PROVIDER = LLMProvider.SELF_HOSTED

    def __init__(self, config: ProcessorConfig) -> None:
        self._config = config
        api_key = config.get_active_api_key() or "not-required"
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=config.api_base_url,
            timeout=float(config.llm_timeout_seconds),
            max_retries=0,
        )
        self._capabilities = get_model_capabilities(self.PROVIDER, config.model_name)
        # Latched per instance: once a backend has rejected
        # ``response_format`` for a given model we stop sending it on
        # subsequent calls to that instance.
        # The capability matrix defaults SELF_HOSTED to False, so we
        # opt-in via the operator's intent (force probe on the first
        # call by starting at None which is interpreted as "unknown,
        # try once"). When the operator later flips the catalog entry
        # for a known good self-hosted model, the probe succeeds and
        # this flag latches True.
        self._response_format_supported: Optional[bool] = (
            True if self._capabilities.supports_structured_output else None
        )

    def _build_request_kwargs(
        self,
        *,
        system_prompt: str,
        user_message: str,
        stream: bool,
        with_response_format: bool,
    ) -> dict[str, Any]:
        # with_response_format is the FINAL decision (after combining
        # the per-call use_structured_output toggle with the latched
        # _response_format_supported probe). The caller is responsible
        # for the AND of those signals; this method only honors the
        # final boolean it receives.
        kwargs: dict[str, Any] = {
            "model": self._config.model_name,
            "max_tokens": self._config.max_output_tokens,
            "temperature": self._config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        if with_response_format:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": _RESPONSE_FORMAT_NAME,
                    "schema": compile_for_openai_compatible(),
                    "strict": True,
                },
            }
        if stream:
            kwargs["stream"] = True
            kwargs["stream_options"] = {"include_usage": True}
        return kwargs

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

        # The final "send response_format" decision is the AND of
        #   (a) the caller's per-call use_structured_output toggle, and
        #   (b) the latched _response_format_supported probe.
        # When the caller passes False (non-analysis path) we never
        # attach the AnalysisOutput schema regardless of probe state,
        # and we do NOT mutate the latched probe value -- the latch
        # exists to remember server capability for the analysis path
        # and a free-text call must not flip it.
        attempt_with_format = (
            use_structured_output and self._response_format_supported is not False
        )

        async def _do_call(use_format: bool):
            return await self._client.chat.completions.create(
                **self._build_request_kwargs(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    stream=False,
                    with_response_format=use_format,
                )
            )

        try:
            try:
                response = await _do_call(attempt_with_format)
                if (
                    use_structured_output
                    and attempt_with_format
                    and self._response_format_supported is None
                ):
                    # First successful probe latches True. Only the
                    # analysis path (use_structured_output=True) is
                    # allowed to latch; a free-text call leaves the
                    # probe value untouched so the analysis path's
                    # first call still performs its own probe.
                    self._response_format_supported = True
            except Exception as exc:
                if (
                    use_structured_output
                    and attempt_with_format
                    and _is_unsupported_response_format(exc)
                ):
                    self._response_format_supported = False
                    logger.warning(
                        "self_hosted_response_format_unsupported",
                        extra={
                            "model": model,
                            "base_url": self._config.api_base_url,
                            "trace_id": trace_id,
                            "error": str(exc),
                        },
                    )
                    response = await _do_call(False)
                else:
                    raise
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
                    "provider": "self_hosted",
                    "model": model,
                    "error": str(exc),
                    "duration_ms": round(elapsed_ms, 1),
                    "base_url": self._config.api_base_url,
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
                "provider": "self_hosted",
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "duration_ms": round(elapsed_ms, 1),
                "stop_reason": stop_reason,
                "response_length": len(text),
                "base_url": self._config.api_base_url,
                "trace_id": trace_id,
                "structured_output_used": self._response_format_supported is True,
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
        trace_id: Optional[str] = None,
        usage_out: Optional[dict] = None,
        use_structured_output: bool = True,
    ) -> AsyncGenerator[str, None]:
        model = self._config.model_name

        async def _open_stream(use_format: bool):
            return await self._client.chat.completions.create(
                **self._build_request_kwargs(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    stream=True,
                    with_response_format=use_format,
                )
            )

        # See call() for the rationale: AND of caller intent and
        # latched probe, and only the analysis path mutates the probe.
        attempt_with_format = (
            use_structured_output and self._response_format_supported is not False
        )
        try:
            try:
                response = await _open_stream(attempt_with_format)
                if (
                    use_structured_output
                    and attempt_with_format
                    and self._response_format_supported is None
                ):
                    self._response_format_supported = True
            except Exception as exc:
                if (
                    use_structured_output
                    and attempt_with_format
                    and _is_unsupported_response_format(exc)
                ):
                    self._response_format_supported = False
                    logger.warning(
                        "self_hosted_response_format_unsupported_stream",
                        extra={
                            "model": model,
                            "base_url": self._config.api_base_url,
                            "trace_id": trace_id,
                            "error": str(exc),
                        },
                    )
                    response = await _open_stream(False)
                else:
                    raise

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
                    "provider": "self_hosted",
                    "model": model,
                    "error": str(exc),
                    "trace_id": trace_id,
                },
            )
            raise _translate_provider_error(exc) from exc

    async def close(self) -> None:
        await self._client.close()

    @property
    def structured_output_active(self) -> bool:
        """Reflect whether the latched probe enables structured output.

        ``service.py`` reads this after each call to decide whether the
        response should be parsed with the strict path or the hardened
        free-text path (None -> [] coercion). The flag is latched on
        the first probe and stays in place until the client is
        reconstructed.
        """
        return self._response_format_supported is True

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
