"""Gateway-specific configuration.

Loaded from environment variables prefixed with ``GATEWAY_``.
Validated at startup; the application fails fast on invalid values.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewayConfig(BaseSettings):
    """Gateway orchestration configuration."""

    model_config = SettingsConfigDict(
        env_prefix="GATEWAY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Master switch for the gateway service")

    # -- Cycle timing --------------------------------------------------------
    cycle_interval_seconds: int = Field(
        default=14400, ge=60,
        description="Interval between analysis cycles (default 4 H)",
    )
    cycle_timeout_seconds: int = Field(
        default=300, ge=30, le=600,
        description="Hard timeout for a single analysis cycle",
    )

    # -- Parallelism ---------------------------------------------------------
    max_concurrent_symbols: int = Field(
        default=4, ge=1, le=16,
        description="Max symbols analysed concurrently within one cycle",
    )
    ta_macro_parallel_timeout_seconds: int = Field(
        default=120, ge=10, le=300,
        description="Timeout for the parallel TA + Macro collection phase",
    )

    # -- RAG -----------------------------------------------------------------
    rag_timeout_seconds: int = Field(
        default=30, ge=5, le=120,
        description="Timeout for RAG retrieval",
    )

    # -- Processor LLM -------------------------------------------------------
    processor_timeout_seconds: int = Field(
        default=60, ge=10, le=180,
        description="Timeout for the processor LLM call",
    )

    # -- Guard evaluation ----------------------------------------------------
    guard_timeout_seconds: int = Field(
        default=10, ge=2, le=30,
        description="Timeout for post-processor guard evaluation",
    )

    # -- Retry policy --------------------------------------------------------
    max_cycle_retries: int = Field(
        default=1, ge=0, le=3,
        description="Retries for a failed cycle before giving up",
    )
    retry_backoff_base_seconds: float = Field(
        default=2.0, ge=0.5, le=30.0,
    )

    # -- Observability -------------------------------------------------------
    log_full_context_payload: bool = Field(
        default=False,
        description="Log the full LLM context payload (dev/debug only)",
    )

    @model_validator(mode="after")
    def _validate_timeout_budget(self) -> Self:
        """Ensure sub-phase timeouts fit within the cycle timeout."""
        sub_total = (
            self.ta_macro_parallel_timeout_seconds
            + self.rag_timeout_seconds
            + self.processor_timeout_seconds
            + self.guard_timeout_seconds
        )
        if sub_total >= self.cycle_timeout_seconds:
            raise ValueError(
                f"Sum of sub-phase timeouts ({sub_total}s) must be less than "
                f"cycle_timeout_seconds ({self.cycle_timeout_seconds}s) to allow "
                f"overhead for context assembly and routing"
            )
        return self


@lru_cache(maxsize=1)
def get_gateway_config() -> GatewayConfig:
    """Return the singleton gateway config, cached after first load."""
    return GatewayConfig()
