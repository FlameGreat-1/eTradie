"""LLM connection management endpoints.

Routes:
    GET    /api/llm/providers
    GET    /api/llm/connections
    GET    /api/llm/connections/active
    POST   /api/llm/connections
    PUT    /api/llm/connections/{connection_id}
    POST   /api/llm/connections/{connection_id}/activate
    POST   /api/llm/connections/{connection_id}/deactivate
    DELETE /api/llm/connections/{connection_id}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from engine.dependencies import Container
from engine.helpers import _rate_limit
from engine.processor.constants import AVAILABLE_MODELS, DEFAULT_MODELS, LLMProvider
from engine.processor.storage.repositories.llm_connection_repository import (
    LLMConnectionRepository,
)
from engine.schemas import CreateLLMConnectionRequest, UpdateLLMConnectionRequest
from engine.shared.auth import AuthenticatedUser, get_current_user
from engine.shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/llm/providers")
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


@router.get("/api/llm/connections")
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


@router.get("/api/llm/connections/active")
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


@router.post("/api/llm/connections")
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

    # Auto-resolve model: use the platform's curated default for the
    # provider when the frontend does not send a specific model.
    resolved_model = body.model_name
    if not resolved_model or not resolved_model.strip():
        resolved_model = DEFAULT_MODELS.get(body.provider, "")
    if not resolved_model:
        raise HTTPException(
            status_code=400,
            detail=f"No default model configured for provider '{body.provider}'. Please contact support.",
        )

    # Temperature is locked to 0.0 for deterministic trading analysis.
    resolved_temperature = 0.0

    async with container.db.session() as session:
        repo = LLMConnectionRepository(session)
        row = await repo.create(
            user_id=user.user_id,
            provider=body.provider,
            model_name=resolved_model,
            api_key=body.api_key,
            base_url=body.base_url,
            temperature=resolved_temperature,
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
        "model_name": resolved_model,
        "is_active": body.activate,
        "label": body.label or f"{body.provider} / {resolved_model}",
        "message": (
            "Connection created and activated."
            if body.activate
            else "Connection created."
        ),
    }


@router.put("/api/llm/connections/{connection_id}")
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


@router.post("/api/llm/connections/{connection_id}/activate")
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


@router.post("/api/llm/connections/{connection_id}/deactivate")
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


@router.delete("/api/llm/connections/{connection_id}")
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
