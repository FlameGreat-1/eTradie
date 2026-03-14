"""Processor-specific configuration.

Loaded from environment variables prefixed with ``PROCESSOR_``.
Validated at startup; the application fails fast on invalid values.
Follows the same pattern as GatewayConfig.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from engine.processor.constants import DEFAULT_MODEL


class ProcessorConfig(BaseSettings):
    """Processor LLM configuration."""

    model_config = SettingsConfigDict(
        env_prefix="PROCESSOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Anthropic API -------------------------------------------------------
    anthropic_api_key: SecretStr = Field(
        description="Anthropic API key for Claude access",
    )
    model_name: str = Field(
        default=DEFAULT_MODEL,
        description="Claude model identifier",
    )
    temperature: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="LLM temperature. 0 for deterministic output.",
    )
    max_output_tokens: int = Field(
        default=16384, ge=1024, le=65536,
        description="Maximum tokens in LLM response",
    )

    # -- Timeouts ------------------------------------------------------------
    llm_timeout_seconds: int = Field(
        default=60, ge=10, le=180,
        description="Timeout for a single LLM API call",
    )
    total_timeout_seconds: int = Field(
        default=90, ge=15, le=240,
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
    def _validate_timeout_budget(self) -> Self:
        """Total timeout must accommodate at least one LLM call."""
        if self.total_timeout_seconds <= self.llm_timeout_seconds:
            raise ValueError(
                f"total_timeout_seconds ({self.total_timeout_seconds}s) must be "
                f"greater than llm_timeout_seconds ({self.llm_timeout_seconds}s)"
            )
        return self


@lru_cache(maxsize=1)
def get_processor_config() -> ProcessorConfig:
    """Return the singleton processor config, cached after first load."""
    return ProcessorConfig()
