from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from engine.config import get_settings
from engine.dependencies import Container
from engine.shared.logging import configure_logging, get_logger
from engine.shared.metrics.prometheus import APP_INFO
from engine.shared.tracing.otel import init_tracing
from engine.macro.scheduler_jobs import register_macro_jobs
from engine.ta.scheduler_jobs import register_ta_jobs
from engine.config import TAConfig

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

    ta_config = TAConfig()
    register_ta_jobs(
        container.scheduler,
        ta_config=ta_config,
        orchestrator=container.ta_orchestrator,
        broker_client=container.mt5_client,
        candle_repository=container.candle_repository,
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

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app
