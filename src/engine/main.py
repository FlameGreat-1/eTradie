from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from engine.config import get_rag_config, get_settings
from engine.dependencies import Container
from engine.macro.scheduler_jobs import register_macro_jobs
from engine.shared.retention import RetentionPruner, register_retention_jobs
from engine.shared.logging import configure_logging, get_logger
from engine.shared.metrics.prometheus import APP_INFO
from engine.shared.models.currency import get_correlation_config
from engine.shared.store import RedisSymbolReader
from engine.shared.tracing.otel import init_tracing

# Import modular routers
from engine.routers import (
    analysis,
    broker_bridge,
    broker_connections,
    chart,
    health,
    internal,
    llm_connections,
    performance_review,
    processor_config,
    trading_plan,
)

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

    # Performance Review cron jobs (weekly Mon 06:00 UTC, monthly 1st
    # 06:00 UTC). Registered before the macro jobs so the scheduler
    # has both trigger sets armed before .start() is called below.
    # The app reference is captured so the cron can resolve the
    # container at fire time via app.state.container and dispatch
    # review-generation jobs IN-PROCESS (no HTTP-to-self).
    from engine.processor.performance_review.scheduler import (
        register_performance_review_jobs,
    )
    register_performance_review_jobs(app, container.scheduler)

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
        calendar_collector_fn=container.calendar_collector.refresh,
        dxy_collector_fn=container.dxy_collector.refresh,
        intermarket_collector_fn=container.intermarket_collector.refresh,
        sentiment_collector_fn=container.sentiment_collector.refresh,
        poll_cb=settings.poll_interval_central_bank_rss,
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

    # Warm the macro cache asynchronously, NOT inline before yield.
    async def _macro_cache_warmup() -> None:
        macro_warmup_targets = {
            "central_bank": container.cb_collector,
            "cot": container.cot_collector,
            "economic": container.economic_collector,
            "calendar": container.calendar_collector,
            "dxy": container.dxy_collector,
            "intermarket": container.intermarket_collector,
            "sentiment": container.sentiment_collector,
        }
        logger.info(
            "macro_cache_warmup_started",
            extra={
                "namespaces": list(macro_warmup_targets.keys()),
                "mode": "background",
            },
        )
        warmup_start = asyncio.get_event_loop().time()
        warmup_results = await asyncio.gather(
            *(c.collect() for c in macro_warmup_targets.values()),
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

    await container.background_tasks.schedule_once(
        "lifespan:macro_warmup",
        _macro_cache_warmup,
        cooldown_s=3600,
        timeout_s=300,
    )

    container.scheduler.start()
    logger.info("application_started", env=settings.app_env.value)

    yield

    await container.shutdown()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="eTradie Engine",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # Mount routers
    app.include_router(health.router)
    app.include_router(internal.router)
    app.include_router(analysis.router)
    app.include_router(llm_connections.router)
    app.include_router(processor_config.router)
    app.include_router(broker_connections.router)
    app.include_router(broker_bridge.router)
    app.include_router(chart.router)
    app.include_router(trading_plan.router)
    app.include_router(performance_review.router)

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # -- CSRF middleware ---------------------------------------------------
    # Must be added BEFORE the CORS middleware so the CSRF check runs
    # on the already-authenticated request (get_current_user populates
    # request.state.user via the route dependency before the middleware
    # chain runs in Starlette's order). Internal routes (/internal/*)
    # are exempt because they use X-Internal-Auth instead.
    from engine.shared.csrf import CSRFMiddleware
    app.add_middleware(CSRFMiddleware)

    # -- CORS middleware ---------------------------------------------------
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
        # X-CSRF-Token is added so mutating engine calls from the SPA
        # (e.g. POST /api/analysis/rerun) pass the CORS preflight when
        # the axios interceptor attaches the double-submit header.
        # X-Requested-With is allowed for compatibility with libraries
        # that add it on XHR. Authorization remains in the list for
        # CLI / server-to-server callers that still send Bearer tokens.
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-CSRF-Token",
            "X-Trace-ID",
            "X-Requested-With",
        ],
        max_age=86400,
    )

    return app
