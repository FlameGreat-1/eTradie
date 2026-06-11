#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
  eTradie — TA Engine Diagnostic Harness
  Tests each SMC component in ISOLATION with REAL market data.
═══════════════════════════════════════════════════════════════════════════

Usage (inside Docker):
    python3 src/diagnostic_harness.py BTCUSDm
    python3 src/diagnostic_harness.py BTCUSDm --tf D1,H4
    python3 src/diagnostic_harness.py EURUSDm --tf W1,D1,H4,H1,M30,M15

Tests (in dependency order):
    1. Swing Detection
    2. BMS Detection
    3. CHoCH Detection
    4. SMS Detection
    5. FVG Detection          ← PRIMARY SUSPECT
    6. Order Block Detection
    7. Zone Freshness         ← PRIMARY SUSPECT
    8. FVG ↔ OB Pairing      ← PRIMARY SUSPECT
    9. Full Zone Validation
   10. Full SMC Pipeline
"""

from __future__ import annotations

import sys
import asyncio
import os
import argparse
import traceback
from datetime import datetime, timedelta, UTC
from collections import Counter
from typing import Optional

# ── Engine imports ────────────────────────────────────────────────────────
from engine.ta.smc.config import SMCConfig
from engine.ta.common.analyzers.candles import CandleAnalyzer
from engine.ta.common.analyzers.swings import SwingAnalyzer
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.analyzers.sweeps import SweepAnalyzer
from engine.ta.common.analyzers.liquidity import LiquidityAnalyzer
from engine.ta.constants import Direction, Timeframe, TIMEFRAME_MINUTES
from engine.ta.models.candle import CandleSequence
from engine.ta.smc.detectors.bms import BMSDetector
from engine.ta.smc.detectors.choch import CHOCHDetector
from engine.ta.smc.detectors.sms import SMSDetector
from engine.ta.smc.detectors.inducement import InducementDetector
from engine.ta.smc.zones.fvg import FVGDetector
from engine.ta.smc.zones.order_block import OrderBlockDetector
from engine.ta.smc.validators.zone.validator import ZoneValidator
from engine.ta.smc.detector import SMCDetector
from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.mt5.factory import create_mt5_broker
from engine.ta.broker.base import BrokerBase

# ── Constants ─────────────────────────────────────────────────────────────
LOOKBACKS = {
    Timeframe.W1: 30, Timeframe.D1: 60, Timeframe.H4: 150,
    Timeframe.H1: 300, Timeframe.M30: 500, Timeframe.M15: 750,
    Timeframe.M5: 1000, Timeframe.M1: 1500,
}

ALL_TIMEFRAMES = [
    Timeframe.W1, Timeframe.D1, Timeframe.H4, Timeframe.H1,
    Timeframe.M30, Timeframe.M15, Timeframe.M5, Timeframe.M1,
]

SEPARATOR = "═" * 72
SUBSEP    = "─" * 60


# ── Formatting helpers ────────────────────────────────────────────────────
def header(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def subheader(title: str) -> None:
    print(f"\n  {SUBSEP}")
    print(f"  {title}")
    print(f"  {SUBSEP}")


def ok(msg: str)   -> None: print(f"    ✅  {msg}")
def warn(msg: str)  -> None: print(f"    ⚠️   {msg}")
def fail(msg: str)  -> None: print(f"    ❌  {msg}")
def info(msg: str)  -> None: print(f"    ℹ️   {msg}")
def bullet(msg: str) -> None: print(f"       • {msg}")


# ══════════════════════════════════════════════════════════════════════════
#  BROKER / DATA LOADING
# ══════════════════════════════════════════════════════════════════════════

async def create_broker() -> BrokerBase:
    """Create broker from env-var config (same as production)."""
    mt5_config = MT5Config()
    if mt5_config.provider == "native":
        return create_mt5_broker(mt5_config)
    else:
        # MetaAPI needs an HTTP client
        try:
            from engine.shared.http.client import HttpClient
            http_client = HttpClient()
            return create_mt5_broker(mt5_config, http_client)
        except Exception:
            # Fallback: try without http_client
            return create_mt5_broker(mt5_config)


async def fetch_candles(
    broker: BrokerBase,
    symbol: str,
    timeframes: list[Timeframe],
) -> dict[Timeframe, CandleSequence]:
    """Fetch candle data for each timeframe (same lookbacks as orchestrator)."""
    sequences: dict[Timeframe, CandleSequence] = {}
    end_time = datetime.now(UTC)

    for tf in timeframes:
        lookback = LOOKBACKS.get(tf, 500)
        minutes = TIMEFRAME_MINUTES.get(tf)
        if minutes is None:
            warn(f"Unknown timeframe {tf.value}, skipping")
            continue

        start_time = end_time - timedelta(minutes=minutes * lookback)
        try:
            seq = await broker.fetch_candles(
                symbol=symbol,
                timeframe=tf,
                start_time=start_time,
                end_time=end_time,
                count=lookback,
            )
            if seq and seq.count > 0:
                sequences[tf] = seq
                ok(f"{tf.value:>4}: {seq.count} candles  "
                   f"({seq.start_time.strftime('%Y-%m-%d')} → "
                   f"{seq.end_time.strftime('%Y-%m-%d %H:%M')})")
            else:
                fail(f"{tf.value:>4}: No data returned")
        except Exception as e:
            fail(f"{tf.value:>4}: Fetch error — {e}")

    return sequences


# ══════════════════════════════════════════════════════════════════════════
#  TEST 1: SWING DETECTION
# ══════════════════════════════════════════════════════════════════════════

def test_swings(
    swing_analyzer: SwingAnalyzer,
    sequences: dict[Timeframe, CandleSequence],
) -> dict:
    header("TEST 1: SWING DETECTION")
    results = {}

    for tf, seq in sequences.items():
        subheader(f"{tf.value} ({seq.count} candles)")
        try:
            highs = swing_analyzer.detect_swing_highs(seq)
            lows  = swing_analyzer.detect_swing_lows(seq)

            results[tf] = {"highs": highs, "lows": lows}

            if highs:
                ok(f"Swing Highs: {len(highs)}")
                for sh in highs[-3:]:
                    bullet(f"Price: {sh.price:.2f}  @  {sh.timestamp}")
            else:
                fail("Swing Highs: 0  ← No swing highs detected!")

            if lows:
                ok(f"Swing Lows:  {len(lows)}")
                for sl in lows[-3:]:
                    bullet(f"Price: {sl.price:.2f}  @  {sl.timestamp}")
            else:
                fail("Swing Lows:  0  ← No swing lows detected!")

        except Exception as e:
            fail(f"EXCEPTION: {e}")
            traceback.print_exc()

    return results


# ══════════════════════════════════════════════════════════════════════════
#  TEST 2: BMS DETECTION
# ══════════════════════════════════════════════════════════════════════════

def test_bms(
    bms_detector: BMSDetector,
    sequences: dict[Timeframe, CandleSequence],
    swing_data: dict,
) -> dict:
    header("TEST 2: BMS (Break in Market Structure) DETECTION")
    results = {}

    for tf, seq in sequences.items():
        subheader(f"{tf.value}")
        try:
            highs = swing_data.get(tf, {}).get("highs", [])
            lows  = swing_data.get(tf, {}).get("lows", [])

            bullish = bms_detector.detect_bullish_bms(seq, highs)
            bearish = bms_detector.detect_bearish_bms(seq, lows)

            results[tf] = {"bullish": bullish, "bearish": bearish}

            status_b = "✅" if bullish else "❌"
            status_s = "✅" if bearish else "❌"
            print(f"    {status_b}  Bullish BMS: {len(bullish)}")
            for b in bullish[-3:]:
                bullet(f"Break: {b.breakout_price:.2f}  Dir: {b.direction.value}  @  {b.timestamp}")
            print(f"    {status_s}  Bearish BMS: {len(bearish)}")
            for b in bearish[-3:]:
                bullet(f"Break: {b.breakout_price:.2f}  Dir: {b.direction.value}  @  {b.timestamp}")

        except Exception as e:
            fail(f"EXCEPTION: {e}")
            traceback.print_exc()

    return results


# ══════════════════════════════════════════════════════════════════════════
#  TEST 3: CHoCH DETECTION
# ══════════════════════════════════════════════════════════════════════════

def test_choch(
    choch_detector: CHOCHDetector,
    sequences: dict[Timeframe, CandleSequence],
    swing_data: dict,
) -> dict:
    header("TEST 3: CHoCH (Change of Character) DETECTION")
    results = {}

    for tf, seq in sequences.items():
        subheader(f"{tf.value}")
        try:
            highs = swing_data.get(tf, {}).get("highs", [])
            lows  = swing_data.get(tf, {}).get("lows", [])

            bullish = choch_detector.detect_bullish_choch(seq, highs)
            bearish = choch_detector.detect_bearish_choch(seq, lows)

            results[tf] = {"bullish": bullish, "bearish": bearish}

            status_b = "✅" if bullish else "⚠️ "
            status_s = "✅" if bearish else "⚠️ "
            print(f"    {status_b}  Bullish CHoCH: {len(bullish)}")
            for c in bullish[-3:]:
                bullet(f"Break: {c.breakout_price:.2f}  Minor: {c.is_minor}  @  {c.timestamp}")
            print(f"    {status_s}  Bearish CHoCH: {len(bearish)}")
            for c in bearish[-3:]:
                bullet(f"Break: {c.breakout_price:.2f}  Minor: {c.is_minor}  @  {c.timestamp}")

        except Exception as e:
            fail(f"EXCEPTION: {e}")
            traceback.print_exc()

    return results


# ══════════════════════════════════════════════════════════════════════════
#  TEST 4: SMS DETECTION
# ══════════════════════════════════════════════════════════════════════════

def test_sms(
    sms_detector: SMSDetector,
    sequences: dict[Timeframe, CandleSequence],
    swing_data: dict,
) -> dict:
    header("TEST 4: SMS (Smart Money Shift) DETECTION")
    results = {}

    for tf, seq in sequences.items():
        subheader(f"{tf.value}")
        try:
            highs = swing_data.get(tf, {}).get("highs", [])
            lows  = swing_data.get(tf, {}).get("lows", [])

            bullish = sms_detector.detect_bullish_sms(seq, lows)
            bearish = sms_detector.detect_bearish_sms(seq, highs)

            results[tf] = {"bullish": bullish, "bearish": bearish}

            status_b = "✅" if bullish else "⚠️ "
            status_s = "✅" if bearish else "⚠️ "
            print(f"    {status_b}  Bullish SMS: {len(bullish)}")
            print(f"    {status_s}  Bearish SMS: {len(bearish)}")

        except Exception as e:
            fail(f"EXCEPTION: {e}")
            traceback.print_exc()

    return results


# ══════════════════════════════════════════════════════════════════════════
#  TEST 5: FVG DETECTION  ← PRIMARY SUSPECT
# ══════════════════════════════════════════════════════════════════════════

def test_fvg(
    fvg_detector: FVGDetector,
    sequences: dict[Timeframe, CandleSequence],
) -> dict:
    header("TEST 5: FVG (Fair Value Gap) DETECTION")
    results = {}

    for tf, seq in sequences.items():
        subheader(f"{tf.value} ({seq.count} candles)")
        try:
            fvgs = fvg_detector.detect_fvgs(seq)
            results[tf] = fvgs

            bullish_fvgs = [f for f in fvgs if f.direction == Direction.BULLISH]
            bearish_fvgs = [f for f in fvgs if f.direction == Direction.BEARISH]

            total = len(fvgs)
            if total > 0:
                ok(f"Total FVGs: {total}  (Bullish: {len(bullish_fvgs)}, Bearish: {len(bearish_fvgs)})")
                info("Latest 5 FVGs:")
                for f in fvgs[-5:]:
                    bullet(
                        f"Dir: {f.direction.value:>7}  "
                        f"Range: [{f.lower_bound:.2f} — {f.upper_bound:.2f}]  "
                        f"CandleIdx: {f.candle_index}  "
                        f"@ {f.timestamp}"
                    )
            else:
                fail(f"Total FVGs: 0  ← NO FVGs DETECTED ON {tf.value}!")
                info("This means the CandleAnalyzer.detect_imbalance() found "
                     "zero 3-candle gaps where candle2 wick doesn't overlap "
                     "candle1/candle3 wicks.")
                info(f"fvg_min_gap_pips config: {fvg_detector.config.fvg_min_gap_pips}")

                # Debug: check how many raw imbalances exist before pip filter
                raw_count = 0
                for i in range(len(seq.candles) - 2):
                    imb = fvg_detector.candle_analyzer.detect_imbalance(
                        seq.candles[i], seq.candles[i+1], seq.candles[i+2],
                    )
                    if imb:
                        raw_count += 1
                if raw_count > 0:
                    warn(f"Raw imbalances (before pip filter): {raw_count} "
                         f"← FVGs exist but are too small (< {fvg_detector.config.fvg_min_gap_pips} pips)")
                else:
                    fail(f"Raw imbalances (before pip filter): 0 "
                         f"← detect_imbalance() returns None for ALL 3-candle sequences")

        except Exception as e:
            fail(f"EXCEPTION: {e}")
            traceback.print_exc()

    return results


# ══════════════════════════════════════════════════════════════════════════
#  TEST 6: ORDER BLOCK DETECTION
# ══════════════════════════════════════════════════════════════════════════

def test_order_blocks(
    ob_detector: OrderBlockDetector,
    sequences: dict[Timeframe, CandleSequence],
    bms_data: dict,
) -> dict:
    header("TEST 6: ORDER BLOCK DETECTION")
    results = {}

    for tf, seq in sequences.items():
        subheader(f"{tf.value}")
        try:
            bullish_bms = bms_data.get(tf, {}).get("bullish", [])
            bearish_bms = bms_data.get(tf, {}).get("bearish", [])
            all_bms = bullish_bms + bearish_bms

            obs = []
            for bms in all_bms:
                if bms.direction == Direction.BULLISH:
                    ob = ob_detector.detect_bullish_ob(seq, bms)
                else:
                    ob = ob_detector.detect_bearish_ob(seq, bms)
                if ob:
                    obs.append(ob)

            results[tf] = obs

            bullish_obs = [o for o in obs if o.direction == Direction.BULLISH]
            bearish_obs = [o for o in obs if o.direction == Direction.BEARISH]

            if obs:
                ok(f"Total OBs: {len(obs)}  (Bullish: {len(bullish_obs)}, Bearish: {len(bearish_obs)})")
                for o in obs[-5:]:
                    bullet(
                        f"Dir: {o.direction.value:>7}  "
                        f"Range: [{o.lower_bound:.2f} — {o.upper_bound:.2f}]  "
                        f"CandleIdx: {o.candle_index}  "
                        f"@ {o.timestamp}"
                    )
            else:
                warn(f"Total OBs: 0 (from {len(all_bms)} BMS events)")

        except Exception as e:
            fail(f"EXCEPTION: {e}")
            traceback.print_exc()

    return results


# ══════════════════════════════════════════════════════════════════════════
#  TEST 7: ZONE FRESHNESS / MITIGATION  ← PRIMARY SUSPECT
# ══════════════════════════════════════════════════════════════════════════

def test_zone_freshness(
    zone_validator: ZoneValidator,
    sequences: dict[Timeframe, CandleSequence],
    ob_data: dict,
) -> dict:
    header("TEST 7: ZONE FRESHNESS (MITIGATION)")
    results = {}

    for tf, obs in ob_data.items():
        if not obs:
            continue
        seq = sequences.get(tf)
        if not seq:
            continue

        subheader(f"{tf.value} ({len(obs)} OBs)")
        try:
            fresh_count = 0
            mitigated_count = 0
            fresh_obs = []

            for ob in obs:
                is_fresh = zone_validator.validate_zone_freshness(ob, seq)
                if is_fresh:
                    fresh_count += 1
                    fresh_obs.append(ob)
                else:
                    mitigated_count += 1

            results[tf] = {"fresh": fresh_obs, "fresh_count": fresh_count, "mitigated_count": mitigated_count}

            if fresh_count > 0:
                ok(f"Fresh (unmitigated): {fresh_count}")
            else:
                fail(f"Fresh (unmitigated): 0  ← ALL OBs mitigated!")

            if mitigated_count > 0:
                status = "❌" if fresh_count == 0 else "⚠️ "
                print(f"    {status}  Mitigated: {mitigated_count}"
                      f"  (rule: candle close beyond OB extreme — SMC-OB-004)")

            info(f"Ratio: {fresh_count}/{len(obs)} fresh")

            # Show sample of fresh OBs if any
            if fresh_obs:
                info("Fresh OBs (available for candidate building):")
                for ob in fresh_obs[-3:]:
                    bullet(
                        f"Dir: {ob.direction.value:>7}  "
                        f"[{ob.lower_bound:.2f} — {ob.upper_bound:.2f}]  "
                        f"CandleIdx: {ob.candle_index}  @ {ob.timestamp}"
                    )

        except Exception as e:
            fail(f"EXCEPTION: {e}")
            traceback.print_exc()

    return results


# ══════════════════════════════════════════════════════════════════════════
#  TEST 8: FVG ↔ OB PAIRING  ← PRIMARY SUSPECT
# ══════════════════════════════════════════════════════════════════════════

def test_fvg_ob_pairing(
    zone_validator: ZoneValidator,
    ob_data: dict,
    fvg_data: dict,
) -> None:
    header("TEST 8: FVG ↔ OB PAIRING")

    for tf in ob_data:
        obs = ob_data.get(tf, [])
        fvgs = fvg_data.get(tf, [])
        if not obs:
            continue

        subheader(f"{tf.value}  —  {len(obs)} OBs vs {len(fvgs)} FVGs")

        if not fvgs:
            fail(f"Zero FVGs on {tf.value} → impossible to pair with any OB!")
            info("This is WHY has_fvg=False for every OB on this timeframe.")
            continue

        matched = 0
        unmatched_reasons = Counter()

        for ob in obs:
            has_fvg = zone_validator.validate_ob_has_fvg(ob, fvgs)
            if has_fvg:
                matched += 1
            else:
                # Diagnose WHY no match
                max_dist = zone_validator.config.fvg_max_candle_distance
                for fvg in fvgs:
                    if fvg.direction != ob.direction:
                        unmatched_reasons["direction_mismatch"] += 1
                    elif abs(fvg.candle_index - ob.candle_index) > max_dist:
                        unmatched_reasons["too_far_apart"] += 1
                    else:
                        unmatched_reasons["no_spatial_overlap"] += 1

        if matched > 0:
            ok(f"Matched: {matched}/{len(obs)} OBs have FVG pairing")
        else:
            fail(f"Matched: 0/{len(obs)} OBs  ← ZERO MATCHES!")

        if unmatched_reasons:
            info("Mismatch breakdown (across all OB↔FVG combinations):")
            for reason, count in unmatched_reasons.most_common():
                bullet(f"{reason}: {count}")


# ══════════════════════════════════════════════════════════════════════════
#  TEST 9: FULL ZONE VALIDATION
# ══════════════════════════════════════════════════════════════════════════

def test_full_zone_validation(
    zone_validator: ZoneValidator,
    sequences: dict[Timeframe, CandleSequence],
    ob_data: dict,
    fvg_data: dict,
    swing_data: dict,
    sweep_analyzer: SweepAnalyzer,
    inducement_detector: InducementDetector,
    fibonacci_analyzer: FibonacciAnalyzer,
    swing_analyzer: SwingAnalyzer,
) -> None:
    header("TEST 9: FULL ZONE VALIDATION (validate_all_ob_rules)")

    # Per SMC-MIT-003 the Fibonacci leg is now per-candidate, built
    # inside each builder from that candidate's own sweep / BMS /
    # SMS / CHoCH / Asian-range endpoints (see smc.builders.fib_leg).
    # There is deliberately no run-wide HTF leg.  This test therefore
    # exercises the non-Fib zone rules (FVG association, liquidity,
    # freshness) with retracement=None — which validate_all_ob_rules
    # handles cleanly (validate_ob_at_premium_discount is a no-op and
    # score_ob_fib_confluence returns 0).  The full per-candidate Fib
    # pipeline is exercised end-to-end by TEST 10.
    info(
        "TEST 9 evaluates FVG/liquidity/freshness gates only. "
        "OTE / Fibonacci confluence is exercised per-candidate in TEST 10."
    )

    for tf in ob_data:
        obs = ob_data.get(tf, [])
        if not obs:
            continue
        seq = sequences.get(tf)
        if not seq:
            continue

        fvgs = fvg_data.get(tf, [])
        highs = swing_data.get(tf, {}).get("highs", [])
        lows  = swing_data.get(tf, {}).get("lows", [])

        # Detect sweeps + inducements for this timeframe
        sweeps = sweep_analyzer.detect_sweeps_in_sequence(seq, highs, lows)
        inducements_bull = inducement_detector.detect_bullish_inducement(seq, lows)
        inducements_bear = inducement_detector.detect_bearish_inducement(seq, highs)
        inducements = inducements_bull + inducements_bear

        # No global Fibonacci retracement by design; see note above.
        retracement = None

        idm_cleared = [idm for idm in inducements if idm.cleared]
        idm_uncleared = [idm for idm in inducements if not idm.cleared]
        idm_total = len(inducements)
        if idm_total > 0:
            cleared_ratio = f"{len(idm_cleared)}/{idm_total} ({100 * len(idm_cleared) / idm_total:.0f}%)"
        else:
            cleared_ratio = "0/0"

        subheader(f"{tf.value}  —  {len(obs)} OBs | {len(fvgs)} FVGs | "
                  f"{len(sweeps)} Sweeps | {idm_total} Inducements "
                  f"(cleared: {cleared_ratio})")

        if idm_cleared:
            info("Sample cleared inducements:")
            for idm in idm_cleared[-3:]:
                bullet(
                    f"Dir: {idm.direction.value:>7}  "
                    f"Level: {idm.inducement_level:.2f}  "
                    f"@ {idm.inducement_timestamp}  "
                    f"cleared_at: {idm.cleared_timestamp}"
                )
        elif idm_uncleared:
            info(f"No inducements cleared yet ({len(idm_uncleared)} waiting). "
                 "This is expected post-Fix 1 for strict-penetration swings.")

        passed = 0
        failed_reasons = Counter()

        for ob in obs:
            result = zone_validator.validate_all_ob_rules(
                ob, fvgs, sweeps, inducements, retracement, seq, [],
            )
            if result:
                passed += 1
            else:
                # Check individual gates
                has_fvg = zone_validator.validate_ob_has_fvg(ob, fvgs)
                has_liq = zone_validator.validate_ob_has_liquidity(ob, sweeps, inducements)
                at_pd   = zone_validator.validate_ob_at_premium_discount(ob, retracement)
                fresh   = zone_validator.validate_zone_freshness(ob, seq)

                if not has_fvg:
                    failed_reasons["has_fvg=False"] += 1
                if not has_liq:
                    failed_reasons["has_liquidity=False"] += 1
                if not at_pd:
                    failed_reasons["at_premium_discount=False"] += 1
                if not fresh:
                    failed_reasons["is_fresh=False"] += 1

        if passed > 0:
            ok(f"PASSED zone validation: {passed}/{len(obs)}")
        else:
            fail(f"PASSED zone validation: 0/{len(obs)}  ← ALL OBs REJECTED!")

        if failed_reasons:
            info("Failure breakdown:")
            for reason, count in failed_reasons.most_common():
                bullet(f"{reason}: {count}")


# ══════════════════════════════════════════════════════════════════════════
#  TEST 10: FULL SMC PIPELINE
# ══════════════════════════════════════════════════════════════════════════

def test_full_pipeline(
    sequences: dict[Timeframe, CandleSequence],
    smc: SMCDetector,
) -> list:
    header("TEST 10: FULL SMC PIPELINE (SMCDetector.detect_patterns)")

    # Define the pairs the orchestrator uses
    htf_pairs = [
        (Timeframe.W1, Timeframe.D1),
        (Timeframe.D1, Timeframe.H4),
        (Timeframe.H4, Timeframe.H1),
    ]
    ltf_pairs = [
        (Timeframe.M30, Timeframe.M15),
        (Timeframe.M15, Timeframe.M5),
        (Timeframe.M5, Timeframe.M1),
    ]
    cross_pair = (Timeframe.H1, Timeframe.M30)

    all_pairs = htf_pairs + [cross_pair] + ltf_pairs
    total_candidates = []

    for htf_tf, ltf_tf in all_pairs:
        if htf_tf not in sequences or ltf_tf not in sequences:
            continue

        subheader(f"{htf_tf.value} → {ltf_tf.value}")
        try:
            candidates = smc.detect_patterns(
                sequences[htf_tf], sequences[ltf_tf],
            )

            total_candidates.extend(candidates)

            pattern_counts = Counter(c.pattern.value for c in candidates)

            if candidates:
                ok(f"Candidates: {len(candidates)}")
                for pattern, count in pattern_counts.most_common():
                    bullet(f"{pattern}: {count}")

                non_turtle = [c for c in candidates
                              if "TURTLE" not in c.pattern.value]
                if non_turtle:
                    ok(f"NON-TURTLE candidates: {len(non_turtle)}")
                    for c in non_turtle[-5:]:
                        meta = c.metadata or {}
                        sweep_ctx = meta.get("sweep_context") or {}
                        sweep_bits = ""
                        if sweep_ctx:
                            sweep_bits = (
                                f"  Sweep: {sweep_ctx.get('liquidity_type')}"
                                f"(cb_in={sweep_ctx.get('closed_back_inside')})"
                            )
                        bullet(
                            f"Pattern: {c.pattern.value}  "
                            f"Dir: {c.direction.value}  "
                            f"Entry: {c.entry_price:.2f}  "
                            f"Fib: {c.fib_level}  "
                            f"IDM_cleared: {c.inducement_cleared}  "
                            f"LTF_Conf: {c.ltf_confirmation}"
                            f"{sweep_bits}"
                        )
                else:
                    warn("NON-TURTLE candidates: 0")
            else:
                warn(f"Candidates: 0")

        except Exception as e:
            fail(f"EXCEPTION: {e}")
            traceback.print_exc()

    # Final summary
    subheader("PIPELINE SUMMARY")
    total = len(total_candidates)
    pattern_summary = Counter(c.pattern.value for c in total_candidates)
    non_turtle = [c for c in total_candidates if "TURTLE" not in c.pattern.value]

    info(f"Total candidates across all pairs: {total}")
    for pattern, count in pattern_summary.most_common():
        bullet(f"{pattern}: {count}")

    if non_turtle:
        ok(f"NON-TURTLE SOUP CANDIDATES: {len(non_turtle)}")
    else:
        fail(f"NON-TURTLE SOUP CANDIDATES: 0  ← THE BUG IS CONFIRMED!")
        info("All structural candidates (Continuation, Reversal, CHoCH) are being dropped.")
        info("Root cause is in Tests 5/7/8 above (FVG detection or zone validation).")

    return total_candidates


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="eTradie TA Diagnostic Harness")
    parser.add_argument("symbol", help="Trading symbol (e.g. BTCUSDm)")
    parser.add_argument(
        "--tf", default=None,
        help="Comma-separated timeframes to test (e.g. D1,H4,H1). Default: all.",
    )
    args = parser.parse_args()

    symbol = args.symbol
    if args.tf:
        tf_names = [t.strip().upper() for t in args.tf.split(",")]
        timeframes = []
        for name in tf_names:
            try:
                timeframes.append(Timeframe(name))
            except ValueError:
                print(f"Unknown timeframe: {name}")
                sys.exit(1)
    else:
        timeframes = ALL_TIMEFRAMES

    print(f"\n{'█' * 72}")
    print(f"  eTradie TA Engine — Diagnostic Harness")
    print(f"  Symbol:     {symbol}")
    print(f"  Timeframes: {', '.join(tf.value for tf in timeframes)}")
    print(f"  Timestamp:  {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'█' * 72}")

    # ── Create broker & fetch data ────────────────────────────────────
    header("PHASE 0: DATA LOADING")
    try:
        broker = await create_broker()
        ok(f"Broker created successfully")
    except Exception as e:
        fail(f"Broker creation failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    sequences = await fetch_candles(broker, symbol, timeframes)
    if not sequences:
        fail("No candle data retrieved. Cannot run diagnostics.")
        sys.exit(1)

    info(f"Loaded {len(sequences)} timeframes")

    # ── Create detectors (same config as production) ──────────────────
    config = SMCConfig()
    info(f"SMCConfig loaded:")
    bullet(f"fvg_min_gap_pips:      {config.fvg_min_gap_pips}")
    bullet(f"fvg_max_candle_distance: {config.fvg_max_candle_distance}")
    bullet(f"require_fvg_with_ob:   {config.require_fvg_with_ob}")
    bullet(f"min_displacement_pips: {config.min_displacement_pips}")
    bullet(f"inducement_min_break_pips: {config.inducement_min_break_pips}")
    bullet(f"fibonacci_tolerance_pips: {config.fibonacci_tolerance_pips}")
    bullet(f"sweep_max_candle_distance: {config.sweep_max_candle_distance}")

    # Create all common analyzers
    from engine.ta.common.analyzers.session import SessionAnalyzer
    from engine.ta.common.analyzers.dealing_range import DealingRangeAnalyzer

    candle_analyzer = CandleAnalyzer()
    swing_analyzer = SwingAnalyzer()
    session_analyzer = SessionAnalyzer()
    liquidity_analyzer = LiquidityAnalyzer()
    sweep_analyzer = SweepAnalyzer()
    fibonacci_analyzer = FibonacciAnalyzer()
    dealing_range_analyzer = DealingRangeAnalyzer()

    # Use SMCDetector to create all sub-detectors (ensures identical config)
    smc = SMCDetector(
        config=config,
        candle_analyzer=candle_analyzer,
        swing_analyzer=swing_analyzer,
        session_analyzer=session_analyzer,
        liquidity_analyzer=liquidity_analyzer,
        sweep_analyzer=sweep_analyzer,
        fibonacci_analyzer=fibonacci_analyzer,
        dealing_range_analyzer=dealing_range_analyzer,
    )
    bms_detector       = smc.bms_detector
    choch_detector     = smc.choch_detector
    sms_detector       = smc.sms_detector
    fvg_detector       = smc.fvg_detector
    ob_detector        = smc.ob_detector
    zone_validator     = smc.zone_validator
    inducement_detector = smc.inducement_detector

    # ── Run all tests ─────────────────────────────────────────────────
    swing_data = test_swings(swing_analyzer, sequences)
    bms_data   = test_bms(bms_detector, sequences, swing_data)
    choch_data = test_choch(choch_detector, sequences, swing_data)
    sms_data   = test_sms(sms_detector, sequences, swing_data)
    fvg_data   = test_fvg(fvg_detector, sequences)
    ob_data    = test_order_blocks(ob_detector, sequences, bms_data)
    fresh_data = test_zone_freshness(zone_validator, sequences, ob_data)
    test_fvg_ob_pairing(zone_validator, ob_data, fvg_data)
    test_full_zone_validation(
        zone_validator, sequences, ob_data, fvg_data, swing_data,
        sweep_analyzer, inducement_detector, fibonacci_analyzer, swing_analyzer,
    )
    candidates = test_full_pipeline(sequences, smc)

    # Dump candidates to JSON for user inspection
    import json
    
    # Simple serializer for dates/enums
    def default_serializer(obj):
        if hasattr(obj, 'value'): # Enums
            return obj.value
        elif hasattr(obj, 'isoformat'): # Datetimes
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, 'model_dump'): # BaseModel
            return obj.model_dump(mode='json')
        return str(obj)

    json_path = '/tmp/diagnostic_results.json'
    try:
        # Pydantic models usually support model_dump(mode='json')
        dump_data = []
        for c in candidates:
            if hasattr(c, 'model_dump'):
                dump_data.append(c.model_dump(mode='json'))
            else:
                dump_data.append(c.__dict__)
                
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(dump_data, f, indent=2, default=default_serializer)
        ok(f"Saved {len(candidates)} candidates to JSON: {json_path}")
    except Exception as e:
        fail(f"Could not save JSON results: {e}")

    # ── FINAL VERDICT ─────────────────────────────────────────────────
    header("FINAL DIAGNOSTIC VERDICT")

    total_fvgs = sum(len(f) for f in fvg_data.values())
    total_obs  = sum(len(o) for o in ob_data.values())
    total_fresh = sum(
        d.get("fresh_count", 0) for d in fresh_data.values()
    )

    info(f"Total FVGs detected:     {total_fvgs}")
    info(f"Total OBs detected:      {total_obs}")
    info(f"Total Fresh (unmit) OBs: {total_fresh}")

    if total_fvgs == 0:
        fail("VERDICT: FVG DETECTOR IS BROKEN!")
        fail("The CandleAnalyzer.detect_imbalance() is not finding any "
             "3-candle gaps. This is the ROOT CAUSE of has_fvg=False.")
    elif total_fresh == 0:
        fail("VERDICT: ZONE FRESHNESS IS TOO AGGRESSIVE!")
        fail("Every single OB is flagged as mitigated under the "
             "close-beyond-extreme rule (SMC-OB-004). Review the "
             "candles-after-OB stream or the OB detector output.")
    elif total_fvgs > 0 and total_fresh > 0:
        ok("Individual components look healthy!")
        info("If non-turtle candidates are still 0, the issue is in "
             "FVG↔OB pairing (distance/direction/overlap) or "
             "the candidate builders themselves.")

    # ── FIX VERIFICATION ────────────────────────────────────────────
    # Summarise whether the recent Fixes are actually reflected in the
    # emitted candidates. Purely informational; does not alter behaviour.
    header("FIX VERIFICATION SUMMARY")

    total_candidates = len(candidates)
    info(f"Total candidates emitted: {total_candidates}")

    if total_candidates == 0:
        info("No candidates emitted — fix verification skipped.")
    else:
        pattern_summary = Counter(c.pattern.value for c in candidates)
        info("Pattern distribution:")
        for pattern, count in pattern_summary.most_common():
            bullet(f"{pattern}: {count}")

        # Fix 1: inducement clearance should not be uniformly True
        cleared_count = sum(1 for c in candidates if c.inducement_cleared)
        cleared_pct = 100.0 * cleared_count / total_candidates
        info(
            f"inducement_cleared=True on {cleared_count}/{total_candidates} "
            f"({cleared_pct:.1f}%)"
        )
        if cleared_pct >= 99.0:
            warn(
                "Almost every candidate still shows inducement_cleared=True. "
                "If this is real market behaviour it's fine, but verify the "
                "inducement_min_break_pips threshold is applied."
            )

        # Per SMC-MIT-003 each candidate now carries a per-candidate
        # Fibonacci leg built inside its own builder from that
        # candidate's structural endpoints (sweep, BMS, SMS, CHoCH,
        # Asian range).  fib_level/fib_context are intentionally None
        # when the setup lacks those endpoints (e.g. a continuation
        # candidate with no associated sweep) — no fallback leg is
        # ever fabricated.
        fib_level_count = sum(1 for c in candidates if c.fib_level is not None)
        fib_context_count = sum(
            1 for c in candidates
            if isinstance(c.metadata, dict)
            and c.metadata.get("fib_context") is not None
        )
        fib_level_pct = 100.0 * fib_level_count / total_candidates
        fib_context_pct = 100.0 * fib_context_count / total_candidates
        info(
            f"fib_level populated on {fib_level_count}/{total_candidates} "
            f"({fib_level_pct:.1f}%)"
        )
        info(
            f"metadata.fib_context populated on {fib_context_count}/"
            f"{total_candidates} ({fib_context_pct:.1f}%)"
        )
        if fib_level_count == 0:
            warn(
                "fib_level is null on every candidate. That is expected "
                "only if every emitted candidate lacks its setup-specific "
                "Fib endpoints (no sweep on continuations, no Asian range "
                "on AMD, no opposing swing on turtle soup, etc.). If you "
                "see this on a run with obviously valid setups, check the "
                "has_per_candidate_fib_leg field in the per-builder logs."
            )

        # Direction-mismatched OTE readings were the core bug fixed by
        # the per-candidate leg work.  A healthy run should show zero
        # candidates whose fib_context.is_in_ote conflicts with the
        # candidate's own direction zone.
        direction_mismatches = 0
        for c in candidates:
            if not isinstance(c.metadata, dict):
                continue
            ctx = c.metadata.get("fib_context")
            if not ctx or not ctx.get("is_in_ote"):
                continue
            zone = ctx.get("zone")
            if c.is_bullish and zone == "PREMIUM":
                direction_mismatches += 1
            elif c.is_bearish and zone == "DISCOUNT":
                direction_mismatches += 1
        if direction_mismatches > 0:
            warn(
                f"{direction_mismatches} candidate(s) report is_in_ote=True "
                "against a zone that disagrees with the candidate direction. "
                "This should be zero after the per-candidate Fib refactor."
            )
        else:
            ok("No direction-mismatched OTE readings detected.")

        # Fix 3: sweep_context should exist on candidates whose selected
        # LiquiditySweep was non-null. We expect this on most SH_BMS_RTO
        # candidates and on turtle-soup candidates.
        sweep_context_count = sum(
            1 for c in candidates
            if isinstance(c.metadata, dict)
            and c.metadata.get("sweep_context") is not None
        )
        liquidity_types = Counter()
        for c in candidates:
            if not isinstance(c.metadata, dict):
                continue
            ctx = c.metadata.get("sweep_context")
            if ctx is None:
                continue
            lt = ctx.get("liquidity_type")
            if lt:
                liquidity_types[lt] += 1

        info(
            f"metadata.sweep_context populated on {sweep_context_count}/"
            f"{total_candidates} ({100.0 * sweep_context_count / total_candidates:.1f}%)"
        )
        if liquidity_types:
            info("Distinct liquidity_type values observed:")
            for lt, count in liquidity_types.most_common():
                bullet(f"{lt}: {count}")
        elif sweep_context_count == 0:
            info(
                "No sweep_context present — either no sweep was selected "
                "for any candidate, or the selected pattern had liquidity_swept=False."
            )

    print(f"\n{'█' * 72}")
    print(f"  Diagnostic complete.")
    print(f"{'█' * 72}\n")


if __name__ == "__main__":
    asyncio.run(main())
