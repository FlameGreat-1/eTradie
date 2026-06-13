"""Per-user streaming channel helpers.

The live-reasoning stream uses Redis pub/sub as the transport between
the processor and the engine's SSE endpoint. Every message is scoped
to a single authenticated user so that concurrent analysis cycles
run by different users never share frames.

Channel naming:
    etradie:stream:user:{user_id}

This module centralises the channel naming convention so the producer
(processor.service) and the consumer (main.stream_live_analysis)
cannot drift apart. Changing the name here changes both ends at once.
"""
from __future__ import annotations

from typing import Final

# Namespace prefix shared with every other Redis key in the app
# (see engine.shared.cache.redis_cache._make_key). Keeping the same
# prefix here means a `redis-cli KEYS 'etradie:*'` still discovers
# streaming channels alongside cache keys, which matters for ops.
_STREAM_NAMESPACE: Final[str] = "etradie:stream:user"


def stream_channel_for_user(user_id: str) -> str:
    """Return the per-user pub/sub channel name.

    Args:
        user_id: Authenticated user id. Must be non-empty; callers
            should obtain it from the auth context. Passing an empty
            string is treated as a programming error because it would
            silently collapse every user onto a single channel.

    Returns:
        Fully qualified channel name, e.g. ``etradie:stream:user:abc123``.

    Raises:
        ValueError: If ``user_id`` is empty.
    """
    if not user_id:
        raise ValueError("stream_channel_for_user requires a non-empty user_id")
    return f"{_STREAM_NAMESPACE}:{user_id}"


# Heartbeat cadence for the SSE endpoint. SSE comment frames
# (`: keepalive`) keep intermediaries (nginx, cloudflare, browsers)
# from closing an idle stream while the LLM is still reasoning. 15s
# is well below common 30-60s idle timeouts and negligible in cost.
SSE_HEARTBEAT_SECONDS: Final[float] = 15.0
