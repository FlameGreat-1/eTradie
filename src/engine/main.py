from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, Request
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

from engine.config import TAConfig, get_rag_config, get_settings
from engine.dependencies import Container
from engine.shared.logging import configure_logging, get_logger
from engine.shared.metrics.prometheus import APP_INFO
from engine.shared.tracing.otel import init_tracing
from engine.macro.scheduler_jobs import register_macro_jobs
from engine.ta.scheduler_jobs import register_ta_jobs
from engine.processor.constants import LLMProvider
from gateway.config import get_gateway_config
from gateway.container import GatewayContainer

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

    ta_config = TAConfig()
    register_ta_jobs(
        container.scheduler,
        ta_config=ta_config,
        orchestrator=container.ta_orchestrator,
        broker_client=container.mt5_client,
        candle_repository=container.candle_repository,
    )

    # -- Processor LLM -------------------------------------------------------
    container.build_processor()
    logger.info(
        "processor_built",
        provider=container.processor_config.llm_provider,
        model=container.processor_config.model_name,
    )

    # -- Gateway Orchestration -----------------------------------------------
    gateway_config = get_gateway_config()
    if gateway_config.enabled:
        gateway = GatewayContainer(
            engine=container,
            processor=container.processor,
        )
        app.state.gateway = gateway
        gateway.register_scheduler()
        logger.info(
            "gateway_started",
            cycle_interval=gateway_config.cycle_interval_seconds,
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

    # -- Analysis dashboard endpoints ----------------------------------------

    @app.get("/api/analysis/latest")
    async def get_latest_analyses(
        request: Request,
        pair: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """List recent analyses for the dashboard.

        Returns the LLM analysis decisions so users can see what
        the processor analyzed and decided.
        """
        container: Container = request.app.state.container
        if not hasattr(container, "processor_analysis_repo"):
            raise HTTPException(status_code=503, detail="Processor not initialized")

        repo = container.processor_analysis_repo
        limit = min(limit, 100)

        if pair:
            rows = await repo.get_latest_by_pair(pair.upper(), limit=limit)
        else:
            rows = await repo.list_all(limit=limit)

        results = []
        for row in rows:
            results.append({
                "analysis_id": row.analysis_id,
                "pair": row.pair,
                "direction": row.direction,
                "setup_grade": row.setup_grade,
                "confluence_score": row.confluence_score,
                "confidence": row.confidence,
                "proceed_to_module_b": row.proceed_to_module_b,
                "rr_ratio": row.rr_ratio,
                "entry_price_low": row.entry_price_low,
                "entry_price_high": row.entry_price_high,
                "stop_loss_price": row.stop_loss_price,
                "tp1_price": row.tp1_price,
                "tp2_price": row.tp2_price,
                "tp3_price": row.tp3_price,
                "trading_style": row.trading_style,
                "session": row.session,
                "llm_provider": row.llm_provider,
                "llm_model": row.llm_model,
                "status": row.status,
                "duration_ms": row.duration_ms,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })

        return {"analyses": results, "count": len(results)}

    @app.get("/api/analysis/{analysis_id}")
    async def get_analysis_detail(request: Request, analysis_id: str) -> dict:
        """Full analysis detail including LLM reasoning and raw output.

        This is what the dashboard displays so users can see the
        complete LLM analysis, reasoning chain, confluence factors,
        trade construction, and citations.
        """
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

        return {
            "analysis_id": row.analysis_id,
            "pair": row.pair,
            "direction": row.direction,
            "setup_grade": row.setup_grade,
            "confluence_score": row.confluence_score,
            "confidence": row.confidence,
            "proceed_to_module_b": row.proceed_to_module_b,
            "rr_ratio": row.rr_ratio,
            "entry_price_low": row.entry_price_low,
            "entry_price_high": row.entry_price_high,
            "stop_loss_price": row.stop_loss_price,
            "tp1_price": row.tp1_price,
            "tp2_price": row.tp2_price,
            "tp3_price": row.tp3_price,
            "trading_style": row.trading_style,
            "session": row.session,
            "llm_provider": row.llm_provider,
            "llm_model": row.llm_model,
            "status": row.status,
            "error_message": row.error_message,
            "duration_ms": row.duration_ms,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "raw_output": row.raw_output,
            "audit": audit_data,
        }

    # -- Processor config endpoints (LLM provider/model switching) -----------

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
        Takes effect on the next analysis cycle. Does not interrupt
        any currently running cycle.
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

        # Build new config with overrides
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

        # Override API key for the new provider if provided
        if body.api_key:
            key_field = f"{new_provider}_api_key"
            if key_field in config_overrides:
                config_overrides[key_field] = SecretStr(body.api_key)

        try:
            new_cfg = ProcessorConfig(**config_overrides)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid configuration: {exc}")

        # Close old client
        if hasattr(container, "processor_llm_client"):
            await container.processor_llm_client.close()

        # Build new client and processor
        new_client = create_llm_client(new_cfg)
        new_processor = AnalysisProcessor(
            config=new_cfg,
            llm_client=new_client,
            analysis_repo=container.processor_analysis_repo,
            audit_repo=container.processor_audit_repo,
        )

        # Swap references
        container.processor_config = new_cfg
        container.processor_llm_client = new_client
        container.processor = new_processor

        # Update gateway's orchestrator if gateway is active
        if hasattr(request.app.state, "gateway"):
            gw: GatewayContainer = request.app.state.gateway
            gw.orchestrator._processor = new_processor

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

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app
