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

    # BMS multi-candle confirmation thresholds (base values for H1).
    # Internally scaled per-timeframe by the BMS detector.
    bms_strong_displacement_pips: float = Field(default=50.0, ge=20.0, le=200.0)
    bms_moderate_displacement_pips: float = Field(default=30.0, ge=15.0, le=100.0)
    bms_weak_confirm_candles: int = Field(default=5, ge=3, le=10)

    min_sweep_pips: float = Field(default=5.0, ge=2.0, le=20.0)

    turtle_soup_min_pips: float = Field(default=5.0, ge=2.0, le=20.0)

    turtle_soup_min_sl_pips: float = Field(default=10.0, ge=5.0, le=30.0)

    ob_sl_buffer_pips: float = Field(default=2.0, ge=1.0, le=10.0)

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

    # --- Fibonacci / OTE confluence settings ---
    # OTE alignment is a confluence booster, not a hard gate.
    # When an OB sits inside the OTE pocket (61.8%-78.6%) it gets the
    # maximum Fib confluence score.  OBs at broader premium/discount
    # (above/below equilibrium) still receive partial credit.  OBs at
    # equilibrium receive zero Fib confluence but are NOT rejected.
    fibonacci_tolerance_pips: float = Field(default=5.0, ge=1.0, le=20.0)

    # --- FVG association settings ---
    # Maximum number of candles between the OB candle and an associated
    # FVG.  Replaces the old 1-hour clock-time check with a structural
    # proximity measure that works across all timeframes.
    fvg_max_candle_distance: int = Field(default=5, ge=1, le=20)

    # --- Sweep association settings ---
    # Maximum candle-index distance for sweep-to-BMS association.
    sweep_max_candle_distance: int = Field(default=10, ge=3, le=30)

    # --- Zone freshness / mitigation settings ---
    # Minimum percentage of the candle body that must close through the
    # OB zone for it to count as true mitigation.  A wick into the zone
    # (RTO) is the entry opportunity, not invalidation.
    # 0.0 = any body overlap counts as mitigation (old behaviour).
    # 50.0 = at least 50% of the body must be inside the zone.
    zone_mitigation_body_threshold: float = Field(
        default=50.0, ge=0.0, le=100.0,
    )

    @field_validator("min_confluences")
    @classmethod
    def validate_min_confluences(cls, v: int) -> int:
        if v < 3:
            raise ValueError("SMC requires minimum 3 confluences (Universal Rule 5)")
        return v
