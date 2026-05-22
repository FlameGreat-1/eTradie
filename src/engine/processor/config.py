"""Processor-specific configuration.

Loaded from environment variables prefixed with ``PROCESSOR_``.
Validated at startup; the application fails fast on invalid values.
Follows the same pattern as GatewayConfig.

The processor is LLM-agnostic. Users select their provider and model
from the dashboard. Environment variables set the defaults.

LLM token metering (Pro Managed quota enforcement) is configured
separately via the top-level METERING_ENABLED / METERING_GATEWAY_URL /
ENGINE_INTERNAL_SHARED_SECRET env vars consumed directly by
engine.shared.metering_client. Those values are deliberately NOT
mirrored on ProcessorConfig: the metering client is process-wide and
should not be re-resolvable per ProcessorConfig instance (which is
built per-user from saved LLM connection rows). Mirroring them here
would create two sources of truth and silent drift.
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
        default=0.0,
        ge=0.0,
        le=2.0,
        description="LLM temperature. 0 for deterministic output.",
    )
    max_output_tokens: int = Field(
        default=32768,
        ge=1024,
        le=131072,
        description=(
            "Maximum tokens in the LLM response. Sized for the worst-case "
            "AnalysisOutput (deeply nested, up to 30 RAG citations + 30 "
            "audit citations, up to 50 evidence items per nested model, "
            "explainable_reasoning capped at ~2048 tokens) plus the "
            "reasoning_budget_tokens cap below. 32768 leaves ~20k for "
            "visible output after the 12288 reasoning cap, which is "
            "several multiples of the real p99. Truncation on a "
            "well-formed analysis is practically impossible. Providers "
            "bill on tokens actually generated, not on this ceiling, so "
            "raising it is cost-neutral on average."
        ),
    )
    reasoning_budget_tokens: Optional[int] = Field(
        default=12288,
        ge=0,
        le=131072,
        description=(
            "Cap on hidden reasoning tokens for thinking-capable models "
            "(Gemini thinking_config.thinking_budget, Anthropic "
            "thinking.budget_tokens, OpenAI o-series reasoning_effort). "
            "Sized for cross-source reasoning over TA snapshots (13 "
            "timeframes) + SMC/SnD candidates + macro + RAG + user OS. "
            "12288 maps to OpenAI o-series reasoning_effort='medium' "
            "via reasoning.py's ordinal translator. Bounded so the "
            "model cannot degenerate into a 15k+ thinking spiral that "
            "would exhaust max_output_tokens before emitting visible "
            "output (the MAX_TOKENS failure mode documented in "
            "PROBLEM.md). None = capability-driven default from "
            "MODEL_CATALOG. 0 = disable thinking on supported providers."
        ),
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
    # Upper bounds are sized to accommodate the slow tail of large-context
    # LLM calls (~280KB user message, 26 RAG chunks) without relaxing the
    # defaults for the common case. The defaults stay at 60/90 to keep
    # existing deployments behaviourally unchanged.
    llm_timeout_seconds: int = Field(
        default=150,
        ge=10,
        le=540,
        description=(
            "Timeout for a single LLM API call. A 32k output budget + "
            "12k reasoning budget on a thinking-capable model takes "
            "60-120s of wall time at typical provider TPS. 150s leaves "
            "headroom for the slow tail of large-context calls (~280KB "
            "user message, 26 RAG chunks) without cutting off the "
            "budget before it can be spent."
        ),
    )
    total_timeout_seconds: int = Field(
        default=180,
        ge=15,
        le=600,
        description=(
            "Total timeout for the full process() call including "
            "retries. Must accommodate at least one full llm_timeout_seconds "
            "plus the prompt-build, metering, parsing, and audit-persist "
            "phases. Sized so a single retry on a transient failure "
            "still fits inside the wall-clock budget."
        ),
    )

    # -- Retry policy --------------------------------------------------------
    max_retries: int = Field(
        default=1,
        ge=0,
        le=5,
        description=(
            "Max retries on transient LLM failures (502/504, network "
            "glitches, connect/read timeouts). Rate-limit (429), "
            "provider-overload (503/529), and quota-exhausted are NOT "
            "retried -- see retry.py docstring. One retry is enough "
            "for genuine transient blips; sustained outages should "
            "fail fast so the gateway-level cycle retry can handle "
            "recovery on a longer wall-clock cadence without burning "
            "the user-facing trigger latency budget."
        ),
    )
    retry_backoff_base_seconds: float = Field(
        default=1.0,
        ge=0.5,
        le=10.0,
        description="Base delay for exponential backoff",
    )
    retry_backoff_max_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
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

    # -- Metering --------------------------------------------------------------
    # Drives whether service.py invokes the gateway's metering layer
    # (reserve / commit / refund). True only for configs built from the
    # platform LLM key (the env-var baseline or the `is_platform=true`
    # row in llm_connections). False for any BYOK config built from a
    # personal row in llm_connections: the user pays their own provider
    # bill so the platform has nothing to meter.
    #
    # Default False so a caller that constructs a ProcessorConfig without
    # setting the flag is treated as BYOK and skips metering. The two
    # platform paths (_load_platform_processor_config and the env-var
    # startup config) set it explicitly.
    uses_platform_key: bool = Field(
        default=False,
        description=(
            "Internal flag set by the LLM-connection resolver to indicate "
            "this config carries the platform API key. service.py uses it "
            "to gate metering calls so BYOK users never touch the "
            "platform's billing_usage counters."
        ),
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
