"""Admin processor configuration endpoints.

Routes:
    GET /api/processor/models
    GET /api/processor/config
    PUT /api/processor/config
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import SecretStr

from engine.dependencies import Container
from engine.processor.config import ProcessorConfig
from engine.processor.constants import (
    AVAILABLE_MODELS,
    DEFAULT_MODELS,
    MODEL_CATALOG,
    LLMProvider,
)
from engine.processor.llm.factory import create_llm_client
from engine.processor.service import AnalysisProcessor
from engine.schemas import ProcessorConfigResponse, ProcessorConfigUpdateRequest
from engine.shared.auth import AuthenticatedUser, get_admin_user
from engine.shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/processor/models")
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
        "catalog": MODEL_CATALOG,
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


@router.get("/api/processor/config")
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


@router.put("/api/processor/config")
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
        logger.error("processor_config_invalid", extra={"error": str(exc)})
        raise HTTPException(
            status_code=400,
            detail="Invalid processor configuration. Check the provider, model and limits and try again.",
        )

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
