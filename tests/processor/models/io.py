import pytest
from pydantic import ValidationError

from engine.processor.constants import LLMProvider
from engine.processor.models.io import ProcessorInput, ProcessorOutput


def test_processor_input_frozen():
    """ProcessorInput must be frozen."""
    input_data = ProcessorInput(
        symbol="EURUSD",
        ta_analysis={},
        macro_analysis={},
        retrieved_knowledge={},
    )
    with pytest.raises(ValidationError):
        input_data.symbol = "GBPUSD"


def test_processor_output_defaults():
    """ProcessorOutput fills in reasonable defaults for missing optional fields."""
    output = ProcessorOutput(
        trade_valid=False,
        symbol="EURUSD",
        confidence=0.5,
        grade="REJECT",
        reasoning="Testing defaults",
        analysis_id="test-123",
        raw_response={},
    )
    
    assert output.direction is None
    assert output.risk_percentage is None
    assert output.entry_price is None
    assert output.execution_mode is None
    assert output.rejection_rules == []
    assert output.tp1_price is None
    assert output.tp1_pct == 0
    assert output.confluence_score == 0.0


def test_processor_output_validation():
    """ProcessorOutput enforces boundaries on scores and percentages."""
    with pytest.raises(ValidationError):
        # Confidence must be between 0 and 1
        ProcessorOutput(
            trade_valid=False, symbol="EURUSD", confidence=1.5, grade="REJECT",
            reasoning="Test", analysis_id="t-1", raw_response={}
        )
        
    with pytest.raises(ValidationError):
        # Risk percentage must be between 0 and 5
        ProcessorOutput(
            trade_valid=False, symbol="EURUSD", confidence=0.5, grade="REJECT",
            risk_percentage=6.0, reasoning="Test", analysis_id="t-1", raw_response={}
        )

    with pytest.raises(ValidationError):
        # Confluence score must be between 0 and 10
        ProcessorOutput(
            trade_valid=False, symbol="EURUSD", confidence=0.5, grade="REJECT",
            confluence_score=11.0, reasoning="Test", analysis_id="t-1", raw_response={}
        )


def test_processor_output_trade_valid_consistency():
    """Test standard valid trade initialization."""
    output = ProcessorOutput(
        trade_valid=True,
        direction="LONG",
        symbol="EURUSD",
        confidence=0.85,
        grade="A",
        risk_percentage=1.0,
        reasoning="Valid setup",
        entry_price=1.1000,
        stop_loss=1.0950,
        execution_mode="LIMIT",
        tp1_price=1.1100,
        tp1_pct=100,
        trading_style="INTRADAY",
        session="NEW_YORK",
        rr_ratio=2.0,
        confluence_score=8.5,
        analysis_id="t-1",
        raw_response={},
    )
    assert output.trade_valid is True
    assert output.direction == "LONG"
    assert output.risk_percentage == 1.0
