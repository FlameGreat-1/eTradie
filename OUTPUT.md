
---

## 🟢 TA SYSTEM OUTPUT (Complete & Structured)

The orchestrator.py method returns:

```json
{
  "status": "success | insufficient_data | error",
  "smc_candidates": 2,          // Count of detected SMC patterns
  "snd_candidates": 3,          // Count of detected SnD patterns
  "snapshot_id": "uuid-string"  // ID of persisted TechnicalSnapshot
}
```

### TA CANDIDATE STRUCTURES

#### **SMCCandidate** (for break-of-structure patterns):
```json
{
  "symbol": "EURUSD",
  "timeframe": "H4",
  "pattern": "break_of_structure | choch | bms | sms",
  "direction": "BULLISH | BEARISH",
  "timestamp": "2026-03-12T14:30:00Z",
  
  "entry_price": 1.0950,
  "stop_loss": 1.0920,
  "take_profit": 1.1020,
  
  "htf_timeframe": "D1",
  "ltf_timeframe": "H4",
  
  // HTF Structure Events
  "bms_detected": true,
  "bms_price": 1.0900,
  "bms_timestamp": "2026-03-10T00:00:00Z",
  
  "choch_detected": false,
  "choch_price": null,
  "choch_timestamp": null,
  
  "sms_detected": true,
  "sms_price": 1.0895,
  
  // HTF Zones
  "order_block_upper": 1.0975,
  "order_block_lower": 1.0945,
  
  "fvg_upper": 1.1010,
  "fvg_lower": 1.0980,
  
  // Liquidity Analysis
  "liquidity_swept": true,
  "swept_level": 1.0880,
  "sweep_timestamp": "2026-03-11T06:15:00Z",
  
  "inducement_cleared": true,
  "inducement_level": 1.0875,
  
  // LTF Confirmation
  "ltf_confirmation": true,
  "ltf_confirmation_timestamp": "2026-03-11T10:30:00Z",
  
  "displacement_pips": 120.5,
  
  "fib_level": "0.618",
  "session_context": "Asian",
  "metadata": {}
}
```

#### **SnDCandidate** (for supply/demand patterns):
```json
{
  "symbol": "EURUSD",
  "timeframe": "H4",
  "pattern": "supply_test | demand_mitigation | fakeout",
  "direction": "BEARISH",
  "timestamp": "2026-03-12T14:30:00Z",
  
  "entry_price": 1.0950,
  "stop_loss": 1.0920,
  "take_profit": 1.0880,
  
  "htf_timeframe": "D1",
  "ltf_timeframe": "H4",
  
  // HTF Level Events
  "qml_detected": true,
  "qml_price": 1.0960,
  
  "sr_flip_detected": true,
  "sr_flip_price": 1.0955,
  
  "rs_flip_detected": false,
  "rs_flip_price": null,
  
  "mpl_detected": true,
  "mpl_price": 1.0942,
  
  // Supply/Demand Zones
  "supply_zone_upper": 1.0975,
  "supply_zone_lower": 1.0955,
  
  "demand_zone_upper": 1.0920,
  "demand_zone_lower": 1.0900,
  
  // Fakeout Detection
  "fakeout_detected": true,
  "fakeout_level": 1.0965,
  
  "previous_highs_count": 3,
  "previous_lows_count": 2,
  
  // LTF Confirmation
  "marubozu_detected": false,
  "compression_detected": true,
  "compression_candle_count": 5,
  
  "ltf_confirmation": true,
  "ltf_confirmation_timestamp": "2026-03-11T10:30:00Z",
  
  "fib_level": "0.382",
  "session_context": "European",
  "metadata": {}
}
```

