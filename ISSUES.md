

E501 Line too long (293 > 120)
   --> src/engine/processor/prompts/system_prompt.py:98:121
    |
 96 | …
 97 | …
 98 | …a — technical analysis snapshots, SMC/SnD candidates, macroeconomic analysis, retrieved knowledge base rules, and metadata — then produce a single structured JSON trade analysis.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 99 | …
100 | …Y data point. Every snapshot, every candidate, every macro signal, every RAG chunk must be read and cross-referenced before you make any trade decision. Incomplete analysis is UNACCEP…
    |

E501 Line too long (304 > 120)
   --> src/engine/processor/prompts/system_prompt.py:100:121
    |
 98 | …a — technical analysis snapshots, SMC/SnD candidates, macroeconomic analysis, retrieved knowledge base rules, and metadata — then produce a single structured JSON trade analysis.
 99 | …
100 | …Y data point. Every snapshot, every candidate, every macro signal, every RAG chunk must be read and cross-referenced before you make any trade decision. Incomplete analysis is UNACCEPTABLE.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
101 | …
102 | …
    |

E501 Line too long (322 > 120)
   --> src/engine/processor/prompts/system_prompt.py:108:121
    |
106 | …
107 | …
108 | …6, H4, H3, H1, M30, M15, M5, M1). The dict is ordered LTF-first, HTF-last so the highest-authority structure (MN1..H1) is the last region you read before generating your output. Each timeframe entry carries:
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
109 | …
110 | … Blocks, FVGs, breaker blocks, liquidity sweeps, inducement events, equal highs/lows, liquidity grabs, SR/RS flips, QM levels, MPL levels, supply/demand zones, fibonacci retracements, and dealing ranges.
    |

E501 Line too long (318 > 120)
   --> src/engine/processor/prompts/system_prompt.py:110:121
    |
108 | …6, H4, H3, H1, M30, M15, M5, M1). The dict is ordered LTF-first, HTF-last so the highest-authority structure (MN1..H1) is the last region you read before generating your output. Each timeframe entry carries:
109 | …
110 | … Blocks, FVGs, breaker blocks, liquidity sweeps, inducement events, equal highs/lows, liquidity grabs, SR/RS flips, QM levels, MPL levels, supply/demand zones, fibonacci retracements, and dealing ranges.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
111 | …
112 | …breaker blocks, liquidity sweeps, inducement events, SR/RS flips, QM levels, MPL levels, supply/demand zones. The sections `equal_highs_lows`, `liquidity_grabs`, `fibonacci_retracements`, and `dealing_ranges`…
    |

E501 Line too long (532 > 120)
   --> src/engine/processor/prompts/system_prompt.py:112:121
    |
110 | … Blocks, FVGs, breaker blocks, liquidity sweeps, inducement events, equal highs/lows, liquidity grabs, SR/RS flips, QM levels, MPL levels, supply/demand zones, fibonacci retracements, and dealing ranges.
111 | …
112 | …breaker blocks, liquidity sweeps, inducement events, SR/RS flips, QM levels, MPL levels, supply/demand zones. The sections `equal_highs_lows`, `liquidity_grabs`, `fibonacci_retracements`, and `dealing_ranges` are intentionally omitted on M5/M1 because the HTF equivalents already carry the actionable signal and the LTF versions are session noise. Their absence on M5/M1 is by design — do NOT flag it as missing data.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
113 | …
114 | … tested QM and MPL levels, and broken supply/demand zones are dropped. Every event that reaches you is therefore live and tradeable from a state perspective.
    |

E501 Line too long (272 > 120)
   --> src/engine/processor/prompts/system_prompt.py:114:121
    |
112 | …breaker blocks, liquidity sweeps, inducement events, SR/RS flips, QM levels, MPL levels, supply/demand zones. The sections `equal_highs_lows`, `liquidity_grabs`, …
113 | …
114 | … tested QM and MPL levels, and broken supply/demand zones are dropped. Every event that reaches you is therefore live and tradeable from a state perspective.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
115 | …
116 | …IMPORTANT: The candidates span BOTH historical and current market timestamps. Historical candidates provide context about how the market has been moving and trend…
    |

E501 Line too long (522 > 120)
   --> src/engine/processor/prompts/system_prompt.py:116:121
    |
114 | … tested QM and MPL levels, and broken supply/demand zones are dropped. Every event that reaches you is therefore live and tradeable from a state perspective.
115 | …
116 | …IMPORTANT: The candidates span BOTH historical and current market timestamps. Historical candidates provide context about how the market has been moving and trending. Only candidates whose timestamp is near the analysis timestamp represent CURRENT LIVE opportunities. You must use historical candidates for context and trend validation, but only evaluate the most recent candidates as potentially tradeable.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
117 | …
118 | …
    |

E501 Line too long (149 > 120)
   --> src/engine/processor/prompts/system_prompt.py:120:121
    |
118 | …idates. Same historical/live rules apply.
119 | …
120 | … economic indicators, DXY correlation, COT positioning, and event risk calendar.
    |                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
121 | …
122 | …contain the exact rules, patterns, and confluence requirements you MUST follow. Every claim you make must cite a specific chunk from…
    |

E501 Line too long (212 > 120)
   --> src/engine/processor/prompts/system_prompt.py:122:121
    |
120 | …lation, COT positioning, and event risk calendar.
121 | …
122 | …ns, and confluence requirements you MUST follow. Every claim you make must cite a specific chunk from this data.
    |                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
123 | …
124 | …and candidate counts.
    |

E501 Line too long (121 > 120)
   --> src/engine/processor/prompts/system_prompt.py:124:121
    |
122 | 5. retrieved_knowledge — RAG chunks from the trading rulebook. These contain the exact rules, patterns, and confluence requirements y…
123 |
124 | 6. metadata — Analysis metadata including timeframe alignment results, overall trend determination, and candidate counts.
    |                                                                                                                         ^
125 |
126 | ═══════════════════════════════════════════════════════════════
    |

E501 Line too long (243 > 120)
   --> src/engine/processor/prompts/system_prompt.py:133:121
    |
132 | …
133 | …oses back below. This is the BASELINE pattern — lowest confluence by itself. Needs session timing and HTF alignment to be valid.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
134 | … at OB. This is the CORE flagship setup.
135 | …TO to Bearish OB → SELL. Reversal confirmation setup.
    |

E501 Line too long (155 > 120)
   --> src/engine/processor/prompts/system_prompt.py:134:121
    |
132 | …
133 | …, sweeps 5-20+ pips above, single candle closes back below. This is the BASELINE pattern — lowest confluence by itself. Needs sessio…
134 | …rice retraces to Bearish Order Block → SELL at OB. This is the CORE flagship setup.
    |                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
135 | …gh) → BMS lower confirms trend reversal → RTO to Bearish OB → SELL. Reversal confirmation setup.
136 | …PWARD (traps buyers) → Distribution phase sells DOWN. Entry during Distribution only.
    |

E501 Line too long (168 > 120)
   --> src/engine/processor/prompts/system_prompt.py:135:121
    |
133 | …ps 5-20+ pips above, single candle closes back below. This is the BASELINE pattern — lowest confluence by itself. Needs session timi…
134 | …etraces to Bearish Order Block → SELL at OB. This is the CORE flagship setup.
135 | …BMS lower confirms trend reversal → RTO to Bearish OB → SELL. Reversal confirmation setup.
    |                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
136 | …(traps buyers) → Distribution phase sells DOWN. Entry during Distribution only.
    |

E501 Line too long (157 > 120)
   --> src/engine/processor/prompts/system_prompt.py:136:121
    |
134 | …ice retraces to Bearish Order Block → SELL at OB. This is the CORE flagship setup.
135 | …h) → BMS lower confirms trend reversal → RTO to Bearish OB → SELL. Reversal confirmation setup.
136 | …WARD (traps buyers) → Distribution phase sells DOWN. Entry during Distribution only.
    |                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
137 | …
138 | …
    |

E501 Line too long (146 > 120)
   --> src/engine/processor/prompts/system_prompt.py:139:121
    |
138 | …
139 | …s), sweeps 5-20+ pips below, single candle closes back above. BASELINE pattern.
    |                                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^
140 | …ms → RTO to Bullish OB → BUY. Core flagship setup.
141 | …OB → BUY. Reversal confirmation.
    |

E501 Line too long (333 > 120)
   --> src/engine/processor/prompts/system_prompt.py:144:121
    |
142 | …
143 | …
144 | …TO to Bearish OB → SELL. This is the earliest reversal entry — CHoCH happens BEFORE SMS. The OB may be unmitigated and awaiting price return (ltf_confirmation=false means the execution engine will monitor for the RTO).
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
145 | …earliest-reversal logic.
    |

E501 Line too long (139 > 120)
   --> src/engine/processor/prompts/system_prompt.py:145:121
    |
144 | …nfirms trend shift → LTF BMS confirms direction → RTO to Bearish OB → SELL. This is the earliest reversal entry — CHoCH happens BEFO…
145 | …→ LTF BMS confirms → RTO to Bullish OB → BUY. Same earliest-reversal logic.
    |                                                          ^^^^^^^^^^^^^^^^^^^
146 | …
147 | …
    |

E501 Line too long (344 > 120)
   --> src/engine/processor/prompts/system_prompt.py:154:121
    |
152 | …
153 | …
154 | …er_block, fvg) showing null/false is a LOW confluence signal. It should NEVER receive an A+ or A grade by itself. It needs ADDITIONAL confluence from the snapshots (matching OB, FVG, session timing) to qualify for even a B grade.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
155 | …
156 | …
    |

E501 Line too long (560 > 120)
   --> src/engine/processor/prompts/system_prompt.py:160:121
    |
158 | …
159 | …
160 | …ifferent framework than SMC but is equally valid. SnD patterns are validated by 9 Universal Rules: (1) Marubozu is non-negotiable, (2) Minimum 2 Previous Highs/Lows, (3) Entry is a zone not a line, (4) Top-down timeframe execution, (5) Compression adds conviction, (6) Diamond Fakeout is exhaustion warning, (7) Fakeout broken by Marubozu = entry imminent, (8) Multiple fakeout tests = trend strength, (9) Fibonacci confluence = 90% probability.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
161 | …
162 | …
    |

E501 Line too long (177 > 120)
   --> src/engine/processor/prompts/system_prompt.py:163:121
    |
162 | …
163 | …p confirms resistance → Fakeout test rejects. Entry at the rejection zone. Baseline SnD setup.
    |                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
164 | …t Price Level). Highest conviction SnD sell — multiple structural confirmations stacked.
165 | …tion without MPL.
    |

E501 Line too long (171 > 120)
   --> src/engine/processor/prompts/system_prompt.py:164:121
    |
162 | …
163 | …Flip confirms resistance → Fakeout test rejects. Entry at the rejection zone. Baseline SnD setup.
164 | …rket Price Level). Highest conviction SnD sell — multiple structural confirmations stacked.
    |                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
165 | …viction without MPL.
166 | …e. Core SnD continuation sell.
    |

E501 Line too long (231 > 120)
   --> src/engine/processor/prompts/system_prompt.py:199:121
    |
197 | …
198 | …
199 | … (or near-Marubozu), the candidate is INVALID regardless of other confluences. This is Universal Rule 1 — non-negotiable.
    |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
200 | …
201 | …
    |

E501 Line too long (163 > 120)
   --> src/engine/processor/prompts/system_prompt.py:205:121
    |
203 | …
204 | …
205 | …0, M15, M5, M1). You must enforce strict timeframe hierarchy: HIGHER TIMEFRAME IS KING.
    |                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
206 | …
207 | …signed to engineer liquidity. You will frequently see LTF candidates (e.g., M5 CHoCH or M15 OBs) that contradict the dominant HTF tr…
    |

E501 Line too long (212 > 120)
   --> src/engine/processor/prompts/system_prompt.py:207:121
    |
205 | …t enforce strict timeframe hierarchy: HIGHER TIMEFRAME IS KING.
206 | …
207 | …dity. You will frequently see LTF candidates (e.g., M5 CHoCH or M15 OBs) that contradict the dominant HTF trend.
    |                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
208 | …
209 | …onsidered if they strongly align with the HTF narrative or are confirming a reaction off an already-tapped HTF POI. If an LTF candid…
    |

E501 Line too long (407 > 120)
   --> src/engine/processor/prompts/system_prompt.py:209:121
    |
207 | …frequently see LTF candidates (e.g., M5 CHoCH or M15 OBs) that contradict the dominant HTF trend.
208 | …
209 | …ey strongly align with the HTF narrative or are confirming a reaction off an already-tapped HTF POI. If an LTF candidate contradicts the HTF trend and price is approaching a major HTF Supply/Demand zone, you must instantly recognize the LTF setup as a liquidity trap/inducement and REJECT IT.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
210 | …
211 | …
    |

E501 Line too long (128 > 120)
   --> src/engine/processor/prompts/system_prompt.py:213:121
    |
211 | When you receive conflicting HTF and LTF candidates:
212 | 1. ACKNOWLEDGE BOTH in your reasoning, but defer to the HTF.
213 | 2. If the LTF setup is just noise pushing price toward an unmitigated HTF POI, do NOT trade the LTF setup. Wait for the HTF POI.
    |                                                                                                                         ^^^^^^^^
214 | 3. If both align perfectly (e.g., HTF is bullish, price tapped HTF Demand, and LTF shows bullish CHoCH), this is peak confluence.
    |

E501 Line too long (129 > 120)
   --> src/engine/processor/prompts/system_prompt.py:214:121
    |
212 | ….
213 | …nmitigated HTF POI, do NOT trade the LTF setup. Wait for the HTF POI.
214 | …ped HTF Demand, and LTF shows bullish CHoCH), this is peak confluence.
    |                                                               ^^^^^^^^^
215 | …
216 | …════
    |

E501 Line too long (123 > 120)
   --> src/engine/processor/prompts/system_prompt.py:220:121
    |
218 | ═══════════════════════════════════════════════════════════════
219 |
220 | In professional trading, WAITING is a highly profitable position. You do NOT have to force a trade on every analysis cycle.
    |                                                                                                                         ^^^
221 |
222 | If the market is currently mid-range, exhibiting LTF noise, and approaching a high-quality HTF POI (e.g., an unmitigated H4 Order Blo…
    |

E501 Line too long (221 > 120)
   --> src/engine/processor/prompts/system_prompt.py:222:121
    |
220 | …ry analysis cycle.
221 | …
222 | … an unmitigated H4 Order Block or D1 Demand zone), the correct action is to wait for price to mitigate that HTF POI.
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
223 | …
224 | …
    |

E501 Line too long (184 > 120)
   --> src/engine/processor/prompts/system_prompt.py:226:121
    |
224 | …
225 | …
226 | … are "remaining patient and waiting for price to mitigate the [HTF] [Zone Type] at [Price Level]."
    |                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
227 | …
228 | …alysis. Do not hallucinate setups just to output a trade.
    |

E501 Line too long (143 > 120)
   --> src/engine/processor/prompts/system_prompt.py:228:121
    |
226 | …ng LTF noise and you are "remaining patient and waiting for price to mitigate the [HTF] [Zone Type] at [Price Level]."
227 | …
228 | …y is a SUCCESSFUL analysis. Do not hallucinate setups just to output a trade.
    |                                                        ^^^^^^^^^^^^^^^^^^^^^^^
229 | …
230 | …
    |

E501 Line too long (148 > 120)
   --> src/engine/processor/prompts/system_prompt.py:236:121
    |
234 | …
235 | …
236 | …ructural context — this is necessary and correct. However, you must distinguish:
    |                                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
237 | …
238 | …fore the analysis timestamp. Use these ONLY for context — understanding market trend, where liquidity has been taken, which OBs have…
    |

E501 Line too long (245 > 120)
   --> src/engine/processor/prompts/system_prompt.py:238:121
    |
236 | …t. However, you must distinguish:
237 | …
238 | … context — understanding market trend, where liquidity has been taken, which OBs have been created, and how structure has shifted.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
239 | …
240 | …he last few hours). ONLY these are potentially tradeable RIGHT NOW.
    |

E501 Line too long (182 > 120)
   --> src/engine/processor/prompts/system_prompt.py:240:121
    |
238 | … timestamp. Use these ONLY for context — understanding market trend, where liquidity has been taken, which OBs have been created, an…
239 | …
240 | …mp (same day, ideally within the last few hours). ONLY these are potentially tradeable RIGHT NOW.
    |                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
241 | …
242 | …
    |

E501 Line too long (179 > 120)
   --> src/engine/processor/prompts/system_prompt.py:254:121
    |
252 | …
253 | …
254 | …eption. Take Profit must ALWAYS target the next draw on liquidity — never arbitrary pip values.
    |                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
255 | …
256 | …
    |

E501 Line too long (130 > 120)
   --> src/engine/processor/prompts/system_prompt.py:257:121
    |
256 | When a candidate has take_profit: null, YOU must construct the TP levels by:
257 | 1. Finding the nearest opposing swing high (BSL) for bullish trades, or swing low (SSL) for bearish trades, from the snapshot data
    |                                                                                                                         ^^^^^^^^^^
258 | 2. Identifying unmitigated Order Blocks in the opposing direction as secondary targets
259 | 3. Using dealing range boundaries (premium/discount extremes) as tertiary targets
    |

E501 Line too long (178 > 120)
   --> src/engine/processor/prompts/system_prompt.py:262:121
    |
260 | …1 (40%), TP2 (30%), TP3 (30%)
261 | …
262 | …igns with a real structural level, use it. If not, override with the nearest structural target.
    |                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
263 | …
264 | …
    |

E501 Line too long (143 > 120)
   --> src/engine/processor/prompts/system_prompt.py:269:121
    |
268 | …
269 | …, DXY, COT, and macro data together to determine if they align or contradict.
    |                                                        ^^^^^^^^^^^^^^^^^^^^^^^
270 | …1 Bearish, H4 Bullish) DO NOT automatically equal "NO SETUP". If the LTF is moving counter to the HTF to target a HTF Supply/Demand …
271 | …ors are genuinely present in the LIVE data. Do not assume or fabricate any factor.
    |

E501 Line too long (461 > 120)
   --> src/engine/processor/prompts/system_prompt.py:270:121
    |
268 | …
269 | …if they align or contradict.
270 | … "NO SETUP". If the LTF is moving counter to the HTF to target a HTF Supply/Demand Zone/OB (Counter-Trend Retracement), OR if the LTF is reversing at a HTF Zone to realign with the HTF (Pro-Trend Reversal), the setup is HIGHLY VALID. Reject the trade ONLY if the timeframes are in structureless chaos with no clear pullback or reversal narrative.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
271 | …t assume or fabricate any factor.
272 | …alidation, three TP targets from liquidity pools and structural levels, and R:R ratio.
    |

E501 Line too long (148 > 120)
   --> src/engine/processor/prompts/system_prompt.py:271:121
    |
269 | …DXY, COT, and macro data together to determine if they align or contradict.
270 | …Bearish, H4 Bullish) DO NOT automatically equal "NO SETUP". If the LTF is moving counter to the HTF to target a HTF Supply/Demand Zo…
271 | …s are genuinely present in the LIVE data. Do not assume or fabricate any factor.
    |                                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
272 | …ne (OTE 62-79% of OB), SL beyond structural invalidation, three TP targets from liquidity pools and structural levels, and R:R ratio.
273 | … retrieved knowledge chunk. If you cannot cite a rule, you cannot make the claim.
    |

E501 Line too long (201 > 120)
   --> src/engine/processor/prompts/system_prompt.py:272:121
    |
270 | … automatically equal "NO SETUP". If the LTF is moving counter to the HTF to target a HTF Supply/Demand Zone/OB (Counter-Trend Retrac…
271 | …the LIVE data. Do not assume or fabricate any factor.
272 | …eyond structural invalidation, three TP targets from liquidity pools and structural levels, and R:R ratio.
    |                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
273 | … If you cannot cite a rule, you cannot make the claim.
    |

E501 Line too long (149 > 120)
   --> src/engine/processor/prompts/system_prompt.py:273:121
    |
271 | … are genuinely present in the LIVE data. Do not assume or fabricate any factor.
272 | …e (OTE 62-79% of OB), SL beyond structural invalidation, three TP targets from liquidity pools and structural levels, and R:R ratio.
273 | …retrieved knowledge chunk. If you cannot cite a rule, you cannot make the claim.
    |                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
274 | …
275 | …
    |

E501 Line too long (122 > 120)
   --> src/engine/processor/prompts/system_prompt.py:276:121
    |
275 | 2. HALLUCINATION PREVENTION
276 |    - You may ONLY reason from the retrieved_knowledge chunks and the live data provided in ta_analysis and macro_analysis.
    |                                                                                                                         ^^
277 |    - If a market scenario is not covered by any retrieved chunk, output direction: "NO SETUP".
278 |    - Every factor in the confluence score must be verifiably present in the provided data.
    |

E501 Line too long (164 > 120)
   --> src/engine/processor/prompts/system_prompt.py:279:121
    |
277 | …ction: "NO SETUP".
278 | …provided data.
279 | … the conflict is a valid fractal pullback (e.g., LTF pushing into HTF Premium/Discount).
    |                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
280 | …
    |

E501 Line too long (189 > 120)
   --> src/engine/processor/prompts/system_prompt.py:286:121
    |
284 | …ll for trade-specific fields).
285 | …_<4 random hex chars>.
286 | …ing chain. It must reference specific price levels, timestamps, and structural events from the data.
    |                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
287 | …itly spell out the exact market variation in your reasoning based on its boolean flags. For example: For SMC, if a base SH_BMS_RTO c…
288 | …ed_knowledge provided.
    |

E501 Line too long (584 > 120)
   --> src/engine/processor/prompts/system_prompt.py:287:121
    |
285 | …
286 | …ce specific price levels, timestamps, and structural events from the data.
287 | …arket variation in your reasoning based on its boolean flags. For example: For SMC, if a base SH_BMS_RTO candidate has an FVG and inducement_cleared=true, you MUST literally write the pattern as "SH+BMS+FVG+IDM+RTO". For SnD, if a QML candidate has an MPL, Fakeout, and Marubozu confirmed, you MUST literally write out "QML+MPL+SR_FLIP+FAKEOUT+MARUBOZU". Do not just write the base name; expose the exact dynamic variations and confluences present (e.g., +COMPRESSION).
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
288 | …
    |

E501 Line too long (138 > 120)
   --> src/engine/processor/prompts/system_prompt.py:292:121
    |
290 | …
291 | …al quality):
292 | …y if available, but treat neutral or missing data as non-blocking/aligned.)
    |                                                           ^^^^^^^^^^^^^^^^^^
293 | …d Counter-Trend Pullback targeting a HTF zone (MANDATORY)
294 | …rection (MANDATORY)
    |

E501 Line too long (165 > 120)
   --> src/engine/processor/prompts/system_prompt.py:295:121
    |
293 | …d Pullback targeting a HTF zone (MANDATORY)
294 | …TORY)
295 | …zone (for SnD setups) OR an Entry Timeframe Order Block/FVG (for SMC setups) (MANDATORY)
    |                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
296 | …
297 | …
    |

E501 Line too long (165 > 120)
   --> src/engine/processor/prompts/system_prompt.py:316:121
    |
314 | …
315 | …riate one based on your analysis:
316 | …ou want the system to place a limit order immediately and wait for price to activate it.
    |                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
317 | …uires LTF confirmation.
318 | …ntly at the current live price because confirmation is already met.
    |

W291 Trailing whitespace
   --> src/engine/processor/prompts/system_prompt.py:317:101
    |
315 |    The system has two distinct modes of execution. You must select the appropriate one based on your analysis:
316 |    - "LIMIT": Use this when you have a high-confidence, valid HTF setup and you want the system to place a limit order immediately an…
317 |    - "INSTANT": Use this when you are assigning a trade at a HTF POI that requires LTF confirmation.
    |                                                                                                     ^
318 |      * If ltf_confirmed is TRUE: The system will execute a Market Order instantly at the current live price because confirmation is a…
319 |      * If ltf_confirmed is FALSE: The system will continuously monitor prices until price gets to the POI, wait for the LTF confirmat…
    |
help: Remove trailing whitespace

E501 Line too long (144 > 120)
   --> src/engine/processor/prompts/system_prompt.py:318:121
    |
316 | …setup and you want the system to place a limit order immediately and wait for price to activate it.
317 | …OI that requires LTF confirmation.
318 | …Order instantly at the current live price because confirmation is already met.
    |                                                        ^^^^^^^^^^^^^^^^^^^^^^^^
319 | …itor prices until price gets to the POI, wait for the LTF confirmation to print, and THEN execute instantly.
320 | …provided explicitly has ltf_confirmation: true AND choch_detected: true AND bms_detected: true, otherwise output false.
    |

E501 Line too long (174 > 120)
   --> src/engine/processor/prompts/system_prompt.py:319:121
    |
317 | …s LTF confirmation.
318 | … at the current live price because confirmation is already met.
319 | …il price gets to the POI, wait for the LTF confirmation to print, and THEN execute instantly.
    |                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
320 | …itly has ltf_confirmation: true AND choch_detected: true AND bms_detected: true, otherwise output false.
    |

E501 Line too long (185 > 120)
   --> src/engine/processor/prompts/system_prompt.py:320:121
    |
318 | …e current live price because confirmation is already met.
319 | …ce gets to the POI, wait for the LTF confirmation to print, and THEN execute instantly.
320 | …as ltf_confirmation: true AND choch_detected: true AND bms_detected: true, otherwise output false.
    |                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
321 | …
322 | …
    |

E501 Line too long (123 > 120)
   --> src/engine/processor/prompts/system_prompt.py:323:121
    |
322 | 8. CONTEXTUAL VALIDATION (CRITICAL)
323 |    - You must validate that the provided ta_analysis snapshots and smc_candidates are relevant to the current market state.
    |                                                                                                                         ^^^
324 |    - Check the timestamps: Only consider candidates whose timestamps are near the analysis timestamp (within the last 24-48 hours dep…
325 |    - Historical candidates provide context but are NOT tradeable. Use them to understand trend evolution, not as live setups.
    |

E501 Line too long (154 > 120)
   --> src/engine/processor/prompts/system_prompt.py:324:121
    |
322 | …
323 | …candidates are relevant to the current market state.
324 | …e near the analysis timestamp (within the last 24-48 hours depending on timeframe).
    |                                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
325 | …hem to understand trend evolution, not as live setups.
326 | …utput direction: "NO SETUP".
    |

E501 Line too long (125 > 120)
   --> src/engine/processor/prompts/system_prompt.py:325:121
    |
323 |    - You must validate that the provided ta_analysis snapshots and smc_candidates are relevant to the current market state.
324 |    - Check the timestamps: Only consider candidates whose timestamps are near the analysis timestamp (within the last 24-48 hours dep…
325 |    - Historical candidates provide context but are NOT tradeable. Use them to understand trend evolution, not as live setups.
    |                                                                                                                         ^^^^^
326 |    - If all candidates are historical (e.g., from days or weeks ago), output direction: "NO SETUP".
    |

E501 Line too long (167 > 120)
   --> src/engine/processor/prompts/system_prompt.py:329:121
    |
328 | …
329 | …ap risks, Asian session low-liquidity constraints) apply ONLY to traditional Forex pairs.
    |                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
330 | …, "Step", "Volatility", and Cryptocurrencies), session-based liquidity constraints and weekend closures DO NOT APPLY. Treat these ma…
    |

E501 Line too long (239 > 120)
   --> src/engine/processor/prompts/system_prompt.py:330:121
    |
328 | …
329 | …y constraints) apply ONLY to traditional Forex pairs.
330 | …rrencies), session-based liquidity constraints and weekend closures DO NOT APPLY. Treat these markets as continuously liquid.
    |        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
331 | …
332 | …
    |

E501 Line too long (180 > 120)
   --> src/engine/processor/prompts/system_prompt.py:335:121
    |
334 | …
335 | …is is an opaque pulse-matching identifier used by the downstream Gateway and Execution services.
    |                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
336 | …_module_b is YES), you MUST populate `entry_setup.zone_id` with the EXACT `candidate_id` string of the candidate you chose. Copy it …
337 | …inal TA candidate via a ~100ms fast-path. If the value is missing, empty, or does not match a real candidate_id from the input, the …
    |

E501 Line too long (299 > 120)
   --> src/engine/processor/prompts/system_prompt.py:336:121
    |
334 | …
335 | …identifier used by the downstream Gateway and Execution services.
336 | …ulate `entry_setup.zone_id` with the EXACT `candidate_id` string of the candidate you chose. Copy it verbatim, character for character. Do not invent, abbreviate, hash, or reformat it.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
337 | …fast-path. If the value is missing, empty, or does not match a real candidate_id from the input, the Gateway is forced into a ~5-10s full TA replay, materially degrading trade latency.
338 | …
    |

E501 Line too long (299 > 120)
   --> src/engine/processor/prompts/system_prompt.py:337:121
    |
335 | …identifier used by the downstream Gateway and Execution services.
336 | …ulate `entry_setup.zone_id` with the EXACT `candidate_id` string of the candidate you chose. Copy it verbatim, character for character. Do not invent, abbreviate, hash, or reformat it.
337 | …fast-path. If the value is missing, empty, or does not match a real candidate_id from the input, the Gateway is forced into a ~5-10s full TA replay, materially degrading trade latency.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
338 | …
339 | …e.
    |

E501 Line too long (242 > 120)
   --> src/engine/processor/prompts/system_prompt.py:342:121
    |
341 | …
342 | …mat strict, Anthropic tools input_schema). Field semantics described above remain authoritative regardless of provider support.
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
343 | …
344 | …
    |

PLR0915 Too many statements (65 > 50)
   --> src/engine/processor/prompts/system_prompt.py:353:5
    |
353 | def build_user_message(context: ProcessorInput) -> str:
    |     ^^^^^^^^^^^^^^^^^^
