from __future__ import annotations


from datetime import datetime

from pydantic import Field

from engine.shared.models.base import TimestampedModel
from engine.shared.models.events import RiskEnvironment


class RiskEnvironmentAssessment(TimestampedModel):
    environment: RiskEnvironment = RiskEnvironment.NEUTRAL
    vix_level: float | None = None
    yield_curve_inverted: bool = False
    safe_haven_demand_elevated: bool = False
    commodity_currencies_weak: bool = False
    stagflation_detected: bool = False
    assessed_at: datetime = Field(
        default_factory=lambda: __import__("datetime").datetime.now(__import__("datetime").UTC),
    )


def assess_risk_environment(
    *,
    vix: float | None = None,
    us2y_yield: float | None = None,
    us10y_yield: float | None = None,
    gold_price_change_pct: float | None = None,
    jpy_strength: bool = False,
    chf_strength: bool = False,
    aud_weakness: bool = False,
    nzd_weakness: bool = False,
    cpi_above_target: bool = False,
    gdp_negative: bool = False,
) -> RiskEnvironmentAssessment:
    risk_off_signals = 0
    risk_on_signals = 0

    yield_inverted = False
    if us2y_yield is not None and us10y_yield is not None:
        yield_inverted = us2y_yield > us10y_yield
        if yield_inverted:
            risk_off_signals += 1

    if vix is not None:
        if vix > 30:
            risk_off_signals += 2
        elif vix > 20:
            risk_off_signals += 1
        elif vix < 15:
            risk_on_signals += 1

    safe_haven_elevated = False
    if jpy_strength or chf_strength:
        risk_off_signals += 1
        safe_haven_elevated = True

    if gold_price_change_pct is not None and gold_price_change_pct > 1.0:
        risk_off_signals += 1
        safe_haven_elevated = True

    commodity_weak = False
    if aud_weakness and nzd_weakness:
        risk_off_signals += 1
        commodity_weak = True
    elif not aud_weakness and not nzd_weakness:
        risk_on_signals += 1

    stagflation = cpi_above_target and gdp_negative

    if stagflation:
        env = RiskEnvironment.STAGFLATION
    elif risk_off_signals >= 3:
        env = RiskEnvironment.RISK_OFF
    elif risk_on_signals >= 2 and risk_off_signals == 0:
        env = RiskEnvironment.RISK_ON
    else:
        env = RiskEnvironment.NEUTRAL

    return RiskEnvironmentAssessment(
        environment=env,
        vix_level=vix,
        yield_curve_inverted=yield_inverted,
        safe_haven_demand_elevated=safe_haven_elevated,
        commodity_currencies_weak=commodity_weak,
        stagflation_detected=stagflation,
    )