### TA TECHNICAL SNAPSHOT (Summary):
```json
{
  "symbol": "EURUSD",
  "timeframe": "H4",
  "timestamp": "2026-03-12T14:30:00Z",
  
  "trend_direction": "BEARISH",
  
  "swing_highs": [
    {"price": 1.1050, "timestamp": "2026-03-10T12:00:00Z", "index": 45},
    {"price": 1.0995, "timestamp": "2026-03-09T08:00:00Z", "index": 32}
  ],
  "swing_lows": [
    {"price": 1.0900, "timestamp": "2026-03-11T16:00:00Z", "index": 52},
    {"price": 1.0850, "timestamp": "2026-03-08T20:00:00Z", "index": 20}
  ],
  
  "bos_events": [{"price": 1.0900, "timestamp": "2026-03-10T06:00:00Z"}],
  "choch_events": [],
  "bms_events": [{"price": 1.0895, "timestamp": "2026-03-10T00:00:00Z"}],
  "sms_events": [],
  
  "supply_zones": [{"upper": 1.0975, "lower": 1.0955, "timestamp": "2026-03-09T12:00:00Z"}],
  "demand_zones": [{"upper": 1.0920, "lower": 1.0900, "timestamp": "2026-03-11T16:00:00Z"}],
  
  "order_blocks": [{"upper": 1.0975, "lower": 1.0945}],
  "fvgs": [{"upper": 1.1010, "lower": 1.0980}],
  
  "liquidity_sweeps": [{"level": 1.0880, "timestamp": "2026-03-11T06:15:00Z"}],
  
  "fibonacci_retracements": [
    {"level": 0.618, "price": 1.0900},
    {"level": 0.382, "price": 1.0925}
  ],
  
  "total_swing_points": 4,
  "total_structure_events": 2,
  "total_liquidity_events": 1,
  "total_zones": 4
}
```

---

## 🔴 MACRO SYSTEM OUTPUT 

### 1. **Central Bank Collector** → `CentralBankDataSet`
```json
{
  "rate_decisions": [
    {
      "bank": "FED",
      "event_type": "RATE_DECISION",
      "rate_current": 4.75,
      "rate_previous": 5.00,
      "rate_change_bps": -25,
      "tone": "dovish",
      "statement_summary": "Labor market cooling, inflation moderating",
      "decision_date": "2026-03-12T18:00:00Z"
    }
  ],
  "speeches": [
    {
      "bank": "ECB",
      "event_type": "CB_SPEECH",
      "speaker": "Christine Lagarde",
      "title": "Monetary Policy Outlook",
      "summary": "Maintaining hawkish stance on inflation",
      "tone": "hawkish",
      "speech_date": "2026-03-11T14:00:00Z"
    }
  ],
  "meeting_minutes": [
    {
      "bank": "BOE",
      "event_type": "MEETING_MINUTES",
      "title": "March 2026 MPC Meeting",
      "tone": "neutral",
      "hawkish_count": 4,
      "dovish_count": 3,
      "meeting_date": "2026-03-06T00:00:00Z",
      "release_date": "2026-03-12T09:00:00Z"
    }
  ],
  "forward_guidance": [
    {
      "bank": "BOJ",
      "event_type": "FORWARD_GUIDANCE",
      "title": "Rate Path Guidance",
      "rate_path_signal": "Likely holding rates through Q2 2026",
      "tone": "dovish",
      "guidance_date": "2026-03-10T00:00:00Z"
    }
  ],
  "banks_reporting": ["FED", "ECB", "BOE", "BOJ"],
  "collected_at": "2026-03-12T15:30:00Z"
}
```

### 2. **COT (Commitment of Traders) Collector** → `COTDataSet`
```json
{
  "latest_positions": [
    {
      "currency": "USD",
      "contract_name": "EUR/USD",
      "non_commercial_long": 250000,
      "non_commercial_short": 180000,
      "non_commercial_net": 70000,
      "commercial_long": 100000,
      "commercial_short": 150000,
      "commercial_net": -50000,
      "open_interest": 600000,
      "report_date": "2026-03-09"
    },
    {
      "currency": "GBP",
      "contract_name": "GBP/USD",
      "non_commercial_long": 85000,
      "non_commercial_short": 120000,
      "non_commercial_net": -35000,
      "commercial_long": 60000,
      "commercial_short": 70000,
      "commercial_net": -10000,
      "open_interest": 250000,
      "report_date": "2026-03-09"
    }
  ],
  "previous_positions": [],
  "report_date": "2026-03-09",
  "collected_at": "2026-03-12T15:30:00Z"
}
```

