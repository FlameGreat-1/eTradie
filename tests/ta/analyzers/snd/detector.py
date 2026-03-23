"""Tests for SnDDetector (Supply and Demand detection).

Production module: src/engine/ta/snd/detector.py

The SnDDetector requires 6 injected analyzer dependencies. Full
detection tests require realistic candle sequences with QML/QMH
patterns. These tests verify the import chain and model structure.
Pattern detection tests are deferred to integration phase.
"""

from datetime import UTC, datetime

import pytest

from engine.ta.constants import Direction, Timeframe


class TestSnDDetectorImports:
    def test_detector_importable(self):
        from engine.ta.snd.detector import SnDDetector
        assert SnDDetector is not None

    def test_snd_config_importable(self):
        from engine.ta.snd.config import SnDConfig
        cfg = SnDConfig()
        assert cfg.enabled is True


class TestSupplyDemandZoneModels:
    def test_supply_zone(self):
        from engine.ta.models.zone import SupplyZone

        sz = SupplyZone(
            symbol="EURUSD",
            timeframe=Timeframe.H4,
            upper_bound=1.1200,
            lower_bound=1.1150,
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            qml_level=1.1200,
            qml_timestamp=datetime(2024, 5, 28, tzinfo=UTC),
            sr_flip_level=1.1150,
            sr_flip_timestamp=datetime(2024, 5, 30, tzinfo=UTC),
        )
        assert sz.range_size == pytest.approx(0.0050)
        assert sz.midpoint == pytest.approx(1.1175)
        assert sz.is_valid is True

    def test_demand_zone(self):
        from engine.ta.models.zone import DemandZone

        dz = DemandZone(
            symbol="EURUSD",
            timeframe=Timeframe.H4,
            upper_bound=1.0900,
            lower_bound=1.0850,
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            qmh_level=1.0850,
            qmh_timestamp=datetime(2024, 5, 28, tzinfo=UTC),
            rs_flip_level=1.0900,
            rs_flip_timestamp=datetime(2024, 5, 30, tzinfo=UTC),
        )
        assert dz.range_size == pytest.approx(0.0050)
        assert dz.is_valid is True


class TestQMLModels:
    def test_quasi_modo_level_bearish(self):
        from engine.ta.models.zone import QuasiModoLevel

        qml = QuasiModoLevel(
            symbol="EURUSD",
            timeframe=Timeframe.H4,
            qml_price=1.1000,
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            candle_index=20,
            direction=Direction.BEARISH,
            h_price=1.1000,
            hh_price=1.1200,
            h_timestamp=datetime(2024, 5, 25, tzinfo=UTC),
            hh_timestamp=datetime(2024, 5, 28, tzinfo=UTC),
            hh_index=18,
            break_timestamp=datetime(2024, 6, 1, tzinfo=UTC),
        )
        assert qml.is_qml is True
        assert qml.is_qmh is False
        assert qml.level == 1.1000

    def test_mini_price_level(self):
        from engine.ta.models.zone import MiniPriceLevel

        mpl = MiniPriceLevel(
            symbol="EURUSD",
            timeframe=Timeframe.M15,
            level=1.0950,
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            candle_index=5,
            direction=Direction.BEARISH,
            has_internal_structure=True,
            is_type1=True,
        )
        assert mpl.mpl_price == 1.0950
        assert mpl.is_bearish is True
        assert mpl.is_type1 is True


class TestSRFlipModels:
    def test_sr_flip(self):
        from engine.ta.models.structure_event import SRFlip

        flip = SRFlip(
            symbol="EURUSD",
            timeframe=Timeframe.H4,
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            original_support_level=1.1000,
            original_support_timestamp=datetime(2024, 5, 20, tzinfo=UTC),
            breakout_candle_index=25,
            breakout_price=1.0980,
            new_resistance_level=1.1000,
        )
        assert flip.previous_role == "SUPPORT"
        assert flip.new_role == "RESISTANCE"
        assert flip.flip_level == 1.1000

    def test_rs_flip(self):
        from engine.ta.models.structure_event import RSFlip

        flip = RSFlip(
            symbol="EURUSD",
            timeframe=Timeframe.H4,
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            original_resistance_level=1.1200,
            original_resistance_timestamp=datetime(2024, 5, 20, tzinfo=UTC),
            breakout_candle_index=30,
            breakout_price=1.1220,
            new_support_level=1.1200,
        )
        assert flip.previous_role == "RESISTANCE"
        assert flip.new_role == "SUPPORT"
        assert flip.flip_level == 1.1200
