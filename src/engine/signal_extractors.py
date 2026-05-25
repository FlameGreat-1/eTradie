"""Signal extraction helpers for the dashboard rerun pipeline.

These functions replicate the Go gateway's macro_extractor.go and
ta_extractor.go signal extraction logic in Python. They are used by
the rerun_analysis endpoint which bypasses the Go gateway and needs
to derive the same enriched signals from raw collected data.

The Go gateway path does NOT use these functions. It extracts signals
in Go code and passes them via HTTP to the Python engine.
"""

from __future__ import annotations


def derive_macro_signals(macro: dict) -> dict:
    """Derive enriched macro signal flags from raw macro collection output.

    Replicates the signal extraction logic from the Go gateway's
    macro_extractor.go so the rerun endpoint produces identical
    signals as the normal Go gateway pipeline.
    """
    signals: dict = {
        "has_macro_data": False,
        "has_cot_data": False,
        "has_rate_decision": False,
        "has_high_impact_event": False,
        "has_dxy_data": False,
        "has_qe_qt": False,
        "has_tff_data": False,
        "has_core_inflation": False,
        "has_nfp": False,
        "has_cpi": False,
        "stagflation_detected": False,
        "safe_haven_elevated": False,
        "commodity_currencies_weak": False,
        "risk_environment": "",
        "dxy_momentum": "",
        "cot_extremes": [],
        "fed_tone": "",
        "ecb_tone": "",
        "qe_qt_action": "",
        "qe_qt_bank": "",
        "balance_sheet_direction": "",
    }

    # Central bank signals.
    cb = macro.get("central_bank")
    if cb and isinstance(cb, dict):
        signals["has_macro_data"] = True
        for source_key in ("speeches", "forward_guidance"):
            for item in cb.get(source_key) or []:
                if not isinstance(item, dict):
                    continue
                bank = (item.get("bank") or "").upper()
                tone = (item.get("tone") or "NEUTRAL").upper()
                if bank == "FED" and not signals["fed_tone"]:
                    signals["fed_tone"] = tone
                elif bank == "ECB" and not signals["ecb_tone"]:
                    signals["ecb_tone"] = tone
                policy = (item.get("monetary_policy_action") or "NONE").upper()
                if policy in ("QE", "QT"):
                    signals["has_qe_qt"] = True
                    signals["qe_qt_action"] = policy
                    signals["qe_qt_bank"] = bank
                    signals["balance_sheet_direction"] = (
                        "EXPANDING" if policy == "QE" else "CONTRACTING"
                    )
        for action in cb.get("policy_actions") or []:
            if not isinstance(action, dict):
                continue
            action_type = (action.get("action") or "NONE").upper()
            if action_type in ("QE", "QT"):
                signals["has_qe_qt"] = True
                signals["qe_qt_action"] = action_type
                signals["qe_qt_bank"] = (action.get("bank") or "").upper()
                signals["balance_sheet_direction"] = (
                    "EXPANDING" if action_type == "QE" else "CONTRACTING"
                )
        for decision in cb.get("rate_decisions") or []:
            if not isinstance(decision, dict):
                continue
            bank = (decision.get("bank") or "").upper()
            tone = (decision.get("tone") or "NEUTRAL").upper()
            if bank == "FED":
                signals["fed_tone"] = tone
            elif bank == "ECB":
                signals["ecb_tone"] = tone
            bps = decision.get("rate_change_bps") or decision.get("change") or 0
            try:
                if float(bps) != 0:
                    signals["has_rate_decision"] = True
            except (ValueError, TypeError):
                pass
            policy = (decision.get("monetary_policy_action") or "NONE").upper()
            if policy in ("QE", "QT"):
                signals["has_qe_qt"] = True
                signals["qe_qt_action"] = policy
                signals["qe_qt_bank"] = bank
                signals["balance_sheet_direction"] = (
                    "EXPANDING" if policy == "QE" else "CONTRACTING"
                )

    # COT signals.
    cot = macro.get("cot")
    if cot and isinstance(cot, dict):
        positions = cot.get("latest_positions") or []
        if positions:
            signals["has_cot_data"] = True
        extremes = cot.get("extremes_flagged") or []
        if isinstance(extremes, list):
            signals["cot_extremes"] = [str(e) for e in extremes]
        signals["has_tff_data"] = bool(cot.get("has_tff_data"))

    # Economic signals.
    # has_core_inflation stays False unconditionally: the
    # EconomicRelease model no longer carries inflation_type after the
    # 2026-05 cleanup (no provider populated it). The key is preserved
    # in the signals dict initialisation above so the dashboard rerun
    # endpoint can forward it to the RAG request without a KeyError.
    # The Go gateway path agrees -- it also forwards false for this
    # flag now.

    # Calendar signals.
    cal = macro.get("calendar")
    if cal and isinstance(cal, dict):
        for event in cal.get("events") or []:
            if not isinstance(event, dict):
                continue
            impact = (event.get("impact") or "").upper()
            name_upper = (event.get("event_name") or "").upper()
            if impact == "HIGH":
                signals["has_high_impact_event"] = True
            if "RATE" in name_upper and "DECISION" in name_upper:
                signals["has_rate_decision"] = True
            if (
                "NFP" in name_upper
                or "NON-FARM" in name_upper
                or "NONFARM" in name_upper
            ):
                signals["has_nfp"] = True
            if "CPI" in name_upper or "CONSUMER PRICE INDEX" in name_upper:
                signals["has_cpi"] = True

    # DXY signals.
    dxy = macro.get("dxy")
    if dxy and isinstance(dxy, dict):
        latest = dxy.get("latest") or {}
        if not latest:
            snapshots = dxy.get("snapshots") or []
            if snapshots and isinstance(snapshots, list):
                latest = snapshots[-1] if isinstance(snapshots[-1], dict) else {}
        if latest.get("dxy_value") is not None:
            signals["has_dxy_data"] = True
        momentum = latest.get("dxy_momentum") or latest.get("momentum") or ""
        if momentum:
            signals["dxy_momentum"] = str(momentum).upper()

    # Sentiment / risk environment signals.
    sent = macro.get("sentiment")
    if sent and isinstance(sent, dict):
        signals["has_macro_data"] = True
        risk_env = sent.get("risk_environment") or ""
        if risk_env:
            signals["risk_environment"] = str(risk_env).upper()
        risk_assessment = sent.get("risk_assessment")
        if isinstance(risk_assessment, dict):
            signals["stagflation_detected"] = bool(
                risk_assessment.get("stagflation_detected"),
            )
            signals["safe_haven_elevated"] = bool(
                risk_assessment.get("safe_haven_demand_elevated"),
            )
            signals["commodity_currencies_weak"] = bool(
                risk_assessment.get("commodity_currencies_weak"),
            )

    # Intermarket presence implies macro data.
    inter = macro.get("intermarket")
    if inter and isinstance(inter, dict):
        latest = inter.get("latest") or {}
        if not latest:
            snapshots = inter.get("snapshots") or []
            if snapshots and isinstance(snapshots, list):
                latest = snapshots[-1] if isinstance(snapshots[-1], dict) else {}
        if latest:
            signals["has_macro_data"] = True

    return signals