### 3. **Economic Data Collector** → `EconomicDataSet`
```json
{
  "releases": [
    {
      "currency": "USD",
      "indicator": "CPI",
      "indicator_name": "Consumer Price Index",
      "actual": 3.2,
      "forecast": 3.4,
      "previous": 3.6,
      "surprise": -0.2,
      "surprise_direction": "miss",
      "impact": "HIGH",
      "release_time": "2026-03-12T13:30:00Z",
      "source": "BLS"
    },
    {
      "currency": "EUR",
      "indicator": "UNEMPLOYMENT",
      "indicator_name": "Eurozone Unemployment Rate",
      "actual": 6.1,
      "forecast": 6.2,
      "previous": 6.3,
      "surprise": -0.1,
      "surprise_direction": "beat",
      "impact": "MEDIUM",
      "release_time": "2026-03-12T10:00:00Z",
      "source": "Eurostat"
    },
    {
      "currency": "GBP",
      "indicator": "NFP",
      "indicator_name": "UK Employment Change",
      "actual": 150000,
      "forecast": 180000,
      "previous": 200000,
      "surprise": -30000,
      "surprise_direction": "miss",
      "impact": "HIGH",
      "release_time": "2026-03-11T08:00:00Z",
      "source": "ONS"
    }
  ],
  "sources": ["BLS", "Eurostat", "ONS"],
  "collected_at": "2026-03-12T15:30:00Z"
}
```

### 4. **DXY (US Dollar Index) Collector** → `MarketDataSet`
```json
{
  "latest": {
    "dxy_value": 104.75,
    "gold_price": 2050.50,
    "silver_price": 24.30,
    "oil_price": 78.45,
    "us2y_yield": 4.25,
    "us10y_yield": 4.15,
    "us30y_yield": 4.12,
    "sp500": 5180.25,
    "vix": 16.75,
    "snapshot_at": "2026-03-12T15:00:00Z",
    "source": "Bloomberg"
  },
  "snapshots": [],
  "sources": ["Bloomberg", "Reuters"],
  "collected_at": "2026-03-12T15:30:00Z"
}
```

### 5. **Intermarket Collector** → `MarketDataSet`
```json
{
  "latest": {
    "dxy_value": 104.75,
    "gold_price": 2050.50,
    "sp500": 5180.25,
    "vix": 16.75,
    "us10y_yield": 4.15,
    "snapshot_at": "2026-03-12T15:00:00Z",
    "source": "TwelveData"
  },
  "snapshots": [],
  "sources": ["TwelveData"],
  "collected_at": "2026-03-12T15:30:00Z"
}
```

### 6. **Sentiment Collector** → `SentimentDataSet`
```json
{
  "sentiments": [
    {
      "currency": "USD",
      "source": "tradingeconomics",
      "long_percentage": 62.5,
      "short_percentage": 37.5,
      "net_positioning": 25.0
    },
    {
      "currency": "EUR",
      "source": "tradingeconomics",
      "long_percentage": 45.0,
      "short_percentage": 55.0,
      "net_positioning": -10.0
    },
    {
      "currency": "GBP",
      "source": "tradingeconomics",
      "long_percentage": 55.0,
      "short_percentage": 45.0,
      "net_positioning": 10.0
    }
  ],
  "sources": ["tradingeconomics"],
  "collected_at": "2026-03-12T15:30:00Z"
}
```

### 7. **News Collector** → `NewsDataSet`
```json
{
  "items": [
    {
      "headline": "Fed Cuts Rates 25bps Amid Inflation Moderation",
      "source": "Reuters",
      "summary": "The Federal Reserve lowered interest rates...",
      "currencies_mentioned": ["USD", "EUR"],
      "impact": "HIGH",
      "sentiment": "bearish",
      "published_at": "2026-03-12T18:15:00Z",
      "url": "https://reuters.com/..."
    },
    {
      "headline": "UK Employment Figures Disappoint",
      "source": "Bloomberg",
      "summary": "British unemployment worse than expected...",
      "currencies_mentioned": ["GBP"],
      "impact": "HIGH",
      "sentiment": "bearish",
      "published_at": "2026-03-11T08:30:00Z",
      "url": "https://bloomberg.com/..."
    }
  ],
  "sources": ["Reuters", "Bloomberg"],
  "collected_at": "2026-03-12T15:30:00Z"
}
```

