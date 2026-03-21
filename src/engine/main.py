from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from datetime import datetime as dt, timezone

from fastapi import FastAPI, HTTPException, Request
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

from engine.config import get_rag_config, get_settings
from engine.dependencies import Container
from engine.shared.logging import configure_logging, get_logger
from engine.shared.metrics.prometheus import APP_INFO
from engine.shared.tracing.otel import init_tracing
from engine.macro.scheduler_jobs import register_macro_jobs
from engine.ta.scheduler_jobs import register_ta_jobs
from engine.processor.constants import AVAILABLE_MODELS, DEFAULT_MODELS, LLMProvider
from engine.processor.mapping.dashboard_formatter import format_for_dashboard
from engine.processor.models.io import ProcessorInput
from engine.shared.store import RedisSymbolReader
from engine.signal_extractors import derive_macro_signals, derive_ta_signals

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(log_level=settings.app_log_level, json_output=settings.json_logs)

    if not settings.is_testing:
        init_tracing(
            service_name=settings.otel_service_name,
            otlp_endpoint=settings.otel_exporter_otlp_endpoint,
        )

    container = Container()
    app.state.container = container

    APP_INFO.info({"version": "1.0.0", "environment": settings.app_env.value})

    db_ok = await container.db.health_check()
    cache_ok = await container.cache.health_check()
    logger.info("startup_health", db=db_ok, cache=cache_ok)

    # Publish the dynamic Correlation matrix to Redis for the Go Exposure Engine
    try:
        from engine.shared.models.currency import get_correlation_config
        corr_config = get_correlation_config()
        await container.cache.set(
            namespace="correlation",
            key="config",
            value=corr_config.model_dump(mode="json"),
            ttl_seconds=86400 * 30,  # Refresh every 30 days or on restart
        )
        logger.info("correlation_config_published_to_redis")
    except Exception as e:
        logger.error("failed_to_publish_correlation_config", error=str(e))

    rag_config = get_rag_config()
    if rag_config.enabled:
        await container.build_rag()

        if rag_config.ingest_on_startup:
            await container.rag_bootstrap_service.bootstrap()
            rag_ready = await container.rag_bootstrap_service.check_readiness()
            logger.info("rag_startup", ready=rag_ready)

        rag_health = await container.rag_health_service.check()
        logger.info(
            "rag_health_startup",
            overall=rag_health.overall_healthy,
            vectorstore=rag_health.vectorstore.connected,
            database=rag_health.database_connected,
            embedding=rag_health.embedding_provider_ready,
        )

    register_macro_jobs(
        container.scheduler,
        cb_collector_fn=container.cb_collector.collect,
        cot_collector_fn=container.cot_collector.collect,
        economic_collector_fn=container.economic_collector.collect,
        news_collector_fn=container.news_collector.collect,
        calendar_collector_fn=container.calendar_collector.collect,
        dxy_collector_fn=container.dxy_collector.collect,
        intermarket_collector_fn=container.intermarket_collector.collect,
        sentiment_collector_fn=container.sentiment_collector.collect,
        poll_cb=settings.poll_interval_central_bank_rss,
        poll_news=settings.poll_interval_news,
        poll_calendar=settings.poll_interval_calendar,
        poll_cot=settings.poll_interval_cot,
        poll_dxy=settings.poll_interval_dxy,
        poll_intermarket=settings.poll_interval_intermarket,
        poll_sentiment=settings.poll_interval_sentiment,
        poll_economic=settings.poll_interval_economic_data,
    )

    # -- Processor LLM -------------------------------------------------------
    container.build_processor()
    logger.info(
        "processor_built",
        provider=container.processor_config.llm_provider,
        model=container.processor_config.model_name,
    )

    # -- TA Data Infrastructure ----------------------------------------------
    # The Go gateway owns the symbol selection via Redis.
    # RedisSymbolReader reads from the same Redis key the Go gateway writes to.
    # TA data jobs (candle refresh, backfill, broker sync) use this reader
    # to know which symbols to fetch data for.
    symbol_reader = RedisSymbolReader(cache=container.cache)
    app.state.symbol_reader = symbol_reader

    register_ta_jobs(
        container.scheduler,
        symbol_store=symbol_reader,
        broker_client=container.mt5_client,
        candle_repository=container.candle_repository,
    )

    container.scheduler.start()
    logger.info("application_started", env=settings.app_env.value)

    yield

    await container.shutdown()
    logger.info("application_stopped")


