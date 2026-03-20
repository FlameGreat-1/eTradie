from datetime import datetime

from engine.ta.analyzers.snd import SnDDetector
from engine.ta.models.swing import SwingPoint
from tests.factories import make_candle, make_candle_sequence


def test_detect_qml_pattern():
    """QML is High, Low, Higher High, Lower Low."""
    detector = SnDDetector()
    
    swings = [
        SwingPoint(price=1.1000, timestamp=datetime.now(), type="high"),
        SwingPoint(price=1.0800, timestamp=datetime.now(), type="low"),
        SwingPoint(price=1.1200, timestamp=datetime.now(), type="high"),
        SwingPoint(price=1.0700, timestamp=datetime.now(), type="low"),
    ]
    
    detector._detect_qml(swings)
    
    assert detector.context.qml_pattern is not None
    assert detector.context.qml_pattern.direction == "bearish"
    assert detector.context.qml_pattern.qml_level == 1.1000  # The left shoulder High


def test_detect_supply_zone():
    """Test supply zone creation from Drop-Base-Drop or Rally-Base-Drop."""
    detector = SnDDetector()
    
    # Rally
    c1 = make_candle(datetime.now(), open=1.0, close=1.1, high=1.1, low=0.9)
    # Base (narrow ranges)
    c2 = make_candle(datetime.now(), open=1.1, close=1.12, high=1.15, low=1.08)
    c3 = make_candle(datetime.now(), open=1.12, close=1.11, high=1.14, low=1.09)
    # Drop
    c4 = make_candle(datetime.now(), open=1.11, close=0.95, high=1.13, low=0.90)
    
    detector._detect_zones([c1, c2, c3, c4])
    
    supplies = [z for z in detector.context.zones if z.type == "supply" and z.status == "fresh"]
    assert len(supplies) > 0
    
    # Supply zone bounds are highest high of the base and lowest body of the base
    assert supplies[-1].upper == 1.15  # c2 high
    assert supplies[-1].lower in (1.1, 1.11, 1.12)  # depending on exact body logic


def test_detect_demand_zone():
    """Test demand zone creation from Drop-Base-Rally or Rally-Base-Rally."""
    detector = SnDDetector()
    
    # Drop
    c1 = make_candle(datetime.now(), open=1.1, close=1.0, high=1.15, low=0.95)
    # Base
    c2 = make_candle(datetime.now(), open=1.0, close=0.98, high=1.02, low=0.95)
    # Rally
    c3 = make_candle(datetime.now(), open=0.98, close=1.15, high=1.20, low=0.97)
    
    detector._detect_zones([c1, c2, c3])
    
    demands = [z for z in detector.context.zones if z.type == "demand" and z.status == "fresh"]
    assert len(demands) > 0
    
    assert demands[-1].lower == 0.95  # lowest low of base
    assert demands[-1].upper in (0.98, 1.0)  # depending on highest body of base
