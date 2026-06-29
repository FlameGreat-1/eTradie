from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from engine.config import get_rag_config, get_settings
from engine.dependencies import Container
from engine.macro.scheduler_jobs import register_macro_jobs

# Import modular routers
from engine.routers import (
    analysis,
    broker_bridge,
    broker_connections,
    broker_metaapi,
    chart,
    health,
    internal,
    llm_connections,
    performance_review,
    processor_config,
    trading_plan,
)
from engine.shared.logging import configure_logging, get_logger
from engine.shared.metrics.prometheus import APP_INFO
from engine.shared.models.currency import get_correlation_config
from engine.shared.retention import RetentionPruner, register_retention_jobs
from engine.shared.store import RedisSymbolReader
from engine.shared.tracing.otel import init_tracing

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(log_level=settings.app_log_level, json_output=settings.json_logs)

    # Distributed tracing is opt-in: an empty OTLP endpoint means tracing
    # is explicitly disabled, mirroring the Go services'
    # observability.InitTracing (which no-ops and logs
    # tracing_disabled_no_otlp_endpoint_configured on an empty endpoint).
    # init_tracing() validates the endpoint and RAISES on an empty value,
    # so it must only be called when an endpoint is actually configured;
    # calling it unconditionally would crash the engine on boot wherever
    # the endpoint is unset (base Helm values without the otelEndpoint
    # overlay, docker-compose dev). Audit ref: SC-H7 / tracing opt-in.
    if not settings.is_testing:
        if settings.otel_exporter_otlp_endpoint:
            init_tracing(
                service_name=settings.otel_service_name,
                otlp_endpoint=settings.otel_exporter_otlp_endpoint,
                # Plaintext gRPC: the in-cluster OTel Collector's OTLP
                # receiver binds 0.0.0.0:4317 with no TLS, and the Go
                # services dial it with insecure credentials too.
                # Transport security on this hop is Linkerd mTLS, not
                # the exporter. Without this the SDK attempts a TLS
                # handshake against a plaintext receiver and every span
                # export fails. Matches docker-compose jaeger:4317.
                insecure=True,
            )
        else:
            logger.info("tracing_disabled_no_otlp_endpoint_configured")

    container = Container()
    app.state.container = container

    # Section 5 (CHECKLIST): launch the broker client pool sweeper so
    # idle clients are evicted in the background. stop() runs from
    # container.shutdown() at the bottom of this lifespan.
    await container.broker_client_pool.start()

    APP_INFO.info({"version": "1.0.0", "environment": settings.app_env.value})

    # Warm the DB + cache pools BEFORE any application-level workload
    # tries to use them. health_check() has retry-with-backoff (3
    # attempts, exponential 0.1->0.2->0.4s, 5s timeout each ~= 15s
    # budget); it deterministically warms the cold pool with bounded
    # latency. Running this BEFORE start_active_connections_refresh()
    # eliminates the lifespan-internal startup race where the gauge
    # refresher's first SELECT raced an un-warmed asyncpg connection
    # and crashed the engine (RAGBootstrapError -> CrashLoopBackOff).
    # Industry-standard pattern: confirm dependency health before
    # launching application background tasks.
    db_ok = await container.db.health_check()
    cache_ok = await container.cache.health_check()
    logger.info("startup_health", db=db_ok, cache=cache_ok)

    # Section 5 (CHECKLIST): refresh the etradie_active_user_connections
    # gauge so the engine HPA can scale on user count when the operator
    # has wired prometheus-adapter (see values.yaml autoscaling.customMetrics).
    # Now safe to run: the pool is warm.
    await container.start_active_connections_refresh(interval_secs=30.0)

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
    #
    # The import below is DELIBERATELY in-lifespan rather than at the
    # top of this module. Top-of-file would (a) create a module-load-
    # time edge from main.py into the processor package's scheduler,
    # which would force every reverse path (alembic env.py, pytest
    # collection, ad-hoc scripts that `import engine.main`) to also
    # import the LLM SDK adapters and prompts pulled in transitively
    # by performance_review.scheduler, and (b) make a future
    # circular-import accident much easier when processor/* starts
    # depending on anything that touches engine.routers. Lifting this
    # to the top is the wrong instinct — leave it where it is.
    # Audit ref: SC-H11.
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
        poll_cb=settings.poll_interval_calendar,
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

    # Section 8 (CHECKLIST): hosted MT-node failure recovery.
    #
    # The eager startup sweep MUST run before yield so that every
    # broker_connections row with connection_type='hosted' is
    # guaranteed to have a healthy K8s StatefulSet before FastAPI
    # starts accepting traffic. If a request lands during the gap
    # between the lifespan's first await and the sweep completion,
    # it might observe a stale 'connection exists in DB but no Pod'
    # state and fail with a confusing 503.
    #
    # Construction failure (missing MT_NODE_CREDENTIAL_ENCRYPTION_KEY
    # in production/staging) is a configuration error - log and
    # continue, so the rest of the engine still boots. Hosted
    # connections will fail their per-request resolution with the
    # same ConfigurationError, surfacing the misconfig to the
    # dashboard exactly once. Audit ref: CHECKLIST Section 8.
    # The eager startup sweep is bypass_threshold=True: it reprovisions
    # every missing / not-Ready hosted StatefulSet immediately rather
    # than waiting unhealthy_threshold_secs. run_once_at_startup() ->
    # _sweep -> _reprovision -> HostedProvisioner.provision_account()
    # BLOCKS on _wait_ready (StatefulSet Ready + ZMQ PING), a ~300s
    # (_READINESS_TIMEOUT_SECS) gate PER tenant.
    #
    # That gate MUST NOT run before yield. If it does, uvicorn never
    # binds :8000 during the sweep, the engine's /health startup probe
    # gets connection-refused for the whole window, the kubelet kills
    # the pod, and the engine crash-loops -- which never gives the
    # tenant Wine pod a stable parent to finish booting (a layering
    # inversion: engine readiness must not depend on tenant-pod
    # readiness). Audit ref: CHECKLIST Section 8 / defect #9.
    #
    # So we construct the service and arm the periodic background loop
    # inline (both instant), but run the eager bypass-threshold sweep
    # as a fire-and-forget background task via schedule_once(), exactly
    # mirroring the macro-cache warmup below and the provisioner's own
    # _catalog_sync_runner wave. The timeout (1800s) comfortably exceeds
    # the 300s per-tenant readiness gate under the default
    # max_concurrent_reprovisions so the eager sweep can fully complete,
    # while still being bounded so a wedged sweep cannot leak. The
    # engine reaches yield and serves /health immediately, then
    # converges hosted tenants in the background. The "full system
    # restart recovery" guarantee is preserved -- the eager sweep still
    # runs, just not on the blocking boot path. A request landing in
    # the gap resolves hosted state per-request and the row transitions
    # provisioning->ready as the background sweep completes.
    #
    # Construction failure (missing MT_NODE_CREDENTIAL_ENCRYPTION_KEY
    # in production/staging) is a configuration error - log and
    # continue, so the rest of the engine still boots. Hosted
    # connections will fail their per-request resolution with the
    # same ConfigurationError, surfacing the misconfig to the
    # dashboard exactly once. Audit ref: CHECKLIST Section 8.
    try:
        recovery_service = container.hosted_recovery_service
        recovery_service.start_background_loop(
            coordinator=container.background_tasks,
        )

        async def _hosted_recovery_startup_sweep() -> None:
            startup_summary = await recovery_service.run_once_at_startup()
            logger.info(
                "hosted_recovery_startup_complete",
                extra=startup_summary,
            )

        await container.background_tasks.schedule_once(
            "lifespan:hosted_recovery_startup_sweep",
            _hosted_recovery_startup_sweep,
            cooldown_s=3600.0,
            timeout_s=1800.0,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "hosted_recovery_startup_failed",
            extra={"error": str(exc), "error_type": type(exc).__name__},
        )

    try:
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
            # Use refresh() (force fetch + persist durable snapshot), NOT
            # collect(). On a cold start there is no Redis cache and no
            # persisted snapshot yet, so collect() would fall through to an
            # empty dataset and warm nothing real; the first true fetch
            # would then wait for the scheduler interval (up to 7 days for
            # COT/sentiment). refresh() fetches once at boot, repopulates
            # Redis, and writes the last-good snapshot so every subsequent
            # request-path cache miss serves real data with no API call.
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

        await container.background_tasks.schedule_once(
            "lifespan:macro_warmup",
            _macro_cache_warmup,
            cooldown_s=3600,
            timeout_s=300,
        )

        container.scheduler.start()
        logger.info("application_started", env=settings.app_env.value)

        yield

    except Exception:
        # Startup failed after background tasks were already registered.
        # Ensure every task and resource is cleaned up so tests do not see
        # 'Exception ignored in: <coroutine object ...>' warnings from
        # orphaned asyncio tasks that were never awaited.
        logger.error("lifespan_startup_failed", exc_info=True)
        raise
    finally:
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
    app.include_router(broker_metaapi.router)
    app.include_router(broker_bridge.router)
    app.include_router(chart.router)
    app.include_router(trading_plan.router)
    app.include_router(performance_review.router)

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Distributed-tracing server instrumentation. Attached only when
    # tracing is actually enabled (same guard as init_tracing in the
    # lifespan: a configured OTLP endpoint and not under test) so a
    # bare / local / test render attaches no middleware. The
    # instrumentor extracts the inbound W3C traceparent the gateway's
    # engine HTTP client injects and records a server span under the
    # gateway span, using the global provider + propagator that the
    # lifespan's init_tracing sets before the first request is served.
    # The /metrics mount is excluded so Prometheus scrapes do not
    # generate spans. Audit ref: observability end-to-end (Step 10d).
    if settings.otel_exporter_otlp_endpoint and not settings.is_testing:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app, excluded_urls="/metrics")

    # -- Global last-resort exception handler -----------------------------
    # Catches any exception that escapes a route or middleware without a
    # more specific handler, logs it with full structured context, and
    # returns a sanitized generic 500 so no internal detail leaks. Does
    # not intercept HTTPException / RequestValidationError or the
    # routers' typed ETradieBaseError mappings.
    from engine.shared.error_handler import register_exception_handlers

    register_exception_handlers(app)

    # -- Request body-size limit (TIER 4 "Length limits") -----------------
    # FastAPI/uvicorn impose no body cap by default and several
    # /internal/broker/* order-path endpoints decode raw
    # `await request.json()`. This middleware bounds every inbound body
    # (Content-Length fast path + streaming byte count) and is the
    # authoritative request-body size limit for the engine, mirroring
    # the Go services' http.MaxBytesReader cap. Added FIRST so it sits
    # OUTERMOST in Starlette's reverse-add middleware order and rejects
    # an oversized body before CSRF or any route handler runs.
    from engine.shared.body_limit import MaxBodySizeMiddleware

    app.add_middleware(MaxBodySizeMiddleware)

    # -- CSRF middleware ---------------------------------------------------
    # The CSRF check runs on the already-authenticated request
    # (get_current_user populates request.state.user via the route
    # dependency before the middleware chain runs in Starlette's order).
    # Internal routes (/internal/*) are exempt because they authenticate
    # with X-Internal-Auth instead of a browser session. Added after the
    # body-limit middleware (registered above) so an oversized body is
    # rejected before the CSRF check runs. There is no CORS middleware in
    # this app by design (see the NOTE below) so CSRF has no CORS
    # ordering dependency.
    from engine.shared.csrf import CSRFMiddleware

    app.add_middleware(CSRFMiddleware)

    # NOTE: no CORS middleware here by design. Under the Option B
    # architecture the SPA talks ONLY to the gateway origin; the engine
    # is reached exclusively via the gateway reverse proxy
    # (server-to-server), never directly by a browser, so no browser
    # ever reads a CORS header from the engine. CORS is emitted once, at
    # the gateway edge (src/gateway/internal/server/http_server.go
    # corsMiddleware), and the gateway proxy strips any upstream
    # Access-Control-* in ModifyResponse so the gateway is the single
    # CORS authority. Re-adding CORSMiddleware here would reintroduce the
    # duplicated `Access-Control-Allow-Credentials: true,true` the
    # browser rejects. Do NOT add it back.

    return app
