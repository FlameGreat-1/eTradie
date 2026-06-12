"""Processor enums and constants.

All processor-specific enumerations and fixed values.
Every other processor module imports from this file.
"""

from __future__ import annotations

from enum import StrEnum, unique
from typing import Final, TypedDict


@unique
class LLMProvider(StrEnum):
    """Supported LLM providers.

    The system is LLM-agnostic. Users select their provider
    from the dashboard. Default is ANTHROPIC.
    SELF_HOSTED covers any OpenAI-compatible API (vLLM, Ollama, etc.).
    """

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    SELF_HOSTED = "self_hosted"


# Default model per provider. The backend auto-assigns this when the
# user creates a connection without specifying a model (standard flow).
DEFAULT_MODELS: Final[dict[str, str]] = {
    LLMProvider.ANTHROPIC: "claude-sonnet-4-6",
    LLMProvider.OPENAI: "gpt-5.5",
    LLMProvider.GEMINI: "gemini-3.5-flash",
    LLMProvider.SELF_HOSTED: "default",
}


class ModelMetadata(TypedDict):
    """Metadata for a specific LLM model."""

    id: str
    display_name: str
    provider: str
    context_window: int
    group: str  # reasoning, balanced, efficient
    is_premium: bool


# Complete catalogue of supported models with enterprise-grade metadata.
# Used to populate the model-first selection UX.
MODEL_CATALOG: Final[list[ModelMetadata]] = [
    # --- ANTHROPIC ---
    {
        "id": "claude-opus-4-7",
        "display_name": "Claude Opus 4.7",
        "provider": LLMProvider.ANTHROPIC,
        "context_window": 1000000,
        "group": "thinking",
        "is_premium": True,
    },
    {
        "id": "claude-sonnet-4-6",
        "display_name": "Claude Sonnet 4.6",
        "provider": LLMProvider.ANTHROPIC,
        "context_window": 1000000,
        "group": "balanced",
        "is_premium": True,
    },
    {
        "id": "claude-opus-4-6",
        "display_name": "Claude Opus 4.6",
        "provider": LLMProvider.ANTHROPIC,
        "context_window": 1000000,
        "group": "thinking",
        "is_premium": True,
    },
    {
        "id": "claude-haiku-4-5-20251001",
        "display_name": "Claude Haiku 4.5",
        "provider": LLMProvider.ANTHROPIC,
        "context_window": 200000,
        "group": "efficient",
        "is_premium": False,
    },
    # --- OPENAI ---
    {
        "id": "gpt-5.5-pro",
        "display_name": "GPT-5.5 Pro",
        "provider": LLMProvider.OPENAI,
        "context_window": 1000000,
        "group": "thinking",
        "is_premium": True,
    },
    {
        "id": "gpt-5.5",
        "display_name": "GPT-5.5",
        "provider": LLMProvider.OPENAI,
        "context_window": 1000000,
        "group": "balanced",
        "is_premium": True,
    },
    {
        "id": "o4-mini",
        "display_name": "o4-mini",
        "provider": LLMProvider.OPENAI,
        "context_window": 200000,
        "group": "efficient",
        "is_premium": False,
    },
    {
        "id": "gpt-5.4-pro",
        "display_name": "GPT-5.4 Pro",
        "provider": LLMProvider.OPENAI,
        "context_window": 1000000,
        "group": "thinking",
        "is_premium": True,
    },
    {
        "id": "gpt-4o",
        "display_name": "GPT-4o",
        "provider": LLMProvider.OPENAI,
        "context_window": 128000,
        "group": "legacy",
        "is_premium": False,
    },
    # --- GEMINI ---
    {
        "id": "gemini-3.1-pro-preview",
        "display_name": "Gemini 3.1 Pro",
        "provider": LLMProvider.GEMINI,
        "context_window": 1048576,
        "group": "pro",
        "is_premium": True,
    },
    {
        "id": "gemini-3.5-flash",
        "display_name": "Gemini 3.5 Flash",
        "provider": LLMProvider.GEMINI,
        "context_window": 1048576,
        "group": "flash",
        "is_premium": False,
    },
    {
        "id": "gemini-2.5-pro",
        "display_name": "Gemini 2.5 Pro",
        "provider": LLMProvider.GEMINI,
        "context_window": 1048576,
        "group": "pro",
        "is_premium": True,
    },
    {
        "id": "gemini-2.5-flash",
        "display_name": "Gemini 2.5 Flash",
        "provider": LLMProvider.GEMINI,
        "context_window": 1048576,
        "group": "flash",
        "is_premium": False,
    },
]

