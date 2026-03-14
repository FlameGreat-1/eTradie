"""Processor enums and constants.

All processor-specific enumerations and fixed values.
Every other processor module imports from this file.
"""

from __future__ import annotations

from enum import StrEnum, unique
from typing import Final


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


# Default model per provider. Users can override with ANY model string.
DEFAULT_MODELS: Final[dict[str, str]] = {
    LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
    LLMProvider.OPENAI: "gpt-4o",
    LLMProvider.GEMINI: "gemini-2.5-pro",
    LLMProvider.SELF_HOSTED: "default",
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

# Minimum R:R by style (Rulebook Section 7.3)
MIN_RR_SCALPING: Final[float] = 2.0
MIN_RR_INTRADAY: Final[float] = 3.0
MIN_RR_SWING: Final[float] = 3.0
MIN_RR_POSITIONAL: Final[float] = 5.0

# LLM response constraints
MAX_LLM_RESPONSE_LENGTH: Final[int] = 65536
MAX_REASONING_LENGTH: Final[int] = 8192
MAX_EVIDENCE_ITEMS: Final[int] = 50
MAX_CITATIONS: Final[int] = 30
MAX_TAKE_PROFIT_LEVELS: Final[int] = 3

# Processor identification for metrics labels
PROCESSOR_NAME: Final[str] = "analysis_processor"