354 |     """Serialize the gateway-assembled context as the user message.
    |

ERA001 Found commented-out code
   --> src/engine/processor/prompts/system_prompt.py:455:5
    |
453 |     #
454 |     # NOTE: `candidate_id` is INTENTIONALLY NOT stripped. The Gateway's
455 |     # processSymbol() in src/gateway/internal/pipeline/orchestrator.go
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
456 |     # calls matchesCandidate(cand, processorOutput.AnalysisID) and the
457 |     # primary lookup uses cand["candidate_id"]. processorOutput.AnalysisID
    |
help: Remove commented-out code

N806 Variable `_STRIP_KEYS` in function should be lowercase
   --> src/engine/processor/prompts/system_prompt.py:464:5
    |
462 |     # /internal/ta/confirm_ltf and forces a full ~5-10s TA replay per
463 |     # trade. Do not re-add `candidate_id` to this set.
464 |     _STRIP_KEYS = {
    |     ^^^^^^^^^^^
465 |         # DB / collector metadata
466 |         "id",
    |

N806 Variable `_EMPTY_VALUES` in function should be lowercase
   --> src/engine/processor/prompts/system_prompt.py:485:5
    |
484 |     # Values that carry zero information for the LLM
485 |     _EMPTY_VALUES = {
    |     ^^^^^^^^^^^^^
486 |         None,
487 |         "",
    |

N806 Variable `_DEAD_WHEN_FALSE_SUFFIXES` in function should be lowercase
   --> src/engine/processor/prompts/system_prompt.py:502:5
    |
500 |     # decisions the LLM relies on for its top-down spine and must
501 |     # remain explicit either way.
502 |     _DEAD_WHEN_FALSE_SUFFIXES = (
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^
503 |         "_detected",
504 |         "_cleared",
    |

PLR0124 Name compared with itself, consider replacing `value != value`
   --> src/engine/processor/prompts/system_prompt.py:522:12
    |
520 |         preserved untouched.
521 |         """
522 |         if value != value:  # NaN guard (NaN != NaN by IEEE-754)
    |            ^^^^^
523 |             return value
524 |         return round(value, 5)
    |

PLR1714 Consider merging multiple comparisons: `v_clean in ("", [], {})`. Use a `set` if the elements are hashable.
   --> src/engine/processor/prompts/system_prompt.py:559:20
    |
557 |                 v_clean = _clean_dict(v)
558 |                 # Drop None, empty string, empty list, empty dict
559 |                 if v_clean is None or v_clean == "" or v_clean == [] or v_clean == {}:
    |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
560 |                     continue
561 |                 # Drop known zero-information string defaults
    |
help: Merge multiple comparisons

PLR1714 Consider merging multiple comparisons: `item not in ("", [], {})`. Use a `set` if the elements are hashable.
   --> src/engine/processor/prompts/system_prompt.py:589:20
    |
587 |                 item
588 |                 for item in cleaned
589 |                 if item is not None and item != "" and item != [] and item != {}
    |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
590 |             ]
591 |         if isinstance(d, bool):
    |
help: Merge multiple comparisons

ERA001 Found commented-out code
   --> src/engine/processor/prompts/system_prompt.py:646:5
    |
644 |     #    keys from the RAG ContextBundle (rag_strategy_used,
645 |     #    rag_coverage_result, rag_conflict_result,
646 |     #    rag_total_chunks_returned, rag_coverage_gaps,
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
647 |     #    rag_conflict_details). These describe HOW retrieval ran, not
648 |     #    WHAT the LLM should reason about. The chunk content the LLM
    |
help: Remove commented-out code

N806 Variable `_METADATA_STRIP_KEYS` in function should be lowercase
   --> src/engine/processor/prompts/system_prompt.py:664:5
    |
662 |     # logger extras. Neither needs to be inside the prompt body for
663 |     # downstream consumers to function.
664 |     _METADATA_STRIP_KEYS = {"trace_id"}
    |     ^^^^^^^^^^^^^^^^^^^^
665 |     clean_metadata = {
666 |         k: v
    |

N817 CamelCase `AnalysisOutput` imported as acronym `AO`
  --> src/engine/processor/service.py:43:46
   |
41 | from engine.processor.llm.retry import retry_llm_call
42 | from engine.processor.mapping.output_mapper import map_to_processor_output
43 | from engine.processor.models.analysis import AnalysisOutput as AO
   |                                              ^^^^^^^^^^^^^^^^^^^^
44 | from engine.processor.models.io import ProcessorInput, ProcessorOutput, ProcessorPort
45 | from engine.processor.parsing.response_parser import parse_llm_response
   |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/processor/service.py:257:13
    |
255 |               )
256 |
257 | /             raise ProcessorError(
258 | |                 f"Processor timed out after {self._config.total_timeout_seconds}s",
259 | |                 details={"symbol": symbol, "trace_id": trace_id},
260 | |             )
    | |_____________^
261 |
262 |           except ProcessorInsufficientDataError:
    |

PLR0912 Too many branches (21 > 12)
   --> src/engine/processor/service.py:413:15
    |
411 |             await guard.release(handle, trace_id=trace_id)
412 |
413 |     async def _execute(
    |               ^^^^^^^^
414 |         self,
415 |         context: ProcessorInput,
    |

PLR0915 Too many statements (122 > 50)
   --> src/engine/processor/service.py:413:15
    |
411 |             await guard.release(handle, trace_id=trace_id)
412 |
413 |     async def _execute(
    |               ^^^^^^^^
414 |         self,
415 |         context: ProcessorInput,
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/processor/service.py:441:13
    |
439 |         # Dump exact LLM payload to /output/prompts for debugging
440 |         try:
441 |             from datetime import datetime as dt
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
442 |             from pathlib import Path
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/processor/service.py:442:13
    |
440 |         try:
441 |             from datetime import datetime as dt
442 |             from pathlib import Path
    |             ^^^^^^^^^^^^^^^^^^^^^^^^
443 |
444 |             ts = dt.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/processor/service.py:752:17
    |
750 |             # Dump the truncated response for debugging
751 |             try:
752 |                 from datetime import datetime as dt
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
753 |                 from pathlib import Path
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/processor/service.py:753:17
    |
751 |             try:
752 |                 from datetime import datetime as dt
753 |                 from pathlib import Path
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^
754 |
755 |                 ts = dt.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/processor/service.py:770:13
    |
768 |                       encoding="utf-8",
769 |                   )
770 | /             except Exception:
771 | |                 pass
    | |____________________^
772 |
773 |               logger.error(
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/processor/service.py:840:17
    |
838 |             # Dump the truncated response to see exactly what Gemini returned
839 |             try:
840 |                 from datetime import datetime as dt
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
841 |                 from pathlib import Path
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/processor/service.py:841:17
    |
839 |             try:
840 |                 from datetime import datetime as dt
841 |                 from pathlib import Path
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^
842 |
843 |                 ts = dt.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/processor/service.py:852:13
    |
850 |                       "dumped_truncated_response", extra={"directory": str(dump_dir)}
851 |                   )
852 | /             except Exception:
853 | |                 pass
    | |____________________^
854 |               raise parse_exc
    |

SIM108 Use ternary operator `status = ProcessorStatus.NO_SETUP if analysis_output.direction == "NO SETUP" else ProcessorStatus.SUCCESS` instead of `if`-`else`-block
   --> src/engine/processor/service.py:887:9
    |
886 |           # Step 9: Determine status, emit metrics, persist audit trail.
887 | /         if analysis_output.direction == "NO SETUP":
888 | |             status = ProcessorStatus.NO_SETUP
889 | |         else:
890 | |             status = ProcessorStatus.SUCCESS
    | |____________________________________________^
891 |
892 |           PROCESSOR_RUN_TOTAL.labels(
    |
help: Replace `if`-`else`-block with `status = ProcessorStatus.NO_SETUP if analysis_output.direction == "NO SETUP" else ProcessorStatus.SUCCESS`

C416 Unnecessary dict comprehension (rewrite using `dict()`)
   --> src/engine/processor/storage/repositories/analysis_repository.py:255:30
    |
253 |         )
254 |         grade_rows = await self._session.execute(grade_stmt)
255 |         grade_distribution = {g: c for g, c in grade_rows.all()}
    |                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
256 |
257 |         # -- Provider distribution --------------------------------------------
    |
help: Rewrite using `dict()`

C416 Unnecessary dict comprehension (rewrite using `dict()`)
   --> src/engine/processor/storage/repositories/analysis_repository.py:273:33
    |
271 |         )
272 |         provider_rows = await self._session.execute(provider_stmt)
273 |         provider_distribution = {p: c for p, c in provider_rows.all()}
    |                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
274 |
275 |         # -- Pair distribution ------------------------------------------------
    |
help: Rewrite using `dict()`

C416 Unnecessary dict comprehension (rewrite using `dict()`)
   --> src/engine/processor/storage/repositories/analysis_repository.py:291:29
    |
289 |         )
290 |         pair_rows = await self._session.execute(pair_stmt)
291 |         pair_distribution = {p: c for p, c in pair_rows.all()}
    |                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
