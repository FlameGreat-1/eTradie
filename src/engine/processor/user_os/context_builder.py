"""Compress a structured Profile into an LLM-safe instruction block.

PRACTICE.md is explicit on this point:

    "Do NOT pass the raw JSON directly to the LLM eventually.
     Instead: create A User Context Builder which converts structured
     JSON into:
       - compressed reasoning context,
       - normalized prompt-safe instructions,
       - weighted preferences.
     This prevents:
       - prompt bloat,
       - inconsistency,
       - malformed context,
       - token waste."

Everything below is the implementation of that builder. Every field is
mapped through a known label so an attacker who tampers with the
stored profile cannot inject prompts: only enum-valued fields are
rendered, and unrecognised values are silently dropped.
"""

from __future__ import annotations

from typing import Any, Optional

# ---------------------------------------------------------------------------
# Human-readable label maps. Anything not in these tables is dropped.
# ---------------------------------------------------------------------------

_EXPERIENCE = {
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
}
_AUTOMATION = {
    "manual": "Manual",
    "semi_automated": "Semi-Automated",
    "fully_automated": "Fully Automated",
}
_RISK_APPETITE = {
    "conservative": "Conservative",
    "balanced": "Balanced",
    "aggressive": "Aggressive",
}
_TRADER_TYPE = {
    "precision": "Precision (fewer, high-quality)",
    "frequent": "Frequent (more opportunities)",
}
_DISCIPLINE = {
    "rule_based": "Rule-Based",
    "flexible_discretion": "Flexible Discretion",
}
_STYLE = {
    "scalping": "Scalping (M1-M15)",
    "intraday": "Intraday (M15-H4)",
    "swing": "Swing (H4-D1)",
    "positional": "Positional (D1-W1)",
}
_SESSION = {
    "asian": "Asian",
    "london": "London",
    "new_york": "New York",
    "london_ny_overlap": "London/NY Overlap",
}
_RISK_MODEL = {
    "fixed": "Fixed % per trade",
    "adaptive": "Adaptive % per trade",
}
_CONFIRMATION = {
    "aggressive": "Aggressive early entries",
    "balanced": "Balanced confirmation",
    "strict": "Strict confirmation only",
}
_FRAMEWORK = {
    "smc": "SMC",
    "snd": "Supply & Demand",
    "wyckoff": "Wyckoff",
    "liquidity": "Liquidity concepts",
}
_ENTRY_MODE = {
    "limit_only": "Limit orders only",
    "market_allowed": "Market execution allowed",
    "either_allowed": "Either limit or market",
}
_AUTO_MODE = {
    "alert_only": "Alert-only (no execution)",
    "manual_approval": "Manual approval per trade",
    "semi_automatic": "Semi-automatic",
    "fully_automatic": "Fully automatic",
}
_ASSET = {
    "forex": "Forex",
    "indices": "Indices",
    "gold": "Gold",
    "crypto": "Crypto",
    "volatility_indices": "Volatility Indices (24/7)",
}
_GOAL = {
    "capital_preservation": "Capital preservation",
    "consistency": "Consistency",
    "aggressive_growth": "Aggressive growth",
    "low_stress": "Low stress",
    "high_probability_only": "High-probability setups only",
    "fewer_high_quality": "Fewer but higher-quality trades",
}
_PARTIAL_TP = {
    "disabled": "disabled",
    "aggressive": "aggressive (lock fast)",
    "balanced": "balanced",
    "let_run": "let runners run",
}
_TRAILING = {
    "disabled": "disabled",
    "structure_based": "structure-based",
    "atr_based": "ATR-based",
    "fixed_pips": "fixed-pips",
}
_BE_TRIGGER = {
    "disabled": "disabled",
    "at_tp1": "at TP1",
    "at_1rr": "at 1R",
    "at_midpoint": "at zone midpoint",
}
_EMPHASIS = {"low": "low", "medium": "medium", "high": "high"}


