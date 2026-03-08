from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingViewConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TRADINGVIEW_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    enabled: bool = Field(default=False)
    
    webhook_secret: str = Field(default="")
    
    webhook_path: str = Field(default="/webhooks/tradingview")
    
    max_payload_size_bytes: int = Field(default=10240, ge=1024, le=102400)
    
    signature_header: str = Field(default="X-TradingView-Signature")
    
    timeout_seconds: int = Field(default=10, ge=5, le=60)
    
    allowed_ips: list[str] = Field(default_factory=list)
    
    validate_signature: bool = Field(default=True)
    
    @field_validator("webhook_secret")
    @classmethod
    def validate_webhook_secret(cls, v: str, info) -> str:
        if info.data.get("enabled") and info.data.get("validate_signature") and not v:
            raise ValueError("Webhook secret cannot be empty when signature validation is enabled")
        return v
    
    @field_validator("webhook_path")
    @classmethod
    def validate_webhook_path(cls, v: str) -> str:
        if not v.startswith("/"):
            return f"/{v}"
        return v
    
    @field_validator("allowed_ips")
    @classmethod
    def validate_allowed_ips(cls, v: list[str]) -> list[str]:
        import ipaddress
        
        validated = []
        for ip in v:
            try:
                ipaddress.ip_address(ip)
                validated.append(ip)
            except ValueError:
                try:
                    ipaddress.ip_network(ip)
                    validated.append(ip)
                except ValueError:
                    raise ValueError(f"Invalid IP address or network: {ip}")
        
        return validated