### 8. **Calendar Collector** → `CalendarDataSet`
```json
{
  "events": [
    {
      "event_name": "US Non-Farm Payroll",
      "currency": "USD",
      "impact": "HIGH",
      "event_time": "2026-03-13T13:30:00Z",
      "actual": "",
      "forecast": "250000",
      "previous": "275000",
      "source": "Forex Factory"
    },
    {
      "event_name": "ECB Interest Rate Decision",
      "currency": "EUR",
      "impact": "HIGH",
      "event_time": "2026-03-20T13:00:00Z",
      "actual": "",
      "forecast": "3.75%",
      "previous": "4.00%",
      "source": "Forex Factory"
    }
  ],
  "sources": ["Forex Factory"],
  "collected_at": "2026-03-12T15:30:00Z"
}
```

---

















Here is the exact JSON the LLM outputs after every analysis cycle. This is what gets persisted, what the dashboard displays, and what gets mapped to the gateway's ProcessorOutput.
Example: Trade Approved (LONG EURUSD)



{
  "analysis_id": "analysis_EURUSD_20260314_0800_a3f1",
  "pair": "EURUSD",
  "timestamp": "2026-03-14T08:00:12Z",
  "trading_style": "INTRADAY",
  "session": "LONDON_OPEN",

  "macro_bias": {
    "base_currency": {
      "bias": "BULLISH",
      "evidence": [
        {"doc_id": "master_rulebook_v1", "chunk_id": "c_041", "section": "Section 4.1 Macro Bias", "rule_id": "MR-4.1", "content_preview": "ECB hawkish tone = bullish EUR signal"}
      ]
    },
    "quote_currency": {
      "bias": "BEARISH",
      "evidence": [
        {"doc_id": "master_rulebook_v1", "chunk_id": "c_042", "section": "Section 4.1 Macro Bias", "rule_id": "MR-4.1", "content_preview": "Fed dovish language = bearish USD signal"}
      ]
    }
  },

  "dxy_bias": {
    "direction": "BEARISH",
    "evidence": [
      {"doc_id": "master_rulebook_v1", "chunk_id": "c_015", "section": "Section 2.2 DXY Rules", "rule_id": "MR-2.2", "content_preview": "Bullish DXY = Bearish USD quote pair. DXY bearish = bullish EURUSD"}
    ]
  },

  "cot_signal": {
    "summary": "Non-commercial net long EUR increasing for 3 consecutive weeks, not at extreme",
    "week_over_week": "increase",
    "extreme_flag": false,
    "evidence": [
      {"doc_id": "cot_guide_v1", "chunk_id": "c_008", "section": "COT Interpretation", "rule_id": "COT-1", "content_preview": "Net long increasing WoW + not extreme = BULLISH signal"}
    ]
  },

  "event_risk": [
    {"event": "ECB Rate Decision", "time": "2026-03-16T12:45:00Z", "impact": "HIGH", "currency": "EUR"},
    {"event": "US Retail Sales", "time": "2026-03-15T13:30:00Z", "impact": "HIGH", "currency": "USD"}
  ],

  "1w_bias": {
    "structure": "bullish",
    "key_levels": [1.0720, 1.0950, 1.1050],
    "notes": "HH-HL formation intact. Price above 1W demand at 1.0720."
  },

  "1d_bias": {
    "structure": "choch_bullish",
    "key_levels": [1.0780, 1.0835, 1.0920],
    "notes": "1D ChoCH confirmed at 1.0835 with BOS above previous swing high. Demand zone at 1.0780 unmitigated."
  },

  "4h_setup": {
    "type": "OB",
    "zone_id": "OB_EURUSD_4H_20260314_01",
    "quality": "A",
    "bounds": [1.0832, 1.0850],
    "evidence": [
      {"doc_id": "smc_framework_v1", "chunk_id": "c_023", "section": "Order Block Validity", "rule_id": "SMC-OB-1", "content_preview": "Valid OB: strong impulse departure + BOS + not previously mitigated"}
    ]
  },

  "wyckoff_phase": {
    "phase": "markup",
    "evidence": [
      {"doc_id": "wyckoff_guide_v1", "chunk_id": "c_012", "section": "Markup Phase", "rule_id": "WYK-3", "content_preview": "Price rising out of accumulation with increasing volume. HH-HL structure."}
    ]
  },

  "confluence_score": {
    "score": 8.5,
    "factors": [
      {"name": "Macro bias aligned", "present": true, "value": 1.0, "notes": "EUR bullish + USD bearish = aligned with LONG"},
      {"name": "1W structure aligned", "present": true, "value": 1.0, "notes": "Weekly bullish HH-HL intact"},
      {"name": "1D BOS/ChoCH confirmed", "present": true, "value": 1.0, "notes": "1D ChoCH bullish at 1.0835"},
      {"name": "Valid SnD zone 4H+", "present": true, "value": 1.0, "notes": "Grade A demand zone at 1.0780"},
      {"name": "4H OB/FVG at entry", "present": true, "value": 1.0, "notes": "4H OB at 1.0832-1.0850 unmitigated"},
      {"name": "Liquidity sweep", "present": true, "value": 1.0, "notes": "SSL swept below 1.0830 with rejection wick"},
      {"name": "COT alignment", "present": true, "value": 1.0, "notes": "Specs net long EUR increasing 3 weeks"},
      {"name": "Wyckoff phase supports", "present": true, "value": 0.5, "notes": "Markup phase supports longs"},
      {"name": "No high-impact news 30min", "present": true, "value": 0.0, "notes": "Next event 26+ hours away"},
      {"name": "Minimum R:R achievable", "present": true, "value": 1.0, "notes": "R:R 5.38 exceeds 1:3 minimum for intraday"}
    ]
  },

  "setup_grade": "A",
  "direction": "LONG",

  "entry_zone": {"low": 1.08320, "high": 1.08500},

  "stop_loss": {
    "price": 1.07780,
    "reason": "Below 4H OB low (1.0832) + 1D demand zone (1.0780) with 3 pip buffer. Not on round number.",
    "evidence": [
      {"doc_id": "master_rulebook_v1", "chunk_id": "c_067", "section": "Section 8.3 SL Placement", "rule_id": "MR-8.3", "content_preview": "SL placed beyond OB low + spread buffer. Never on round number."}
    ]
  },

  "take_profits": [
    {"level": 1.09200, "size_pct": 40, "basis": "Nearest liquidity pool at previous 4H swing high"},
    {"level": 1.09850, "size_pct": 30, "basis": "1D structure target at major supply zone"},
    {"level": 1.10500, "size_pct": 30, "basis": "1W key level and final macro target"}
  ],

  "rr_ratio": 5.38,
  "confidence": "HIGH",
  "proceed_to_module_b": "YES",

  "explainable_reasoning": "EURUSD presents a high-probability long setup. Macro environment is strongly aligned: ECB hawkish tone supports EUR strength while Fed dovish guidance weakens USD. DXY is bearish with descending structure below the 50MA, confirming inverse bullish bias for EURUSD per Rulebook Section 2.2. COT shows non-commercial net long EUR increasing for 3 consecutive weeks without reaching extreme levels, supporting the bullish thesis per COT Interpretation Guide. Weekly structure shows intact HH-HL formation with price above the 1W demand at 1.0720. Daily confirmed a ChoCH bullish at 1.0835 with a BOS above the previous swing high. On the 4H, an unmitigated Grade A order block sits at 1.0832-1.0850 with a liquidity sweep below 1.0830 that rejected sharply, creating a high-quality entry scenario per SMC Framework Section OB-1. Wyckoff analysis identifies the current phase as Markup, supporting continuation longs. All 5 mandatory confluence factors are present plus 3 bonus factors for a total score of 8.5/10 (Grade A). Entry at OTE zone 1.0832-1.0850, SL at 1.0778 below structural invalidation with 3-pip buffer, targeting TP1 at 1.0920 (nearest liquidity), TP2 at 1.0985 (1D supply), TP3 at 1.1050 (1W level). R:R of 5.38 exceeds the 1:3 intraday minimum. No high-impact events within 30 minutes. Proceeding to Module B.",

  "rag_sources": [
    {"doc_id": "master_rulebook_v1", "chunk_id": "c_041", "section": "Section 4.1 Macro Bias", "relevance_score": 0.95},
    {"doc_id": "master_rulebook_v1", "chunk_id": "c_015", "section": "Section 2.2 DXY Rules", "relevance_score": 0.93},
    {"doc_id": "smc_framework_v1", "chunk_id": "c_023", "section": "Order Block Validity", "relevance_score": 0.91},
    {"doc_id": "master_rulebook_v1", "chunk_id": "c_067", "section": "Section 8.3 SL Placement", "relevance_score": 0.89},
    {"doc_id": "cot_guide_v1", "chunk_id": "c_008", "section": "COT Interpretation", "relevance_score": 0.87},
    {"doc_id": "wyckoff_guide_v1", "chunk_id": "c_012", "section": "Markup Phase", "relevance_score": 0.85}
  ],

  "audit": {
    "retrieval": {
      "query_summary": "EURUSD bullish BOS order block fair value gap liquidity sweep Fed dovish ECB hawkish DXY bearish COT EUR net long",
      "strategy_used": "scenario_first",
      "top_k": 8,
      "chunks_returned": [
        {"doc_id": "master_rulebook_v1", "chunk_id": "c_041", "section": "Section 4.1", "relevance_score": 0.95},
        {"doc_id": "smc_framework_v1", "chunk_id": "c_023", "section": "OB Validity", "relevance_score": 0.91},
        {"doc_id": "master_rulebook_v1", "chunk_id": "c_067", "section": "Section 8.3", "relevance_score": 0.89}
      ]
    },
    "citations": [
      {"doc_id": "master_rulebook_v1", "chunk_id": "c_041", "section": "Section 4.1 Macro Bias", "relevance_score": 0.95},
      {"doc_id": "master_rulebook_v1", "chunk_id": "c_015", "section": "Section 2.2 DXY", "relevance_score": 0.93},
      {"doc_id": "smc_framework_v1", "chunk_id": "c_023", "section": "OB Validity", "relevance_score": 0.91}
    ]
  }
}






