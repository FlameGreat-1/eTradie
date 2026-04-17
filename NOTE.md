Both MRs are merged. I have the first 42% of the output — enough to confirm the good news and isolate the real issue. Let me state it directly.

Note: This response is based on the first 42% of the output; the later H1/M15 sections and the bearish patterns were truncated. What I'm reporting below is anchored on rows I verified, plus one issue in the truncated summary you pasted in your message.

#### What's working correctly now

**candidate_id uniqueness — fixed.** Every row now carries an 8-char fingerprint suffix. Rows at the same entry price but different source triples get distinct IDs. Example: the two `BTCUSDM_SH_BMS_RTO_BULLISH_BULLISH_67307.0` rows now read `_6bba777e` and `_01501aff`. Correct.

**Turtle Soup fib — removed.** All Turtle Soup rows I saw have `fib_level: null` and no `fib_context`. Correct, per your instruction.

**Structural SLs landed and behaviour is visibly different.** Comparing H1 `SH_BMS_RTO_BULLISH @ 75502.66`:
- Previous run: SL `75096.39` (406 points risk) paired with TP `75557.94` (55 reward) → R:R 0.14.
- Current run: SL `75017.536` (485 risk) paired with TP `76111.67` (609 reward) → R:R 1.26. Clean 1:1+ R:R, TP now reaches the actual 76111.67 swept-high level.

The TP improvements are real and come from the `min_take_profit_rr` floor combined with the wider structural SL.

**Example R:R checks on individual rows that worked cleanly:**
- H1 SH_BMS_RTO_BULLISH @ 69129.02 → risk 1039, reward 1143 → R:R 1.10 ✓
- H1 SH_BMS_RTO_BULLISH @ 71074.83 → risk 547, reward 745 → R:R 1.36 ✓
- H4 SMS_BMS_RTO_BULLISH @ 66883.755 → risk 2017, reward 2405 → R:R 1.19 ✓
- H1 CHOCH_BMS_RTO_BULLISH @ 75502.66 → risk 485, reward 609 → R:R 1.26 ✓

#### What is NOT working — real issues

**Issue A (CRITICAL): bullish TPs placed BELOW entry on H4 SH_BMS_RTO.** Four rows at entry `74853.345`:

| Row | Entry | SL | TP | Problem |
|---|---|---|---|---|
| 1 | 74853.345 | 73236.853 | **72982.15** | TP is *below* entry — bearish target on bullish setup |
| 2 | 74853.345 | 73236.853 | **72982.15** | same |
| 3 | 74853.345 | **67823.893** | 72982.15 | SL is 7030 pts away, TP still below entry |

This is catastrophic. A bullish candidate with TP below entry is an inverted trade. The math says `(entry - TP) = 1871` satisfies the R:R floor because `|swing - entry| = 1871 ≥ 1617 * 1.0`, but the selector only filters by **distance**, not by **direction**. The selector `_find_nearest_bsl_target` should only return swings **above** entry; it's apparently allowing the fallback `htf_bms.breakout_price = 72982.15` to be used even though it sits below entry on these candidates.

Looking at the data: `htf_bms.breakout_price = 72982.15` (from BMS on `2026-04-11`) is below the current entry `74853.345`. The fallback doesn't check direction. **Bug in fallback logic across all non-Turtle-Soup bullish builders.**

**Issue B (CRITICAL): SMS bullish rows with `take_profit: null`.** Five H1 SMS rows have `take_profit: null`:
- H1 SMS_BMS_RTO_BULLISH @ 70990.65 → SL 65609, TP null
- H1 SMS_BMS_RTO_BULLISH @ 72100.195 → SL 65599, TP null
- H1 SMS_BMS_RTO_BULLISH @ 75502.66 → SL 65602, TP null
- H1 SMS_BMS_RTO_BULLISH @ 74691.035 → SL 65656, TP null (×2)

