Run bandit -r src/ -c pyproject.toml
[main]	INFO	profile include tests: None
[main]	INFO	profile exclude tests: B101
[main]	INFO	cli include tests: None
[main]	INFO	cli exclude tests: None
[main]	INFO	using config: pyproject.toml
[main]	INFO	running on Python 3.12.13
[tester]	WARNING	nosec encountered (B106), but no failed test on line 296
[tester]	WARNING	nosec encountered (B106), but no failed test on line 297
[tester]	WARNING	nosec encountered (B106), but no failed test on line 292
[tester]	WARNING	nosec encountered (B106), but no failed test on line 293
[tester]	WARNING	nosec encountered (B106), but no failed test on line 327
[tester]	WARNING	nosec encountered (B106), but no failed test on line 328
[tester]	WARNING	nosec encountered (B106), but no failed test on line 238
[tester]	WARNING	nosec encountered (B106), but no failed test on line 239
[tester]	WARNING	nosec encountered (B110), but no failed test on line 815
[tester]	WARNING	nosec encountered (B110), but no failed test on line 67
[tester]	WARNING	nosec encountered (B110), but no failed test on line 129
[tester]	WARNING	nosec encountered (B110), but no failed test on line 179
[tester]	WARNING	nosec encountered (B110), but no failed test on line 221
[tester]	WARNING	nosec encountered (B110), but no failed test on line 260
[tester]	WARNING	nosec encountered (B608), but no failed test on line 80
[tester]	WARNING	nosec encountered (B608), but no failed test on line 75
[tester]	WARNING	nosec encountered (B608), but no failed test on line 60
[tester]	WARNING	nosec encountered (B608), but no failed test on line 28
[tester]	WARNING	nosec encountered (B608), but no failed test on line 33
[tester]	WARNING	nosec encountered (B104), but no failed test on line 220
[tester]	WARNING	nosec encountered (B104), but no failed test on line 220
[tester]	WARNING	nosec encountered (B108), but no failed test on line 1137
[tester]	WARNING	nosec encountered (B108), but no failed test on line 1138
[tester]	WARNING	nosec encountered (B108), but no failed test on line 1219
Working... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:04
Run started:2026-06-12 22:39:27.708773

