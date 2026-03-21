"""Tests for ProcessorInput and ProcessorOutput models.

Production module: src/engine/processor/models/io.py
"""

import pytest
from pydantic import ValidationError

from engine.processor.models.io import ProcessorInput, ProcessorOutput


class TestProcessorInput:
    def test_frozen_immutability(self):
        """ProcessorInput must be frozen (immutable after creation)."""
        inp = ProcessorInput(
            symbol="EURUSD",
            ta_analysis={},
            macro_analysis={},
            retrieved_knowledge={},
        )
        with pytest.raises(ValidationError):
            inp.symbol = "GBPUSD"

    def test_default_empty_dicts(self):
        """Optional dict fields default to empty dicts."""
        inp = ProcessorInput(symbol="EURUSD")
        assert inp.ta_analysis == {}
        assert inp.macro_analysis == {}
        assert inp.retrieved_knowledge == {}
        assert inp.metadata == {}


class TestProcessorOutputDefaults:
    def test_all_defaults(self):
        """ProcessorOutput fills reasonable defaults for optional fields."""
        out = ProcessorOutput(
            trade_valid=False,
            symbol="EURUSD",
            confidence=0.5,
            grade="REJECT",
            reasoning="Testing defaults",
            analysis_id="test-123",
            raw_response={},
        )
        assert out.direction is None
        assert out.risk_percentage is None
        assert out.entry_price is None
        assert out.stop_loss is None
        assert out.take_profit is None
        assert out.execution_mode is None
        assert out.ltf_confirmed is False
        assert out.rejection_rules == []
        assert out.tp1_price is None
        assert out.tp1_pct == 0
        assert out.tp2_price is None
        assert out.tp2_pct == 0
        assert out.tp3_price is None
        assert out.tp3_pct == 0
        assert out.entry_zone_low is None
        assert out.entry_zone_high is None
        assert out.confluence_score == 0.0
        assert out.trading_style is None
        assert out.session is None
        assert out.rr_ratio is None


class TestProcessorOutputValidation:
    def test_confidence_above_1_rejected(self):
        with pytest.raises(ValidationError):
            ProcessorOutput(
                trade_valid=False, symbol="EURUSD", confidence=1.5,
                grade="REJECT", reasoning="Test", analysis_id="t-1",
                raw_response={},
            )

    def test_confidence_below_0_rejected(self):
        with pytest.raises(ValidationError):
            ProcessorOutput(
                trade_valid=False, symbol="EURUSD", confidence=-0.1,
                grade="REJECT", reasoning="Test", analysis_id="t-1",
                raw_response={},
            )

    def test_risk_percentage_above_5_rejected(self):
        with pytest.raises(ValidationError):
            ProcessorOutput(
                trade_valid=False, symbol="EURUSD", confidence=0.5,
                grade="REJECT", risk_percentage=6.0, reasoning="Test",
                analysis_id="t-1", raw_response={},
            )


class TestProcessorOutputValidTrade:
    def test_full_valid_trade(self):
        """A complete valid trade with all Module B fields."""
        out = ProcessorOutput(
            trade_valid=True,
            direction="LONG",
            symbol="EURUSD",
            confidence=0.85,
            grade="A",
            risk_percentage=1.0,
            reasoning="Valid setup",
            entry_price=1.1005,
            entry_zone_low=1.1000,
            entry_zone_high=1.1010,
            stop_loss=1.0950,
            take_profit=1.1200,
            execution_mode="LIMIT",
            ltf_confirmed=False,
            tp1_price=1.1100,
            tp1_pct=40,
            tp2_price=1.1150,
            tp2_pct=30,
            tp3_price=1.1200,
            tp3_pct=30,
            trading_style="INTRADAY",
            session="NEW_YORK",
            rr_ratio=3.0,
            confluence_score=8.5,
            analysis_id="t-1",
            raw_response={},
        )
        assert out.trade_valid is True
        assert out.direction == "LONG"
        assert out.risk_percentage == 1.0
        assert out.tp1_pct == 40
        assert out.tp2_pct == 30
        assert out.tp3_pct == 30
        assert out.execution_mode == "LIMIT"
