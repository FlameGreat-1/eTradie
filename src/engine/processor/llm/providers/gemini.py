"""Google Gemini provider."""

from __future__ import annotations

import time
from typing import Optional

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
from engine.processor.llm.client import LLMClient, LLMResponse

logger = get_logger(__name__)


class GeminiClient(LLMClient):
    """Google Gemini client via the google-genai SDK."""

    PROVIDER = LLMProvider.GEMINI

    def __init__(self, config: ProcessorConfig) -> None:
        self._config = config
        self._client = genai.Client(api_key=config.get_active_api_key())

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
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=self._config.temperature,
                    max_output_tokens=self._config.max_output_tokens,
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
            raise

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
    ) -> __import__("typing").AsyncGenerator[str, None]:
        model = self._config.model_name
        
        try:
            import asyncio
            import threading
            
            queue = asyncio.Queue()
            loop = asyncio.get_running_loop()
            
            def _sync_worker():
                try:
                    stream = self._client.models.generate_content_stream(
                        model=model,
                        contents=user_message,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=self._config.temperature,
                            max_output_tokens=self._config.max_output_tokens,
                        ),
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
                    raise chunk
                    
                if usage_out is not None and chunk.usage_metadata:
                    usage_out["input_tokens"] = chunk.usage_metadata.prompt_token_count
                    usage_out["output_tokens"] = chunk.usage_metadata.candidates_token_count
                # Capture the finish_reason from every chunk. The final
                # chunk carries the authoritative reason (STOP, MAX_TOKENS,
                # SAFETY, RECITATION, OTHER). Earlier chunks typically
                # have None or STOP. We always overwrite so the last
                # value wins.
                if usage_out is not None and chunk.candidates:
                    try:
                        fr = chunk.candidates[0].finish_reason
                        if fr is not None:
                            usage_out["finish_reason"] = fr.name if hasattr(fr, "name") else str(fr)
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
