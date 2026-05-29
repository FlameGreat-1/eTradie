"""Request and response schemas for the engine API.

Extracted from main.py for maintainability. Every schema is a pure
Pydantic model with no side effects.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from engine.processor.config import get_processor_config


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
    api_key: Optional[str] = Field(
        default=None, description="API key for the new provider"
    )
    api_base_url: Optional[str] = Field(
        default=None, description="Base URL for self-hosted"
    )


# -- Request schemas for internal gateway endpoints --------------------------


class InternalLTFConfirmRequest(BaseModel):
    symbol: str
    direction: str  # "BULLISH" or "BEARISH"
    ltf_timeframe: str  # e.g. "M5", "M15"
    ob_upper: float
    ob_lower: float
    entry_price: float
    trace_id: Optional[str] = None

    # Invalidation layer fields. When provided, the service runs HTF
    # invalidation checks (OB mitigation, opposing BMS, SL blown)
    # before the LTF confirmation checks.
    stop_loss: Optional[float] = None
    htf_timeframe: Optional[str] = None  # e.g. "H4" - derived from LTF if not set


class InternalTARequest(BaseModel):
    symbols: list[str]
    trace_id: Optional[str] = None


class InternalMacroRequest(BaseModel):
    trace_id: Optional[str] = None


class InternalRAGRequest(BaseModel):
    query_text: str
    strategy: Optional[str] = None
    framework: Optional[str] = None
    setup_family: Optional[str] = None
    direction: Optional[str] = None
    timeframe: Optional[str] = None
    style: Optional[str] = None
    symbol: Optional[str] = None
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
    dxy_momentum: Optional[str] = None
    risk_environment: Optional[str] = None
    trace_id: Optional[str] = None


class InternalProcessorRequest(BaseModel):
    """Payload for POST /internal/processor/process.

    user_id, tier, role, username are OPTIONAL because the gateway
    forwards them via X-User-Id / X-User-Tier / X-User-Role /
    X-User-Username headers as the canonical channel. The body
    fields exist for callers that prefer a single transport (the
    handler resolves header-first, body-second).
    """
    processor_input: dict
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    tier: Optional[str] = None
    role: Optional[str] = None
    username: Optional[str] = None


class InternalDebugRunCycleRequest(BaseModel):
    """Payload sent by the Go gateway after a successful analysis cycle.

    Contains the full pipeline data (TA, macro, RAG, processor) so the
    engine can persist it to /output/runcycle/ for offline inspection.
    """
    symbol: str
    ta_data: dict
    macro_data: Optional[dict] = None
    rag_data: Optional[dict] = None
    processor_data: Optional[dict] = None
    execution_request: Optional[dict] = None
    trace_id: Optional[str] = None


class CreateLLMConnectionRequest(BaseModel):
    provider: str
    api_key: str
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default_factory=lambda: get_processor_config().max_output_tokens, ge=1024, le=131072)
    label: Optional[str] = None
    activate: bool = True

class UpdateLLMConnectionRequest(BaseModel):
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(default=None, ge=1024, le=131072)
    label: Optional[str] = None

class CreateBrokerConnectionRequest(BaseModel):
    connection_type: str  # 'ea', 'metaapi', or 'hosted'
    name: str
    # MetaAPI / Hosted: user's MT broker credentials
    mt5_login: Optional[str] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None
    platform: str = Field(default="mt5", description="Trading platform (mt4 or mt5)")
    # Default chart symbol for the hosted MT terminal (broker-correct name,
    # e.g. 'EURUSDm' on Exness). Defaults to 'EURUSD'. The engine writes
    # this into the StatefulSet's MT_SYMBOL env var at provision time.
    mt5_symbol: str = Field(default="EURUSD", description="Default chart symbol (broker-correct name)")
    # EA: no user-facing fields (auto from env)
    activate: bool = True

class UpdateBrokerConnectionRequest(BaseModel):
    name: Optional[str] = None
    mt5_server: Optional[str] = None
    mt5_login: Optional[str] = None
    mt5_password: Optional[str] = None
    platform: Optional[str] = None
