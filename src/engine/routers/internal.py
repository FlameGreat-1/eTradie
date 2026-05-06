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

from engine.dependencies import Container
from engine.helpers import _resolve_user_broker, _resolve_user_processor, _save_debug_output
from engine.processor.models.io import ProcessorInput
from engine.schemas import (
    InternalDebugRunCycleRequest,
    InternalLTFConfirmRequest,
    InternalMacroRequest,
    InternalProcessorRequest,
    InternalRAGRequest,
    InternalTARequest,
)
from engine.shared.auth import AuthenticatedUser, get_current_user
from engine.shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/internal/ta/confirm_ltf")
async def internal_ta_confirm_ltf(
    request: Request,
    body: InternalLTFConfirmRequest,
    user: AuthenticatedUser = Depends(get_current_user),
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
    user_broker = await _resolve_user_broker(container, user.user_id)

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
        ltf_request, user_broker,
    )

    return result.model_dump(mode="json")


@router.post("/internal/ta/analyze")
async def internal_ta_analyze(
    request: Request,
    body: InternalTARequest,
    user: AuthenticatedUser = Depends(get_current_user),
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
        raise HTTPException(
            status_code=503, detail="TA orchestrator not initialized"
        )
    user_broker = await _resolve_user_broker(container, user.user_id)

    results = []
    for symbol in body.symbols:
        try:
            result = await container.ta_orchestrator.analyze(
                symbol=symbol,
                broker_client=user_broker,
                user_id=user.user_id,
            )
            results.append(result)
        except Exception as exc:
            logger.error(
                "internal_ta_analyze_failed",
                extra={
                    "symbol": symbol,
                    "error": str(exc),
                    "trace_id": body.trace_id,
                    "user_id": user.user_id,
                },
            )
            results.append(
                {
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
            )

    return {"symbol_results": results}


@router.post("/internal/macro/collect")
async def internal_macro_collect(
    request: Request,
    body: InternalMacroRequest,
    user: AuthenticatedUser = Depends(get_current_user),
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

    collector_map = {
        "central_bank": container.cb_collector,
        "cot": container.cot_collector,
        "economic": container.economic_collector,
        "news": container.news_collector,
        "calendar": container.calendar_collector,
        "dxy": container.dxy_collector,
        "intermarket": container.intermarket_collector,
        "sentiment": container.sentiment_collector,
    }

    tasks = {name: c.collect() for name, c in collector_map.items()}
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
        "news": datasets.get("news"),
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
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Perform RAG retrieval with the given query parameters.

    Called by the Go gateway. Delegates to RAGOrchestrator.retrieve_context().
    """
    container: Container = request.app.state.container
    if not hasattr(container, "rag_orchestrator"):
        raise HTTPException(status_code=503, detail="RAG not initialized")

    try:
        bundle = await container.rag_orchestrator.retrieve_context(
            body.query_text,
            user.user_id,
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

        if hasattr(bundle, "model_dump"):
            return bundle.model_dump(mode="json")
        return {"context_bundle": str(bundle)}

    except Exception as exc:
        logger.error(
            "internal_rag_retrieve_failed",
            extra={"error": str(exc), "trace_id": body.trace_id},
        )
        raise HTTPException(status_code=500, detail=f"RAG retrieval failed: {exc}")


@router.post("/internal/processor/process")
async def internal_processor_process(
    request: Request,
    body: InternalProcessorRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Send assembled context to the Processor LLM.

    Called by the Go gateway. Delegates to AnalysisProcessor.
    The processor_input dict contains ta_analysis, macro_analysis,
    retrieved_knowledge, and metadata.
    """
    container: Container = request.app.state.container
    processor = await _resolve_user_processor(container, user.user_id)

    try:
        processor_input = ProcessorInput(**body.processor_input)
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
    user: AuthenticatedUser = Depends(get_current_user),
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
        logger.error(
            "debug_runcycle_save_failed",
            extra={
                "symbol": symbol,
                "error": str(exc),
                "trace_id": body.trace_id,
            },
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save runcycle debug output: {exc}",
        )

    return {
        "status": "saved",
        "symbol": symbol,
        "output_files": saved,
    }