These are emitting with `take_profit=null` because no swing satisfies the 1:1 R:R floor against a massive SL distance (~9000-10000 points) and there's no fallback for SMS. The SMS anchor `htf_sms.failed_level = 65682.9` produces a gigantic SL because the SMS failed level is way below the entry. The OB range is small, so clamp doesn't help.

This is working as designed (no swing clears 9000-point reward floor → null TP), but the **root cause** is the SMS SL is being anchored to a failure level from 2 weeks ago that has nothing to do with the current OB. On a 20-bar SMS on H1, the failure level was correct. On a 10-day-old SMS paired with an OB from today, the SL is absurd.

**Issue C: AMD rows have similarly deep SLs.** H4 AMD_BULLISH @ 74853.345: SL `74461.863`, TP `75463.56`. That works. But the AMD SL uses `asian_range.low` — the Asian-range-per-session fix I landed should prevent the old "aggregated weeks" bug. The numbers look plausible here so this is fine.

**Issue D: `is_in_ote=true` on 8 candidates that disagree with direction (from your diagnostic summary).** The harness flagged this. Worth checking — but from the rows I saw, the direction-matching is correct in the fib_context blocks I verified. Likely related to OTE pip tolerance at leg boundaries. Not urgent.

**Issue E: `ltf_confirmation=false` on basically everything except Turtle Soup.** As before, working by design per the validator docstring.

#### The fixes I need to ship

Two bugs require immediate action before you run another test:

**Fix 1 (Issue A): TP fallback direction guard.** In `continuation.py`, `reversal.py`, `amd/candidates.py`, and `detector.py` CHoCH path, when `_find_nearest_bsl_target`/`_find_nearest_ssl_target` returns `None`, the caller falls back to `htf_bms.breakout_price` / `htf_choch.breakout_price` / `asian_range.high`. **None of these fallbacks check direction.** The fallback must be:

```python
# Bullish:
if take_profit is None or take_profit <= entry_price:
    take_profit = None  # emit null rather than inverted

# Bearish:
if take_profit is None or take_profit >= entry_price:
    take_profit = None
```

Emitting `null` is cleaner than emitting an inverted TP.

**Fix 2 (Issue B): SMS SL clamp to entry-relative bound.** When `htf_sms.failed_level` sits absurdly far from the current OB (more than, say, 3× the OB range below entry for bullish), the SL is structurally wrong — that SMS is stale relative to this OB. Options:
- (a) Clamp SL distance to `max(OB-edge-buffer, structural_level - buffer)` capped at some multiple of OB range.
- (b) Reject SMS candidates where the failure level is too far from the current OB.
- (c) Leave as-is and accept the null TP outcome.

I lean toward (a) with a cap of 3× OB range, because that keeps the SMC structural rule intact while preventing the absurd 9000-point SL. But this is a trading-policy call, not a code call.

Tell me:
1. Ship Fix 1 immediately (direction guard on TP fallbacks) — yes/no?
2. For Fix 2, which option (a/b/c)?




YOU SHOULD ADDRESS ALL THE ISSUES NOW NOT JUST ONLY 2




Now I have full ground truth on every issue. Let me state each fix with precise evidence, then ship them as atomic commits.

#### Complete issue catalogue with root-cause evidence

**Issue A — Inverted TPs (bullish candidates with TP below entry).** Verified in the JSON: H4 SH_BMS_RTO_BULLISH at entry 74853.345 has `take_profit: 72982.15` (below entry, equal to `htf_bms.breakout_price` from 2026-04-11). The fallback does not check direction. **Root cause:** in `continuation.py` / `detector.py` / `reversal.py` / `amd/candidates.py`, every fallback `if take_profit is None: take_profit = <fallback_price>` assumes the fallback is directionally correct, but it isn't. When the current setup's OB is above the historical BMS breakout, a bullish TP fallback to that breakout price places TP below entry.

