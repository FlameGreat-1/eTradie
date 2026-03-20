from datetime import datetime

from engine.ta.analyzers.smc import SMCDetector
from engine.ta.models.swing import SwingPoint
from tests.factories import make_candle, make_candle_sequence


def test_detect_bms_bullish():
    detector = SMCDetector()
    
    # We need a swing point that gets broken
    swing_high = SwingPoint(price=1.1000, timestamp=datetime.now(), type="high")
    
    # And a candle that breaks it strongly
    c1 = make_candle(datetime.now(), open=1.0950, close=1.1050, high=1.1060, low=1.0900)
    
    detector._detect_bms([c1], [swing_high])
    
    assert detector.context.bms is not None
    assert detector.context.bms.direction == "bullish"
    assert detector.context.bms.break_price == 1.1000


def test_detect_choch_bearish():
    detector = SMCDetector()
    detector.context.trend = "bullish"
    
    # Opposing break
    swing_low = SwingPoint(price=1.0800, timestamp=datetime.now(), type="low")
    c1 = make_candle(datetime.now(), open=1.0850, close=1.0700, high=1.0860, low=1.0690)
    
    detector._detect_choch([c1], [swing_low])
    
    assert detector.context.choch is not None
    assert detector.context.choch.direction == "bearish"
    assert detector.context.trend == "bearish"


def test_detect_order_block_bullish():
    detector = SMCDetector()
    
    # Down close candle followed by strong up close with FVG
    c1 = make_candle(datetime.now(), open=1.0500, close=1.0400, high=1.0550, low=1.0350)
    c2 = make_candle(datetime.now(), open=1.0400, close=1.0600, high=1.0650, low=1.0380)
    c3 = make_candle(datetime.now(), open=1.0600, close=1.0700, high=1.0720, low=1.0580)
    
    # Emulate a BMS having occurred to validate the OB
    detector.context.bms = lambda: None
    detector.context.bms.direction = "bullish"
    detector.context.bms.break_candle = c2
    detector.context.bms.timestamp = c2.timestamp
    
    detector._detect_order_blocks([c1, c2, c3])
    
    obs = [ob for ob in detector.context.order_blocks if ob.type == "bullish"]
    assert len(obs) > 0
    # OB should encapsulate c1's high/low
    assert obs[-1].zone.high >= c1.high
    assert obs[-1].zone.low <= c1.low


def test_detect_fair_value_gap():
    detector = SMCDetector()
    
    # 3 candle sequence with a gap between c1 high and c3 low
    c1 = make_candle(datetime.now(), open=1.0, close=1.1, high=1.15, low=0.95)
    c2 = make_candle(datetime.now(), open=1.1, close=1.3, high=1.35, low=1.05)
    c3 = make_candle(datetime.now(), open=1.3, close=1.4, high=1.45, low=1.25)
    
    detector._detect_fvgs([c1, c2, c3])
    
    fvgs = [fvg for fvg in detector.context.fvgs if fvg.type == "bullish"]
    assert len(fvgs) > 0
    # Gap is between 1.15 (c1 high) and 1.25 (c3 low)
    assert fvgs[-1].gap_low >= 1.15
    assert fvgs[-1].gap_high <= 1.25
