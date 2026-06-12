"""Internal endpoints called by the Go gateway.

Routes:
    POST /internal/ta/confirm_ltf
    POST /internal/ta/analyze
    POST /internal/macro/collect
    POST /internal/rag/retrieve
    POST /internal/processor/process
    POST /internal/debug/runcycle
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from engine.dependencies import Container
from engine.helpers import (
    _resolve_user_broker,
    _resolve_user_processor,
    _save_debug_output,
)
from engine.processor.llm.errors import (
    LLMDuplicateSuppressedError,
    LLMRateLimitedError,
    LLMSafetyFilterError,
    LLMSchemaViolationError,
    LLMTruncatedError,
)
from engine.processor.models.io import ProcessorInput
from engine.shared.exceptions import (
    MeteringUnavailableError,
    ProcessorInsufficientDataError,
    QuotaExceededError,
)
from engine.schemas import (
    InternalDebugRunCycleRequest,
    InternalLTFConfirmRequest,
    InternalMacroRequest,
    InternalProcessorRequest,
    InternalRAGRequest,
    InternalTARequest,
)
from engine.shared.auth import AuthenticatedUser, get_current_user
from engine.shared.internal_auth import verify_internal_auth
from engine.shared.logging import get_logger
from engine.shared.pulse import NoOpPulse, PulsePublisher

logger = get_logger(__name__)
router = APIRouter()


@router.post("/internal/ta/confirm_ltf")
async def internal_ta_confirm_ltf(
    request: Request,
    body: InternalLTFConfirmRequest,
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Lightweight LTF-only confirmation check.

    Called by the Go gateway's RunConfirmationPulse when the
    execution watcher detects price in the entry zone. Fetches
    only LTF candle data and runs only the 7 LTF confirmation
    checks. Returns in milliseconds, not seconds.

    This is the fast-path alternative to re-running the full
    /internal/ta/analyze pipeline.
    """
    container: Container = request.app.state.container
    user_id = request.headers.get("X-User-Id", "")
    if not user_id:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400, detail="X-User-Id header required for internal LTF confirm"
        )
    user_broker = await _resolve_user_broker(container, user_id)

    # Lazy-build the LTF confirmation service
    if not hasattr(container, "ltf_confirmation_service"):
        from engine.ta.common.services.ltf_confirmation.service import (
            LTFConfirmationService,
        )
        from engine.ta.smc.config import SMCConfig

        smc_config = SMCConfig()
        # Reuse analyzers from the TA orchestrator if available
        if hasattr(container, "ta_orchestrator"):
            orch = container.ta_orchestrator
            container.ltf_confirmation_service = LTFConfirmationService(
                smc_config=smc_config,
                swing_analyzer=orch.snapshot_builder.swing_analyzer,
                session_analyzer=orch.snapshot_builder.session_analyzer,
                sweep_analyzer=orch.snapshot_builder.sweep_analyzer,
                candle_analyzer=orch.smc_detector.candle_analyzer,
            )
        else:
            raise HTTPException(
                status_code=503,
                detail="TA orchestrator not initialized",
            )

    from engine.ta.common.services.ltf_confirmation.service import (
        LTFConfirmationRequest,
    )

    ltf_request = LTFConfirmationRequest(
        symbol=body.symbol,
        direction=body.direction,
        ltf_timeframe=body.ltf_timeframe,
        ob_upper=body.ob_upper,
        ob_lower=body.ob_lower,
        entry_price=body.entry_price,
        trace_id=body.trace_id,
        stop_loss=body.stop_loss,
        htf_timeframe=body.htf_timeframe,
    )

    result = await container.ltf_confirmation_service.confirm(
        ltf_request,
        user_broker,
    )

    return result.model_dump(mode="json")


