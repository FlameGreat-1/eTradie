"""Processor LLM service.

Concrete implementation of the gateway's ProcessorPort interface.
Receives assembled TA + Macro + RAG context from the gateway,
sends it to Claude API for reasoning, parses the structured
response, and returns a ProcessorOutput for guard evaluation
and execution routing.
"""
