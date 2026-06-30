"""Redis-based symbol reader for TA data jobs.

Reads the active symbol list from the same Redis key that the Go
gateway writes to. In multi-tenant mode, each user's symbols are
stored at: ``etradie:gateway:user:{userID}:active_symbols``.

Falls back to a configurable default list when no user selection
exists in Redis. This is the Python-side counterpart of the Go
gateway's SymbolStore.

The Go gateway WRITES to these keys.
The Python engine READS from these keys.
Both use the same Redis instance and the same key format.
"""

from __future__ import annotations

from engine.shared.cache import RedisCache
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Must match the Go gateway's constants exactly.
_CACHE_NAMESPACE = "gateway"

_DEFAULT_SYMBOLS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "NZDUSD",
    "USDCAD",
    "XAUUSD",
]


def _user_symbols_key(user_id: str) -> str:
    """Build the user-scoped Redis key for active symbols.

    Must match the Go gateway's symbolstore.activeSymbolsKey() exactly:
        "user:" + userID + ":active_symbols"
    """
    return f"user:{user_id}:active_symbols"


class RedisSymbolReader:
    """Reads the active symbol list from Redis (written by the Go gateway).

    In multi-tenant mode, each user has their own symbol selection.
    TA data fetching happens per-user when the Go gateway triggers
    /internal/ta/analyze with the user's JWT. There are no
    platform-level TA scheduler jobs.
    """

    def __init__(
        self,
        cache: RedisCache,
        default_symbols: list[str] | None = None,
    ) -> None:
        self._cache = cache
        self._defaults = default_symbols or list(_DEFAULT_SYMBOLS)

    async def get_active_symbols(self, user_id: str | None = None) -> list[str]:
        """Return the active symbols from Redis, falling back to defaults.

        Args:
            user_id: If provided, reads the user-scoped symbol selection
                     from Redis. If None, returns the configured defaults
                     (used by platform-level TA scheduler jobs).

        Priority:
        1. User-scoped selection persisted in Redis by the Go gateway
        2. Default symbols from configuration
        """
        if user_id is None:
            logger.debug(
                "symbol_reader_no_user_id_using_defaults",
                extra={"symbols": self._defaults, "source": "defaults"},
            )
            return list(self._defaults)

        key = _user_symbols_key(user_id)

        try:
            stored = await self._cache.get(
                _CACHE_NAMESPACE,
                key,
            )

            if stored is not None and isinstance(stored, list) and len(stored) > 0:
                symbols = [s for s in stored if isinstance(s, str) and s.strip()]
                if symbols:
                    logger.debug(
                        "symbol_reader_loaded_from_redis",
                        extra={
                            "symbols": symbols,
                            "source": "redis",
                            "user_id": user_id,
                        },
                    )
                    return symbols

        except Exception as exc:
            logger.warning(
                "symbol_reader_redis_failed_using_defaults",
                extra={"error": str(exc), "user_id": user_id},
            )

        logger.debug(
            "symbol_reader_using_defaults",
            extra={"symbols": self._defaults, "source": "defaults", "user_id": user_id},
        )
        return list(self._defaults)
