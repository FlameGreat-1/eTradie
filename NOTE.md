se/.hushlogin file.
softverse@Softverse:~$ cd eTradie
softverse@Softverse:~/eTradie$ git pull gitlab main
remote: Enumerating objects: 106, done.
remote: Counting objects: 100% (106/106), done.
remote: Compressing objects: 100% (89/89), done.
remote: Total 89 (delta 74), reused 0 (delta 0), pack-reused 0 (from 0)
Unpacking objects: 100% (89/89), 24.27 KiB | 176.00 KiB/s, done.
From https://gitlab.com/exoper-chi/exoper-izi
 * branch            main       -> FETCH_HEAD
   fbf5113..1cfd9bf  main       -> gitlab/main
Updating fbf5113..1cfd9bf
Fast-forward
 src/engine/ta/smc/builders/amd/candidates.py   |  99 ++++++++++++++----
 src/engine/ta/smc/builders/continuation.py     |  77 +++++++++++---
 src/engine/ta/smc/builders/fib_leg.py          | 364 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 src/engine/ta/smc/builders/reversal.py         | 138 +++++++++++++++++++++----
 src/engine/ta/smc/config.py                    |  17 +--
 src/engine/ta/smc/detector.py                  | 135 ++++++++++--------------
 src/engine/ta/smc/detectors/bms.py             |  22 ++--
 src/engine/ta/smc/validators/zone/validator.py |  50 ++++++---
 8 files changed, 743 insertions(+), 159 deletions(-)
 create mode 100644 src/engine/ta/smc/builders/fib_leg.py
softverse@Softverse:~/eTradie$ git status
On branch main
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   NOTE.md

no changes added to commit (use "git add" and/or "git commit -a")
softverse@Softverse:~/eTradie$



 (use "git add" and/or "git commit -a")
softverse@Softverse:~/eTradie$ git pull gitlab main
remote: Enumerating objects: 7, done.
remote: Counting objects: 100% (7/7), done.
remote: Compressing objects: 100% (4/4), done.
remote: Total 4 (delta 3), reused 0 (delta 0), pack-reused 0 (from 0)
Unpacking objects: 100% (4/4), 3.02 KiB | 119.00 KiB/s, done.
From https://gitlab.com/exoper-chi/exoper-izi
 * branch            main       -> FETCH_HEAD
   1cfd9bf..65135fe  main       -> gitlab/main
Updating 1cfd9bf..65135fe
Fast-forward
 src/diagnostic_harness.py | 82 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--------------------
 1 file changed, 62 insertions(+), 20 deletions(-)
softverse@Softverse:~/eTradie$





