@router.post("/internal/ta/analyze")
async def internal_ta_analyze(
    request: Request,
    body: InternalTARequest,
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Run TA analysis for the given symbols.

    Called by the Go gateway. Delegates to TAOrchestrator.analyze()
    for each symbol and returns the aggregated results.

    MULTI-TENANT: Each user has their own MT5 broker connection
    (MetaAPI or ZeroMQ EA). TA analysis uses the authenticated
    user's broker to fetch candles from their specific MT5 account.
    Different brokers may have different symbol names, available
    symbols, and candle data. If the user has not configured a
    broker connection, returns HTTP 503.
    """
    container: Container = request.app.state.container
    if not hasattr(container, "ta_orchestrator"):
        raise HTTPException(status_code=503, detail="TA orchestrator not initialized")
    user_id = request.headers.get("X-User-Id", "")
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-Id header required for internal TA analyze",
        )
    user_broker = await _resolve_user_broker(container, user_id)

    # Analyze symbols concurrently, bounded by TA_MAX_CONCURRENT_SYMBOL_ANALYSIS.
    # A sequential loop here serializes every symbol's multi-timeframe candle
    # fetch + detection, so an N-symbol request takes N x single-symbol time and
    # blows the gateway's TA_MACRO_PARALLEL_TIMEOUT_SECONDS budget, which makes
    # the gateway retry the whole cycle and never reach RAG/LLM. Bounding with
    # a semaphore lets the per-symbol work overlap while still capping load on
    # the user's single broker connection.
    from engine.config import get_ta_config

    semaphore = asyncio.Semaphore(get_ta_config().max_concurrent_symbol_analysis)

    def _error_result(symbol: str, exc: Exception) -> dict:
        logger.error(
            "internal_ta_analyze_failed",
            extra={
                "symbol": symbol,
                "error": str(exc),
                "trace_id": body.trace_id,
                "user_id": user_id,
            },
        )
        return {
            "status": "error",
            "symbol": symbol,
            "error": str(exc),
            "htf_timeframes": [],
            "ltf_timeframes": [],
            "snapshots": {},
            "smc_candidates": [],
            "snd_candidates": [],
            "smc_candidates_count": 0,
            "snd_candidates_count": 0,
            "alignment": {},
            "overall_trend": "NEUTRAL",
        }

    def _build_pulse(symbol: str):
        """Per-symbol pulse publisher for the gateway-driven path.

        The gateway already forwards X-User-Id, so we can broadcast on
        the user's private SSE channel exactly like the manual rerun
        endpoint. Falls back to NoOpPulse when the cache is missing so
        a transient cache outage never affects analysis.
        """
        cache = getattr(container, "cache", None)
        if cache is None or not user_id:
            return NoOpPulse()
        try:
            return PulsePublisher(cache=cache, user_id=user_id, symbol=symbol)
        except Exception:  # noqa: BLE001 - pulse must never break analysis
            return NoOpPulse()

    async def _analyze_one(symbol: str) -> dict:
        async with semaphore:
            pulse = _build_pulse(symbol)
            await pulse.emit("LOADING", f"Preparing analysis for {symbol}")
            try:
                return await container.ta_orchestrator.analyze(
                    symbol=symbol,
                    broker_client=user_broker,
                    user_id=user_id,
                    pulse=pulse,
                )
            except Exception as exc:  # noqa: BLE001 - per-symbol isolation
                return _error_result(symbol, exc)

    # gather preserves input order, so symbol_results aligns with body.symbols.
    results = await asyncio.gather(*(_analyze_one(symbol) for symbol in body.symbols))

    return {"symbol_results": list(results)}


@router.post("/internal/macro/collect")
async def internal_macro_collect(
    request: Request,
    body: InternalMacroRequest,
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Run all 8 macro collectors in parallel.

    Called by the Go gateway. Delegates to each macro collector
    and returns the aggregated results.

    MULTI-TENANT NOTE: Macro data (central bank speeches, COT reports,
    economic releases, news, calendar events, DXY, intermarket,
    sentiment) is market-wide data identical for all users. The
    collectors are global singletons by design. Auth is required to
    prevent unauthorized resource consumption.
    """
    container: Container = request.app.state.container

    # Pulse publisher for the user's SSE channel. The macro call is
    # cycle-scoped (not per-symbol), so the symbol label is "macro".
    # Falls back to NoOpPulse when cache/user_id is unavailable.
    user_id = (request.headers.get("X-User-Id") or "").strip()
    cache = getattr(container, "cache", None)
    if cache is not None and user_id:
        try:
            pulse = PulsePublisher(cache=cache, user_id=user_id, symbol="macro")
        except Exception:  # noqa: BLE001 - pulse must never break collection
            pulse = NoOpPulse()
    else:
        pulse = NoOpPulse()

    # Human-readable sub-step labels for each collector. Shown after the
    # CLAUDING verb as the macro row's text swaps in-place per collector.
    _collector_labels = {
        "central_bank": "Polling central bank feeds & rate decisions",
        "cot": "Fetching CFTC COT positioning",
        "economic": "Harvesting economic releases",
        "calendar": "Loading high-impact event calendar",
        "dxy": "Computing DXY momentum",
        "intermarket": "Analyzing intermarket correlations",
        "sentiment": "Deriving market sentiment",
    }

    collector_map = {
        "central_bank": container.cb_collector,
        "cot": container.cot_collector,
        "economic": container.economic_collector,
        "calendar": container.calendar_collector,
        "dxy": container.dxy_collector,
        "intermarket": container.intermarket_collector,
        "sentiment": container.sentiment_collector,
    }

    async def _collect_one(name: str, collector):
        """Run one collector, emitting a CLAUDING pulse on start and on
        completion. The pulse is best-effort; collection behaviour and
        per-collector isolation are unchanged.
        """
        label = _collector_labels.get(name, name)
        await pulse.emit("CLAUDING", label, source="macro")
        result = await collector.collect()
        await pulse.emit(
            "CLAUDING", f"{label} \u2014 done", source="macro", completed=True
        )
        return result

    tasks = {name: _collect_one(name, c) for name, c in collector_map.items()}
    raw_results = await asyncio.gather(
        *tasks.values(),
        return_exceptions=True,
    )

    datasets = {}
    errors = {}
    for name, result in zip(tasks.keys(), raw_results):
        if isinstance(result, Exception):
            logger.error(
                "internal_macro_collector_failed",
                extra={
                    "collector": name,
                    "error": str(result),
                    "trace_id": body.trace_id,
                },
            )
            datasets[name] = None
            errors[name] = str(result)
        else:
            if isinstance(result, dict):
                datasets[name] = result
            elif hasattr(result, "model_dump"):
                datasets[name] = result.model_dump(mode="json")
            else:
                datasets[name] = {"raw": str(result)}

    return {
        "central_bank": datasets.get("central_bank"),
        "cot": datasets.get("cot"),
        "economic": datasets.get("economic"),
        "calendar": datasets.get("calendar"),
        "dxy": datasets.get("dxy"),
        "intermarket": datasets.get("intermarket"),
        "sentiment": datasets.get("sentiment"),
        "errors": errors,
    }


@router.post("/internal/rag/retrieve")
async def internal_rag_retrieve(
    request: Request,
    body: InternalRAGRequest,
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Perform RAG retrieval with the given query parameters.

    Called by the Go gateway. Delegates to RAGOrchestrator.retrieve_context().
    """
    container: Container = request.app.state.container
    if not hasattr(container, "rag_orchestrator"):
        raise HTTPException(status_code=503, detail="RAG not initialized")

    user_id = (
        request.headers.get("X-User-Id") or getattr(body, "user_id", "") or ""
    ).strip()

    cache = getattr(container, "cache", None)
    if cache is not None and user_id:
        try:
            pulse = PulsePublisher(
                cache=cache, user_id=user_id, symbol=body.symbol or ""
            )
        except Exception:  # noqa: BLE001 - pulse must never break retrieval
            pulse = NoOpPulse()
    else:
        pulse = NoOpPulse()

    await pulse.emit("GERMINATING", "Querying rulebook knowledge base", source="rag")
    try:
        bundle = await container.rag_orchestrator.retrieve_context(
            body.query_text,
            user_id,
            strategy=body.strategy,
            framework=body.framework,
            setup_family=body.setup_family,
            direction=body.direction,
            timeframe=body.timeframe,
            style=body.style,
            trace_id=body.trace_id,
            symbol=body.symbol,
            all_frameworks=body.all_frameworks,
            all_setup_families=body.all_setup_families,
            has_smc_candidates=body.has_smc_candidates,
            has_snd_candidates=body.has_snd_candidates,
            has_macro_data=body.has_macro_data,
            has_cot_data=body.has_cot_data,
            has_rate_decision=body.has_rate_decision,
            has_high_impact_event=body.has_high_impact_event,
            has_dxy_data=body.has_dxy_data,
            has_qe_qt=body.has_qe_qt,
            has_stagflation=body.has_stagflation,
            has_cot_extremes=body.has_cot_extremes,
            has_tff_data=body.has_tff_data,
            has_core_inflation=body.has_core_inflation,
            has_safe_haven_elevated=body.has_safe_haven_elevated,
            has_commodity_currencies_weak=body.has_commodity_currencies_weak,
            dxy_momentum=body.dxy_momentum,
            risk_environment=body.risk_environment,
        )

        await pulse.emit(
            "GERMINATING",
            "Knowledge retrieval complete",
            source="rag",
            completed=True,
        )
        if hasattr(bundle, "model_dump"):
            return bundle.model_dump(mode="json")
        return {"context_bundle": str(bundle)}

    except Exception as exc:
        logger.exception(
            "internal_rag_retrieve_failed",
            extra={"trace_id": body.trace_id},
        )
        raise HTTPException(status_code=500, detail=f"RAG retrieval failed: {exc}")


@router.post("/internal/processor/process")
async def internal_processor_process(
    request: Request,
    body: InternalProcessorRequest,
    _: None = Depends(verify_internal_auth),
) -> Response:
    """Send assembled context to the Processor LLM.

    Called by the Go gateway. Delegates to AnalysisProcessor.
    The processor_input dict contains ta_analysis, macro_analysis,
    retrieved_knowledge, and metadata.

    The gateway forwards the authenticated user identity via four
    headers: X-User-Id, X-User-Tier, X-User-Role, X-User-Username.
    These are read first; the matching body fields are honoured as a
    fallback for callers that prefer a single transport. The user_id
    is REQUIRED — a missing value yields 400 so a misconfigured deploy
    fails loudly instead of silently dropping the user OS personalization.

    The return type is the FastAPI Response base class because the
    happy path returns a plain dict (FastAPI auto-encodes to JSON) but
    the QuotaExceededError branch returns a JSONResponse with custom
    status code (429) and Retry-After header. Annotating as Response
    keeps static analysers honest about both code paths.
    """
    container: Container = request.app.state.container

    # Header-first resolution (canonical channel — mirrors the
    # LTF-confirm handler). Body fields are a fallback for callers
    # that prefer a single transport.
    user_id = (request.headers.get("X-User-Id") or body.user_id or "").strip()
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-Id header (or user_id body field) is required",
        )

    # Tier and role default to safe non-privileged values so a missing
    # header NEVER elevates a user to admin or pro_managed. The
    # downstream _load_active_llm_connection guard enforces this again
    # as defense-in-depth.
    tier = (request.headers.get("X-User-Tier") or body.tier or "free").strip().lower()
    role = (
        (request.headers.get("X-User-Role") or body.role or "etradie").strip().lower()
    )
    username = (
        request.headers.get("X-User-Username") or body.username or user_id
    ).strip()
    if role not in ("admin", "etradie"):
        # Reject unknown roles defensively rather than coercing them to
        # the safer 'etradie' — a typo in a future deploy should fail
        # loudly, not silently downgrade.
        raise HTTPException(
            status_code=400,
            detail=f"X-User-Role must be 'admin' or 'etradie', got {role!r}",
        )

    user = AuthenticatedUser(
        user_id=user_id,
        username=username,
        role=role,
        tier=tier,
        status="active",  # The gateway only forwards calls for active users.
    )
    processor = await _resolve_user_processor(container, user)

    try:
        processor_input = ProcessorInput(**body.processor_input)

        cache = getattr(container, "cache", None)
        _proc_symbol = getattr(processor_input, "symbol", "") or ""
        if cache is not None and user_id:
            try:
                _proc_pulse = PulsePublisher(
                    cache=cache, user_id=user_id, symbol=_proc_symbol
                )
            except Exception:  # noqa: BLE001 - pulse must never break the LLM call
                _proc_pulse = NoOpPulse()
        else:
            _proc_pulse = NoOpPulse()
        await _proc_pulse.emit(
            "REASONING", "AI processor analyzing setup", source="processor"
        )

        result = await processor.process(
            processor_input,
            user_id=user.user_id,
            trace_id=body.trace_id,
        )

        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")
        if isinstance(result, dict):
            return result
        return {"raw": str(result)}

    except QuotaExceededError as exc:
        # The metering layer rejected the reservation. Log the rejection
        # at warning level so operators can correlate the SPA-side 429
        # toast to the gateway-side metering log entry by trace_id.
        # Then map to a structured 429 with a Retry-After header so the
        # SPA's axios interceptor surfaces a meaningful message.
        logger.warning(
            "internal_processor_quota_exceeded",
            extra={
                "user_id": user.user_id,
                "tier": user.tier,
                "trace_id": body.trace_id,
                "dimension": exc.dimension,
                "limit": exc.limit,
                "used": exc.used,
                "requested": exc.requested,
                "resets_at": exc.resets_at,
                "retry_after": exc.retry_after,
            },
        )
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(exc.retry_after)},
            content={
                "error": "llm quota exceeded",
                "dimension": exc.dimension,
                "limit": exc.limit,
                "used": exc.used,
                "requested": exc.requested,
                "resets_at": exc.resets_at,
                "retry_after": exc.retry_after,
            },
        )

    except MeteringUnavailableError as exc:
        # Gateway's metering layer is transiently unavailable. Map to
        # HTTP 503 + Retry-After so the gateway's engine_http.go
        # retries the call with backoff. No LLM call was made.
        # Audit ref: ADMIN-QUOTA-AUDIT-V3-A8.
        logger.warning(
            "internal_processor_metering_unavailable",
            extra={
                "user_id": user.user_id,
                "trace_id": body.trace_id,
                "retry_after": exc.retry_after,
            },
        )
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": str(exc.retry_after)},
            content={
                "error": "metering_unavailable",
                "detail": "Metering layer is temporarily unavailable; please retry shortly.",
                "retry_after": exc.retry_after,
                "trace_id": body.trace_id,
            },
        )

    except LLMDuplicateSuppressedError as exc:
        # This call was a duplicate of an in-flight / just-completed
        # identical analysis (same user_id + symbol + prompt_hash). The
        # idempotency guard deliberately did NOT run a second LLM call.
        # 409 Conflict: well-formed request, intentionally not executed
        # because an identical operation owns the result. The Go gateway
        # retries only 502/503/504, so a 409 surfaces without a retry
        # storm and the orchestrator records a benign per-symbol outcome.
        logger.info(
            "internal_processor_duplicate_suppressed",
            extra={
                "user_id": user.user_id,
                "trace_id": body.trace_id,
                "detail": str(exc),
            },
        )
        return JSONResponse(
            status_code=409,
            content={
                "error": "llm_duplicate_suppressed",
                "detail": str(exc),
                "trace_id": body.trace_id,
            },
        )

    except ProcessorInsufficientDataError as exc:
        # Sufficient-data preconditions did not hold for this symbol.
        # 400 because the request was structurally fine but the
        # assembled context did not carry the minimum data required
        # to produce a decision.
        logger.warning(
            "internal_processor_insufficient_data",
            extra={
                "user_id": user.user_id,
                "trace_id": body.trace_id,
                "detail": str(exc),
            },
        )
        return JSONResponse(
            status_code=400,
            content={
                "error": "insufficient_data",
                "detail": str(exc),
                "trace_id": body.trace_id,
            },
        )

    except (
        LLMTruncatedError,
        LLMSchemaViolationError,
        LLMSafetyFilterError,
        LLMRateLimitedError,
    ) as exc:
        # Per-symbol analysis-unavailable. The Go gateway already
        # does NOT retry 4xx (engine_http.go retries 502/503/504
        # only), so a 422 surfaces cleanly without triggering an
        # expensive retry storm. The orchestrator then continues
        # processing other symbols in the same cycle instead of
        # marking the whole pipeline as PIPELINE_ERROR.
        code_map = {
            LLMTruncatedError: "llm_truncated",
            LLMSchemaViolationError: "llm_schema_violation",
            LLMSafetyFilterError: "llm_safety_filter",
            LLMRateLimitedError: "llm_rate_limited",
        }
        code = code_map.get(type(exc), "llm_analysis_unavailable")
        logger.warning(
            "internal_processor_llm_analysis_unavailable",
            extra={
                "user_id": user.user_id,
                "trace_id": body.trace_id,
                "code": code,
                "detail": str(exc),
                "details": exc.details,
            },
        )
        body_out: dict = {
            "error": code,
            "detail": str(exc),
            "trace_id": body.trace_id,
        }
        # Surface the structured fields each typed error carries so an
        # operator can act without parsing the message string.
        if isinstance(exc, LLMTruncatedError):
            body_out["finish_reason"] = exc.finish_reason
            body_out["output_tokens"] = exc.output_tokens
            body_out["max_output_tokens"] = exc.max_output_tokens
            body_out["response_length"] = exc.response_length
        if isinstance(exc, LLMSchemaViolationError):
            body_out["validation_errors"] = exc.validation_errors
        return JSONResponse(status_code=422, content=body_out)

    except Exception as exc:
        logger.error(
            "internal_processor_failed",
            extra={"error": str(exc), "trace_id": body.trace_id},
        )
        raise HTTPException(status_code=500, detail=f"Processor failed: {exc}")


@router.post("/internal/debug/runcycle")
async def internal_debug_runcycle(
    request: Request,
    body: InternalDebugRunCycleRequest,
    _: None = Depends(verify_internal_auth),
) -> dict:
    """Persist analysis cycle outputs to /output/runcycle/ for debugging.

    Called by the Go gateway (fire-and-forget) after a successful
    analysis cycle to save the full pipeline data for offline
    inspection. Identical output format to /api/analysis/rerun
    but written to /output/runcycle/ instead of /output/rerun/.

    This endpoint does NOT affect the main pipeline flow. The
    gateway calls it in a background goroutine after the processor
    LLM completes, so execution and management continue unimpeded.
    """
    symbol = body.symbol.strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    try:
        saved = _save_debug_output(
            symbol,
            ta_data=body.ta_data,
            macro_data=body.macro_data,
            rag_data=body.rag_data,
            processor_data=body.processor_data,
            execution_request=body.execution_request,
            subdirectory="runcycle",
        )
    except Exception as exc:
        # Fire-and-forget contract: this endpoint persists debug
        # artifacts only and "does NOT affect the main pipeline flow".
        # A write failure (e.g. a non-writable /output in the
        # container) must therefore NEVER surface as an HTTP 500 on
        # the gateway's background call -- that just produces
        # engine_http_error_response noise for a successful cycle.
        # Log for observability (same as before) and degrade to a
        # 200 "skipped" response, mirroring the already-graceful
        # prompt-payload save path in the processor.
        logger.error(
            "debug_runcycle_save_failed",
            extra={
                "symbol": symbol,
                "error": str(exc),
                "trace_id": body.trace_id,
            },
        )
        return {
            "status": "skipped",
            "symbol": symbol,
            "reason": str(exc),
            "output_files": {},
        }

    return {
        "status": "saved",
        "symbol": symbol,
        "output_files": saved,
    }
