"""Health check endpoints.

Routes:
    GET /health
    GET /health/rag
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from engine.dependencies import Container

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/rag")
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
