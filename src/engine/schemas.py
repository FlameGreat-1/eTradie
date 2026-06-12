"""Request and response schemas for the engine API.

Extracted from main.py for maintainability. Every schema is a pure
Pydantic model with no side effects.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from engine.processor.config import get_processor_config

# Shared strict config for every REQUEST model below. extra="forbid"
# implements TIER 4 "Reject unknown fields": a body carrying any field
# not declared on the model is a 422, not silently ignored (Pydantic
# v2's default is extra="ignore"). Response models do not use this.
_STRICT_REQUEST_CONFIG = ConfigDict(extra="forbid")


# -- Request/Response schemas for dashboard API ------------------------------


class ProcessorConfigResponse(BaseModel):
    llm_provider: str
    model_name: str
    temperature: float
    max_output_tokens: int
    supported_providers: list[str]


class ProcessorConfigUpdateRequest(BaseModel):
    model_config = _STRICT_REQUEST_CONFIG

    llm_provider: str | None = None
    model_name: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: int | None = Field(default=None, ge=1024, le=131072)
    api_key: str | None = Field(default=None, description="API key for the new provider")
    api_base_url: str | None = Field(default=None, description="Base URL for self-hosted")


# -- Request schemas for internal gateway endpoints --------------------------


class InternalLTFConfirmRequest(BaseModel):
    model_config = _STRICT_REQUEST_CONFIG

    symbol: str
    direction: str  # "BULLISH" or "BEARISH"
    ltf_timeframe: str  # e.g. "M5", "M15"
    ob_upper: float
    ob_lower: float
    entry_price: float
    trace_id: str | None = None

    # Invalidation layer fields. When provided, the service runs HTF
    # invalidation checks (OB mitigation, opposing BMS, SL blown)
    # before the LTF confirmation checks.
    stop_loss: float | None = None
    htf_timeframe: str | None = None  # e.g. "H4" - derived from LTF if not set


class InternalTARequest(BaseModel):
    model_config = _STRICT_REQUEST_CONFIG

    symbols: list[str]
    trace_id: str | None = None


class InternalMacroRequest(BaseModel):
    model_config = _STRICT_REQUEST_CONFIG

    trace_id: str | None = None


class InternalRAGRequest(BaseModel):
    model_config = _STRICT_REQUEST_CONFIG

    query_text: str
    strategy: str | None = None
    framework: str | None = None
    setup_family: str | None = None
    direction: str | None = None
    timeframe: str | None = None
    style: str | None = None
    symbol: str | None = None
    all_frameworks: list[str] = Field(default_factory=list)
    all_setup_families: list[str] = Field(default_factory=list)
    has_smc_candidates: bool = False
    has_snd_candidates: bool = False
    has_macro_data: bool = False
    has_cot_data: bool = False
    has_rate_decision: bool = False
    has_high_impact_event: bool = False
    has_dxy_data: bool = False
    has_qe_qt: bool = False
    has_stagflation: bool = False
    has_cot_extremes: bool = False
    has_tff_data: bool = False
    has_core_inflation: bool = False
    has_safe_haven_elevated: bool = False
    has_commodity_currencies_weak: bool = False
    dxy_momentum: str | None = None
    risk_environment: str | None = None
    trace_id: str | None = None


class InternalProcessorRequest(BaseModel):
    """Payload for POST /internal/processor/process.

    user_id, tier, role, username are OPTIONAL because the gateway
    forwards them via X-User-Id / X-User-Tier / X-User-Role /
    X-User-Username headers as the canonical channel. The body
    fields exist for callers that prefer a single transport (the
    handler resolves header-first, body-second).
    """

    model_config = _STRICT_REQUEST_CONFIG

    processor_input: dict
    trace_id: str | None = None
    user_id: str | None = None
    tier: str | None = None
    role: str | None = None
    username: str | None = None


class InternalDebugRunCycleRequest(BaseModel):
    """Payload sent by the Go gateway after a successful analysis cycle.

    Contains the full pipeline data (TA, macro, RAG, processor) so the
    engine can persist it to /output/runcycle/ for offline inspection.
    """

    model_config = _STRICT_REQUEST_CONFIG

    symbol: str
    ta_data: dict
    macro_data: dict | None = None
    rag_data: dict | None = None
    processor_data: dict | None = None
    execution_request: dict | None = None
    trace_id: str | None = None


class CreateLLMConnectionRequest(BaseModel):
    model_config = _STRICT_REQUEST_CONFIG

    provider: str
    api_key: str
    model_name: str | None = None
    base_url: str | None = None
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_output_tokens: int = Field(
        default_factory=lambda: get_processor_config().max_output_tokens,
        ge=1024,
        le=131072,
    )
    label: str | None = None
    activate: bool = True


class UpdateLLMConnectionRequest(BaseModel):
    model_config = _STRICT_REQUEST_CONFIG

    provider: str | None = None
    model_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: int | None = Field(default=None, ge=1024, le=131072)
    label: str | None = None


class CreateBrokerConnectionRequest(BaseModel):
    model_config = _STRICT_REQUEST_CONFIG

    connection_type: str  # 'ea', 'metaapi', or 'hosted'
    name: str
    # MetaAPI / Hosted: user's MT broker credentials
    mt5_login: str | None = None
    mt5_password: str | None = None
    mt5_server: str | None = None
    # 'mt4' is reserved but rejected at the router until the MT4 EA
    # binary is bundled in the mt-node image. Only 'mt5' is buildable
    # end-to-end today; see docker/mt-node/ea/README.md.
    platform: str = Field(
        default="mt5",
        description="Trading platform. Currently only 'mt5' is supported end-to-end; 'mt4' is reserved for future support.",
    )
    # No symbol field. The hosted provisioner runs automatic broker
    # symbol resolution (GET_ALL_SYMBOLS over ZMQ) after the Pod boots
    # and persists the canonical->broker-actual map to the row.
    activate: bool = True


class UpdateBrokerConnectionRequest(BaseModel):
    model_config = _STRICT_REQUEST_CONFIG

    name: str | None = None
    mt5_server: str | None = None
    mt5_login: str | None = None
    mt5_password: str | None = None
    platform: str | None = None
