from datetime import UTC, datetime

from engine.ta.analyzers.candle import (
    is_bearish_engulfing,
    is_bullish_engulfing,
    is_doji,
    is_marubozu,
    is_pin_bar,
)
from engine.ta.constants import Timeframe
from tests.factories import make_candle


def test_is_doji():
    """Test doji classification (open nearly equal to close)."""
    # Perfect doji
    c1 = make_candle(datetime.now(), open=1.0, high=1.05, low=0.95, close=1.0)
    assert is_doji(c1) is True
    
    # Near doji within 10% tolerance
    body = 0.009
    total = 0.1
    c2 = make_candle(datetime.now(), open=1.0, close=1.0+body, high=1.05, low=0.95)
    assert is_doji(c2) is True
    
    # Not a doji
    c3 = make_candle(datetime.now(), open=1.0, close=1.1, high=1.15, low=0.95)
    assert is_doji(c3) is False


def test_is_marubozu():
    """Test marubozu classification (very little wick)."""
    # Perfect bullish marubozu
    c1 = make_candle(datetime.now(), open=1.0, low=1.0, close=1.1, high=1.1)
    assert is_marubozu(c1) is True
    
    # Perfect bearish marubozu
    c2 = make_candle(datetime.now(), open=1.1, high=1.1, close=1.0, low=1.0)
    assert is_marubozu(c2) is True
    
    # Normal candle
    c3 = make_candle(datetime.now(), open=1.0, low=0.9, close=1.1, high=1.2)
    assert is_marubozu(c3) is False


def test_is_pin_bar():
    """Test pin bar classification."""
    # Bullish pin bar (long lower wick)
    c1 = make_candle(datetime.now(), open=1.05, close=1.06, high=1.07, low=0.90)
    assert is_pin_bar(c1) == "bullish"
    
    # Bearish pin bar (long upper wick)
    c2 = make_candle(datetime.now(), open=1.05, close=1.04, high=1.20, low=1.03)
    assert is_pin_bar(c2) == "bearish"
    
    # Not a pin bar
    c3 = make_candle(datetime.now(), open=1.0, close=1.1, high=1.15, low=0.95)
    assert is_pin_bar(c3) is None


def test_is_bullish_engulfing():
    """Test bullish engulfing pattern between two candles."""
    prev = make_candle(datetime.now(), open=1.05, close=1.0, high=1.06, low=0.99)
    curr = make_candle(datetime.now(), open=0.99, close=1.06, high=1.07, low=0.98)
    
    assert is_bullish_engulfing(prev, curr) is True
    
    # Curr is bearish
    curr.close = 0.95
    assert is_bullish_engulfing(prev, curr) is False
    
    # Curr body doesn't engulf
    curr.open = 1.01
    curr.close = 1.04
    assert is_bullish_engulfing(prev, curr) is False


def test_is_bearish_engulfing():
    """Test bearish engulfing pattern between two candles."""
    prev = make_candle(datetime.now(), open=1.0, close=1.05, high=1.06, low=0.99)
    curr = make_candle(datetime.now(), open=1.06, close=0.99, high=1.07, low=0.98)
    
    assert is_bearish_engulfing(prev, curr) is True
    
    # Curr is bullish
    curr.close = 1.10
    assert is_bearish_engulfing(prev, curr) is False