292 |
293 |         return {
    |
help: Rewrite using `dict()`

S608 Possible SQL injection vector through string-based query construction
   --> src/engine/processor/storage/repositories/billing_repository.py:160:21
    |
158 |               return
159 |
160 |           stmt = text(f"""
    |  _____________________^
161 | |             UPDATE billing_usage
162 | |             SET {column} = {column} + :amount
163 | |             WHERE user_id = :user_id
164 | |             """)
    | |_______________^
165 |           await self._session.execute(stmt, {"user_id": user_id, "amount": amount})
166 |           await self._session.commit()
    |

PLR2004 Magic value used in comparison, consider replacing `253` with a constant variable
   --> src/engine/processor/storage/repositories/broker_connection_repository.py:107:20
    |
105 | def _validate_host(host: str) -> None:
106 |     """Validate that a host string is a valid IP address or hostname."""
107 |     if len(host) > 253:
    |                    ^^^
108 |         raise ValueError(f"ea_host too long ({len(host)} chars, max 253)")
109 |     if not _HOST_PATTERN.match(host):
    |

PLR2004 Magic value used in comparison, consider replacing `1024` with a constant variable
   --> src/engine/processor/storage/repositories/broker_connection_repository.py:143:41
    |
141 |             raise ValueError("ea_host is required for EA connections")
142 |         _validate_host(ea_host.strip())
143 |         if ea_port is None or ea_port < 1024 or ea_port > 65535:
    |                                         ^^^^
144 |             raise ValueError(
145 |                 f"ea_port must be 1024..65535 for EA connections, got {ea_port}"
    |

PLR2004 Magic value used in comparison, consider replacing `65535` with a constant variable
   --> src/engine/processor/storage/repositories/broker_connection_repository.py:143:59
    |
141 |             raise ValueError("ea_host is required for EA connections")
142 |         _validate_host(ea_host.strip())
143 |         if ea_port is None or ea_port < 1024 or ea_port > 65535:
    |                                                           ^^^^^
144 |             raise ValueError(
145 |                 f"ea_port must be 1024..65535 for EA connections, got {ea_port}"
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/processor/storage/repositories/broker_connection_repository.py:267:17
    |
265 |         if id is not None:
266 |             try:
267 |                 from uuid import UUID as _UUIDValidate
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
268 |
269 |                 _UUIDValidate(str(id))
    |

N811 Constant `UUID` imported as non-constant `_UUIDValidate`
   --> src/engine/processor/storage/repositories/broker_connection_repository.py:267:34
    |
265 |         if id is not None:
266 |             try:
267 |                 from uuid import UUID as _UUIDValidate
    |                                  ^^^^^^^^^^^^^^^^^^^^^
268 |
269 |                 _UUIDValidate(str(id))
    |

PLR0912 Too many branches (15 > 12)
   --> src/engine/processor/storage/repositories/broker_connection_repository.py:372:15
    |
370 |     # -- Update ----------------------------------------------------------------
371 |
372 |     async def update_connection(
    |               ^^^^^^^^^^^^^^^^^
373 |         self,
374 |         connection_id: str,
    |

PLR2004 Magic value used in comparison, consider replacing `1024` with a constant variable
   --> src/engine/processor/storage/repositories/broker_connection_repository.py:403:26
    |
401 |             values["ea_host"] = ea_host.strip()
402 |         if ea_port is not None:
403 |             if ea_port < 1024 or ea_port > 65535:
    |                          ^^^^
404 |                 raise ValueError(f"ea_port must be 1024..65535, got {ea_port}")
405 |             values["ea_port"] = ea_port
    |

PLR2004 Magic value used in comparison, consider replacing `65535` with a constant variable
   --> src/engine/processor/storage/repositories/broker_connection_repository.py:403:44
    |
401 |             values["ea_host"] = ea_host.strip()
402 |         if ea_port is not None:
403 |             if ea_port < 1024 or ea_port > 65535:
    |                                            ^^^^^
404 |                 raise ValueError(f"ea_port must be 1024..65535, got {ea_port}")
405 |             values["ea_port"] = ea_port
    |

SIM105 Use `contextlib.suppress(Exception)` instead of `try`-`except`-`pass`
   --> src/engine/processor/trading_plan/generator.py:180:9
    |
178 |       async def aclose(self) -> None:
179 |           """Close the dedicated callback HTTP client. Safe to re-call."""
180 | /         try:
181 | |             await self._http.aclose()
182 | |         except Exception:
183 | |             pass
    | |________________^
184 |
185 |       # -- Public entry point -------------------------------------------------
    |
help: Replace `try`-`except`-`pass` with `with contextlib.suppress(Exception): ...`

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/processor/trading_plan/generator.py:182:9
    |
180 |           try:
181 |               await self._http.aclose()
182 | /         except Exception:
183 | |             pass
    | |________________^
184 |
185 |       # -- Public entry point -------------------------------------------------
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/processor/trading_plan/generator.py:231:9
    |
229 |         # gateway falls back to skipping the metric if this field is
230 |         # missing, so deploys mid-flight stay backward-compatible.
231 |         from datetime import datetime
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
232 |
233 |         generation_started_at = datetime.now(UTC).isoformat()
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/processor/trading_plan/generator.py:302:17
    |
300 |                       },
301 |                   )
302 | /                 raise TradingPlanGenerationError(
303 | |                     f"LLM quota reached for your tier ({exc.dimension}); "
304 | |                     f"resets in {exc.retry_after} seconds"
305 | |                 )
    | |_________________^
306 |
307 |               # Bounded retry loop for the LLM call. Transient transport
    |

ERA001 Found commented-out code
   --> src/engine/processor/trading_plan/generator.py:329:21
    |
327 |                     # API grammar to coerce every plan response into
328 |                     # an AnalysisOutput object, after which
329 |                     # _shape_plan()._require_dict("trader_profile")
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
330 |                     # would always fail with "AI response is missing
331 |                     # the 'trader_profile' section".
    |
help: Remove commented-out code

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/processor/trading_plan/generator.py:429:13
    |
427 |             data = json.loads(candidate)
428 |         except json.JSONDecodeError:
429 |             raise TradingPlanGenerationError("AI response was not valid JSON")
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
430 |         if not isinstance(data, dict):
431 |             raise TradingPlanGenerationError("AI response was not a JSON object")
    |

PLR2004 Magic value used in comparison, consider replacing `200` with a constant variable
   --> src/engine/processor/trading_plan/generator.py:628:36
    |
626 |             last_body_preview = resp.text[:300]
627 |
628 |             if resp.status_code == 200:
    |                                    ^^^
629 |                 logger.info(
630 |                     "trading_plan_callback_persisted",
    |

PLR2004 Magic value used in comparison, consider replacing `422` with a constant variable
   --> src/engine/processor/trading_plan/generator.py:636:36
    |
635 |             # 422 — validator rejection; retry will not fix it.
636 |             if resp.status_code == 422:
    |                                    ^^^
637 |                 logger.error(
638 |                     "trading_plan_callback_rejected_validation",
    |

PLR2004 Magic value used in comparison, consider replacing `500` with a constant variable
   --> src/engine/processor/trading_plan/generator.py:651:16
    |
650 |             # 5xx — transient on the gateway side, retry.
651 |             if 500 <= resp.status_code < 600:
    |                ^^^
652 |                 logger.warning(
653 |                     "trading_plan_callback_attempt_failed_5xx",
    |

PLR2004 Magic value used in comparison, consider replacing `600` with a constant variable
   --> src/engine/processor/trading_plan/generator.py:651:42
    |
650 |             # 5xx — transient on the gateway side, retry.
651 |             if 500 <= resp.status_code < 600:
    |                                          ^^^
652 |                 logger.warning(
653 |                     "trading_plan_callback_attempt_failed_5xx",
    |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/rag/embeddings/nomic.py:36:17
   |
34 |         if self._model is None:
35 |             try:
36 |                 from sentence_transformers import SentenceTransformer
   |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
37 |
38 |                 self._model = SentenceTransformer(
   |

S311 Standard pseudo-random generators are not suitable for cryptographic purposes
  --> src/engine/rag/embeddings/openai.py:96:48
   |
94 |                 )
95 |                 if attempt < self._max_retries:
96 |                     backoff = min(2**attempt + random.uniform(0, 1), 30.0)
   |                                                ^^^^^^^^^^^^^^^^^^^^
97 |                     await asyncio.sleep(backoff)
   |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/rag/embeddings/sentence_transformers.py:36:17
   |
34 |         if self._model is None:
35 |             try:
36 |                 from sentence_transformers import SentenceTransformer
   |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
37 |
38 |                 self._model = SentenceTransformer(self._model_name)
   |

PLR2004 Magic value used in comparison, consider replacing `0.7` with a constant variable
   --> src/engine/rag/ingest/chunkers/metadata.py:206:22
    |
204 |     short_ratio = short_count / total if total > 0 else 0
205 |
206 |     if long_ratio >= 0.7:
    |                      ^^^
207 |         directions.add("long")
208 |     elif short_ratio >= 0.7:
    |

PLR2004 Magic value used in comparison, consider replacing `0.7` with a constant variable
   --> src/engine/rag/ingest/chunkers/metadata.py:208:25
    |
206 |     if long_ratio >= 0.7:
207 |         directions.add("long")
208 |     elif short_ratio >= 0.7:
    |                         ^^^
209 |         directions.add("short")
210 |     # If neither dominates (mixed chunk), tag both so it can be
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/rag/ingest/chunkers/metadata.py:212:19
    |
210 |     # If neither dominates (mixed chunk), tag both so it can be
211 |     # retrieved for either direction query
212 |     elif total >= 2:
    |                   ^
213 |         directions.add("long")
214 |         directions.add("short")
    |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/rag/ingest/loaders/docx.py:25:13
   |
23 |             )
24 |         try:
25 |             from docx import Document as DocxDocument
   |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
26 |         except ImportError as exc:
27 |             raise RAGLoaderError(
   |

ASYNC240 Async functions should not use pathlib.Path methods, use trio.Path or anyio.path
  --> src/engine/rag/ingest/loaders/json.py:26:19
   |
24 |             )
25 |         try:
26 |             raw = path.read_text(encoding="utf-8")
   |                   ^^^^^^^^^^^^^^
27 |         except OSError as exc:
28 |             raise RAGLoaderError(
   |

ASYNC240 Async functions should not use pathlib.Path methods, use trio.Path or anyio.path
  --> src/engine/rag/ingest/loaders/markdown.py:29:23
   |
27 |             )
28 |         try:
29 |             content = path.read_text(encoding="utf-8")
   |                       ^^^^^^^^^^^^^^
30 |         except OSError as exc:
31 |             raise RAGLoaderError(
   |

PLW2901 `for` loop variable `line` overwritten by assignment target
  --> src/engine/rag/ingest/loaders/markdown.py:94:13
   |
92 |         metadata: dict[str, str] = {}
93 |         for line in frontmatter_text.split("\n"):
94 |             line = line.strip()
   |             ^^^^
95 |             if not line or line.startswith("#"):
96 |                 continue
   |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/rag/ingest/loaders/markdown.py:102:34
    |
100 |                 value = value.strip()
101 |                 # Remove surrounding quotes
102 |                 if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
    |                                  ^
103 |                     value = value[1:-1]
104 |                 if key and value:
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/rag/ingest/loaders/markdown.py:151:29
    |
149 |                 heading_text = heading_match.group(2).strip()
150 |
151 |                 if level <= 2:
    |                             ^
152 |                     _flush()
153 |                     current_heading = heading_text
    |

ASYNC240 Async functions should not use pathlib.Path methods, use trio.Path or anyio.path
  --> src/engine/rag/ingest/loaders/scenario_asset.py:90:29
   |
89 |         image_refs: list[str] = []
90 |         for child in sorted(path.iterdir()):
   |                             ^^^^^^^^^^^^
91 |             if child.suffix.lower() in SUPPORTED_IMAGE_FORMATS:
92 |                 image_refs.append(str(child.relative_to(path)))
   |

ASYNC240 Async functions should not use pathlib.Path methods, use trio.Path or anyio.path
  --> src/engine/rag/ingest/loaders/text.py:25:23
   |
23 |             )
24 |         try:
25 |             content = path.read_text(encoding="utf-8")
   |                       ^^^^^^^^^^^^^^
26 |         except OSError as exc:
27 |             raise RAGLoaderError(
   |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/rag/orchestrator.py:321:9
    |
319 |         relevant scenario examples for the LLM.
320 |         """
321 |         from engine.rag.models.scenario import Scenario
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
322 |
323 |         all_scenarios: list[Scenario] = []
    |

PLR0912 Too many branches (15 > 12)
  --> src/engine/rag/retrieval/coverage.py:41:5
   |
41 | def check_coverage(
   |     ^^^^^^^^^^^^^^
42 |     chunks: list[RetrievedChunk],
43 |     *,
   |

PLR0915 Too many statements (51 > 50)
  --> src/engine/rag/retrieval/coverage.py:41:5
   |
41 | def check_coverage(
   |     ^^^^^^^^^^^^^^
42 |     chunks: list[RetrievedChunk],
43 |     *,
   |

PLR0912 Too many branches (18 > 12)
  --> src/engine/rag/retrieval/mandatory.py:90:5
   |
90 | def compute_mandatory_requirements(
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
91 |     *,
92 |     symbol: str | None = None,
   |

PLR0915 Too many statements (91 > 50)
  --> src/engine/rag/retrieval/mandatory.py:90:5
   |
90 | def compute_mandatory_requirements(
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
91 |     *,
92 |     symbol: str | None = None,
   |

PLR0912 Too many branches (14 > 12)
  --> src/engine/rag/retrieval/strategies/hybrid.py:31:15
   |
29 |         return RetrievalStrategy.HYBRID
30 |
31 |     async def execute(
   |               ^^^^^^^
32 |         self,
33 |         query_text: str,
   |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/rag/retrieval/strategies/hybrid.py:143:9
    |
141 |                       merged.append(chunk)
142 |                       seen_ids.add(chunk.chunk_id)
143 | /         except Exception:
144 | |             # Scenario collection may be empty (0 documents) which causes
145 | |             # ChromaDB to error on query. Scenarios are supplementary, so
146 | |             # gracefully skip rather than crash the entire analysis pipeline.
147 | |             pass
    | |________________^
148 |
149 |           merged.sort(key=lambda c: c.score, reverse=True)
    |

ERA001 Found commented-out code
  --> src/engine/rag/retrieval/strategies/rule_first.py:51:9
   |
49 |         macro_k = max(3, (top_k * 35) // 100)  # ~35%
50 |
51 |         # Rules (master_rulebook + trading_style_rules)
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
52 |         rule_chunks = await self._retriever.retrieve(
53 |             query_text,
   |
help: Remove commented-out code

PLR0912 Too many branches (14 > 12)
  --> src/engine/rag/retrieval/strategies/scenario_first.py:29:15
   |
27 |         return RetrievalStrategy.SCENARIO_FIRST
28 |
29 |     async def execute(
   |               ^^^^^^^
30 |         self,
31 |         query_text: str,
   |

S110 `try`-`except`-`pass` detected, consider logging the exception
  --> src/engine/rag/retrieval/strategies/scenario_first.py:71:9
   |
69 |                       merged.append(chunk)
70 |                       seen_ids.add(chunk.chunk_id)
71 | /         except Exception:
72 | |             # Scenario collection may be empty (0 documents) which causes
73 | |             # ChromaDB to error on query. Scenarios are supplementary, so
74 | |             # gracefully skip rather than crash the entire analysis pipeline.
75 | |             pass
   | |________________^
76 |
77 |           # Rules
   |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/rag/scenarios/validator.py:60:5
   |
58 |     config: ScenarioConfig,
59 | ) -> None:
60 |     from engine.rag.knowledge.policies import enforce_scenario_minimum
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
61 |
62 |     enforce_scenario_minimum(count, minimum=config.min_total_scenarios)
   |

S110 `try`-`except`-`pass` detected, consider logging the exception
  --> src/engine/rag/services/health.py:55:9
   |
53 |               test_vec = await self._embedding_provider.embed_single("health check")
54 |               embed_ok = len(test_vec) == self._embedding_provider.dimensions
55 | /         except Exception:
56 | |             pass
   | |________________^
57 |
58 |           overall = vs_health.connected and db_ok and embed_ok
   |

PLR0912 Too many branches (18 > 12)
  --> src/engine/rag/vectorstore/filters.py:10:5
   |
10 | def build_where_filter(
   |     ^^^^^^^^^^^^^^^^^^
11 |     *,
12 |     doc_types: list[str] | None = None,
   |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
  --> src/engine/routers/analysis.py:55:31
   |
53 | async def get_my_usage(
54 |     request: Request,
55 |     user: AuthenticatedUser = Depends(get_current_user),
   |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
56 | ) -> dict:
57 |     """Return the current user's usage metrics (for dashboard countdown timer).
   |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/routers/analysis.py:66:5
   |
64 |       """
65 |       container: Container = request.app.state.container
66 | /     from engine.processor.storage.repositories.billing_repository import (
67 | |         BillingRepository,
68 | |     )
   | |_____^
69 |
70 |       try:
   |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
  --> src/engine/routers/analysis.py:82:9
   |
80 |               extra={"user_id": user.user_id},
81 |           )
82 | /         raise HTTPException(
83 | |             status_code=401,
84 | |             detail="Session is no longer valid. Please sign in again.",
85 | |             headers={"WWW-Authenticate": "Bearer"},
86 | |         )
   | |_________^
87 |       except DatabaseIntegrityError as exc:
88 |           # Defensive: any other integrity error on this write path is
   |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/analysis.py:97:9
    |
 95 |               extra={"user_id": user.user_id, "error": str(exc)},
 96 |           )
 97 | /         raise HTTPException(
 98 | |             status_code=401,
 99 | |             detail="Session is no longer valid. Please sign in again.",
100 | |             headers={"WWW-Authenticate": "Bearer"},
101 | |         )
    | |_________^
102 |
103 |       return {
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/analysis.py:120:31
    |
118 |     pair: str | None = None,
119 |     limit: int = 20,
120 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
121 | ) -> dict:
122 |     """List recent analyses for the dashboard."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/analysis.py:222:31
    |
220 |     offset: int = 0,
221 |     limit: int = 20,
222 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
223 | ) -> dict:
224 |     """Paginated analysis history with filters.
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/analysis.py:249:13
    |
247 |               since_dt = dt.fromisoformat(since.replace("Z", "+00:00"))
248 |           except ValueError:
249 | /             raise HTTPException(
250 | |                 status_code=400, detail=f"Invalid 'since' datetime: {since}"
251 | |             )
    | |_____________^
252 |       if until:
253 |           try:
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/analysis.py:256:13
    |
254 |               until_dt = dt.fromisoformat(until.replace("Z", "+00:00"))
255 |           except ValueError:
256 | /             raise HTTPException(
257 | |                 status_code=400, detail=f"Invalid 'until' datetime: {until}"
258 | |             )
    | |_____________^
259 |
260 |       limit = min(limit, 100)
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/analysis.py:319:31
    |
317 |     since: str | None = None,
318 |     until: str | None = None,
319 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
320 | ) -> dict:
321 |     """Aggregate analysis statistics for the dashboard.
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/analysis.py:337:13
    |
335 |               since_dt = dt.fromisoformat(since.replace("Z", "+00:00"))
336 |           except ValueError:
337 | /             raise HTTPException(
338 | |                 status_code=400, detail=f"Invalid 'since' datetime: {since}"
339 | |             )
    | |_____________^
340 |       if until:
341 |           try:
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/analysis.py:344:13
    |
342 |               until_dt = dt.fromisoformat(until.replace("Z", "+00:00"))
343 |           except ValueError:
344 | /             raise HTTPException(
345 | |                 status_code=400, detail=f"Invalid 'until' datetime: {until}"
346 | |             )
    | |_____________^
347 |
348 |       async with container.db.read_session() as session:
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/analysis.py:364:31
    |
362 | async def stream_live_analysis(
363 |     request: Request,
364 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
365 | ):
366 |     """SSE endpoint for the dashboard's live-reasoning panel.
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/analysis.py:473:31
    |
471 |     request: Request,
472 |     analysis_id: str,
473 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
474 | ) -> dict:
475 |     """Full analysis detail including LLM reasoning and raw output."""
    |

PLR0912 Too many branches (47 > 12)
   --> src/engine/routers/analysis.py:561:11
    |
560 | @router.post("/api/analysis/rerun")
561 | async def rerun_analysis(
    |           ^^^^^^^^^^^^^^
562 |     request: Request,
563 |     symbol: str,
    |

PLR0915 Too many statements (136 > 50)
   --> src/engine/routers/analysis.py:561:11
    |
560 | @router.post("/api/analysis/rerun")
561 | async def rerun_analysis(
    |           ^^^^^^^^^^^^^^
562 |     request: Request,
563 |     symbol: str,
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/analysis.py:565:31
    |
563 |     symbol: str,
564 |     trace_id: str | None = None,
565 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
566 | ) -> dict:
567 |     """Re-trigger analysis for a single symbol on demand.
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/routers/analysis.py:604:5
    |
602 |         raise HTTPException(status_code=400, detail="Symbol is required")
603 |
604 |     from datetime import timedelta
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
605 |
606 |     from engine.processor.storage.repositories.billing_repository import (
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/routers/analysis.py:606:5
    |
604 |       from datetime import timedelta
605 |
606 | /     from engine.processor.storage.repositories.billing_repository import (
607 | |         BillingRepository,
608 | |     )
    | |_____^
609 |
610 |       async with container.db.session() as session:
    |

E501 Line too long (170 > 120)
   --> src/engine/routers/analysis.py:630:121
    |
628 | …
629 | …
630 | …s. Next analysis available in {hours}h {minutes}m. Upgrade to Pro for unlimited analyses.",
    |                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
631 | …
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/analysis.py:651:9
    |
649 |       except Exception as exc:
650 |           logger.error("rerun_ta_failed", extra={"symbol": symbol, "error": str(exc)})
651 | /         raise HTTPException(
652 | |             status_code=500,
653 | |             detail="Technical analysis failed. Please try again in a moment.",
654 | |         )
    | |_________^
655 |
656 |       if isinstance(ta_result, dict):
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/analysis.py:712:9
    |
710 |       except Exception as exc:
711 |           logger.error("rerun_macro_failed", extra={"symbol": symbol, "error": str(exc)})
712 | /         raise HTTPException(
713 | |             status_code=500,
714 | |             detail="Macro collection failed. Please try again in a moment.",
715 | |         )
    | |_________^
716 |
717 |       # Derive enriched macro signal flags from collected data.
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/analysis.py:848:9
    |
846 |       except Exception as exc:
847 |           logger.error("rerun_rag_failed", extra={"symbol": symbol, "error": str(exc)})
848 | /         raise HTTPException(
849 | |             status_code=500,
850 | |             detail="Knowledge retrieval failed. Please try again in a moment.",
851 | |         )
    | |_________^
852 |
853 |       if not retrieved_knowledge:
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
  --> src/engine/routers/broker_bridge.py:73:9
   |
71 |               if cached is not None:
72 |                   return cached
73 | /         except Exception:
74 | |             pass
   | |________________^
75 |
76 |           logger.error(
   |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/routers/broker_bridge.py:135:9
    |
133 |               if cached is not None:
134 |                   return cached
135 | /         except Exception:
136 | |             pass
    | |________________^
137 |
138 |           logger.error(
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/routers/broker_bridge.py:186:9
    |
184 |               if cached is not None:
185 |                   return cached
186 | /         except Exception:
187 | |             pass
    | |________________^
188 |           return []
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/routers/broker_bridge.py:233:9
    |
231 |               if cached_orders is not None:
232 |                   return cached_orders
233 | /         except Exception:
234 | |             pass
    | |________________^
235 |
236 |           return []
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/routers/broker_bridge.py:272:9
    |
270 |               if cached:
271 |                   return cached
272 | /         except Exception:
273 | |             pass
    | |________________^
274 |
275 |           logger.error(
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/broker_bridge.py:279:9
    |
277 |               extra={"symbol": symbol, "error": str(exc), "user_id": user_id},
278 |           )
279 | /         raise HTTPException(
280 | |             status_code=502, detail=f"Symbol info unavailable and no cache: {exc}"
281 | |         )
    | |_________^
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/broker_bridge.py:312:9
    |
310 |             extra={"symbol": symbol, "error": str(exc), "user_id": user_id},
311 |         )
312 |         raise HTTPException(status_code=502, detail=f"Tick price unavailable: {exc}")
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/broker_bridge.py:370:9
    |
368 |             },
369 |         )
370 |         raise HTTPException(status_code=502, detail=f"Order placement failed: {exc}")
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/broker_bridge.py:434:9
    |
432 |             extra={"ticket": ticket, "error": str(exc), "user_id": user_id},
433 |         )
434 |         raise HTTPException(status_code=502, detail=f"Position unavailable: {exc}")
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |

PLR0912 Too many branches (15 > 12)
  --> src/engine/routers/broker_connections.py:96:11
   |
95 | @router.post("/api/broker/connections")
96 | async def create_broker_connection(
   |           ^^^^^^^^^^^^^^^^^^^^^^^^
97 |     request: Request,
98 |     body: CreateBrokerConnectionRequest,
   |

PLR0915 Too many statements (80 > 50)
  --> src/engine/routers/broker_connections.py:96:11
   |
95 | @router.post("/api/broker/connections")
96 | async def create_broker_connection(
   |           ^^^^^^^^^^^^^^^^^^^^^^^^
97 |     request: Request,
98 |     body: CreateBrokerConnectionRequest,
   |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/broker_connections.py:100:31
    |
 98 |     body: CreateBrokerConnectionRequest,
 99 |     background_tasks: BackgroundTasks,
100 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
101 | ) -> dict:
102 |     """Create a new broker connection (EA or MetaAPI).
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/broker_connections.py:214:17
    |
212 |                       extra={"error": str(exc)},
213 |                   )
214 | /                 raise HTTPException(
215 | |                     status_code=400,
216 | |                     detail="Broker provisioning failed. Check the broker server, login and password and try again.",
217 | |                 )
    | |_________________^
218 |
219 |           elif body.connection_type == "hosted":
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/routers/broker_connections.py:257:13
    |
255 |             # all agree. HostedRecoveryService and gc_orphans key on the
256 |             # row id; any mismatch breaks recovery and GC silently.
257 |             from uuid import uuid4 as _uuid4
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
258 |
259 |             allocated_connection_id = str(_uuid4())
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/routers/broker_connections.py:272:13
    |
271 |             # Generate a secure token upfront.
272 |             import secrets
    |             ^^^^^^^^^^^^^^
273 |
274 |             ea_auth_token = secrets.token_hex(32)
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/broker_connections.py:369:9
    |
367 |             str(row.id)
368 |     except ValueError as exc:
369 |         raise HTTPException(status_code=400, detail=str(exc))
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
370 |
371 |     if body.activate:
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/broker_connections.py:383:31
    |
381 | async def list_broker_connections(
382 |     request: Request,
383 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
384 | ) -> dict:
385 |     """List all saved broker connections."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/broker_connections.py:399:31
    |
397 | async def get_active_broker_connection(
398 |     request: Request,
399 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
400 | ) -> dict:
401 |     """Get the currently active broker connection."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/broker_connections.py:425:31
    |
423 |     request: Request,
424 |     connection_id: str,
425 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
426 | ) -> dict:
427 |     """Get a specific broker connection by ID."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/broker_connections.py:445:31
    |
443 |     connection_id: str,
444 |     body: UpdateBrokerConnectionRequest,
445 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
446 | ) -> dict:
447 |     """Update an existing broker connection.
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/broker_connections.py:493:9
    |
491 |             )
492 |     except ValueError as exc:
493 |         raise HTTPException(status_code=400, detail=str(exc))
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
494 |
495 |     if row is None:
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/broker_connections.py:565:31
    |
563 |     request: Request,
564 |     connection_id: str,
565 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
566 | ) -> dict:
567 |     """Activate a broker connection.
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/broker_connections.py:593:31
    |
591 |     request: Request,
592 |     connection_id: str,
593 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
594 | ) -> dict:
595 |     """Deactivate a broker connection without deleting it."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/broker_connections.py:616:31
    |
614 |     request: Request,
615 |     connection_id: str,
616 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
617 | ) -> dict:
618 |     """Set a connection as primary (also activates it).
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/broker_connections.py:643:31
    |
641 |     request: Request,
642 |     connection_id: str,
643 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
644 | ) -> dict:
645 |     """Test a broker connection's health.
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/broker_connections.py:740:31
    |
738 |     request: Request,
739 |     connection_id: str,
740 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
741 | ) -> dict:
742 |     """Permanently delete a saved broker connection."""
    |

N814 Camelcase `Timeframe` imported as constant `TF`
  --> src/engine/routers/chart.py:38:33
   |
36 | from engine.shared.logging import get_logger
37 | from engine.ta.broker.priority import BrokerRequestPriority, broker_priority
38 | from engine.ta.constants import Timeframe as TF
   |                                 ^^^^^^^^^^^^^^^
39 |
40 | logger = get_logger(__name__)
   |

E402 Module level import not at top of file
  --> src/engine/routers/chart.py:58:1
   |
56 | # is only a hot-path shield against repeated DB reads during a single
57 | # dashboard render.
58 | import contextlib
   | ^^^^^^^^^^^^^^^^^
59 | from collections import OrderedDict
   |

E402 Module level import not at top of file
  --> src/engine/routers/chart.py:59:1
   |
57 | # dashboard render.
58 | import contextlib
59 | from collections import OrderedDict
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
60 |
61 | _BROKER_SYMBOLS_CACHE_CAPACITY: int = 1024
   |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/chart.py:113:31
    |
111 | async def broker_symbols(
112 |     request: Request,
113 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
114 | ) -> dict:
115 |     """Return all available broker instruments with name, description, and path.
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/routers/chart.py:120:5
    |
118 |     and full metadata. Triggers background sync if registry is empty.
119 |     """
120 |     from engine.ta.broker.sync import BrokerSyncService
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
121 |
122 |     container = request.app.state.container
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/chart.py:197:9
    |
195 |               extra={"error": str(exc), "user_id": user.user_id},
196 |           )
197 | /         raise HTTPException(
198 | |             status_code=502,
199 | |             detail="Could not fetch broker symbols. Please try again in a moment.",
200 | |         )
    | |_________^
    |

PLR0912 Too many branches (13 > 12)
   --> src/engine/routers/chart.py:240:11
    |
239 | @router.get("/api/broker/candles")
240 | async def chart_candles(
    |           ^^^^^^^^^^^^^
241 |     request: Request,
242 |     symbol: str = Query(..., description="Broker symbol, e.g. USDJPYm"),
    |

PLR0915 Too many statements (137 > 50)
   --> src/engine/routers/chart.py:240:11
    |
239 | @router.get("/api/broker/candles")
240 | async def chart_candles(
    |           ^^^^^^^^^^^^^
241 |     request: Request,
242 |     symbol: str = Query(..., description="Broker symbol, e.g. USDJPYm"),
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/chart.py:245:31
    |
243 |     timeframe: str = Query("H1", description="Timeframe: M1,M5,M15,M30,H1,H4,D1,W1"),
244 |     count: int = Query(2000, ge=10, le=5000, description="Number of candles"),
245 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
246 | ) -> dict:
247 |     """Return historical OHLCV candles for the dashboard chart.
    |

N806 Variable `REVALIDATE_AFTER_S` in function should be lowercase
   --> src/engine/routers/chart.py:254:5
    |
252 |     """
253 |     # -- Tunables -------------------------------------------------------
254 |     REVALIDATE_AFTER_S = 30
    |     ^^^^^^^^^^^^^^^^^^
255 |     TOTAL_TTL_S = 1800
256 |     COLD_FETCH_DEADLINE_S = 60
    |

N806 Variable `TOTAL_TTL_S` in function should be lowercase
   --> src/engine/routers/chart.py:255:5
    |
253 |     # -- Tunables -------------------------------------------------------
254 |     REVALIDATE_AFTER_S = 30
255 |     TOTAL_TTL_S = 1800
    |     ^^^^^^^^^^^
256 |     COLD_FETCH_DEADLINE_S = 60
257 |     LOCK_TTL_S = 90
    |

N806 Variable `COLD_FETCH_DEADLINE_S` in function should be lowercase
   --> src/engine/routers/chart.py:256:5
    |
254 |     REVALIDATE_AFTER_S = 30
255 |     TOTAL_TTL_S = 1800
256 |     COLD_FETCH_DEADLINE_S = 60
    |     ^^^^^^^^^^^^^^^^^^^^^
257 |     LOCK_TTL_S = 90
258 |     LOCK_WAIT_POLL_S = 0.15
    |

N806 Variable `LOCK_TTL_S` in function should be lowercase
   --> src/engine/routers/chart.py:257:5
    |
255 |     TOTAL_TTL_S = 1800
256 |     COLD_FETCH_DEADLINE_S = 60
257 |     LOCK_TTL_S = 90
    |     ^^^^^^^^^^
258 |     LOCK_WAIT_POLL_S = 0.15
259 |     PREWARM_COOLDOWN_S = 300
    |

N806 Variable `LOCK_WAIT_POLL_S` in function should be lowercase
   --> src/engine/routers/chart.py:258:5
    |
256 |     COLD_FETCH_DEADLINE_S = 60
257 |     LOCK_TTL_S = 90
258 |     LOCK_WAIT_POLL_S = 0.15
    |     ^^^^^^^^^^^^^^^^
259 |     PREWARM_COOLDOWN_S = 300
260 |     REVALIDATE_COOLDOWN_S = 20
    |

N806 Variable `PREWARM_COOLDOWN_S` in function should be lowercase
   --> src/engine/routers/chart.py:259:5
    |
257 |     LOCK_TTL_S = 90
258 |     LOCK_WAIT_POLL_S = 0.15
259 |     PREWARM_COOLDOWN_S = 300
    |     ^^^^^^^^^^^^^^^^^^
260 |     REVALIDATE_COOLDOWN_S = 20
261 |     PREWARM_WAVE_DEADLINE_S = 300
    |

N806 Variable `REVALIDATE_COOLDOWN_S` in function should be lowercase
   --> src/engine/routers/chart.py:260:5
    |
258 |     LOCK_WAIT_POLL_S = 0.15
259 |     PREWARM_COOLDOWN_S = 300
260 |     REVALIDATE_COOLDOWN_S = 20
    |     ^^^^^^^^^^^^^^^^^^^^^
261 |     PREWARM_WAVE_DEADLINE_S = 300
262 |     BACKGROUND_FETCH_DEADLINE_S = 25
    |

N806 Variable `PREWARM_WAVE_DEADLINE_S` in function should be lowercase
   --> src/engine/routers/chart.py:261:5
    |
259 |     PREWARM_COOLDOWN_S = 300
260 |     REVALIDATE_COOLDOWN_S = 20
261 |     PREWARM_WAVE_DEADLINE_S = 300
    |     ^^^^^^^^^^^^^^^^^^^^^^^
262 |     BACKGROUND_FETCH_DEADLINE_S = 25
263 |     PREWARM_SPACING_S = 0.25
    |

N806 Variable `BACKGROUND_FETCH_DEADLINE_S` in function should be lowercase
   --> src/engine/routers/chart.py:262:5
    |
260 |     REVALIDATE_COOLDOWN_S = 20
261 |     PREWARM_WAVE_DEADLINE_S = 300
262 |     BACKGROUND_FETCH_DEADLINE_S = 25
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^
263 |     PREWARM_SPACING_S = 0.25
    |

N806 Variable `PREWARM_SPACING_S` in function should be lowercase
   --> src/engine/routers/chart.py:263:5
    |
261 |     PREWARM_WAVE_DEADLINE_S = 300
262 |     BACKGROUND_FETCH_DEADLINE_S = 25
263 |     PREWARM_SPACING_S = 0.25
    |     ^^^^^^^^^^^^^^^^^
264 |
265 |     tf_norm = timeframe.upper()
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/chart.py:500:9
    |
498 |               },
499 |           )
500 | /         raise HTTPException(
501 | |             status_code=502,
502 | |             detail="Could not fetch chart data. Please try again in a moment.",
503 | |         )
    | |_________^
504 |
505 |       if payload is not None:
    |

PLR0912 Too many branches (13 > 12)
   --> src/engine/routers/chart.py:543:11
    |
542 | @router.websocket("/api/broker/stream-ticks")
543 | async def stream_ticks(websocket: WebSocket):
    |           ^^^^^^^^^^^^
544 |     """True WebSocket stream of live tick prices for the dashboard chart.
    |

PLR0915 Too many statements (59 > 50)
   --> src/engine/routers/chart.py:543:11
    |
542 | @router.websocket("/api/broker/stream-ticks")
543 | async def stream_ticks(websocket: WebSocket):
    |           ^^^^^^^^^^^^
544 |     """True WebSocket stream of live tick prices for the dashboard chart.
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/routers/chart.py:564:5
    |
562 |       into the init frame.
563 |     """
564 |     from engine.shared.auth import AuthError, verify_token_from_websocket
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
565 |
566 |     await websocket.accept()
    |

PLR0912 Too many branches (14 > 12)
   --> src/engine/routers/chart.py:681:11
    |
680 | @router.websocket("/api/broker/stream-positions")
681 | async def stream_positions(websocket: WebSocket):
    |           ^^^^^^^^^^^^^^^^
682 |     """WebSocket stream of live position updates.
    |

PLR0915 Too many statements (60 > 50)
   --> src/engine/routers/chart.py:681:11
    |
680 | @router.websocket("/api/broker/stream-positions")
681 | async def stream_positions(websocket: WebSocket):
    |           ^^^^^^^^^^^^^^^^
682 |     """WebSocket stream of live position updates.
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/routers/chart.py:692:5
    |
690 |          [{ "ticket": 12345, "sl": 1.05, "tp": 1.10, ... }]
691 |     """
692 |     from engine.shared.auth import AuthError, verify_token_from_websocket
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
693 |
694 |     await websocket.accept()
    |

S324 Probable use of insecure hash functions in `hashlib`: `md5`
   --> src/engine/routers/chart.py:772:32
    |
771 |                 # Check for diff
772 |                 current_hash = hashlib.md5(
    |                                ^^^^^^^^^^^
773 |                     json.dumps(result, sort_keys=True).encode()
774 |                 ).hexdigest()
    |

F402 Import `status` from line 20 shadowed by loop variable
   --> src/engine/routers/health.py:130:15
    |
128 |     by_provider: dict[str, dict[str, str]] = {}
129 |     healthy = 0
130 |     for name, status in statuses.items():
    |               ^^^^^^
131 |         category = providers[name].category.value if name in providers else "unknown"
132 |         by_provider[name] = {
    |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/routers/internal.py:74:9
   |
72 |     user_id = request.headers.get("X-User-Id", "")
73 |     if not user_id:
74 |         from fastapi import HTTPException
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
75 |
76 |         raise HTTPException(
   |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/routers/internal.py:83:9
   |
81 |       # Lazy-build the LTF confirmation service
82 |       if not hasattr(container, "ltf_confirmation_service"):
83 | /         from engine.ta.common.services.ltf_confirmation.service import (
84 | |             LTFConfirmationService,
85 | |         )
   | |_________^
86 |           from engine.ta.smc.config import SMCConfig
   |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/routers/internal.py:86:9
   |
84 |             LTFConfirmationService,
85 |         )
86 |         from engine.ta.smc.config import SMCConfig
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
87 |
88 |         smc_config = SMCConfig()
   |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/routers/internal.py:105:5
    |
103 |               )
104 |
105 | /     from engine.ta.common.services.ltf_confirmation.service import (
106 | |         LTFConfirmationRequest,
107 | |     )
    | |_____^
108 |
109 |       ltf_request = LTFConfirmationRequest(
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/routers/internal.py:165:5
    |
163 |     # a semaphore lets the per-symbol work overlap while still capping load on
164 |     # the user's single broker connection.
165 |     from engine.config import get_ta_config
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
166 |
167 |     semaphore = asyncio.Semaphore(get_ta_config().max_concurrent_symbol_analysis)
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/internal.py:413:9
    |
411 |             extra={"trace_id": body.trace_id},
412 |         )
413 |         raise HTTPException(status_code=500, detail=f"RAG retrieval failed: {exc}")
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |

PLR0911 Too many return statements (8 > 6)
   --> src/engine/routers/internal.py:417:11
    |
416 | @router.post("/internal/processor/process")
417 | async def internal_processor_process(
    |           ^^^^^^^^^^^^^^^^^^^^^^^^^^
418 |     request: Request,
419 |     body: InternalProcessorRequest,
    |

PLR0912 Too many branches (15 > 12)
   --> src/engine/routers/internal.py:417:11
    |
416 | @router.post("/internal/processor/process")
417 | async def internal_processor_process(
    |           ^^^^^^^^^^^^^^^^^^^^^^^^^^
418 |     request: Request,
419 |     body: InternalProcessorRequest,
    |

PLR0915 Too many statements (51 > 50)
   --> src/engine/routers/internal.py:417:11
    |
416 | @router.post("/internal/processor/process")
417 | async def internal_processor_process(
    |           ^^^^^^^^^^^^^^^^^^^^^^^^^^
418 |     request: Request,
419 |     body: InternalProcessorRequest,
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/internal.py:667:9
    |
665 |             extra={"error": str(exc), "trace_id": body.trace_id},
666 |         )
667 |         raise HTTPException(status_code=500, detail=f"Processor failed: {exc}")
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
  --> src/engine/routers/llm_connections.py:38:31
   |
36 | async def get_llm_providers(
37 |     request: Request,
38 |     user: AuthenticatedUser = Depends(get_current_user),
   |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
39 | ) -> dict:
40 |     """List available LLM models and providers.
   |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
  --> src/engine/routers/llm_connections.py:68:31
   |
66 | async def list_llm_connections(
67 |     request: Request,
68 |     user: AuthenticatedUser = Depends(get_current_user),
   |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
69 | ) -> dict:
70 |     """List all saved LLM connections."""
   |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/llm_connections.py:100:31
    |
 98 | async def get_active_llm_connection(
 99 |     request: Request,
100 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
101 | ) -> dict:
102 |     """Get the currently active LLM connection."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/llm_connections.py:135:31
    |
133 |     request: Request,
134 |     body: CreateLLMConnectionRequest,
135 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
136 | ) -> dict:
137 |     """Create a new LLM connection.
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/llm_connections.py:217:31
    |
215 |     connection_id: str,
216 |     body: UpdateLLMConnectionRequest,
217 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
218 | ) -> dict:
219 |     """Update an existing LLM connection."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/llm_connections.py:269:31
    |
267 |     request: Request,
268 |     connection_id: str,
269 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
270 | ) -> dict:
271 |     """Activate a saved LLM connection.
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/llm_connections.py:306:31
    |
304 |     request: Request,
305 |     connection_id: str,
306 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
307 | ) -> dict:
308 |     """Deactivate a connection without deleting it."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/llm_connections.py:341:31
    |
339 |     request: Request,
340 |     connection_id: str,
341 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
342 | ) -> dict:
343 |     """Permanently delete a saved LLM connection."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/llm_connections.py:366:32
    |
364 | async def get_platform_llm_connection(
365 |     request: Request,
366 |     admin: AuthenticatedUser = Depends(get_admin_user),
    |                                ^^^^^^^^^^^^^^^^^^^^^^^
367 | ) -> dict:
368 |     """Get the currently active Platform LLM connection from the DB."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/llm_connections.py:402:32
    |
400 |     request: Request,
401 |     body: CreateLLMConnectionRequest,
402 |     admin: AuthenticatedUser = Depends(get_admin_user),
    |                                ^^^^^^^^^^^^^^^^^^^^^^^
403 | ) -> dict:
404 |     """Create or overwrite the Platform LLM connection."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/llm_connections.py:470:32
    |
468 | async def delete_platform_llm_connection(
469 |     request: Request,
470 |     admin: AuthenticatedUser = Depends(get_admin_user),
    |                                ^^^^^^^^^^^^^^^^^^^^^^^
471 | ) -> dict:
472 |     """Delete the Platform LLM connection."""
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
  --> src/engine/routers/processor_config.py:35:31
   |
33 | async def get_available_models(
34 |     request: Request,
35 |     user: AuthenticatedUser = Depends(get_admin_user),
   |                               ^^^^^^^^^^^^^^^^^^^^^^^
36 | ) -> dict:
37 |     """Available models per provider for the admin processor config.
   |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
  --> src/engine/routers/processor_config.py:74:31
   |
72 | async def get_processor_config(
73 |     request: Request,
74 |     user: AuthenticatedUser = Depends(get_admin_user),
   |                               ^^^^^^^^^^^^^^^^^^^^^^^
75 | ) -> ProcessorConfigResponse:
76 |     """Current system-level LLM provider and model configuration.
   |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/routers/processor_config.py:101:31
    |
 99 |     request: Request,
100 |     body: ProcessorConfigUpdateRequest,
101 |     user: AuthenticatedUser = Depends(get_admin_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^
102 | ) -> dict:
103 |     """Hot-swap the system-level LLM processor at runtime.
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/routers/processor_config.py:161:9
    |
159 |       except Exception as exc:
160 |           logger.error("processor_config_invalid", extra={"error": str(exc)})
161 | /         raise HTTPException(
162 | |             status_code=400,
163 | |             detail="Invalid processor configuration. Check the provider, model and limits and try again.",
164 | |         )
    | |_________^
165 |
166 |       if hasattr(container, "processor_llm_client"):
    |

E501 Line too long (124 > 120)
   --> src/engine/schemas.py:193:121
    |
191 |     platform: str = Field(
192 |         default="mt5",
193 |         description="Trading platform. Currently only 'mt5' is supported end-to-end; 'mt4' is reserved for future support.",
    |                                                                                                                         ^^^^
194 |     )
195 |     # No symbol field. The hosted provisioner runs automatic broker
    |

S105 Possible hardcoded password assigned to: "ACCESS_TOKEN_COOKIE_NAME"
  --> src/engine/shared/auth.py:71:28
   |
69 | # src/auth/cookies.go::AccessTokenCookieName. Kept in sync via
70 | # coordinated change; both services share the same auth contract.
71 | ACCESS_TOKEN_COOKIE_NAME = "access_token"
   |                            ^^^^^^^^^^^^^^
72 |
73 | # RFC 6265bis __Secure- prefix the Go gateway prepends when
   |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/shared/auth.py:194:9
    |
192 |         )
193 |     except jwt.ExpiredSignatureError:
194 |         raise HTTPException(status_code=401, detail="Token expired")
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
195 |     except jwt.InvalidIssuerError:
196 |         raise HTTPException(status_code=401, detail="Invalid token issuer")
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/shared/auth.py:196:9
    |
194 |         raise HTTPException(status_code=401, detail="Token expired")
195 |     except jwt.InvalidIssuerError:
196 |         raise HTTPException(status_code=401, detail="Invalid token issuer")
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
197 |     except jwt.InvalidTokenError as exc:
198 |         logger.warning("jwt_verification_failed", extra={"error": str(exc)})
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/shared/auth.py:199:9
    |
197 |     except jwt.InvalidTokenError as exc:
198 |         logger.warning("jwt_verification_failed", extra={"error": str(exc)})
199 |         raise HTTPException(status_code=401, detail="Invalid token")
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
200 |
201 |     user_id = payload.get("sub")
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/shared/auth.py:261:56
    |
259 | async def get_current_user(
260 |     request: Request,
261 |     credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    |                                                        ^^^^^^^^^^^^^^^^^^^^^^^
262 | ) -> AuthenticatedUser:
263 |     """FastAPI dependency: require a valid JWT from header or cookie.
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/shared/auth.py:286:56
    |
284 | async def get_optional_user(
285 |     request: Request,
286 |     credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    |                                                        ^^^^^^^^^^^^^^^^^^^^^^^
287 | ) -> AuthenticatedUser | None:
288 |     """FastAPI dependency: optionally authenticate from header or cookie.
    |

B008 Do not perform function call `Depends` in argument defaults; instead, perform the call within the function, or read the default from a module-level singleton variable
   --> src/engine/shared/auth.py:301:31
    |
300 | async def get_admin_user(
301 |     user: AuthenticatedUser = Depends(get_current_user),
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^
302 | ) -> AuthenticatedUser:
303 |     """FastAPI dependency: require admin role."""
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/shared/concurrency/background_coordinator.py:189:13
    |
187 |                       else:
188 |                           self._in_flight[key] = n
189 | /             except Exception:
190 | |                 # Bookkeeping must never propagate.
191 | |                 pass
    | |____________________^
192 |
193 |       async def shutdown(self, *, drain_timeout_s: float = 2.0) -> None:
    |

PLW0603 Using the global statement to update `_singleton` is discouraged
   --> src/engine/shared/crypto/credential_cipher.py:387:12
    |
385 |     secret delivered by the ExternalSecret.
386 |     """
387 |     global _singleton
    |            ^^^^^^^^^^
388 |     if _singleton is None:
389 |         with _singleton_lock:
    |

PLW0603 Using the global statement to update `_singleton` is discouraged
   --> src/engine/shared/crypto/credential_cipher.py:400:12
    |
