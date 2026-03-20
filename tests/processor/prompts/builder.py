import json

from engine.processor.models.io import ProcessorInput
from engine.processor.prompts.system_prompt import (
    build_system_prompt,
    build_user_message,
    compute_prompt_hash,
)
from engine.ta.constants import Timeframe
from engine.ta.models.candidate import SMCCandidate


def test_build_system_prompt():
    """System prompt contains constraints and JSON schema."""
    prompt = build_system_prompt()
    
    assert "You are the Analysis Processor" in prompt
    assert "HALLUCINATION PREVENTION" in prompt
    assert "analysis_id" in prompt  # Part of schema


def test_build_user_message():
    """User message accurately serializes ProcessorInput payload."""
    input_data = ProcessorInput(
        symbol="EURUSD",
        ta_analysis={"trend": "BULLISH"},
        macro_analysis={"bias": "BULLISH"},
        retrieved_knowledge={"chunks": []},
        metadata={"trace_id": "test"}
    )
    
    msg = build_user_message(input_data)
    parsed = json.loads(msg)
    
    assert parsed["symbol"] == "EURUSD"
    assert parsed["ta_analysis"]["trend"] == "BULLISH"
    assert parsed["metadata"]["trace_id"] == "test"


def test_compute_prompt_hash():
    """Hash is deterministic and short."""
    sys = "test system"
    usr = "test user"
    
    hash1 = compute_prompt_hash(sys, usr)
    hash2 = compute_prompt_hash(sys, usr)
    
    assert hash1 == hash2
    assert len(hash1) == 32
    
    hash3 = compute_prompt_hash("test system2", usr)
    assert hash1 != hash3
