from engine.processor.constants import LLMProvider
from engine.processor.mapping.output_mapper import map_to_processor_output
from engine.processor.models.analysis import AnalysisOutput


def create_test_analysis_output(overrides=None):
    """Factory helper to quickly build an AnalysisOutput for mapping tests."""
    data = {
        "analysis_id": "test-123",
        "pair": "EURUSD",
        "timestamp": "2025-01-01T12:00:00Z",
        "trading_style": "INTRADAY",
        "session": "NEW_YORK",
        
        "macro_bias": {
            "base_currency": {"bias": "BULLISH", "evidence": []},
            "quote_currency": {"bias": "BEARISH", "evidence": []}
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
            {"level": 1.1200, "size_pct": 50, "basis": "R2"}
        ],
        "rr_ratio": 2.0,
        
        "confidence": "HIGH",
        "proceed_to_module_b": "YES",
        "execution_mode": "LIMIT",
        "ltf_confirmed": True,
        "explainable_reasoning": "Looks good.",
        
        "rag_sources": [],
        "audit": {"retrieval": {"query_summary": "", "top_k": 0}, "citations": []}
    }
    
    if overrides:
        data.update(overrides)
        
    return AnalysisOutput.model_validate(data)


def test_map_valid_long_setup():
    """Test mapping a fully valid A-grade LONG setup."""
    analysis = create_test_analysis_output()
    raw = {"_llm_model": "test-model"}
    
    output = map_to_processor_output(analysis, raw_response=raw)
    
    assert output.trade_valid is True
    assert output.direction == "LONG"
    assert output.symbol == "EURUSD"
    assert output.confidence == 0.85  # HIGH -> 0.85
    assert output.grade == "A"
    assert output.risk_percentage == 1.0  # A grade -> 1%
    assert output.entry_price == 1.1005  # Average of 1.1000 and 1.1010
    
    assert output.tp1_price == 1.1100
    assert output.tp1_pct == 50
    assert output.tp2_price == 1.1200
    assert output.tp2_pct == 50
    assert output.tp3_price is None
    assert output.tp3_pct == 0
    
    assert output.take_profit == 1.1200  # Legacy field gets the last TP
    assert output.raw_response == raw


def test_map_no_setup():
    """Test mapping a NO SETUP decision."""
    analysis = create_test_analysis_output({
        "direction": "NO SETUP",
        "proceed_to_module_b": "NO",
        "setup_grade": "REJECT",
        "confidence": "NO SETUP",
        "entry_zone": {"low": None, "high": None},
        "stop_loss": {"price": None, "reason": "", "evidence": []},
        "take_profits": [],
        "rr_ratio": None,
        "execution_mode": None,
        "confluence_score": {"score": 0.0, "factors": [
            {"name": "htf_alignment", "present": False, "value": 0.0, "notes": "opposed"}
        ]}
    })
    
    output = map_to_processor_output(analysis)
    
    assert output.trade_valid is False
    assert output.direction is None
    assert output.risk_percentage is None
    assert output.entry_price is None
    assert output.tp1_price is None
    assert "missing_htf_alignment" in output.rejection_rules


def test_map_reject_grade_despite_direction():
    """Test mapping a trade that looked good but graded REJECT or YES but invalid direction."""
    analysis = create_test_analysis_output({
        "direction": "LONG",
        "proceed_to_module_b": "YES",
        "setup_grade": "REJECT",  # Invalid combo
    })
    
    output = map_to_processor_output(analysis)
    
    # Trade valid must be strictly LONG/SHORT + A+/A/B + YES
    assert output.trade_valid is False
    assert output.risk_percentage is None


def test_map_confidence_conversion():
    """Test mapping discrete confidence strings to floats for gateway."""
    high = create_test_analysis_output({"confidence": "HIGH"})
    medium = create_test_analysis_output({"confidence": "MEDIUM"})
    low = create_test_analysis_output({"confidence": "LOW"})
    no_setup = create_test_analysis_output({"confidence": "NO SETUP"})
    other = create_test_analysis_output({"confidence": "UNCERTAIN"})
    
    assert map_to_processor_output(high).confidence == 0.85
    assert map_to_processor_output(medium).confidence == 0.60
    assert map_to_processor_output(low).confidence == 0.35
    assert map_to_processor_output(no_setup).confidence == 0.0
    assert map_to_processor_output(other).confidence == 0.0


def test_map_risk_conversion():
    """Test mapping grades to risk percentages strictly."""
    a_plus = create_test_analysis_output({"setup_grade": "A+"})
    a = create_test_analysis_output({"setup_grade": "A"})
    b = create_test_analysis_output({"setup_grade": "B"})
    
    assert map_to_processor_output(a_plus).risk_percentage == 1.0
    assert map_to_processor_output(a).risk_percentage == 1.0
    assert map_to_processor_output(b).risk_percentage == 0.5