398 |     Test-only seam; production never calls this.
399 |     """
400 |     global _singleton
    |            ^^^^^^^^^^
401 |     with _singleton_lock:
402 |         _singleton = None
    |

PLR0911 Too many return statements (9 > 6)
  --> src/engine/shared/csrf.py:97:5
   |
97 | def _verify_csrf(
   |     ^^^^^^^^^^^^
98 |     request: Request, header_name: str, signed: bool, secret: bytes
99 | ) -> bool:
   |

PLR0912 Too many branches (14 > 12)
  --> src/engine/shared/csrf.py:97:5
   |
97 | def _verify_csrf(
   |     ^^^^^^^^^^^^
98 |     request: Request, header_name: str, signed: bool, secret: bytes
99 | ) -> bool:
   |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/shared/csrf.py:160:9
    |
159 |     if token:
160 |         import jwt
    |         ^^^^^^^^^^
161 |
162 |         try:
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/shared/csrf.py:169:9
    |
167 |               payload = jwt.decode(token, options={"verify_signature": False})
168 |               user_id = payload.get("sub", "")
169 | /         except Exception:
170 | |             pass
    | |________________^
171 |
172 |       if not user_id:
    |

E402 Module level import not at top of file
  --> src/engine/shared/db/migrations/versions/0008_llm_connections.py:18:1
   |
18 | from sqlalchemy import inspect
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
19 |
20 | revision = "0008"
   |

PLR0912 Too many branches (15 > 12)
  --> src/engine/shared/db/migrations/versions/0008_llm_connections.py:26:5
   |
26 | def upgrade() -> None:
   |     ^^^^^^^
27 |     conn = op.get_bind()
28 |     inspector = inspect(conn)
   |

PLR0912 Too many branches (24 > 12)
  --> src/engine/shared/db/migrations/versions/0009_broker_connections_schema.py:34:5
   |
34 | def upgrade() -> None:
   |     ^^^^^^^
35 |     conn = op.get_bind()
36 |     inspector = inspect(conn)
   |

PLR0915 Too many statements (57 > 50)
  --> src/engine/shared/db/migrations/versions/0009_broker_connections_schema.py:34:5
   |
34 | def upgrade() -> None:
   |     ^^^^^^^
35 |     conn = op.get_bind()
36 |     inspector = inspect(conn)
   |

S608 Possible SQL injection vector through string-based query construction
  --> src/engine/shared/db/migrations/versions/0011_add_user_id_multi_tenant.py:81:21
   |
79 |         # these to the actual admin user ID after first startup.
80 |         op.execute(
81 |             sa.text(f"UPDATE {table_name} SET user_id = 'system' WHERE user_id IS NULL")
   |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
82 |         )
   |

PLR0912 Too many branches (15 > 12)
  --> src/engine/shared/db/migrations/versions/0012_add_user_id_to_ta_tables.py:49:5
   |
49 | def upgrade() -> None:
   |     ^^^^^^^
50 |     conn = op.get_bind()
51 |     inspector = inspect(conn)
   |

S608 Possible SQL injection vector through string-based query construction
  --> src/engine/shared/db/migrations/versions/0012_add_user_id_to_ta_tables.py:76:21
   |
74 |         # Step 2: Backfill existing rows with 'system' placeholder.
75 |         op.execute(
76 |             sa.text(f"UPDATE {table_name} SET user_id = 'system' WHERE user_id IS NULL")
   |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
77 |         )
   |

PLR0912 Too many branches (16 > 12)
   --> src/engine/shared/db/migrations/versions/0013_add_user_id_to_macro_tables.py:213:5
    |
213 | def upgrade() -> None:
    |     ^^^^^^^
214 |     conn = op.get_bind()
215 |     insp = inspect(conn)
    |

PLR0912 Too many branches (15 > 12)
   --> src/engine/shared/db/migrations/versions/0013_add_user_id_to_macro_tables.py:278:5
    |
278 | def downgrade() -> None:
    |     ^^^^^^^^^
279 |     conn = op.get_bind()
280 |     insp = inspect(conn)
    |

N806 Variable `_OLD_CONSTRAINTS_RESTORE` in function should be lowercase
   --> src/engine/shared/db/migrations/versions/0013_add_user_id_to_macro_tables.py:300:5
    |
299 |     # Phase 3: Restore old unique constraints.
300 |     _OLD_CONSTRAINTS_RESTORE = [
    |     ^^^^^^^^^^^^^^^^^^^^^^^^
301 |         ("cot_reports", "uq_cot_currency_date", ["currency", "report_date"]),
302 |         ("news_items", "uq_news_dedupe_hash", ["dedupe_hash"]),
    |

N806 Variable `_OLD_INDEXES_RESTORE` in function should be lowercase
   --> src/engine/shared/db/migrations/versions/0013_add_user_id_to_macro_tables.py:310:5
    |
309 |     # Phase 4: Restore old indexes.
310 |     _OLD_INDEXES_RESTORE = [
    |     ^^^^^^^^^^^^^^^^^^^^
311 |         ("calendar_events", "ix_cal_currency_time", ["currency", "event_time"]),
312 |         ("calendar_events", "ix_cal_event_time", ["event_time"]),
    |

ERA001 Found commented-out code
   --> src/engine/shared/db/migrations/versions/0014_candidates_schema_alignment.py:123:5
    |
121 |     )
122 |
123 |     # SnD: Marubozu
    |     ^^^^^^^^^^^^^^^
124 |     _add_if_missing(existing_columns, "marubozu_detected", sa.Boolean, nullable=True)
125 |     _add_if_missing(
    |
help: Remove commented-out code

ERA001 Found commented-out code
   --> src/engine/shared/db/migrations/versions/0014_candidates_schema_alignment.py:132:5
    |
130 |     )
131 |
132 |     # SnD: Compression
    |     ^^^^^^^^^^^^^^^^^^
133 |     _add_if_missing(existing_columns, "compression_detected", sa.Boolean, nullable=True)
134 |     _add_if_missing(
    |
help: Remove commented-out code

PLR0912 Too many branches (15 > 12)
   --> src/engine/shared/db/migrations/versions/0024_retire_economic_releases_dead_columns.py:149:5
    |
149 | def downgrade() -> None:
    |     ^^^^^^^^^
150 |     conn = op.get_bind()
151 |     insp = inspect(conn)
    |

S608 Possible SQL injection vector through string-based query construction
  --> src/engine/shared/db/migrations/versions/0026_add_user_id_to_rag_retrieval_logs.py:61:21
   |
59 |         # Step 2: Backfill existing rows with empty string (matches model default).
60 |         op.execute(
61 |             sa.text(f"UPDATE {table_name} SET user_id = '' WHERE user_id IS NULL")
   |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
62 |         )
   |

S608 Possible SQL injection vector through string-based query construction
  --> src/engine/shared/db/migrations/versions/0027_increase_llm_max_output_tokens.py:30:13
   |
28 |     op.execute(
29 |         sa.text(
30 |             f"UPDATE {_TABLE} SET max_output_tokens = 32768 WHERE max_output_tokens = 16384"
   |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
31 |         )
32 |     )
   |

S608 Possible SQL injection vector through string-based query construction
  --> src/engine/shared/db/migrations/versions/0027_increase_llm_max_output_tokens.py:39:13
   |
37 |     op.execute(
38 |         sa.text(
39 |             f"UPDATE {_TABLE} SET max_output_tokens = 16384 WHERE max_output_tokens = 32768"
   |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
40 |         )
41 |     )
   |

C408 Unnecessary `dict()` call (rewrite as a literal)
  --> src/engine/shared/db/migrations/versions/0028_tier_quota_policies.py:37:5
   |
35 |   _SEED_ROWS = [
36 |       # Pro Managed: paying tier on platform LLM key.
37 | /     dict(
38 | |         tier="pro_managed",
39 | |         daily_input_tokens=2_000_000,
40 | |         daily_output_tokens=200_000,
41 | |         monthly_input_tokens=20_000_000,
42 | |         monthly_output_tokens=2_000_000,
43 | |         max_input_tokens_per_call=300_000,
44 | |         soft_cap_percent=80,
45 | |         reservation_ttl_seconds=300,
46 | |         allowed_models=[],
47 | |         enforced=True,
48 | |     ),
   | |_____^
49 |       # Admin: shares the pro_managed envelope. Confirmed with product:
50 |       # admins consume the platform key by default; capping them on the
   |
help: Rewrite as a literal

C408 Unnecessary `dict()` call (rewrite as a literal)
  --> src/engine/shared/db/migrations/versions/0028_tier_quota_policies.py:53:5
   |
51 |       # same numbers keeps the operational ceiling visible and editable
52 |       # from the same panel.
53 | /     dict(
54 | |         tier="admin",
55 | |         daily_input_tokens=2_000_000,
56 | |         daily_output_tokens=200_000,
57 | |         monthly_input_tokens=20_000_000,
58 | |         monthly_output_tokens=2_000_000,
59 | |         max_input_tokens_per_call=300_000,
60 | |         soft_cap_percent=80,
61 | |         reservation_ttl_seconds=300,
62 | |         allowed_models=[],
63 | |         enforced=True,
64 | |     ),
   | |_____^
65 |       # Pro BYOK: user supplies their own provider key. The platform
66 |       # never debits a reservation for them; all caps zero so the
   |
help: Rewrite as a literal

C408 Unnecessary `dict()` call (rewrite as a literal)
  --> src/engine/shared/db/migrations/versions/0028_tier_quota_policies.py:70:5
   |
68 |       # reaches the handler (defense-in-depth; in normal flow the
69 |       # engine's uses_platform_key gate already short-circuits this).
70 | /     dict(
71 | |         tier="pro_byok",
72 | |         daily_input_tokens=0,
73 | |         daily_output_tokens=0,
74 | |         monthly_input_tokens=0,
75 | |         monthly_output_tokens=0,
76 | |         max_input_tokens_per_call=0,
77 | |         soft_cap_percent=0,
78 | |         reservation_ttl_seconds=300,
79 | |         allowed_models=[],
80 | |         enforced=False,
81 | |     ),
   | |_____^
82 |       # Free: same posture as pro_byok. Free users also BYOK on a
83 |       # restricted feature set.
   |
help: Rewrite as a literal

C408 Unnecessary `dict()` call (rewrite as a literal)
  --> src/engine/shared/db/migrations/versions/0028_tier_quota_policies.py:84:5
   |
82 |       # Free: same posture as pro_byok. Free users also BYOK on a
83 |       # restricted feature set.
84 | /     dict(
85 | |         tier="free",
86 | |         daily_input_tokens=0,
87 | |         daily_output_tokens=0,
88 | |         monthly_input_tokens=0,
89 | |         monthly_output_tokens=0,
90 | |         max_input_tokens_per_call=0,
91 | |         soft_cap_percent=0,
92 | |         reservation_ttl_seconds=300,
93 | |         allowed_models=[],
94 | |         enforced=False,
95 | |     ),
   | |_____^
96 |   ]
   |
help: Rewrite as a literal

UP046 Generic class `BaseRepository` uses `Generic` subclass instead of type parameters
  --> src/engine/shared/db/repositories/base_repository.py:34:22
   |
34 | class BaseRepository(Generic[ModelT]):
   |                      ^^^^^^^^^^^^^^^
35 |     """
36 |     Production-grade base repository with type safety, metrics, and error handling.
   |
help: Use type parameters

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/shared/http/client.py:98:13
    |
 96 |           """Get current circuit state with automatic recovery check."""
 97 |           async with self._lock:
 98 | /             if self._state == CircuitState.OPEN:
 99 | |                 if time.monotonic() - self._last_failure_time >= self._recovery_timeout:
    | |________________________________________________________________________________________^
100 |                       self._state = CircuitState.HALF_OPEN
101 |                       self._half_open_successes = 0
    |
help: Combine `if` statements using `and`

S104 Possible binding to all interfaces
   --> src/engine/shared/http/client.py:220:62
    |
219 |             # Security: Prevent SSRF to internal networks
220 |             if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
    |                                                              ^^^^^^^^^
221 |                 logger.warning(
222 |                     "localhost_url_detected",
    |

PLR0915 Too many statements (63 > 50)
   --> src/engine/shared/http/client.py:279:15
    |
277 |         return delay + jitter
278 |
279 |     async def request(
    |               ^^^^^^^
280 |         self,
281 |         method: str,
    |

PLR2004 Magic value used in comparison, consider replacing `429` with a constant variable
   --> src/engine/shared/http/client.py:377:39
    |
376 |                     # Handle rate limiting (429)
377 |                     if resp.status == 429:
    |                                       ^^^
378 |                         await self._handle_rate_limit(
379 |                             resp,
    |

PLR2004 Magic value used in comparison, consider replacing `500` with a constant variable
   --> src/engine/shared/http/client.py:398:39
    |
397 |                     # Handle server errors (5xx)
398 |                     if resp.status >= 500:
    |                                       ^^^
399 |                         await self._handle_server_error(
400 |                             resp,
    |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/shared/internal_auth.py:72:9
   |
70 |         # will reject every request with 401 until the secret is set,
71 |         # which is the safe default.
72 |         import logging
   |         ^^^^^^^^^^^^^^
73 |
74 |         logging.getLogger(__name__).warning(
   |

PLW0603 Using the global statement to update `_config` is discouraged
   --> src/engine/shared/metering_client.py:155:12
    |
153 |     module-level binding is acceptable.
154 |     """
155 |     global _config
    |            ^^^^^^^
156 |     cfg = _config
157 |     if cfg is not None:
    |

PLW0603 Using the global statement to update `_config` is discouraged
   --> src/engine/shared/metering_client.py:172:12
    |
170 |     regression on the LLM hot path.
171 |     """
172 |     global _config
    |            ^^^^^^^
173 |     with _config_lock:
174 |         _config = None
    |

PLR2004 Magic value used in comparison, consider replacing `429` with a constant variable
   --> src/engine/shared/metering_client.py:255:28
    |
253 |             raise
254 |
255 |     if resp.status_code == 429:
    |                            ^^^
256 |         body = _safe_json(resp)
257 |         dimension = body.get("dimension", "unknown")
    |

PLR2004 Magic value used in comparison, consider replacing `503` with a constant variable
   --> src/engine/shared/metering_client.py:275:28
    |
273 |         )
274 |
275 |     if resp.status_code == 503:
    |                            ^^^
276 |         # Gateway said the policy / metering layer is temporarily
277 |         # unavailable (transient DB error, seed-row missing, etc.).
    |

PLR2004 Magic value used in comparison, consider replacing `200` with a constant variable
   --> src/engine/shared/metering_client.py:297:28
    |
295 |         )
296 |
297 |     if resp.status_code != 200:
    |                            ^^^
298 |         logger.error(
299 |             "metering_reserve_failed",
    |

PLR2004 Magic value used in comparison, consider replacing `200` with a constant variable
   --> src/engine/shared/metering_client.py:381:32
    |
379 |                 },
380 |             )
381 |         if resp.status_code != 200:
    |                                ^^^
382 |             logger.error(
383 |                 "metering_commit_failed",
    |

PLR2004 Magic value used in comparison, consider replacing `200` with a constant variable
   --> src/engine/shared/metering_client.py:431:32
    |
429 |                 },
430 |             )
431 |         if resp.status_code != 200:
    |                                ^^^
432 |             logger.error(
433 |                 "metering_refund_failed",
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/shared/metering_client.py:476:9
    |
474 |               delta = (dt - datetime.now(UTC)).total_seconds()
475 |               return max(1, int(delta))
476 | /         except Exception:
477 | |             pass
    | |________________^
478 |       if header_value:
479 |           try:
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/shared/metering_client.py:481:9
    |
479 |           try:
480 |               return max(1, int(header_value))
481 | /         except Exception:
482 | |             pass
    | |________________^
483 |       return 60
    |

SIM105 Use `contextlib.suppress(Exception)` instead of `try`-`except`-`pass`
   --> src/engine/shared/pulse/publisher.py:111:9
    |
109 |                          pulsing caret.
110 |           """
111 | /         try:
112 | |             await self._cache.publish(
113 | |                 self._channel,
114 | |                 {
115 | |                     "type": "pulse",
116 | |                     "symbol": self._symbol,
117 | |                     "phase": phase,
118 | |                     "message": message,
119 | |                     "source": source,
120 | |                     "completed": completed,
121 | |                 },
122 | |             )
123 | |         except Exception:
124 | |             # Absolute safety net. RedisCache.publish already swallows
125 | |             # errors internally, but if anything unexpected slips through
126 | |             # (e.g. the cache object itself is in a bad state) we must
127 | |             # never let it reach the analysis pipeline.
128 | |             pass
    | |________________^
    |
help: Replace `try`-`except`-`pass` with `with contextlib.suppress(Exception): ...`

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/shared/pulse/publisher.py:123:9
    |
121 |                   },
122 |               )
123 | /         except Exception:
124 | |             # Absolute safety net. RedisCache.publish already swallows
125 | |             # errors internally, but if anything unexpected slips through
126 | |             # (e.g. the cache object itself is in a bad state) we must
127 | |             # never let it reach the analysis pipeline.
128 | |             pass
    | |________________^
    |

PLR2004 Magic value used in comparison, consider replacing `256` with a constant variable
  --> src/engine/shared/tracing/otel.py:36:28
   |
34 |         raise TracingValidationError("Service name cannot be empty")
35 |
36 |     if len(service_name) > 256:
   |                            ^^^
37 |         raise TracingValidationError("Service name exceeds maximum length of 256")
   |

PLR2004 Magic value used in comparison, consider replacing `65535` with a constant variable
  --> src/engine/shared/tracing/otel.py:75:38
   |
73 |                 )
74 |             port_num = int(port_part)
75 |             if not (1 <= port_num <= 65535):
   |                                      ^^^^^
76 |                 raise TracingValidationError(
77 |                     f"Invalid OTLP endpoint: port out of range in {endpoint!r}"
   |

PLW0603 Using the global statement to update `_tracer` is discouraged
   --> src/engine/shared/tracing/otel.py:98:12
    |
 96 |     max_export_batch_size: int = 512,
 97 | ) -> None:
 98 |     global _tracer, _provider
    |            ^^^^^^^
 99 |
100 |     _validate_service_name(service_name)
    |

PLW0603 Using the global statement to update `_provider` is discouraged
   --> src/engine/shared/tracing/otel.py:98:21
    |
 96 |     max_export_batch_size: int = 512,
 97 | ) -> None:
 98 |     global _tracer, _provider
    |                     ^^^^^^^^^
 99 |
100 |     _validate_service_name(service_name)
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/shared/tracing/otel.py:135:9
    |
133 |           # the dependency is only touched on the tracing-enabled path.
134 |           # ZeroMQ to mt-node is NOT instrumented (non-HTTP, opaque).
135 | /         from opentelemetry.instrumentation.aiohttp_client import (
136 | |             AioHttpClientInstrumentor,
137 | |         )
    | |_________^
138 |
139 |           AioHttpClientInstrumentor().instrument()
    |

PLW0603 Using the global statement to update `_tracer` is discouraged
   --> src/engine/shared/tracing/otel.py:161:12
    |
160 | def get_tracer() -> Tracer:
161 |     global _tracer
    |            ^^^^^^^
162 |
163 |     if _tracer is None:
    |

PLW0602 Using global for `_provider` but no assignment is done
   --> src/engine/shared/tracing/otel.py:203:12
    |
202 | def shutdown_tracing(timeout_seconds: int = 30) -> None:
203 |     global _provider
    |            ^^^^^^^^^
204 |
205 |     try:
    |

S105 Possible hardcoded password assigned to: "_DEFAULT_SA_TOKEN_PATH"
  --> src/engine/shared/vault/client.py:37:26
   |
35 | logger = get_logger(__name__)
36 |
37 | _DEFAULT_SA_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
   |                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
38 | _DEFAULT_K8S_AUTH_PATH = "kubernetes"
39 | _DEFAULT_KV_MOUNT = "etradie"
   |

PLR0912 Too many branches (35 > 12)
  --> src/engine/signal_extractors.py:15:5
   |
15 | def derive_macro_signals(macro: dict) -> dict:
   |     ^^^^^^^^^^^^^^^^^^^^
16 |     """Derive enriched macro signal flags from raw macro collection output.
   |

PLR0915 Too many statements (107 > 50)
  --> src/engine/signal_extractors.py:15:5
   |
15 | def derive_macro_signals(macro: dict) -> dict:
   |     ^^^^^^^^^^^^^^^^^^^^
16 |     """Derive enriched macro signal flags from raw macro collection output.
   |

PLR0912 Too many branches (47 > 12)
   --> src/engine/signal_extractors.py:220:5
    |
220 | def derive_ta_signals(ta: dict) -> dict:
    |     ^^^^^^^^^^^^^^^^^
221 |     """Derive TA signal flags from raw TA analysis output.
    |

PLR0915 Too many statements (97 > 50)
   --> src/engine/signal_extractors.py:220:5
    |
220 | def derive_ta_signals(ta: dict) -> dict:
    |     ^^^^^^^^^^^^^^^^^
221 |     """Derive TA signal flags from raw TA analysis output.
    |

S311 Standard pseudo-random generators are not suitable for cryptographic purposes
  --> src/engine/ta/broker/connectivity/reconnect.py:70:16
   |
68 |             return 0.0
69 |         schedule = min(self.cap_secs, self.base_secs * (2 ** (attempt - 1)))
70 |         return random.uniform(0.0, schedule)
   |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
71 |
72 |     def exhausted(self, attempt: int) -> bool:
   |

PLR2004 Magic value used in comparison, consider replacing `12` with a constant variable
   --> src/engine/ta/broker/mt5/client_pool.py:142:61
    |
140 |                     "account_id": (
141 |                         (account_id[:12] + "...")
142 |                         if account_id and len(account_id) > 12
    |                                                             ^^
143 |                         else (account_id or "unknown")
144 |                     ),
    |

SIM105 Use `contextlib.suppress(asyncio.CancelledError, Exception)` instead of `try`-`except`-`pass`
   --> src/engine/ta/broker/mt5/client_pool.py:228:13
    |
226 |           if self._sweeper is not None:
227 |               self._sweeper.cancel()
228 | /             try:
229 | |                 await self._sweeper
230 | |             except (asyncio.CancelledError, Exception):
231 | |                 pass
    | |____________________^
232 |               self._sweeper = None
233 |           # Snapshot and clear to avoid mutation-during-iteration.
    |
help: Replace `try`-`except`-`pass` with `with contextlib.suppress(asyncio.CancelledError, Exception): ...`

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/ta/broker/mt5/client_pool.py:230:13
    |
228 |               try:
229 |                   await self._sweeper
230 | /             except (asyncio.CancelledError, Exception):
231 | |                 pass
    | |____________________^
232 |               self._sweeper = None
233 |           # Snapshot and clear to avoid mutation-during-iteration.
    |

SIM102 Use a single `if` statement instead of nested `if` statements
  --> src/engine/ta/broker/mt5/config.py:82:9
   |
80 |           via the MetaAPI Provisioning API and stored in the database.
81 |           """
82 | /         if self.provider == "metaapi":
83 | |             if not self.metaapi_token:
   | |______________________________________^
84 |                   raise ValueError(
85 |                       "MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi"
   |
help: Combine `if` statements using `and`

PLR1714 Consider merging multiple comparisons. Use a `set` if the elements are hashable.
   --> src/engine/ta/broker/mt5/ea_identity.py:117:13
    |
116 |           if (
117 | /             expected.magic_number != 0
118 | |             and observed.magic_number != expected.magic_number
    | |______________________________________________________________^
119 |           ):
120 |               mismatches["magic"] = (expected.magic_number, observed.magic_number)
    |
help: Merge multiple comparisons

PLR2004 Magic value used in comparison, consider replacing `3` with a constant variable
   --> src/engine/ta/broker/mt5/ea_identity.py:209:24
    |
207 |                 break
208 |         parts.append(int(digits) if digits else 0)
209 |     while len(parts) < 3:
    |                        ^
210 |         parts.append(0)
211 |     return tuple(parts[:3])
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/broker/mt5/factory.py:195:9
    |
193 |                 details={"provider": config.provider},
194 |             )
195 |         from engine.ta.broker.mt5.metaapi.client import MetaApiClient
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
196 |
197 |         acct_id = config.metaapi_account_id
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/broker/mt5/factory.py:213:9
    |
212 |     if config.provider == "native":
213 |         from engine.ta.broker.mt5.zmq.client import ZmqClient
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
214 |
215 |         endpoint_account = f"{config.zmq_host}:{config.zmq_port}"
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/broker/mt5/factory.py:310:9
    |
308 |         )
309 |
310 |         from engine.ta.broker.mt5.zmq.client import ZmqClient
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
311 |
312 |         endpoint_account = f"{row.ea_host}:{row.ea_port}"
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/broker/mt5/factory.py:370:9
    |
368 |         )
369 |
370 |         from engine.ta.broker.mt5.metaapi.client import MetaApiClient
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
371 |
372 |         client = MetaApiClient(
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/broker/mt5/factory.py:427:9
    |
425 |           # re-provision it. Until then, ZmqClient calls will fail with
426 |           # ProviderTimeoutError, which the caller surfaces to the user.
427 | /         from engine.ta.broker.mt5.hosted.provisioner import (
428 | |             namespace_default,
429 | |             service_dns_for,
430 | |         )
    | |_________^
431 |
432 |           zmq_host = service_dns_for(row.hosted_container_id, namespace_default())
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/broker/mt5/factory.py:490:9
    |
488 |         )
489 |
490 |         from engine.ta.broker.mt5.zmq.client import ZmqClient
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
491 |
492 |         client = ZmqClient(
    |

SIM105 Use `contextlib.suppress(Exception)` instead of `try`-`except`-`pass`
   --> src/engine/ta/broker/mt5/hosted/provisioner.py:352:9
    |
350 |       @staticmethod
351 |       async def _close(api) -> None:
352 | /         try:
353 | |             await api.api_client.close()
354 | |         except Exception:  # noqa: BLE001
355 | |             pass
    | |________________^
356 |
357 |       # -- Naming + label helpers ---------------------------------------------
    |
help: Replace `try`-`except`-`pass` with `with contextlib.suppress(Exception): ...`

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/ta/broker/mt5/hosted/provisioner.py:354:9
    |
352 |           try:
353 |               await api.api_client.close()
354 | /         except Exception:  # noqa: BLE001
355 | |             pass
    | |________________^
356 |
357 |       # -- Naming + label helpers ---------------------------------------------
    |

PLR2004 Magic value used in comparison, consider replacing `404` with a constant variable
   --> src/engine/ta/broker/mt5/hosted/provisioner.py:677:34
    |
675 |                 )
676 |             except ApiException as exc:
677 |                 if exc.status == 404:
    |                                  ^^^
678 |                     return {
679 |                         "container_id": container_id,
    |

PLR2004 Magic value used in comparison, consider replacing `409` with a constant variable
   --> src/engine/ta/broker/mt5/hosted/provisioner.py:951:38
    |
949 |                     return
950 |                 except ApiException as exc:
951 |                     if exc.status == 409:
    |                                      ^^^
952 |                         existing = await core_api.read_namespaced_config_map(
953 |                             name=name,
    |

PLR2004 Magic value used in comparison, consider replacing `409` with a constant variable
    --> src/engine/ta/broker/mt5/hosted/provisioner.py:1000:38
     |
 998 |                     return
 999 |                 except ApiException as exc:
1000 |                     if exc.status == 409:
     |                                      ^^^
1001 |                         existing = await core_api.read_namespaced_service_account(
1002 |                             name=name,
     |

S108 Probable insecure usage of temporary file or directory: "/tmp"
    --> src/engine/ta/broker/mt5/hosted/provisioner.py:1166:61
     |
1164 |                 ),
1165 |                 client.V1VolumeMount(name="mt-cache", mount_path="/home/mt/.cache"),
1166 |                 client.V1VolumeMount(name="tmp", mount_path="/tmp"),
     |                                                             ^^^^^^
1167 |                 client.V1VolumeMount(name="var-tmp", mount_path="/var/tmp"),
1168 |             ],
     |

S108 Probable insecure usage of temporary file or directory: "/var/tmp"
    --> src/engine/ta/broker/mt5/hosted/provisioner.py:1167:65
     |
1165 |                 client.V1VolumeMount(name="mt-cache", mount_path="/home/mt/.cache"),
1166 |                 client.V1VolumeMount(name="tmp", mount_path="/tmp"),
1167 |                 client.V1VolumeMount(name="var-tmp", mount_path="/var/tmp"),
     |                                                                 ^^^^^^^^^^
1168 |             ],
1169 |         )
     |

S108 Probable insecure usage of temporary file or directory: "/tmp"
    --> src/engine/ta/broker/mt5/hosted/provisioner.py:1252:61
     |
1250 |             volume_mounts=[
1251 |                 # Watchdog only needs /tmp (for any transient writes).
1252 |                 client.V1VolumeMount(name="tmp", mount_path="/tmp"),
     |                                                             ^^^^^^
1253 |             ],
1254 |         )
     |

PLR2004 Magic value used in comparison, consider replacing `409` with a constant variable
    --> src/engine/ta/broker/mt5/hosted/provisioner.py:1450:38
     |
1448 |                     return
1449 |                 except ApiException as exc:
1450 |                     if exc.status == 409:
     |                                      ^^^
