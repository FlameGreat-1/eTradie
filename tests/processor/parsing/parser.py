import json

import pytest

from engine.processor.models.analysis import AnalysisOutput
from engine.processor.parsing.response_parser import parse_llm_response
from engine.shared.exceptions import ProcessorError


@pytest.fixture
def valid_llm_json():
    return json.dumps({
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
        "cot_signal": {"summary": "Longs increasing", "extreme_flag": False, "evidence": []},
        "event_risk": [],
        
        "htf_bias": {"structure": "bullish", "key_levels": []},
        "mtf_bias": {"structure": "bullish", "key_levels": []},
        "entry_setup": {"type": "OB", "bounds": [1.0, 1.1], "evidence": []},
        "wyckoff_phase": {"phase": "markup", "evidence": []},
        
        "confluence_score": {"score": 8.0, "factors": []},
        "setup_grade": "A",
        "direction": "LONG",
        
        "entry_zone": {"low": 1.1000, "high": 1.1010},
        "stop_loss": {"price": 1.0950, "reason": "Below OB", "evidence": []},
        "take_profits": [
            {"level": 1.1100, "size_pct": 50, "basis": "HTF resistance"},
            {"level": 1.1200, "size_pct": 50, "basis": "Liquidity pool"}
        ],
        "rr_ratio": 2.0,
        
        "confidence": "HIGH",
        "proceed_to_module_b": "YES",
        "execution_mode": "LIMIT",
        "ltf_confirmed": True,
        "explainable_reasoning": "Strong bullish structure with macro alignment.",
        
        "rag_sources": [{"doc_id": "d1", "chunk_id": "c1", "relevance_score": 0.9}],
        "audit": {
            "retrieval": {"query_summary": "test", "top_k": 5},
            "citations": []
        }
    })


def test_parse_valid_json_direct(valid_llm_json):
    """Test parsing a clean JSON string directly."""
    output, warnings = parse_llm_response(valid_llm_json)
    
    assert isinstance(output, AnalysisOutput)
    assert output.direction == "LONG"
    assert output.setup_grade == "A"
    assert output.take_profits[0].level == 1.1100
    assert len(warnings) == 0


def test_parse_json_markdown_blocks(valid_llm_json):
    """Test extracting JSON from markdown code blocks (```json ... ```)."""
    raw_text = f"Here is my analysis:\n```json\n{valid_llm_json}\n```\nGood luck!"
    output, warnings = parse_llm_response(raw_text)
    
    assert output.direction == "LONG"


def test_parse_json_noisy_text(valid_llm_json):
    """Test extracting JSON when surrounded by unstructured text without markdown."""
    raw_text = f"Analysis follows:\n{valid_llm_json}\nThat concludes the report."
    output, warnings = parse_llm_response(raw_text)
    
    assert output.direction == "LONG"


def test_parse_empty_string():
    """Test that empty strings raise a ProcessorError."""
    with pytest.raises(ProcessorError, match="empty response"):
        parse_llm_response("   \n   ")


def test_parse_invalid_json():
    """Test that malformed JSON raises a ProcessorError."""
    with pytest.raises(ProcessorError, match="Failed to parse LLM JSON"):
        parse_llm_response('{"broken": "json')


def test_schema_validation_failure():
    """Test that missing required fields raise a ProcessorError with schema details."""
    missing_fields_json = '{"direction": "LONG"}'  # Missing essentially everything else
    with pytest.raises(ProcessorError, match="schema validation"):
        parse_llm_response(missing_fields_json)


def test_business_logic_validation_fatal(valid_llm_json):
    """Test that business logic failures (like negative SL) raise a ProcessorError."""
    data = json.loads(valid_llm_json)
    data["stop_loss"]["price"] = -1.5  # Invalid price
    
    with pytest.raises(ProcessorError, match="failed validation.*stop_loss"):
        parse_llm_response(json.dumps(data))


def test_business_logic_validation_warning(valid_llm_json):
    """Test that non-fatal issues (like missing citations) just return warnings."""
    data = json.loads(valid_llm_json)
    data["rag_sources"] = []  # Empty citations is a warning
    
    output, warnings = parse_llm_response(json.dumps(data))
    
    assert output.direction == "LONG"
    assert len(warnings) > 0
    assert "rag_sources" in warnings[0].lower()
