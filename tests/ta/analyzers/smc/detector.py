"""Tests for SMCDetector (Smart Money Concepts detection).

Production module: src/engine/ta/smc/detector.py

The SMCDetector requires 8 injected analyzer dependencies. Full
detection tests require realistic candle sequences with specific
structural patterns. These tests verify the import chain and model
structure. Pattern detection tests are deferred to integration phase.
"""

import pytest

from engine.ta.constants import Direction, Timeframe


class TestSMCDetectorImports:
    def test_detector_importable(self):
        from engine.ta.smc.detector import SMCDetector

        assert SMCDetector is not None

    def test_smc_config_importable(self):
        from engine.ta.smc.config import SMCConfig

        cfg = SMCConfig()
        assert cfg.enabled is True


class TestStructureEventModels:
    def test_break_of_structure(self):
        from engine.ta.models.structure_event import BreakOfStructure

        assert BreakOfStructure is not None

    def test_change_of_character(self):
        from engine.ta.models.structure_event import ChangeOfCharacter

        assert ChangeOfCharacter is not None

    def test_break_in_market_structure(self):
        from engine.ta.models.structure_event import BreakInMarketStructure

        assert BreakInMarketStructure is not None

    def test_shift_in_market_structure(self):
        from engine.ta.models.structure_event import ShiftInMarketStructure

        assert ShiftInMarketStructure is not None


class TestZoneModels:
    def test_order_block(self):
        from datetime import UTC, datetime

        from engine.ta.models.zone import OrderBlock

        ob = OrderBlock(
            symbol="EURUSD",
            timeframe=Timeframe.H4,
            upper_bound=1.1050,
            lower_bound=1.1000,
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            candle_index=10,
            direction=Direction.BULLISH,
            displacement_pips=25.0,
        )
        assert ob.is_bullish is True
        assert ob.range_size == pytest.approx(0.0050)
        assert ob.midpoint == pytest.approx(1.1025)

    def test_fair_value_gap(self):
        from datetime import UTC, datetime

        from engine.ta.models.zone import FairValueGap

        fvg = FairValueGap(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            upper_bound=1.1100,
            lower_bound=1.1050,
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            candle_index=15,
            direction=Direction.BULLISH,
        )
        assert fvg.is_bullish is True
        assert fvg.filled is False
        assert fvg.range_size == pytest.approx(0.0050)
