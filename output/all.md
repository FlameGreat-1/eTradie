{
  "status": "success",
  "symbol": "EURUSD",
  "htf_timeframes": ["D1", "H4", "H1"],
  "ltf_timeframes": ["M30", "M15", "M5", "M1"],

  "snapshots": {
    "D1": {
      "symbol": "EURUSD",
      "timeframe": "D1",
      "timestamp": "2026-03-15T12:30:00",
      "candle_count": 500,
      "trend_direction": "BULLISH",
      
      "swing_highs": {
        "count": 12,
        "data": [
          {
            "price": 1.1500,
            "timestamp": "2026-03-10T10:00:00",
            "index": 485,
            "strength": 9,
            "timeframe": "D1"
          },
          {
            "price": 1.1450,
            "timestamp": "2026-02-20T15:30:00",
            "index": 420,
            "strength": 8,
            "timeframe": "D1"
          }
        ]
      },
      
      "swing_lows": {
        "count": 11,
        "data": [
          {
            "price": 1.1200,
            "timestamp": "2026-03-05T08:00:00",
            "index": 450,
            "strength": 8,
            "timeframe": "D1"
          }
        ]
      },
      
      "bms_events": {
        "count": 2,
        "data": [
          {
            "breakout_price": 1.1510,
            "broken_level": 1.1500,
            "timestamp": "2026-03-14T10:00:00",
            "direction": "BULLISH",
            "displacement_pips": 45.0,
            "timeframe": "D1",
            "confirmed": true
          }
        ]
      },
      
      "choch_events": {
        "count": 1,
        "data": [
          {
            "breakout_price": 1.1480,
            "broken_level": 1.1450,
            "timestamp": "2026-03-12T08:00:00",
            "direction": "BULLISH",
            "timeframe": "D1",
            "is_minor": false
          }
        ]
      },
      
      "sms_events": {
        "count": 2,
        "data": [
          {
            "failed_level": 1.1380,
            "reversal_price": 1.1370,
            "timestamp": "2026-03-08T12:00:00",
            "direction": "BEARISH",
            "timeframe": "D1",
            "is_failure_swing": true
          }
        ]
      },
      
      "order_blocks": {
        "count": 5,
        "data": [
          {
            "upper_bound": 1.1300,
            "lower_bound": 1.1250,
            "timestamp": "2026-02-28T10:00:00",
            "direction": "BULLISH",
            "displacement_pips": 120.0,
            "is_breaker": true,
            "mitigated": false,
            "timeframe": "D1",
            "candle_index": 420
          },
          {
            "upper_bound": 1.1400,
            "lower_bound": 1.1350,
            "timestamp": "2026-03-01T14:30:00",
            "direction": "BEARISH",
            "displacement_pips": 80.0,
            "is_breaker": false,
            "mitigated": true,
            "timeframe": "D1",
            "candle_index": 440
          }
        ]
      },
      
      "fair_value_gaps": {
        "count": 3,
        "data": [
          {
            "upper_bound": 1.1195,
            "lower_bound": 1.1185,
            "timestamp": "2026-03-13T15:00:00",
            "direction": "BEARISH",
            "filled": false,
            "fill_percentage": 0.0,
            "timeframe": "D1",
            "candle_index": 495
          },
          {
            "upper_bound": 1.1320,
            "lower_bound": 1.1310,
            "timestamp": "2026-03-10T08:00:00",
            "direction": "BULLISH",
            "filled": true,
            "fill_percentage": 85.5,
            "timeframe": "D1",
            "candle_index": 480
          }
        ]
      },
      
      "liquidity_sweeps": {
        "count": 4,
        "data": [
          {
            "swept_level": 1.1500,
            "timestamp": "2026-03-14T09:30:00",
            "liquidity_type": "BSL",
            "sweep_pips": 18.0,
            "closed_back_inside": true
          },
          {
            "swept_level": 1.1200,
            "timestamp": "2026-03-05T07:45:00",
            "liquidity_type": "SSL",
            "sweep_pips": 12.0,
            "closed_back_inside": true
          }
        ]
      },
      
      "inducement_events": {
        "count": 2,
        "data": [
          {
            "price": 1.1510,
            "timestamp": "2026-03-14T08:30:00",
            "direction": "BULLISH",
            "cleared": true
          }
        ]
      },
      
      "qm_levels": {
        "count": 1,
        "data": [
          {
            "qml_price": 1.1275,
            "timestamp": "2026-03-10T12:00:00",
            "direction": "BULLISH",
            "h_price": 1.1300,
            "hh_price": 1.1500,
            "h_timestamp": "2026-03-05T08:00:00",
            "hh_timestamp": "2026-03-10T10:00:00",
            "tested": true,
            "timeframe": "D1"
          }
        ]
      },
      
      "sr_flips": {
        "count": 2,
        "data": [
          {
            "flip_level": 1.1350,
            "breakout_price": 1.1355,
            "timestamp": "2026-03-08T10:00:00",
            "previous_role": "SUPPORT",
            "new_role": "RESISTANCE",
            "timeframe": "D1"
          }
        ]
      },
      
      "rs_flips": {
        "count": 1,
        "data": [
          {
            "flip_level": 1.1200,
            "breakout_price": 1.1195,
            "timestamp": "2026-03-05T09:00:00",
            "previous_role": "RESISTANCE",
            "new_role": "SUPPORT",
            "timeframe": "D1"
          }
        ]
      },
      
      "mpl_levels": {
        "count": 3,
        "data": [
          {
            "mpl_price": 1.1250,
            "timestamp": "2026-03-07T14:00:00",
            "direction": "BULLISH",
            "has_internal_structure": true,
            "tested": false,
            "timeframe": "D1"
          }
        ]
      },
      
      "supply_zones": {
        "count": 2,
        "data": [
          {
            "upper_bound": 1.1450,
            "lower_bound": 1.1400,
            "timestamp": "2026-02-20T15:30:00",
            "strength": 8,
            "tested": true,
            "test_count": 3,
            "broken": false,
            "timeframe": "D1"
          }
        ]
      },
      
      "demand_zones": {
        "count": 3,
        "data": [
          {
            "upper_bound": 1.1250,
            "lower_bound": 1.1200,
            "timestamp": "2026-03-05T08:00:00",
            "strength": 9,
            "tested": true,
            "test_count": 2,
            "broken": false,
            "timeframe": "D1"
          }
        ]
      },
      
      "fibonacci_retracements": {
        "count": 2,
        "data": [
          {
            "swing_high": 1.1500,
            "swing_low": 1.1200,
            "swing_high_timestamp": "2026-03-10T10:00:00",
            "swing_low_timestamp": "2026-03-05T08:00:00",
            "is_bullish": true
          }
        ]
      },
      
      "total_structure_events": 5,
      "total_liquidity_events": 8,
      "total_zones": 13
    },

    "H4": {
      "symbol": "EURUSD",
      "timeframe": "H4",
      "timestamp": "2026-03-15T12:00:00",
      "candle_count": 500,
      "trend_direction": "BULLISH",
      "swing_highs": { "count": 28, "data": [...] },
      "swing_lows": { "count": 27, "data": [...] },
      "bms_events": { "count": 5, "data": [...] },
      "choch_events": { "count": 3, "data": [...] },
      "sms_events": { "count": 4, "data": [...] },
      "order_blocks": { "count": 8, "data": [...] },
      "fair_value_gaps": { "count": 6, "data": [...] },
      "liquidity_sweeps": { "count": 12, "data": [...] },
      "inducement_events": { "count": 5, "data": [...] },
      "qm_levels": { "count": 2, "data": [...] },
      "sr_flips": { "count": 4, "data": [...] },
      "rs_flips": { "count": 3, "data": [...] },
      "mpl_levels": { "count": 5, "data": [...] },
      "supply_zones": { "count": 3, "data": [...] },
      "demand_zones": { "count": 5, "data": [...] },
      "fibonacci_retracements": { "count": 3, "data": [...] },
      "total_structure_events": 16,
      "total_liquidity_events": 22,
      "total_zones": 27
    },

    "H1": {
      "symbol": "EURUSD",
      "timeframe": "H1",
      "timestamp": "2026-03-15T12:00:00",
      "candle_count": 500,
      "trend_direction": "BULLISH",
      "swing_highs": { "count": 55, "data": [...] },
      "swing_lows": { "count": 54, "data": [...] },
      "bms_events": { "count": 12, "data": [...] },
      "choch_events": { "count": 8, "data": [...] },
      "sms_events": { "count": 10, "data": [...] },
      "order_blocks": { "count": 15, "data": [...] },
      "fair_value_gaps": { "count": 12, "data": [...] },
      "liquidity_sweeps": { "count": 25, "data": [...] },
      "inducement_events": { "count": 12, "data": [...] },
      "qm_levels": { "count": 4, "data": [...] },
      "sr_flips": { "count": 8, "data": [...] },
      "rs_flips": { "count": 6, "data": [...] },
      "mpl_levels": { "count": 10, "data": [...] },
      "supply_zones": { "count": 6, "data": [...] },
      "demand_zones": { "count": 8, "data": [...] },
      "fibonacci_retracements": { "count": 5, "data": [...] },
      "total_structure_events": 44,
      "total_liquidity_events": 55,
      "total_zones": 59
    },

    "M30": {
      "symbol": "EURUSD",
      "timeframe": "M30",
      "timestamp": "2026-03-15T12:00:00",
      "candle_count": 500,
      "trend_direction": "BULLISH",
      "swing_highs": { "count": 78, "data": [...] },
      "swing_lows": { "count": 77, "data": [...] },
      "bms_events": { "count": 18, "data": [...] },
      "choch_events": { "count": 12, "data": [...] },
      "sms_events": { "count": 15, "data": [...] },
      "order_blocks": { "count": 22, "data": [...] },
      "fair_value_gaps": { "count": 18, "data": [...] },
      "liquidity_sweeps": { "count": 35, "data": [...] },
      "inducement_events": { "count": 18, "data": [...] },
      "qm_levels": { "count": 6, "data": [...] },
      "sr_flips": { "count": 12, "data": [...] },
      "rs_flips": { "count": 10, "data": [...] },
      "mpl_levels": { "count": 15, "data": [...] },
      "supply_zones": { "count": 8, "data": [...] },
      "demand_zones": { "count": 12, "data": [...] },
      "fibonacci_retracements": { "count": 7, "data": [...] },
      "total_structure_events": 75,
      "total_liquidity_events": 85,
      "total_zones": 95
    },

    "M15": {
      "symbol": "EURUSD",
      "timeframe": "M15",
      "timestamp": "2026-03-15T12:00:00",
      "candle_count": 500,
      "trend_direction": "BULLISH",
      "swing_highs": { "count": 110, "data": [...] },
      "swing_lows": { "count": 110, "data": [...] },
      "bms_events": { "count": 28, "data": [...] },
      "choch_events": { "count": 18, "data": [...] },
      "sms_events": { "count": 22, "data": [...] },
      "order_blocks": { "count": 32, "data": [...] },
      "fair_value_gaps": { "count": 28, "data": [...] },
      "liquidity_sweeps": { "count": 52, "data": [...] },
      "inducement_events": { "count": 28, "data": [...] },
      "qm_levels": { "count": 10, "data": [...] },
      "sr_flips": { "count": 18, "data": [...] },
      "rs_flips": { "count": 16, "data": [...] },
      "mpl_levels": { "count": 22, "data": [...] },
      "supply_zones": { "count": 12, "data": [...] },
      "demand_zones": { "count": 16, "data": [...] },
      "fibonacci_retracements": { "count": 10, "data": [...] },
      "total_structure_events": 128,
      "total_liquidity_events": 145,
      "total_zones": 158
    },

    "M5": {
      "symbol": "EURUSD",
      "timeframe": "M5",
      "timestamp": "2026-03-15T12:00:00",
      "candle_count": 500,
      "trend_direction": "NEUTRAL",
      "swing_highs": { "count": 150, "data": [...] },
      "swing_lows": { "count": 150, "data": [...] },
      "bms_events": { "count": 42, "data": [...] },
      "choch_events": { "count": 28, "data": [...] },
      "sms_events": { "count": 35, "data": [...] },
      "order_blocks": { "count": 48, "data": [...] },
      "fair_value_gaps": { "count": 42, "data": [...] },
      "liquidity_sweeps": { "count": 78, "data": [...] },
      "inducement_events": { "count": 42, "data": [...] },
      "qm_levels": { "count": 16, "data": [...] },
      "sr_flips": { "count": 28, "data": [...] },
      "rs_flips": { "count": 24, "data": [...] },
      "mpl_levels": { "count": 35, "data": [...] },
      "supply_zones": { "count": 18, "data": [...] },
      "demand_zones": { "count": 24, "data": [...] },
      "fibonacci_retracements": { "count": 15, "data": [...] },
      "total_structure_events": 198,
      "total_liquidity_events": 225,
      "total_zones": 248
    },

    "M1": {
      "symbol": "EURUSD",
      "timeframe": "M1",
      "timestamp": "2026-03-15T12:00:00",
      "candle_count": 500,
      "trend_direction": "NEUTRAL",
      "swing_highs": { "count": 198, "data": [...] },
      "swing_lows": { "count": 198, "data": [...] },
      "bms_events": { "count": 65, "data": [...] },
      "choch_events": { "count": 45, "data": [...] },
      "sms_events": { "count": 58, "data": [...] },
      "order_blocks": { "count": 72, "data": [...] },
      "fair_value_gaps": { "count": 65, "data": [...] },
      "liquidity_sweeps": { "count": 125, "data": [...] },
      "inducement_events": { "count": 65, "data": [...] },
      "qm_levels": { "count": 28, "data": [...] },
      "sr_flips": { "count": 48, "data": [...] },
      "rs_flips": { "count": 42, "data": [...] },
      "mpl_levels": { "count": 58, "data": [...] },
      "supply_zones": { "count": 32, "data": [...] },
      "demand_zones": { "count": 42, "data": [...] },
      "fibonacci_retracements": { "count": 28, "data": [...] },
      "total_structure_events": 316,
      "total_liquidity_events": 368,
      "total_zones": 412
    }
  },

  "smc_candidates": [
    {
      "symbol": "EURUSD",
      "timeframe": "H4",
      "pattern": "SH_BMS_RTO_BULLISH",
      "direction": "BULLISH",
      "timestamp": "2026-03-14T12:00:00",
      "entry_price": 1.0995,
      "stop_loss": 1.0950,
      "take_profit": 1.1050,
      "risk_reward_ratio": 2.0,
      "framework": "SMC",
      "htf_timeframe": "D1",
      "ltf_timeframe": "H4",
      "htf_context": {
        "bms_price": 1.1200,
        "bms_timestamp": "2026-03-13T00:00:00",
        "confirmed": true
      },
      "ltf_confirmation": {
        "confirmed": true,
        "confirmation_timestamp": "2026-03-14T11:00:00"
      },
      "zone_upper": 1.1020,
      "zone_lower": 1.0970,
      "liquidity_swept": true,
      "swept_level": 1.0950,
      "swept_timestamp": "2026-03-14T10:30:00",
      "structure_broken": true,
      "broken_level": 1.1100,
      "session_context": "LONDON",
      "fib_level": "0.618",
      "metadata": {
        "displacement_pips": 120.0,
        "inducement_cleared": true
      }
    },
    {
      "symbol": "EURUSD",
      "timeframe": "M30",
      "pattern": "TURTLE_SOUP_LONG",
      "direction": "BULLISH",
      "timestamp": "2026-03-14T08:30:00",
      "entry_price": 1.0975,
      "stop_loss": 1.0920,
      "take_profit": 1.1080,
      "risk_reward_ratio": 3.2,
      "framework": "SMC",
      "htf_timeframe": "H1",
      "ltf_timeframe": "M30",
      "htf_context": {
        "bms_price": 1.1150,
        "choch_detected": true
      },
      "ltf_confirmation": {
        "confirmed": true,
        "confirmation_timestamp": "2026-03-14T08:15:00"
      },
      "zone_upper": 1.1000,
      "zone_lower": 1.0950,
      "liquidity_swept": true,
      "swept_level": 1.0920,
      "structure_broken": true,
      "broken_level": 1.1050,
      "session_context": "LONDON_NY_OVERLAP",
      "fib_level": "0.5",
      "metadata": {}
    },
    {
      "symbol": "EURUSD",
      "timeframe": "M15",
      "pattern": "SMS_BMS_RTO_BULLISH",
      "direction": "BULLISH",
      "timestamp": "2026-03-14T09:45:00",
      "entry_price": 1.0988,
      "stop_loss": 1.0945,
      "take_profit": 1.1065,
      "risk_reward_ratio": 2.4,
      "framework": "SMC",
      "htf_timeframe": "M30",
      "ltf_timeframe": "M15",
      "htf_context": {
        "sms_price": 1.1100,
        "bms_price": 1.1120
      },
      "ltf_confirmation": {
        "confirmed": true
      },
      "zone_upper": 1.1010,
      "zone_lower": 1.0960,
      "liquidity_swept": true,
      "swept_level": 1.0945,
      "structure_broken": true,
      "broken_level": 1.1090,
      "session_context": "LONDON_NY_OVERLAP",
      "fib_level": "0.382",
      "metadata": {}
    }
  ],

  "snd_candidates": [
    {
      "symbol": "EURUSD",
      "timeframe": "M15",
      "pattern": "FAKEOUT_KING_BUY",
      "direction": "BULLISH",
      "timestamp": "2026-03-14T09:15:00",
      "entry_price": 1.0975,
      "stop_loss": 1.0930,
      "take_profit": 1.1040,
      "risk_reward_ratio": 2.2,
      "framework": "SND",
      "htf_timeframe": "H1",
      "ltf_timeframe": "M15",
      "htf_context": {
        "qml_price": 1.0950,
        "sr_flip_price": 1.0955,
        "mpl_price": 1.0965
      },
      "ltf_confirmation": {
        "confirmed": true,
        "confirmation_timestamp": "2026-03-14T09:10:00",
        "marubozu_detected": true,
        "compression_detected": true
      },
      "zone_upper": 1.0985,
      "zone_lower": 1.0935,
      "liquidity_swept": true,
      "swept_level": null,
      "structure_broken": false,
      "broken_level": null,
      "session_context": "LONDON_NY_OVERLAP",
      "fib_level": "0.5",
      "metadata": {
        "fakeout_level": 1.0920,
        "previous_highs_count": 3,
        "compression_candle_count": 5
      }
    },
    {
      "symbol": "EURUSD",
      "timeframe": "M5",
      "pattern": "QML_SR_FLIP_FAKEOUT",
      "direction": "BEARISH",
      "timestamp": "2026-03-14T10:00:00",
      "entry_price": 1.1005,
      "stop_loss": 1.1030,
      "take_profit": 1.0940,
      "risk_reward_ratio": 2.6,
      "framework": "SND",
      "htf_timeframe": "M15",
      "ltf_timeframe": "M5",
      "htf_context": {
        "sr_flip_price": 1.1015,
        "mpl_price": 1.0995
      },
      "ltf_confirmation": {
        "confirmed": true,
        "marubozu_detected": true,
        "compression_candle_count": 3
      },
      "zone_upper": 1.1020,
      "zone_lower": 1.0990,
      "liquidity_swept": false,
      "structure_broken": true,
      "broken_level": 1.1025,
      "session_context": "OVERLAP",
      "fib_level": "0.618",
      "metadata": {
        "previous_lows_count": 2
      }
    }
  ],

  "smc_candidates_count": 3,
  "snd_candidates_count": 2,

  "alignment": {
    "D1_H4": {
      "htf_timeframe": "D1",
      "ltf_timeframe": "H4",
      "trends_aligned": true,
      "htf_ltf_aligned": true,
      "htf_trend": "BULLISH",
      "ltf_trend": "BULLISH",
      "alignment_metadata": {}
    },
    "H4_H1": {
      "htf_timeframe": "H4",
      "ltf_timeframe": "H1",
      "trends_aligned": true,
      "htf_ltf_aligned": true,
      "htf_trend": "BULLISH",
      "ltf_trend": "BULLISH",
      "alignment_metadata": {}
    },
    "H1_M30": {
      "htf_timeframe": "H1",
      "ltf_timeframe": "M30",
      "trends_aligned": true,
      "htf_ltf_aligned": true,
      "htf_trend": "BULLISH",
      "ltf_trend": "BULLISH",
      "alignment_metadata": {}
    },
    "M30_M15": {
      "htf_timeframe": "M30",
      "ltf_timeframe": "M15",
      "trends_aligned": true,
      "htf_ltf_aligned": true,
      "htf_trend": "BULLISH",
      "ltf_trend": "BULLISH",
      "alignment_metadata": {}
    },
    "M15_M5": {
      "htf_timeframe": "M15",
      "ltf_timeframe": "M5",
      "trends_aligned": false,
      "htf_ltf_aligned": false,
      "htf_trend": "BULLISH",
      "ltf_trend": "NEUTRAL",
      "alignment_metadata": {}
    },
    "M5_M1": {
      "htf_timeframe": "M5",
      "ltf_timeframe": "M1",
      "trends_aligned": false,
      "htf_ltf_aligned": false,
      "htf_trend": "NEUTRAL",
      "ltf_trend": "NEUTRAL",
      "alignment_metadata": {}
    }
  },

  "overall_trend": "BULLISH",
  "error": null
}