1451 |                         await apps_api.replace_namespaced_stateful_set(
1452 |                             name=release,
     |

PLR2004 Magic value used in comparison, consider replacing `409` with a constant variable
    --> src/engine/ta/broker/mt5/hosted/provisioner.py:1520:38
     |
1518 |                     return
1519 |                 except ApiException as exc:
1520 |                     if exc.status == 409:
     |                                      ^^^
1521 |                         existing = await core_api.read_namespaced_service(
1522 |                             name=name,
     |

ASYNC109 Async function definition with a `timeout` parameter
    --> src/engine/ta/broker/mt5/hosted/provisioner.py:1552:9
     |
1550 |         zmq_port: int,
1551 |         token: str,
1552 |         timeout: float,
     |         ^^^^^^^^^^^^^^
1553 |     ) -> None:
1554 |         """Block until StatefulSet has a Ready replica AND ZMQ PING
     |
help: Use `asyncio.timeout` instead

SIM105 Use `contextlib.suppress(Exception)` instead of `try`-`except`-`pass`
    --> src/engine/ta/broker/mt5/hosted/provisioner.py:1791:13
     |
1789 |               return False
1790 |           finally:
1791 | /             try:
1792 | |                 sock.close(linger=0)
1793 | |             except Exception:  # noqa: BLE001
1794 | |                 pass
     | |____________________^
1795 |
1796 |       # -- Internal: deletion helpers -----------------------------------------
     |
help: Replace `try`-`except`-`pass` with `with contextlib.suppress(Exception): ...`

S110 `try`-`except`-`pass` detected, consider logging the exception
    --> src/engine/ta/broker/mt5/hosted/provisioner.py:1793:13
     |
1791 |               try:
1792 |                   sock.close(linger=0)
1793 | /             except Exception:  # noqa: BLE001
1794 | |                 pass
     | |____________________^
1795 |
1796 |       # -- Internal: deletion helpers -----------------------------------------
     |

PLR2004 Magic value used in comparison, consider replacing `404` with a constant variable
    --> src/engine/ta/broker/mt5/hosted/provisioner.py:1804:30
     |
1802 |             return True
1803 |         except ApiException as exc:
1804 |             if exc.status == 404:
     |                              ^^^
1805 |                 return True
1806 |             logger.warning(
     |

PLR2004 Magic value used in comparison, consider replacing `404` with a constant variable
    --> src/engine/ta/broker/mt5/hosted/provisioner.py:1857:34
     |
1855 |                 await fn(name=name, namespace=self._namespace)
1856 |             except ApiException as exc:
1857 |                 if exc.status != 404:
     |                                  ^^^
1858 |                     logger.warning(
1859 |                         "hosted_rollback_warning",
     |

SIM105 Use `contextlib.suppress(asyncio.CancelledError, Exception)` instead of `try`-`except`-`pass`
   --> src/engine/ta/broker/mt5/hosted/recovery.py:270:13
    |
268 |           if task is not None and not task.done():
269 |               task.cancel()
270 | /             try:
271 | |                 await task
272 | |             except (asyncio.CancelledError, Exception):  # noqa: BLE001
273 | |                 pass
    | |____________________^
274 |           self._task = None
    |
help: Replace `try`-`except`-`pass` with `with contextlib.suppress(asyncio.CancelledError, Exception): ...`

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/ta/broker/mt5/hosted/recovery.py:272:13
    |
270 |               try:
271 |                   await task
272 | /             except (asyncio.CancelledError, Exception):  # noqa: BLE001
273 | |                 pass
    | |____________________^
274 |           self._task = None
    |

PLR0915 Too many statements (56 > 50)
   --> src/engine/ta/broker/mt5/hosted/recovery.py:302:15
    |
300 |     # ---- Core sweep ----------------------------------------------------
301 |
302 |     async def _sweep(self, *, phase: str, bypass_threshold: bool) -> dict[str, int]:
    |               ^^^^^^
303 |         """One pass over every active hosted broker_connections row."""
304 |         rows = await self._list_active_hosted_rows()
    |

SIM108 Use ternary operator `reason = "missing" if sts_status == "removed" else "unhealthy"` instead of `if`-`else`-block
   --> src/engine/ta/broker/mt5/hosted/recovery.py:351:13
    |
350 |               # Decide the reason and whether we are allowed to act.
351 | /             if sts_status == "removed":
352 | |                 reason = "missing"
353 | |             else:
354 | |                 reason = "unhealthy"
    | |____________________________________^
355 |
356 |               # First-observed-unhealthy bookkeeping.
    |
help: Replace `if`-`else`-block with `reason = "missing" if sts_status == "removed" else "unhealthy"`

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/ta/broker/mt5/hosted/recovery.py:360:13
    |
358 |               age_secs = now_mono - first_seen
359 |
360 | /             if not bypass_threshold and reason == "unhealthy":
361 | |                 if age_secs < self._config.unhealthy_threshold_secs:
    | |____________________________________________________________________^
362 |                       # Still inside the kubelet's normal backoff envelope.
363 |                       logger.info(
    |
help: Combine `if` statements using `and`

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/broker/mt5/metaapi/client.py:581:9
    |
580 |     async def get_history(self, days: int = 30) -> list[HistoryDealInfo]:
581 |         from datetime import timedelta
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
582 |
583 |         end_time = datetime.now(UTC)
    |

E722 Do not use bare `except`
   --> src/engine/ta/broker/mt5/metaapi/client.py:620:17
    |
618 |                     ts = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
619 |                     deal_time = int(ts.timestamp())
620 |                 except:
    |                 ^^^^^^
621 |                     pass
    |

S110 `try`-`except`-`pass` detected, consider logging the exception
   --> src/engine/ta/broker/mt5/metaapi/client.py:620:17
    |
618 |                       ts = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
619 |                       deal_time = int(ts.timestamp())
620 | /                 except:
621 | |                     pass
    | |________________________^
622 |
623 |               history.append(
    |

F841 Local variable `raw` is assigned to but never used
   --> src/engine/ta/broker/mt5/metaapi/client.py:814:13
    |
813 |         try:
814 |             raw = await self._api_post("/trade", payload, category="order_cancel")
    |             ^^^
815 |         except Exception as e:
816 |             logger.error(
    |
help: Remove assignment to unused variable `raw`

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/broker/mt5/zmq/client.py:245:9
    |
243 |     ) -> dict[str, Any] | list[Any]:
244 |         """Shared send/recv implementation parameterised by socket."""
245 |         import json
    |         ^^^^^^^^^^^
246 |
247 |         if sock is None:
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/ta/broker/mt5/zmq/client.py:258:13
    |
256 |                   await sock.send(payload)
257 |           except TimeoutError:
258 | /             raise ProviderTimeoutError(
259 | |                 "ZMQ send timed out",
260 | |                 details={
261 | |                     "endpoint": self._endpoint,
262 | |                     "socket": socket_label,
263 | |                     "timeout": self.config.timeout_seconds,
264 | |                 },
265 | |             )
    | |_____________^
266 |
267 |           try:
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/ta/broker/mt5/zmq/client.py:271:13
    |
269 |                   raw_reply = await sock.recv()
270 |           except TimeoutError:
271 | /             raise ProviderTimeoutError(
272 | |                 "ZMQ recv timed out",
273 | |                 details={
274 | |                     "endpoint": self._endpoint,
275 | |                     "socket": socket_label,
276 | |                     "timeout": self.config.timeout_seconds,
277 | |                 },
278 | |             )
    | |_____________^
279 |
280 |           decoded_reply = raw_reply.decode("utf-8")
    |

SIM108 Use ternary operator `reply = [] if not decoded_reply else json.loads(decoded_reply)` instead of `if`-`else`-block
   --> src/engine/ta/broker/mt5/zmq/client.py:281:9
    |
280 |           decoded_reply = raw_reply.decode("utf-8")
281 | /         if not decoded_reply:
282 | |             reply = []
283 | |         else:
284 | |             reply = json.loads(decoded_reply)
    | |_____________________________________________^
285 |
286 |           # Check for EA-level errors.
    |
help: Replace `if`-`else`-block with `reply = [] if not decoded_reply else json.loads(decoded_reply)`

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/broker/mt5/zmq/client.py:293:9
    |
291 |             )
292 |
293 |         from typing import cast
    |         ^^^^^^^^^^^^^^^^^^^^^^^
294 |
295 |         return cast(dict[str, Any] | list[Any], reply)
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/ta/broker/mt5/zmq/client.py:337:17
    |
335 |                       account_id=self.account_id,
336 |                   ).inc()
337 | /                 raise ProviderTimeoutError(
338 | |                     "in-flight gate exhausted before deadline",
339 | |                     details={
340 | |                         "endpoint": self._endpoint,
341 | |                         "gate_deadline_secs": gate_deadline,
342 | |                         "inflight_limit": self._inflight_limit,
343 | |                     },
344 | |                 )
    | |_________________^
345 |               BROKER_INFLIGHT_GATE_WAIT_SECONDS.labels(provider="zmq").observe(
346 |                   _time.monotonic() - gate_start
    |

PLR0912 Too many branches (16 > 12)
   --> src/engine/ta/broker/mt5/zmq/client.py:357:15
    |
355 |                 self._inflight_gate.release()
356 |
357 |     async def _request_inner(
    |               ^^^^^^^^^^^^^^
358 |         self,
359 |         request: dict[str, Any],
    |

PLR0915 Too many statements (52 > 50)
   --> src/engine/ta/broker/mt5/zmq/client.py:357:15
    |
355 |                 self._inflight_gate.release()
356 |
357 |     async def _request_inner(
    |               ^^^^^^^^^^^^^^
358 |         self,
359 |         request: dict[str, Any],
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> src/engine/ta/broker/mt5/zmq/client.py:436:21
    |
434 |                           account_id=self.account_id,
435 |                       ).inc()
436 | /                     raise ProviderTimeoutError(
437 | |                         "request deadline elapsed waiting for EA reply",
438 | |                         details={
439 | |                             "endpoint": self._endpoint,
440 | |                             "request_deadline_secs": request_deadline_secs,
441 | |                         },
442 | |                     )
    | |_____________________^
443 |                   except ProviderResponseError as e:
444 |                       # Re-auth inline if the EA was restarted (ZMQ socket is stateless, so EA forgets us)
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/broker/mt5/zmq/client.py:975:21
    |
973 |               if 0.0 <= since_connect <= self._tick_recovery_window_secs:
974 |                   try:
975 | /                     from engine.shared.metrics.prometheus import (
976 | |                         BROKER_TICK_FETCH_RECOVERY_TOTAL,
977 | |                     )
    | |_____________________^
978 |
979 |                       BROKER_TICK_FETCH_RECOVERY_TOTAL.labels(
    |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/ta/broker/tradingview/config.py:50:9
   |
48 |     @classmethod
49 |     def validate_allowed_ips(cls, v: list[str]) -> list[str]:
50 |         import ipaddress
   |         ^^^^^^^^^^^^^^^^
51 |
52 |         validated = []
   |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
  --> src/engine/ta/broker/tradingview/config.py:62:21
   |
60 |                     validated.append(ip)
61 |                 except ValueError:
62 |                     raise ValueError(f"Invalid IP address or network: {ip}")
   |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
63 |
64 |         return validated
   |

PLR2004 Magic value used in comparison, consider replacing `6` with a constant variable
   --> src/engine/ta/broker/twelve_data/client.py:478:24
    |
477 |         # Clean pair - standard 6-char forex/metals symbol
478 |         if len(raw) == 6 and raw.isalpha():
    |                        ^
479 |             return f"{raw[:3]}/{raw[3:]}"
    |

PLR2004 Magic value used in comparison, consider replacing `6` with a constant variable
   --> src/engine/ta/broker/twelve_data/client.py:483:23
    |
481 |         # Broker-suffixed symbol - the base pair is always the first
482 |         # 6 alphabetic characters (e.g. XAUUSDm -> XAUUSD, EURUSDpro -> EURUSD)
483 |         if len(raw) > 6:
    |                       ^
484 |             base = raw[:6]
485 |             if base.isalpha():
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/broker/validator.py:101:29
    |
100 |     def _validate_timestamp_continuity(self, sequence: CandleSequence) -> None:
101 |         if sequence.count < 2:
    |                             ^
102 |             return
    |

DTZ005 `datetime.datetime.now()` called without a `tz` argument
   --> src/engine/ta/broker/validator.py:252:62
    |
252 |             _now = datetime.now(UTC) if end_time.tzinfo else datetime.now()
    |                                                              ^^^^^^^^^^^^^^
253 |             if end_time > _now:
254 |                 raise ProviderValidationError(
    |
help: Pass a `datetime.timezone` object to the `tz` parameter

PLC0415 `import` should be at the top-level of a file
  --> src/engine/ta/common/analyzers/candles.py:76:9
   |
74 |         min_displacement_pips: float = 20.0,
75 |     ) -> list[tuple[int, float]]:
76 |         from engine.ta.common.utils.price.math import calculate_pips
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
77 |
78 |         displacements = []
   |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/ta/common/analyzers/compression.py:64:13
   |
62 |             temp_low = min(low, current.low)
63 |
64 |             from engine.ta.common.utils.price.math import calculate_pips
   |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
65 |
66 |             temp_range_pips = calculate_pips(temp_low, temp_high, current.symbol)
   |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/common/analyzers/compression.py:142:9
    |
140 |         high = max(c.high for c in candles)
141 |
142 |         from engine.ta.common.utils.price.math import calculate_pips
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
143 |
144 |         range_pips = calculate_pips(low, high, symbol)
    |

SIM103 Return the negated condition directly
   --> src/engine/ta/common/analyzers/compression.py:146:9
    |
144 |           range_pips = calculate_pips(low, high, symbol)
145 |
146 | /         if range_pips < self.min_range_pips or range_pips > self.max_range_pips:
147 | |             return False
148 | |
149 | |         return True
    | |___________________^
150 |
151 |       def is_valid_compression(
    |
help: Inline condition

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/common/analyzers/compression.py:158:9
    |
156 |             return False
157 |
158 |         from engine.ta.common.utils.price.math import calculate_pips
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
159 |
160 |         range_pips = calculate_pips(
    |

SIM103 Return the negated condition directly
   --> src/engine/ta/common/analyzers/compression.py:166:9
    |
164 |           )
165 |
166 | /         if range_pips < self.min_range_pips or range_pips > self.max_range_pips:
167 | |             return False
168 | |
169 | |         return True
    | |___________________^
170 |
171 |       def get_compression_midpoint(self, compression: CompressionEvent) -> float:
    |
help: Inline condition

PLC0415 `import` should be at the top-level of a file
  --> src/engine/ta/common/analyzers/dealing_range.py:27:9
   |
25 |         session_range: SessionRange,
26 |     ) -> DealingRange | None:
27 |         from engine.ta.common.utils.price.math import calculate_pips
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
28 |
29 |         range_pips = calculate_pips(
   |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/ta/common/analyzers/dealing_range.py:65:9
   |
63 |         low = min(c.low for c in range_candles)
64 |
65 |         from engine.ta.common.utils.price.math import calculate_pips
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
66 |
67 |         range_pips = calculate_pips(low, high, sequence.symbol)
   |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/common/analyzers/dealing_range.py:109:9
    |
107 |         dealing_range: DealingRange,
108 |     ) -> float:
109 |         from engine.ta.common.utils.price.math import calculate_pips
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
110 |
111 |         return calculate_pips(
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/common/analyzers/liquidity.py:212:9
    |
210 |         target_pool: LiquidityPool,
211 |     ) -> float:
212 |         from engine.ta.common.utils.price.math import calculate_pips
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
213 |
214 |         return calculate_pips(
    |

PLC0415 `import` should be at the top-level of a file
  --> src/engine/ta/common/analyzers/marubozu.py:65:9
   |
63 |             return False
64 |
65 |         from engine.ta.common.utils.price.math import calculate_pips
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
66 |
67 |         displacement = calculate_pips(
   |

SIM103 Return the condition `not displacement < self.min_displacement_pips` directly
  --> src/engine/ta/common/analyzers/marubozu.py:73:9
   |
71 |           )
72 |
73 | /         if displacement < self.min_displacement_pips:
74 | |             return False
75 | |
76 | |         return True
   | |___________________^
77 |
78 |       def is_marubozu_for_timeframe(
   |
help: Replace with `return not displacement < self.min_displacement_pips`

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/common/analyzers/marubozu.py:106:9
    |
104 |             return False
105 |
106 |         from engine.ta.common.utils.price.math import calculate_pips
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
107 |
108 |         displacement = calculate_pips(
    |

SIM103 Return the condition `not displacement < scaled_threshold` directly
   --> src/engine/ta/common/analyzers/marubozu.py:117:9
    |
115 |           scaled_threshold = self.min_displacement_pips * scale
116 |
117 | /         if displacement < scaled_threshold:
118 | |             return False
119 | |
120 | |         return True
    | |___________________^
121 |
122 |       def is_bullish_marubozu(self, candle: Candle) -> bool:
    |
help: Replace with `return not displacement < scaled_threshold`

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/common/analyzers/marubozu.py:199:9
    |
197 |         end_candle = sequence.candles[end_idx]
198 |
199 |         from engine.ta.common.utils.price.math import calculate_pips
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
200 |
201 |         if start_candle.is_bullish:
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/common/analyzers/marubozu.py:228:13
    |
226 |                 continue
227 |
228 |             from engine.ta.common.utils.price.math import calculate_pips
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
229 |
230 |             displacement = calculate_pips(
    |

PLR0912 Too many branches (27 > 12)
  --> src/engine/ta/common/analyzers/sweeps.py:93:9
   |
91 |         )
92 |
93 |     def detect_sweeps_in_sequence(
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^
94 |         self,
95 |         sequence: CandleSequence,
   |

PLR0915 Too many statements (58 > 50)
  --> src/engine/ta/common/analyzers/sweeps.py:93:9
   |
91 |         )
92 |
93 |     def detect_sweeps_in_sequence(
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^
94 |         self,
95 |         sequence: CandleSequence,
   |

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/ta/common/analyzers/sweeps.py:126:17
    |
125 |                   # Check PDH
126 | /                 if pdh not in invalidated_highs:
127 | |                     if candle.high > pdh:
    | |_________________________________________^
128 |                           if candle.close <= pdh:  # VALID SWEEP
129 |                               sweep_pips = calculate_pips(pdh, candle.high, candle.symbol)
    |
help: Combine `if` statements using `and`

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/ta/common/analyzers/sweeps.py:155:17
    |
154 |                   # Check PDL
155 | /                 if pdl not in invalidated_lows:
156 | |                     if candle.low < pdl:
    | |________________________________________^
157 |                           if candle.close >= pdl:  # VALID SWEEP
158 |                               sweep_pips = calculate_pips(candle.low, pdl, candle.symbol)
    |
help: Combine `if` statements using `and`

PLR2004 Magic value used in comparison, consider replacing `5` with a constant variable
   --> src/engine/ta/common/analyzers/sweeps.py:191:82
    |
189 |                         if sweep:
190 |                             sweep = sweep.model_copy(
191 |                                 update={"is_major_sweep": swing_high.strength >= 5}
    |                                                                                  ^
192 |                             )
193 |                             sweeps.append(sweep)
    |

PLR2004 Magic value used in comparison, consider replacing `5` with a constant variable
   --> src/engine/ta/common/analyzers/sweeps.py:207:81
    |
205 |                         if sweep:
206 |                             sweep = sweep.model_copy(
207 |                                 update={"is_major_sweep": swing_low.strength >= 5}
    |                                                                                 ^
208 |                             )
209 |                             sweeps.append(sweep)
    |

PLR2004 Magic value used in comparison, consider replacing `14` with a constant variable
   --> src/engine/ta/common/analyzers/swings.py:207:30
    |
205 |         total_dominated = left_count + right_count
206 |
207 |         if total_dominated < 14:
    |                              ^^
208 |             return 3  # Extremely minor
209 |         if total_dominated < 20:
    |

PLR2004 Magic value used in comparison, consider replacing `20` with a constant variable
   --> src/engine/ta/common/analyzers/swings.py:209:30
    |
207 |         if total_dominated < 14:
208 |             return 3  # Extremely minor
209 |         if total_dominated < 20:
    |                              ^^
210 |             return 5  # Minor internal
211 |         if total_dominated < 30:
    |

PLR2004 Magic value used in comparison, consider replacing `30` with a constant variable
   --> src/engine/ta/common/analyzers/swings.py:211:30
    |
209 |         if total_dominated < 20:
210 |             return 5  # Minor internal
211 |         if total_dominated < 30:
    |                              ^^
212 |             return 7  # Intermediate
213 |         if total_dominated < 40:
    |

PLR2004 Magic value used in comparison, consider replacing `40` with a constant variable
   --> src/engine/ta/common/analyzers/swings.py:213:30
    |
211 |         if total_dominated < 30:
212 |             return 7  # Intermediate
213 |         if total_dominated < 40:
    |                              ^^
214 |             return 8  # Standard structural (CHOCH max cutoff)
215 |         if total_dominated < 50:
    |

PLR2004 Magic value used in comparison, consider replacing `50` with a constant variable
   --> src/engine/ta/common/analyzers/swings.py:215:30
    |
213 |         if total_dominated < 40:
214 |             return 8  # Standard structural (CHOCH max cutoff)
215 |         if total_dominated < 50:
    |                              ^^
216 |             return 9  # Strong structural
217 |         return 10  # Major macro structural pivot
    |

PLR2004 Magic value used in comparison, consider replacing `5` with a constant variable
   --> src/engine/ta/common/analyzers/swings.py:229:58
    |
228 |         recent_highs = (
229 |             existing_highs[-5:] if len(existing_highs) > 5 else existing_highs
    |                                                          ^
230 |         )
    |

PLR2004 Magic value used in comparison, consider replacing `5` with a constant variable
   --> src/engine/ta/common/analyzers/swings.py:252:66
    |
250 |             return False
251 |
252 |         recent_lows = existing_lows[-5:] if len(existing_lows) > 5 else existing_lows
    |                                                                  ^
253 |
254 |         for swing_low in recent_lows:
    |

PLR2004 Magic value used in comparison, consider replacing `50.0` with a constant variable
   --> src/engine/ta/common/services/alignment/service.py:110:38
    |
108 |         nesting_percentage = (nested_count / len(ltf_zones)) * 100 if ltf_zones else 0
109 |
110 |         return nesting_percentage >= 50.0
    |                                      ^^^^
111 |
112 |     def _get_all_zones(self, snapshot: TechnicalSnapshot) -> list[Zone]:
    |

PLR2004 Magic value used in comparison, consider replacing `10` with a constant variable
   --> src/engine/ta/common/services/ltf_confirmation/service.py:221:53
    |
219 |                 self.LTF_LOOKBACK,
220 |             )
221 |             if sequence is None or sequence.count < 10:
    |                                                     ^^
222 |                 elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
223 |                 return LTFConfirmationResponse(
    |

PLR2004 Magic value used in comparison, consider replacing `5` with a constant variable
   --> src/engine/ta/common/services/ltf_confirmation/service.py:353:49
    |
351 |         )
352 |
353 |         if sequence is None or sequence.count < 5:
    |                                                 ^
354 |             # Cannot validate -> assume still valid (fail-open).
355 |             # Better to attempt the trade than to block it because
    |

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/ta/common/services/ltf_confirmation/service.py:480:13
    |
478 |                   if candle.close < ob_lower:
479 |                       return False
480 | /             elif direction == Direction.BEARISH:
481 | |                 # Bearish OB (supply): mitigated once price CLOSES
482 | |                 # completely above the zone's high.
483 | |                 if candle.close > ob_upper:
    | |___________________________________________^
484 |                       return False
    |
help: Combine `if` statements using `and`

PLR2004 Magic value used in comparison, consider replacing `10` with a constant variable
   --> src/engine/ta/common/services/ltf_confirmation/service.py:579:63
    |
577 |         # Older candles predate the watcher arming.
578 |         recent = (
579 |             sequence.candles[-10:] if len(sequence.candles) > 10 else sequence.candles
    |                                                               ^^
580 |         )
    |

PLR0911 Too many return statements (12 > 6)
   --> src/engine/ta/common/services/snapshot/builder.py:149:9
    |
147 |         return snapshot
148 |
149 |     def _determine_trend_direction(
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^
150 |         self,
151 |         candles: CandleSequence,
    |

PLR0912 Too many branches (15 > 12)
   --> src/engine/ta/common/services/snapshot/builder.py:149:9
    |
147 |         return snapshot
148 |
149 |     def _determine_trend_direction(
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^
150 |         self,
151 |         candles: CandleSequence,
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/common/services/snapshot/builder.py:250:33
    |
248 |         recent_lows = sorted(swing_lows, key=lambda x: x.timestamp)[-3:]
249 |
250 |         if len(recent_highs) >= 2:
    |                                 ^
251 |             higher_highs = all(
252 |                 recent_highs[i].price > recent_highs[i - 1].price
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/common/services/snapshot/builder.py:258:32
    |
256 |                 return Direction.BULLISH
257 |
258 |         if len(recent_lows) >= 2:
    |                                ^
259 |             lower_lows = all(
260 |                 recent_lows[i].price < recent_lows[i - 1].price
    |

PLR0911 Too many return statements (11 > 6)
   --> src/engine/ta/common/utils/price/math.py:149:5
    |
149 | def _get_pair_type(symbol: str) -> str:
    |     ^^^^^^^^^^^^^^
150 |     """Detect instrument type from symbol, handling arbitrary broker suffixes.
    |

PLR0912 Too many branches (18 > 12)
   --> src/engine/ta/common/utils/price/math.py:149:5
    |
149 | def _get_pair_type(symbol: str) -> str:
    |     ^^^^^^^^^^^^^^
150 |     """Detect instrument type from symbol, handling arbitrary broker suffixes.
    |

PLR2004 Magic value used in comparison, consider replacing `6` with a constant variable
   --> src/engine/ta/common/utils/price/math.py:176:29
    |
174 |     # but only if the base (without typical 1-3 char broker suffix) ends with JPY.
175 |     # e.g. "USDJPYxyz" — strip up to 3 trailing chars and check.
176 |     if len(symbol_upper) >= 6 and symbol_upper[:6].endswith("JPY"):
    |                             ^
177 |         return "JPY"
178 |     if len(symbol_upper) >= 7 and symbol_upper[:7].endswith("JPY"):
    |

PLR2004 Magic value used in comparison, consider replacing `7` with a constant variable
   --> src/engine/ta/common/utils/price/math.py:178:29
    |
176 |     if len(symbol_upper) >= 6 and symbol_upper[:6].endswith("JPY"):
177 |         return "JPY"
178 |     if len(symbol_upper) >= 7 and symbol_upper[:7].endswith("JPY"):
    |                             ^
179 |         return "JPY"
    |

PLR1714 Consider merging multiple comparisons: `pair_type in {"JPY", "METAL", "OIL"}`.
   --> src/engine/ta/common/utils/price/math.py:210:8
    |
208 |     pair_type = _get_pair_type(symbol)
209 |
210 |     if pair_type == "JPY" or pair_type == "METAL" or pair_type == "OIL":
    |        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
211 |         return Decimal("0.01")
212 |     if pair_type == "INDEX" or pair_type == "CRYPTO":
    |
help: Merge multiple comparisons

PLR1714 Consider merging multiple comparisons: `pair_type in {"INDEX", "CRYPTO"}`.
   --> src/engine/ta/common/utils/price/math.py:212:8
    |
210 |     if pair_type == "JPY" or pair_type == "METAL" or pair_type == "OIL":
211 |         return Decimal("0.01")
212 |     if pair_type == "INDEX" or pair_type == "CRYPTO":
    |        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
213 |         return Decimal("1.0")
214 |     if pair_type.startswith("DERIV_"):
    |
help: Merge multiple comparisons

SIM108 Use ternary operator `wick_size = high_price - candle_top if upper else candle_bottom - low_price` instead of `if`-`else`-block
   --> src/engine/ta/common/utils/price/math.py:368:5
    |
366 |       candle_bottom = min(open_price, close_price)
367 |
368 | /     if upper:
369 | |         wick_size = high_price - candle_top
370 | |     else:
371 | |         wick_size = candle_bottom - low_price
    | |_____________________________________________^
372 |
373 |       return (wick_size / total_range) * 100.0
    |
help: Replace `if`-`else`-block with `wick_size = high_price - candle_top if upper else candle_bottom - low_price`

PLR0912 Too many branches (25 > 12)
   --> src/engine/ta/orchestrator.py:117:15
    |
115 |     # ── Public API ───────────────────────────────────────────────────
116 |
117 |     async def analyze(
    |               ^^^^^^^
118 |         self,
119 |         symbol: str,
    |

PLR0915 Too many statements (87 > 50)
   --> src/engine/ta/orchestrator.py:117:15
    |
115 |     # ── Public API ───────────────────────────────────────────────────
116 |
117 |     async def analyze(
    |               ^^^^^^^
118 |         self,
119 |         symbol: str,
    |

SIM103 Return the negated condition directly
   --> src/engine/ta/orchestrator.py:510:13
    |
508 |               ):
509 |                   return False
510 | /             if (
511 | |                 c.fvg_timestamp is not None
512 | |                 and (c.ltf_timeframe, c.fvg_timestamp) in dead_fvg_timestamps
513 | |             ):
514 | |                 return False
515 | |             return True
    | |_______________________^
516 |
517 |           def _snd_is_live(c: SnDCandidate) -> bool:
    |
help: Inline condition

SIM103 Return the negated condition directly
   --> src/engine/ta/orchestrator.py:521:13
    |
519 |               tested. SR/RS flips and fakeouts have no consumed flag.
520 |               """
521 | /             if (
522 | |                 c.qml_timestamp is not None
523 | |                 and (c.htf_timeframe, c.qml_timestamp) in dead_qm_timestamps
524 | |             ):
525 | |                 return False
526 | |             return True
    | |_______________________^
527 |
528 |           live_smc = [c for c in smc_list if _smc_is_live(c)]
    |
help: Inline condition

PLR0911 Too many return statements (7 > 6)
   --> src/engine/ta/orchestrator.py:684:9
    |
683 |     @classmethod
684 |     def _zone_bucket(
    |         ^^^^^^^^^^^^
685 |         cls,
686 |         lower: float | None,
    |

PLR0912 Too many branches (18 > 12)
   --> src/engine/ta/orchestrator.py:964:15
    |
962 |     # ── Per-timeframe structural detection + enriched snapshot ────────
963 |
964 |     async def _build_enriched_snapshot(
    |               ^^^^^^^^^^^^^^^^^^^^^^^^
965 |         self,
966 |         sequence: CandleSequence,
    |

PLR0915 Too many statements (82 > 50)
   --> src/engine/ta/orchestrator.py:964:15
    |
962 |     # ── Per-timeframe structural detection + enriched snapshot ────────
963 |
964 |     async def _build_enriched_snapshot(
    |               ^^^^^^^^^^^^^^^^^^^^^^^^
965 |         self,
966 |         sequence: CandleSequence,
    |

B007 Loop control variable `tf` not used within loop body
    --> src/engine/ta/orchestrator.py:1458:17
     |
1457 |         async with self._ta_uow_factory() as uow:
1458 |             for tf, snapshot in snapshots.items():
     |                 ^^
1459 |                 await self._persist_snapshot(snapshot, uow, user_id=user_id)
     |
help: Rename unused `tf` to `_tf`

PLR2004 Magic value used in comparison, consider replacing `3` with a constant variable
   --> src/engine/ta/smc/builders/amd/candidates.py:470:25
    |
468 |         # 6. Fibonacci / OTE confluence (0-3 points), per-candidate leg
469 |         fib_score = self.zone_validator.score_ob_fib_confluence(ob, retracement)
470 |         if fib_score >= 3:
    |                         ^
471 |             confluences += 2  # OTE pocket = strong confluence
472 |         elif fib_score >= 2:
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/smc/builders/amd/candidates.py:472:27
    |
470 |         if fib_score >= 3:
471 |             confluences += 2  # OTE pocket = strong confluence
472 |         elif fib_score >= 2:
    |                           ^
473 |             confluences += 1  # Correct premium/discount zone
    |

PLR2004 Magic value used in comparison, consider replacing `3` with a constant variable
   --> src/engine/ta/smc/builders/continuation.py:448:25
    |
446 |         # 7. Fibonacci / OTE confluence (0-2 points), per-candidate leg
447 |         fib_score = self.zone_validator.score_ob_fib_confluence(ob, retracement)
448 |         if fib_score >= 3:
    |                         ^
449 |             confluences += 2  # OTE pocket = strong confluence
450 |         elif fib_score >= 2:
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/smc/builders/continuation.py:450:27
    |
448 |         if fib_score >= 3:
449 |             confluences += 2  # OTE pocket = strong confluence
450 |         elif fib_score >= 2:
    |                           ^
451 |             confluences += 1  # Correct premium/discount zone
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/smc/builders/continuation.py:579:9
    |
577 |         Identifies local maxima using a simple 3-bar pivot.
578 |         """
579 |         from engine.ta.models.swing import SwingHigh
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
580 |
581 |         highs = []
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/smc/builders/continuation.py:605:9
    |
603 |     def _get_swing_lows_from_sequence(sequence: CandleSequence) -> list:
604 |         """Extract approximate swing lows from a candle sequence."""
605 |         from engine.ta.models.swing import SwingLow
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
606 |
607 |         lows = []
    |

PLR2004 Magic value used in comparison, consider replacing `3` with a constant variable
   --> src/engine/ta/smc/builders/reversal.py:586:25
    |
584 |         # 6. Fibonacci / OTE confluence (0-2 points), per-candidate leg
585 |         fib_score = self.zone_validator.score_ob_fib_confluence(ob, retracement)
586 |         if fib_score >= 3:
    |                         ^
587 |             confluences += 2  # OTE pocket = strong confluence
588 |         elif fib_score >= 2:
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/smc/builders/reversal.py:588:27
    |
586 |         if fib_score >= 3:
587 |             confluences += 2  # OTE pocket = strong confluence
588 |         elif fib_score >= 2:
    |                           ^
589 |             confluences += 1  # Correct premium/discount zone
    |

ERA001 Found commented-out code
  --> src/engine/ta/smc/config.py:38:5
   |
36 |     # as a percentage of the OB's own range:
37 |     #
38 |     #   buffer = (ob.upper_bound - ob.lower_bound) * ob_sl_buffer_range_pct
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
39 |     #
40 |     # This scales the buffer with the OB that sponsored the setup, so
   |
help: Remove commented-out code

ERA001 Found commented-out code
   --> src/engine/ta/smc/config.py:138:5
    |
136 |     # layers:
137 |     #
138 |     #   abs(swing - entry) >= sl_distance * min_take_profit_rr
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
139 |     #
140 |     # 1.0 is the mathematical breakeven floor (reward == risk).  It
    |
help: Remove commented-out code

PLR0912 Too many branches (16 > 12)
   --> src/engine/ta/smc/detector.py:404:9
    |
402 |     # ------------------------------------------------------------------
403 |
404 |     def _build_choch_reversal_candidates(
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
405 |         self,
406 |         htf_sequence: CandleSequence,
    |

F821 Undefined name `OrderBlock`
   --> src/engine/ta/smc/detector.py:593:14
    |
591 |         ltf_choch: ChangeOfCharacter | None,
592 |         ltf_sweep: LiquiditySweep | None,
593 |         ob: "OrderBlock",
    |              ^^^^^^^^^^
594 |         ltf_fvgs: list,
595 |         inducement_events: list,
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/smc/detector.py:607:9
    |
605 |         select_leg_for_choch_bms_rto and SMC-MIT-003.
606 |         """
607 |         from engine.ta.common.utils.price.math import get_pip_value
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
608 |
609 |         # Per-candidate Fibonacci leg (SMC-MIT-003).
    |

F841 Local variable `pip_val` is assigned to but never used
   --> src/engine/ta/smc/detector.py:653:9
    |
651 |         )
652 |
653 |         pip_val = float(get_pip_value(ltf_sequence.symbol))
    |         ^^^^^^^
654 |         entry_price = ob.midpoint
    |
help: Remove assignment to unused variable `pip_val`

F821 Undefined name `OrderBlock`
   --> src/engine/ta/smc/detector.py:783:14
    |
781 |         ltf_choch: ChangeOfCharacter | None,
782 |         ltf_sweep: LiquiditySweep | None,
783 |         ob: "OrderBlock",
    |              ^^^^^^^^^^
784 |         fvgs: list,
785 |         retracement: FibonacciRetracement | None,
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/smc/detector.py:795:9
    |
793 |         scored against this candidate's own impulse.
794 |         """
795 |         from engine.ta.common.utils.price.math import get_pip_value
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
796 |
797 |         confluences = 0
    |

PLR2004 Magic value used in comparison, consider replacing `3` with a constant variable
   --> src/engine/ta/smc/detector.py:827:25
    |
825 |         # 8. Fibonacci / OTE confluence, per-candidate leg
826 |         fib_score = self.zone_validator.score_ob_fib_confluence(ob, retracement)
827 |         if fib_score >= 3:
    |                         ^
828 |             confluences += 2
829 |         elif fib_score >= 2:
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/smc/detector.py:829:27
    |
827 |         if fib_score >= 3:
828 |             confluences += 2
829 |         elif fib_score >= 2:
    |                           ^
830 |             confluences += 1
    |

PLR0912 Too many branches (22 > 12)
   --> src/engine/ta/smc/detector.py:927:9
    |
925 |     # ------------------------------------------------------------------
926 |
927 |     def _build_continuation_candidates(
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
928 |         self,
929 |         htf_sequence: CandleSequence,
    |

PLR0915 Too many statements (56 > 50)
   --> src/engine/ta/smc/detector.py:927:9
    |
925 |     # ------------------------------------------------------------------
926 |
927 |     def _build_continuation_candidates(
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
928 |         self,
929 |         htf_sequence: CandleSequence,
    |

PLR0912 Too many branches (22 > 12)
    --> src/engine/ta/smc/detector.py:1149:9
     |
1147 |     # ------------------------------------------------------------------
1148 |
1149 |     def _build_reversal_candidates(
     |         ^^^^^^^^^^^^^^^^^^^^^^^^^^
1150 |         self,
1151 |         htf_sequence: CandleSequence,
     |

PLR0915 Too many statements (59 > 50)
    --> src/engine/ta/smc/detector.py:1149:9
     |
1147 |     # ------------------------------------------------------------------
1148 |
1149 |     def _build_reversal_candidates(
     |         ^^^^^^^^^^^^^^^^^^^^^^^^^^
1150 |         self,
1151 |         htf_sequence: CandleSequence,
     |

B007 Loop control variable `htf_sms` not used within loop body
    --> src/engine/ta/smc/detector.py:1223:21
     |
1221 |             # If no LTF BMS yet, build from HTF structure alone
1222 |             if not ltf_bms_bullish:
1223 |                 for htf_sms in htf_sms_bullish:
     |                     ^^^^^^^
1224 |                     # Use the SMS reversal candle to find an OB on HTF
1225 |                     htf_bms_from_sms = self.bms_detector.detect_bullish_bms(
     |
help: Rename unused `htf_sms` to `_htf_sms`

B007 Loop control variable `htf_sms` not used within loop body
    --> src/engine/ta/smc/detector.py:1313:21
     |
1312 |             if not ltf_bms_bearish:
1313 |                 for htf_sms in htf_sms_bearish:
     |                     ^^^^^^^
1314 |                     htf_bms_from_sms = self.bms_detector.detect_bearish_bms(
1315 |                         htf_sequence,
     |
help: Rename unused `htf_sms` to `_htf_sms`

SIM102 Use a single `if` statement instead of nested `if` statements
    --> src/engine/ta/smc/detector.py:1548:13
     |
1546 |                   continue
1547 |
1548 | /             if direction == Direction.BULLISH and sweep.liquidity_type.value in (
1549 | |                 "SSL",
1550 | |                 "EQUAL_LOWS",
1551 | |                 "PDL_SWEEP",
1552 | |             ) or direction == Direction.BEARISH and sweep.liquidity_type.value in (
1553 | |                 "BSL",
1554 | |                 "EQUAL_HIGHS",
1555 | |                 "PDH_SWEEP",
1556 | |             ):
1557 | |                 if distance < best_distance:
     | |____________________________________________^
1558 |                       best_distance = distance
1559 |                       best_sweep = sweep
     |
help: Combine `if` statements using `and`

PLR0912 Too many branches (13 > 12)
  --> src/engine/ta/smc/detectors/bms.py:69:9
   |
67 |     # ------------------------------------------------------------------
68 |
69 |     def detect_bullish_bms(
   |         ^^^^^^^^^^^^^^^^^^
70 |         self,
71 |         sequence: CandleSequence,
   |

PLR0912 Too many branches (13 > 12)
   --> src/engine/ta/smc/detectors/bms.py:189:9
    |
187 |         return bms_events
188 |
189 |     def detect_bearish_bms(
    |         ^^^^^^^^^^^^^^^^^^
190 |         self,
191 |         sequence: CandleSequence,
    |

PLR0912 Too many branches (13 > 12)
  --> src/engine/ta/smc/detectors/choch.py:61:9
   |
59 |     # ------------------------------------------------------------------
60 |
61 |     def detect_bullish_choch(
   |         ^^^^^^^^^^^^^^^^^^^^
62 |         self,
63 |         sequence: CandleSequence,
   |

PLR2004 Magic value used in comparison, consider replacing `5` with a constant variable
   --> src/engine/ta/smc/detectors/choch.py:137:41
    |
135 |                 breakout_price=breakout_candle.close,
136 |                 candle_index=first_break_idx,
137 |                 is_minor=sh.strength <= 5,
    |                                         ^
138 |             )
    |

PLR0912 Too many branches (13 > 12)
   --> src/engine/ta/smc/detectors/choch.py:157:9
    |
155 |         return choch_events
156 |
157 |     def detect_bearish_choch(
    |         ^^^^^^^^^^^^^^^^^^^^
158 |         self,
159 |         sequence: CandleSequence,
    |

PLR2004 Magic value used in comparison, consider replacing `5` with a constant variable
   --> src/engine/ta/smc/detectors/choch.py:233:41
    |
231 |                 breakout_price=breakout_candle.close,
232 |                 candle_index=first_break_idx,
233 |                 is_minor=sl.strength <= 5,
    |                                         ^
234 |             )
    |

PLR2004 Magic value used in comparison, consider replacing `5` with a constant variable
  --> src/engine/ta/smc/detectors/inducement.py:47:67
   |
45 |         inducement_events: list[InducementEvent] = []
46 |
47 |         internal_lows = [sl for sl in swing_lows if sl.strength < 5]
   |                                                                   ^
48 |
49 |         pip_value = float(get_pip_value(sequence.symbol))
   |

PLR2004 Magic value used in comparison, consider replacing `5` with a constant variable
   --> src/engine/ta/smc/detectors/inducement.py:111:69
    |
109 |         inducement_events: list[InducementEvent] = []
110 |
111 |         internal_highs = [sh for sh in swing_highs if sh.strength < 5]
    |                                                                     ^
112 |
113 |         pip_value = float(get_pip_value(sequence.symbol))
    |

PLR2004 Magic value used in comparison, consider replacing `3` with a constant variable
  --> src/engine/ta/smc/detectors/sms.py:38:30
   |
36 |         sms_events = []
37 |
38 |         if len(swing_lows) < 3:
   |                              ^
39 |             return sms_events
   |

PLR2004 Magic value used in comparison, consider replacing `3` with a constant variable
  --> src/engine/ta/smc/detectors/sms.py:92:31
   |
90 |         sms_events = []
91 |
92 |         if len(swing_highs) < 3:
   |                               ^
93 |             return sms_events
   |

RET504 Unnecessary assignment to `ob` before `return` statement
   --> src/engine/ta/smc/zones/order_block.py:191:28
    |
189 |                         mitigated=False,
190 |                     )
191 |                     return ob
    |                            ^^
192 |
193 |         else:
    |
help: Remove unnecessary assignment

RET504 Unnecessary assignment to `ob` before `return` statement
   --> src/engine/ta/smc/zones/order_block.py:210:28
    |
208 |                         mitigated=False,
209 |                     )
210 |                     return ob
    |                            ^^
211 |
212 |         return None
    |
help: Remove unnecessary assignment

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
  --> src/engine/ta/snd/builders/candidates/continuation.py:83:33
   |
81 |             return None
82 |
83 |         if len(fakeout_tests) < 2:
   |                                 ^
84 |             self._logger.debug(
85 |                 "continuation_short_insufficient_fakeouts",
   |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
  --> src/engine/ta/snd/builders/candidates/continuation.py:93:63
   |
91 |             return None
92 |
93 |         if not previous_highs or previous_highs.touch_count < 2:
   |                                                               ^
94 |             self._logger.debug(
95 |                 "continuation_short_no_previous_highs",
   |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/snd/builders/candidates/continuation.py:213:33
    |
211 |             return None
212 |
213 |         if len(fakeout_tests) < 2:
    |                                 ^
214 |             self._logger.debug(
215 |                 "continuation_long_insufficient_fakeouts",
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/snd/builders/candidates/continuation.py:223:61
    |
221 |             return None
222 |
223 |         if not previous_lows or previous_lows.touch_count < 2:
    |                                                             ^
224 |             self._logger.debug(
225 |                 "continuation_long_no_previous_lows",
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/snd/builders/candidates/continuation.py:330:63
    |
328 |         confluences += len(fakeout_tests)
329 |
330 |         if previous_levels and previous_levels.touch_count >= 2:
    |                                                               ^
331 |             confluences += previous_levels.touch_count
    |

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/ta/snd/builders/candidates/continuation.py:333:9
    |
331 |               confluences += previous_levels.touch_count
332 |
333 | /         if retracement:
334 | |             if self.ltf_validator.check_fibonacci_alignment(
335 | |                 qm_level.level, retracement
336 | |             ):
    | |______________^
337 |                   confluences += 2
    |
help: Combine `if` statements using `and`

PLR2004 Magic value used in comparison, consider replacing `3` with a constant variable
   --> src/engine/ta/snd/builders/candidates/fakeout.py:111:38
    |
109 |         pattern = (
110 |             CandidatePattern.FAKEOUT_KING
111 |             if len(fakeout_tests) >= 3
    |                                      ^
112 |             else CandidatePattern.SOP
113 |         )
    |

PLR2004 Magic value used in comparison, consider replacing `3` with a constant variable
   --> src/engine/ta/snd/builders/candidates/fakeout.py:147:73
    |
145 |             metadata={
146 |                 "confluences": confluences,
147 |                 "pattern_type": "fakeout_king" if len(fakeout_tests) >= 3 else "sop",
    |                                                                         ^
148 |             },
149 |         )
    |

PLR2004 Magic value used in comparison, consider replacing `3` with a constant variable
   --> src/engine/ta/snd/builders/candidates/fakeout.py:217:38
    |
215 |         pattern = (
216 |             CandidatePattern.FAKEOUT_KING
217 |             if len(fakeout_tests) >= 3
    |                                      ^
218 |             else CandidatePattern.SOP
219 |         )
    |

PLR2004 Magic value used in comparison, consider replacing `3` with a constant variable
   --> src/engine/ta/snd/builders/candidates/fakeout.py:253:73
    |
251 |             metadata={
252 |                 "confluences": confluences,
253 |                 "pattern_type": "fakeout_king" if len(fakeout_tests) >= 3 else "sop",
    |                                                                         ^
254 |             },
255 |         )
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/snd/builders/candidates/fakeout.py:280:63
    |
278 |         confluences += len(fakeout_tests)
279 |
280 |         if previous_levels and previous_levels.touch_count >= 2:
    |                                                               ^
281 |             confluences += previous_levels.touch_count
    |

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/ta/snd/builders/candidates/fakeout.py:283:9
    |
281 |               confluences += previous_levels.touch_count
282 |
283 | /         if retracement:
284 | |             if self.ltf_validator.check_fibonacci_alignment(zone_price, retracement):
    | |_____________________________________________________________________________________^
285 |                   confluences += 2
    |
help: Combine `if` statements using `and`

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/snd/builders/candidates/qm.py:527:61
    |
525 |         confluences += len(fakeout_tests)
526 |
527 |         if previous_highs and previous_highs.touch_count >= 2:
    |                                                             ^
528 |             confluences += previous_highs.touch_count
    |

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/ta/snd/builders/candidates/qm.py:533:9
    |
531 |               confluences += 2 if mpl.is_type1 else 1
532 |
533 | /         if retracement:
534 | |             if self.ltf_validator.check_fibonacci_alignment(qml.level, retracement):
    | |____________________________________________________________________________________^
535 |                   confluences += 2
    |
help: Combine `if` statements using `and`

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/snd/builders/candidates/qm.py:551:59
    |
549 |         confluences += len(fakeout_tests)
550 |
551 |         if previous_lows and previous_lows.touch_count >= 2:
    |                                                           ^
552 |             confluences += previous_lows.touch_count
    |

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/ta/snd/builders/candidates/qm.py:557:9
    |
555 |               confluences += 2 if mpl.is_type1 else 1
556 |
557 | /         if retracement:
558 | |             if self.ltf_validator.check_fibonacci_alignment(qmh.level, retracement):
    | |____________________________________________________________________________________^
559 |                   confluences += 2
    |
help: Combine `if` statements using `and`

F841 Local variable `last_fakeout` is assigned to but never used
   --> src/engine/ta/snd/builders/candidates/qm.py:571:9
    |
569 |         if not fakeout_tests:
570 |             return False
571 |         last_fakeout = fakeout_tests[-1]
    |         ^^^^^^^^^^^^
572 |         return self.ltf_validator.validate_compression_at_zone(
573 |             sequence,
    |
help: Remove assignment to unused variable `last_fakeout`

PLR0911 Too many return statements (7 > 6)
  --> src/engine/ta/snd/builders/levels.py:72:5
   |
72 | def compute_trade_levels(
   |     ^^^^^^^^^^^^^^^^^^^^
73 |     *,
74 |     symbol: str,
   |

PLR0912 Too many branches (14 > 12)
  --> src/engine/ta/snd/builders/levels.py:72:5
   |
72 | def compute_trade_levels(
   |     ^^^^^^^^^^^^^^^^^^^^
73 |     *,
74 |     symbol: str,
   |

SIM108 Use ternary operator `risk_reward = resolve_min_tp_rr(timeframe) if timeframe is not None else 3.0` instead of `if`-`else`-block
   --> src/engine/ta/snd/builders/levels.py:143:9
    |
141 |       # 3.0 (legacy SnD default) only when neither is available.
142 |       if risk_reward is None:
143 | /         if timeframe is not None:
144 | |             risk_reward = resolve_min_tp_rr(timeframe)
145 | |         else:
146 | |             risk_reward = 3.0
    | |_____________________________^
147 |       if not _is_positive_finite(risk_reward):
148 |           return None
    |
help: Replace `if`-`else`-block with `risk_reward = resolve_min_tp_rr(timeframe) if timeframe is not None else 3.0`

PLR0124 Name compared with itself, consider replacing `v != v`
   --> src/engine/ta/snd/builders/levels.py:297:8
    |
295 |     except (TypeError, ValueError):
296 |         return False
297 |     if v != v:  # NaN
    |        ^
298 |         return False
299 |     if v in (float("inf"), float("-inf")):
    |

PLR0124 Name compared with itself, consider replacing `v != v`
   --> src/engine/ta/snd/builders/levels.py:310:8
    |
308 |     except (TypeError, ValueError):
309 |         return False
310 |     if v != v:  # NaN
    |        ^
311 |         return False
312 |     if v in (float("inf"), float("-inf")):
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
  --> src/engine/ta/snd/config.py:53:16
   |
51 |     @classmethod
52 |     def validate_min_previous_touches(cls, v: int) -> int:
53 |         if v < 2:
   |                ^
54 |             raise ValueError(
55 |                 "SnD requires minimum 2 previous touches (Universal Rule 2)"
   |

PLR2004 Magic value used in comparison, consider replacing `80.0` with a constant variable
  --> src/engine/ta/snd/config.py:62:16
   |
60 |     @classmethod
61 |     def validate_marubozu_threshold(cls, v: float) -> float:
62 |         if v < 80.0:
   |                ^^^^
63 |             raise ValueError(
64 |                 "Marubozu body percentage must be at least 80% (Universal Rule 1)"
   |

PLR0912 Too many branches (29 > 12)
   --> src/engine/ta/snd/detector.py:106:9
    |
104 |         self._logger = get_logger(__name__)
105 |
106 |     def detect_patterns(
    |         ^^^^^^^^^^^^^^^
107 |         self,
108 |         htf_sequence: CandleSequence,
    |

PLR0915 Too many statements (63 > 50)
   --> src/engine/ta/snd/detector.py:106:9
    |
104 |         self._logger = get_logger(__name__)
105 |
106 |     def detect_patterns(
    |         ^^^^^^^^^^^^^^^
107 |         self,
108 |         htf_sequence: CandleSequence,
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/snd/detector.py:253:70
    |
251 |                 # Build continuation candidates (bearish)
252 |                 # Requires 2+ fakeout tests + previous highs (stricter)
253 |                 if matching_previous_highs and len(fakeout_tests) >= 2:
    |                                                                      ^
254 |                     for prev_high in matching_previous_highs:
255 |                         candidate = self.continuation_builder.build_continuation_short(
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/snd/detector.py:352:69
    |
351 |                 # Build continuation candidates (bullish)
352 |                 if matching_previous_lows and len(fakeout_tests) >= 2:
    |                                                                     ^
353 |                     for prev_low in matching_previous_lows:
354 |                         candidate = self.continuation_builder.build_continuation_long(
    |

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/ta/snd/detectors/fakeouts.py:203:17
    |
202 |               if direction == Direction.BULLISH:
203 | /                 if self.marubozu_analyzer.is_bullish_marubozu(candle):
204 | |                     if candle.close > fakeout_level:
    | |____________________________________________________^
205 |                           return i
    |
help: Combine `if` statements using `and`

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/ta/snd/detectors/fakeouts.py:207:13
    |
205 |                           return i
206 |
207 | /             elif self.marubozu_analyzer.is_bearish_marubozu(candle):
208 | |                 if candle.close < fakeout_level:
    | |________________________________________________^
209 |                       return i
    |
help: Combine `if` statements using `and`

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/snd/detectors/fakeouts.py:219:27
    |
217 |         direction: Direction,
218 |     ) -> bool:
219 |         if candle_index < 2 or candle_index >= len(sequence.candles) - 1:
    |                           ^
220 |             return False
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
  --> src/engine/ta/snd/detectors/mpl.py:40:23
   |
38 |         mpl_levels = []
39 |
40 |         if h2_index < 2:
   |                       ^
41 |             return mpl_levels
   |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/snd/detectors/mpl.py:115:23
    |
113 |         mpl_levels = []
114 |
115 |         if l2_index < 2:
    |                       ^
116 |             return mpl_levels
    |

PLR0912 Too many branches (16 > 12)
  --> src/engine/ta/snd/detectors/qm.py:34:9
   |
32 |         self._logger = get_logger(__name__)
33 |
34 |     def detect_qml(
   |         ^^^^^^^^^^
35 |         self,
36 |         sequence: CandleSequence,
   |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
  --> src/engine/ta/snd/detectors/qm.py:47:31
   |
45 |         qml_levels = []
46 |
47 |         if len(swing_highs) < 2 or not swing_lows:
   |                               ^
48 |             return qml_levels
   |

E741 Ambiguous variable name: `l`
  --> src/engine/ta/snd/detectors/qm.py:66:17
   |
64 |             lowest_price = float("inf")
65 |
66 |             for l in sorted_lows:
   |                 ^
67 |                 if h.timestamp < l.timestamp < hh.timestamp:
68 |                     if l.price < lowest_price:
   |

SIM102 Use a single `if` statement instead of nested `if` statements
  --> src/engine/ta/snd/detectors/qm.py:67:17
   |
66 |               for l in sorted_lows:
67 | /                 if h.timestamp < l.timestamp < hh.timestamp:
68 | |                     if l.price < lowest_price:
   | |______________________________________________^
69 |                           lowest_price = l.price
70 |                           neckline_l = l
   |
help: Combine `if` statements using `and`

F841 Local variable `breakout_candle` is assigned to but never used
  --> src/engine/ta/snd/detectors/qm.py:88:13
   |
86 |                 continue
87 |
88 |             breakout_candle = sequence.candles[first_break_idx]
   |             ^^^^^^^^^^^^^^^
89 |
90 |             # Count consecutive candle closes below the Neckline level
   |
help: Remove assignment to unused variable `breakout_candle`

PLR0912 Too many branches (16 > 12)
   --> src/engine/ta/snd/detectors/qm.py:150:9
    |
148 |         return qml_levels
149 |
150 |     def detect_qmh(
    |         ^^^^^^^^^^
151 |         self,
152 |         sequence: CandleSequence,
    |

PLR2004 Magic value used in comparison, consider replacing `2` with a constant variable
   --> src/engine/ta/snd/detectors/qm.py:163:30
    |
161 |         qmh_levels = []
162 |
163 |         if len(swing_lows) < 2 or not swing_highs:
    |                              ^
164 |             return qmh_levels
    |

E741 Ambiguous variable name: `l`
   --> src/engine/ta/snd/detectors/qm.py:171:13
    |
170 |         for i in range(len(sorted_lows) - 1):
171 |             l = sorted_lows[i]  # L  (Left Shoulder)
    |             ^
172 |             ll = sorted_lows[i + 1]  # LL (Head)
    |

SIM102 Use a single `if` statement instead of nested `if` statements
   --> src/engine/ta/snd/detectors/qm.py:183:17
    |
182 |               for h in sorted_highs:
183 | /                 if l.timestamp < h.timestamp < ll.timestamp:
184 | |                     if h.price > highest_price:
    | |_______________________________________________^
185 |                           highest_price = h.price
186 |                           neckline_h = h
    |
help: Combine `if` statements using `and`

F841 Local variable `breakout_candle` is assigned to but never used
   --> src/engine/ta/snd/detectors/qm.py:204:13
    |
202 |                 continue
203 |
204 |             breakout_candle = sequence.candles[first_break_idx]
    |             ^^^^^^^^^^^^^^^
205 |
206 |             # Count consecutive candle closes above the Neckline level
    |
help: Remove assignment to unused variable `breakout_candle`

SIM103 Return the negated condition directly
   --> src/engine/ta/snd/validators/ltf/confirmation.py:231:9
    |
230 |           is_aligned = self.check_fibonacci_alignment(zone_price, retracement)
231 | /         if self.config.require_fibonacci_confluence and not is_aligned:
232 | |             return False
233 | |
234 | |         return True
    | |___________________^
    |
help: Inline condition

E712 Avoid equality comparisons to `True`; use `CandidateSchema.is_active:` for truth checks
  --> src/engine/ta/storage/repositories/candidate.py:50:21
   |
48 |                     CandidateSchema.direction == candidate.direction.value,
49 |                     CandidateSchema.entry_price == round(candidate.entry_price, 4),
50 |                     CandidateSchema.is_active == True,
   |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
51 |                 )
52 |             )
   |
help: Replace with `CandidateSchema.is_active`

E712 Avoid equality comparisons to `True`; use `CandidateSchema.is_active:` for truth checks
   --> src/engine/ta/storage/repositories/candidate.py:143:21
    |
141 |                     CandidateSchema.direction == candidate.direction.value,
142 |                     CandidateSchema.entry_price == round(candidate.entry_price, 4),
143 |                     CandidateSchema.is_active == True,
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
144 |                 )
145 |             )
    |
help: Replace with `CandidateSchema.is_active`

E712 Avoid equality comparisons to `True`; use `CandidateSchema.is_active:` for truth checks
   --> src/engine/ta/storage/repositories/candidate.py:499:21
    |
497 |                     CandidateSchema.user_id == user_id,
498 |                     CandidateSchema.symbol.in_(symbols),
499 |                     CandidateSchema.is_active == True,
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
500 |                 )
501 |             )
    |
help: Replace with `CandidateSchema.is_active`

E712 Avoid equality comparisons to `True`; use `CandidateSchema.is_active:` for truth checks
   --> src/engine/ta/storage/repositories/candidate.py:539:13
    |
537 |             CandidateSchema.user_id == user_id,
538 |             CandidateSchema.symbol == symbol,
539 |             CandidateSchema.is_active == True,
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
540 |         ]
    |
help: Replace with `CandidateSchema.is_active`

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/storage/repositories/candle.py:115:9
    |
113 |             return []
114 |
115 |         from sqlalchemy.dialects.postgresql import insert as pg_insert
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
116 |
117 |         from engine.shared.metrics.prometheus import (
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/storage/repositories/candle.py:117:9
    |
115 |           from sqlalchemy.dialects.postgresql import insert as pg_insert
116 |
117 | /         from engine.shared.metrics.prometheus import (
118 | |             BROKER_CANDLES_DEDUP_SKIPPED_TOTAL,
119 | |         )
    | |_________^
120 |
121 |           rows = [
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/storage/repositories/snapshot.py:211:9
    |
209 |     ) -> int:
210 |         """Count total snapshots for user/symbol/timeframe."""
211 |         from sqlalchemy import func
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^
212 |
213 |         result = await self.session.execute(
    |

PLC0415 `import` should be at the top-level of a file
   --> src/engine/ta/storage/repositories/snapshot.py:249:9
    |
247 |     ) -> int:
248 |         """Get latest version number for user/symbol/timeframe."""
249 |         from sqlalchemy import func
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^
250 |
251 |         result = await self.session.execute(
    |

S105 Possible hardcoded password assigned to: "token"
 --> src/engine/verify_chroma.py:6:13
  |
5 | def main():
6 |     token = "etradie_internal_secure_token_2026"
  |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
7 |     host = "chromadb"  # Inside docker network
8 |     port = 8000
  |

T201 `print` found
  --> src/engine/verify_chroma.py:10:5
   |
 8 |     port = 8000
 9 |
10 |     print(f"Connecting to ChromaDB at {host}:{port}...")
   |     ^^^^^
11 |     try:
12 |         client = chromadb.HttpClient(
   |
help: Remove `print`

T201 `print` found
  --> src/engine/verify_chroma.py:20:9
   |
19 |         heartbeat = client.heartbeat()
20 |         print(f"Heartbeat: {heartbeat}")
   |         ^^^^^
21 |
22 |         collections = client.list_collections()
   |
help: Remove `print`

T201 `print` found
  --> src/engine/verify_chroma.py:23:9
   |
22 |         collections = client.list_collections()
23 |         print(f"\nFound {len(collections)} collections:")
   |         ^^^^^
24 |
25 |         for col in collections:
   |
help: Remove `print`

T201 `print` found
  --> src/engine/verify_chroma.py:27:13
   |
25 |         for col in collections:
26 |             count = col.count()
27 |             print(f"- {col.name}: {count} documents")
   |             ^^^^^
28 |
29 |             if count > 0:
   |
help: Remove `print`

T201 `print` found
  --> src/engine/verify_chroma.py:30:17
   |
29 |             if count > 0:
30 |                 print(f"  Previewing first 2 documents in '{col.name}':")
   |                 ^^^^^
31 |                 peek = col.peek(limit=2)
32 |                 for i in range(len(peek["ids"])):
   |
help: Remove `print`

T201 `print` found
  --> src/engine/verify_chroma.py:33:21
   |
31 |                 peek = col.peek(limit=2)
32 |                 for i in range(len(peek["ids"])):
33 |                     print(f"    ID: {peek['ids'][i]}")
   |                     ^^^^^
34 |                     print(f"    Metadata: {peek['metadatas'][i]}")
35 |                     # documents and metadatas are lists in peek result
   |
help: Remove `print`

T201 `print` found
  --> src/engine/verify_chroma.py:34:21
   |
32 |                 for i in range(len(peek["ids"])):
33 |                     print(f"    ID: {peek['ids'][i]}")
34 |                     print(f"    Metadata: {peek['metadatas'][i]}")
   |                     ^^^^^
35 |                     # documents and metadatas are lists in peek result
36 |                     docs = peek.get("documents", [])
   |
help: Remove `print`

F841 Local variable `metas` is assigned to but never used
  --> src/engine/verify_chroma.py:37:21
   |
35 |                     # documents and metadatas are lists in peek result
36 |                     docs = peek.get("documents", [])
37 |                     metas = peek.get("metadatas", [])
   |                     ^^^^^
38 |
39 |                     if i < len(docs):
   |
help: Remove assignment to unused variable `metas`

PLR2004 Magic value used in comparison, consider replacing `100` with a constant variable
  --> src/engine/verify_chroma.py:41:43
   |
39 |                     if i < len(docs):
40 |                         content = docs[i]
41 |                         if len(content) > 100:
   |                                           ^^^
42 |                             content = content[:100] + "..."
43 |                         print(f"    Content: {content}")
   |

T201 `print` found
  --> src/engine/verify_chroma.py:43:25
   |
41 |                         if len(content) > 100:
42 |                             content = content[:100] + "..."
43 |                         print(f"    Content: {content}")
   |                         ^^^^^
44 |                     print("-" * 20)
   |
help: Remove `print`

T201 `print` found
  --> src/engine/verify_chroma.py:44:21
   |
42 |                             content = content[:100] + "..."
43 |                         print(f"    Content: {content}")
44 |                     print("-" * 20)
   |                     ^^^^^
45 |
46 |     except Exception as e:
   |
help: Remove `print`

T201 `print` found
  --> src/engine/verify_chroma.py:47:9
   |
46 |     except Exception as e:
47 |         print(f"Error: {e}")
   |         ^^^^^
   |
help: Remove `print`

S105 Possible hardcoded password assigned to: "TEST_JWT_SECRET"
  --> tests/api/conftest.py:31:19
   |
29 | # Deterministic JWT secret for tests. Must be set in env_overrides
30 | # so the Python engine's auth module can verify tokens we generate.
31 | TEST_JWT_SECRET = "test-secret-key-for-jwt-signing-must-be-long-enough-64chars-ok"
   |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
32 | TEST_JWT_ISSUER = "etradie"
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/api/conftest.py:75:9
   |
73 | def _check_db() -> bool:
74 |     try:
75 |         import asyncio
   |         ^^^^^^^^^^^^^^
76 |
77 |         import asyncpg
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/api/conftest.py:77:9
   |
75 |         import asyncio
76 |
77 |         import asyncpg
   |         ^^^^^^^^^^^^^^
78 |
79 |         async def _ping():
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/api/conftest.py:96:9
   |
94 | def _check_redis() -> bool:
95 |     try:
96 |         import redis
   |         ^^^^^^^^^^^^
97 |         r = redis.from_url(_REDIS_URL, socket_timeout=2)
98 |         r.ping()
   |

PLC0415 `import` should be at the top-level of a file
   --> tests/api/conftest.py:116:5
    |
114 |     RAG_CHROMA_AUTH_TOKEN to match the app's RAGConfig.chroma_auth_token.
115 |     """
116 |     import httpx
    |     ^^^^^^^^^^^^
117 |
118 |     # Candidate hosts: env var first, then Docker service name, then localhost.
    |

S112 `try`-`except`-`continue` detected, consider logging the exception
   --> tests/api/conftest.py:139:9
    |
137 |               if resp.status_code == 200:
138 |                   return True, host
139 | /         except Exception:
140 | |             continue
    | |____________________^
141 |       return False, _CHROMA_HOST
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/api/conftest.py:226:5
    |
224 |         env_overrides["ANTHROPIC_API_KEY"] = "sk-test-placeholder"
225 |
226 |     from unittest.mock import patch
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
227 |     with patch.dict(os.environ, env_overrides):
228 |         # Clear cached settings so they pick up test env vars.
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/api/conftest.py:229:9
    |
227 |     with patch.dict(os.environ, env_overrides):
228 |         # Clear cached settings so they pick up test env vars.
229 |         from engine.config import get_rag_config, get_settings
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
230 |         get_settings.cache_clear()
231 |         get_rag_config.cache_clear()
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/api/conftest.py:233:9
    |
231 |         get_rag_config.cache_clear()
232 |
233 |         from engine.main import create_app
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
234 |         app = create_app()
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/api/conftest.py:242:13
    |
240 |             # Create processor tables (analysis_outputs, analysis_audit_logs,
241 |             # llm_connections) if they don't exist.
242 |             from engine.processor.storage.schemas.processor_schema import ProcessorBase
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
243 |             async with container.db.engine.begin() as conn:
244 |                 await conn.run_sync(ProcessorBase.metadata.create_all)
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/api/conftest.py:250:13
    |
248 |             # Uses the same provider/model from the env-var processor
249 |             # config so the LLM client can be built without errors.
250 |             from engine.processor.storage.repositories.llm_connection_repository import LLMConnectionRepository
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
251 |             test_user_id = "user-001"  # matches _user_headers JWT sub claim
252 |             async with container.db.session() as session:
    |

E501 Line too long (129 > 120)
   --> tests/api/conftest.py:268:121
    |
267 |             transport = ASGITransport(app=app)
268 |             user_headers = {"Authorization": f"Bearer {_make_test_jwt(user_id='user-001', username='testuser', role='etradie')}"}
    |                                                                                                                         ^^^^^^^^^
269 |             admin_headers = {"Authorization": f"Bearer {_make_test_jwt(user_id='admin-001', username='admin', role='admin')}"}
    |

E501 Line too long (126 > 120)
   --> tests/api/conftest.py:269:121
    |
267 |             transport = ASGITransport(app=app)
268 |             user_headers = {"Authorization": f"Bearer {_make_test_jwt(user_id='user-001', username='testuser', role='etradie')}"}
269 |             admin_headers = {"Authorization": f"Bearer {_make_test_jwt(user_id='admin-001', username='admin', role='admin')}"}
    |                                                                                                                         ^^^^^^
270 |
271 |             async with AsyncClient(transport=transport, base_url="http://testserver", headers=user_headers) as client:
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/api/conftest.py:377:5
    |
375 |     ]
376 |
377 |     from engine.processor.storage.schemas.processor_schema import AnalysisOutputRow
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
378 |
379 |     async with container.db.session() as session:
    |

PLC0415 `import` should be at the top-level of a file
  --> tests/api/dependencies.py:14:9
   |
12 |     def test_container_importable(self):
13 |         """Container can be imported without side effects."""
14 |         from engine.dependencies import Container
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
15 |         assert Container is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/api/dependencies.py:18:9
   |
17 |     def test_container_has_init(self):
18 |         from engine.dependencies import Container
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
19 |         assert hasattr(Container, "__init__")
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/api/dependencies.py:22:9
   |
21 |     def test_container_has_shutdown(self):
22 |         from engine.dependencies import Container
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
23 |         assert hasattr(Container, "shutdown")
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/api/dependencies.py:26:9
   |
25 |     def test_container_has_build_rag(self):
26 |         from engine.dependencies import Container
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
27 |         assert hasattr(Container, "build_rag")
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/api/dependencies.py:30:9
   |
29 |     def test_container_has_build_processor(self):
30 |         from engine.dependencies import Container
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
31 |         assert hasattr(Container, "build_processor")
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/api/endpoints.py:34:5
   |
32 |     # Settings is an lru_cache singleton; clear it so the env above is
33 |     # honoured even if a prior import already populated the cache.
34 |     from engine.config import get_settings
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
35 |     get_settings.cache_clear()
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/api/endpoints.py:37:5
   |
35 |     get_settings.cache_clear()
36 |
37 |     from engine.main import create_app
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
38 |
39 |     app = create_app()
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/api/endpoints.py:46:9
   |
44 |     def test_create_app_importable(self):
45 |         """create_app factory can be imported."""
46 |         from engine.main import create_app
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
47 |         assert callable(create_app)
   |

S323 Python allows using an insecure context via the `_create_unverified_context` that reverts to the previous behavior that does not validate certificates or perform hostname checks.
  --> tests/chaos/_load/harness.py:47:15
   |
45 |     ctx = None
46 |     if insecure:
47 |         ctx = ssl._create_unverified_context()
   |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
48 |
49 |     def _do() -> str:
   |

S310 Audit URL open for permitted schemes. Allowing use of `file:` or custom schemes is often unexpected.
  --> tests/chaos/_load/harness.py:50:15
   |
49 |     def _do() -> str:
50 |         req = urllib.request.Request(url, headers={"Authorization": f"Bearer {jwt}"})
   |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
51 |         try:
52 |             with urllib.request.urlopen(req, timeout=5.0, context=ctx) as resp:
   |

S310 Audit URL open for permitted schemes. Allowing use of `file:` or custom schemes is often unexpected.
  --> tests/chaos/_load/harness.py:52:18
   |
50 |         req = urllib.request.Request(url, headers={"Authorization": f"Bearer {jwt}"})
51 |         try:
52 |             with urllib.request.urlopen(req, timeout=5.0, context=ctx) as resp:
   |                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
53 |                 return resp.read().decode("utf-8")
54 |         except (urllib.error.URLError, urllib.error.HTTPError):
   |

B905 `zip()` without an explicit `strict=` parameter
   --> tests/chaos/_load/harness.py:105:30
    |
103 |             ]
104 |             scrapes = await asyncio.gather(*scrape_coros, return_exceptions=False)
105 |             for t, scrape in zip(tenants, scrapes):
    |                              ^^^^^^^^^^^^^^^^^^^^^
106 |                 rss[t.connection_id].append(
107 |                     scrape.get("mt_node_mt5_process_rss_bytes", 0.0)
    |
help: Add explicit value for parameter `strict=`

S323 Python allows using an insecure context via the `_create_unverified_context` that reverts to the previous behavior that does not validate certificates or perform hostname checks.
  --> tests/chaos/_load/slo_checker.py:65:19
   |
63 |         ctx = None
64 |         if self._insecure:
65 |             ctx = ssl._create_unverified_context()
   |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
66 |
67 |         def _do() -> str:
   |

S310 Audit URL open for permitted schemes. Allowing use of `file:` or custom schemes is often unexpected.
  --> tests/chaos/_load/slo_checker.py:68:19
   |
67 |           def _do() -> str:
68 |               req = urllib.request.Request(url, headers={
   |  ___________________^
69 | |                 "Authorization": f"Bearer {self._admin_jwt}",
70 | |             })
   | |______________^
71 |               try:
72 |                   with urllib.request.urlopen(req, timeout=10.0, context=ctx) as resp:
   |

S310 Audit URL open for permitted schemes. Allowing use of `file:` or custom schemes is often unexpected.
  --> tests/chaos/_load/slo_checker.py:72:22
   |
70 |             })
71 |             try:
72 |                 with urllib.request.urlopen(req, timeout=10.0, context=ctx) as resp:
   |                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
