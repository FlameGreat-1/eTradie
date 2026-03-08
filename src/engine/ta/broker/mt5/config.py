from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MT5Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MT5_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    enabled: bool = Field(default=True)
    
    terminal_path: Optional[str] = Field(default=None)
    
    account: int = Field(default=0, ge=0)
    
    password: str = Field(default="")
    
    server: str = Field(default="")
    
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    
    max_retries: int = Field(default=3, ge=1, le=10)
    
    retry_delay_seconds: int = Field(default=2, ge=1, le=30)
    
    connection_timeout_seconds: int = Field(default=30, ge=5, le=120)
    
    max_candles_per_request: int = Field(default=5000, ge=100, le=50000)
    
    enable_tick_data: bool = Field(default=False)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v:
            raise ValueError("MT5 password cannot be empty")
        return v
    
    @field_validator("server")
    @classmethod
    def validate_server(cls, v: str) -> str:
        if not v:
            raise ValueError("MT5 server cannot be empty")
        return v
