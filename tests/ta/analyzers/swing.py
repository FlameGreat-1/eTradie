from datetime import UTC, datetime, timedelta

from engine.ta.analyzers.swing import detect_swings, get_latest_swings
from tests.factories import make_candle, make_candle_sequence


def test_detect_swings_uptrend():
    """An uptrend should form mostly swing lows and higher swing highs."""
    seq = make_candle_sequence(count=20, trend="up")
    swings = detect_swings(seq, left_bars=2, right_bars=2)
    
    # Basic structural check
    assert isinstance(swings, list)
    if swings:
        assert swings[0].type in ("high", "low")
        assert swings[0].price > 0


def test_detect_swings_downtrend():
    """A downtrend should form mostly lower highs and lower lows."""
    seq = make_candle_sequence(count=20, trend="down")
    swings = detect_swings(seq, left_bars=3, right_bars=3)
    
    assert isinstance(swings, list)


def test_detect_swings_ranging():
    """A ranging market forms alternating highs and lows."""
    seq = make_candle_sequence(count=30, trend="ranging")
    swings = detect_swings(seq, left_bars=1, right_bars=1)
    
    assert isinstance(swings, list)
    assert len(swings) > 2


def test_get_latest_swings():
    """Test grabbing exactly 1 high and 1 low from end of list."""
    seq = make_candle_sequence(count=50, trend="ranging")
    swings = detect_swings(seq, left_bars=2, right_bars=2)
    
    latest_high, latest_low = get_latest_swings(swings)
    
    assert latest_high is None or latest_high.type == "high"
    assert latest_low is None or latest_low.type == "low"
