"""Analysis dashboard endpoints.

Routes:
    GET  /api/analysis/latest
    GET  /api/analysis/history
    GET  /api/analysis/stats
    GET  /api/analysis/stream-live
    GET  /api/analysis/{analysis_id}
    POST /api/analysis/rerun
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from engine.dependencies import Container
from engine.helpers import _resolve_user_broker, _resolve_user_processor, _save_debug_output
from engine.processor.mapping.dashboard_formatter import format_for_dashboard
from engine.processor.models.io import ProcessorInput
from engine.processor.storage.repositories.analysis_repository import AnalysisRepository
from engine.processor.storage.repositories.audit_repository import AuditRepository
from engine.processor.streaming import (
    SSE_HEARTBEAT_SECONDS,
    stream_channel_for_user,
)
from engine.shared.auth import AuthenticatedUser, get_current_user
from engine.shared.exceptions import ProcessorInsufficientDataError
from engine.shared.logging import get_logger
from engine.signal_extractors import derive_macro_signals, derive_ta_signals

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/analysis/latest")
async def get_latest_analyses(
    request: Request,
    pair: Optional[str] = None,
    limit: int = 20,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """List recent analyses for the dashboard."""
    container: Container = request.app.state.container
    if not hasattr(container, "processor_uow_factory"):
        raise HTTPException(status_code=503, detail="Processor not initialized")

    limit = min(limit, 100)

    async with container.db.read_session() as session:
        repo = AnalysisRepository(session)

        if pair:
            rows = await repo.get_latest_by_pair(pair.upper(), user_id=user.user_id, limit=limit)
        else:
            rows = await repo.list_recent_all(user_id=user.user_id, limit=limit)

    results = []
    for row in rows:
        display = format_for_dashboard(row.raw_output or {}, row)
        raw = row.raw_output or {}

        # Extract numeric trade levels for the dashboard chart.
        # These come from the raw LLM output structure.
        entry_zone = raw.get("entry_zone", {})
        sl_obj = raw.get("stop_loss", {})
        tps_list = raw.get("take_profits", [])

        trade_levels = None
        if row.direction and row.direction != "NO SETUP":
            entry_price = None
            if entry_zone.get("low") is not None and entry_zone.get("high") is not None:
                # Use midpoint of entry zone as the entry level.
                entry_price = (float(entry_zone["low"]) + float(entry_zone["high"])) / 2
            elif entry_zone.get("low") is not None:
                entry_price = float(entry_zone["low"])

            sl_price = float(sl_obj["price"]) if sl_obj.get("price") is not None else None

            tp_price = None
            if tps_list:
                # Prefer the final TP (TP3) for the chart line; fall back to the highest available.
                tp_entry = tps_list[-1] if isinstance(tps_list, list) and len(tps_list) > 0 else None
                if tp_entry and tp_entry.get("level") is not None:
                    tp_price = float(tp_entry["level"])

            if entry_price is not None or sl_price is not None or tp_price is not None:
                trade_levels = {
                    "entry": entry_price,
                    "stop_loss": sl_price,
                    "take_profit": tp_price,
                    "direction": row.direction,
                }

        results.append(
            {
                "analysis_id": row.analysis_id,
                "pair": row.pair,
                "direction": row.direction,
                "setup_grade": row.setup_grade,
                "confluence_score": row.confluence_score,
                "confidence": row.confidence,
                "proceed_to_module_b": row.proceed_to_module_b,
                "rr_ratio": row.rr_ratio,
                "trading_style": row.trading_style,
                "session": row.session,
                "llm_provider": row.llm_provider,
                "llm_model": row.llm_model,
                "status": row.status,
                "duration_ms": row.duration_ms,
                "created_at": (
                    row.created_at.isoformat() if row.created_at else None
                ),
                "display": {
                    "summary": display["summary"],
                    "analyzed_by": display["analyzed_by"],
                    "reasoning": display.get("reasoning", ""),
                },
                "trade_levels": trade_levels,
            }
        )

    return {"analyses": results, "count": len(results)}


@router.get("/api/analysis/history")
async def get_analysis_history(
    request: Request,
    pair: Optional[str] = None,
    status: Optional[str] = None,
    grade: Optional[str] = None,
    provider: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Paginated analysis history with filters.

    Query params:
      pair      - Filter by symbol (e.g. EURUSD)
      status    - Filter by status (success, no_setup, llm_error, ...)
      grade     - Filter by setup grade (A+, A, B, REJECT)
      provider  - Filter by LLM provider (anthropic, openai, ...)
      since     - ISO 8601 datetime lower bound (inclusive)
      until     - ISO 8601 datetime upper bound (inclusive)
      offset    - Pagination offset (default 0)
      limit     - Page size (default 20, max 100)

    Returns analyses array, total_count, offset, and limit for
    the frontend to build pagination controls.
    """
    container: Container = request.app.state.container
    if not hasattr(container, "processor_uow_factory"):
        raise HTTPException(status_code=503, detail="Processor not initialized")

    since_dt = None
    until_dt = None
    if since:
        try:
            since_dt = dt.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid 'since' datetime: {since}"
            )
    if until:
        try:
            until_dt = dt.fromisoformat(until.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid 'until' datetime: {until}"
            )

    limit = min(limit, 100)
    if offset < 0:
        offset = 0

    async with container.db.read_session() as session:
        repo = AnalysisRepository(session)
        rows, total_count = await repo.list_filtered(
            user_id=user.user_id,
            pair=pair,
            status=status,
            grade=grade,
            provider=provider,
            since=since_dt,
            until=until_dt,
            offset=offset,
            limit=limit,
        )

    results = []
    for row in rows:
        display = format_for_dashboard(row.raw_output or {}, row)
        results.append(
            {
                "analysis_id": row.analysis_id,
                "pair": row.pair,
                "direction": row.direction,
                "setup_grade": row.setup_grade,
                "confluence_score": row.confluence_score,
                "confidence": row.confidence,
                "proceed_to_module_b": row.proceed_to_module_b,
                "rr_ratio": row.rr_ratio,
                "trading_style": row.trading_style,
                "session": row.session,
                "llm_provider": row.llm_provider,
                "llm_model": row.llm_model,
                "status": row.status,
                "duration_ms": row.duration_ms,
                "created_at": (
                    row.created_at.isoformat() if row.created_at else None
                ),
                "display": {
                    "summary": display["summary"],
                    "analyzed_by": display["analyzed_by"],
                    "reasoning": display.get("reasoning", ""),
                },
            }
        )

    return {
        "analyses": results,
        "total_count": total_count,
        "offset": offset,
        "limit": limit,
    }


