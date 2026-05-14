"""User Operating System (Layer 2 personalization) for the processor.

Per PRACTICE.md, the user's Trading Operating System is a structured
JSON profile stored in the gateway. The engine fetches it on every
analysis cycle and injects a *compressed, normalised* instruction
block into the LLM user message — NOT the raw JSON, to avoid prompt
bloat and prompt-injection-through-profile.

The institutional RAG (Layer 1) remains the source of truth. The user
OS biases reasoning; it never overrides the rulebook.
"""

from engine.processor.user_os.client import UserOSClient, UserOSRecord
from engine.processor.user_os.context_builder import (
    build_user_operating_context,
)

__all__ = [
    "UserOSClient",
    "UserOSRecord",
    "build_user_operating_context",
]
