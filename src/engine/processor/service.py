"""Concrete ProcessorPort implementation.

The AnalysisProcessor is the single entry point for the gateway.
It implements ProcessorPort.process() and orchestrates the full
processor pipeline:

    ProcessorInput -> Prompt -> LLM API -> Parse -> Validate ->
    Map to ProcessorOutput -> Persist audit -> Return

This service is stateless. All dependencies are injected.
"""

from __future__ import annotations

import asyncio
import re
import time
from datetime import UTC
from typing import Any

import orjson

from engine.processor.audit.logger import (
    build_analysis_record,
    build_audit_log_record,
    build_error_analysis_record,
)
from engine.processor.config import ProcessorConfig
from engine.processor.constants import PROCESSOR_NAME, ProcessorStatus
from engine.processor.idempotency import ProcessorIdempotency, compute_digest
from engine.processor.llm.client import LLMClient, LLMResponse
from engine.processor.llm.error_classifier import (
    CODE_QUOTA_EXCEEDED,
    CODE_RATE_LIMITED,
    classify_llm_failure,
)
from engine.processor.llm.errors import (
    LLMDuplicateSuppressedError,
    LLMTruncatedError,
)
from engine.processor.llm.retry import retry_llm_call
from engine.processor.mapping.output_mapper import map_to_processor_output
from engine.processor.models.analysis import AnalysisOutput as AO
from engine.processor.models.io import ProcessorInput, ProcessorOutput, ProcessorPort
from engine.processor.parsing.response_parser import parse_llm_response
from engine.processor.prompts.system_prompt import (
    build_system_prompt,
    build_user_message,
    compute_prompt_hash,
)
from engine.processor.storage.uow import ProcessorUOWFactory
from engine.processor.streaming import stream_channel_for_user
from engine.shared import metering_client as metering
from engine.shared.alert_publisher import AlertPublisher
from engine.shared.exceptions import (
    MeteringUnavailableError,
    ProcessorError,
    ProcessorInsufficientDataError,
    QuotaExceededError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    PROCESSOR_INSUFFICIENT_DATA_TOTAL,
    PROCESSOR_RUN_DURATION,
    PROCESSOR_RUN_TOTAL,
)

logger = get_logger(__name__)


async def _publish_byok_provider_quota_safe(
    publisher: AlertPublisher,
    *,
    user_id: str,
    provider: str,
    model: str,
    detail: str,
    code: str,
    trace_id: str | None,
) -> None:
    """Wrap the BYOK provider-quota publish in a tight timeout.

    Used as an asyncio background task from
    AnalysisProcessor._execute's BYOK error branch so the primary
    raise is never delayed by a slow Redis. The publisher already
    swallows its own errors; this wrapper additionally:

      - bounds the wait at 2 seconds with asyncio.wait_for so the task
        cannot accumulate against a wedged Redis,
      - swallows TimeoutError / CancelledError so a shutdown-time
        cancellation does not raise into the asyncio loop's default
        exception handler.

    Audit ref: ADMIN-QUOTA-AUDIT-14.
    """
    try:
        await asyncio.wait_for(
            publisher.publish_llm_provider_quota_exceeded(
                user_id=user_id,
                provider=provider,
                model=model,
                detail=detail,
                code=code,
            ),
            timeout=2.0,
        )
        logger.info(
            "llm_provider_quota_event_published",
            extra={
                "user_id": user_id,
                "provider": provider,
                "model": model,
                "code": code,
                "trace_id": trace_id,
            },
        )
    except (TimeoutError, asyncio.CancelledError):
        # These two are the only failure modes this wrapper actually
        # owns (the 2 s wait_for boundary + shutdown cancellation).
        # The underlying AlertPublisher already catches and logs every
        # Redis publish error at WARN; a redundant Exception arm here
        # would just double-log. Audit ref: ADMIN-QUOTA-AUDIT-V2-15.
        logger.warning(
            "llm_provider_quota_event_publish_timeout_or_cancelled",
            extra={
                "user_id": user_id,
                "code": code,
                "trace_id": trace_id,
            },
        )


# Regex used to progressively extract the `explainable_reasoning` field
# from the partial LLM JSON stream so the dashboard SSE consumer can
# render tokens as they arrive. Compiled once at module load to avoid
# re-compiling on every chunk of every analysis cycle.
_REASONING_RE = re.compile(r'"explainable_reasoning"\s*:\s*"((?:\\.|[^"\\])*)')