73 |                     return resp.read().decode("utf-8")
74 |             except (urllib.error.URLError, urllib.error.HTTPError):
   |

PTH123 `open()` should be replaced by `Path.open()`
  --> tests/chaos/_load/tenant_provisioner.py:57:10
   |
55 |             "array of {login, password, server} objects (one per tenant)."
56 |         )
57 |     with open(path, encoding="utf-8") as fh:
   |          ^^^^
58 |         data = json.load(fh)
59 |     if not isinstance(data, list):
   |
help: Replace with `Path.open()`

ASYNC109 Async function definition with a `timeout` parameter
  --> tests/chaos/_load/tenant_provisioner.py:91:9
   |
89 |         *,
90 |         body: dict | None = None,
91 |         timeout: float = 30.0,
   |         ^^^^^^^^^^^^^^^^^^^^^
92 |     ) -> dict[str, Any]:
93 |         url = self._engine_url + path
   |
help: Use `asyncio.timeout` instead

S310 Audit URL open for permitted schemes. Allowing use of `file:` or custom schemes is often unexpected.
   --> tests/chaos/_load/tenant_provisioner.py:99:15
    |
 97 |         }
 98 |         data = json.dumps(body).encode("utf-8") if body is not None else None
 99 |         req = urllib.request.Request(url, method=method, headers=headers, data=data)
    |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