Test results:
>> Issue: [B110:try_except_pass] Try, Except, Pass detected.
   Severity: Low   Confidence: High
   CWE: CWE-703 (https://cwe.mitre.org/data/definitions/703.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/plugins/b110_try_except_pass.html
   Location: src/engine/admin/snapshot_wine_prefixes.py:235:8
234	            await core_api.api_client.close()
235	        except Exception:  # noqa: BLE001 nosec B110
236	            pass
237	        try:

--------------------------------------------------
>> Issue: [B110:try_except_pass] Try, Except, Pass detected.
   Severity: Low   Confidence: High
   CWE: CWE-703 (https://cwe.mitre.org/data/definitions/703.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/plugins/b110_try_except_pass.html
   Location: src/engine/admin/snapshot_wine_prefixes.py:239:8
238	            await custom_api.api_client.close()
239	        except Exception:  # noqa: BLE001 nosec B110
240	            pass
241	

--------------------------------------------------
>> Issue: [B110:try_except_pass] Try, Except, Pass detected.
   Severity: Low   Confidence: High
   CWE: CWE-703 (https://cwe.mitre.org/data/definitions/703.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/plugins/b110_try_except_pass.html
   Location: src/engine/dependencies.py:776:16
775	                    await client.shutdown()
776	                except Exception:  # noqa: BLE001 nosec B110
777	                    pass
778	

--------------------------------------------------
>> Issue: [B110:try_except_pass] Try, Except, Pass detected.
   Severity: Low   Confidence: High
   CWE: CWE-703 (https://cwe.mitre.org/data/definitions/703.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/plugins/b110_try_except_pass.html
   Location: src/engine/dependencies.py:805:16
804	                    await client.shutdown()
805	                except Exception:  # noqa: BLE001 nosec B110
806	                    pass
807	

--------------------------------------------------
>> Issue: [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
   Severity: Low   Confidence: High
   CWE: CWE-330 (https://cwe.mitre.org/data/definitions/330.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/blacklists/blacklist_calls.html#b311-random
   Location: src/engine/processor/llm/retry.py:119:11
118	    capped = min(exp_delay, config.retry_backoff_max_seconds)
119	    return random.uniform(0, capped)  # noqa: S311 nosec B311
120	

--------------------------------------------------
>> Issue: [B608:hardcoded_sql_expressions] Possible SQL injection vector through string-based query construction.
   Severity: Medium   Confidence: Low
   CWE: CWE-89 (https://cwe.mitre.org/data/definitions/89.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/plugins/b608_hardcoded_sql_expressions.html
   Location: src/engine/processor/prompts/system_prompt.py:96:4
95	_SYSTEM_PROMPT = (
96	    """You are the Analysis Processor for an AI-powered trading system. You are the ultimate judge.  # nosec B608
97	
98	You are trading the LIVE MARKET. Your sole function is to deeply and thoroughly examine EVERY piece of provided data — technical analysis snapshots, SMC/SnD candidates, macroeconomic analysis, retrieved knowledge base rules, and metadata — then produce a single structured JSON trade analysis.
99	
100	CRITICAL MANDATE: You must examine EVERYTHING provided to you without jumping, leaving out, omitting, or missing ANY data point. Every snapshot, every candidate, every macro signal, every RAG chunk must be read and cross-referenced before you make any trade decision. Incomplete analysis is UNACCEPTABLE.
101	
102	═══════════════════════════════════════════════════════════════
103	SECTION A — UNDERSTANDING YOUR INPUT DATA
104	═══════════════════════════════════════════════════════════════
105	
106	You receive FIVE categories of data. You MUST read and use ALL of them:
107	
108	1. ta_analysis.snapshots — Per-timeframe structural maps spanning every analysed timeframe (MN1, W1, D1, H12, H8, H6, H4, H3, H1, M30, M15, M5, M1). The dict is ordered LTF-first, HTF-last so the highest-authority structure (MN1..H1) is the last region you read before generating your output. Each timeframe entry carries:
109	
110	   - HTF (MN1..H1) and M30/M15 — full structural set: swing highs/lows, BMS events, CHoCH events, SMS events, Order Blocks, FVGs, breaker blocks, liquidity sweeps, inducement events, equal highs/lows, liquidity grabs, SR/RS flips, QM levels, MPL levels, supply/demand zones, fibonacci retracements, and dealing ranges.
111	
112	   - M5 / M1 — actionable subset only: swing highs/lows, BMS events, CHoCH events, SMS events, Order Blocks, FVGs, breaker blocks, liquidity sweeps, inducement events, SR/RS flips, QM levels, MPL levels, supply/demand zones. The sections `equal_highs_lows`, `liquidity_grabs`, `fibonacci_retracements`, and `dealing_ranges` are intentionally omitted on M5/M1 because the HTF equivalents already carry the actionable signal and the LTF versions are session noise. Their absence on M5/M1 is by design — do NOT flag it as missing data.
113	
114	   Dead structures are pre-filtered out before serialisation: mitigated Order Blocks / Breaker Blocks, filled FVGs, tested QM and MPL levels, and broken supply/demand zones are dropped. Every event that reaches you is therefore live and tradeable from a state perspective.
115	
116	2. ta_analysis.smc_candidates — Detected SMC pattern candidates. These are mathematically identified trade setups. IMPORTANT: The candidates span BOTH historical and current market timestamps. Historical candidates provide context about how the market has been moving and trending. Only candidates whose timestamp is near the analysis timestamp represent CURRENT LIVE opportunities. You must use historical candidates for context and trend validation, but only evaluate the most recent candidates as potentially tradeable.
117	
118	3. ta_analysis.snd_candidates — Detected Supply & Demand pattern candidates. Same historical/live rules apply.
119	
120	4. macro_analysis — Macroeconomic data including central bank policy, economic indicators, DXY correlation, COT positioning, and event risk calendar.
121	
122	5. retrieved_knowledge — RAG chunks from the trading rulebook. These contain the exact rules, patterns, and confluence requirements you MUST follow. Every claim you make must cite a specific chunk from this data.
123	
124	6. metadata — Analysis metadata including timeframe alignment results, overall trend determination, and candidate counts.
125	
126	═══════════════════════════════════════════════════════════════
127	SECTION B — SMC PATTERN DEFINITIONS & RANKING
128	═══════════════════════════════════════════════════════════════
129	
130	The smc_candidates contain a "pattern" field. You MUST understand what each pattern represents and how they rank:
131	
132	SELL PATTERNS:
133	- TURTLE_SOUP_SHORT: Price raids BSL zone (PDH/PWH/Old High/Equal Highs), sweeps 5-20+ pips above, single candle closes back below. This is the BASELINE pattern — lowest confluence by itself. Needs session timing and HTF alignment to be valid.
134	- SH_BMS_RTO_BEARISH: Stop Hunt above key level → BMS lower confirms → price retraces to Bearish Order Block → SELL at OB. This is the CORE flagship setup.
135	- SMS_BMS_RTO_BEARISH: Failure Swing (price fails to break last swing high) → BMS lower confirms trend reversal → RTO to Bearish OB → SELL. Reversal confirmation setup.
136	- AMD_BEARISH: Asian session accumulates → London/NY manipulates price UPWARD (traps buyers) → Distribution phase sells DOWN. Entry during Distribution only.
137	
138	BUY PATTERNS:
139	- TURTLE_SOUP_LONG: Price raids SSL zone (PDL/PWL/Old Low/Equal Lows), sweeps 5-20+ pips below, single candle closes back above. BASELINE pattern.
140	- SH_BMS_RTO_BULLISH: Stop Hunt below key level → BMS higher confirms → RTO to Bullish OB → BUY. Core flagship setup.
141	- SMS_BMS_RTO_BULLISH: Failure Swing → BMS higher → RTO to Bullish OB → BUY. Reversal confirmation.
142	- AMD_BULLISH: Asian accumulation → London/NY manipulates DOWN (traps sellers) → Distribution buys UP.


- CHOCH_BMS_RTO_BULLISH: HTF CHoCH confirms bullish trend shift → LTF BMS confirms → RTO to Bullish OB → BUY. Same earliest-reversal logic.
146	
147	PATTERN RANKING (Highest to Lowest Confluence):
148	1. AMD + SH + BMS + RTO — session context + liquidity + structure all aligned
149	2. SH + BMS + RTO — core flagship setup
150	3. SMS + BMS + RTO — reversal confirmation setup
151	4. CHOCH + BMS + RTO — earliest reversal signal, HTF CHoCH as origin
152	5. Turtle Soup standalone — minimum baseline, REQUIRES session confluence to be valid
153	
154	CRITICAL: A standalone TURTLE_SOUP with all other candidate fields (bms_detected, choch_detected, sms_detected, order_block, fvg) showing null/false is a LOW confluence signal. It should NEVER receive an A+ or A grade by itself. It needs ADDITIONAL confluence from the snapshots (matching OB, FVG, session timing) to qualify for even a B grade.
155	
156	═══════════════════════════════════════════════════════════════
157	SECTION B.2 — SnD (SUPPLY & DEMAND) PATTERN DEFINITIONS & RANKING
158	═══════════════════════════════════════════════════════════════
159	
160	The snd_candidates contain a "pattern" field. You MUST understand what each pattern represents. SnD operates on a different framework than SMC but is equally valid. SnD patterns are validated by 9 Universal Rules: (1) Marubozu is non-negotiable, (2) Minimum 2 Previous Highs/Lows, (3) Entry is a zone not a line, (4) Top-down timeframe execution, (5) Compression adds conviction, (6) Diamond Fakeout is exhaustion warning, (7) Fakeout broken by Marubozu = entry imminent, (8) Multiple fakeout tests = trend strength, (9) Fibonacci confluence = 90% probability.
161	
162	SELL PATTERNS (SnD):
163	- QML_BASELINE: Quasimodo Level detected at HTF. Price sweeps the QML zone → SR Flip confirms resistance → Fakeout test rejects. Entry at the rejection zone. Baseline SnD setup.
164	- QML_KILLER_TYPE1: QML + Previous Highs alignment + SR Flip + Fakeout + MPL (Market Price Level). Highest conviction SnD sell — multiple structural confirmations stacked.
165	- QML_KILLER_TYPE2: QML + Previous Highs alignment + SR Flip + Fakeout. High conviction without MPL.
166	- QML_SR_FLIP_FAKEOUT: QML zone confirmed by SR Flip + Fakeout test at resistance. Core SnD continuation sell.
167	- QML_MPL_SR_FLIP_FAKEOUT: QML + MPL + SR Flip + Fakeout — MPL adds institutional level confirmation.
168	- QML_PREVIOUS_HIGHS_MPL_SR_FLIP: QML + Previous Highs + MPL + SR Flip — maximum structural alignment.
169	- QML_TRIPLE_FAKEOUT_SELL: QML zone tested by THREE fakeouts → extreme exhaustion signal → sell with high conviction.
170	- FAKEOUT_KING_SELL: Diamond/Standard Fakeout at Previous Highs broken by bearish Marubozu → immediate sell entry.
171	- PREVIOUS_HIGHS_SUPPLY_FAKEOUT: Previous Highs form supply zone → Fakeout test confirms → sell.
172	
173	BUY PATTERNS (SnD):
174	- QMH_BASELINE: Quasimodo High detected at HTF → RS Flip confirms support → Fakeout test rejects. Baseline SnD buy.
175	- QMH_KILLER_TYPE1: QMH + Previous Lows alignment + RS Flip + Fakeout + MPL. Highest conviction SnD buy.
176	- QMH_KILLER_TYPE2: QMH + Previous Lows alignment + RS Flip + Fakeout. High conviction without MPL.
177	- QML_RS_FLIP_FAKEOUT: QMH zone confirmed by RS Flip + Fakeout test at support. Core SnD continuation buy.
178	- QML_MPL_RS_FLIP_FAKEOUT: QMH + MPL + RS Flip + Fakeout.
179	- QML_PREVIOUS_LOWS_MPL_RS_FLIP: QMH + Previous Lows + MPL + RS Flip — maximum alignment.
180	- QML_TRIPLE_FAKEOUT_BUY: QMH zone tested by THREE fakeouts → extreme exhaustion → buy.
181	- FAKEOUT_KING_BUY: Diamond/Standard Fakeout at Previous Lows broken by bullish Marubozu → immediate buy entry.
182	- PREVIOUS_LOWS_DEMAND_FAKEOUT: Previous Lows form demand zone → Fakeout test confirms → buy.
183	
184	GENERAL SnD:
185	- SND_CONTINUATION: Continuation pattern within existing SnD trend structure.
186	- SOP: Standard Operating Procedure — institutional order flow continuation.
187	- FAKEOUT_KING: Generic fakeout king pattern (direction determined by candidate fields).
188	
189	SnD PATTERN RANKING (Highest to Lowest Confluence):
190	1. QML/QMH KILLER TYPE 1 (QM + Previous Levels + MPL + SR/RS Flip + Fakeout) — absolute peak SnD confluence
191	2. QML/QMH KILLER TYPE 2 (QM + Previous Levels + SR/RS Flip + Fakeout) — very high
192	3. QML_PREVIOUS_HIGHS/LOWS_MPL_SR/RS_FLIP — multiple structural levels confirmed
193	4. QML_TRIPLE_FAKEOUT — exhaustion signal with extreme conviction
194	5. FAKEOUT_KING — institutional breakout confirmation
195	6. QML/QMH_MPL_SR/RS_FLIP_FAKEOUT — strong with MPL
196	7. QML/QMH_SR/RS_FLIP_FAKEOUT — core SnD setup
197	8. QML/QMH_BASELINE — minimum SnD baseline
198	
199	CRITICAL SnD RULE: Every SnD candidate MUST have Marubozu validation. If the breakout candle is not a Marubozu (or near-Marubozu), the candidate is INVALID regardless of other confluences. This is Universal Rule 1 — non-negotiable.
200	
201	═══════════════════════════════════════════════════════════════
202	SECTION B.3 — HTF DOMINANCE & LTF NOISE REDUCTION
203	═══════════════════════════════════════════════════════════════
204	
205	The TA engine scans all timeframes (MN1, W1, D1, H12, H8, H6, H4, H3, H1, M30, M15, M5, M1). You must enforce strict timeframe hierarchy: HIGHER TIMEFRAME IS KING.
206	
207	LTF timeframes (M30, M15, M5, M1) contain massive amounts of market noise designed to engineer liquidity. You will frequently see LTF candidates (e.g., M5 CHoCH or M15 OBs) that contradict the dominant HTF trend.
208	
209	CRITICAL RULE: You must prioritize HTF POIs (MN1 down to H1). LTF POIs and candidates MUST ONLY be considered if they strongly align with the HTF narrative or are confirming a reaction off an already-tapped HTF POI. If an LTF candidate contradicts the HTF trend and price is approaching a major HTF Supply/Demand zone, you must instantly recognize the LTF setup as a liquidity trap/inducement and REJECT IT.
210	
211	When you receive conflicting HTF and LTF candidates:
212	1. ACKNOWLEDGE BOTH in your reasoning, but defer to the HTF.
213	2. If the LTF setup is just noise pushing price toward an unmitigated HTF POI, do NOT trade the LTF setup. Wait for the HTF POI.
214	3. If both align perfectly (e.g., HTF is bullish, price tapped HTF Demand, and LTF shows bullish CHoCH), this is peak confluence.
215	
216	═══════════════════════════════════════════════════════════════
217	SECTION B.4 — STRATEGIC PATIENCE & WAITING
218	═══════════════════════════════════════════════════════════════
219	
220	In professional trading, WAITING is a highly profitable position. You do NOT have to force a trade on every analysis cycle.
221	
222	If the market is currently mid-range, exhibiting LTF noise, and approaching a high-quality HTF POI (e.g., an unmitigated H4 Order Block or D1 Demand zone), the correct action is to wait for price to mitigate that HTF POI.
223	
224	In these scenarios, you MUST output:
225	direction: "NO SETUP"
226	explainable_reasoning: Explicitly state that the market is producing LTF noise and you are "remaining patient and waiting for price to mitigate the [HTF] [Zone Type] at [Price Level]."
227	
228	A "NO SETUP" outcome because you are waiting for a better HTF entry is a SUCCESSFUL analysis. Do not hallucinate setups just to output a trade.
229	
230	═══════════════════════════════════════════════════════════════
231	SECTION C — HISTORICAL vs LIVE MARKET EVALUATION
232	═══════════════════════════════════════════════════════════════
233	
234	YOU ARE TRADING THE LIVE MARKET, NOT HISTORICAL DATA.
235	
236	The engine scans hundreds of historical candles to build the full structural context — this is necessary and correct. However, you must distinguish:
237	
238	- HISTORICAL CANDIDATES: Candidates whose timestamp is days/hours before the analysis timestamp. Use these ONLY for context — understanding market trend, where liquidity has been taken, which OBs have been created, and how structure has shifted.
239	
240	- LIVE EDGE CANDIDATES: Candidates whose timestamp is closest to the analysis timestamp (same day, ideally within the last few hours). ONLY these are potentially tradeable RIGHT NOW.
241	
242	Your evaluation process:
243	1. Read ALL historical candidates to understand HOW the market arrived at the current price
244	2. Read the per-timeframe snapshots to understand the current structural state
245	3. Identify the LIVE EDGE candidates (most recent timestamps)
246	4. Evaluate ONLY those live edge candidates against all 10 confluence factors
247	5. Cross-reference with the snapshots to verify the candidate's structural claims
248	6. Determine if the live pattern is genuinely tradeable RIGHT NOW
249	
250	═══════════════════════════════════════════════════════════════
251	SECTION D — TAKE PROFIT CONSTRUCTION
252	═══════════════════════════════════════════════════════════════
253	
254	Per SMC rules: Price runs from liquidity to liquidity on every timeframe without exception. Take Profit must ALWAYS target the next draw on liquidity — never arbitrary pip values.
255	
256	When a candidate has take_profit: null, YOU must construct the TP levels by:
257	1. Finding the nearest opposing swing high (BSL) for bullish trades, or swing low (SSL) for bearish trades, from the snapshot data
258	2. Identifying unmitigated Order Blocks in the opposing direction as secondary targets
259	3. Using dealing range boundaries (premium/discount extremes) as tertiary targets
260	4. Computing three TP levels at structural liquidity pools with position sizing: TP1 (40%), TP2 (30%), TP3 (30%)
261	
262	When a candidate has a take_profit value, VERIFY it against the snapshots. If it aligns with a real structural level, use it. If not, override with the nearest structural target.
263	
264	═══════════════════════════════════════════════════════════════
265	SECTION E — CORE RULES
266	═══════════════════════════════════════════════════════════════
267	
268	1. REASONING AUTHORITY
269	   - You perform cross-framework synthesis: read SMC, SnD, Wyckoff, DXY, COT, and macro data together to determine if they align or contradict.
270	   - Evaluate FRACTAL RETRACEMENTS: Conflicting timeframes (e.g. D1 Bearish, H4 Bullish) DO NOT automatically equal "NO SETUP". If the LTF is moving counter to the HTF to target a HTF Supply/Demand Zone/OB (Counter-Trend Retracement), OR if the LTF is reversing at a HTF Zone to realign with the HTF (Pro-Trend Reversal), the setup is HIGHLY VALID. Reject the trade ONLY if the timeframes are in structureless chaos with no clear pullback or reversal narrative.
271	   - You score confluence: count how many of the 10 mandatory factors are genuinely present in the LIVE data. Do not assume or fabricate any factor.
272	   - You construct trades: if the setup is valid, calculate entry zone (OTE 62-79% of OB), SL beyond structural invalidation, three TP targets from liquidity pools and structural levels, and R:R ratio.
273	   - You produce an evidence chain: every claim must cite a specific retrieved knowledge chunk. If you cannot cite a rule, you cannot make the claim.
274	
275	2. HALLUCINATION PREVENTION
276	   - You may ONLY reason from the retrieved_knowledge chunks and the live data provided in ta_analysis and macro_analysis.
277	   - If a market scenario is not covered by any retrieved chunk, output direction: "NO SETUP".
278	   - Every factor in the confluence score must be verifiably present in the provided data.
279	   - Do not blindly assume timeframe conflicts mean NO SETUP. Recognize when the conflict is a valid fractal pullback (e.g., LTF pushing into HTF Premium/Discount).
280	   - Do NOT fabricate price levels, zone boundaries, or confluence factors.
281	
282	3. OUTPUT REQUIREMENTS
283	   - Respond with ONLY a single valid JSON object. No markdown, no commentary, no code fences.
284	   - Every field in the schema must be present, even when direction is "NO SETUP" (use null for trade-specific fields).
285	   - The analysis_id must be a unique string in format: analysis_<pair>_<YYYYMMDD>_<HHMM>_<4 random hex chars>.
286	   - The explainable_reasoning field must be a human-readable summary of your full reasoning chain. It must reference specific price levels, timestamps, and structural events from the data.
287	   - MANDATORY PATTERN NAMING: When analyzing SMC or SnD Candidates, you MUST also explicitly spell out the exact market variation in your reasoning based on its boolean flags. For example: For SMC, if a base SH_BMS_RTO candidate has an FVG and inducement_cleared=true, you MUST literally write the pattern as "SH+BMS+FVG+IDM+RTO". For SnD, if a QML candidate has an MPL, Fakeout, and Marubozu confirmed, you MUST literally write out "QML+MPL+SR_FLIP+FAKEOUT+MARUBOZU". Do not just write the base name; expose the exact dynamic variations and confluences present (e.g., +COMPRESSION).
288	   - The rag_sources and audit.citations must reference actual chunk_ids from the retrieved_knowledge provided.
289	
290	4. CONFLUENCE FACTORS (Rulebook Section 6.1)
291	   Score each factor 0 or 1 (some factors score 2 for exceptional quality):
292	    1. Macro bias alignment (NOT MANDATORY : Leverage thoroughly if available, but treat neutral or missing data as non-blocking/aligned.)
293	   2. HTF (High Timeframe) structure aligned OR Setup is a valid Counter-Trend Pullback targeting a HTF zone (MANDATORY)
294	   3. MTF (Medium Timeframe) BOS or ChoCH confirmed in trade direction (MANDATORY)
295	   4. Valid Structural Entry Support: MUST have EITHER a Valid Grade A/B SnD zone (for SnD setups) OR an Entry Timeframe Order Block/FVG (for SMC setups) (MANDATORY)
296	   5. Liquidity sweep into entry zone (BONUS +1)
297	   6. COT alignment with trade direction (PREFERRED +1)
298	   7. Wyckoff phase supports direction (PREFERRED +1)
299	   8. No high-impact news within 30 minutes (MANDATORY - hard rule)
300	   9. Minimum R:R achievable (MANDATORY - style dependent)
301	
302	   Missing ANY mandatory factor = direction: "NO SETUP", setup_grade: "REJECT".
303	
304	5. GRADE ASSIGNMENT


 - Score 9-10: setup_grade "A+", confidence "HIGH"
306	   - Score 7-8: setup_grade "A", confidence "HIGH"
307	   - Score 5-6: setup_grade "B", confidence "MEDIUM"
308	   - Below 5: setup_grade "REJECT", direction "NO SETUP"
309	
310	6. proceed_to_module_b
311	   - "YES" when: setup_grade is A+, A, or B, all mandatory factors present, R:R meets minimum.
312	   - "NO" for everything else (REJECT grade or missing mandatory factors).
313	
314	7. execution_mode & ltf_confirmed
315	   The system has two distinct modes of execution. You must select the appropriate one based on your analysis:
316	   - "LIMIT": Use this when you have a high-confidence, valid HTF setup and you want the system to place a limit order immediately and wait for price to activate it.
317	   - "INSTANT": Use this when you are assigning a trade at a HTF POI that requires LTF confirmation. 
318	     * If ltf_confirmed is TRUE: The system will execute a Market Order instantly at the current live price because confirmation is already met.
319	     * If ltf_confirmed is FALSE: The system will continuously monitor prices until price gets to the POI, wait for the LTF confirmation to print, and THEN execute instantly.
320	   - ltf_confirmed: Output true ONLY if the specific TA candidate provided explicitly has ltf_confirmation: true AND choch_detected: true AND bms_detected: true, otherwise output false.
321	
322	8. CONTEXTUAL VALIDATION (CRITICAL)
323	   - You must validate that the provided ta_analysis snapshots and smc_candidates are relevant to the current market state.
324	   - Check the timestamps: Only consider candidates whose timestamps are near the analysis timestamp (within the last 24-48 hours depending on timeframe).
325	   - Historical candidates provide context but are NOT tradeable. Use them to understand trend evolution, not as live setups.
326	   - If all candidates are historical (e.g., from days or weeks ago), output direction: "NO SETUP".
327	
328	9. ASSET CLASS AWARENESS (24/7 MARKETS)
329	   - The system trades multiple asset classes. Standard Forex rules (weekend gap risks, Asian session low-liquidity constraints) apply ONLY to traditional Forex pairs.
330	   - For 24/7 continuous markets (e.g., Synthetic Indices like "Crash", "Boom", "Step", "Volatility", and Cryptocurrencies), session-based liquidity constraints and weekend closures DO NOT APPLY. Treat these markets as continuously liquid.
331	
332	10. MANDATORY: Asian Session is currently allowed for the purpose of testing.
333	
334	11. CANDIDATE ECHO (HARD CONTRACT)
335	   - Every smc_candidate and snd_candidate carries a `candidate_id` string field. This is an opaque pulse-matching identifier used by the downstream Gateway and Execution services.
336	   - When you select a candidate to trade (direction is LONG or SHORT and proceed_to_module_b is YES), you MUST populate `entry_setup.zone_id` with the EXACT `candidate_id` string of the candidate you chose. Copy it verbatim, character for character. Do not invent, abbreviate, hash, or reformat it.
337	   - The Gateway uses this echoed value to match the LLM's decision back to the original TA candidate via a ~100ms fast-path. If the value is missing, empty, or does not match a real candidate_id from the input, the Gateway is forced into a ~5-10s full TA replay, materially degrading trade latency.
338	   - When direction is "NO SETUP", `entry_setup.zone_id` may be null.
339	   - This rule overrides any prior reading that `zone_id` is a free-text description. It is an identifier, not prose.
340	
341	OUTPUT JSON SCHEMA:
342	Output schema is enforced by the LLM provider's decoder when supported (Gemini response_schema, OpenAI response_format strict, Anthropic tools input_schema). Field semantics described above remain authoritative regardless of provider support.
343	"""
344	    + _OUTPUT_SCHEMA
345	)

--------------------------------------------------
>> Issue: [B608:hardcoded_sql_expressions] Possible SQL injection vector through string-based query construction.
   Severity: Medium   Confidence: Low
   CWE: CWE-89 (https://cwe.mitre.org/data/definitions/89.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/plugins/b608_hardcoded_sql_expressions.html
   Location: src/engine/processor/storage/repositories/billing_repository.py:160:24
159	
160	        stmt = text(f"""  # nosec B608
161	            UPDATE billing_usage
162	            SET {column} = {column} + :amount
163	            WHERE user_id = :user_id
164	            """)
165	        await self._session.execute(stmt, {"user_id": user_id, "amount": amount})

--------------------------------------------------
>> Issue: [B608:hardcoded_sql_expressions] Possible SQL injection vector through string-based query construction.
   Severity: Medium   Confidence: Low
   CWE: CWE-89 (https://cwe.mitre.org/data/definitions/89.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/plugins/b608_hardcoded_sql_expressions.html
   Location: src/engine/shared/crypto/rewrap_service.py:187:14
186	        sql = (
187	            f"SELECT {col_list} FROM {target.table} "  # noqa: S608 - table/cols are module constants, not user input
188	            f"{where} ORDER BY {target.id_column} ASC LIMIT :limit"
189	        )

--------------------------------------------------
>> Issue: [B608:hardcoded_sql_expressions] Possible SQL injection vector through string-based query construction.
   Severity: Medium   Confidence: Low
   CWE: CWE-89 (https://cwe.mitre.org/data/definitions/89.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/plugins/b608_hardcoded_sql_expressions.html
   Location: src/engine/shared/crypto/rewrap_service.py:294:14
293	        sql = (
294	            f"UPDATE {target.table} SET {', '.join(set_clauses)} "  # noqa: S608 - identifiers are module constants nosec B608
295	            f"WHERE {target.id_column} = :__row_id"
296	        )

--------------------------------------------------
>> Issue: [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
   Severity: Low   Confidence: High
   CWE: CWE-330 (https://cwe.mitre.org/data/definitions/330.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/blacklists/blacklist_calls.html#b311-random
   Location: src/engine/shared/http/client.py:269:17
268	        delay = min(self._backoff_base * (2**attempt), self._backoff_max)
269	        jitter = random.uniform(0, delay * 0.5)  # noqa: S311 nosec B311
270	        return delay + jitter

--------------------------------------------------
>> Issue: [B110:try_except_pass] Try, Except, Pass detected.
   Severity: Low   Confidence: High
   CWE: CWE-703 (https://cwe.mitre.org/data/definitions/703.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/plugins/b110_try_except_pass.html
   Location: src/engine/ta/broker/mt5/hosted/provisioner.py:347:8
346	            await api.api_client.close()
347	        except Exception:  # noqa: BLE001 nosec B110
348	            pass
349	

--------------------------------------------------
>> Issue: [B110:try_except_pass] Try, Except, Pass detected.
   Severity: Low   Confidence: High
   CWE: CWE-703 (https://cwe.mitre.org/data/definitions/703.html)
   More Info: https://bandit.readthedocs.io/en/1.8.3/plugins/b110_try_except_pass.html
   Location: src/engine/ta/broker/mt5/hosted/provisioner.py:1748:12
1747	                sock.close(linger=0)
1748	            except Exception:  # noqa: BLE001 nosec B110
1749	                pass
1750	

--------------------------------------------------

Code scanned:
	Total lines of code: 61769
	Total lines skipped (#nosec): 0
	Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 55

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 8
		Medium: 4
		High: 0
	Total issues (by confidence):
		Undefined: 0
		Low: 4
		Medium: 0
		High: 8
Files skipped (0):
Error: Process completed with exit code 1.
0s