@router.get("/api/analysis/stats")
async def get_analysis_stats(
    request: Request,
    pair: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Aggregate analysis statistics for the dashboard.

    Returns total count, success rate, grade distribution,
    average confluence score, average duration, and breakdowns
    by provider and pair. Optionally filtered by pair and date range.
    """
    container: Container = request.app.state.container
    if not hasattr(container, "processor_uow_factory"):
        raise HTTPException(status_code=503, detail="Processor not initialized")

    since_dt = None
    until_dt = None
    if since:
        try:
            since_dt = dt.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid 'since' datetime: {since}"
            )
    if until:
        try:
            until_dt = dt.fromisoformat(until.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid 'until' datetime: {until}"
            )

    async with container.db.read_session() as session:
        repo = AnalysisRepository(session)
        stats = await repo.get_stats(user_id=user.user_id, pair=pair, since=since_dt, until=until_dt)
    return stats


# NOTE: The SSE /api/analysis/stream-live route is registered BEFORE
# /api/analysis/{analysis_id} on purpose. FastAPI matches routes in
# declaration order and the {analysis_id} catch-all would otherwise
# swallow "stream-live" and return 404 from get_analysis_detail.


@router.get("/api/analysis/stream-live")
async def stream_live_analysis(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """SSE endpoint for the dashboard's live-reasoning panel.

    Streams frames published by the processor during an analysis
    cycle run by the authenticated user. Each frame is a single
    JSON object with a ``type`` field (``status``,
    ``reasoning_chunk``, ``final``, or ``error``).

    Each user has a private pub/sub channel so concurrent cycles
    across users never cross-contaminate and a terminal frame from
    one user does not close another user's stream.
    """
    container: Container = request.app.state.container
    channel_name = stream_channel_for_user(user.user_id)

    async def event_generator():
        pubsub = container.cache.pubsub()
        await pubsub.subscribe(channel_name)
        logger.info(
            "stream_subscriber_started",
            extra={"user_id": user.user_id, "channel": channel_name},
        )

        last_keepalive = asyncio.get_event_loop().time()

        try:
            while True:
                if await request.is_disconnected():
                    break

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )

                if message and message.get("type") == "message":
                    try:
                        data_raw = message["data"]
                        if isinstance(data_raw, bytes):
                            data_str = data_raw.decode("utf-8")
                        else:
                            data_str = str(data_raw)
                        yield f"data: {data_str}\n\n"
                        last_keepalive = asyncio.get_event_loop().time()

                        data_obj = json.loads(data_str)
                        if data_obj.get("type") in ("final", "error"):
                            break
                    except Exception as exc:
                        logger.warning(
                            "stream_parse_error",
                            extra={
                                "user_id": user.user_id,
                                "error": str(exc),
                            },
                        )
                else:
                    now = asyncio.get_event_loop().time()
                    if now - last_keepalive >= SSE_HEARTBEAT_SECONDS:
                        yield ": keepalive\n\n"
                        last_keepalive = now
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "stream_generator_error",
                extra={"user_id": user.user_id, "error": str(exc)},
                exc_info=True,
            )
        finally:
            async def _cleanup_pubsub():
                try:
                    await pubsub.unsubscribe(channel_name)
                except Exception:
                    pass
                try:
                    await pubsub.aclose()
                except Exception:
                    pass

            # Run cleanup in a background task so it doesn't get cancelled
            # by the exact CancelledError that triggered this finally block.
            asyncio.create_task(_cleanup_pubsub())

            logger.info(
                "stream_subscriber_stopped",
                extra={"user_id": user.user_id, "channel": channel_name},
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/analysis/{analysis_id}")
async def get_analysis_detail(
    request: Request,
    analysis_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Full analysis detail including LLM reasoning and raw output."""
    container: Container = request.app.state.container
    if not hasattr(container, "processor_uow_factory"):
        raise HTTPException(status_code=503, detail="Processor not initialized")

    async with container.db.read_session() as session:
        repo = AnalysisRepository(session)
        row = await repo.get_by_analysis_id(analysis_id, user_id=user.user_id)

        audit_rows = []
        audit_repo = AuditRepository(session)
        audit_rows = await audit_repo.get_by_analysis_id(analysis_id, user_id=user.user_id)

    if not row:
        raise HTTPException(
            status_code=404, detail=f"Analysis '{analysis_id}' not found"
        )

    audit_data = None
    if audit_rows:
        a = audit_rows[0]
        audit_data = {
            "llm_model": a.llm_model,
            "llm_input_tokens": a.llm_input_tokens,
            "llm_output_tokens": a.llm_output_tokens,
            "llm_duration_ms": a.llm_duration_ms,
            "retrieval_strategy": a.retrieval_strategy,
            "retrieval_chunks_count": a.retrieval_chunks_count,
            "retrieval_coverage": a.retrieval_coverage,
            "citations": a.citations,
            "validation_passed": a.validation_passed,
            "validation_errors": a.validation_errors,
        }

    raw_data = row.raw_output or {}
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except Exception:
            raw_data = {}

    display = format_for_dashboard(raw_data, row)

    # Override confidence since we have it correctly inside raw_data as well
    if "confidence" in raw_data and raw_data["confidence"] is not None:
        confidence = raw_data["confidence"]
    else:
        confidence = row.confidence

    return {
        "analysis_id": row.analysis_id,
        "pair": row.pair,
        "direction": row.direction,
        "setup_grade": row.setup_grade,
        "confluence_score": row.confluence_score,
        "confidence": confidence,
        "proceed_to_module_b": row.proceed_to_module_b,
        "rr_ratio": row.rr_ratio,
        "trading_style": row.trading_style,
        "session": row.session,
        "llm_provider": row.llm_provider,
        "llm_model": row.llm_model,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "raw_output": raw_data,
        "display": {
            "summary": display["summary"],
            "reasoning": display["reasoning"],
            "macro_summary": display["macro_summary"],
            "technical_summary": display["technical_summary"],
            "trade_plan": display["trade_plan"],
            "confluence_breakdown": display["confluence_breakdown"],
            "risk_info": display["risk_info"],
            "event_warnings": display["event_warnings"],
            "analyzed_by": display["analyzed_by"],
        },
        "audit": audit_data,
    }


# -- Re-run analysis endpoint --------------------------------------------


@router.post("/api/analysis/rerun")
async def rerun_analysis(
    request: Request,
    symbol: str,
    trace_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Re-trigger analysis for a single symbol on demand.

    Uses the current processor config (provider, model, temperature).
    Calls the same internal pipeline as the Go gateway but bypasses
    the scheduler. Useful for testing a new model or re-checking
    a symbol without waiting for the next scheduled cycle.

    This endpoint calls the Python-side TA, Macro, RAG, and Processor
    in sequence. It does NOT go through the Go gateway's guards or
    execution routing (those are gateway-side concerns).
    """
    container: Container = request.app.state.container
    processor = await _resolve_user_processor(container, user.user_id)
    if not hasattr(container, "ta_orchestrator"):
        raise HTTPException(
            status_code=503, detail="TA orchestrator not initialized"
        )
    user_broker = await _resolve_user_broker(container, user.user_id)

    symbol = symbol.strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    # Step 1: Run TA analysis for the symbol using the user's broker.
    try:
        ta_result = await container.ta_orchestrator.analyze(
            symbol=symbol,
            broker_client=user_broker,
            user_id=user.user_id,
        )
    except Exception as exc:
        logger.error("rerun_ta_failed", extra={"symbol": symbol, "error": str(exc)})
        raise HTTPException(status_code=500, detail=f"TA analysis failed: {exc}")

    if isinstance(ta_result, dict):
        ta_analysis = ta_result
    elif hasattr(ta_result, "model_dump"):
        ta_analysis = ta_result.model_dump(mode="json")
    else:
        ta_analysis = {"raw": str(ta_result)}

    # Check if TA analysis produced usable data. If the TA orchestrator
    # returned an error or insufficient_data status with no candidates,
    # fail early with 500 rather than proceeding to macro/RAG/processor.
    ta_status = ta_analysis.get("status", "")
    ta_has_candidates = bool(ta_analysis.get("smc_candidates")) or bool(
        ta_analysis.get("snd_candidates")
    )
    if ta_status in ("error", "insufficient_data") and not ta_has_candidates:
        ta_error = ta_analysis.get("error", "unknown error")
        saved = _save_debug_output(symbol, ta_data=ta_analysis, subdirectory="rerun")
        return {
            "status": "completed",
            "symbol": symbol,
            "result": {
                "direction": "NO SETUP",
                "reason": f"TA analysis: {ta_error}",
                "proceed_to_module_b": False,
            },
            "output_files": saved,
        }

    # Step 2: Run macro collection.
    macro_analysis: dict = {}
    try:
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
        raw_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for name, result in zip(tasks.keys(), raw_results):
            if isinstance(result, Exception):
                macro_analysis[name] = None
            elif isinstance(result, dict):
                macro_analysis[name] = result
            elif hasattr(result, "model_dump"):
                macro_analysis[name] = result.model_dump(mode="json")
            else:
                macro_analysis[name] = {"raw": str(result)}
    except Exception as exc:
        logger.error(
            "rerun_macro_failed", extra={"symbol": symbol, "error": str(exc)}
        )
        raise HTTPException(
            status_code=500, detail=f"Macro collection failed: {exc}"
        )

    # Derive enriched macro signal flags from collected data.
    # This replicates what the Go gateway's macro_extractor.go and
    # assembler.go do, so the rerun endpoint produces identical
    # RAG queries and processor metadata as the normal pipeline.
    macro_signals = derive_macro_signals(macro_analysis)
    ta_signals = derive_ta_signals(ta_analysis)

    # Build a rich query text matching the Go gateway's BuildQueryText.
    query_parts: list[str] = [symbol]
    if ta_signals["direction"]:
        dir_word = {
            "long": "bullish",
            "short": "bearish",
            "neutral": "neutral",
        }.get(
            ta_signals["direction"],
            ta_signals["direction"],
        )
        query_parts.append(dir_word)
    if ta_signals["overall_trend"] and ta_signals["overall_trend"] != "NEUTRAL":
        query_parts.append(f"trend {ta_signals['overall_trend'].lower()}")
    if ta_signals["framework"]:
        query_parts.append(ta_signals["framework"].upper())
    for pattern in ta_signals["patterns"]:
        query_parts.append(pattern.lower().replace("_", " "))
    for family in ta_signals["setup_families"]:
        query_parts.append(family.replace("_", " "))
    if macro_signals["fed_tone"]:
        query_parts.append(f"Fed {macro_signals['fed_tone'].lower()}")
    if macro_signals["ecb_tone"]:
        query_parts.append(f"ECB {macro_signals['ecb_tone'].lower()}")
    if macro_signals["has_qe_qt"]:
        action = macro_signals.get("qe_qt_action", "qe").lower()
        bank = macro_signals.get("qe_qt_bank", "central bank")
        query_parts.append(f"{bank} {action}")
        if macro_signals.get("balance_sheet_direction"):
            query_parts.append(
                f"balance sheet {macro_signals['balance_sheet_direction'].lower()}"
            )
        if action == "qe":
            query_parts.append("quantitative easing asset purchases")
        elif action == "qt":
            query_parts.append("quantitative tightening balance sheet reduction")
    if macro_signals["has_rate_decision"]:
        query_parts.append("rate decision interest rate")
    if macro_signals["has_nfp"]:
        query_parts.append("NFP non-farm payrolls")
    if macro_signals["has_cpi"]:
        query_parts.append("CPI consumer price index inflation")
    if macro_signals["dxy_momentum"] and macro_signals["dxy_momentum"] != "FLAT":
        query_parts.append(f"DXY momentum {macro_signals['dxy_momentum'].lower()}")
    if macro_signals["cot_extremes"]:
        for ccy in macro_signals["cot_extremes"]:
            query_parts.append(f"{ccy} COT extreme positioning contrarian risk")
    if macro_signals["has_tff_data"]:
        query_parts.append("TFF leveraged funds data available")
    if macro_signals["stagflation_detected"]:
        query_parts.append("stagflation detected high inflation negative growth")
    if macro_signals["safe_haven_elevated"]:
        query_parts.append("safe haven demand elevated JPY CHF gold")
    if macro_signals["commodity_currencies_weak"]:
        query_parts.append("commodity currencies weak AUD NZD CAD risk-off")
    if (
        macro_signals["risk_environment"]
        and macro_signals["risk_environment"] != "NEUTRAL"
    ):
        query_parts.append(
            f"risk environment {macro_signals['risk_environment'].lower()}"
        )
    query_text = " ".join(query_parts)

    # Step 3: RAG retrieval (mandatory).
    # The RAG knowledge base is the rulebook the LLM reasons over.
    # Without it the LLM cannot cite rules, score confluence, or
    # grade setups. RAG failure is a hard stop.
    if not hasattr(container, "rag_orchestrator"):
        raise HTTPException(
            status_code=503,
            detail="RAG knowledge base not initialized. The LLM cannot reason without the rulebook.",
        )

    try:
        bundle = await container.rag_orchestrator.retrieve_context(
            query_text,
            user.user_id,
            strategy=None,
            framework=ta_signals["framework"] or None,
            setup_family=(
                ta_signals["setup_families"][0]
                if ta_signals["setup_families"]
                else None
            ),
            direction=ta_signals["direction"] or None,
            timeframe=None,
            style=None,
            trace_id=trace_id,
            symbol=symbol,
            all_frameworks=ta_signals["all_frameworks"],
            all_setup_families=ta_signals["setup_families"],
            has_smc_candidates=ta_signals["has_smc"],
            has_snd_candidates=ta_signals["has_snd"],
            has_macro_data=macro_signals["has_macro_data"],
            has_cot_data=macro_signals["has_cot_data"],
            has_rate_decision=macro_signals["has_rate_decision"],
            has_high_impact_event=macro_signals["has_high_impact_event"],
            has_dxy_data=macro_signals["has_dxy_data"],
            has_qe_qt=macro_signals["has_qe_qt"],
            has_stagflation=macro_signals["stagflation_detected"],
            has_cot_extremes=len(macro_signals["cot_extremes"]) > 0,
            has_tff_data=macro_signals["has_tff_data"],
            has_core_inflation=macro_signals["has_core_inflation"],
            has_safe_haven_elevated=macro_signals["safe_haven_elevated"],
            has_commodity_currencies_weak=macro_signals[
                "commodity_currencies_weak"
            ],
            dxy_momentum=macro_signals["dxy_momentum"] or None,
            risk_environment=macro_signals["risk_environment"] or None,
        )
        if hasattr(bundle, "model_dump"):
            retrieved_knowledge = bundle.model_dump(mode="json")
        elif isinstance(bundle, dict):
            retrieved_knowledge = bundle
        else:
            retrieved_knowledge = {}
    except Exception as exc:
        logger.error(
            "rerun_rag_failed", extra={"symbol": symbol, "error": str(exc)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"RAG retrieval failed: {exc}. The LLM cannot reason without the knowledge base.",
        )

    if not retrieved_knowledge:
        raise HTTPException(
            status_code=500,
            detail="RAG returned empty knowledge base. The LLM cannot reason without rulebook context.",
        )

    # --- rerun_analysis continues in _rerun_process_and_return below ---
    return await _rerun_process_and_return(
        container=container,
        processor=processor,
        user=user,
        symbol=symbol,
        trace_id=trace_id,
        ta_analysis=ta_analysis,
        macro_analysis=macro_analysis,
        macro_signals=macro_signals,
        ta_signals=ta_signals,
        retrieved_knowledge=retrieved_knowledge,
    )


async def _rerun_process_and_return(
    *,
    container: Container,
    processor,
    user: AuthenticatedUser,
    symbol: str,
    trace_id: Optional[str],
    ta_analysis: dict,
    macro_analysis: dict,
    macro_signals: dict,
    ta_signals: dict,
    retrieved_knowledge: dict,
) -> dict:
    """Build enriched metadata matching the Go gateway's assembler.go output,
    run the processor LLM, and return the final result.

    Split from rerun_analysis to keep the endpoint function under the
    token limit while preserving the exact same logic.
    """
    available_datasets = [
        name
        for name in [
            "central_bank",
            "cot",
            "economic",
            "news",
            "calendar",
            "dxy",
            "intermarket",
            "sentiment",
        ]
        if macro_analysis.get(name) is not None
    ]
    metadata: dict = {
        "symbol": symbol,
        "source": "dashboard_rerun",
        "trace_id": trace_id or "",
        "overall_trend": ta_signals["overall_trend"],
        "macro_datasets_available": available_datasets,
    }
    if macro_signals["risk_environment"]:
        metadata["risk_environment"] = macro_signals["risk_environment"]
    metadata["stagflation_detected"] = macro_signals["stagflation_detected"]
    metadata["safe_haven_elevated"] = macro_signals["safe_haven_elevated"]
    metadata["commodity_currencies_weak"] = macro_signals[
        "commodity_currencies_weak"
    ]
    if macro_signals["dxy_momentum"]:
        metadata["dxy_momentum"] = macro_signals["dxy_momentum"]
    metadata["cot_extremes_count"] = len(macro_signals["cot_extremes"])
    if macro_signals["cot_extremes"]:
        metadata["cot_extremes_currencies"] = macro_signals["cot_extremes"]
    metadata["has_tff_data"] = macro_signals["has_tff_data"]
    metadata["has_qe_qt"] = macro_signals["has_qe_qt"]
    if macro_signals["has_qe_qt"]:
        metadata["qe_qt_action"] = macro_signals.get("qe_qt_action", "")
        metadata["qe_qt_bank"] = macro_signals.get("qe_qt_bank", "")
        metadata["balance_sheet_direction"] = macro_signals.get(
            "balance_sheet_direction", ""
        )
    metadata["has_core_inflation"] = macro_signals["has_core_inflation"]
    # Propagate RAG metadata if present in the bundle.
    for key in [
        "strategy_used",
        "coverage_result",
        "conflict_result",
        "total_chunks_returned",
        "coverage_gaps",
        "conflict_details",
    ]:
        if key in retrieved_knowledge:
            metadata[f"rag_{key}"] = retrieved_knowledge[key]

    # Step 4: Run processor LLM.
    try:
        processor_input = ProcessorInput(
            symbol=symbol,
            ta_analysis=ta_analysis,
            macro_analysis=macro_analysis,
            retrieved_knowledge=retrieved_knowledge,
            metadata=metadata,
        )
        result = await processor.process(
            processor_input,
            user_id=user.user_id,
            trace_id=trace_id,
        )
    except ProcessorInsufficientDataError as exc:
        logger.info(
            "rerun_processor_no_setup", extra={"symbol": symbol, "reason": str(exc)}
        )
        saved = _save_debug_output(
            symbol,
            ta_data=ta_analysis,
            macro_data=macro_analysis,
            rag_data=retrieved_knowledge,
            subdirectory="rerun",
        )
        return {
            "status": "completed",
            "symbol": symbol,
            "result": {
                "direction": "NO SETUP",
                "reason": str(exc),
                "proceed_to_module_b": False,
            },
            "output_files": saved,
        }
    except Exception as exc:
        logger.error(
            "rerun_processor_failed", extra={"symbol": symbol, "error": str(exc)}
        )
        saved = _save_debug_output(
            symbol,
            ta_data=ta_analysis,
            macro_data=macro_analysis,
            rag_data=retrieved_knowledge,
            subdirectory="rerun",
        )
        return {
            "status": "error",
            "symbol": symbol,
            "result": {
                "direction": "LLM_ERROR",
                "reason": f"Processor failed: {exc}",
                "proceed_to_module_b": False,
            },
            "output_files": saved,
        }

    # Build processor result dict.
    if hasattr(result, "model_dump"):
        processor_dict = result.model_dump(mode="json")
    elif isinstance(result, dict):
        processor_dict = result
    else:
        processor_dict = {"raw": str(result)}

    saved = _save_debug_output(
        symbol,
        ta_data=ta_analysis,
        macro_data=macro_analysis,
        rag_data=retrieved_knowledge,
        processor_data=processor_dict,
        subdirectory="rerun",
    )
    return {
        "status": "completed",
        "symbol": symbol,
        "result": processor_dict,
        "output_files": saved,
    }
