"""Tests for map_to_processor_output (AnalysisOutput -> ProcessorOutput).

Production module: src/engine/processor/mapping/output_mapper.py
"""

from engine.processor.mapping.output_mapper import map_to_processor_output
from engine.processor.models.analysis import AnalysisOutput


def _make_analysis(overrides=None):
    """Build a valid AnalysisOutput for mapping tests."""
    data = {
        "analysis_id": "test-123",
        "pair": "EURUSD",
        "timestamp": "2025-01-01T12:00:00Z",
        "trading_style": "INTRADAY",
        "session": "NEW_YORK",
        "macro_bias": {
            "base_currency": {"bias": "BULLISH", "evidence": []},
            "quote_currency": {"bias": "BEARISH", "evidence": []},
        },
        "dxy_bias": {"direction": "BEARISH", "evidence": []},
        "cot_signal": {"summary": "increasing", "extreme_flag": False, "evidence": []},
        "event_risk": [],
        "htf_bias": {"structure": "bullish", "key_levels": []},
        "mtf_bias": {"structure": "bullish", "key_levels": []},
        "entry_setup": {"type": "OB", "bounds": [1.0, 1.1], "evidence": []},
        "wyckoff_phase": {"phase": "markup", "evidence": []},
        "confluence_score": {"score": 8.0, "factors": []},
        "setup_grade": "A",
        "direction": "LONG",
        "entry_zone": {"low": 1.1000, "high": 1.1010},
        "stop_loss": {"price": 1.0950, "reason": "OB", "evidence": []},
        "take_profits": [
            {"level": 1.1100, "size_pct": 50, "basis": "R1"},
            {"level": 1.1200, "size_pct": 50, "basis": "R2"},
        ],
        "rr_ratio": 3.0,
        "confidence": "HIGH",
        "proceed_to_module_b": "YES",
        "execution_mode": "LIMIT",
        "ltf_confirmed": True,
        "explainable_reasoning": "Looks good.",
        "rag_sources": [],
        "audit": {"retrieval": {"query_summary": "", "top_k": 0}, "citations": []},
    }
    if overrides:
        data.update(overrides)
    return AnalysisOutput.model_validate(data)


class TestMapValidLongSetup:
    def test_trade_valid(self):
        output = map_to_processor_output(_make_analysis())
        assert output.trade_valid is True
        assert output.direction == "LONG"
        assert output.symbol == "EURUSD"

    def test_confidence_mapping(self):
        assert map_to_processor_output(_make_analysis({"confidence": "HIGH"})).confidence == 0.85
        assert map_to_processor_output(_make_analysis({"confidence": "MEDIUM"})).confidence == 0.60
        assert map_to_processor_output(_make_analysis({"confidence": "LOW"})).confidence == 0.35
        assert map_to_processor_output(_make_analysis({"confidence": "NO SETUP"})).confidence == 0.0

    def test_risk_mapping(self):
        assert map_to_processor_output(_make_analysis({"setup_grade": "A+"})).risk_percentage == 1.0
        assert map_to_processor_output(_make_analysis({"setup_grade": "A"})).risk_percentage == 1.0
        assert map_to_processor_output(_make_analysis({"setup_grade": "B"})).risk_percentage == 0.5

    def test_entry_midpoint(self):
        output = map_to_processor_output(_make_analysis())
        assert output.entry_price == 1.1005  # (1.1000 + 1.1010) / 2

    def test_tp_extraction(self):
        output = map_to_processor_output(_make_analysis())
        assert output.tp1_price == 1.1100
        assert output.tp1_pct == 50
        assert output.tp2_price == 1.1200
        assert output.tp2_pct == 50
        assert output.tp3_price is None
        assert output.tp3_pct == 0

    def test_legacy_take_profit(self):
        output = map_to_processor_output(_make_analysis())
        assert output.take_profit == 1.1200  # Last TP level

    def test_execution_fields(self):
        output = map_to_processor_output(_make_analysis())
        assert output.execution_mode == "LIMIT"
        assert output.ltf_confirmed is True
        assert output.trading_style == "INTRADAY"
        assert output.session == "NEW_YORK"
        assert output.rr_ratio == 3.0
        assert output.confluence_score == 8.0
        assert output.analysis_id == "test-123"


class TestMapNoSetup:
    def test_no_setup_invalid(self):
        output = map_to_processor_output(_make_analysis({
            "direction": "NO SETUP",
            "proceed_to_module_b": "NO",
            "setup_grade": "REJECT",
            "confidence": "NO SETUP",
            "entry_zone": {"low": None, "high": None},
            "stop_loss": {"price": None, "reason": "", "evidence": []},
            "take_profits": [],
            "rr_ratio": None,
            "execution_mode": None,
            "confluence_score": {"score": 0.0, "factors": []},
        }))
        assert output.trade_valid is False
        assert output.direction is None
        assert output.risk_percentage is None
        assert output.entry_price is None


class TestMapRejectGrade:
    def test_reject_grade_overrides_direction(self):
        output = map_to_processor_output(_make_analysis({
            "direction": "LONG",
            "proceed_to_module_b": "YES",
            "setup_grade": "REJECT",
        }))
        assert output.trade_valid is False
        assert output.risk_percentage is None