**Issue B — Null TPs on SMS with huge SL distances.** Verified: five H1 SMS rows with SL ~65600 and `take_profit: null`. SL distance 9000+ points, no swing meets 1:1 R:R floor. **Root cause:** SMS SL is anchored to `htf_sms.failed_level`, which can be structurally stale relative to the current OB when they're weeks apart. The SMS failure level is valid SMC structure, but the pair (failure-level, current-OB) is not coherent when the OB formed 10+ days after the SMS.

**Issue C — AMD SLs still using aggregated Asian range.** Wait — verified: H4 AMD_BULLISH at 74853.345 has SL 74461.863. OB lower is 74527.11, so SL sits 65 points below OB lower. That's the clamped-to-OB-edge case (Asian range low is above OB). Correct behaviour. But the smaller H4 AMD at 66883.755 has SL 66528.645 = `ob.lower_bound (66587.83) - buffer (59.19)`. Also clamped. **This is working correctly.**

**Issue D — `is_in_ote=true` on 8 candidates disagreeing with direction.** Looking at `build_fib_context`: it returns `is_in_ote` raw from `fibonacci_analyzer.is_at_ote`, which checks pip-tolerance proximity to the OTE pocket. It does NOT check that the price is on the right side of equilibrium for the direction. So a bullish candidate at 0.365 percentage (PREMIUM zone — wrong side for a buy) with `is_in_ote: true` is misleading. **Root cause:** `is_in_ote=true` should require both (a) proximity to 0.618/0.786 levels AND (b) `zone == DISCOUNT` for bullish / `zone == PREMIUM` for bearish.

Evidence: H4 SH_BMS_RTO_BULLISH @ 74853.345 with fib_level 0.365, zone PREMIUM, `is_in_ote: true`. A bullish setup at a premium price cannot be "in the OTE buy pocket" — that contradicts the definition of OTE. The flag should be `false`.

**Issue E — `ltf_confirmation=false` on everything.** Working as designed per the validator docstring ("execution timing, not detection gate"). **No action.**

#### The fixes

I'll ship four atomic commits:

1. **TP direction guard** — emit `null` rather than an inverted fallback TP.
2. **SMS SL coherence cap** — cap SMS SL distance to a reasonable multiple of OB range so stale failure levels don't produce 9000-point stops.
3. **`is_in_ote` direction-coherent** — require the zone to match the candidate direction before flagging OTE true.
4. **Unified documentation commit** — one-line field note on `is_in_ote` semantics.

Shipping now.