Example: NO SETUP (Conflicting Timeframes)


{
  "analysis_id": "analysis_GBPUSD_20260314_0800_b7e2",
  "pair": "GBPUSD",
  "timestamp": "2026-03-14T08:00:15Z",
  "trading_style": "INTRADAY",
  "session": "LONDON_OPEN",

  "macro_bias": {
    "base_currency": {"bias": "NEUTRAL", "evidence": [...]},
    "quote_currency": {"bias": "BEARISH", "evidence": [...]}
  },

  "dxy_bias": {"direction": "BEARISH", "evidence": [...]},

  "cot_signal": {
    "summary": "Non-commercial net short GBP, decreasing",
    "week_over_week": "decrease",
    "extreme_flag": false,
    "evidence": [...]
  },

  "event_risk": [],

  "1w_bias": {"structure": "bearish", "key_levels": [1.2550, 1.2700], "notes": "1W in downtrend, LH-LL"},
  "1d_bias": {"structure": "bullish", "key_levels": [1.2620, 1.2680], "notes": "1D BOS bullish at 1.2620"},
  "4h_setup": {"type": null, "zone_id": null, "quality": null, "bounds": [], "evidence": []},

  "wyckoff_phase": {"phase": "ranging", "evidence": [...]},

  "confluence_score": {
    "score": 3.0,
    "factors": [
      {"name": "Macro bias aligned", "present": false, "value": 0.0, "notes": "GBP neutral, not aligned with either direction"},
      {"name": "1W structure aligned", "present": false, "value": 0.0, "notes": "1W bearish conflicts with 1D bullish"},
      {"name": "1D BOS/ChoCH confirmed", "present": true, "value": 1.0, "notes": "1D BOS bullish confirmed"},
      {"name": "Valid SnD zone 4H+", "present": false, "value": 0.0, "notes": "No unmitigated zone identified"},
      {"name": "4H OB/FVG at entry", "present": false, "value": 0.0, "notes": "No valid OB or FVG at current price"},
      {"name": "Liquidity sweep", "present": false, "value": 0.0, "notes": "No sweep detected"},
      {"name": "COT alignment", "present": true, "value": 1.0, "notes": "COT short decreasing supports potential reversal"},
      {"name": "Wyckoff phase supports", "present": false, "value": 0.0, "notes": "Ranging phase, no directional support"},
      {"name": "No high-impact news 30min", "present": true, "value": 0.0, "notes": "No events within window"},
      {"name": "Minimum R:R achievable", "present": true, "value": 1.0, "notes": "Theoretical R:R available but no valid entry zone"}
    ]
  },

  "setup_grade": "REJECT",
  "direction": "NO SETUP",

  "entry_zone": {"low": null, "high": null},
  "stop_loss": {"price": null, "reason": "", "evidence": []},
  "take_profits": [],
  "rr_ratio": null,

  "confidence": "NO SETUP",
  "proceed_to_module_b": "NO",

  "explainable_reasoning": "GBPUSD does not present a valid setup. The 1W structure is bearish (LH-LL) while the 1D has confirmed a bullish BOS at 1.2620, creating a direct timeframe conflict. Per Rulebook Section 3.2: 'A trade is only valid when 1W, 1D, and 4H all agree on direction. If any one timeframe contradicts the thesis, the setup is rejected.' Additionally, no unmitigated Grade A or B supply/demand zone was identified on the 4H, and no valid order block or FVG exists at current price levels. Macro bias for GBP is neutral, failing the mandatory macro alignment factor. Confluence score of 3.0/10 falls below the 5.0 rejection threshold. Output: NO SETUP.",

  "rag_sources": [
    {"doc_id": "master_rulebook_v1", "chunk_id": "c_029", "section": "Section 3.2 Timeframe Alignment", "relevance_score": 0.94}
  ],

  "audit": {
    "retrieval": {
      "query_summary": "GBPUSD bearish weekly bullish daily conflict timeframe alignment",
      "strategy_used": "rule_first",
      "top_k": 6,
      "chunks_returned": [
        {"doc_id": "master_rulebook_v1", "chunk_id": "c_029", "section": "Section 3.2", "relevance_score": 0.94}
      ]
    },
    "citations": [
      {"doc_id": "master_rulebook_v1", "chunk_id": "c_029", "section": "Section 3.2 Timeframe Alignment", "relevance_score": 0.94}
    ]
  }
}







