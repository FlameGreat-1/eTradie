from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SMCConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SMC_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    enabled: bool = Field(default=True)
    
    min_displacement_pips: float = Field(default=20.0, ge=10.0, le=100.0)
    
    min_sweep_pips: float = Field(default=5.0, ge=2.0, le=20.0)
    
    turtle_soup_min_pips: float = Field(default=5.0, ge=2.0, le=20.0)
    
    turtle_soup_min_sl_pips: float = Field(default=10.0, ge=5.0, le=30.0)
    
    ob_body_percentage_threshold: float = Field(default=50.0, ge=30.0, le=80.0)
    
    fvg_min_gap_pips: float = Field(default=2.0, ge=1.0, le=10.0)
    
    require_fvg_with_ob: bool = Field(default=True)
    
    require_premium_discount: bool = Field(default=True)
    
    require_session_timing: bool = Field(default=True)
    
    require_htf_bms_alignment: bool = Field(default=True)
    
    min_confluences: int = Field(default=3, ge=2, le=10)
    
    enable_turtle_soup: bool = Field(default=True)
    
    enable_sh_bms_rto: bool = Field(default=True)
    
    enable_sms_bms_rto: bool = Field(default=True)
    
    enable_amd: bool = Field(default=True)
    
    enable_combined_patterns: bool = Field(default=True)
    
    @field_validator("min_confluences")
    @classmethod
    def validate_min_confluences(cls, v: int) -> int:
        if v < 3:
            raise ValueError("SMC requires minimum 3 confluences (Universal Rule 5)")
        return v
