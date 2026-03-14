"""Processor-specific configuration.

Loaded from environment variables prefixed with ``PROCESSOR_``.
Validated at startup; the application fails fast on invalid values.
Follows the same pattern as GatewayConfig.

The processor is LLM-agnostic. Users select their provider and model
from the dashboard. Environment variables set the defaults.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from engine.processor.constants import (
    DEFAULT_MODEL,
    DEFAULT_MODELS,
    DEFAULT_PROVIDER,
    LLMProvider,
)


class ProcessorConfig(BaseSettings):
    """Processor LLM configuration."""

    model_config = SettingsConfigDict(
        env_prefix="PROCESSOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Provider selection ---------------------------------------------------
    llm_provider: str = Field(
        default=DEFAULT_PROVIDER,
        description="Active LLM provider: anthropic, openai, gemini, self_hosted",
    )
    model_name: str = Field(
        default="",
        description="Model identifier. Any model string accepted. Empty = provider default.",
    )
    temperature: float = Field(
        default=0.0, ge=0.0, le=2.0,
        description="LLM temperature. 0 for deterministic output.",
    )
    max_output_tokens: int = Field(
        default=16384, ge=1024, le=131072,
        description="Maximum tokens in LLM response",
    )

    # -- Provider API keys (only the active provider's key is required) ------
    anthropic_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Anthropic API key for Claude models",
    )
    openai_api_key: Optional[SecretStr] = Field(
        default=None,
        description="OpenAI API key for GPT models",
    )
    gemini_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Google Gemini API key",
    )
    self_hosted_api_key: Optional[SecretStr] = Field(
        default=None,
        description="API key for self-hosted endpoint (optional, some don't require one)",
    )

    # -- Self-hosted endpoint ------------------------------------------------
    api_base_url: Optional[str] = Field(
        default=None,
        description="Base URL for self-hosted OpenAI-compatible API (e.g. http://localhost:8000/v1)",
    )

    # -- Timeouts ------------------------------------------------------------
    llm_timeout_seconds: int = Field(
        default=60, ge=10, le=300,
        description="Timeout for a single LLM API call",
    )
    total_timeout_seconds: int = Field(
        default=90, ge=15, le=360,
        description="Total timeout for the full process() call including retries",
    )

    # -- Retry policy --------------------------------------------------------
    max_retries: int = Field(
        default=2, ge=0, le=5,
        description="Max retries on transient LLM failures",
    )
    retry_backoff_base_seconds: float = Field(
        default=1.0, ge=0.5, le=10.0,
        description="Base delay for exponential backoff",
    )
    retry_backoff_max_seconds: float = Field(
        default=30.0, ge=5.0, le=120.0,
        description="Maximum delay between retries",
    )

    # -- Validation ----------------------------------------------------------
    strict_schema_validation: bool = Field(
        default=True,
        description="Reject LLM responses that fail schema validation",
    )
    require_citations: bool = Field(
        default=True,
        description="Require RAG citations in every analysis output",
    )

    # -- Audit ---------------------------------------------------------------
    persist_audit_logs: bool = Field(
        default=True,
        description="Persist analysis audit trail to Postgres",
    )
    log_raw_llm_response: bool = Field(
        default=False,
        description="Log full raw LLM response (dev/debug only)",
    )

    @model_validator(mode="after")
    def _set_default_model(self) -> Self:
        """Auto-fill model_name from provider defaults if empty."""
        if not self.model_name:
            default = DEFAULT_MODELS.get(self.llm_provider, DEFAULT_MODEL)
            object.__setattr__(self, "model_name", default)
        return self

    @model_validator(mode="after")
    def _validate_provider_api_key(self) -> Self:
        """Ensure the active provider's API key is set.

        self_hosted may not require a key (some local endpoints don't).
        """
        provider = self.llm_provider
        key_map: dict[str, Optional[SecretStr]] = {
            LLMProvider.ANTHROPIC: self.anthropic_api_key,
            LLMProvider.OPENAI: self.openai_api_key,
            LLMProvider.GEMINI: self.gemini_api_key,
        }

        if provider in key_map:
            key = key_map[provider]
            if key is None or not key.get_secret_value():
                raise ValueError(
                    f"Provider '{provider}' requires PROCESSOR_{provider.upper()}_API_KEY to be set"
                )

        if provider == LLMProvider.SELF_HOSTED and not self.api_base_url:
            raise ValueError(
                "Provider 'self_hosted' requires PROCESSOR_API_BASE_URL to be set"
            )

        return self

    @model_validator(mode="after")
    def _validate_provider_value(self) -> Self:
        """Ensure llm_provider is a recognized value."""
        valid = {p.value for p in LLMProvider}
        if self.llm_provider not in valid:
            raise ValueError(
                f"llm_provider '{self.llm_provider}' not recognized. "
                f"Must be one of: {', '.join(sorted(valid))}"
            )
        return self

    @model_validator(mode="after")
    def _validate_timeout_budget(self) -> Self:
        """Total timeout must accommodate at least one LLM call."""
        if self.total_timeout_seconds <= self.llm_timeout_seconds:
            raise ValueError(
                f"total_timeout_seconds ({self.total_timeout_seconds}s) must be "
                f"greater than llm_timeout_seconds ({self.llm_timeout_seconds}s)"
            )
        return self

    def get_active_api_key(self) -> str:
        """Return the API key for the active provider.

        Returns empty string for self_hosted when no key is configured.
        """
        key_map: dict[str, Optional[SecretStr]] = {
            LLMProvider.ANTHROPIC: self.anthropic_api_key,
            LLMProvider.OPENAI: self.openai_api_key,
            LLMProvider.GEMINI: self.gemini_api_key,
            LLMProvider.SELF_HOSTED: self.self_hosted_api_key,
        }
        key = key_map.get(self.llm_provider)
        if key is not None:
            return key.get_secret_value()
        return ""


@lru_cache(maxsize=1)
def get_processor_config() -> ProcessorConfig:
    """Return the singleton processor config, cached after first load."""
    return ProcessorConfig()