Commit 9 landed: [`amd/candidates.py`](https://gitlab.com/exoper-chi/exoper-izi/-/blob/main/src/engine/ta/smc/builders/amd/candidates.py).

All dead `retracement` passthroughs are now gone from the SMC builder layer.

Summary of everything shipped to `main`:

1. [`fib_leg.py`](https://gitlab.com/exoper-chi/exoper-izi/-/blob/main/src/engine/ta/smc/builders/fib_leg.py) — new per-candidate leg selector module
2. [`continuation.py`](https://gitlab.com/exoper-chi/exoper-izi/-/blob/main/src/engine/ta/smc/builders/continuation.py) — fib leg wiring
3. [`reversal.py`](https://gitlab.com/exoper-chi/exoper-izi/-/blob/main/src/engine/ta/smc/builders/reversal.py) — fib leg wiring
4. [`amd/candidates.py`](https://gitlab.com/exoper-chi/exoper-izi/-/blob/main/src/engine/ta/smc/builders/amd/candidates.py) — fib leg wiring
5. [`detector.py`](https://gitlab.com/exoper-chi/exoper-izi/-/blob/main/src/engine/ta/smc/detector.py) — deleted `_create_fibonacci_retracement`, rewired call sites, CHoCH per-candidate leg
6. [`validator.py`](https://gitlab.com/exoper-chi/exoper-izi/-/blob/main/src/engine/ta/smc/validators/zone/validator.py) — freshness docstring corrected
7. [`config.py`](https://gitlab.com/exoper-chi/exoper-izi/-/blob/main/src/engine/ta/smc/config.py) — deleted dead `zone_mitigation_body_threshold` field
8. `continuation.py` — deleted dead `retracement` param
9. `reversal.py` — deleted dead `retracement` param
10. `amd/candidates.py` — deleted dead `retracement` param

Swing-bar HTF override left untouched per your instruction.





Now here is exactly how each fib is drawn. No code, just the leg endpoints in plain trading terms.

#### SH + BMS + RTO — Bullish (Pattern 7)
- **Swing low** = the SSL level that price swept (the stop-hunt low below a PDL / PWL / old low / equal lows).
- **Swing high** = the closing price of the candle that broke structure upward (BMS breakout close).
- **Direction** = bullish (low → high).
- **Meaning**: fib is drawn on the impulse that ran from the swept low up through the broken structure. The bullish OB sits inside this leg; 61.8 / 70.5 / 78.6 retracement from the high *down* toward the low is the OTE buy pocket.

#### SH + BMS + RTO — Bearish (Pattern 2)
- **Swing high** = the BSL level that price swept (the stop-hunt high above a PDH / PWH / old high / equal highs).
- **Swing low** = the closing price of the candle that broke structure downward (BMS breakout close).
- **Direction** = bearish (high → low).
- **Meaning**: fib is drawn on the impulse that ran from the swept high down through the broken structure. The bearish OB sits inside this leg; 61.8 / 70.5 / 78.6 retracement from the low *up* toward the high is the OTE sell pocket.

#### SMS + BMS + RTO — Bullish (Pattern 8)
- **Swing low** = the SMS failure level — the previous swing low that price failed to break (the "held" low that signalled exhaustion).
- **Swing high** = the closing price of the confirming bullish BMS.
- **Direction** = bullish (low → high).

#### SMS + BMS + RTO — Bearish (Pattern 3)
- **Swing high** = the SMS failure level — the previous swing high that price failed to break.
- **Swing low** = the closing price of the confirming bearish BMS.
- **Direction** = bearish (high → low).

#### CHOCH + BMS + RTO — Bullish
- **Swing low** = the CHoCH broken level — the last lower-high of the prior bearish structure that was taken out (the first sign of order-flow shift upward).
- **Swing high** = the closing price of the candle that made the CHoCH (the close that broke the LH).
- **Direction** = bullish (low → high).

#### CHOCH + BMS + RTO — Bearish
- **Swing high** = the CHoCH broken level — the last higher-low of the prior bullish structure that was taken out (first sign of order-flow shift downward).
- **Swing low** = the closing price of the candle that made the CHoCH.
- **Direction** = bearish (high → low).

#### AMD — Bullish (Pattern 9)
- **Swing low** = the Asian session range low (this is the manipulation extreme — London/NY took price down below the Asian low to trap sellers before reversing).
- **Swing high** = the closing price of the confirming bullish BMS during the Distribution phase.
- **Direction** = bullish (low → high).
- **Meaning**: fib is drawn on the reversal impulse that started at the manipulation low and ended at the distribution-confirming BMS close.

#### AMD — Bearish (Pattern 4)
- **Swing high** = the Asian session range high (manipulation extreme — London/NY pushed above Asian high to trap buyers).
- **Swing low** = the closing price of the confirming bearish BMS during Distribution.
- **Direction** = bearish (high → low).

#### Turtle Soup Long (Pattern 6)
- **Swing low** = the SSL level that was swept (the low below the key support where stops were sitting).
- **Swing high** = the nearest structural swing high that is strictly above the swept level, taken from the LTF swing-high list.
- **Direction** = bullish (low → high).
- **Meaning**: after the SSL sweep and bullish close-back-inside, price rallies toward the nearest opposing swing high. Fib is drawn on that immediate reversal leg. If no swing high above the swept level exists in the supplied swing list, the selector returns no leg and the candidate emits without fib context — no fabrication.

#### Turtle Soup Short (Pattern 1)
- **Swing high** = the BSL level that was swept.
- **Swing low** = the nearest structural swing low strictly below the swept level.
- **Direction** = bearish (high → low).
- Same nearest-swing logic, symmetric. No leg → no fib context.

#### Universal policy across all of the above
- Leg is **always** direction-matched to the candidate: bullish candidate → up-leg → `is_bullish=True`; bearish candidate → down-leg → `is_bullish=False`. They are never crossed.
- Leg is **always** per-candidate. Nothing is shared across candidates or across a run.
- If any required endpoint is missing (no sweep, no Asian range, no opposing swing in the supplied list), the leg is `None` and the candidate emits with `fib_level=None` and no `fib_context` in metadata. There is no fallback leg, no global HTF leg, no invented price.
- OTE pocket bounds used downstream for the `is_in_ote` flag and the confluence score are 61.8 % and 78.6 % of the leg. 70.5 % is the middle reference. These are the correct institutional OTE levels.

If any of the endpoints I listed disagree with how you personally draw the fib on a chart, tell me which pattern and where you anchor the leg, and I'll re-examine that selector specifically. Otherwise this matches your rulebook and the standard Wade/ICT SMC convention.