def derive_ta_signals(ta: dict) -> dict:
    """Derive TA signal flags from raw TA analysis output.

    Replicates the signal extraction logic from the Go gateway's
    ta_extractor.go so the rerun endpoint produces identical
    signals as the normal Go gateway pipeline.
    """
    signals: dict = {
        "direction": "",
        "overall_trend": (ta.get("overall_trend") or "NEUTRAL"),
        "framework": "",
        "setup_families": [],
        "all_frameworks": [],
        "patterns": [],
        "has_smc": False,
        "has_snd": False,
    }

    status = ta.get("status", "")
    if status != "success":
        return signals

    smc = ta.get("smc_candidates") or []
    snd = ta.get("snd_candidates") or []
    signals["has_smc"] = len(smc) > 0
    signals["has_snd"] = len(snd) > 0

    # Determine framework.
    if smc and not snd:
        signals["framework"] = "smc"
    elif snd and not smc:
        signals["framework"] = "snd"
    elif smc and snd:
        signals["framework"] = "smc" if len(smc) >= len(snd) else "snd"

    # Collect all frameworks.
    frameworks: set[str] = set()
    if smc:
        frameworks.add("smc")
    if snd:
        frameworks.add("snd")
    frameworks.add("wyckoff")
    signals["all_frameworks"] = sorted(frameworks)

    # Determine direction from candidates.
    directions: list[str] = []
    for c in smc:
        if isinstance(c, dict) and c.get("direction"):
            directions.append(str(c["direction"]).upper())
    for c in snd:
        if isinstance(c, dict) and c.get("direction"):
            directions.append(str(c["direction"]).upper())
    if directions:
        bullish = sum(1 for d in directions if d == "BULLISH")
        bearish = sum(1 for d in directions if d == "BEARISH")
        if bullish > bearish:
            signals["direction"] = "long"
        elif bearish > bullish:
            signals["direction"] = "short"
        else:
            signals["direction"] = "neutral"

    # Collect patterns.
    patterns: set[str] = set()
    for c in smc:
        if isinstance(c, dict) and c.get("pattern"):
            patterns.add(str(c["pattern"]))
    for c in snd:
        if isinstance(c, dict) and c.get("pattern"):
            patterns.add(str(c["pattern"]))
    signals["patterns"] = sorted(patterns)

    # Collect setup families from SMC candidate fields.
    families: set[str] = set()
    for c in smc:
        if not isinstance(c, dict):
            continue
        if c.get("order_block_upper") or c.get("order_block_lower"):
            families.add("order_block")
        if c.get("fvg_upper") or c.get("fvg_lower"):
            families.add("fair_value_gap")
        if c.get("liquidity_swept"):
            families.add("liquidity_sweep")
        if c.get("inducement_cleared"):
            families.add("inducement")
        # Pattern-based SMC families (matches Go ta_extractor.go exactly).
        pattern = str(c.get("pattern") or "")
        if "TURTLE_SOUP" in pattern:
            families.add("turtle_soup")
        if "AMD" in pattern:
            families.add("amd")
        if "SH_BMS_RTO" in pattern:
            families.add("bms_rto")
        if "SMS_BMS_RTO" in pattern:
            families.add("sms_rto")
        if "CHOCH_BMS_RTO" in pattern:
            families.add("choch_rto")

    # Collect setup families from SnD candidate fields.
    for c in snd:
        if not isinstance(c, dict):
            continue
        if c.get("qml_detected"):
            families.add("qml")
        if c.get("sr_flip_detected"):
            families.add("sr_flip")
        if c.get("rs_flip_detected"):
            families.add("rs_flip")
        if c.get("mpl_detected"):
            families.add("mpl")
        if c.get("fakeout_detected"):
            families.add("fakeout")
        if c.get("compression_detected"):
            families.add("compression")
        if c.get("supply_zone_upper"):
            families.add("supply_zone")
        if c.get("demand_zone_upper"):
            families.add("demand_zone")
        # Pattern-based SnD families (matches Go ta_extractor.go exactly).
        pattern = str(c.get("pattern") or "")
        if "FAKEOUT_KING" in pattern:
            families.add("fakeout_king")
        if "QML_KILLER" in pattern:
            families.add("qml_killer")
        if "QML_TRIPLE" in pattern:
            families.add("triple_fakeout")
        if "SOP" in pattern:
            families.add("sop")
        if "CONTINUATION" in pattern:
            families.add("continuation")
    signals["setup_families"] = sorted(families)

    return signals