0, tzinfo=datetime.timezone.utc), 75627.49, 75178.66, datetime.datetime(2026, 4, 17, 8, 30, tzinfo=datetime.timezone.utc), False, None, None, False, None, False, None, 218.86, \'0.512\', \'AMD_DISTRIBUTION\', None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, \'{"confluences": 5, "fib_context": {"percentage": 0.5118, "zone": "EQUILIBRIUM", "is_in_ote": false, "nearest_level_name": "0.5"}}\', True, None, None, None, datetime.datetime(2026, 4, 17, 18, 6, 36, 253845, tzinfo=datetime.timezone.utc))]\n(Background on this error at: https://sqlalche.me/e/20/gkpj) (Background on this error at: https://sqlalche.me/e/20/7s2a)'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1093, in _persist_all_results
etradie-engine  |     snd_schemas = await uow.candidate_repo.bulk_create_snd_candidates(
etradie-engine  |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 361, in bulk_create_snd_candidates
etradie-engine  |     existing_keys = await self._fetch_existing_dedup_keys(
etradie-engine  |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/app/src/engine/ta/storage/repositories/candidate.py", line 480, in _fetch_existing_dedup_keys
etradie-engine  |     result = await self.session.execute(
etradie-engine  |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 463, in execute
etradie-engine  |     result = await greenlet_spawn(
etradie-engine  |              ^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 190, in greenlet_spawn
etradie-engine  |     result = context.switch(*args, **kwargs)
etradie-engine  |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2365, in execute
etradie-engine  |     return self._execute_internal(
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2241, in _execute_internal
etradie-engine  |     conn = self._connection_for_bind(bind)
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2110, in _connection_for_bind
etradie-engine  |     return trans._connection_for_bind(engine, execution_options)
etradie-engine  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "<string>", line 2, in _connection_for_bind
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/state_changes.py", line 103, in _go
etradie-engine  |     self._raise_for_prerequisite_state(fn.__name__, current_state)
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 973, in _raise_for_prerequisite_state
etradie-engine  |     raise sa_exc.PendingRollbackError(
etradie-engine  | sqlalchemy.exc.PendingRollbackError: This Session's transaction has been rolled back due to a previous exception during flush. To begin a new transaction with this Session, first issue Session.rollback(). Original exception was: (sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) <class 'asyncpg.exceptions.NotNullViolationError'>: null value in column "take_profit" of relation "candidates" violates not-null constraint
etradie-engine  | DETAIL:  Failing row contains (088e093d-e40e-47b7-952e-1a7eee663d64, BTCUSDM, H4, SMS_BMS_RTO_BULLISH, BULLISH, 2026-04-17 16:00:00+00, 74853.345, 64860.543, null, D1, H4, t, f, t, 64925.79, 2026-04-02 00:00:00+00, t, 77828.58, 2026-04-17 16:00:00+00, t, 75611.69, 2026-04-17 16:00:00+00, 75179.58, 74527.11, 2026-04-17 00:00:00+00, f, null, null, f, f, null, 1716.91, 0.231, null, null, null, null, {"confluences": 9, "fib_context": {"percentage": 0.2306, "zone":..., t, null, null, null, 2026-04-17 18:06:36.252834+00, admin_uuid_123, 75550.18, 75113.31, 2026-04-17 08:00:00+00, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null).
etradie-engine  | [SQL: INSERT INTO candidates (id, user_id, symbol, timeframe, pattern, direction, timestamp, entry_price, stop_loss, take_profit, htf_timeframe, ltf_timeframe, is_smc, is_snd, sms_detected, sms_price, sms_timestamp, bms_detected, bms_price, bms_timestamp,  ... 219397 characters truncated ... 11157::TIMESTAMP WITH TIME ZONE, $11158::VARCHAR, $11159::VARCHAR, $11160::TIMESTAMP WITH TIME ZONE)]
etradie-engine  | [parameters: (UUID('63b0c957-7cb2-4581-aec0-76c1c3ba2191'), 'admin_uuid_123', 'BTCUSDM', <Timeframe.D1: 'D1'>, 'SH_BMS_RTO_BEARISH', 'BEARISH', datetime.datetime(2026, 4, 17, 0, 0, tzinfo=datetime.timezone.utc), 110097.75, 114876.774, 103506.14, <Timeframe.W1: 'W1'>, <Timeframe.D1: 'D1'>, True, False, False, None, None, True, 102282.38, datetime.datetime(2025, 11, 9, 0, 0, tzinfo=datetime.timezone.utc), True, 66352.98, datetime.datetime(2026, 3, 29, 0, 0, tzinfo=datetime.timezone.utc), 114080.27, 106115.23, datetime.datetime(2025, 10, 19, 0, 0, tzinfo=datetime.timezone.utc), 67138.79, 64982.73, datetime.datetime(2026, 2, 23, 0, 0, tzinfo=datetime.timezone.utc), True, 68298.33, datetime.datetime(2026, 2, 21, 0, 0, tzinfo=datetime.timezone.utc), False, None, False, None, 1223.76, None, None, None, None, None, None, None, None, None, None, None, None, None ... 11060 parameters truncated ... datetime.datetime(2026, 4, 15, 19, 30, tzinfo=datetime.timezone.utc), 75906.93, 75181.66, datetime.datetime(2026, 4, 17, 10, 0, tzinfo=datetime.timezone.utc), 75627.49, 75178.66, datetime.datetime(2026, 4, 17, 8, 30, tzinfo=datetime.timezone.utc), False, None, None, False, None, False, None, 218.86, '0.512', 'AMD_DISTRIBUTION', None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, '{"confluences": 5, "fib_context": {"percentage": 0.5118, "zone": "EQUILIBRIUM", "is_in_ote": false, "nearest_level_name": "0.5"}}', True, None, None, None, datetime.datetime(2026, 4, 17, 18, 6, 36, 253845, tzinfo=datetime.timezone.utc))]
etradie-engine  | (Background on this error at: https://sqlalche.me/e/20/gk



))]
etradie-engine  | (Background on this error at: https://sqlalche.me/e/20/gkpj) (Background on this error at: https://sqlalche.me/e/20/7s2a)
etradie-engine  | 2026-04-17T18:06:36.519493Z [ERROR    ] db_unexpected_error            [engine.shared.db.connection] extra={'trace_id': None}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/shared/db/connection.py", line 161, in session
etradie-engine  |     await session.commit()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 1011, in commit
etradie-engine  |     await greenlet_spawn(self.sync_session.commit)
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 190, in greenlet_spawn
etradie-engine  |     result = context.switch(*args, **kwargs)
etradie-engine  |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2032, in commit
etradie-engine  |     trans.commit(_to_root=True)
etradie-engine  |   File "<string>", line 2, in commit
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/state_changes.py", line 103, in _go
etradie-engine  |     self._raise_for_prerequisite_state(fn.__name__, current_state)
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 973, in _raise_for_prerequisite_state
etradie-engine  |     raise sa_exc.PendingRollbackError(
etradie-engine  | sqlalchemy.exc.PendingRollbackError: This Session's transaction has be




e, None, None, None, None, None, None, \'{"confluences": 5, "fib_context": {"percentage": 0.5118, "zone": "EQUILIBRIUM", "is_in_ote": false, "nearest_level_name": "0.5"}}\', True, None, None, None, datetime.datetime(2026, 4, 17, 18, 6, 36, 253845, tzinfo=datetime.timezone.utc))]\n(Background on this error at: https://sqlalche.me/e/20/gkpj) (Background on this error at: https://sqlalche.me/e/20/7s2a)'}
etradie-engine  | Traceback (most recent call last):
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 330, in analyze
etradie-engine  |     await self._persist_all_results(
etradie-engine  |   File "/app/src/engine/ta/orchestrator.py", line 1072, in _persist_all_results
etradie-engine  |     async with self._ta_uow_factory() as uow:
etradie-engine  |                ^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/app/src/engine/ta/storage/uow.py", line 49, in __aexit__
etradie-engine  |     await self._ctx.__aexit__(exc_type, exc_val, exc_tb)
etradie-engine  |   File "/usr/local/lib/python3.12/contextlib.py", line 217, in __aexit__
etradie-engine  |     await anext(self.gen)
etradie-engine  |   File "/app/src/engine/shared/db/connection.py", line 161, in session
etradie-engine  |     await session.commit()
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 1011, in commit
etradie-engine  |     await greenlet_spawn(self.sync_session.commit)
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/util/_concurrency_py3k.py", line 190, in greenlet_spawn
etradie-engine  |     result = context.switch(*args, **kwargs)
etradie-engine  |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 2032, in commit
etradie-engine  |     trans.commit(_to_root=True)
etradie-engine  |   File "<string>", line 2, in commit
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/state_changes.py", line 103, in _go
etradie-engine  |     self._raise_for_prerequisite_state(fn.__name__, current_state)
etradie-engine  |   File "/usr/local/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 973, in _raise_for_prerequisite_state
etradie-engine  |     raise sa_exc.PendingRollbackError(
etradie-engine  | sqlalchemy.exc.PendingRollbackError: This Session's transaction has been rolled back due to a previous exception during flush. To begin a new transaction with this Session, first issue Session.rollback(). Original exception was: (sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) <class 'asyncpg.exceptions.NotNullViolationError'>: null value in column "take_profit" of relation