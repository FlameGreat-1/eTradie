"""Tests for system prompt and user message construction.

Production module: src/engine/processor/prompts/system_prompt.py
"""

import json

from engine.processor.models.io import ProcessorInput
from engine.processor.prompts.system_prompt import (
    build_system_prompt,
    build_user_message,
    compute_prompt_hash,
)


class TestBuildSystemPrompt:
    def test_contains_role_definition(self):
        prompt = build_system_prompt()
        assert "You are the Analysis Processor" in prompt

    def test_contains_hallucination_prevention(self):
        prompt = build_system_prompt()
        assert "HALLUCINATION PREVENTION" in prompt

    def test_contains_output_schema(self):
        prompt = build_system_prompt()
        assert "analysis_id" in prompt
        assert "confluence_score" in prompt
        assert "proceed_to_module_b" in prompt

    def test_contains_grade_rules(self):
        prompt = build_system_prompt()
        assert "setup_grade" in prompt
        assert "REJECT" in prompt


class TestBuildUserMessage:
    def test_serializes_processor_input(self):
        # `retrieved_knowledge` is projected only via the
        # `retrieved_chunks` key -- any other top-level key is
        # dropped by the RAG projection. `metadata.trace_id` is
        # stripped by _METADATA_STRIP_KEYS because the LLM cannot
        # act on a distributed-tracing correlation id.
        inp = ProcessorInput(
            symbol="EURUSD",
            ta_analysis={"trend": "BULLISH"},
            macro_analysis={"bias": "BULLISH"},
            retrieved_knowledge={"retrieved_chunks": []},
            metadata={"trace_id": "test-trace", "overall_trend": "BULLISH"},
        )
        msg = build_user_message(inp)
        parsed = json.loads(msg)

        assert parsed["symbol"] == "EURUSD"
        assert parsed["ta_analysis"]["trend"] == "BULLISH"
        assert parsed["macro_analysis"]["bias"] == "BULLISH"
        # Empty `retrieved_chunks` projects to an empty list under the
        # same key in the output payload.
        assert parsed["retrieved_knowledge"] == {"retrieved_chunks": []}
        # trace_id is stripped; surviving metadata keys remain.
        assert "trace_id" not in parsed["metadata"]
        assert parsed["metadata"]["overall_trend"] == "BULLISH"
        # The analysis payload must never carry a user_operating_system
        # block -- that block was removed in this MR.
        assert "user_operating_system" not in parsed

    def test_empty_context(self):
        inp = ProcessorInput(symbol="GBPUSD")
        msg = build_user_message(inp)
        parsed = json.loads(msg)

        assert parsed["symbol"] == "GBPUSD"
        assert parsed["ta_analysis"] == {}
        assert parsed["macro_analysis"] == {}
        assert parsed["retrieved_knowledge"] == {}
        assert parsed["metadata"] == {}


class TestComputePromptHash:
    def test_deterministic(self):
        h1 = compute_prompt_hash("sys", "usr")
        h2 = compute_prompt_hash("sys", "usr")
        assert h1 == h2

    def test_length_32(self):
        h = compute_prompt_hash("system", "user")
        assert len(h) == 32

    def test_different_inputs_different_hash(self):
        h1 = compute_prompt_hash("sys1", "usr")
        h2 = compute_prompt_hash("sys2", "usr")
        assert h1 != h2

    def test_hex_characters_only(self):
        h = compute_prompt_hash("test", "test")
        assert all(c in "0123456789abcdef" for c in h)
