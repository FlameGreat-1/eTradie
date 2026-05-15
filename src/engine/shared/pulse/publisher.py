"""PulsePublisher — non-blocking Redis broadcaster for analysis milestones.

Publishes ``pulse`` frames to the user's private SSE channel. The
existing SSE endpoint (``/api/analysis/stream-live``) already forwards
every message on the channel to the browser. The frontend reducer
handles frames by ``type``; we introduce ``type: "pulse"`` alongside
the existing ``status``, ``reasoning_chunk``, ``final``, and ``error``
types — so the existing stream contract is extended, not broken.

Frame format published to Redis::

    {
        "type":      "pulse",
        "symbol":    "EURUSD",
        "phase":     "SHARDING",                 # Hacker-verb category
        "message":   "Fetching H4 Candle Data",  # Granular sub-step
        "source":    "ta",                        # ta | macro | rag | processor
        "completed": false                        # true → phase done
    }

The ``phase`` field maps to the "in-place update" UI rows:
    LOADING       → System initialisation
    SHARDING      → Data acquisition (candle fetching per timeframe)
    DETECTING     → Structural analysis (swings, BMS, ChoCH, SMS)
    SHIMMING      → Zone scanning (OBs, FVGs, breakers, QM levels)
    PONTIFICATING → Liquidity & momentum (sweeps, inducements, fibo)
    FERMENTING    → Confluence (alignment, trend, candidate building)
    CLAUDING      → Macro intelligence (CB, COT, news, economic)
    GERMINATING   → RAG knowledge retrieval
    REASONING     → LLM processor / AI decision
    ACTIONING     → Persistence and finalisation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from engine.processor.streaming import stream_channel_for_user
from engine.shared.logging import get_logger

if TYPE_CHECKING:
    from engine.shared.cache.redis_cache import RedisCache

logger = get_logger(__name__)


@runtime_checkable
class PulseEmitter(Protocol):
    """Protocol so callers can type-hint without importing the concrete class."""

    async def emit(
        self,
        phase: str,
        message: str,
        *,
        source: str = "ta",
        completed: bool = False,
    ) -> None: ...


class PulsePublisher:
    """Production pulse emitter backed by Redis pub/sub.

    Every ``emit()`` call serialises a small JSON frame and publishes it
    to the user's private channel via ``RedisCache.publish()``. That
    method already handles:
        • ``orjson`` serialisation
        • Retry with exponential backoff
        • Graceful error swallowing (returns 0 on failure)

    This class adds an additional try/except so that **no exception**
    of any kind can ever propagate to the caller. The analysis pipeline
    must never be affected by a pulse failure.

    Args:
        cache:   The application's ``RedisCache`` instance.
        user_id: Authenticated user whose SSE channel receives frames.
        symbol:  Trading symbol being analysed (attached to every frame).
    """

    __slots__ = ("_cache", "_channel", "_symbol")

    def __init__(
        self,
        cache: RedisCache,
        user_id: str,
        symbol: str,
    ) -> None:
        self._cache = cache
        self._channel = stream_channel_for_user(user_id)
        self._symbol = symbol

    async def emit(
        self,
        phase: str,
        message: str,
        *,
        source: str = "ta",
        completed: bool = False,
    ) -> None:
        """Publish a single pulse frame. Fire-and-forget.

        Args:
            phase:     Hacker-verb category (SHARDING, DETECTING, …).
            message:   Human-readable sub-step description.
            source:    Origin component (ta, macro, rag, processor).
            completed: ``True`` when this phase has finished; the UI
                       renders a completion indicator instead of the
                       pulsing caret.
        """
        try:
            await self._cache.publish(
                self._channel,
                {
                    "type": "pulse",
                    "symbol": self._symbol,
                    "phase": phase,
                    "message": message,
                    "source": source,
                    "completed": completed,
                },
            )
        except Exception:
            # Absolute safety net. RedisCache.publish already swallows
            # errors internally, but if anything unexpected slips through
            # (e.g. the cache object itself is in a bad state) we must
            # never let it reach the analysis pipeline.
            pass


class NoOpPulse:
    """Silent no-op pulse for unit tests or when streaming is unavailable.

    Drop-in replacement for ``PulsePublisher`` that satisfies the
    ``PulseEmitter`` protocol without requiring Redis or a user_id.
    """

    async def emit(
        self,
        phase: str,
        message: str,
        *,
        source: str = "ta",
        completed: bool = False,
    ) -> None:
        """Do nothing."""