100 |         ctx = None
101 |         if self._insecure:
    |

S323 Python allows using an insecure context via the `_create_unverified_context` that reverts to the previous behavior that does not validate certificates or perform hostname checks.
   --> tests/chaos/_load/tenant_provisioner.py:102:19
    |
100 |         ctx = None
101 |         if self._insecure:
102 |             ctx = ssl._create_unverified_context()
    |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
103 |
104 |         # urllib is blocking; run in a worker thread so a slow engine
    |

S310 Audit URL open for permitted schemes. Allowing use of `file:` or custom schemes is often unexpected.
   --> tests/chaos/_load/tenant_provisioner.py:109:22
    |
107 |         def _do() -> str:
108 |             try:
109 |                 with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
    |                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
110 |                     return resp.read().decode("utf-8")
111 |             except urllib.error.HTTPError as exc:
    |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> tests/chaos/_load/tenant_provisioner.py:116:17
    |
114 |                 except Exception:  # noqa: BLE001
115 |                     err_body = str(exc)
116 |                 raise RuntimeError(f"HTTP {exc.code} {method} {path}: {err_body}")
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
117 |
118 |         raw = await asyncio.to_thread(_do)
    |

T201 `print` found
   --> tests/chaos/_load/tenant_provisioner.py:218:21
    |
216 |                     )
217 |                 except RuntimeError as exc:
218 |                     print(
    |                     ^^^^^
219 |                         f"teardown: DELETE {t.connection_id} failed: {exc}",
220 |                         flush=True,
    |
help: Remove `print`

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/_load/workload_driver.py:80:13
   |
78 |         url = self._engine_url + path
79 |         if params:
80 |             from urllib.parse import urlencode
   |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
81 |             url = url + "?" + urlencode(params)
82 |         headers = {
   |

S310 Audit URL open for permitted schemes. Allowing use of `file:` or custom schemes is often unexpected.
  --> tests/chaos/_load/workload_driver.py:86:15
   |
84 |             "X-User-Id": tenant.user_id,
85 |         }
86 |         req = urllib.request.Request(url, method="GET", headers=headers)
   |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
87 |         ctx = None
88 |         if self._insecure:
   |

S323 Python allows using an insecure context via the `_create_unverified_context` that reverts to the previous behavior that does not validate certificates or perform hostname checks.
  --> tests/chaos/_load/workload_driver.py:89:19
   |
87 |         ctx = None
88 |         if self._insecure:
89 |             ctx = ssl._create_unverified_context()
   |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
90 |
91 |         def _do() -> tuple[int, float]:
   |

S310 Audit URL open for permitted schemes. Allowing use of `file:` or custom schemes is often unexpected.
  --> tests/chaos/_load/workload_driver.py:94:22
   |
92 |             start = time.monotonic()
93 |             try:
94 |                 with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SECS, context=ctx) as resp:
   |                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
95 |                     resp.read()
96 |                     return (resp.status, (time.monotonic() - start) * 1000.0)
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/conftest.py:70:5
   |
68 |     if not real_cluster_available:
69 |         pytest.skip("ETRADIE_CHAOS_KUBECONFIG not set; skipping real-cluster test")
70 |     from kubernetes_asyncio import client, config
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
71 |
72 |     await config.load_kube_config(config_file=os.environ["ETRADIE_CHAOS_KUBECONFIG"])
   |

N818 Exception name `_Boom` should be named with an Error suffix
  --> tests/chaos/test_broker_connectivity.py:48:11
   |
46 |     monkeypatch.setattr("random.uniform", lambda a, b: 0.0)
47 |
48 |     class _Boom(Exception):
   |           ^^^^^
49 |         pass
   |

N818 Exception name `_Boom` should be named with an Error suffix
  --> tests/chaos/test_broker_connectivity.py:67:11
   |
65 |     monkeypatch.setattr("random.uniform", lambda a, b: 0.0)
66 |
67 |     class _Boom(Exception):
   |           ^^^^^
68 |         pass
   |

C408 Unnecessary `dict()` call (rewrite as a literal)
  --> tests/chaos/test_ea_identity_and_clock.py:28:12
   |
26 |   # ---------------------------------------------------------------------
27 |   def _snap(**overrides):
28 |       base = dict(
   |  ____________^
29 | |         magic_number=20260321,
30 | |         account_login="435112187",
31 | |         account_server="Exness-MT5Trial9",
32 | |         account_company="Exness",
33 | |         account_name="Test User",
34 | |         terminal_build=4200,
35 | |         ea_version="2.10.0",
36 | |         zmq_port=5555,
37 | |         started_at=int(_time.time()),
38 | |     )
   | |_____^
39 |       base.update(overrides)
40 |       return EAIdentitySnapshot(**base)
   |
help: Rewrite as a literal

N818 Exception name `_FakeApiException` should be named with an Error suffix
  --> tests/chaos/test_hosted_provisioner_contract.py:49:7
   |
49 | class _FakeApiException(Exception):
   |       ^^^^^^^^^^^^^^^^^
50 |     def __init__(self, status: int, reason: str = "fake", body: str = "") -> None:
51 |         super().__init__(reason)
   |

S105 Possible hardcoded password assigned to: "mt5_password_encrypted"
  --> tests/chaos/test_hosted_recovery_service.py:36:34
   |
34 |     row.mt5_server = "Exness-MT5Trial9"
35 |     row.mt5_login = "123456"
36 |     row.mt5_password_encrypted = "gAAAAA-fake-fernet-ciphertext"
   |                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
37 |     return row
   |

PLC0415 `import` should be at the top-level of a file
   --> tests/chaos/test_hosted_recovery_service.py:165:5
    |
163 |     # decrypt_credential is called inside _reprovision. Patch it so we
164 |     # do not need a real Fernet key.
165 |     import engine.ta.broker.mt5.hosted.recovery as recovery_mod
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
166 |     recovery_mod.decrypt_credential = lambda enc: "plaintext-password"  # type: ignore[assignment]
    |

S105 Possible hardcoded password assigned to: "password"
   --> tests/chaos/test_hosted_recovery_service.py:175:39
    |
173 |     assert call_kwargs["user_id"] == "user-1"
174 |     assert call_kwargs["login"] == "123456"
175 |     assert call_kwargs["password"] == "plaintext-password"
    |                                       ^^^^^^^^^^^^^^^^^^^^
176 |     assert call_kwargs["server"] == "Exness-MT5Trial9"
177 |     assert call_kwargs["platform"] == "mt5"
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/chaos/test_hosted_recovery_service.py:206:5
    |
204 |         }
205 |     )
206 |     import engine.ta.broker.mt5.hosted.recovery as recovery_mod
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
207 |     recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/chaos/test_hosted_recovery_service.py:256:5
    |
254 |     row = _make_row("ffffffffffff-1")
255 |     provisioner = _make_provisioner()  # default 'removed'
256 |     import engine.ta.broker.mt5.hosted.recovery as recovery_mod
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
257 |     recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/chaos/test_hosted_recovery_service.py:280:5
    |
278 |         status_by_release={release: {"status": "pending", "running": False}}
279 |     )
280 |     import engine.ta.broker.mt5.hosted.recovery as recovery_mod
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
281 |     recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/chaos/test_hosted_recovery_service.py:303:5
    |
301 |         ),
302 |     )
303 |     import engine.ta.broker.mt5.hosted.recovery as recovery_mod
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
304 |     recovery_mod.decrypt_credential = lambda enc: "plaintext"  # type: ignore[assignment]
    |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_broker_disconnect.py:30:5
   |
29 | async def _scrape(host: str, port: int) -> dict[str, float]:
30 |     from tests.chaos.test_mt_node_soak import _scrape_watchdog
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
31 |     return await _scrape_watchdog(host, port)
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_broker_disconnect.py:45:5
   |
43 |         pytest.skip("ETRADIE_CHAOS_MT_NODE_TOKEN not set")
44 |
45 |     import zmq
   |     ^^^^^^^^^^
46 |     import zmq.asyncio as zmq_async
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_broker_disconnect.py:46:5
   |
45 |     import zmq
46 |     import zmq.asyncio as zmq_async
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
47 |
48 |     ctx = zmq_async.Context.instance()
   |

SIM105 Use `contextlib.suppress(Exception)` instead of `try`-`except`-`pass`
  --> tests/chaos/test_mt_node_broker_disconnect.py:64:9
   |
62 |           sock.close(linger=0)
63 |       finally:
64 | /         try:
65 | |             sock.close(linger=0)
66 | |         except Exception:  # noqa: BLE001
67 | |             pass
   | |________________^
68 |
69 |       # Watchdog should issue an in-pod restart within MAX_FAILURES * POLL.
   |
help: Replace `try`-`except`-`pass` with `with contextlib.suppress(Exception): ...`

S110 `try`-`except`-`pass` detected, consider logging the exception
  --> tests/chaos/test_mt_node_broker_disconnect.py:66:9
   |
64 |           try:
65 |               sock.close(linger=0)
66 | /         except Exception:  # noqa: BLE001
67 | |             pass
   | |________________^
68 |
69 |       # Watchdog should issue an in-pod restart within MAX_FAILURES * POLL.
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_load_n_tenants.py:64:5
   |
62 |     if not real_cluster_available:
63 |         pytest.skip("ETRADIE_CHAOS_KUBECONFIG not set; load tests require a real cluster")
64 |     from tests.chaos._load.harness import build_harness_from_env
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
65 |     harness = build_harness_from_env()
66 |     if harness is None:
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_oom.py:26:5
   |
25 | async def _scrape(host: str, port: int) -> dict[str, float]:
26 |     from tests.chaos.test_mt_node_soak import _scrape_watchdog
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
27 |     return await _scrape_watchdog(host, port)
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_random_kill.py:43:5
   |
41 |     auth=0 polls.
42 |     """
43 |     import asyncio
   |     ^^^^^^^^^^^^^^
44 |     import random
45 |     import subprocess
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_random_kill.py:44:5
   |
42 |     """
43 |     import asyncio
44 |     import random
   |     ^^^^^^^^^^^^^
45 |     import subprocess
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_random_kill.py:45:5
   |
43 |     import asyncio
44 |     import random
45 |     import subprocess
   |     ^^^^^^^^^^^^^^^^^
46 |
47 |     if not real_cluster_available:
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_random_kill.py:49:5
   |
47 |     if not real_cluster_available:
48 |         pytest.skip("ETRADIE_CHAOS_KUBECONFIG not set")
49 |     from tests.chaos._load.harness import build_harness_from_env
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
50 |     harness = build_harness_from_env()
51 |     if harness is None:
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_random_kill.py:63:5
   |
61 |     # workload. We reuse LoadHarness.run but inject the kill task
62 |     # by extending the harness contract minimally below.
63 |     from tests.chaos._load.tenant_provisioner import TenantProvisioner
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
64 |     from tests.chaos._load.workload_driver import WorkloadDriver
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_random_kill.py:64:5
   |