Detail View (GET /api/analysis/{id}) - full page shows:



summary:
  "LONG EURUSD - Grade A - Score 8.5/10"

reasoning:
  "EURUSD presents a high-probability long setup. Macro environment is
   strongly aligned: ECB hawkish tone supports EUR strength while Fed
   dovish guidance weakens USD. DXY is bearish with descending structure
   below the 50MA, confirming inverse bullish bias for EURUSD..."

macro_summary:
  "Base currency: BULLISH
   Quote currency: BEARISH
   US Dollar (DXY): BEARISH
   COT: Non-commercial net long EUR increasing for 3 consecutive weeks"

technical_summary:
  "Weekly: Bullish
     HH-HL formation intact. Price above 1W demand at 1.0720.
   Daily: Choch Bullish
     1D ChoCH confirmed at 1.0835 with BOS above previous swing high.
   4H Setup: OB (Grade A) at 1.0832 - 1.0850
   Wyckoff Phase: Markup"

trade_plan:
  "Direction: LONG
   Entry Zone: 1.0832 to 1.085
   Stop Loss: 1.0778 (Below 4H OB low + 1D demand zone with 3 pip buffer)
   Take Profit 1: 1.092 (close 40% of position) - Nearest liquidity pool
   Take Profit 2: 1.0985 (close 30% of position) - 1D structure target
   Take Profit 3: 1.105 (close 30% of position) - 1W key level
   Reward-to-Risk Ratio: 1:5.4"

