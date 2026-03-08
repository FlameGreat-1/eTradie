from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SnDConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SND_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    enabled: bool = Field(default=True)
    
    marubozu_body_percentage_threshold: float = Field(default=80.0, ge=70.0, le=95.0)
    
    marubozu_max_wick_percentage: float = Field(default=10.0, ge=5.0, le=20.0)
    
    min_previous_touches: int = Field(default=2, ge=2, le=10)
    
    previous_level_tolerance_pips: float = Field(default=3.0, ge=1.0, le=10.0)
    
    min_fakeout_tests: int = Field(default=1, ge=1, le=10)
    
    compression_min_candles: int = Field(default=3, ge=2, le=10)
    
    compression_max_range_pips: float = Field(default=15.0, ge=5.0, le=30.0)
    
    require_premium_discount: bool = Field(default=True)
    
    require_fibonacci_confluence: bool = Field(default=False)
    
    fibonacci_tolerance_pips: float = Field(default=5.0, ge=2.0, le=15.0)
    
    enable_qml_baseline: bool = Field(default=True)
    
    enable_qml_mpl: bool = Field(default=True)
    
    enable_qml_previous_levels_type1: bool = Field(default=True)
    
    enable_qml_previous_levels_type2: bool = Field(default=True)
    
    enable_triple_fakeout: bool = Field(default=True)
    
    enable_fakeout_king: bool = Field(default=True)
    
    enable_sop: bool = Field(default=True)
    
    @field_validator("min_previous_touches")
    @classmethod
    def validate_min_previous_touches(cls, v: int) -> int:
        if v < 2:
            raise ValueError("SnD requires minimum 2 previous touches (Universal Rule 2)")
        return v
    
    @field_validator("marubozu_body_percentage_threshold")
    @classmethod
    def validate_marubozu_threshold(cls, v: float) -> float:
        if v < 80.0:
            raise ValueError("Marubozu body percentage must be at least 80% (Universal Rule 1)")
        return v