class AnalysisProcessor(ProcessorPort):
    """Concrete implementation of the gateway's ProcessorPort.

    Receives the fully assembled context from the gateway, sends it
    to the configured LLM for reasoning, parses and validates the
    response, maps it to the gateway's ProcessorOutput, and persists
    the audit trail.
    """

    def __init__(
        self,
        *,
        config: ProcessorConfig,
        llm_client: LLMClient,
        uow_factory: ProcessorUOWFactory | None = None,
        cache: Any | None = None,
        alert_publisher: AlertPublisher | None = None,
    ) -> None:
        self._config = config
        self._llm = llm_client
        self._uow_factory = uow_factory
        self._cache = cache
        # alert_publisher is the bridge that emits typed events to the
        # gateway's alert bus over Redis pub/sub. Used today exclusively
        # by the BYOK retry-exhausted branch in _execute() to surface
        # LLM_PROVIDER_QUOTA_EXCEEDED when a user's OWN provider returns
        # a 429 / insufficient_quota error. Optional so the legacy test
        # harnesses that build a minimal processor with cache=None still
        # construct; when None the branch logs + skips publishing and
        # the ProcessorError still raises so the gateway records the
        # failure -- only the SPA modal is silenced.
        #
        # Audit ref: ADMIN-QUOTA-9.
        self._alert_publisher = alert_publisher

    async def process(
        self,
        context: ProcessorInput,
        *,
        user_id: str,
        trace_id: str | None = None,
    ) -> ProcessorOutput:
        """Process the assembled context and return a trade decision.

        This is the method the gateway calls. It implements the full
        processor pipeline with timeout, error handling, and audit.

        Args:
            context: Full TA + Macro + RAG context from gateway.
            user_id: Authenticated user id used for metering and audit.
            trace_id: Distributed trace ID for correlation.

        Returns:
            ProcessorOutput for guard evaluation and routing.

        Raises:
            QuotaExceededError: When the metering layer rejects the
                reservation. Propagated unchanged so the internal
                router can map it to HTTP 429 with Retry-After.
            ProcessorError: On LLM call failure after retries.
            ProcessorInsufficientDataError: On insufficient context.
        """
        start = time.monotonic()
        symbol = context.symbol

        logger.info(
            "processor_started",
            extra={
                "symbol": symbol,
                "ta_keys": list(context.ta_analysis.keys()),
                "macro_keys": list(context.macro_analysis.keys()),
                "rag_keys": list(context.retrieved_knowledge.keys()),
                "trace_id": trace_id,
            },
        )

        try:
            async with asyncio.timeout(self._config.total_timeout_seconds):
                return await self._execute_guarded(context, user_id=user_id, trace_id=trace_id, start=start)

        except QuotaExceededError:
            # Propagate immediately: the metering layer already recorded
            # the blocked-count; no audit row is needed for a quota
            # rejection (the user never got an LLM response).
            raise

        except MeteringUnavailableError:
            # Gateway said the metering layer is temporarily down.
            # Fail-closed: do NOT proceed with the LLM call. Propagate
            # so the internal router can map it to HTTP 503 with the
            # parsed Retry-After. No audit row is persisted; the user
            # never got an LLM response and the failure is
            # infrastructure-side, not user-side.
            # Audit ref: ADMIN-QUOTA-AUDIT-V3-A8.
            raise

        except TimeoutError:
            elapsed_ms = (time.monotonic() - start) * 1000
            PROCESSOR_RUN_TOTAL.labels(
                processor=PROCESSOR_NAME,
                status=ProcessorStatus.TIMEOUT,
            ).inc()
            PROCESSOR_RUN_DURATION.labels(
                processor=PROCESSOR_NAME,
            ).observe(elapsed_ms / 1000)

            await self._persist_error(
                user_id=user_id,
                pair=symbol,
                error_message=f"Processor timed out after {self._config.total_timeout_seconds}s",
                status=ProcessorStatus.TIMEOUT,
                duration_ms=elapsed_ms,
                trace_id=trace_id,
            )

            raise ProcessorError(
                f"Processor timed out after {self._config.total_timeout_seconds}s",
                details={"symbol": symbol, "trace_id": trace_id},
            )

        except ProcessorInsufficientDataError:
            elapsed_ms = (time.monotonic() - start) * 1000
            PROCESSOR_RUN_TOTAL.labels(
                processor=PROCESSOR_NAME,
                status=ProcessorStatus.INSUFFICIENT_DATA,
            ).inc()
            PROCESSOR_RUN_DURATION.labels(
                processor=PROCESSOR_NAME,
            ).observe(elapsed_ms / 1000)
            raise

        except ProcessorError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            PROCESSOR_RUN_TOTAL.labels(
                processor=PROCESSOR_NAME,
                status=ProcessorStatus.LLM_ERROR,
            ).inc()
            PROCESSOR_RUN_DURATION.labels(
                processor=PROCESSOR_NAME,
            ).observe(elapsed_ms / 1000)
            # Persist an audit row so the dashboard can surface the
            # per-symbol failure. Without this the router's 422 / 5xx
            # response leaves no trail in analysis_outputs and the
            # SPA shows the symbol as if it was never analysed.
            await self._persist_error(
                user_id=user_id,
                pair=symbol,
                error_message=str(exc),
                status=ProcessorStatus.LLM_ERROR,
                duration_ms=elapsed_ms,
                trace_id=trace_id,
            )
            raise

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            PROCESSOR_RUN_TOTAL.labels(
                processor=PROCESSOR_NAME,
                status=ProcessorStatus.LLM_ERROR,
            ).inc()
            PROCESSOR_RUN_DURATION.labels(
                processor=PROCESSOR_NAME,
            ).observe(elapsed_ms / 1000)

            await self._persist_error(
                user_id=user_id,
                pair=symbol,
                error_message=str(exc),
                status=ProcessorStatus.LLM_ERROR,
                duration_ms=elapsed_ms,
                trace_id=trace_id,
            )

            raise ProcessorError(
                f"Processor failed: {exc}",
                details={"symbol": symbol, "trace_id": trace_id},
            ) from exc

    async def _execute_guarded(
        self,
        context: ProcessorInput,
        *,
        user_id: str,
        trace_id: str | None = None,
        start: float,
    ) -> ProcessorOutput:
        """Idempotency wrapper around the core execution pipeline.

        Collapses duplicate analysis calls (a proxy that abandons and
        replays the request, or two cycles triggered close together)
        into a single LLM call. The dedupe identity is
        sha256(user_id : symbol : prompt_hash); two duplicates for the
        same input produce the same prompt_hash, so the digest is
        stable across duplicates.

        The guard is skipped (straight passthrough to _execute) when the
        cache or user_id is unavailable, so test harnesses and any
        cache-less construction behave exactly as before.
        """
        # No cache or no user identity -> no dedupe possible; run directly.
        if self._cache is None or not user_id:
            return await self._execute(context, user_id=user_id, trace_id=trace_id, start=start)

        symbol = context.symbol

        # Recompute the dedupe digest from the SAME pure builders the
        # core pipeline uses. build_system_prompt / build_user_message /
        # compute_prompt_hash are deterministic and side-effect-free
        # (no LLM, no IO), so recomputing here is cheap and yields the
        # exact prompt_hash the real call keys on.
        prompt_hash = compute_prompt_hash(build_system_prompt(), build_user_message(context))
        digest = compute_digest(user_id=user_id, symbol=symbol, prompt_hash=prompt_hash)
        guard = ProcessorIdempotency(self._cache)

        # 1. A completed result for this exact input already exists.
        cached = await guard.check_cached(digest, trace_id=trace_id)
        if cached is not None:
            logger.info(
                "processor_idempotency_cache_hit",
                extra={"symbol": symbol, "user_id": user_id, "trace_id": trace_id},
            )
            return cached

        # 2. Single-flight: try to become the sole in-flight owner.
        handle = await guard.acquire(digest, trace_id=trace_id)
        if handle is None:
            # A concurrent identical call already owns the lock. Do NOT
            # run a second LLM call; wait for the owner's result.
            owner_result = await guard.await_result(digest, trace_id=trace_id)
            if owner_result is not None:
                logger.info(
                    "processor_idempotency_served_owner_result",
                    extra={
                        "symbol": symbol,
                        "user_id": user_id,
                        "trace_id": trace_id,
                    },
                )
                return owner_result
            logger.warning(
                "processor_idempotency_duplicate_suppressed",
                extra={
                    "symbol": symbol,
                    "user_id": user_id,
                    "trace_id": trace_id,
                },
            )
            raise LLMDuplicateSuppressedError(
                "Duplicate analysis call suppressed: an identical request "
                "(same user, symbol, and prompt) is already in flight.",
                details={"symbol": symbol, "trace_id": trace_id},
            )

        # 3. We own the lock: run the real pipeline, cache the successful
        #    result, and ALWAYS release the lock. _execute only ever
        #    returns on success (SUCCESS / NO_SETUP) and raises on every
        #    failure, so the returned value is always safe to cache and
        #    error states are never cached.
        try:
            result = await self._execute(context, user_id=user_id, trace_id=trace_id, start=start)
            await guard.store_result(digest, result, trace_id=trace_id)
            return result
        finally:
            await guard.release(handle, trace_id=trace_id)

    async def _execute(
        self,
        context: ProcessorInput,
        *,
        user_id: str,
        trace_id: str | None = None,
        start: float,
    ) -> ProcessorOutput:
        """Core execution pipeline."""
        symbol = context.symbol

        # Step 1: Validate sufficient data.
        self._validate_context(context, trace_id=trace_id)

        # Step 2: Build prompt.
        #
        # The analysis path uses the institutional rulebook (system
        # prompt + retrieved RAG chunks) as the sole source of truth.
        # The user Trading Operating System is intentionally NOT
        # injected here -- it is consumed by the dedicated
        # trading-plan and performance-review generators which are
        # the user-facing surfaces for personalised guidance.
        system_prompt = build_system_prompt()
        user_message = build_user_message(context)
        prompt_hash = compute_prompt_hash(system_prompt, user_message)

        # Dump exact LLM payload to /output/prompts for debugging
        try:
            from datetime import datetime as dt
            from pathlib import Path

            ts = dt.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            prompts_dir = Path("/output/prompts") / f"{symbol}_{ts}"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            (prompts_dir / "system_prompt.txt").write_text(system_prompt, encoding="utf-8")
            (prompts_dir / "user_message.txt").write_text(user_message, encoding="utf-8")
            # Diagnostic: identify WHICH invocation produced this dump so
            # duplicate dumps for a single trigger can be correlated.
            _meta = context.metadata if isinstance(context.metadata, dict) else {}
            (prompts_dir / "meta.txt").write_text(
                "trace_id: {tid}\n"
                "source: {src}\n"
                "user_id: {uid}\n"
                "symbol: {sym}\n"
                "model: {model}\n"
                "max_output_tokens: {mot}\n"
                "prompt_hash: {ph}\n".format(
                    tid=trace_id or "",
                    src=_meta.get("source", ""),
                    uid=user_id,
                    sym=symbol,
                    model=self._config.model_name,
                    mot=self._config.max_output_tokens,
                    ph=prompt_hash,
                ),
                encoding="utf-8",
            )
            logger.info(
                "prompt_payload_saved",
                extra={
                    "directory": str(prompts_dir),
                    "symbol": symbol,
                    "trace_id": trace_id,
                    "source": _meta.get("source", ""),
                },
            )
        except Exception as exc:
            logger.error(
                "failed_to_save_prompt_payload",
                extra={"error": str(exc), "symbol": symbol, "trace_id": trace_id},
            )

        logger.debug(
            "processor_prompt_built",
            extra={
                "symbol": symbol,
                "user_message_length": len(user_message),
                "prompt_hash": prompt_hash,
                "trace_id": trace_id,
            },
        )

        # Step 3: Metering reserve (Pro Managed / admin only).
        # We estimate the input token count from the prompt byte length
        # divided by 4 (a conservative approximation that errs on the
        # side of over-reserving; the Commit step corrects to the real
        # count). The max_output_tokens cap is the hard ceiling the
        # provider will honour.
        #
        # If metering is disabled (METERING_ENABLED=false or no gateway
        # URL configured) reserve() returns '' and the call proceeds
        # without any quota check. This is the correct behaviour for
        # BYOK users (they pay their own bill) and for local dev.
        # Metering is platform-only: a BYOK user supplies their own
        # provider key, so the platform incurs no LLM cost and has no
        # business writing to billing_usage. The uses_platform_key flag
        # is set by the resolver in dependencies.py based on whether the
        # active ProcessorConfig was built from the platform row / env
        # baseline (True) or from a personal row in llm_connections
        # (False). Default is False so a misconfigured construction
        # fails closed (no platform metering on an unknown key origin).
        estimated_input = max(0, len(user_message.encode("utf-8")) // 4)
        if self._config.uses_platform_key:
            reservation_id = await metering.reserve(
                user_id=user_id,
                provider=self._llm.PROVIDER,
                model=self._config.model_name,
                estimated_input_tokens=estimated_input,
                max_output_tokens=self._config.max_output_tokens,
                trace_id=trace_id or "",
            )
            # QuotaExceededError propagates immediately (no LLM call,
            # no audit row). The internal router maps it to HTTP 429.
        else:
            reservation_id = ""
            logger.debug(
                "metering_skipped_byok",
                extra={
                    "user_id": user_id,
                    "provider": self._llm.PROVIDER,
                    "model": self._config.model_name,
                    "trace_id": trace_id,
                },
            )

        # Step 4: Call LLM API with retry + exponential backoff.
        # retry_llm_call handles transient failures (rate limits, server
        # errors, timeouts) with exponential backoff + jitter. Non-retryable
        # errors (auth, bad request) are raised immediately.
        #
        # Streaming: during the call we publish status/reasoning_chunk
        # frames to the authenticated user's private pub/sub channel
        # (see engine.processor.streaming). This is what the dashboard's
        # SSE consumer subscribes to. On cache failure the publish is a
        # no-op so the processor never blocks on streaming being broken.
        stream_channel = stream_channel_for_user(user_id) if self._cache and user_id else None

        async def _llm_call() -> LLMResponse:
            # Token counts come from `usage_metadata` only. The old
            # `output_tokens += 1` chunk-counter masquerade was wrong
            # (a chunk is not a token) and produced misleading
            # diagnostics like "414 tokens out of 16384" that were
            # actually chunk counts. When a provider omits
            # usage_metadata (rare, provider bug) the count stays 0
            # rather than fabricated, and a warning log records it.
            full_text = ""
            start_llm = time.monotonic()
            if stream_channel and self._cache is not None:
                await self._cache.publish(
                    stream_channel,
                    {
                        "symbol": symbol,
                        "type": "status",
                        "message": "Analyzing...",
                    },
                )

            last_published_reasoning = ""
            usage_dict: dict[str, Any] = {}
            async for chunk in self._llm.stream_call(
                system_prompt=system_prompt,
                user_message=user_message,
                trace_id=trace_id,
                usage_out=usage_dict,
            ):
                full_text += chunk

                # Progressively extract explainable_reasoning using a
                # regex that handles escaped quotes so partial JSON
                # still yields clean, displayable reasoning text to the
                # dashboard.
                match = _REASONING_RE.search(full_text)
                if match:
                    current_extracted = match.group(1)
                    # Unescape json newlines and quotes progressively.
                    current_extracted = current_extracted.replace("\\n", "\n").replace('\\"', '"')

                    if len(current_extracted) > len(last_published_reasoning):
                        new_text = current_extracted[len(last_published_reasoning) :]
                        last_published_reasoning = current_extracted
                        if stream_channel and new_text and self._cache is not None:
                            await self._cache.publish(
                                stream_channel,
                                {
                                    "symbol": symbol,
                                    "type": "reasoning_chunk",
                                    "text": new_text,
                                },
                            )

            # Signal terminal state so the SSE reader on the dashboard
            # can tear down its EventSource loop and trigger a refetch
            # of the analysis feed. Publishing here (not inside the
            # except path) guarantees we only emit `final` when the LLM
            # call actually completed.
            if stream_channel and self._cache is not None:
                # Settle the REASONING phase row to the done (✓) state.
                # The row was opened by the gateway/engine processor
                # pulses but otherwise only ever ended via the separate
                # `final` frame, which the Thinking Terminal does not
                # treat as a phase completion — so the row stayed active
                # forever. Emit a matching pulse frame with
                # completed=true on the same channel before `final`.
                await self._cache.publish(
                    stream_channel,
                    {
                        "symbol": symbol,
                        "type": "pulse",
                        "phase": "REASONING",
                        "message": "AI decision finalised",
                        "source": "processor",
                        "completed": True,
                    },
                )
                await self._cache.publish(
                    stream_channel,
                    {
                        "symbol": symbol,
                        "type": "final",
                        "message": "Analysis Complete",
                    },
                )

            actual_finish_reason = usage_dict.get("finish_reason", "STOP")
            output_tokens_reported = usage_dict.get("output_tokens", 0)
            if output_tokens_reported == 0 and full_text:
                logger.warning(
                    "llm_usage_metadata_missing",
                    extra={
                        "symbol": symbol,
                        "provider": self._llm.PROVIDER,
                        "model": self._config.model_name,
                        "response_length": len(full_text),
                        "trace_id": trace_id,
                    },
                )
            return LLMResponse(
                text=full_text,
                model=self._config.model_name,
                provider=self._llm.PROVIDER,
                input_tokens=usage_dict.get("input_tokens", 0),
                output_tokens=output_tokens_reported,
                duration_ms=(time.monotonic() - start_llm) * 1000,
                stop_reason=actual_finish_reason,
            )

        try:
            llm_response: LLMResponse = await retry_llm_call(
                _llm_call,
                config=self._config,
                trace_id=trace_id,
            )
        except Exception as llm_exc:
            # LLM call failed after all retries. Refund the provisional
            # debit so the user's quota is not permanently consumed for
            # a call that never completed. The refund is best-effort;
            # the janitor will reap the reservation after its TTL if
            # the refund call itself fails. Skipped for BYOK because no
            # reservation was made.
            if reservation_id:
                await metering.refund(reservation_id=reservation_id)

            # --------------------------------------------------------------
            # BYOK provider-quota notification (Audit ref: ADMIN-QUOTA-9).
            #
            # When a BYOK user's OWN provider returns a quota / rate-limit
            # error and all retries are exhausted, surface a typed event
            # so the SPA can open the dedicated provider-quota modal whose
            # copy directs the user to THEIR OWN provider dashboard.
            #
            # Gate (per QUOTA.md scope decision):
            #   - uses_platform_key=False  -> BYOK path; this branch fires.
            #   - uses_platform_key=True   -> Platform path; the deep
            #     metering.reserve already raised QuotaExceededError
            #     above the retry layer, so this code is unreachable in
            #     that case.
            #
            # We only publish for quota-shaped failures (CODE_QUOTA_EXCEEDED
            # or CODE_RATE_LIMITED). Auth / model-not-found / timeout /
            # transient errors have different remediation paths and
            # surface through the existing ProcessorError -> generic
            # SPA error UX.
            # --------------------------------------------------------------
            if not self._config.uses_platform_key and self._alert_publisher is not None and user_id:
                classified = classify_llm_failure(llm_exc)
                if classified.code in (CODE_QUOTA_EXCEEDED, CODE_RATE_LIMITED):
                    # Background fire-and-forget so a slow Redis cannot
                    # add latency to the user-visible error path. The
                    # publisher already swallows its own Redis errors;
                    # the 2 s wait_for here is a hard upper bound that
                    # cancels a wedged publish so it cannot leak across
                    # request boundaries.
                    #
                    # NOT registered with container.background_tasks --
                    # the Processor does not own the coordinator and a
                    # publish task is short-lived (worst case 2 s); on
                    # shutdown the Redis client closes and the task's
                    # next await raises CancelledError, which the
                    # publisher's own try/except converts to a log line.
                    #
                    # Audit ref: ADMIN-QUOTA-AUDIT-14.
                    provider_name = getattr(self._llm, "PROVIDER", "unknown")
                    asyncio.create_task(
                        _publish_byok_provider_quota_safe(
                            self._alert_publisher,
                            user_id=user_id,
                            provider=provider_name,
                            model=self._config.model_name,
                            detail=str(llm_exc),
                            code=classified.code,
                            trace_id=trace_id,
                        ),
                        name=f"alert_publish_byok_quota_{user_id}",
                    )

            raise

        # Step 4b: Detect LLM output truncation BEFORE parsing.
        # Gemini's finish_reason tells us exactly why it stopped
        # generating. If it's anything other than STOP, the JSON is
        # guaranteed to be incomplete. Surface the real reason instead
        # of letting the parser crash with a confusing "unexpected end
        # of data" error.
        finish_reason = llm_response.stop_reason or "STOP"
        if finish_reason not in ("STOP", "stop"):
            # Dump the truncated response for debugging
            try:
                from datetime import datetime as dt
                from pathlib import Path

                ts = dt.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                dump_dir = Path("/output/prompts") / f"truncated_{symbol}_{ts}"
                dump_dir.mkdir(parents=True, exist_ok=True)
                (dump_dir / "truncated_response.txt").write_text(llm_response.text, encoding="utf-8")
                (dump_dir / "metadata.txt").write_text(
                    f"finish_reason: {finish_reason}\n"
                    f"output_tokens: {llm_response.output_tokens}\n"
                    f"input_tokens: {llm_response.input_tokens}\n"
                    f"duration_ms: {llm_response.duration_ms}\n"
                    f"model: {llm_response.model}\n"
                    f"max_output_tokens: {self._config.max_output_tokens}\n",
                    encoding="utf-8",
                )
            except Exception:  # nosec B110
                pass

            logger.error(
                "llm_output_truncated",
                extra={
                    "symbol": symbol,
                    "finish_reason": finish_reason,
                    "output_tokens": llm_response.output_tokens,
                    "max_output_tokens": self._config.max_output_tokens,
                    "response_length": len(llm_response.text),
                    "trace_id": trace_id,
                },
            )
            # The call succeeded at the wire (the retry layer did not
            # see an exception, so the existing refund-on-retry-exhausted
            # branch did NOT fire) but the response is unusable. Refund
            # the provisional debit so the reservation does not leak
            # until TTL. Best-effort: a refund failure is reaped by the
            # janitor. Skipped for BYOK because no reservation was made.
            if reservation_id:
                await metering.refund(reservation_id=reservation_id)
            raise LLMTruncatedError(
                f"LLM output was truncated (finish_reason={finish_reason}). "
                f"The model generated {llm_response.output_tokens} tokens "
                f"out of {self._config.max_output_tokens} allowed before "
                f"the provider terminated the response. This is NOT a "
                f"parsing error — the LLM provider stopped generating.",
                finish_reason=finish_reason,
                output_tokens=llm_response.output_tokens,
                max_output_tokens=self._config.max_output_tokens,
                response_length=len(llm_response.text),
                details={
                    "symbol": symbol,
                    "trace_id": trace_id,
                },
            )

        # Step 5: Commit the real token counts. The over-reservation on
        # the output side (max_output - actual_output) is returned to
        # the user's quota. Commit is best-effort: a transient failure
        # does not roll back the completed LLM call. Skipped for BYOK
        # because no reservation was made.
        if reservation_id:
            await metering.commit(
                reservation_id=reservation_id,
                actual_input_tokens=llm_response.input_tokens,
                actual_output_tokens=llm_response.output_tokens,
            )

        if self._config.log_raw_llm_response:
            logger.debug(
                "processor_raw_llm_response",
                extra={
                    "symbol": symbol,
                    "response_length": len(llm_response.text),
                    "trace_id": trace_id,
                },
            )

        # Step 6: Parse response into AnalysisOutput.
        try:
            analysis_output, validation_warnings = parse_llm_response(
                llm_response.text,
                require_citations=self._config.require_citations,
                trace_id=trace_id,
            )
        except Exception as parse_exc:
            # Dump the truncated response to see exactly what Gemini returned
            try:
                from datetime import datetime as dt
                from pathlib import Path

                ts = dt.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                dump_dir = Path("/output/prompts") / f"failed_{symbol}_{ts}"
                dump_dir.mkdir(parents=True, exist_ok=True)
                (dump_dir / "truncated_response.txt").write_text(llm_response.text, encoding="utf-8")
                logger.error("dumped_truncated_response", extra={"directory": str(dump_dir)})
            except Exception:  # nosec B110
                pass
            raise parse_exc

        # Override the LLM's `pair` with the authoritative input symbol.
        # The LLM is non-deterministic with casing (e.g. "BOOM 500 INDEX"
        # vs "Boom 500 Index") but MT5 requires exact case. context.symbol
        # is the canonical name from the user's Market Watch.
        analysis_output = analysis_output.model_copy(update={"pair": symbol})

        # Step 7: Build raw response dict for audit (include provider metadata).
        try:
            text = llm_response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            raw_dict = orjson.loads(text)
        except (orjson.JSONDecodeError, ValueError):
            raw_dict = {"raw_text": llm_response.text[:4096]}
        raw_dict["_llm_provider"] = llm_response.provider
        raw_dict["_llm_model"] = llm_response.model

        # Step 8: Map to gateway's ProcessorOutput.
        processor_output = map_to_processor_output(
            analysis_output,
            raw_response=raw_dict,
        )

        elapsed_ms = (time.monotonic() - start) * 1000

        # Step 9: Determine status, emit metrics, persist audit trail.
        status = ProcessorStatus.NO_SETUP if analysis_output.direction == "NO SETUP" else ProcessorStatus.SUCCESS

        PROCESSOR_RUN_TOTAL.labels(
            processor=PROCESSOR_NAME,
            status=status,
        ).inc()
        PROCESSOR_RUN_DURATION.labels(
            processor=PROCESSOR_NAME,
        ).observe(elapsed_ms / 1000)

        if self._config.persist_audit_logs:
            await self._persist_success(
                user_id=user_id,
                analysis_output=analysis_output,
                llm_response=llm_response,
                prompt_hash=prompt_hash,
                validation_warnings=validation_warnings,
                raw_dict=raw_dict,
                elapsed_ms=elapsed_ms,
                trace_id=trace_id,
            )

        logger.info(
            "processor_completed",
            extra={
                "symbol": symbol,
                "analysis_id": analysis_output.analysis_id,
                "direction": analysis_output.direction,
                "grade": analysis_output.setup_grade,
                "score": analysis_output.confluence_score.score,
                "confidence": analysis_output.confidence,
                "proceed": analysis_output.proceed_to_module_b,
                "rr_ratio": analysis_output.rr_ratio,
                "duration_ms": round(elapsed_ms, 1),
                "input_tokens": llm_response.input_tokens,
                "output_tokens": llm_response.output_tokens,
                "reservation_id": reservation_id,
                "warnings": validation_warnings,
                "trace_id": trace_id,
            },
        )

        return processor_output

    @staticmethod
    def _validate_context(
        context: ProcessorInput,
        *,
        trace_id: str | None = None,
    ) -> None:
        """Validate that the context has sufficient data for analysis."""
        if not context.ta_analysis:
            PROCESSOR_INSUFFICIENT_DATA_TOTAL.labels(
                processor=PROCESSOR_NAME,
                reason="empty_ta",
            ).inc()
            raise ProcessorInsufficientDataError(
                "ProcessorInput has empty ta_analysis",
                details={"symbol": context.symbol, "trace_id": trace_id},
            )

        ta = context.ta_analysis
        has_candidates = bool(ta.get("smc_candidates")) or bool(ta.get("snd_candidates"))
        if not has_candidates:
            PROCESSOR_INSUFFICIENT_DATA_TOTAL.labels(
                processor=PROCESSOR_NAME,
                reason="no_candidates",
            ).inc()
            raise ProcessorInsufficientDataError(
                "ProcessorInput has no SMC or SnD candidates",
                details={"symbol": context.symbol, "trace_id": trace_id},
            )

        if not context.retrieved_knowledge:
            PROCESSOR_INSUFFICIENT_DATA_TOTAL.labels(
                processor=PROCESSOR_NAME,
                reason="empty_rag",
            ).inc()
            raise ProcessorInsufficientDataError(
                "ProcessorInput has empty retrieved_knowledge",
                details={"symbol": context.symbol, "trace_id": trace_id},
            )

    async def _persist_success(
        self,
        *,
        user_id: str,
        analysis_output: AO,
        llm_response: LLMResponse,
        prompt_hash: str,
        validation_warnings: list[str],
        raw_dict: dict[str, Any],
        elapsed_ms: float,
        trace_id: str | None,
    ) -> None:
        """Persist analysis record and audit log on success."""

        if not self._uow_factory:
            return

        try:
            async with self._uow_factory() as uow:
                record = build_analysis_record(
                    analysis_output,
                    user_id=user_id,
                    status=("success" if analysis_output.direction != "NO SETUP" else "no_setup"),
                    duration_ms=elapsed_ms,
                    trace_id=trace_id,
                    raw_output=raw_dict,
                )

                await uow.analysis_repo.save_analysis(
                    user_id=record.user_id,
                    analysis_id=record.analysis_id,
                    pair=record.pair,
                    direction=record.direction,
                    setup_grade=record.setup_grade,
                    confluence_score=record.confluence_score,
                    confidence=record.confidence,
                    proceed_to_module_b=record.proceed_to_module_b,
                    rr_ratio=record.rr_ratio,
                    entry_price_low=record.entry_price_low,
                    entry_price_high=record.entry_price_high,
                    stop_loss_price=record.stop_loss_price,
                    tp1_price=record.tp1_price,
                    tp2_price=record.tp2_price,
                    tp3_price=record.tp3_price,
                    trading_style=record.trading_style,
                    session=record.session,
                    llm_provider=record.llm_provider,
                    llm_model=record.llm_model,
                    status=record.status,
                    error_message=record.error_message,
                    duration_ms=record.duration_ms,
                    trace_id=record.trace_id,
                    raw_output=record.raw_output,
                )

                audit_record = build_audit_log_record(
                    analysis_output,
                    llm_response,
                    user_id=user_id,
                    prompt_hash=prompt_hash,
                    validation_passed=len(validation_warnings) == 0,
                    validation_errors=validation_warnings,
                    trace_id=trace_id,
                )

                await uow.audit_repo.save_audit_log(
                    user_id=audit_record.user_id,
                    analysis_id=audit_record.analysis_id,
                    pair=audit_record.pair,
                    timestamp=audit_record.timestamp,
                    retrieval_query_summary=audit_record.retrieval_query_summary,
                    retrieval_strategy=audit_record.retrieval_strategy,
                    retrieval_chunks_count=audit_record.retrieval_chunks_count,
                    retrieval_coverage=audit_record.retrieval_coverage,
                    retrieval_coverage_details=audit_record.retrieval_coverage_details,
                    retrieval_conflicts=audit_record.retrieval_conflicts,
                    retrieval_conflict_details=audit_record.retrieval_conflict_details,
                    llm_model=audit_record.llm_model,
                    llm_prompt_hash=audit_record.llm_prompt_hash,
                    llm_input_tokens=audit_record.llm_input_tokens,
                    llm_output_tokens=audit_record.llm_output_tokens,
                    llm_duration_ms=audit_record.llm_duration_ms,
                    llm_response=audit_record.llm_response,
                    citations=audit_record.citations,
                    final_direction=audit_record.final_direction,
                    final_grade=audit_record.final_grade,
                    final_confidence=audit_record.final_confidence,
                    final_proceed=audit_record.final_proceed,
                    validation_passed=audit_record.validation_passed,
                    validation_errors=audit_record.validation_errors,
                    trace_id=audit_record.trace_id,
                )

        except Exception as exc:
            logger.error(
                "processor_audit_persist_failed",
                extra={
                    "error": str(exc),
                    "analysis_id": analysis_output.analysis_id,
                    "trace_id": trace_id,
                },
                exc_info=True,
            )

    async def _persist_error(
        self,
        *,
        user_id: str,
        pair: str,
        error_message: str,
        status: str,
        duration_ms: float,
        trace_id: str | None,
    ) -> None:
        """Persist an error analysis record."""
        if not self._uow_factory:
            return

        try:
            async with self._uow_factory() as uow:
                record = build_error_analysis_record(
                    user_id=user_id,
                    pair=pair,
                    error_message=error_message,
                    status=status,
                    duration_ms=duration_ms,
                    trace_id=trace_id,
                )

                await uow.analysis_repo.save_analysis(
                    user_id=record.user_id,
                    analysis_id=record.analysis_id,
                    pair=record.pair,
                    direction=record.direction,
                    setup_grade=record.setup_grade,
                    confluence_score=record.confluence_score,
                    confidence=record.confidence,
                    proceed_to_module_b=record.proceed_to_module_b,
                    status=record.status,
                    error_message=record.error_message,
                    duration_ms=record.duration_ms,
                    trace_id=record.trace_id,
                )

        except Exception as exc:
            logger.error(
                "processor_error_persist_failed",
                extra={
                    "error": str(exc),
                    "pair": pair,
                    "trace_id": trace_id,
                },
                exc_info=True,
            )
