from __future__ import annotations

from enum import IntEnum, StrEnum, unique


@unique
class EventImpact(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@unique
class EventType(StrEnum):
    RATE_DECISION = "RATE_DECISION"
    CPI = "CPI"
    PPI = "PPI"
    NFP = "NFP"
    GDP = "GDP"
    PMI = "PMI"
    RETAIL_SALES = "RETAIL_SALES"
    EMPLOYMENT = "EMPLOYMENT"
    TRADE_BALANCE = "TRADE_BALANCE"
    CONSUMER_CONFIDENCE = "CONSUMER_CONFIDENCE"
    HOUSING = "HOUSING"
    MANUFACTURING = "MANUFACTURING"
    CB_SPEECH = "CB_SPEECH"
    MEETING_MINUTES = "MEETING_MINUTES"
    FORWARD_GUIDANCE = "FORWARD_GUIDANCE"
    GEOPOLITICAL = "GEOPOLITICAL"
    OTHER = "OTHER"


@unique
class MacroBias(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@unique
class DataPriority(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@unique
class TradingSession(StrEnum):
    LONDON_OPEN = "LONDON_OPEN"
    LONDON_NY_OVERLAP = "LONDON_NY_OVERLAP"
    NEW_YORK = "NEW_YORK"
    ASIAN = "ASIAN"


@unique
class CentralBank(StrEnum):
    FED = "FED"
    ECB = "ECB"
    BOE = "BOE"
    BOJ = "BOJ"


@unique
class CBTone(StrEnum):
    HAWKISH = "HAWKISH"
    DOVISH = "DOVISH"
    NEUTRAL = "NEUTRAL"


@unique
class SurpriseDirection(StrEnum):
    BEAT = "BEAT"
    MISS = "MISS"
    INLINE = "INLINE"


@unique
class RiskSentiment(StrEnum):
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    NEUTRAL = "NEUTRAL"


@unique
class TrendDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    SIDEWAYS = "SIDEWAYS"


@unique
class ProviderCategory(StrEnum):
    CENTRAL_BANK = "CENTRAL_BANK"
    COT = "COT"
    ECONOMIC_DATA = "ECONOMIC_DATA"
    NEWS = "NEWS"
    CALENDAR = "CALENDAR"
    MARKET_DATA = "MARKET_DATA"
    SENTIMENT = "SENTIMENT"


@unique
class ProviderStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


NEWS_LOCKOUT_MINUTES: int = 30
SCALP_NEWS_LOCKOUT_MINUTES: int = 45
EVENT_RISK_LOOKAHEAD_HOURS: int = 48
