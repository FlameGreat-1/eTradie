from pydantic import Field
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

    # --- Confluence scoring (informational, NOT a gate) ---
    # The confluence count is stored as metadata on every candidate so
    # the LLM can see how many structural factors are present.  It is
    # NEVER used to reject a candidate.  The LLM performs its own
    # confluence scoring with full macro/Wyckoff/cross-TF context that
    # no Python counter can replicate.
    min_confluences: int = Field(default=3, ge=0, le=10)

    enable_turtle_soup: bool = Field(default=True)

    enable_sh_bms_rto: bool = Field(default=True)

    enable_sms_bms_rto: bool = Field(default=True)

    enable_amd: bool = Field(default=True)

    enable_combined_patterns: bool = Field(default=True)

    # --- CHoCH reversal candidates ---
    # When True, the detector builds reversal candidates from HTF CHoCH
    # events (e.g. D1 bullish CHoCH after a W1 bearish trend).  CHoCH
    # is the earliest signal of a trend reversal and is a valid
    # structural origin for candidate building.
    enable_choch_reversal: bool = Field(default=True)

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
    #
    # The mitigation rule is enforced directly in
    # ZoneValidator.validate_zone_freshness as a close-beyond-extreme
    # test per SMC-MS-004 / SMC-OB-004 / SMC-MIT-001 / SMC-INV-005.
    # There is no body-percentage knob here: the authoritative SMC
    # framework defines mitigation in binary close-beyond terms, and
    # introducing a tunable body threshold would silently change the
    # gate on live capital.  If the rule ever needs to change, it is
    # a framework-level decision, not a config toggle.

    # --- Inducement (IDM) clearance settings ---
    # Per SMC-LIQ-004 and SMC-MS-003/004: an inducement is only
    # "cleared/swept" when price genuinely takes it out with a wick
    # that penetrates beyond the internal swing level.  A trivial
    # retest or equal-touch does NOT clear the inducement.
    #
    # This value is the minimum wick penetration (in pips) past the
    # internal swing price before the IDM is flagged as cleared.
    # It is scaled per-symbol via get_pip_value() at detection time,
    # so the same value works correctly for FX, metals, indices, and
    # crypto instruments.
    #
    # 0.0 = any touch counts (legacy, not recommended).
    # 1.0 = default; requires a real wick past the level.
    inducement_min_break_pips: float = Field(
        default=1.0, ge=0.0, le=50.0,
    )
