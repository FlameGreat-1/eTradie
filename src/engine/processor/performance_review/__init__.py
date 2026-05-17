"""Engine-side Performance Review module.

Public API:
    GenerationRequest      - typed input to the generator
    PerformanceReviewGenerator
                           - wraps a single LLM call + gateway callback
    PerformanceReviewGenerationError
                           - user-safe error class raised on parse / shape failures

The generator is fully self-contained: it does not own its HTTP client
or LLM client, so unit tests can swap both with fakes. The Container
builds ONE instance per process and reuses it across users (mirrors
the trading_plan module exactly).
"""
from engine.processor.performance_review.generator import (
    GenerationRequest,
    PerformanceReviewGenerationError,
    PerformanceReviewGenerator,
)

__all__ = [
    "GenerationRequest",
    "PerformanceReviewGenerationError",
    "PerformanceReviewGenerator",
]
