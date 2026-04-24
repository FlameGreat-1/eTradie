from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime as dt, timezone
from typing import AsyncIterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field, SecretStr

from engine.config import get_rag_config, get_settings
from engine.dependencies import Container
from engine.macro.scheduler_jobs import register_macro_jobs
from engine.shared.retention import RetentionPruner, register_retention_jobs
from engine.processor.config import ProcessorConfig
from engine.processor.constants import AVAILABLE_MODELS, DEFAULT_MODELS, LLMProvider
from engine.processor.llm.factory import create_llm_client
from engine.processor.mapping.dashboard_formatter import format_for_dashboard
from engine.processor.models.io import ProcessorInput
from engine.processor.service import AnalysisProcessor
from engine.processor.storage.repositories.analysis_repository import AnalysisRepository
from engine.processor.storage.repositories.audit_repository import AuditRepository
from engine.processor.storage.repositories.broker_connection_repository import (
    BrokerConnectionRepository,
    STATUS_CONNECTED,
    STATUS_ERROR,
    VALID_CONNECTION_TYPES,
    decrypt_credential,
)
from engine.processor.storage.repositories.llm_connection_repository import (
    LLMConnectionRepository,
    decrypt_api_key,
)
from engine.shared.auth import (
    AuthenticatedUser,
    get_admin_user,
    get_current_user,
    get_optional_user,
)
from engine.shared.logging import configure_logging, get_logger
from engine.shared.metrics.prometheus import APP_INFO
from engine.shared.models.currency import get_correlation_config
from engine.shared.store import RedisSymbolReader
from engine.shared.tracing.otel import init_tracing
from engine.shared.exceptions import ProcessorInsufficientDataError
from engine.signal_extractors import derive_macro_signals, derive_ta_signals
from engine.ta.broker.mt5.factory import create_mt5_broker_from_connection
from engine.ta.broker.mt5.metaapi.provisioner import MetaApiProvisioner


async def _rate_limit(
    request: "Request",
    key_prefix: str,
    max_requests: int = 10,
    window_seconds: int = 60,
) -> None:
    """Redis-based sliding window rate limiter for dashboard API endpoints.

    Raises HTTP 429 if the caller exceeds max_requests within window_seconds.
    Uses the client IP as the rate limit key.
    """
    container: Container = request.app.state.container
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"ratelimit:{key_prefix}:{client_ip}"

    try:
        current = await container.cache.increment(rate_key)
        if current == 1:
            await container.cache.expire(rate_key, window_seconds)
        if current > max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        # If Redis is down, allow the request (fail open for availability)
        # but log a warning so operators know rate limiting is bypassed.
        logger.warning(
            "rate_limit_redis_unavailable_failing_open",
            extra={
                "key_prefix": key_prefix,
                "client_ip": client_ip,
                "error": str(exc),
            },
        )


logger = get_logger(__name__)


async def _resolve_user_processor(
    container: "Container", user_id: str
) -> "AnalysisProcessor":
    """Resolve the authenticated user's LLM processor.

    Called by every endpoint that runs the LLM processor to ensure
    each user's analysis uses their own API key, model, and settings.

    Uses the Container's per-user processor cache. Every user MUST
    configure their own LLM connection via the dashboard. There is
    no env-var fallback for regular users.
    """
    try:
        return await container.resolve_user_processor(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


async def _resolve_user_broker(container: "Container", user_id: str):
    """Resolve the authenticated user's broker connection.

    Called by every endpoint that needs broker access to ensure
    operations execute against the correct user's MT5 account.

    Every user (including admin) MUST configure their own broker
    connection via the dashboard. There is NO env-var fallback and
    NO platform-level broker.

    Resolution (handled by container.load_user_broker):
      1. Active broker connection from DB for this user
      2. None -> raises HTTP 503

    Works for both MetaAPI and ZeroMQ EA connection types.
    """
    client = await container.load_user_broker(user_id)
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="No broker connection configured. Please set up a broker connection via the dashboard.",
        )
    return client


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

    # Scheduler jobs bind to .refresh() (cache-bypass writer path) so
    # every scheduled interval unconditionally fetches from providers
    # and repopulates Redis. All request-driven callers (analysis
    # rerun, /internal/macro/collect, downstream readers) use
    # .collect() which is the read-through fast path that serves
    # from cache when a fresh value is available.
    register_macro_jobs(
        container.scheduler,
        cb_collector_fn=container.cb_collector.refresh,
        cot_collector_fn=container.cot_collector.refresh,
        economic_collector_fn=container.economic_collector.refresh,
        news_collector_fn=container.news_collector.refresh,
        calendar_collector_fn=container.calendar_collector.refresh,
        dxy_collector_fn=container.dxy_collector.refresh,
        intermarket_collector_fn=container.intermarket_collector.refresh,
        sentiment_collector_fn=container.sentiment_collector.refresh,
        poll_cb=settings.poll_interval_central_bank_rss,
        poll_news=settings.poll_interval_news,
        poll_calendar=settings.poll_interval_calendar,
        poll_cot=settings.poll_interval_cot,
        poll_dxy=settings.poll_interval_dxy,
        poll_intermarket=settings.poll_interval_intermarket,
        poll_sentiment=settings.poll_interval_sentiment,
        poll_economic=settings.poll_interval_economic_data,
    )

    # -- Data Retention Pruning -----------------------------------------------
    # Runs daily at 03:00 UTC to prune expired TA and Macro data.
    # All pruned data self-heals from external sources on next cycle.
    retention_pruner = RetentionPruner(container.db)
    register_retention_jobs(container.scheduler, retention_pruner)

    await container.build_broker()

    await container.build_processor()
    logger.info(
        "processor_built",
        provider=container.processor_config.llm_provider,
        model=container.processor_config.model_name,
    )

    # The Go gateway owns the symbol selection via Redis.
    # RedisSymbolReader reads from the same Redis key the Go gateway writes to.
    symbol_reader = RedisSymbolReader(cache=container.cache)
    app.state.symbol_reader = symbol_reader

    # Warm the macro cache before accepting HTTP traffic. APScheduler's
    # first tick for each interval job fires only after one full
    # interval has elapsed (up to one week for COT), so without this
    # step the first analysis request after a restart would hit a cold
    # Redis and pay the full provider-fetch latency on every namespace.
    # Running through .refresh() invokes the single-flight lock inside
    # BaseCollector, so if an incoming request somehow arrives during
    # warm-up it will coalesce onto the same fetch rather than
    # launching a duplicate.
    macro_warmup_targets = {
        "central_bank": container.cb_collector,
        "cot": container.cot_collector,
        "economic": container.economic_collector,
        "news": container.news_collector,
        "calendar": container.calendar_collector,
        "dxy": container.dxy_collector,
        "intermarket": container.intermarket_collector,
        "sentiment": container.sentiment_collector,
    }
    logger.info(
        "macro_cache_warmup_started",
        extra={"namespaces": list(macro_warmup_targets.keys())},
    )
    warmup_start = asyncio.get_event_loop().time()
    warmup_results = await asyncio.gather(
        *(c.refresh() for c in macro_warmup_targets.values()),
        return_exceptions=True,
    )
    warmup_duration_s = asyncio.get_event_loop().time() - warmup_start
    warmup_summary: dict[str, str] = {}
    for name, result in zip(macro_warmup_targets.keys(), warmup_results):
        if isinstance(result, Exception):
            warmup_summary[name] = f"failed: {type(result).__name__}: {result}"
            logger.warning(
                "macro_cache_warmup_namespace_failed",
                extra={
                    "namespace": name,
                    "error": str(result),
                    "error_type": type(result).__name__,
                },
            )
        else:
            warmup_summary[name] = "ok"
    logger.info(
        "macro_cache_warmup_completed",
        extra={
            "duration_seconds": round(warmup_duration_s, 2),
            "results": warmup_summary,
        },
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
    api_key: Optional[str] = Field(
        default=None, description="API key for the new provider"
    )
    api_base_url: Optional[str] = Field(
        default=None, description="Base URL for self-hosted"
    )


# -- Request schemas for internal gateway endpoints --------------------------


class InternalLTFConfirmRequest(BaseModel):
    symbol: str
    direction: str  # "BULLISH" or "BEARISH"
    ltf_timeframe: str  # e.g. "M5", "M15"
    ob_upper: float
    ob_lower: float
    entry_price: float
    trace_id: Optional[str] = None

    # Invalidation layer fields. When provided, the service runs HTF
    # invalidation checks (OB mitigation, opposing BMS, SL blown)
    # before the LTF confirmation checks.
    stop_loss: Optional[float] = None
    htf_timeframe: Optional[str] = None  # e.g. "H4" - derived from LTF if not set


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


class InternalDebugRunCycleRequest(BaseModel):
    """Payload sent by the Go gateway after a successful analysis cycle.

    Contains the full pipeline data (TA, macro, RAG, processor) so the
    engine can persist it to /output/runcycle/ for offline inspection.
    """
    symbol: str
    ta_data: dict
    macro_data: Optional[dict] = None
    rag_data: Optional[dict] = None
    processor_data: Optional[dict] = None
    execution_request: Optional[dict] = None
    trace_id: Optional[str] = None


class CreateLLMConnectionRequest(BaseModel):
    provider: str
    model_name: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=16384, ge=1024, le=131072)
    label: Optional[str] = None
    activate: bool = True

