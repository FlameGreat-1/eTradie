"""Google Gemini provider.

The decision-path call uses the existing ``stream_call`` so the
dashboard SSE feed is preserved byte-for-byte. Two production knobs
are added to the generation config without touching the call shape:

  * ``response_mime_type='application/json'`` +
    ``response_schema=<compiled_AnalysisOutput>`` -- grammar-constrained
    JSON output. The wire response is guaranteed to validate against
    the Pydantic model before any Python code touches it.

  * ``thinking_config=ThinkingConfig(thinking_budget=N)`` -- caps
    hidden reasoning tokens for Gemini 2.5/3.x thinking models so the
    visible response always has room inside ``max_output_tokens``.

Neither parameter is sent as a prompt token; both are part of the
request config and not billed against ``prompt_token_count`` or
``candidates_token_count``.
"""

from __future__ import annotations

import time
from typing import AsyncGenerator, Optional

from google import genai
from google.genai import types

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
from engine.processor.llm.reasoning import resolve_reasoning_budget
from engine.processor.llm.schema_compiler import compile_for_gemini

logger = get_logger(__name__)

# Gemini finish_reason values that indicate a content-policy block.
# All other non-STOP values are treated as truncation (MAX_TOKENS,
# OTHER, FINISH_REASON_UNSPECIFIED).
_SAFETY_FINISH_REASONS = {"SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST"}


def _translate_provider_error(exc: Exception) -> Exception:
    """Map a google-genai exception to a typed LLMError when possible.

    Matching is by class name + message so the engine boots without
    pinning a specific SDK version.
    """
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "429" in msg or "resource_exhausted" in msg or "ratelimit" in name:
        return LLMRateLimitedError(str(exc))
    if (
        "timeout" in name
        or "timeout" in msg
        or "unavailable" in msg
        or " 500" in msg
        or " 502" in msg
        or " 503" in msg
        or " 504" in msg
    ):
        return LLMTransientError(str(exc))
    return exc


def classify_finish_reason_as_safety(finish_reason: Optional[str]) -> bool:
    """Return True if the Gemini finish_reason is a safety/policy block."""
    return finish_reason is not None and finish_reason.upper() in _SAFETY_FINISH_REASONS


class GeminiClient(LLMClient):
    """Google Gemini client via the google-genai SDK."""

    PROVIDER = LLMProvider.GEMINI

    def __init__(self, config: ProcessorConfig) -> None:
        self._config = config
        self._client = genai.Client(api_key=config.get_active_api_key())
        self._capabilities = get_model_capabilities(self.PROVIDER, config.model_name)

    # ---------- Private helpers ----------------------------------------

    def _build_generation_config(
        self,
        *,
        system_prompt: str,
        use_structured_output: bool,
    ) -> types.GenerateContentConfig:
        """Construct the GenerateContentConfig for both call paths.

        Structured-output and thinking-budget parameters are added only
        when the capability matrix says they apply; unknown user-
        supplied models silently fall back to the unconstrained path.
        """
        kwargs: dict = {
            "system_instruction": system_prompt,
            "temperature": self._config.temperature,
            "max_output_tokens": self._config.max_output_tokens,
        }

        if use_structured_output and self._capabilities.supports_structured_output:
            kwargs["response_mime_type"] = "application/json"
            kwargs["response_schema"] = compile_for_gemini()

        budget = resolve_reasoning_budget(
            operator_budget_tokens=getattr(self._config, "reasoning_budget_tokens", None),
            capabilities=self._capabilities,
        )
        if budget.is_active and self._capabilities.is_thinking:
            kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_budget=budget.budget_tokens or 0,
            )

        return types.GenerateContentConfig(**kwargs)

    # ---------- LLMClient interface ------------------------------------

    async def call(
        self,
        *,
        system_prompt: str,
        user_message: str,
        trace_id: Optional[str] = None,
    ) -> LLMResponse:
        model = self._config.model_name
        start = time.monotonic()

        try:
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=user_message,
                config=self._build_generation_config(
                    system_prompt=system_prompt,
                    use_structured_output=True,
                ),
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
                    "provider": "gemini",
                    "model": model,
                    "error": str(exc),
                    "duration_ms": round(elapsed_ms, 1),
                    "trace_id": trace_id,
                },
            )
            raise _translate_provider_error(exc) from exc

        elapsed_ms = (time.monotonic() - start) * 1000
        text = response.text or ""
        stop_reason = (
            response.candidates[0].finish_reason.name if response.candidates else None
        )
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0

        self._record_metrics(model, input_tokens, output_tokens, elapsed_ms)
        logger.info(
            "llm_call_completed",
            extra={
                "provider": "gemini",
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
        trace_id: Optional[str] = None,
        usage_out: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        model = self._config.model_name

        try:
            import asyncio
            import threading

            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_running_loop()
            generation_config = self._build_generation_config(
                system_prompt=system_prompt,
                use_structured_output=True,
            )

            def _sync_worker() -> None:
                try:
                    stream = self._client.models.generate_content_stream(
                        model=model,
                        contents=user_message,
                        config=generation_config,
                    )
                    for c in stream:
                        loop.call_soon_threadsafe(queue.put_nowait, c)
                    loop.call_soon_threadsafe(queue.put_nowait, None)
                except Exception as e:
                    loop.call_soon_threadsafe(queue.put_nowait, e)

            threading.Thread(target=_sync_worker, daemon=True).start()

            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                if isinstance(chunk, Exception):
                    raise _translate_provider_error(chunk) from chunk

                if usage_out is not None and chunk.usage_metadata:
                    usage_out["input_tokens"] = chunk.usage_metadata.prompt_token_count
                    usage_out["output_tokens"] = chunk.usage_metadata.candidates_token_count
                # Capture the finish_reason from every chunk. The final
                # chunk carries the authoritative reason (STOP,
                # MAX_TOKENS, SAFETY, RECITATION, OTHER). Earlier
                # chunks typically have None or STOP. We always
                # overwrite so the last value wins.
                if usage_out is not None and chunk.candidates:
                    try:
                        fr = chunk.candidates[0].finish_reason
                        if fr is not None:
                            usage_out["finish_reason"] = (
                                fr.name if hasattr(fr, "name") else str(fr)
                            )
                    except (IndexError, AttributeError):
                        pass
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            logger.error(
                "llm_stream_call_failed",
                extra={
                    "provider": "gemini",
                    "model": model,
                    "error": str(exc),
                    "trace_id": trace_id,
                },
            )
            raise

    async def close(self) -> None:
        """Close the underlying genai client HTTP transport."""
        if hasattr(self._client, "_http_client") and hasattr(
            self._client._http_client, "close"
        ):
            await self._client._http_client.close()
        elif hasattr(self._client, "close"):
            self._client.close()

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