# Legacy mapping for backwards compatibility during migration.
# Components should migrate to using MODEL_CATALOG directly.
AVAILABLE_MODELS: Final[dict[str, list[str]]] = {
    LLMProvider.ANTHROPIC: [
        m["id"] for m in MODEL_CATALOG if m["provider"] == LLMProvider.ANTHROPIC
    ],
    LLMProvider.OPENAI: [
        m["id"] for m in MODEL_CATALOG if m["provider"] == LLMProvider.OPENAI
    ],
    LLMProvider.GEMINI: [
        m["id"] for m in MODEL_CATALOG if m["provider"] == LLMProvider.GEMINI
    ],
}

# System default provider
DEFAULT_PROVIDER: Final[str] = LLMProvider.ANTHROPIC
DEFAULT_MODEL: Final[str] = DEFAULT_MODELS[LLMProvider.ANTHROPIC]


@unique
class SetupGrade(StrEnum):
    """Trade setup quality grade as defined in Rulebook Section 6.2."""

    A_PLUS = "A+"
    A = "A"
    B = "B"
    REJECT = "REJECT"


@unique
class TradeDirection(StrEnum):
    """Trade direction output."""

    LONG = "LONG"
    SHORT = "SHORT"
    NO_SETUP = "NO SETUP"


@unique
class Confidence(StrEnum):
    """Processor confidence level."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NO_SETUP = "NO SETUP"


@unique
class TradingStyle(StrEnum):
    """Active trading style from Rulebook Section 2.4."""

    SCALPING = "SCALPING"
    INTRADAY = "INTRADAY"
    SWING = "SWING"
    POSITIONAL = "POSITIONAL"


@unique
class ProcessorStatus(StrEnum):
    """Status of a processor invocation."""

    SUCCESS = "success"
    NO_SETUP = "no_setup"
    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    LLM_ERROR = "llm_error"
    TIMEOUT = "timeout"
    INSUFFICIENT_DATA = "insufficient_data"


# Confluence scoring bounds (Rulebook Section 6.1)
CONFLUENCE_SCORE_MIN: Final[float] = 0.0
CONFLUENCE_SCORE_MAX: Final[float] = 10.0
CONFLUENCE_REJECT_THRESHOLD: Final[float] = 5.0
CONFLUENCE_B_GRADE_THRESHOLD: Final[float] = 5.0
CONFLUENCE_A_GRADE_THRESHOLD: Final[float] = 7.0
CONFLUENCE_A_PLUS_THRESHOLD: Final[float] = 9.0

# Risk allocation by grade (Rulebook Section 6.2)
RISK_PERCENT_A_PLUS: Final[float] = 1.0
RISK_PERCENT_A: Final[float] = 1.0
RISK_PERCENT_B: Final[float] = 0.5

# Minimum R:R by style (Rulebook Section 7.3).
# Re-exported from engine.shared.risk so there is a single canonical
# definition shared with the TA layer; importers of
# engine.processor.constants.MIN_RR_* are unaffected.
from engine.shared.risk import (  # noqa: E402
    MIN_RR_INTRADAY,
    MIN_RR_POSITIONAL,
    MIN_RR_SCALPING,
    MIN_RR_SWING,
)

# LLM response constraints
MAX_LLM_RESPONSE_LENGTH: Final[int] = 65536
MAX_REASONING_LENGTH: Final[int] = 8192
MAX_EVIDENCE_ITEMS: Final[int] = 50
MAX_CITATIONS: Final[int] = 30
MAX_TAKE_PROFIT_LEVELS: Final[int] = 3

# Processor identification for metrics labels
PROCESSOR_NAME: Final[str] = "analysis_processor"
