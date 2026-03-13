"""Persisted user symbol selection.

Stores the user's active symbol list in Redis so that every gateway
cycle (scheduled or on-demand) uses the same selection until the user
changes it.  Falls back to TAConfig.default_symbols when no user
selection exists.

The gateway is stateless per GATEWAY.md, but the user's symbol
preference is application state that must survive restarts.  Redis
is the correct store for this: fast, already in the stack, and
the data is small (a JSON list of strings).
"""

from __future__ import annotations

from typing import Optional

from engine.config import get_ta_config
from engine.shared.cache import RedisCache
from engine.shared.logging import get_logger
from gateway.constants import GATEWAY_CACHE_NAMESPACE

logger = get_logger(__name__)

_ACTIVE_SYMBOLS_KEY = "active_symbols"

# No TTL expiry: the selection persists until explicitly changed.
# Using a very long TTL (30 days) as a safety net against orphaned keys.
_ACTIVE_SYMBOLS_TTL = 30 * 24 * 3600


class SymbolStore:
    """Redis-backed store for the user's active symbol selection."""

    def __init__(self, cache: RedisCache) -> None:
        self._cache = cache

    async def get_active_symbols(self) -> list[str]:
        """Return the user's active symbols, falling back to defaults.

        Priority:
        1. User selection persisted in Redis
        2. TAConfig.default_symbols (initial defaults)
        """
        try:
            stored = await self._cache.get(
                GATEWAY_CACHE_NAMESPACE,
                _ACTIVE_SYMBOLS_KEY,
            )

            if stored is not None and isinstance(stored, list) and len(stored) > 0:
                symbols = [s.upper() for s in stored if isinstance(s, str) and s.strip()]
                if symbols:
                    logger.debug(
                        "symbol_store_loaded_user_selection",
                        extra={"symbols": symbols, "source": "redis"},
                    )
                    return symbols

        except Exception as exc:
            logger.warning(
                "symbol_store_read_failed_using_defaults",
                extra={"error": str(exc)},
            )

        defaults = list(get_ta_config().default_symbols)
        logger.debug(
            "symbol_store_using_defaults",
            extra={"symbols": defaults, "source": "ta_config"},
        )
        return defaults

    async def set_active_symbols(self, symbols: list[str]) -> bool:
        """Persist the user's symbol selection.

        Args:
            symbols: Non-empty list of symbol strings.

        Returns:
            True on success, False on failure.
        """
        if not symbols:
            logger.warning("symbol_store_set_called_with_empty_list")
            return False

        normalized = [s.upper().strip() for s in symbols if s.strip()]
        if not normalized:
            logger.warning("symbol_store_set_called_with_invalid_symbols")
            return False

        try:
            success = await self._cache.set(
                GATEWAY_CACHE_NAMESPACE,
                _ACTIVE_SYMBOLS_KEY,
                normalized,
                ttl_seconds=_ACTIVE_SYMBOLS_TTL,
            )

            if success:
                logger.info(
                    "symbol_store_updated",
                    extra={"symbols": normalized},
                )

            return success

        except Exception as exc:
            logger.error(
                "symbol_store_write_failed",
                extra={"symbols": normalized, "error": str(exc)},
            )
            return False

    async def reset_to_defaults(self) -> bool:
        """Clear user selection so the next read falls back to defaults."""
        try:
            success = await self._cache.delete(
                GATEWAY_CACHE_NAMESPACE,
                _ACTIVE_SYMBOLS_KEY,
            )

            if success:
                logger.info("symbol_store_reset_to_defaults")

            return success

        except Exception as exc:
            logger.error(
                "symbol_store_reset_failed",
                extra={"error": str(exc)},
            )
            return False
