{
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
  "snd_candidates_count": 2
}