# -- Request/Response schemas for dashboard API ------------------------------


class ProcessorConfigResponse(BaseModel):
    llm_provider: str
    model_name: str
    temperature: float
    max_output_tokens: int
    supported_providers: list[str]


class ProcessorConfigUpdateRequest(BaseModel):
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(default=None, ge=1024, le=131072)
    api_key: Optional[str] = Field(default=None, description="API key for the new provider")
    api_base_url: Optional[str] = Field(default=None, description="Base URL for self-hosted")


# -- Request schemas for internal gateway endpoints --------------------------


class InternalTARequest(BaseModel):
    symbols: list[str]
    trace_id: Optional[str] = None


class InternalMacroRequest(BaseModel):
    trace_id: Optional[str] = None

class InternalRAGRequest(BaseModel):
    query_text: str
    strategy: Optional[str] = None
    framework: Optional[str] = None
    setup_family: Optional[str] = None
    direction: Optional[str] = None
    timeframe: Optional[str] = None
    style: Optional[str] = None
    symbol: Optional[str] = None
    all_frameworks: list[str] = Field(default_factory=list)
    all_setup_families: list[str] = Field(default_factory=list)
    has_smc_candidates: bool = False
    has_snd_candidates: bool = False
    has_macro_data: bool = False
    has_cot_data: bool = False
    has_rate_decision: bool = False
    has_high_impact_event: bool = False
    has_dxy_data: bool = False
    has_qe_qt: bool = False
    has_stagflation: bool = False
    has_cot_extremes: bool = False
    has_tff_data: bool = False
    has_core_inflation: bool = False
    has_safe_haven_elevated: bool = False
    has_commodity_currencies_weak: bool = False
    dxy_momentum: Optional[str] = None
    risk_environment: Optional[str] = None
    trace_id: Optional[str] = None



