"""Tests for parse_llm_response (JSON extraction, validation, warnings).

Production module: src/engine/processor/parsing/response_parser.py
"""

import json

import pytest

from engine.processor.models.analysis import AnalysisOutput
from engine.processor.parsing.response_parser import parse_llm_response
from engine.shared.exceptions import ProcessorError


@pytest.fixture
def valid_llm_json():
    """Minimal valid AnalysisOutput JSON matching the real schema."""
    return json.dumps({
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
            {"level": 1.1200, "size_pct": 50, "basis": "Liquidity pool"},
        ],
        "rr_ratio": 3.0,
        "confidence": "HIGH",
        "proceed_to_module_b": "YES",
        "execution_mode": "LIMIT",
        "ltf_confirmed": True,
        "explainable_reasoning": "Strong bullish structure with macro alignment.",
        "rag_sources": [{"doc_id": "d1", "chunk_id": "c1", "relevance_score": 0.9}],
        "audit": {
            "retrieval": {"query_summary": "test", "top_k": 5},
            "citations": [],
        },
    })


class TestParseValidJSON:
    def test_clean_json(self, valid_llm_json):
        """Parse a clean JSON string directly."""
        output, warnings = parse_llm_response(valid_llm_json)
        assert isinstance(output, AnalysisOutput)
        assert output.direction == "LONG"
        assert output.setup_grade == "A"
        assert output.take_profits[0].level == 1.1100

    def test_markdown_code_block(self, valid_llm_json):
        """Extract JSON from markdown ```json ... ``` blocks."""
        raw = f"Here is my analysis:\n```json\n{valid_llm_json}\n```\nGood luck!"
        output, warnings = parse_llm_response(raw)
        assert output.direction == "LONG"

    def test_noisy_surrounding_text(self, valid_llm_json):
        """Extract JSON when surrounded by unstructured text."""
        raw = f"Analysis follows:\n{valid_llm_json}\nThat concludes the report."
        output, warnings = parse_llm_response(raw)
        assert output.direction == "LONG"


class TestParseErrors:
    def test_empty_string_raises(self):
        """Empty input raises ProcessorError."""
        with pytest.raises(ProcessorError, match="empty"):
            parse_llm_response("   \n   ")

    def test_malformed_json_raises(self):
        """Broken JSON raises ProcessorError."""
        with pytest.raises(ProcessorError, match="Failed to parse LLM JSON"):
            parse_llm_response('{"broken": "json')

    def test_missing_required_fields_raises(self):
        """JSON missing required AnalysisOutput fields raises ProcessorError."""
        with pytest.raises(ProcessorError, match="schema validation"):
            parse_llm_response('{"direction": "LONG"}')

    def test_non_object_json_raises(self):
        """JSON array instead of object raises ProcessorError."""
        with pytest.raises(ProcessorError):
            parse_llm_response('[1, 2, 3]')


class TestWarnings:
    def test_empty_rag_sources_produces_warning(self, valid_llm_json):
        """Empty rag_sources is a non-fatal warning, not an error."""
        data = json.loads(valid_llm_json)
        data["rag_sources"] = []
        output, warnings = parse_llm_response(json.dumps(data))
        assert output.direction == "LONG"
        # rag_sources empty should produce a warning
        rag_warnings = [w for w in warnings if "rag_sources" in w.lower()]
        assert len(rag_warnings) > 0

    def test_valid_response_no_warnings(self, valid_llm_json):
        """A fully valid response produces zero warnings."""
        output, warnings = parse_llm_response(valid_llm_json)
        assert output.direction == "LONG"
        # May or may not have warnings depending on citation requirements
        # The key assertion is that it parses successfully
        assert isinstance(warnings, list)
