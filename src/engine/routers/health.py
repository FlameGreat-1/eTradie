"""Health check endpoints.

Routes:
    GET /health      - liveness; trivial, non-blocking, always 200.
    GET /readiness   - readiness; 200 only when DB + cache + RAG are
                       all healthy. Used by the helm chart's
                       readinessProbe so the kubelet drops the pod
                       from the Service until dependencies are warm.
    GET /health/rag  - detailed RAG diagnostics for operators.

The split between /health and /readiness is deliberate: liveness
must never block on a downstream because that turns a slow
dependency into a pod restart loop. Readiness can block because the
worst case is traffic stops being routed to this pod until the
dependency recovers. Audit ref: V-14, X-8.
"""
from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from engine.config import get_rag_config
from engine.dependencies import Container
from engine.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Liveness probe. Returns immediately; never blocks on a downstream.

    The helm chart configures liveness + startup probes against this
    path; readiness lives at /readiness so a slow dependency does NOT
    trigger a pod restart loop.
    """
    return {"status": "ok"}


@router.get("/readiness")
async def readiness(request: Request, response: Response) -> dict:
    """Readiness probe. 200 when every critical dependency is healthy.

    Returns 503 (Service Unavailable) when any dependency is
    unhealthy so the kubelet removes this pod from the Service's
    endpoints. /health remains 200 in that case so the pod is not
    restarted (kubelet liveness != readiness).

    Audit ref: V-14, X-8.
    """
    container: Container = request.app.state.container

    # Trivial dependency checks already exercised by lifespan() in
    # engine.main.create_app. Both return bool; both are idempotent
    # and bounded (<= 1s on a healthy connection).
    db_ok = await container.db.health_check()
    cache_ok = await container.cache.health_check()

    # RAG readiness is optional - only required when RAG is enabled.
    # An engine with RAG_ENABLED=false (rare; mostly tests) should be
    # Ready as soon as DB + cache pass.
    rag_config = get_rag_config()
    rag_ok = True
    rag_detail: dict = {"enabled": False}
    if rag_config.enabled and hasattr(container, "rag_health_service"):
        rag_status = await container.rag_health_service.check()
        rag_ok = rag_status.overall_healthy
        rag_detail = {
            "enabled": True,
            "vectorstore_connected": rag_status.vectorstore.connected,
            "database_connected": rag_status.database_connected,
            "embedding_ready": rag_status.embedding_provider_ready,
        }

    healthy = bool(db_ok and cache_ok and rag_ok)
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning(
            "readiness_probe_unhealthy",
            extra={"db": db_ok, "cache": cache_ok, "rag": rag_ok},
        )
    return {
        "status": "ready" if healthy else "not_ready",
        "db": db_ok,
        "cache": cache_ok,
        "rag": rag_detail,
    }


@router.get("/health/rag")
async def rag_health(request: Request) -> dict:
    """Detailed RAG diagnostics for operators (not used by probes)."""
    container: Container = request.app.state.container
    if not hasattr(container, "rag_health_service"):
        return {"status": "disabled"}
    rag_status = await container.rag_health_service.check()
    return {
        "status": "healthy" if rag_status.overall_healthy else "degraded",
        "vectorstore_connected": rag_status.vectorstore.connected,
        "database_connected": rag_status.database_connected,
        "embedding_ready": rag_status.embedding_provider_ready,
        "documents_count": rag_status.vectorstore.documents_collection_count,
        "scenarios_count": rag_status.vectorstore.scenarios_collection_count,
    }


@router.get("/health/providers")
async def providers_health(request: Request) -> dict:
    """Per-provider health for operators (not used by probes).

    Runs the provider registry's health check across every registered
    macro data provider (central bank, COT, economic, market data,
    sentiment, calendar). As a side effect this refreshes the
    ACTIVE_PROVIDERS Prometheus gauge per category, so an operator
    scrape after hitting this endpoint reflects current provider
    health. Grouped by category and provider name for quick triage of
    which external feed is degraded.
    """
    container: Container = request.app.state.container
    if not hasattr(container, "registry"):
        return {"status": "disabled"}

    statuses = await container.registry.health_check_all()
    providers = container.registry.all_providers

    by_provider: dict[str, dict[str, str]] = {}
    healthy = 0
    for name, status in statuses.items():
        category = (
            providers[name].category.value
            if name in providers
            else "unknown"
        )
        by_provider[name] = {
            "category": category,
            "status": status.value,
        }
        if status.value == "HEALTHY":
            healthy += 1

    total = len(statuses)
    return {
        "status": "healthy" if healthy == total else "degraded",
        "healthy": healthy,
        "total": total,
        "providers": by_provider,
    }
