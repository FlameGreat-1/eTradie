"""User Trading Operating System integration.

Fetches the authenticated user's structured profile from the gateway
and compresses it into a deterministic, prompt-safe instruction block
that the processor injects into the LLM user message. See PRACTICE.md
Layer 2 for the architectural rationale.
"""

from engine.processor.user_os.cache import UserOSCache
from engine.processor.user_os.client import UserOSClient, UserOSRecord
from engine.processor.user_os.context_builder import (
    build_user_operating_context,
)

__all__ = [
    "UserOSCache",
    "UserOSClient",
    "UserOSRecord",
    "build_user_operating_context",
]