class InternalProcessorRequest(BaseModel):
    processor_input: dict
    trace_id: Optional[str] = None


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="eTradie Engine",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # -- Health endpoints ----------------------------------------------------

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/health/rag")
    async def rag_health(request: Request) -> dict:
        container: Container = request.app.state.container
        if not hasattr(container, "rag_health_service"):
            return {"status": "disabled"}
        status = await container.rag_health_service.check()
        return {
            "status": "healthy" if status.overall_healthy else "degraded",
            "vectorstore_connected": status.vectorstore.connected,
            "database_connected": status.database_connected,
            "embedding_ready": status.embedding_provider_ready,
            "documents_count": status.vectorstore.documents_collection_count,
            "scenarios_count": status.vectorstore.scenarios_collection_count,
        }

    # -- Internal endpoints for Go gateway -----------------------------------

    @app.post("/internal/ta/analyze")
    async def internal_ta_analyze(request: Request, body: InternalTARequest) -> dict:
        """Run TA analysis for the given symbols.

        Called by the Go gateway. Delegates to TAOrchestrator.analyze()
        for each symbol and returns the aggregated results.
        """
        container: Container = request.app.state.container
        if not hasattr(container, "ta_orchestrator"):
            raise HTTPException(status_code=503, detail="TA orchestrator not initialized")

        results = []
        for symbol in body.symbols:
            try:
                result = await container.ta_orchestrator.analyze(symbol=symbol)
                results.append(result)
            except Exception as exc:
                logger.error(
                    "internal_ta_analyze_failed",
                    extra={"symbol": symbol, "error": str(exc), "trace_id": body.trace_id},
                )
                results.append({
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
                })

        return {"symbol_results": results}

    @app.post("/internal/macro/collect")
    async def internal_macro_collect(request: Request, body: InternalMacroRequest) -> dict:
        """Run all 8 macro collectors in parallel.

        Called by the Go gateway. Delegates to each macro collector
        and returns the aggregated results.
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
            *tasks.values(), return_exceptions=True,
        )

        datasets = {}
        errors = {}
        for name, result in zip(tasks.keys(), raw_results):
            if isinstance(result, Exception):
                logger.error(
                    "internal_macro_collector_failed",
                    extra={"collector": name, "error": str(result), "trace_id": body.trace_id},
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


    @app.post("/internal/rag/retrieve")
    async def internal_rag_retrieve(request: Request, body: InternalRAGRequest) -> dict:
        """Perform RAG retrieval with the given query parameters.

        Called by the Go gateway. Delegates to RAGOrchestrator.retrieve_context().
        """
        container: Container = request.app.state.container
        if not hasattr(container, "rag_orchestrator"):
            raise HTTPException(status_code=503, detail="RAG not initialized")

        try:
            bundle = await container.rag_orchestrator.retrieve_context(
                body.query_text,
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

    @app.post("/internal/processor/process")
    async def internal_processor_process(request: Request, body: InternalProcessorRequest) -> dict:
        """Send assembled context to the Processor LLM.

        Called by the Go gateway. Delegates to AnalysisProcessor.
        The processor_input dict contains ta_analysis, macro_analysis,
        retrieved_knowledge, and metadata.
        """
        container: Container = request.app.state.container
        if not hasattr(container, "processor"):
            raise HTTPException(status_code=503, detail="Processor not initialized")

        try:
            processor_input = ProcessorInput(**body.processor_input)
            result = await container.processor.process(
                processor_input,
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

    # -- Analysis dashboard endpoints ----------------------------------------

    @app.get("/api/analysis/latest")
    async def get_latest_analyses(
        request: Request,
        pair: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """List recent analyses for the dashboard."""
        container: Container = request.app.state.container
        if not hasattr(container, "processor_analysis_repo"):
            raise HTTPException(status_code=503, detail="Processor not initialized")

        repo = container.processor_analysis_repo
        limit = min(limit, 100)

        if pair:
            rows = await repo.get_latest_by_pair(pair.upper(), limit=limit)
        else:
            rows = await repo.list_recent_all(limit=limit)

        results = []
        for row in rows:
            display = format_for_dashboard(row.raw_output or {}, row)
            results.append({
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
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "display": {
                    "summary": display["summary"],
                    "analyzed_by": display["analyzed_by"],
                },
            })

        return {"analyses": results, "count": len(results)}

    @app.get("/api/analysis/history")
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
        if not hasattr(container, "processor_analysis_repo"):
            raise HTTPException(status_code=503, detail="Processor not initialized")

        since_dt = None
        until_dt = None
        if since:
            try:
                since_dt = dt.fromisoformat(since.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid 'since' datetime: {since}")
        if until:
            try:
                until_dt = dt.fromisoformat(until.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid 'until' datetime: {until}")

        limit = min(limit, 100)
        if offset < 0:
            offset = 0

        repo = container.processor_analysis_repo
        rows, total_count = await repo.list_filtered(
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
            results.append({
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
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "display": {
                    "summary": display["summary"],
                    "analyzed_by": display["analyzed_by"],
                },
            })

        return {
            "analyses": results,
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
        }

    @app.get("/api/analysis/stats")
    async def get_analysis_stats(
        request: Request,
        pair: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> dict:
        """Aggregate analysis statistics for the dashboard.

        Returns total count, success rate, grade distribution,
        average confluence score, average duration, and breakdowns
        by provider and pair. Optionally filtered by pair and date range.
        """
        container: Container = request.app.state.container
        if not hasattr(container, "processor_analysis_repo"):
            raise HTTPException(status_code=503, detail="Processor not initialized")

        from datetime import datetime as dt

        since_dt = None
        until_dt = None
        if since:
            try:
                since_dt = dt.fromisoformat(since.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid 'since' datetime: {since}")
        if until:
            try:
                until_dt = dt.fromisoformat(until.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid 'until' datetime: {until}")

        repo = container.processor_analysis_repo
        stats = await repo.get_stats(pair=pair, since=since_dt, until=until_dt)
        return stats

    @app.get("/api/analysis/{analysis_id}")
    async def get_analysis_detail(request: Request, analysis_id: str) -> dict:
        """Full analysis detail including LLM reasoning and raw output."""
        container: Container = request.app.state.container
        if not hasattr(container, "processor_analysis_repo"):
            raise HTTPException(status_code=503, detail="Processor not initialized")

        row = await container.processor_analysis_repo.get_by_analysis_id(analysis_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found")

        audit_rows = []
        if hasattr(container, "processor_audit_repo"):
            audit_rows = await container.processor_audit_repo.get_by_analysis_id(analysis_id)

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

        display = format_for_dashboard(row.raw_output or {}, row)

        return {
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
            "created_at": row.created_at.isoformat() if row.created_at else None,
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

    @app.post("/api/analysis/rerun")
    async def rerun_analysis(
        request: Request,
        symbol: str,
        trace_id: Optional[str] = None,
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
        if not hasattr(container, "processor"):
            raise HTTPException(status_code=503, detail="Processor not initialized")
        if not hasattr(container, "ta_orchestrator"):
            raise HTTPException(status_code=503, detail="TA orchestrator not initialized")

        symbol = symbol.upper().strip()
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol is required")

        # Step 1: Run TA analysis for the symbol.
        try:
            ta_result = await container.ta_orchestrator.analyze(symbol=symbol)
        except Exception as exc:
            logger.error("rerun_ta_failed", extra={"symbol": symbol, "error": str(exc)})
            raise HTTPException(status_code=500, detail=f"TA analysis failed: {exc}")

        if isinstance(ta_result, dict):
            ta_analysis = ta_result
        elif hasattr(ta_result, "model_dump"):
            ta_analysis = ta_result.model_dump(mode="json")
        else:
            ta_analysis = {"raw": str(ta_result)}

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
            logger.error("rerun_macro_failed", extra={"symbol": symbol, "error": str(exc)})
            raise HTTPException(status_code=500, detail=f"Macro collection failed: {exc}")

        # Derive enriched macro signal flags from collected data.
        # This replicates what the Go gateway's macro_extractor.go and
        # assembler.go do, so the rerun endpoint produces identical
        # RAG queries and processor metadata as the normal pipeline.
        macro_signals = derive_macro_signals(macro_analysis)
        ta_signals = derive_ta_signals(ta_analysis)

        # Build a rich query text matching the Go gateway's BuildQueryText.
        query_parts: list[str] = [symbol]
        if ta_signals["direction"]:
            dir_word = {"long": "bullish", "short": "bearish", "neutral": "neutral"}.get(
                ta_signals["direction"], ta_signals["direction"],
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
                query_parts.append(f"balance sheet {macro_signals['balance_sheet_direction'].lower()}")
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
        if macro_signals["risk_environment"] and macro_signals["risk_environment"] != "NEUTRAL":
            query_parts.append(f"risk environment {macro_signals['risk_environment'].lower()}")
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
                strategy=None,
                framework=ta_signals["framework"] or None,
                setup_family=ta_signals["setup_families"][0] if ta_signals["setup_families"] else None,
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
                has_commodity_currencies_weak=macro_signals["commodity_currencies_weak"],
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
            logger.error("rerun_rag_failed", extra={"symbol": symbol, "error": str(exc)})
            raise HTTPException(
                status_code=500,
                detail=f"RAG retrieval failed: {exc}. The LLM cannot reason without the knowledge base.",
            )

        if not retrieved_knowledge:
            raise HTTPException(
                status_code=500,
                detail="RAG returned empty knowledge base. The LLM cannot reason without rulebook context.",
            )

        # Build enriched metadata matching the Go gateway's assembler.go output.
        available_datasets = [
            name for name in [
                "central_bank", "cot", "economic", "news",
                "calendar", "dxy", "intermarket", "sentiment",
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
        metadata["commodity_currencies_weak"] = macro_signals["commodity_currencies_weak"]
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
            metadata["balance_sheet_direction"] = macro_signals.get("balance_sheet_direction", "")
        metadata["has_core_inflation"] = macro_signals["has_core_inflation"]
        # Propagate RAG metadata if present in the bundle.
        for key in [
            "strategy_used", "coverage_result", "conflict_result",
            "total_chunks_returned", "coverage_gaps", "conflict_details",
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
            result = await container.processor.process(
                processor_input,
                trace_id=trace_id,
            )
        except Exception as exc:
            logger.error("rerun_processor_failed", extra={"symbol": symbol, "error": str(exc)})
            raise HTTPException(status_code=500, detail=f"Processor failed: {exc}")

        if hasattr(result, "model_dump"):
            return {"status": "completed", "symbol": symbol, "result": result.model_dump(mode="json")}
        if isinstance(result, dict):
            return {"status": "completed", "symbol": symbol, "result": result}
        return {"status": "completed", "symbol": symbol, "result": {"raw": str(result)}}

    # -- Processor config endpoints (LLM provider/model switching) -----------

    @app.get("/api/processor/models")
    async def get_available_models(request: Request) -> dict:
        """Available models per provider for the dashboard model selector.

        Returns the model list for each provider plus the currently
        active provider and model. The user selects a model from this
        list; the selection is applied via PUT /api/processor/config
        which persists it as the active model until changed.
        """
        container: Container = request.app.state.container
        if not hasattr(container, "processor_config"):
            raise HTTPException(status_code=503, detail="Processor not initialized")

        cfg = container.processor_config
        return {
            "current_provider": cfg.llm_provider,
            "current_model": cfg.model_name,
            "providers": {
                provider: {
                    "models": models,
                    "default_model": DEFAULT_MODELS.get(provider, ""),
                    "accepts_custom": provider == LLMProvider.SELF_HOSTED,
                }
                for provider, models in AVAILABLE_MODELS.items()
            },
            "self_hosted": {
                "models": [],
                "default_model": DEFAULT_MODELS.get(LLMProvider.SELF_HOSTED, "default"),
                "accepts_custom": True,
                "note": "Enter any model name supported by your endpoint",
                "requires_api_base_url": True,
            },
        }

    @app.get("/api/processor/config")
    async def get_processor_config(request: Request) -> ProcessorConfigResponse:
        """Current LLM provider and model configuration."""
        container: Container = request.app.state.container
        if not hasattr(container, "processor_config"):
            raise HTTPException(status_code=503, detail="Processor not initialized")

        cfg = container.processor_config
        return ProcessorConfigResponse(
            llm_provider=cfg.llm_provider,
            model_name=cfg.model_name,
            temperature=cfg.temperature,
            max_output_tokens=cfg.max_output_tokens,
            supported_providers=[p.value for p in LLMProvider],
        )

    @app.put("/api/processor/config")
    async def update_processor_config(
        request: Request,
        body: ProcessorConfigUpdateRequest,
    ) -> dict:
        """Switch LLM provider or model at runtime from the dashboard.

        Rebuilds the LLM client and processor with the new settings.
        Takes effect on the next analysis cycle (the Go gateway calls
        /internal/processor/process which uses the latest processor).
        """
        container: Container = request.app.state.container
        if not hasattr(container, "processor_config"):
            raise HTTPException(status_code=503, detail="Processor not initialized")

        from pydantic import SecretStr
        from engine.processor.config import ProcessorConfig
        from engine.processor.llm.factory import create_llm_client
        from engine.processor.service import AnalysisProcessor

        old_cfg = container.processor_config
        new_provider = body.llm_provider or old_cfg.llm_provider
        new_model = body.model_name or old_cfg.model_name
        new_temp = body.temperature if body.temperature is not None else old_cfg.temperature
        new_max_tokens = body.max_output_tokens if body.max_output_tokens is not None else old_cfg.max_output_tokens

        valid_providers = {p.value for p in LLMProvider}
        if new_provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider '{new_provider}'. Supported: {sorted(valid_providers)}",
            )

        config_overrides = {
            "llm_provider": new_provider,
            "model_name": new_model,
            "temperature": new_temp,
            "max_output_tokens": new_max_tokens,
            "llm_timeout_seconds": old_cfg.llm_timeout_seconds,
            "total_timeout_seconds": old_cfg.total_timeout_seconds,
            "max_retries": old_cfg.max_retries,
            "retry_backoff_base_seconds": old_cfg.retry_backoff_base_seconds,
            "retry_backoff_max_seconds": old_cfg.retry_backoff_max_seconds,
            "strict_schema_validation": old_cfg.strict_schema_validation,
            "require_citations": old_cfg.require_citations,
            "persist_audit_logs": old_cfg.persist_audit_logs,
            "log_raw_llm_response": old_cfg.log_raw_llm_response,
            "anthropic_api_key": old_cfg.anthropic_api_key,
            "openai_api_key": old_cfg.openai_api_key,
            "gemini_api_key": old_cfg.gemini_api_key,
            "self_hosted_api_key": old_cfg.self_hosted_api_key,
            "api_base_url": body.api_base_url or old_cfg.api_base_url,
        }

        if body.api_key:
            key_field = f"{new_provider}_api_key"
            if key_field in config_overrides:
                config_overrides[key_field] = SecretStr(body.api_key)

        try:
            new_cfg = ProcessorConfig(**config_overrides)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid configuration: {exc}")

        if hasattr(container, "processor_llm_client"):
            await container.processor_llm_client.close()

        new_client = create_llm_client(new_cfg)
        new_processor = AnalysisProcessor(
            config=new_cfg,
            llm_client=new_client,
            analysis_repo=container.processor_analysis_repo,
            audit_repo=container.processor_audit_repo,
        )

        container.processor_config = new_cfg
        container.processor_llm_client = new_client
        container.processor = new_processor

        # The Go gateway calls /internal/processor/process which reads
        # container.processor directly, so the hot-swap takes effect
        # on the next gRPC call without any gateway-side update needed.

        logger.info(
            "processor_config_updated",
            extra={
                "old_provider": old_cfg.llm_provider,
                "new_provider": new_provider,
                "old_model": old_cfg.model_name,
                "new_model": new_model,
                "temperature": new_temp,
            },
        )

        return {
            "status": "updated",
            "llm_provider": new_provider,
            "model_name": new_model,
            "temperature": new_temp,
            "max_output_tokens": new_max_tokens,
        }

    # -- Internal broker bridge endpoints (Go Execution + Management) --------
    # These endpoints proxy broker operations from the Go services through
    # the Python engine's active broker client (MetaApiClient or ZmqClient).
    # The Go services call these at EXECUTION_BROKER_BRIDGE_URL and
    # MANAGEMENT_BROKER_BRIDGE_URL (both http://engine:8000).

    @app.get("/internal/broker/account_info")
    async def broker_account_info(request: Request) -> dict:
        """Return live account balance, equity, margin, free margin."""
        container: Container = request.app.state.container
        try:
            info = await container.mt5_client.get_account_info()
            return {
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "margin_free": info.free_margin,
                "currency": info.currency,
            }
        except Exception as exc:
            logger.error("broker_account_info_failed", extra={"error": str(exc)})
            raise HTTPException(status_code=502, detail=f"Broker unavailable: {exc}")

    @app.get("/internal/broker/positions")
    async def broker_positions(request: Request) -> list:
        """Return all open positions at the broker."""
        container: Container = request.app.state.container
        try:
            positions = await container.mt5_client.get_positions()
            return [
                {
                    "symbol": p.symbol,
                    "type": 0 if p.direction == "BUY" else 1,
                    "price_open": p.entry_price,
                    "price_current": p.current_price,
                    "sl": p.stop_loss,
                    "tp": p.take_profit,
                    "volume": p.volume,
                    "profit": p.profit,
                    "ticket": int(p.ticket) if p.ticket.isdigit() else 0,
                    "comment": p.comment,
                    "time_setup": p.open_time,
                }
                for p in positions
            ]
        except Exception as exc:
            logger.error("broker_positions_failed", extra={"error": str(exc)})
            raise HTTPException(status_code=502, detail=f"Broker unavailable: {exc}")

    @app.get("/internal/broker/pending_orders")
    async def broker_pending_orders(request: Request) -> list:
        """Return all pending limit/stop orders at the broker."""
        container: Container = request.app.state.container
        try:
            orders = await container.mt5_client.get_pending_orders()
            return [
                {
                    "symbol": o.symbol,
                    "type": o.order_type,
                    "price_open": o.price,
                    "sl": o.stop_loss,
                    "tp": o.take_profit,
                    "volume": o.volume,
                    "ticket": int(o.ticket) if o.ticket.isdigit() else 0,
                    "comment": o.comment,
                    "time_setup": o.open_time,
                }
                for o in orders
            ]
        except Exception as exc:
            logger.error("broker_pending_orders_failed", extra={"error": str(exc)})
            raise HTTPException(status_code=502, detail=f"Broker unavailable: {exc}")

    @app.get("/internal/broker/symbol_info")
    async def broker_symbol_info(request: Request, symbol: str = "") -> dict:
        """Return instrument metadata for the Go sizing engine.

        Extends the existing get_symbol_info() with trade_tick_value and
        trade_tick_size fields that the Go bridge.go uses for pip value
        calculation.
        """
        if not symbol:
            raise HTTPException(status_code=400, detail="symbol parameter required")
        container: Container = request.app.state.container
        try:
            info = await container.mt5_client.get_symbol_info(symbol)
            return info
        except Exception as exc:
            logger.error("broker_symbol_info_failed", extra={"symbol": symbol, "error": str(exc)})
            raise HTTPException(status_code=502, detail=f"Symbol info unavailable: {exc}")

    @app.get("/internal/broker/tick_price")
    async def broker_tick_price(request: Request, symbol: str = "") -> dict:
        """Return latest bid/ask for a symbol.

        Called by both Execution (watcher tick polling) and Management
        (per-trade monitoring worker) on every tick cycle.
        """
        if not symbol:
            raise HTTPException(status_code=400, detail="symbol parameter required")
        container: Container = request.app.state.container
        try:
            tick = await container.mt5_client.get_tick_price(symbol)
            return {
                "bid": tick.bid,
                "ask": tick.ask,
                "time": tick.time,
            }
        except Exception as exc:
            logger.error("broker_tick_price_failed", extra={"symbol": symbol, "error": str(exc)})
            raise HTTPException(status_code=502, detail=f"Tick price unavailable: {exc}")

    @app.post("/internal/broker/place_order")
    async def broker_place_order(request: Request) -> dict:
        """Place a limit or market order at the broker.

        Called by Execution Module B's bridge.go placeOrder().
        """
        container: Container = request.app.state.container
        body = await request.json()

        symbol = body.get("symbol", "")
        direction = body.get("direction", "")
        order_type = body.get("order_type", "MARKET")
        price = float(body.get("price", 0))
        stop_loss = float(body.get("stop_loss", 0))
        take_profit = float(body.get("take_profit", 0))
        lot_size = float(body.get("lot_size", 0))
        comment = body.get("comment", "")

        if not symbol or not direction:
            raise HTTPException(status_code=400, detail="symbol and direction required")

        try:
            result = await container.mt5_client.place_order(
                symbol=symbol,
                direction=direction,
                order_type=order_type,
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                lot_size=lot_size,
                comment=comment,
            )
            return {
                "order_id": result.order_id,
                "price": result.price,
                "status": result.status,
                "error": result.error,
            }
        except Exception as exc:
            logger.error(
                "broker_place_order_failed",
                extra={"symbol": symbol, "direction": direction, "error": str(exc)},
            )
            raise HTTPException(status_code=502, detail=f"Order placement failed: {exc}")

    @app.post("/internal/broker/cancel_order")
    async def broker_cancel_order(request: Request) -> dict:
        """Cancel a pending order by broker order ID."""
        container: Container = request.app.state.container
        body = await request.json()
        order_id = str(body.get("order_id", ""))

        if not order_id:
            raise HTTPException(status_code=400, detail="order_id required")

        try:
            success = await container.mt5_client.cancel_order(order_id)
            return {"success": success, "error": ""}
        except Exception as exc:
            logger.error("broker_cancel_order_failed", extra={"order_id": order_id, "error": str(exc)})
            return {"success": False, "error": str(exc)}

    @app.get("/internal/broker/position")
    async def broker_position(request: Request, ticket: str = "") -> dict:
        """Return a single open position by broker ticket.

        Called by Management Module C's stream.go GetPosition().
        """
        if not ticket:
            raise HTTPException(status_code=400, detail="ticket parameter required")
        container: Container = request.app.state.container
        try:
            p = await container.mt5_client.get_position(ticket)
            return {
                "symbol": p.symbol,
                "type": 0 if p.direction == "BUY" else 1,
                "price_open": p.entry_price,
                "price_current": p.current_price,
                "sl": p.stop_loss,
                "tp": p.take_profit,
                "volume": p.volume,
                "profit": p.profit,
                "ticket": int(p.ticket) if p.ticket.isdigit() else 0,
            }
        except Exception as exc:
            logger.error("broker_position_failed", extra={"ticket": ticket, "error": str(exc)})
            raise HTTPException(status_code=502, detail=f"Position unavailable: {exc}")

    @app.post("/internal/broker/modify_position")
    async def broker_modify_position(request: Request) -> dict:
        """Modify SL/TP on an existing open position.

        Called by Management Module C's client.go ModifyPosition().
        """
        container: Container = request.app.state.container
        body = await request.json()

        ticket = str(body.get("ticket", ""))
        stop_loss = float(body.get("stop_loss", 0))
        take_profit = float(body.get("take_profit", 0))

        if not ticket:
            raise HTTPException(status_code=400, detail="ticket required")

        try:
            success = await container.mt5_client.modify_position(
                ticket=ticket,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
            return {"success": success, "error": ""}
        except Exception as exc:
            logger.error(
                "broker_modify_position_failed",
                extra={"ticket": ticket, "error": str(exc)},
            )
            return {"success": False, "error": str(exc)}

    @app.post("/internal/broker/close_partial")
    async def broker_close_partial(request: Request) -> dict:
        """Partially close a position by volume.

        Called by Management Module C's client.go ClosePartial().
        """
        container: Container = request.app.state.container
        body = await request.json()

        ticket = str(body.get("ticket", ""))
        volume = float(body.get("volume", 0))

        if not ticket or volume <= 0:
            raise HTTPException(status_code=400, detail="ticket and positive volume required")

        try:
            result = await container.mt5_client.close_partial(
                ticket=ticket,
                volume=volume,
            )
            return {
                "success": result.get("success", False),
                "close_price": result.get("close_price", 0),
                "error": result.get("error", ""),
            }
        except Exception as exc:
            logger.error(
                "broker_close_partial_failed",
                extra={"ticket": ticket, "volume": volume, "error": str(exc)},
            )
            return {"success": False, "close_price": 0, "error": str(exc)}

    @app.post("/internal/broker/close_position")
    async def broker_close_position(request: Request) -> dict:
        """Fully close a position at market.

        Called by Management Module C's client.go ClosePosition().
        """
        container: Container = request.app.state.container
        body = await request.json()

        ticket = str(body.get("ticket", ""))

        if not ticket:
            raise HTTPException(status_code=400, detail="ticket required")

        try:
            result = await container.mt5_client.close_position(ticket)
            return {
                "success": result.get("success", False),
                "close_price": result.get("close_price", 0),
                "error": result.get("error", ""),
            }
        except Exception as exc:
            logger.error(
                "broker_close_position_failed",
                extra={"ticket": ticket, "error": str(exc)},
            )
            return {"success": False, "close_price": 0, "error": str(exc)}

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app
