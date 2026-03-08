from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TwelveDataConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TWELVE_DATA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    enabled: bool = Field(default=True)
    
    api_key: str = Field(default="")
    
    base_url: str = Field(default="https://api.twelvedata.com")
    
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    
    max_retries: int = Field(default=3, ge=1, le=10)
    
    retry_delay_seconds: int = Field(default=2, ge=1, le=30)
    
    rate_limit_per_minute: int = Field(default=8, ge=1, le=800)
    
    max_candles_per_request: int = Field(default=5000, ge=100, le=5000)
    
    cache_ttl_seconds: int = Field(default=300, ge=60, le=3600)
    
    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Twelve Data API key cannot be empty")
        return v
    
    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        if not v.startswith("http"):
            raise ValueError("Base URL must start with http or https")
        return v.rstrip("/")