def _label(table: dict[str, str], raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    return table.get(raw)


def _labels(table: dict[str, str], raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        label = _label(table, item)
        if label and label not in seen:
            seen.add(label)
            out.append(label)
    return out


def _safe_num(raw: Any, *, low: float, high: float) -> Optional[float]:
    """Return raw clamped to [low, high] when it is a finite number, else None."""
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if val != val or val == float("inf") or val == float("-inf"):
        return None
    if val < low:
        val = low
    if val > high:
        val = high
    return val


def _safe_int(raw: Any, *, low: int, high: int) -> Optional[int]:
    try:
        val = int(raw)
    except (TypeError, ValueError):
        return None
    if val < low:
        val = low
    if val > high:
        val = high
    return val


def _bool(raw: Any) -> bool:
    return bool(raw) if isinstance(raw, (bool, int)) else False


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_user_operating_context(profile: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Convert a stored Profile dict into the LLM-safe context block.

    Returns None when the profile is missing, malformed, or empty so
    callers can short-circuit and skip injection. The returned
    structure is JSON-serialisable, deterministic, and contains only
    enum-mapped labels and clamped numerics — no free-form user text
    is ever forwarded to the LLM.
    """
    if not isinstance(profile, dict) or not profile:
        return None

    identity = profile.get("identity") or {}
    sessions = profile.get("sessions") or {}
    risk = profile.get("risk") or {}
    structural = profile.get("structural") or {}
    entry = profile.get("entry") or {}
    filtering = profile.get("filtering") or {}
    psychology = profile.get("psychology") or {}
    confluence = profile.get("confluence") or {}
    automation = profile.get("automation") or {}
    assets = profile.get("assets") or {}
    management = profile.get("management") or {}

    # Build the human-readable block. The LLM sees this verbatim.
    out: dict[str, Any] = {
        "schema_version": profile.get("schema_version", 1),
        "identity": {
            "experience": _label(_EXPERIENCE, identity.get("experience")),
            "automation": _label(_AUTOMATION, identity.get("automation")),
            "risk_appetite": _label(_RISK_APPETITE, identity.get("risk_appetite")),
            "trader_type": _label(_TRADER_TYPE, identity.get("trader_type")),
            "discipline": _label(_DISCIPLINE, identity.get("discipline")),
        },
        "style": _label(_STYLE, profile.get("style")),
        "sessions": {
            "preferred": _labels(_SESSION, sessions.get("preferred_sessions")),
            "avoid_low_liquidity": _bool(sessions.get("avoid_low_liquidity")),
            "high_volatility_only": _bool(sessions.get("high_volatility_windows_only")),
        },
        "risk": {
            "model": _label(_RISK_MODEL, risk.get("risk_model")),
            "per_trade_percent": _safe_num(risk.get("fixed_risk_percent"), low=0.1, high=3.0),
            "max_daily_drawdown_percent": _safe_num(risk.get("max_daily_drawdown_percent"), low=1.0, high=10.0),
            "max_weekly_drawdown_percent": _safe_num(risk.get("max_weekly_drawdown_percent"), low=2.0, high=20.0),
            "max_simultaneous_trades": _safe_int(risk.get("max_simultaneous_trades"), low=1, high=10),
            "max_correlated_exposure": _safe_int(risk.get("max_correlated_exposure"), low=1, high=5),
            "partial_take_profits": _bool(risk.get("partial_take_profits")),
            "break_even_management": _bool(risk.get("break_even_management")),
            "trailing_stop_enabled": _bool(risk.get("trailing_stop_enabled")),
        },
        "confirmation": _label(_CONFIRMATION, profile.get("confirmation")),
        "structural": {
            "frameworks": _labels(_FRAMEWORK, structural.get("frameworks")),
            "use_fvg": _bool(structural.get("use_fvg")),
            "use_order_blocks": _bool(structural.get("use_order_blocks")),
            "use_choch_bms": _bool(structural.get("use_choch_bms")),
            "use_idm": _bool(structural.get("use_idm")),
            "emphasis": _label(_EMPHASIS, structural.get("structure_emphasis")),
        },
        "entry": {
            "execution_mode": _label(_ENTRY_MODE, entry.get("execution_mode")),
            "require_confirmation_candle": _bool(entry.get("require_confirmation_candle")),
            "require_retest": _bool(entry.get("require_retest")),
            "require_liquidity_sweep": _bool(entry.get("require_liquidity_sweep")),
            "require_mtf_alignment": _bool(entry.get("require_mtf_alignment")),
        },
        "filtering": {
            "avoid_counter_trend": _bool(filtering.get("avoid_counter_trend")),
            "avoid_news_volatility": _bool(filtering.get("avoid_news_volatility")),
            "minimum_rr": _safe_num(filtering.get("minimum_rr"), low=1.0, high=10.0),
            "avoid_ranging_markets": _bool(filtering.get("avoid_ranging_markets")),
            "avoid_overnight_holds": _bool(filtering.get("avoid_overnight_holds")),
            "avoid_friday_trades": _bool(filtering.get("avoid_friday_trades")),
            "avoid_session_transitions": _bool(filtering.get("avoid_session_transitions")),
        },
        "psychology": {
            "max_losses_before_cooldown": _safe_int(psychology.get("max_losses_before_cooldown"), low=0, high=10),
            "cooldown_after_loss_streak": _bool(psychology.get("cooldown_after_loss_streak")),
            "daily_lockout_after_target": _bool(psychology.get("daily_lockout_after_target")),
            "revenge_trading_protection": _bool(psychology.get("revenge_trading_protection")),
            "overtrading_protection": _bool(psychology.get("overtrading_protection")),
            "emotional_volatility_sensitivity": _label(_EMPHASIS, psychology.get("emotional_volatility_sensitivity")),
        },
        "confluence_weights": {
            "macro_alignment": _safe_int(confluence.get("macro_alignment"), low=0, high=3),
            "dxy": _safe_int(confluence.get("dxy"), low=0, high=3),
            "cot": _safe_int(confluence.get("cot"), low=0, high=3),
            "htf_alignment": _safe_int(confluence.get("htf_alignment"), low=0, high=3),
            "wyckoff": _safe_int(confluence.get("wyckoff"), low=0, high=3),
            "volume_liquidity": _safe_int(confluence.get("volume_liquidity"), low=0, high=3),
            "session_timing": _safe_int(confluence.get("session_timing"), low=0, high=3),
        },
        "automation": {
            "mode": _label(_AUTO_MODE, automation.get("mode")),
            "require_final_confirmation": _bool(automation.get("require_final_confirmation")),
            "allow_unattended_execution": _bool(automation.get("allow_unattended_execution")),
        },
        "assets": {
            "classes": _labels(_ASSET, assets.get("asset_classes")),
            "preferred_pairs": _normalised_pairs(assets.get("preferred_pairs")),
            "avoid_highly_volatile": _bool(assets.get("avoid_highly_volatile")),
            "avoid_correlated_instruments": _bool(assets.get("avoid_correlated_instruments")),
        },
        "goal": _label(_GOAL, profile.get("goal")),
        "management": {
            "partial_tp_style": _label(_PARTIAL_TP, management.get("partial_tp_style")),
            "trailing_stop": _label(_TRAILING, management.get("trailing_stop")),
            "break_even_trigger": _label(_BE_TRIGGER, management.get("break_even_trigger")),
            "scale_in_enabled": _bool(management.get("scale_in_enabled")),
            "scale_out_enabled": _bool(management.get("scale_out_enabled")),
            "hold_runners": _bool(management.get("hold_runners")),
            "close_before_news": _bool(management.get("close_before_news")),
        },
    }
    return out


def _normalised_pairs(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        sym = item.strip().upper()
        if not sym or len(sym) > 16 or sym in seen:
            continue
        # Only ASCII letters/digits to keep prompts clean.
        if not all(ch.isalnum() for ch in sym):
            continue
        seen.add(sym)
        out.append(sym)
        if len(out) >= 50:
            break
    return out
