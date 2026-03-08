from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from engine.ta.constants import Timeframe


class TAConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    enabled: bool = Field(default=True)
    
    smc_enabled: bool = Field(default=True)
    snd_enabled: bool = Field(default=True)
    
    primary_broker: str = Field(default="mt5")
    fallback_broker: str = Field(default="twelve_data")
    
    default_symbols: list[str] = Field(
        default_factory=lambda: [
            "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
            "AUDUSD", "NZDUSD", "USDCAD", "XAUUSD"
        ]
    )
    
    htf_timeframes: list[Timeframe] = Field(
        default_factory=lambda: [Timeframe.D1, Timeframe.H4, Timeframe.H1]
    )
    
    ltf_timeframes: list[Timeframe] = Field(
        default_factory=lambda: [Timeframe.M30, Timeframe.M15, Timeframe.M5, Timeframe.M1]
    )
    
    candle_lookback_periods: int = Field(default=500, ge=100, le=5000)
    
    snapshot_cache_ttl_seconds: int = Field(default=300, ge=60, le=3600)
    
    candidate_cache_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    
    analysis_interval_seconds: int = Field(default=60, ge=30, le=300)
    
    backfill_on_startup: bool = Field(default=True)
    
    max_concurrent_symbol_analysis: int = Field(default=4, ge=1, le=10)
    
    @field_validator("primary_broker", "fallback_broker")
    @classmethod
    def validate_broker(cls, v: str) -> str:
        allowed = {"mt5", "twelve_data", "tradingview"}
        if v not in allowed:
            raise ValueError(f"Broker must be one of {allowed}")
        return v
    
    @field_validator("default_symbols")
    @classmethod
    def validate_symbols(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one symbol must be configured")
        return [s.upper() for s in v]
