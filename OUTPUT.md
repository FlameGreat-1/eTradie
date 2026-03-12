
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