confluence_breakdown:
  "Confluence Score: 8.5/10

     + Macro bias aligned: PRESENT (+1.0) - EUR bullish + USD bearish
     + 1W structure aligned: PRESENT (+1.0) - Weekly bullish HH-HL intact
     + 1D BOS/ChoCH confirmed: PRESENT (+1.0) - 1D ChoCH bullish at 1.0835
     + Valid SnD zone 4H+: PRESENT (+1.0) - Grade A demand zone at 1.0780
     + 4H OB/FVG at entry: PRESENT (+1.0) - 4H OB at 1.0832-1.0850
     + Liquidity sweep: PRESENT (+1.0) - SSL swept below 1.0830
     + COT alignment: PRESENT (+1.0) - Specs net long EUR increasing
     + Wyckoff phase supports: PRESENT (+0.5) - Markup phase supports longs
     + No high-impact news 30min: PRESENT - Next event 26+ hours away
     + Minimum R:R achievable: PRESENT (+1.0) - R:R 5.38 exceeds minimum"

risk_info:
  "Confidence: HIGH
   Setup Grade: A
   Risk Allocation: 1% of account
   Status: Approved for execution"

event_warnings:
  "Upcoming High-Impact Events:
     - ECB Rate Decision (EUR) at 2026-03-16T12:45:00Z
     - US Retail Sales (USD) at 2026-03-15T13:30:00Z"

analyzed_by:
  "Analyzed by: Anthropic Claude (claude-sonnet-4-20250514) in 12.3 seconds"
