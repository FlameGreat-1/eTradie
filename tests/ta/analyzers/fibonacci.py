from engine.ta.analyzers.fibonacci import calculate_retracements


def test_fibonacci_bullish_retracement():
    """Test standard bullish retracement levels (low to high)."""
    swing_low = 1.0000
    swing_high = 2.0000
    
    levels = calculate_retracements(swing_high, swing_low, trend="bullish")
    
    assert levels[0.0] == 2.0000  # 0% retraced = high
    assert levels[1.0] == 1.0000  # 100% retraced = low
    assert levels[0.5] == 1.5000  # 50%
    assert round(levels[0.618], 4) == 1.3820
    assert round(levels[0.786], 4) == 1.2140


def test_fibonacci_bearish_retracement():
    """Test standard bearish retracement levels (high to low)."""
    swing_high = 2.0000
    swing_low = 1.0000
    
    levels = calculate_retracements(swing_high, swing_low, trend="bearish")
    
    assert levels[0.0] == 1.0000  # 0% retraced = low
    assert levels[1.0] == 2.0000  # 100% retraced = high
    assert levels[0.5] == 1.5000  # 50%
    assert round(levels[0.618], 4) == 1.6180
    assert round(levels[0.786], 4) == 1.7860
