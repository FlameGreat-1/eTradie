"""Trading Plan generation subsystem.

Generates the Personalized 90-Day Trading Development Plan described
in PRACTICE.md. The engine never *consumes* the plan; this module
exists only to fulfil the gateway's dispatch request, produce the
six-section workbook with the platform LLM key, and POST it back to
the gateway via /internal/trading-plan/callback.

Authority separation (must remain true):

  - Trading System (engine.processor.user_os)  : governs AI execution.
  - Trading Plan   (this package)              : governs HUMAN discipline.

The plan is for the user's eyes only. The analysis processor never
reads it; the broker layer never reads it; the RAG layer never reads
it. It is downloadable, exportable to Excel, and the user fills the
journal manually.
"""

from engine.processor.trading_plan.generator import (  # noqa: F401
    TradingPlanGenerator,
    GenerationRequest,
)
from engine.processor.trading_plan.prompt import (  # noqa: F401
    SYSTEM_PROMPT,
    build_user_prompt,
)

__all__ = [
    "TradingPlanGenerator",
    "GenerationRequest",
    "SYSTEM_PROMPT",
    "build_user_prompt",
]
