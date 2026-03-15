"""Redis-based symbol reader for TA data jobs.

Reads the active symbol list from the same Redis key that the Go
gateway writes to: ``etradie:gateway:active_symbols``.

Falls back to a configurable default list when no user selection
exists in Redis. This is the Python-side counterpart of the Go
gateway's SymbolStore.

The Go gateway WRITES to this key.
The Python engine READS from this key.
Both use the same Redis instance and the same key format.
"""

from __future__ import annotations

from typing import Optional

from engine.shared.cache import RedisCache
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Must match the Go gateway's constants exactly.
_CACHE_NAMESPACE = "gateway"
_ACTIVE_SYMBOLS_KEY = "active_symbols"

_DEFAULT_SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "AUDUSD", "NZDUSD", "USDCAD", "XAUUSD",
]


class RedisSymbolReader:
    """Reads the active symbol list from Redis (written by the Go gateway).

    Provides the same async interface as the old Python SymbolStore
    so it can be passed directly to register_ta_jobs(symbol_store=...).
    """

    def __init__(
        self,
        cache: RedisCache,
        default_symbols: Optional[list[str]] = None,
    ) -> None:
        self._cache = cache
        self._defaults = default_symbols or list(_DEFAULT_SYMBOLS)

    async def get_active_symbols(self) -> list[str]:
        """Return the active symbols from Redis, falling back to defaults.

        Priority:
        1. User selection persisted in Redis by the Go gateway
        2. Default symbols from configuration
        """
        try:
            stored = await self._cache.get(
                _CACHE_NAMESPACE,
                _ACTIVE_SYMBOLS_KEY,
            )

            if stored is not None and isinstance(stored, list) and len(stored) > 0:
                symbols = [
                    s.upper()
                    for s in stored
                    if isinstance(s, str) and s.strip()
                ]
                if symbols:
                    logger.debug(
                        "symbol_reader_loaded_from_redis",
                        extra={"symbols": symbols, "source": "redis"},
                    )
                    return symbols

        except Exception as exc:
            logger.warning(
                "symbol_reader_redis_failed_using_defaults",
                extra={"error": str(exc)},
            )

        logger.debug(
            "symbol_reader_using_defaults",
            extra={"symbols": self._defaults, "source": "defaults"},
        )
        return list(self._defaults)