62 |     # by extending the harness contract minimally below.
63 |     from tests.chaos._load.tenant_provisioner import TenantProvisioner
64 |     from tests.chaos._load.workload_driver import WorkloadDriver
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
65 |
66 |     prov = TenantProvisioner(
   |

S311 Standard pseudo-random generators are not suitable for cryptographic purposes
  --> tests/chaos/test_mt_node_random_kill.py:82:37
   |
80 |             for victim in victims:
81 |                 pod_name = f"etradie-mt-{victim.connection_id[:12]}-0"
82 |                 await asyncio.sleep(random.uniform(30, 60))
   |                                     ^^^^^^^^^^^^^^^^^^^^^^
83 |                 await asyncio.to_thread(
84 |                     subprocess.run,
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_mt_node_soak.py:31:5
   |
29 | async def _scrape_watchdog(host: str, port: int) -> dict[str, float]:
30 |     """Tiny parser that pulls Prometheus exposition into a flat dict."""
31 |     import urllib.request
   |     ^^^^^^^^^^^^^^^^^^^^^
32 |
33 |     raw = await asyncio.to_thread(
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_positions_snapshot_and_ghost.py:64:9
   |
63 |     try:
64 |         import psycopg2
   |         ^^^^^^^^^^^^^^^
65 |         import psycopg2.pool
66 |     except ImportError:
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/chaos/test_positions_snapshot_and_ghost.py:65:9
   |
63 |     try:
64 |         import psycopg2
65 |         import psycopg2.pool
   |         ^^^^^^^^^^^^^^^^^^^^
66 |     except ImportError:
67 |         pytest.skip("psycopg2 not installed; skipping snapshot chaos test")
   |

PLC0415 `import` should be at the top-level of a file
   --> tests/chaos/test_positions_snapshot_and_ghost.py:281:9
    |
279 |     """BEFORE UPDATE trigger must block any UPDATE on execution_positions_snapshot."""
280 |     try:
281 |         import psycopg2.errors
    |         ^^^^^^^^^^^^^^^^^^^^^^
282 |     except ImportError:
283 |         pytest.skip("psycopg2 not available")
    |

F401 `psycopg2.errors` imported but unused; consider using `importlib.util.find_spec` to test for availability
   --> tests/chaos/test_positions_snapshot_and_ghost.py:281:16
    |
279 |     """BEFORE UPDATE trigger must block any UPDATE on execution_positions_snapshot."""
280 |     try:
281 |         import psycopg2.errors
    |                ^^^^^^^^^^^^^^^
282 |     except ImportError:
283 |         pytest.skip("psycopg2 not available")
    |
help: Remove unused import: `psycopg2.errors`

PLC0415 `import` should be at the top-level of a file
   --> tests/chaos/test_positions_snapshot_and_ghost.py:305:9
    |
303 |     """BEFORE UPDATE trigger must block any UPDATE on execution_audit_logs."""
304 |     try:
305 |         import psycopg2.errors
    |         ^^^^^^^^^^^^^^^^^^^^^^
306 |     except ImportError:
307 |         pytest.skip("psycopg2 not available")
    |

F401 `psycopg2.errors` imported but unused; consider using `importlib.util.find_spec` to test for availability
   --> tests/chaos/test_positions_snapshot_and_ghost.py:305:16
    |
303 |     """BEFORE UPDATE trigger must block any UPDATE on execution_audit_logs."""
304 |     try:
305 |         import psycopg2.errors
    |                ^^^^^^^^^^^^^^^
306 |     except ImportError:
307 |         pytest.skip("psycopg2 not available")
    |
help: Remove unused import: `psycopg2.errors`

SIM108 Use ternary operator `ghosts = [] if latest_snapshot is None else _apply_ghost_detection(latest_snapshot["positions"], [], 999, 300)` instead of `if`-`else`-block
   --> tests/chaos/test_positions_snapshot_and_ghost.py:407:5
    |
405 |       # Mirrors the Go reconciler: if LatestSnapshot returns nil, return early.
406 |       latest_snapshot = None
407 | /     if latest_snapshot is None:
408 | |         ghosts = []
409 | |     else:
410 | |         ghosts = _apply_ghost_detection(
411 | |             latest_snapshot["positions"], [], 999, 300
412 | |         )
    | |_________^
413 |       assert ghosts == []
    |
help: Replace `if`-`else`-block with `ghosts = [] if latest_snapshot is None else _apply_ghost_detection(latest_snapshot["positions"], [], 999, 300)`

S603 `subprocess` call: check for execution of untrusted input
  --> tests/chaos/test_prometheusrule_renders.py:34:11
   |
32 |     for s in set_args:
33 |         cmd.extend(["--set", s])
34 |     out = subprocess.run(cmd, capture_output=True, text=True, check=False)
   |           ^^^^^^^^^^^^^^
35 |     assert out.returncode == 0, f"helm template {chart} failed: {out.stderr}"
36 |     return out.stdout
   |

PLC0415 `import` should be at the top-level of a file
   --> tests/chaos/test_watchdog_broker_disconnect_inproc.py:143:5
    |
141 |     in watchdog.py's ZmqHealthProbe docstring.
142 |     """
143 |     import zmq
    |     ^^^^^^^^^^
144 |
145 |     wd = watchdog_module
    |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/conftest.py:36:9
   |
34 |     """Check if PostgreSQL is reachable (sync check at import time)."""
35 |     try:
36 |         import asyncpg
   |         ^^^^^^^^^^^^^^
37 |
38 |         async def _ping():
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/conftest.py:56:9
   |
54 |     """Check if Redis is reachable."""
55 |     try:
56 |         import redis
   |         ^^^^^^^^^^^^
57 |
58 |         r = redis.from_url(_REDIS_URL, socket_timeout=2)
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/conftest.py:83:5
   |
81 |         pytest.skip("PostgreSQL not available")
82 |
83 |     from engine.shared.db.connection import DatabaseManager
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
84 |
85 |     mgr = DatabaseManager(
   |

PLC0415 `import` should be at the top-level of a file
   --> tests/integration/conftest.py:114:5
    |
112 |         pytest.skip("Redis not available")
113 |
114 |     from engine.shared.cache.redis_cache import RedisCache
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
115 |
116 |     cache = RedisCache(
    |

N806 Variable `MC` in function should be lowercase
  --> tests/integration/test_api_health.py:11:44
   |
 9 | @pytest_asyncio.fixture
10 | async def client():
11 |     with patch("engine.main.Container") as MC:
   |                                            ^^
12 |         c = MagicMock()
13 |         c.mt5_client = MagicMock()
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_api_health.py:23:9
   |
21 |         c.shutdown = AsyncMock()
22 |         MC.return_value = c
23 |         from engine.main import create_app
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
24 |         app = create_app()
25 |         app.state.container = c
   |

S105 Possible hardcoded password assigned to: "_BROKER_TEST_JWT_SECRET"
  --> tests/integration/test_broker_endpoints.py:20:27
   |
19 | # Deterministic JWT for broker integration tests
20 | _BROKER_TEST_JWT_SECRET = "test-secret-key-for-jwt-signing-must-be-long-enough-64chars-ok"
   |                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
21 |
22 | def _broker_test_jwt() -> str:
   |

E402 Module level import not at top of file
  --> tests/integration/test_broker_endpoints.py:35:1
   |
35 | / from engine.ta.broker.base import (
36 | |     AccountInfo,
37 | |     BrokerBase,
38 | |     BrokerCapabilities,
39 | |     HistoryDealInfo,
40 | |     OrderResult,
41 | |     PendingOrderInfo,
42 | |     PositionInfo,
43 | |     TickPrice,
44 | | )
   | |_^
45 |
46 |   pytestmark = pytest.mark.integration
   |

E501 Line too long (134 > 120)
   --> tests/integration/test_broker_endpoints.py:151:121
    |
149 |         return TickPrice(bid=1.1050, ask=1.1052, time=1700002000)
150 |
151 |     async def place_order(self, *, symbol, direction, order_type, price, stop_loss, take_profit, lot_size, comment="") -> OrderResult:
    |                                                                                                                         ^^^^^^^^^^^^^^
152 |         self._next_order_id += 1
153 |         status = "FILLED" if order_type.upper() == "MARKET" else "PLACED"
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/integration/test_broker_endpoints.py:182:5
    |
180 | async def client(mock_broker):
181 |     """FastAPI test client with mock broker injected into Container."""
182 |     import os
    |     ^^^^^^^^^
183 |     env_overrides = {
184 |         "AUTH_JWT_SECRET": _BROKER_TEST_JWT_SECRET,
    |

N806 Variable `MockContainer` in function should be lowercase
   --> tests/integration/test_broker_endpoints.py:189:83
    |
187 |     }
188 |     # Patch Container so it doesn't try to connect to real DB/Redis/broker
189 |     with patch.dict(os.environ, env_overrides), patch("engine.main.Container") as MockContainer:
    |                                                                                   ^^^^^^^^^^^^^
190 |         container = MagicMock()
191 |         container.mt5_client = mock_broker
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/integration/test_broker_endpoints.py:203:9
    |
201 |         MockContainer.return_value = container
202 |
203 |         from engine.main import create_app
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
204 |         app = create_app()
205 |         # Manually set container on app state (lifespan won't run in test)
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/integration/test_cache.py:109:5
    |
107 | async def test_namespace_validation(redis_cache):
108 |     """Invalid namespaces are rejected."""
109 |     from engine.shared.exceptions import CacheValidationError
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
110 |
111 |     with pytest.raises(CacheValidationError):
    |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_db_health.py:20:5
   |
18 | async def test_session_executes_query(db_manager):
19 |     """Write session can execute a simple query."""
20 |     from sqlalchemy import text
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^
21 |
22 |     async with db_manager.session() as session:
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_db_health.py:31:5
   |
29 | async def test_read_session_executes_query(db_manager):
30 |     """Read session can execute SELECT queries."""
31 |     from sqlalchemy import text
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^
32 |
33 |     async with db_manager.read_session() as session:
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_db_health.py:43:5
   |
41 | async def test_session_rollback_on_error(db_manager):
42 |     """Session rolls back on exception."""
43 |     from sqlalchemy import text
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^
44 |
45 |     try:
   |

PLC0415 `import` should be at the top-level of a file
   --> tests/integration/test_hosted_provisioner_release_naming.py:135:5
    |
133 |     writer must fail loudly so the engine cannot silently boot a Pod
134 |     whose broker catalog would never be persisted."""
135 |     from engine.shared.exceptions import ConfigurationError
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
136 |
137 |     provisioner = HostedProvisioner(
    |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_macro_registry.py:65:9
   |
63 | class TestCollectorImports:
64 |     def test_all_collectors_importable(self):
65 |         from engine.macro.collectors.calendar.collector import CalendarCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
66 |         from engine.macro.collectors.central_bank.collector import CentralBankCollector
67 |         from engine.macro.collectors.cot.collector import COTCollector
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_macro_registry.py:66:9
   |
64 |     def test_all_collectors_importable(self):
65 |         from engine.macro.collectors.calendar.collector import CalendarCollector
66 |         from engine.macro.collectors.central_bank.collector import CentralBankCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
67 |         from engine.macro.collectors.cot.collector import COTCollector
68 |         from engine.macro.collectors.dxy.collector import DXYCollector
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_macro_registry.py:67:9
   |
65 |         from engine.macro.collectors.calendar.collector import CalendarCollector
66 |         from engine.macro.collectors.central_bank.collector import CentralBankCollector
67 |         from engine.macro.collectors.cot.collector import COTCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
68 |         from engine.macro.collectors.dxy.collector import DXYCollector
69 |         from engine.macro.collectors.economic_data.collector import EconomicDataCollector
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_macro_registry.py:68:9
   |
66 |         from engine.macro.collectors.central_bank.collector import CentralBankCollector
67 |         from engine.macro.collectors.cot.collector import COTCollector
68 |         from engine.macro.collectors.dxy.collector import DXYCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
69 |         from engine.macro.collectors.economic_data.collector import EconomicDataCollector
70 |         from engine.macro.collectors.intermarket.collector import IntermarketCollector
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_macro_registry.py:69:9
   |
67 |         from engine.macro.collectors.cot.collector import COTCollector
68 |         from engine.macro.collectors.dxy.collector import DXYCollector
69 |         from engine.macro.collectors.economic_data.collector import EconomicDataCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
70 |         from engine.macro.collectors.intermarket.collector import IntermarketCollector
71 |         from engine.macro.collectors.sentiment.collector import SentimentCollector
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_macro_registry.py:70:9
   |
68 | …     from engine.macro.collectors.dxy.collector import DXYCollector
69 | …     from engine.macro.collectors.economic_data.collector import EconomicDataCollector
70 | …     from engine.macro.collectors.intermarket.collector import IntermarketCollector
   |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
71 | …     from engine.macro.collectors.sentiment.collector import SentimentCollector
72 | …     assert all([CentralBankCollector, COTCollector, DXYCollector, EconomicDataCollector, CalendarCollector, IntermarketCollector, Se…
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_macro_registry.py:71:9
   |
69 | …     from engine.macro.collectors.economic_data.collector import EconomicDataCollector
70 | …     from engine.macro.collectors.intermarket.collector import IntermarketCollector
71 | …     from engine.macro.collectors.sentiment.collector import SentimentCollector
   |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
72 | …     assert all([CentralBankCollector, COTCollector, DXYCollector, EconomicDataCollector, CalendarCollector, IntermarketCollector, Se…
   |

E501 Line too long (154 > 120)
  --> tests/integration/test_macro_registry.py:72:121
   |
70 | …marketCollector
71 | …ntCollector
72 | …conomicDataCollector, CalendarCollector, IntermarketCollector, SentimentCollector])
   |                                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   |

E501 Line too long (132 > 120)
  --> tests/integration/test_processor_pipeline.py:29:121
   |
27 |         "pair": "EURUSD", "timestamp": "2025-01-01T12:00:00Z",
28 |         "trading_style": "INTRADAY", "session": "NEW_YORK",
29 |         "macro_bias": {"base_currency": {"bias": "BULLISH", "evidence": []}, "quote_currency": {"bias": "BEARISH", "evidence": []}},
   |                                                                                                                         ^^^^^^^^^^^^
30 |         "dxy_bias": {"direction": "BEARISH", "evidence": []},
31 |         "cot_signal": {"summary": "Longs increasing", "extreme_flag": False, "evidence": []},
   |

E501 Line too long (126 > 120)
   --> tests/integration/test_processor_pipeline.py:126:121
    |
124 |     return ProcessorInput(
125 |         symbol="EURUSD",
126 |         ta_analysis={"status": "success", "smc_candidates": [{"pattern": "X", "direction": "BULLISH"}], "snd_candidates": []},
    |                                                                                                                         ^^^^^^
127 |         macro_analysis={},
128 |         retrieved_knowledge={"chunks": [{"id": "c1"}]},
    |

E501 Line too long (131 > 120)
   --> tests/integration/test_processor_pipeline.py:173:121
    |
171 |         with pytest.raises(ProcessorInsufficientDataError):
172 |             await p.process(
173 |                 ProcessorInput(symbol="X", ta_analysis={"smc_candidates": [], "snd_candidates": []}, retrieved_knowledge={"c": 1}),
    |                                                                                                                         ^^^^^^^^^^^
174 |                 user_id="test_user_id_123"
175 |             )
    |

ERA001 Found commented-out code
  --> tests/integration/test_rag_reranker.py:30:9
   |
28 | class TestDocTypeBoost:
29 |     def test_rulebook_outranks_lower_weighted(self, reranker):
30 |         # CHART_SCENARIO_LIBRARY: 0.70 * 1.2 = 0.84
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
31 |         # MASTER_RULEBOOK:        0.60 * 1.5 = 0.90  -> wins
32 |         ranked = reranker.rerank([_chunk(DocumentType.CHART_SCENARIO_LIBRARY, 0.70), _chunk(DocumentType.MASTER_RULEBOOK, 0.60)])
   |
help: Remove commented-out code

E501 Line too long (129 > 120)
  --> tests/integration/test_rag_reranker.py:32:121
   |
30 |         # CHART_SCENARIO_LIBRARY: 0.70 * 1.2 = 0.84
31 |         # MASTER_RULEBOOK:        0.60 * 1.5 = 0.90  -> wins
32 |         ranked = reranker.rerank([_chunk(DocumentType.CHART_SCENARIO_LIBRARY, 0.70), _chunk(DocumentType.MASTER_RULEBOOK, 0.60)])
   |                                                                                                                         ^^^^^^^^^
33 |         assert ranked[0].doc_type == DocumentType.MASTER_RULEBOOK
   |

ERA001 Found commented-out code
  --> tests/integration/test_rag_reranker.py:36:9
   |
35 |     def test_smc_boosted(self, reranker):
36 |         # CHART_SCENARIO_LIBRARY: 0.65 * 1.2 = 0.78
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
37 |         # SMC_FRAMEWORK:          0.62 * 1.3 = 0.806 -> wins
38 |         ranked = reranker.rerank([_chunk(DocumentType.CHART_SCENARIO_LIBRARY, 0.65), _chunk(DocumentType.SMC_FRAMEWORK, 0.62)])
   |
help: Remove commented-out code

E501 Line too long (127 > 120)
  --> tests/integration/test_rag_reranker.py:38:121
   |
36 |         # CHART_SCENARIO_LIBRARY: 0.65 * 1.2 = 0.78
37 |         # SMC_FRAMEWORK:          0.62 * 1.3 = 0.806 -> wins
38 |         ranked = reranker.rerank([_chunk(DocumentType.CHART_SCENARIO_LIBRARY, 0.65), _chunk(DocumentType.SMC_FRAMEWORK, 0.62)])
   |                                                                                                                         ^^^^^^^
39 |         assert ranked[0].doc_type == DocumentType.SMC_FRAMEWORK
   |

E501 Line too long (154 > 120)
  --> tests/integration/test_rag_reranker.py:52:121
   |
50 | …
51 | …ks the tie
52 | …BRARY, 0.80), _chunk(DocumentType.CHART_SCENARIO_LIBRARY, 0.80, "rules", "entry")])
   |                                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
53 | …
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_ta_repositories.py:26:9
   |
24 |     async def test_create_and_get_by_id(self, db_manager):
25 |         """Create a snapshot and retrieve it by ID."""
26 |         from engine.ta.storage.repositories.snapshot import SnapshotRepository
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
27 |
28 |         async with db_manager.session() as session:
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/integration/test_ta_repositories.py:73:9
   |
71 |     async def test_get_latest_snapshot(self, db_manager):
72 |         """get_latest_snapshot returns the most recent by timestamp."""
73 |         from engine.ta.storage.repositories.snapshot import SnapshotRepository
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
74 |
75 |         async with db_manager.session() as session:
   |

PLC0415 `import` should be at the top-level of a file
   --> tests/integration/test_ta_repositories.py:114:9
    |
112 |     async def test_version_auto_increments(self, db_manager):
113 |         """Each new snapshot for same symbol/tf increments version."""
114 |         from engine.ta.storage.repositories.snapshot import SnapshotRepository
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
115 |
116 |         async with db_manager.session() as session:
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/integration/test_ta_repositories.py:154:9
    |
152 |     async def test_get_snapshot_count(self, db_manager):
153 |         """Count snapshots for a symbol/timeframe."""
154 |         from engine.ta.storage.repositories.snapshot import SnapshotRepository
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
155 |
156 |         async with db_manager.session() as session:
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/integration/test_ta_repositories.py:182:9
    |
180 |     async def test_delete_by_id(self, db_manager):
181 |         """Delete snapshot and verify it's gone."""
182 |         from engine.ta.storage.repositories.snapshot import SnapshotRepository
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
183 |
184 |         async with db_manager.session() as session:
    |

PLC0415 `import` should be at the top-level of a file
  --> tests/macro/collectors/base_collectors.py:16:9
   |
14 |     def test_base_is_abstract(self):
15 |         """BaseCollector cannot be instantiated directly."""
16 |         import pytest
   |         ^^^^^^^^^^^^^
17 |         with pytest.raises(TypeError):
18 |             BaseCollector([], None, None)
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/macro/collectors/base_collectors.py:28:9
   |
26 | class TestConcreteCollectorImports:
27 |     def test_central_bank_collector(self):
28 |         from engine.macro.collectors.central_bank.collector import CentralBankCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
29 |         assert CentralBankCollector is not None
30 |         assert issubclass(CentralBankCollector, BaseCollector)
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/macro/collectors/base_collectors.py:33:9
   |
32 |     def test_cot_collector(self):
33 |         from engine.macro.collectors.cot.collector import COTCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
34 |         assert COTCollector is not None
35 |         assert issubclass(COTCollector, BaseCollector)
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/macro/collectors/base_collectors.py:38:9
   |
37 |     def test_economic_data_collector(self):
38 |         from engine.macro.collectors.economic_data.collector import EconomicDataCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
39 |         assert EconomicDataCollector is not None
40 |         assert issubclass(EconomicDataCollector, BaseCollector)
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/macro/collectors/base_collectors.py:43:9
   |
42 |     def test_calendar_collector(self):
43 |         from engine.macro.collectors.calendar.collector import CalendarCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
44 |         assert CalendarCollector is not None
45 |         assert issubclass(CalendarCollector, BaseCollector)
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/macro/collectors/base_collectors.py:48:9
   |
47 |     def test_dxy_collector(self):
48 |         from engine.macro.collectors.dxy.collector import DXYCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
49 |         assert DXYCollector is not None
50 |         assert issubclass(DXYCollector, BaseCollector)
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/macro/collectors/base_collectors.py:53:9
   |
52 |     def test_intermarket_collector(self):
53 |         from engine.macro.collectors.intermarket.collector import IntermarketCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
54 |         assert IntermarketCollector is not None
55 |         assert issubclass(IntermarketCollector, BaseCollector)
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/macro/collectors/base_collectors.py:58:9
   |
57 |     def test_sentiment_collector(self):
58 |         from engine.macro.collectors.sentiment.collector import SentimentCollector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
59 |         assert SentimentCollector is not None
60 |         assert issubclass(SentimentCollector, BaseCollector)
   |

PLC0415 `import` should be at the top-level of a file
   --> tests/macro/collectors/test_read_through_durability.py:183:5
    |
181 |     which are not fields of COTDataSet.
182 |     """
183 |     from engine.macro.collectors.cot.collector import COTCollector
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
184 |     from engine.macro.models.collector.cot import COTDataSet
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/macro/collectors/test_read_through_durability.py:184:5
    |
182 |     """
183 |     from engine.macro.collectors.cot.collector import COTCollector
184 |     from engine.macro.models.collector.cot import COTDataSet
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
185 |
186 |     empty = COTCollector.__new__(COTCollector)._empty_dataset()
    |

PLC0415 `import` should be at the top-level of a file
  --> tests/processor/service.py:19:9
   |
17 |     def test_service_importable(self):
18 |         """AnalysisProcessor can be imported without side effects."""
19 |         from engine.processor.service import AnalysisProcessor
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
20 |         assert AnalysisProcessor is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/processor/service.py:24:9
   |
22 |     def test_llm_client_importable(self):
23 |         """LLM client interface can be imported."""
24 |         from engine.processor.llm.client import LLMClient
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
25 |         assert LLMClient is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/processor/service.py:29:9
   |
27 |     def test_factory_importable(self):
28 |         """LLM factory can be imported."""
29 |         from engine.processor.llm.factory import create_llm_client
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
30 |         assert create_llm_client is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/rag/orchestrator.py:22:9
   |
20 |     def test_orchestrator_importable(self):
21 |         """RAGOrchestrator can be imported without side effects."""
22 |         from engine.rag.orchestrator import RAGOrchestrator
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
23 |         assert RAGOrchestrator is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/rag/orchestrator.py:26:9
   |
25 |     def test_retriever_importable(self):
26 |         from engine.rag.retrieval.retriever import Retriever
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
27 |         assert Retriever is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/rag/orchestrator.py:30:9
   |
29 |     def test_reranker_importable(self):
30 |         from engine.rag.retrieval.reranker import Reranker
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
31 |         assert Reranker is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/rag/orchestrator.py:34:9
   |
33 |     def test_scenario_matcher_importable(self):
34 |         from engine.rag.scenarios.matcher import ScenarioMatcher
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
35 |         assert ScenarioMatcher is not None
   |

ERA001 Found commented-out code
  --> tests/rag/ranking/reranker.py:66:9
   |
65 |         # Rulebook: 0.70 * 1.5 = 1.05 (capped to 1.0)
66 |         # Baseline: 0.85 * 1.0 = 0.85
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
67 |         assert ranked[0].doc_type == DocumentType.MASTER_RULEBOOK
68 |         assert ranked[1].doc_type == DocumentType.CHART_SCENARIO_LIBRARY
   |
help: Remove commented-out code

ERA001 Found commented-out code
  --> tests/rag/ranking/reranker.py:77:9
   |
75 |         ranked = reranker.rerank([baseline, smc])
76 |
77 |         # SMC: 0.65 * 1.3 = 0.845
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^
78 |         # Baseline: 0.80 * 1.0 = 0.80
79 |         assert ranked[0].doc_type == DocumentType.SMC_FRAMEWORK
   |
help: Remove commented-out code

ERA001 Found commented-out code
  --> tests/rag/ranking/reranker.py:78:9
   |
77 |         # SMC: 0.65 * 1.3 = 0.845
78 |         # Baseline: 0.80 * 1.0 = 0.80
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
79 |         assert ranked[0].doc_type == DocumentType.SMC_FRAMEWORK
   |
help: Remove commented-out code

PLC0415 `import` should be at the top-level of a file
  --> tests/rag/stores/retriever.py:19:9
   |
17 |     def test_retriever_importable(self):
18 |         """Retriever can be imported without side effects."""
19 |         from engine.rag.retrieval.retriever import Retriever
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
20 |         assert Retriever is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/rag/stores/retriever.py:23:9
   |
22 |     def test_vector_store_base_importable(self):
23 |         from engine.rag.vectorstore.base import BaseVectorStore
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
24 |         assert BaseVectorStore is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/rag/stores/retriever.py:27:9
   |
26 |     def test_embedding_base_importable(self):
27 |         from engine.rag.embeddings.base import BaseEmbeddingProvider
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
28 |         assert BaseEmbeddingProvider is not None
   |

PLC0415 `import` should be at the top-level of a file
   --> tests/shared/crypto/test_rewrap_service.py:134:5
    |
133 | def _legacy_token(raw_kek: str, plaintext: str) -> str:
134 |     import base64
    |     ^^^^^^^^^^^^^
135 |     import hashlib
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/shared/crypto/test_rewrap_service.py:135:5
    |
133 | def _legacy_token(raw_kek: str, plaintext: str) -> str:
134 |     import base64
135 |     import hashlib
    |     ^^^^^^^^^^^^^^
136 |
137 |     from cryptography.fernet import Fernet
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/shared/crypto/test_rewrap_service.py:137:5
    |
135 |     import hashlib
136 |
137 |     from cryptography.fernet import Fernet
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
138 |
139 |     digest = hashlib.sha256(raw_kek.encode()).digest()
    |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/smc/detector.py:18:9
   |
16 | class TestSMCDetectorImports:
17 |     def test_detector_importable(self):
18 |         from engine.ta.smc.detector import SMCDetector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
19 |         assert SMCDetector is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/smc/detector.py:22:9
   |
21 |     def test_smc_config_importable(self):
22 |         from engine.ta.smc.config import SMCConfig
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
23 |         cfg = SMCConfig()
24 |         assert cfg.enabled is True
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/smc/detector.py:29:9
   |
27 | class TestStructureEventModels:
28 |     def test_break_of_structure(self):
29 |         from engine.ta.models.structure_event import BreakOfStructure
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
30 |         assert BreakOfStructure is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/smc/detector.py:33:9
   |
32 |     def test_change_of_character(self):
33 |         from engine.ta.models.structure_event import ChangeOfCharacter
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
34 |         assert ChangeOfCharacter is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/smc/detector.py:37:9
   |
36 |     def test_break_in_market_structure(self):
37 |         from engine.ta.models.structure_event import BreakInMarketStructure
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
38 |         assert BreakInMarketStructure is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/smc/detector.py:41:9
   |
40 |     def test_shift_in_market_structure(self):
41 |         from engine.ta.models.structure_event import ShiftInMarketStructure
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
42 |         assert ShiftInMarketStructure is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/smc/detector.py:47:9
   |
45 | class TestZoneModels:
46 |     def test_order_block(self):
47 |         from datetime import UTC, datetime
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
48 |
49 |         from engine.ta.models.zone import OrderBlock
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/smc/detector.py:49:9
   |
47 |         from datetime import UTC, datetime
48 |
49 |         from engine.ta.models.zone import OrderBlock
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
50 |
51 |         ob = OrderBlock(
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/smc/detector.py:66:9
   |
65 |     def test_fair_value_gap(self):
66 |         from datetime import UTC, datetime
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
67 |
68 |         from engine.ta.models.zone import FairValueGap
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/smc/detector.py:68:9
   |
66 |         from datetime import UTC, datetime
67 |
68 |         from engine.ta.models.zone import FairValueGap
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
69 |
70 |         fvg = FairValueGap(
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/snd/detector.py:20:9
   |
18 | class TestSnDDetectorImports:
19 |     def test_detector_importable(self):
20 |         from engine.ta.snd.detector import SnDDetector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
21 |         assert SnDDetector is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/snd/detector.py:24:9
   |
23 |     def test_snd_config_importable(self):
24 |         from engine.ta.snd.config import SnDConfig
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
25 |         cfg = SnDConfig()
26 |         assert cfg.enabled is True
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/snd/detector.py:31:9
   |
29 | class TestSupplyDemandZoneModels:
30 |     def test_supply_zone(self):
31 |         from engine.ta.models.zone import SupplyZone
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
32 |
33 |         sz = SupplyZone(
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/snd/detector.py:49:9
   |
48 |     def test_demand_zone(self):
49 |         from engine.ta.models.zone import DemandZone
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
50 |
51 |         dz = DemandZone(
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/snd/detector.py:68:9
   |
66 | class TestQMLModels:
67 |     def test_quasi_modo_level_bearish(self):
68 |         from engine.ta.models.zone import QuasiModoLevel
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
69 |
70 |         qml = QuasiModoLevel(
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/analyzers/snd/detector.py:89:9
   |
88 |     def test_mini_price_level(self):
89 |         from engine.ta.models.zone import MiniPriceLevel
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
90 |
91 |         mpl = MiniPriceLevel(
   |

PLC0415 `import` should be at the top-level of a file
   --> tests/ta/analyzers/snd/detector.py:108:9
    |
106 | class TestSRFlipModels:
107 |     def test_sr_flip(self):
108 |         from engine.ta.models.structure_event import SRFlip
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
109 |
110 |         flip = SRFlip(
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/ta/analyzers/snd/detector.py:125:9
    |
124 |     def test_rs_flip(self):
125 |         from engine.ta.models.structure_event import RSFlip
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
126 |
127 |         flip = RSFlip(
    |

PLC0415 `import` should be at the top-level of a file
   --> tests/ta/analyzers/swing.py:116:5
    |
114 | def _make_swing_seq(symbol="EURUSD", invert=False):
115 |     """Creates a sequence with a guaranteed peak (or valley if invert=True)."""
116 |     from tests.factories import CandleSequence, make_candle
    |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
117 |     candles = []
118 |     base = datetime.now(UTC)
    |

E501 Line too long (125 > 120)
  --> tests/ta/broker/test_metaapi_client.py:64:121
   |
62 |     def test_parse_multiple_candles(self):
63 |         raw = [
64 |             {"time": "2024-01-15T10:00:00.000Z", "open": 1.09, "high": 1.10, "low": 1.08, "close": 1.095, "tickVolume": 100},
   |                                                                                                                         ^^^^^
65 |             {"time": "2024-01-15T11:00:00.000Z", "open": 1.095, "high": 1.11, "low": 1.09, "close": 1.10, "tickVolume": 200},
66 |             {"time": "2024-01-15T12:00:00.000Z", "open": 1.10, "high": 1.12, "low": 1.09, "close": 1.11, "tickVolume": 300},
   |

E501 Line too long (125 > 120)
  --> tests/ta/broker/test_metaapi_client.py:65:121
   |
63 |         raw = [
64 |             {"time": "2024-01-15T10:00:00.000Z", "open": 1.09, "high": 1.10, "low": 1.08, "close": 1.095, "tickVolume": 100},
65 |             {"time": "2024-01-15T11:00:00.000Z", "open": 1.095, "high": 1.11, "low": 1.09, "close": 1.10, "tickVolume": 200},
   |                                                                                                                         ^^^^^
66 |             {"time": "2024-01-15T12:00:00.000Z", "open": 1.10, "high": 1.12, "low": 1.09, "close": 1.11, "tickVolume": 300},
67 |         ]
   |

E501 Line too long (124 > 120)
  --> tests/ta/broker/test_metaapi_client.py:66:121
   |
64 |             {"time": "2024-01-15T10:00:00.000Z", "open": 1.09, "high": 1.10, "low": 1.08, "close": 1.095, "tickVolume": 100},
65 |             {"time": "2024-01-15T11:00:00.000Z", "open": 1.095, "high": 1.11, "low": 1.09, "close": 1.10, "tickVolume": 200},
66 |             {"time": "2024-01-15T12:00:00.000Z", "open": 1.10, "high": 1.12, "low": 1.09, "close": 1.11, "tickVolume": 300},
   |                                                                                                                         ^^^^
67 |         ]
   |

F841 Local variable `payload` is assigned to but never used
   --> tests/ta/broker/test_metaapi_client.py:136:13
    |
134 |             mock_api_post.assert_called_once()
135 |             _, kwargs = mock_api_post.call_args
136 |             payload = kwargs.get("payload", args[0] if (args := mock_api_post.call_args.args) else {})
    |             ^^^^^^^
137 |             # The second positional arg to _api_post is the payload dict
138 |             call_args = mock_api_post.call_args
    |
help: Remove assignment to unused variable `payload`

S105 Possible hardcoded password assigned to: "metaapi_token"
  --> tests/ta/broker/test_mt5_config.py:31:37
   |
29 |         )
30 |         assert cfg.provider == "metaapi"
31 |         assert cfg.metaapi_token == "token-abc"
   |                                     ^^^^^^^^^^^
32 |         assert cfg.metaapi_account_id == "acc-123"
   |

PLC0415 `import` should be at the top-level of a file
   --> tests/ta/broker/test_zmq_client.py:149:9
    |
147 |     @patch("engine.ta.broker.mt5.zmq.client.zmq_async.Context")
148 |     async def test_request_thread_safe_async(self, mock_ctx_class, client):
149 |         import json
    |         ^^^^^^^^^^^
150 |         mock_ctx = mock_ctx_class.return_value
151 |         mock_socket = mock_ctx.socket.return_value
    |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/orchestrator.py:14:9
   |
12 | class TestTAOrchestratorImports:
13 |     def test_orchestrator_importable(self):
14 |         from engine.ta.orchestrator import TAOrchestrator
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
15 |         assert TAOrchestrator is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/orchestrator.py:18:9
   |
17 |     def test_smc_detector_importable(self):
18 |         from engine.ta.smc.detector import SMCDetector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
19 |         assert SMCDetector is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/orchestrator.py:22:9
   |
21 |     def test_snd_detector_importable(self):
22 |         from engine.ta.snd.detector import SnDDetector
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
23 |         assert SnDDetector is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/orchestrator.py:26:9
   |
25 |     def test_snapshot_builder_importable(self):
26 |         from engine.ta.common.services.snapshot.builder import SnapshotBuilder
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
27 |         assert SnapshotBuilder is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/orchestrator.py:30:9
   |
29 |     def test_alignment_service_importable(self):
30 |         from engine.ta.common.services.alignment.service import AlignmentService
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
31 |         assert AlignmentService is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/orchestrator.py:34:9
   |
33 |     def test_timeframe_manager_importable(self):
34 |         from engine.ta.common.timeframe.manager import TimeframeManager
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
35 |         assert TimeframeManager is not None
   |

PLC0415 `import` should be at the top-level of a file
  --> tests/ta/orchestrator.py:41:9
   |
39 | class TestTAConfigForOrchestrator:
40 |     def test_ta_config_has_required_fields(self):
41 |         from engine.config import TAConfig
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
42 |         cfg = TAConfig()
43 |         assert hasattr(cfg, "htf_timeframes")
   |

DTZ001 `datetime.datetime()` called without a `tzinfo` argument
  --> tests/ta/test_candle_model.py:43:17
   |
42 |     def test_naive_timestamp_gets_utc(self):
43 |         naive = datetime(2024, 1, 15, 10, 0, 0)
   |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
44 |         c = make_candle(timestamp=naive)
45 |         assert c.timestamp.tzinfo is not None
   |
help: Pass a `datetime.timezone` object to the `tzinfo` parameter

Found 1761 errors (737 fixed, 1024 remaining).
No fixes available (187 hidden fixes can be enabled with the `--unsafe-fixes` option).
softverse@Softverse:~/eTradie$