class UpdateLLMConnectionRequest(BaseModel):
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(default=None, ge=1024, le=131072)
    label: Optional[str] = None

class CreateBrokerConnectionRequest(BaseModel):
    connection_type: str  # 'ea' or 'metaapi'
    name: str
    # MetaAPI: user's MT5 broker credentials
    mt5_login: Optional[str] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None
    # EA: no user-facing fields (auto from env)
    activate: bool = True

class UpdateBrokerConnectionRequest(BaseModel):
    name: Optional[str] = None
    mt5_server: Optional[str] = None
    mt5_login: Optional[str] = None
    mt5_password: Optional[str] = None


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

    @app.post("/internal/ta/confirm_ltf")
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

    @app.post("/internal/ta/analyze")
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

    @app.post("/internal/macro/collect")
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

    @app.post("/internal/rag/retrieve")
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

    @app.post("/internal/processor/process")
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

    @app.post("/internal/debug/runcycle")
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

    # -- Analysis dashboard endpoints ----------------------------------------

    @app.get("/api/analysis/latest")
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

    @app.get("/api/analysis/stats")
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

    # NOTE: The SSE /api/analysis/stream-live route below is registered
    # BEFORE /api/analysis/{analysis_id} on purpose. FastAPI matches
    # routes in declaration order and the {analysis_id} catch-all would
    # otherwise swallow "stream-live" and return 404 from
    # get_analysis_detail.
    from fastapi.responses import StreamingResponse as _StreamingResponse_live
    import json as _json_live
    import asyncio as _asyncio_live

    from engine.processor.streaming import (
        SSE_HEARTBEAT_SECONDS as _SSE_HEARTBEAT_SECONDS_live,
        stream_channel_for_user as _stream_channel_for_user_live,
    )

    @app.get("/api/analysis/stream-live")
    async def stream_live_analysis_early(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """SSE endpoint for the dashboard's live-reasoning panel.

        Registered BEFORE /api/analysis/{analysis_id} so the static
        path wins the route match. Streams per-user frames published
        by the processor through Redis pub/sub.
        """
        container: Container = request.app.state.container
        channel_name = _stream_channel_for_user_live(user.user_id)

        async def event_generator():
            pubsub = container.cache.pubsub()
            await pubsub.subscribe(channel_name)
            logger.info(
                "stream_subscriber_started",
                extra={"user_id": user.user_id, "channel": channel_name},
            )

            last_keepalive = _asyncio_live.get_event_loop().time()

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
                            last_keepalive = _asyncio_live.get_event_loop().time()

                            data_obj = _json_live.loads(data_str)
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
                        now = _asyncio_live.get_event_loop().time()
                        if now - last_keepalive >= _SSE_HEARTBEAT_SECONDS_live:
                            yield ": keepalive\n\n"
                            last_keepalive = now
            except _asyncio_live.CancelledError:
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
                _asyncio_live.create_task(_cleanup_pubsub())

                logger.info(
                    "stream_subscriber_stopped",
                    extra={"user_id": user.user_id, "channel": channel_name},
                )

        return _StreamingResponse_live(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/api/analysis/{analysis_id}")
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
                import json
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

    def _save_debug_output(
        symbol: str,
        ta_data: dict,
        macro_data: dict | None = None,
        rag_data: dict | None = None,
        processor_data: dict | None = None,
        execution_request: dict | None = None,
        subdirectory: str = "rerun",
    ) -> dict:
        """Persist analysis outputs to /output/<subdirectory>/<symbol>_<ts>/ as separate JSON files.

        Args:
            symbol: The trading symbol (e.g. "GBPUSDm").
            ta_data: TA analysis result dict.
            macro_data: Macro analysis result dict.
            rag_data: RAG knowledge bundle dict.
            processor_data: Processor LLM result dict.
            subdirectory: Output subdirectory name ("rerun" or "runcycle").

        Returns a dict of {label: filepath} for every file written.
        """
        ts = dt.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_dir = Path("/output") / subdirectory / f"{symbol}_{ts}"
        out_dir.mkdir(parents=True, exist_ok=True)

        files: dict[str, str] = {}

        def _write(name: str, data: dict | None) -> None:
            if data is None:
                return
            path = out_dir / f"{name}.json"
            path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            files[name] = str(path)

        if ta_data is not None:
            _write("ta_snapshots", ta_data.get("snapshots"))
            _write("ta_smc_candidates", ta_data.get("smc_candidates"))
            _write("ta_snd_candidates", ta_data.get("snd_candidates"))

            ta_meta = {k: v for k, v in ta_data.items() if k not in ("snapshots", "smc_candidates", "snd_candidates")}
            _write("ta_metadata", ta_meta)

        _write("macro_analysis", macro_data)
        _write("rag_knowledge", rag_data)
        _write("processor_result", processor_data)
        _write("execution_request", execution_request)

        logger.info(
            "debug_output_saved",
            extra={
                "symbol": symbol,
                "subdirectory": subdirectory,
                "directory": str(out_dir),
                "files": list(files.keys()),
            },
        )
        return files

    @app.post("/api/analysis/rerun")
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

        # Build enriched metadata matching the Go gateway's assembler.go output.
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

    from fastapi.responses import StreamingResponse
    import json

    from engine.processor.streaming import (
        SSE_HEARTBEAT_SECONDS,
        stream_channel_for_user,
    )

    @app.get("/api/analysis/stream-live")
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
                    # Fast exit on client disconnect so we release the
                    # redis pub/sub connection back to the pool promptly.
                    if await request.is_disconnected():
                        break

                    # get_message with a 1s timeout gives us a tight
                    # disconnect-detection loop and a cheap cadence for
                    # the heartbeat below.
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

                            # Terminal frame closes this subscriber.
                            # Safe now that the channel is per-user:
                            # another user's terminal frame cannot
                            # appear on this connection.
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
                        # No real message in this 1s window. Emit an SSE
                        # comment frame periodically so intermediaries
                        # (nginx/cloudflare/browsers) do not kill the
                        # idle connection while the LLM is reasoning.
                        now = asyncio.get_event_loop().time()
                        if now - last_keepalive >= SSE_HEARTBEAT_SECONDS:
                            yield ": keepalive\n\n"
                            last_keepalive = now
            except asyncio.CancelledError:
                # Client went away mid-stream. Propagate so uvicorn
                # can clean up its task reference; our finally block
                # below still runs.
                raise
            except Exception as exc:
                logger.error(
                    "stream_generator_error",
                    extra={"user_id": user.user_id, "error": str(exc)},
                    exc_info=True,
                )
            finally:
                try:
                    await pubsub.unsubscribe(channel_name)
                except Exception:
                    pass
                try:
                    await pubsub.aclose()
                except Exception:
                    pass
                logger.info(
                    "stream_subscriber_stopped",
                    extra={"user_id": user.user_id, "channel": channel_name},
                )

        # Cache-Control disables client-side caching; X-Accel-Buffering
        # tells nginx not to buffer the response (crucial for SSE);
        # Connection: keep-alive keeps the socket warm across the
        # slow-LLM window.
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # -- Processor config endpoints (LLM provider/model switching) -----------

    # -- LLM Connection Management endpoints ---------------------------------

    @app.get("/api/llm/providers")
    async def get_llm_providers(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """List available LLM providers and their models.

        Used by the dashboard "Connect LLM" modal to populate the
        provider dropdown and model selector.
        """
        return {
            "providers": {
                provider: {
                    "models": models,
                    "default_model": DEFAULT_MODELS.get(provider, ""),
                    "accepts_custom": provider == LLMProvider.SELF_HOSTED,
                    "requires_base_url": provider == LLMProvider.SELF_HOSTED,
                }
                for provider, models in AVAILABLE_MODELS.items()
            },
            "self_hosted": {
                "models": [],
                "default_model": DEFAULT_MODELS.get(LLMProvider.SELF_HOSTED, "default"),
                "accepts_custom": True,
                "requires_base_url": True,
                "note": "Enter any model name supported by your endpoint",
            },
        }

    @app.get("/api/llm/connections")
    async def list_llm_connections(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """List all saved LLM connections."""
        container: Container = request.app.state.container

        async with container.db.read_session() as session:
            repo = LLMConnectionRepository(session)
            rows = await repo.get_all(user_id=user.user_id)

        connections = []
        for row in rows:
            connections.append(
                {
                    "id": str(row.id),
                    "provider": row.provider,
                    "model_name": row.model_name,
                    "base_url": row.base_url,
                    "temperature": row.temperature,
                    "max_output_tokens": row.max_output_tokens,
                    "is_active": row.is_active,
                    "label": row.label,
                    "created_at": (
                        row.created_at.isoformat() if row.created_at else None
                    ),
                    "updated_at": (
                        row.updated_at.isoformat() if row.updated_at else None
                    ),
                }
            )

        return {"connections": connections, "count": len(connections)}

    @app.get("/api/llm/connections/active")
    async def get_active_llm_connection(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Get the currently active LLM connection."""
        container: Container = request.app.state.container

        async with container.db.read_session() as session:
            repo = LLMConnectionRepository(session)
            row = await repo.get_active(user_id=user.user_id)

        if row is None:
            return {
                "connection": None,
                "message": "No active LLM connection. Please set up a connection.",
            }

        return {
            "connection": {
                "id": str(row.id),
                "provider": row.provider,
                "model_name": row.model_name,
                "base_url": row.base_url,
                "temperature": row.temperature,
                "max_output_tokens": row.max_output_tokens,
                "is_active": row.is_active,
                "label": row.label,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        }



    @app.post("/api/llm/connections")
    async def create_llm_connection(
        request: Request,
        body: CreateLLMConnectionRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Create a new LLM connection.

        User selects provider, model, enters API key, and saves.
        If activate=True (default), this becomes the active connection
        and the processor is hot-swapped immediately.
        """
        await _rate_limit(request, "llm_create", max_requests=10, window_seconds=60)
        container: Container = request.app.state.container

        valid_providers = {p.value for p in LLMProvider}
        if body.provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider '{body.provider}'. Supported: {sorted(valid_providers)}",
            )

        if body.provider == LLMProvider.SELF_HOSTED and not body.base_url:
            raise HTTPException(
                status_code=400,
                detail="base_url is required for self_hosted provider",
            )

        if not body.api_key.strip():
            raise HTTPException(status_code=400, detail="api_key must not be empty")

        async with container.db.session() as session:
            repo = LLMConnectionRepository(session)
            row = await repo.create(
                user_id=user.user_id,
                provider=body.provider,
                model_name=body.model_name,
                api_key=body.api_key,
                base_url=body.base_url,
                temperature=body.temperature,
                max_output_tokens=body.max_output_tokens,
                label=body.label or "",
                activate=body.activate,
            )

            connection_id = str(row.id)

        # Invalidate the user's cached processor so the next request
        # rebuilds it from the newly created/activated connection.
        await container.invalidate_user_processor(user.user_id)

        return {
            "id": connection_id,
            "provider": body.provider,
            "model_name": body.model_name,
            "is_active": body.activate,
            "label": body.label or f"{body.provider} / {body.model_name}",
            "message": (
                "Connection created and activated."
                if body.activate
                else "Connection created."
            ),
        }



    @app.put("/api/llm/connections/{connection_id}")
    async def update_llm_connection(
        request: Request,
        connection_id: str,
        body: UpdateLLMConnectionRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Update an existing LLM connection."""
        container: Container = request.app.state.container

        if body.provider is not None:
            valid_providers = {p.value for p in LLMProvider}
            if body.provider not in valid_providers:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported provider '{body.provider}'. Supported: {sorted(valid_providers)}",
                )

        async with container.db.session() as session:
            repo = LLMConnectionRepository(session)
            row = await repo.update_connection(
                connection_id,
                user_id=user.user_id,
                provider=body.provider,
                model_name=body.model_name,
                api_key=body.api_key,
                base_url=body.base_url,
                temperature=body.temperature,
                max_output_tokens=body.max_output_tokens,
                label=body.label,
            )

        if row is None:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Invalidate the user's cached processor so the next request
        # rebuilds it with the updated connection settings.
        await container.invalidate_user_processor(user.user_id)

        return {
            "id": str(row.id),
            "provider": row.provider,
            "model_name": row.model_name,
            "is_active": row.is_active,
            "label": row.label,
            "message": "Connection updated.",
        }

    @app.post("/api/llm/connections/{connection_id}/activate")
    async def activate_llm_connection(
        request: Request,
        connection_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Activate a saved LLM connection.

        Deactivates all other connections and hot-swaps the processor
        to use this connection's provider, model, and API key.
        """
        container: Container = request.app.state.container

        async with container.db.session() as session:
            repo = LLMConnectionRepository(session)
            row = await repo.activate(connection_id, user_id=user.user_id)

        if row is None:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Invalidate the user's cached processor so the next request
        # rebuilds it from the newly activated connection.
        await container.invalidate_user_processor(user.user_id)

        return {
            "id": str(row.id),
            "provider": row.provider,
            "model_name": row.model_name,
            "is_active": True,
            "label": row.label,
            "message": f"Connection activated. Processor now using {row.provider}/{row.model_name}.",
        }

    @app.post("/api/llm/connections/{connection_id}/deactivate")
    async def deactivate_llm_connection(
        request: Request,
        connection_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Deactivate a connection without deleting it."""
        container: Container = request.app.state.container

        async with container.db.session() as session:
            repo = LLMConnectionRepository(session)
            row = await repo.deactivate(connection_id, user_id=user.user_id)

        if row is None:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Invalidate the user's cached processor since their active
        # connection was just deactivated.
        await container.invalidate_user_processor(user.user_id)

        return {
            "id": str(row.id),
            "provider": row.provider,
            "model_name": row.model_name,
            "is_active": False,
            "label": row.label,
            "message": "Connection deactivated. No active LLM connection.",
        }

    @app.delete("/api/llm/connections/{connection_id}")
    async def delete_llm_connection(
        request: Request,
        connection_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Permanently delete a saved LLM connection."""
        container: Container = request.app.state.container

        async with container.db.session() as session:
            repo = LLMConnectionRepository(session)
            deleted = await repo.delete(connection_id, user_id=user.user_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Invalidate the user's cached processor in case the deleted
        # connection was the one powering the cached processor.
        await container.invalidate_user_processor(user.user_id)

        return {"deleted": True, "id": connection_id, "message": "Connection deleted."}

    @app.get("/api/processor/models")
    async def get_available_models(
        request: Request,
        user: AuthenticatedUser = Depends(get_admin_user),
    ) -> dict:
        """Available models per provider for the admin processor config.

        Admin-only. Returns the model list for each provider plus the
        currently active system-level provider and model. Regular users
        use GET /api/llm/providers to see available providers/models
        when configuring their own LLM connections.
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
    async def get_processor_config(
        request: Request,
        user: AuthenticatedUser = Depends(get_admin_user),
    ) -> ProcessorConfigResponse:
        """Current system-level LLM provider and model configuration.

        Admin-only. Returns the global processor config built from
        .env at startup or last updated via PUT /api/processor/config.
        Regular users see their own active LLM connection via
        GET /api/llm/connections/active.
        """
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
        user: AuthenticatedUser = Depends(get_admin_user),
    ) -> dict:
        """Hot-swap the system-level LLM processor at runtime.

        Admin-only. Rebuilds the global container.processor with new
        settings. This is the system/admin processor used for startup
        validation and health checks. Regular users configure their
        own LLM connections via /api/llm/connections/* endpoints.
        """
        container: Container = request.app.state.container
        if not hasattr(container, "processor_config"):
            raise HTTPException(status_code=503, detail="Processor not initialized")

        old_cfg = container.processor_config
        new_provider = body.llm_provider or old_cfg.llm_provider
        new_model = body.model_name or old_cfg.model_name
        new_temp = (
            body.temperature if body.temperature is not None else old_cfg.temperature
        )
        new_max_tokens = (
            body.max_output_tokens
            if body.max_output_tokens is not None
            else old_cfg.max_output_tokens
        )

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
            uow_factory=container.processor_uow_factory,
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

    # -- Broker Connection Management endpoints ------------------------------
    # Dashboard CRUD for user-configured MT5 broker connections.
    # Users select EA (ZeroMQ) or MetaAPI, enter credentials, and
    # activate/deactivate/delete connections. Follows the exact same
    # pattern as the LLM Connection Management endpoints above.





    def _serialize_broker_connection(row) -> dict:
        """Serialize a BrokerConnectionRow to a JSON-safe dict."""
        return {
            "id": str(row.id),
            "connection_type": row.connection_type,
            "name": row.name,
            "ea_host": row.ea_host,
            "ea_port": row.ea_port,
            "metaapi_account_id": row.metaapi_account_id,
            "mt5_server": row.mt5_server,
            "mt5_login": row.mt5_login,
            "is_active": row.is_active,
            "is_primary": row.is_primary,
            "status": row.status,
            "status_message": row.status_message,
            "last_connected_at": (
                row.last_connected_at.isoformat() if row.last_connected_at else None
            ),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @app.post("/api/broker/connections")
    async def create_broker_connection(
        request: Request,
        body: CreateBrokerConnectionRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Create a new broker connection (EA or MetaAPI).

        User selects connection type, enters credentials, and saves.
        If activate=True (default), this becomes the active connection.
        The user's broker is resolved per-request from the database
        when they call trading endpoints (/internal/broker/*).
        """
        await _rate_limit(request, "broker_create", max_requests=10, window_seconds=60)
        container: Container = request.app.state.container

        if body.connection_type not in VALID_CONNECTION_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"connection_type must be one of {sorted(VALID_CONNECTION_TYPES)}",
            )

        if not body.name or not body.name.strip():
            raise HTTPException(status_code=400, detail="name must not be empty")

        try:
            # Prepare fields based on connection type
            ea_host = None
            ea_port = None
            ea_auth_token = None
            metaapi_account_id = None
            
            if body.connection_type == "ea":
                # Pull server-side EA config
                ea_host = os.environ.get("MT5_ZMQ_HOST", "host.docker.internal")
                try:
                    ea_port = int(os.environ.get("MT5_ZMQ_PORT", "5555"))
                except ValueError:
                    ea_port = 5555
                ea_auth_token = os.environ.get("MT5_ZMQ_AUTH_TOKEN", "")

            elif body.connection_type == "metaapi":
                # Provision cloud MT5 account dynamically
                if not body.mt5_login or not body.mt5_password or not body.mt5_server:
                    raise HTTPException(
                        status_code=400,
                        detail="mt5_login, mt5_password, and mt5_server are required for MetaAPI connections",
                    )
                
                platform_token = os.environ.get("MT5_METAAPI_TOKEN", "")
                if not platform_token:
                    raise HTTPException(
                        status_code=500,
                        detail="MT5_METAAPI_TOKEN environment variable is not configured on the server."
                    )
                
                provisioner = MetaApiProvisioner(
                    http_client=container.http_client,
                    platform_token=platform_token,
                )
                
                try:
                    metaapi_result = await provisioner.provision_account(
                        login=body.mt5_login,
                        password=body.mt5_password,
                        server=body.mt5_server,
                        name=body.name,
                    )
                    metaapi_account_id = metaapi_result["account_id"]
                except Exception as exc:
                    logger.error(
                        "metaapi_provisioning_error_in_api",
                        extra={"error": str(exc)},
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"MetaAPI provisioning failed: {exc}"
                    )

            async with container.db.session() as session:
                repo = BrokerConnectionRepository(session)
                row = await repo.create(
                    user_id=user.user_id,
                    connection_type=body.connection_type,
                    name=body.name.strip(),
                    ea_host=ea_host,
                    ea_port=ea_port,
                    ea_auth_token=ea_auth_token,
                    metaapi_account_id=metaapi_account_id,
                    mt5_server=body.mt5_server,
                    mt5_login=body.mt5_login,
                    mt5_password=body.mt5_password,
                    activate=body.activate,
                )
                result = _serialize_broker_connection(row)
                connection_id = str(row.id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        result["message"] = (
            "Connection created and activated."
            if body.activate
            else "Connection created."
        )
        return result

    @app.get("/api/broker/connections")
    async def list_broker_connections(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """List all saved broker connections."""
        container: Container = request.app.state.container

        async with container.db.read_session() as session:
            repo = BrokerConnectionRepository(session)
            rows = await repo.get_all(user_id=user.user_id)

        connections = [_serialize_broker_connection(row) for row in rows]
        return {"connections": connections, "count": len(connections)}

    @app.get("/api/broker/connections/active")
    async def get_active_broker_connection(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Get the currently active broker connection."""
        container: Container = request.app.state.container

        async with container.db.read_session() as session:
            repo = BrokerConnectionRepository(session)
            row = await repo.get_active(user_id=user.user_id)

        if row is None:
            return {
                "connection": None,
                "broker_configured": False,
                "message": "No active broker connection. Please set up a connection via the dashboard.",
            }

        return {
            "connection": _serialize_broker_connection(row),
            "broker_configured": True,
        }

    @app.get("/api/broker/connections/{connection_id}")
    async def get_broker_connection(
        request: Request,
        connection_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Get a specific broker connection by ID."""
        container: Container = request.app.state.container

        async with container.db.read_session() as session:
            repo = BrokerConnectionRepository(session)
            row = await repo.get_by_id(connection_id, user_id=user.user_id)

        if row is None:
            raise HTTPException(status_code=404, detail="Connection not found")

        return {"connection": _serialize_broker_connection(row)}

    @app.put("/api/broker/connections/{connection_id}")
    async def update_broker_connection(
        request: Request,
        connection_id: str,
        body: UpdateBrokerConnectionRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Update an existing broker connection.

        Updates are saved to the database. The user's broker is resolved
        per-request from the DB, so the updated values take effect on
        the next trading operation automatically.
        """
        container: Container = request.app.state.container

        try:
            async with container.db.session() as session:
                repo = BrokerConnectionRepository(session)
                row = await repo.update_connection(
                    connection_id,
                    user_id=user.user_id,
                    name=body.name,
                    mt5_server=body.mt5_server,
                    mt5_login=body.mt5_login,
                    mt5_password=body.mt5_password,
                )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        if row is None:
            raise HTTPException(status_code=404, detail="Connection not found")

        result = _serialize_broker_connection(row)
        result["message"] = "Connection updated."
        return result

    @app.post("/api/broker/connections/{connection_id}/activate")
    async def activate_broker_connection(
        request: Request,
        connection_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Activate a broker connection.

        Deactivates all other connections for this user and marks
        this one as active. The user's broker is resolved per-request
        from the database when they call trading endpoints.
        """
        container: Container = request.app.state.container

        async with container.db.session() as session:
            repo = BrokerConnectionRepository(session)
            row = await repo.activate(connection_id, user_id=user.user_id)

        if row is None:
            raise HTTPException(status_code=404, detail="Connection not found")

        result = _serialize_broker_connection(row)
        result["message"] = f"Connection activated. Broker now using {row.name}."
        return result

    @app.post("/api/broker/connections/{connection_id}/deactivate")
    async def deactivate_broker_connection(
        request: Request,
        connection_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Deactivate a broker connection without deleting it."""
        container: Container = request.app.state.container

        async with container.db.session() as session:
            repo = BrokerConnectionRepository(session)
            row = await repo.deactivate(connection_id, user_id=user.user_id)

        if row is None:
            raise HTTPException(status_code=404, detail="Connection not found")

        result = _serialize_broker_connection(row)
        result["message"] = "Connection deactivated."
        return result

    @app.post("/api/broker/connections/{connection_id}/set-primary")
    async def set_primary_broker_connection(
        request: Request,
        connection_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Set a connection as primary (also activates it).

        The user's broker is resolved per-request from the database
        when they call trading endpoints.
        """
        container: Container = request.app.state.container

        async with container.db.session() as session:
            repo = BrokerConnectionRepository(session)
            row = await repo.set_primary(connection_id, user_id=user.user_id)

        if row is None:
            raise HTTPException(status_code=404, detail="Connection not found")

        result = _serialize_broker_connection(row)
        result["message"] = f"Connection set as primary. Broker now using {row.name}."
        return result

    @app.post("/api/broker/connections/{connection_id}/test")
    async def test_broker_connection(
        request: Request,
        connection_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Test a broker connection's health.
        Rate limited to prevent flooding the broker with health checks.

        Creates a temporary broker client from the connection's credentials,
        runs a health check, and updates the connection's status in the DB.
        Does NOT activate the connection or change the active broker.
        """
        await _rate_limit(request, "broker_test", max_requests=5, window_seconds=60)
        container: Container = request.app.state.container

        async with container.db.read_session() as session:
            repo = BrokerConnectionRepository(session)
            row = await repo.get_by_id(connection_id, user_id=user.user_id)

        if row is None:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Decrypt credentials and create a temporary broker client.
        ea_auth_token = ""
        platform_token = ""
        if row.connection_type == "ea" and row.ea_auth_token_encrypted:
            ea_auth_token = decrypt_credential(row.ea_auth_token_encrypted)
        if row.connection_type == "metaapi":
            platform_token = os.environ.get("MT5_METAAPI_TOKEN", "")

        try:
            temp_client = create_mt5_broker_from_connection(
                row=row,
                http_client=container.http_client,
                ea_auth_token=ea_auth_token,
                platform_token=platform_token,
            )
        except Exception as exc:
            # Update status in DB.
            async with container.db.session() as session:
                repo = BrokerConnectionRepository(session)
                await repo.update_status(
                    connection_id,
                    user_id=user.user_id,
                    status=STATUS_ERROR,
                    status_message=f"Failed to create client: {exc}",
                )
            return {
                "connection_id": connection_id,
                "healthy": False,
                "status": STATUS_ERROR,
                "message": f"Failed to create client: {exc}",
            }

        # Run health check.
        try:
            healthy = await temp_client.health_check()
        except Exception as exc:
            healthy = False
            logger.error(
                "broker_test_health_check_failed",
                extra={"connection_id": connection_id, "error": str(exc)},
            )
        finally:
            try:
                await temp_client.shutdown()
            except Exception:
                pass

        # Update status in DB.
        new_status = STATUS_CONNECTED if healthy else STATUS_ERROR
        status_msg = "Connection successful" if healthy else "Health check failed"

        async with container.db.session() as session:
            repo = BrokerConnectionRepository(session)
            await repo.update_status(
                connection_id,
                user_id=user.user_id,
                status=new_status,
                status_message=status_msg,
                connected=healthy,
            )

        return {
            "connection_id": connection_id,
            "healthy": healthy,
            "status": new_status,
            "message": status_msg,
        }

    @app.delete("/api/broker/connections/{connection_id}")
    async def delete_broker_connection(
        request: Request,
        connection_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Permanently delete a saved broker connection."""
        container: Container = request.app.state.container

        async with container.db.read_session() as session:
            repo = BrokerConnectionRepository(session)
            row = await repo.get_by_id(connection_id, user_id=user.user_id)
            
        if not row:
            raise HTTPException(status_code=404, detail="Connection not found")
            
        is_metaapi = row.connection_type == "metaapi"
        metaapi_account_id = row.metaapi_account_id

        async with container.db.session() as session:
            repo = BrokerConnectionRepository(session)
            deleted = await repo.delete(connection_id, user_id=user.user_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Connection not found")

        # Clean up cloud resources asynchronously after DB deletion
        if is_metaapi and metaapi_account_id:
            platform_token = os.environ.get("MT5_METAAPI_TOKEN", "")
            if platform_token:
                try:
                    provisioner = MetaApiProvisioner(
                        http_client=container.http_client,
                        platform_token=platform_token,
                    )
                    # Background task to avoid blocking the user API response
                    asyncio.create_task(provisioner.cleanup_account(metaapi_account_id))
                except Exception as exc:
                    logger.error("failed_to_start_metaapi_cleanup", extra={"error": str(exc)})

        return {"deleted": True, "id": connection_id, "message": "Connection deleted."}

    # -- Internal broker bridge endpoints (Go Execution + Management) --------
    # These endpoints proxy broker operations from the Go services through
    # the Python engine's active broker client (MetaApiClient or ZmqClient).
    # The Go services call these at EXECUTION_BROKER_BRIDGE_URL and
    # MANAGEMENT_BROKER_BRIDGE_URL (both http://engine:8000).

    @app.get("/internal/broker/account_info")
    async def broker_account_info(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Return live account balance, equity, margin, free margin."""
        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)
        try:
            info = await broker_client.get_account_info()
            return {
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "margin_free": info.free_margin,
                "currency": info.currency,
            }
        except Exception as exc:
            logger.error("broker_account_info_failed", extra={"error": str(exc), "user_id": user.user_id})
            raise HTTPException(status_code=502, detail=f"Broker unavailable: {exc}")

    @app.get("/internal/broker/positions")
    async def broker_positions(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> list:
        """Return all open positions at the broker."""
        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)
        try:
            positions = await broker_client.get_positions()
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
            logger.error("broker_positions_failed", extra={"error": str(exc), "user_id": user.user_id})
            raise HTTPException(status_code=502, detail=f"Broker unavailable: {exc}")

    @app.get("/internal/broker/pending_orders")
    async def broker_pending_orders(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> list:
        """Return all pending limit/stop orders at the broker."""
        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)
        try:
            orders = await broker_client.get_pending_orders()
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
            logger.error("broker_pending_orders_failed", extra={"error": str(exc), "user_id": user.user_id})
            raise HTTPException(status_code=502, detail=f"Broker unavailable: {exc}")

    @app.get("/internal/broker/symbol_info")
    async def broker_symbol_info(
        request: Request,
        symbol: str = "",
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Return instrument metadata for the Go sizing engine.

        Extends the existing get_symbol_info() with trade_tick_value and
        trade_tick_size fields that the Go bridge.go uses for pip value
        calculation.
        """
        if not symbol:
            raise HTTPException(status_code=400, detail="symbol parameter required")
        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)
        try:
            info = await broker_client.get_symbol_info(symbol)
            return info
        except Exception as exc:
            logger.error(
                "broker_symbol_info_failed", extra={"symbol": symbol, "error": str(exc), "user_id": user.user_id}
            )
            raise HTTPException(
                status_code=502, detail=f"Symbol info unavailable: {exc}"
            )

    @app.get("/internal/broker/tick_price")
    async def broker_tick_price(
        request: Request,
        symbol: str = "",
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Return latest bid/ask for a symbol.

        Called by both Execution (watcher tick polling) and Management
        (per-trade monitoring worker) on every tick cycle.
        """
        if not symbol:
            raise HTTPException(status_code=400, detail="symbol parameter required")
        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)
        try:
            tick = await broker_client.get_tick_price(symbol)
            return {
                "bid": tick.bid,
                "ask": tick.ask,
                "time": tick.time,
            }
        except Exception as exc:
            logger.error(
                "broker_tick_price_failed", extra={"symbol": symbol, "error": str(exc), "user_id": user.user_id}
            )
            raise HTTPException(
                status_code=502, detail=f"Tick price unavailable: {exc}"
            )

    @app.post("/internal/broker/place_order")
    async def broker_place_order(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Place a limit or market order at the broker.

        Called by Execution Module B's bridge.go placeOrder().
        """
        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)
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
            result = await broker_client.place_order(
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
                extra={"symbol": symbol, "direction": direction, "error": str(exc), "user_id": user.user_id},
            )
            raise HTTPException(
                status_code=502, detail=f"Order placement failed: {exc}"
            )

    @app.post("/internal/broker/cancel_order")
    async def broker_cancel_order(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Cancel a pending order by broker order ID."""
        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)
        body = await request.json()
        order_id = str(body.get("order_id", ""))

        if not order_id:
            raise HTTPException(status_code=400, detail="order_id required")

        try:
            success = await broker_client.cancel_order(order_id)
            return {"success": success, "error": ""}
        except Exception as exc:
            logger.error(
                "broker_cancel_order_failed",
                extra={"order_id": order_id, "error": str(exc), "user_id": user.user_id},
            )
            return {"success": False, "error": str(exc)}

    @app.get("/internal/broker/position")
    async def broker_position(
        request: Request,
        ticket: str = "",
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Return a single open position by broker ticket.

        Called by Management Module C's stream.go GetPosition().
        """
        if not ticket:
            raise HTTPException(status_code=400, detail="ticket parameter required")
        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)
        try:
            p = await broker_client.get_position(ticket)
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
            logger.error(
                "broker_position_failed", extra={"ticket": ticket, "error": str(exc), "user_id": user.user_id}
            )
            raise HTTPException(status_code=502, detail=f"Position unavailable: {exc}")

    @app.post("/internal/broker/modify_position")
    async def broker_modify_position(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Modify SL/TP on an existing open position.

        Called by Management Module C's client.go ModifyPosition().
        """
        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)
        body = await request.json()

        ticket = str(body.get("ticket", ""))
        stop_loss = float(body.get("stop_loss", 0))
        take_profit = float(body.get("take_profit", 0))

        if not ticket:
            raise HTTPException(status_code=400, detail="ticket required")

        try:
            success = await broker_client.modify_position(
                ticket=ticket,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
            return {"success": success, "error": ""}
        except Exception as exc:
            logger.error(
                "broker_modify_position_failed",
                extra={"ticket": ticket, "error": str(exc), "user_id": user.user_id},
            )
            return {"success": False, "error": str(exc)}

    @app.post("/internal/broker/close_partial")
    async def broker_close_partial(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Partially close a position by volume.

        Called by Management Module C's client.go ClosePartial().
        """
        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)
        body = await request.json()

        ticket = str(body.get("ticket", ""))
        volume = float(body.get("volume", 0))

        if not ticket or volume <= 0:
            raise HTTPException(
                status_code=400, detail="ticket and positive volume required"
            )

        try:
            result = await broker_client.close_partial(
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
                extra={"ticket": ticket, "volume": volume, "error": str(exc), "user_id": user.user_id},
            )
            return {"success": False, "close_price": 0, "error": str(exc)}

    @app.post("/internal/broker/close_position")
    async def broker_close_position(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Fully close a position at market.

        Called by Management Module C's client.go ClosePosition().
        """
        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)
        body = await request.json()

        ticket = str(body.get("ticket", ""))

        if not ticket:
            raise HTTPException(status_code=400, detail="ticket required")

        try:
            result = await broker_client.close_position(ticket)
            return {
                "success": result.get("success", False),
                "close_price": result.get("close_price", 0),
                "error": result.get("error", ""),
            }
        except Exception as exc:
            logger.error(
                "broker_close_position_failed",
                extra={"ticket": ticket, "error": str(exc), "user_id": user.user_id},
            )
            return {"success": False, "close_price": 0, "error": str(exc)}

    # -- Chart data endpoints (Dashboard TradingView chart) ------------------
    # These public-facing endpoints power the dashboard's Lightweight Charts.
    # /api/broker/candles provides historical OHLCV data for the initial
    # chart render, and /api/broker/stream-ticks provides a true WebSocket
    # stream of live tick prices for real-time chart animation.

    # ── Broker Symbol Directory ────────────────────────────────────────
    # Fetches the entire list of available instruments from the connected
    # broker (Market Watch for ZMQ, or the MetaApi /symbols endpoint).
    # Cached in-memory for 5 minutes to avoid excessive ZMQ round-trips.

    _broker_symbols_cache: dict = {"data": None, "expires": 0.0}

    @app.get("/api/broker/symbols")
    async def broker_symbols(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Return all available broker instruments with name, description, and path."""
        import time as _time
        container = request.app.state.container

        # Return cached data if still fresh (5 minute TTL).
        now = _time.time()
        if _broker_symbols_cache["data"] is not None and now < _broker_symbols_cache["expires"]:
            return _broker_symbols_cache["data"]

        broker_client = await _resolve_user_broker(container, user.user_id)
        try:
            symbols = await broker_client.get_all_symbols()
            result = {"symbols": symbols, "count": len(symbols)}
            _broker_symbols_cache["data"] = result
            _broker_symbols_cache["expires"] = now + 300.0  # 5 min TTL
            return result
        except Exception as exc:
            logger.error(
                "broker_symbols_failed",
                extra={"error": str(exc), "user_id": user.user_id},
            )
            raise HTTPException(status_code=502, detail=f"Failed to fetch broker symbols: {exc}")

    @app.get("/api/broker/candles")
    async def chart_candles(
        request: Request,
        symbol: str = Query(..., description="Broker symbol, e.g. USDJPYm"),
        timeframe: str = Query("H1", description="Timeframe: M1,M5,M15,M30,H1,H4,D1,W1"),
        count: int = Query(300, ge=10, le=5000, description="Number of candles"),
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> dict:
        """Return historical OHLCV candles for the dashboard chart.

        Uses the user's cached broker connection (ZMQ → MT5) to fetch
        candles in the exact format TradingView Lightweight Charts expects.
        """
        from engine.ta.constants import Timeframe as TF

        tf_map = {
            "M1": TF.M1, "M5": TF.M5, "M15": TF.M15, "M30": TF.M30,
            "H1": TF.H1, "H3": TF.H3, "H4": TF.H4,
            "H6": TF.H6, "H8": TF.H8, "H12": TF.H12,
            "D1": TF.D1, "W1": TF.W1, "MN1": TF.MN1,
        }
        tf = tf_map.get(timeframe.upper())
        if tf is None:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")

        container: Container = request.app.state.container
        broker_client = await _resolve_user_broker(container, user.user_id)

        try:
            seq = await broker_client.fetch_candles(
                symbol=symbol,
                timeframe=tf,
                count=count,
            )
            # Return in Lightweight Charts format: { time, open, high, low, close, volume }
            candles_out = []
            for c in seq.candles:
                candles_out.append({
                    "time": int(c.timestamp.timestamp()),
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                })
            return {
                "symbol": symbol,
                "timeframe": timeframe.upper(),
                "candles": candles_out,
            }
        except Exception as exc:
            logger.error(
                "chart_candles_failed",
                extra={"symbol": symbol, "timeframe": timeframe, "error": str(exc), "user_id": user.user_id},
            )
            raise HTTPException(status_code=502, detail=f"Failed to fetch candles: {exc}")

    @app.websocket("/api/broker/stream-ticks")
    async def stream_ticks(websocket: WebSocket):
        """True WebSocket stream of live tick prices for the dashboard chart.

        Protocol:
          1. Client connects and sends an init message:
             { "symbol": "USDJPYm", "token": "<jwt>" }
          2. Server authenticates, then pushes tick frames every ~500ms:
             { "bid": 149.123, "ask": 149.125, "time": 1713765600 }
          3. Client can send a symbol-switch message at any time:
             { "symbol": "EURUSDm" }
          4. Either side can close the connection.
        """
        await websocket.accept()

        # Step 1: Wait for init message with token and symbol.
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            init_msg = json.loads(raw)
        except WebSocketDisconnect:
            return
        except Exception:
            try:
                await websocket.close(code=4001, reason="Expected init message with token and symbol")
            except Exception:
                pass
            return

        token = init_msg.get("token", "")
        symbol = init_msg.get("symbol", "")

        if not token or not symbol:
            try:
                await websocket.close(code=4002, reason="token and symbol required")
            except Exception:
                pass
            return

        # Step 2: Authenticate the JWT.
        from engine.shared.auth import _verify_token
        try:
            user = _verify_token(token)
            user_id = user.user_id
        except Exception:
            try:
                await websocket.close(code=4003, reason="Invalid or expired token")
            except Exception:
                pass
            return

        container: Container = websocket.app.state.container
        broker_client = await container.load_user_broker(user_id)
        if broker_client is None:
            try:
                await websocket.close(code=4004, reason="No broker connection configured")
            except Exception:
                pass
            return

        logger.info(
            "tick_stream_connected",
            extra={"user_id": user_id, "symbol": symbol},
        )

        # Step 3: Stream ticks in a loop.
        try:
            while True:
                # Check for incoming messages (symbol switch or close).
                try:
                    raw = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                    msg = json.loads(raw)
                    new_symbol = msg.get("symbol", "")
                    if new_symbol:
                        symbol = new_symbol
                        logger.debug(
                            "tick_stream_symbol_switch",
                            extra={"user_id": user_id, "new_symbol": symbol},
                        )
                except asyncio.TimeoutError:
                    pass  # No incoming message — continue streaming.

                # Fetch the latest tick from the broker.
                try:
                    tick = await broker_client.get_tick_price(symbol)
                    await websocket.send_json({
                        "bid": tick.bid,
                        "ask": tick.ask,
                        "time": tick.time,
                        "symbol": symbol,
                    })
                except Exception as exc:
                    # Send error frame but don't disconnect — transient broker glitch.
                    await websocket.send_json({
                        "error": str(exc),
                        "symbol": symbol,
                    })
                    await asyncio.sleep(2.0)  # Back off on error.

        except WebSocketDisconnect:
            logger.info(
                "tick_stream_disconnected",
                extra={"user_id": user_id, "symbol": symbol},
            )
        except Exception as exc:
            logger.error(
                "tick_stream_error",
                extra={"user_id": user_id, "symbol": symbol, "error": str(exc)},
            )
            try:
                await websocket.close(code=1011, reason="Internal error")
            except Exception:
                pass

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # -- CORS middleware (defense-in-depth) ----------------------------------
    # The Go gateway handles CORS for dashboard requests, but the engine
    # should also restrict cross-origin access as a second layer of defense.
    # Internal /internal/* endpoints are called server-to-server (no Origin
    # header) and are unaffected by CORS.
    allowed_origins_str = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
    )
    allowed_origins = [
        origin.strip()
        for origin in allowed_origins_str.split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Trace-ID"],
        max_age=86400,
    )

    return app
