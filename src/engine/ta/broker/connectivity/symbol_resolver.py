"""Logical -> broker symbol resolver.

Different brokers expose the same instrument under slightly different
names: Exness commonly suffixes 'm', IC Markets uses '.r' or '_',
Darwinex uses '.PRO', some MT5 servers use '-' or '.a'. The eTradie
platform stores logical symbols ('EURUSD') in user-supplied data
(trading plans, broker_connections.default_symbol, dashboard pickers);
every broker call MUST go through this resolver to translate the
logical name to the actual broker-side name BEFORE the request is
sent. Otherwise the broker returns 'symbol not found' and the
caller has no good signal to recover.

Three resolution layers, queried in order:
  1. Redis cache. Fastest. TTL = symbol_resolver_cache_ttl_secs.
  2. broker_symbols DB table (populated by BrokerSyncService).
  3. Live broker call: pull the full symbol list and probe common
     suffix variants. Cached + DB-persisted on success.

The resolver is broker-agnostic. ZmqClient and MetaApiClient both
instantiate one with their own get_all_symbol_names() coroutine
bound at construction time.

Audit ref: CHECKLIST Section 2 - 'Symbol mapping consistency layer'.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from redis.asyncio import Redis

from engine.shared.exceptions import ProviderResponseError
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    BROKER_SYMBOL_RESOLVE_CACHE_HITS_TOTAL,
    BROKER_SYMBOL_RESOLVE_TOTAL,
)
from engine.ta.storage.uow import TAUOWFactory

logger = get_logger(__name__)

# Suffix variants probed when neither the Redis cache nor the DB
# already knows the broker-side name. Ordered by observed frequency
# across the integrated brokers. Empty string is always probed first
# (i.e. the broker uses the logical name unchanged).
_SUFFIX_PROBES = (
    "",
    "m",
    ".r",
    "_",
    ".a",
    ".PRO",
    "-",
    ".pro",
    "+",
)

FetchAllNamesFn = Callable[[], Awaitable[list[str]]]


@dataclass
class SymbolResolver:
    """Resolve a logical symbol to its broker-side name.

    Construct one per (provider, account_id). The fetch_all_names
    coroutine is the broker client's own get_all_symbol_names so the
    resolver does not couple to any client implementation.
    """

    provider: str
    account_id: str
    fetch_all_names: FetchAllNamesFn
    uow_factory: TAUOWFactory
    redis_client: Redis
    cache_ttl_secs: int = 3600

    REDIS_KEY_PREFIX = "etradie:symbol:resolve:"

    def _redis_key(self, logical: str) -> str:
        return f"{self.REDIS_KEY_PREFIX}{self.provider}:{self.account_id}:{logical}"

    async def resolve(self, logical_symbol: str) -> str:
        """Return the broker-side symbol name.

        Raises ProviderResponseError when no variant matches. Callers
        should surface this to the dashboard as 'symbol not available
        on this broker' rather than retry.
        """
        logical = logical_symbol.strip()
        if not logical:
            raise ProviderResponseError(
                "Empty symbol passed to SymbolResolver",
                details={"provider": self.provider, "account_id": self.account_id},
            )

        # Layer 1: Redis.
        try:
            cached = await self.redis_client.get(self._redis_key(logical))
            if cached is not None:
                BROKER_SYMBOL_RESOLVE_CACHE_HITS_TOTAL.labels(
                    provider=self.provider,
                    account_id=self.account_id,
                    layer="redis",
                ).inc()
                BROKER_SYMBOL_RESOLVE_TOTAL.labels(
                    provider=self.provider,
                    account_id=self.account_id,
                    result="hit_cache",
                ).inc()
                # redis client may return bytes or str depending on decode_responses
                return cached.decode("utf-8") if isinstance(cached, (bytes, bytearray)) else str(cached)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "symbol_resolver_redis_get_failed",
                extra={"error": str(exc)},
            )

        # Layer 2: DB.
        try:
            async with self.uow_factory() as uow:
                # Try exact logical match first (broker uses unchanged name).
                exact = await uow.broker_symbol_repo.get_by_name(
                    provider=self.provider,
                    account_id=self.account_id,
                    name=logical,
                )
                if exact is not None:
                    BROKER_SYMBOL_RESOLVE_CACHE_HITS_TOTAL.labels(
                        provider=self.provider,
                        account_id=self.account_id,
                        layer="db",
                    ).inc()
                    await self._cache(logical, exact.name)
                    BROKER_SYMBOL_RESOLVE_TOTAL.labels(
                        provider=self.provider,
                        account_id=self.account_id,
                        result="hit_db_exact",
                    ).inc()
                    return exact.name

                # Try suffix-stripped match for cases where the DB row
                # is the broker-side name and the caller passed the
                # logical name (e.g. DB has 'EURUSDm' and caller asks
                # for 'EURUSD').
                rows = await uow.broker_symbol_repo.get_all_by_account(
                    provider=self.provider,
                    account_id=self.account_id,
                )
                for row in rows:
                    for suf in _SUFFIX_PROBES:
                        if suf and row.name == f"{logical}{suf}":
                            await self._cache(logical, row.name)
                            BROKER_SYMBOL_RESOLVE_CACHE_HITS_TOTAL.labels(
                                provider=self.provider,
                                account_id=self.account_id,
                                layer="db",
                            ).inc()
                            BROKER_SYMBOL_RESOLVE_TOTAL.labels(
                                provider=self.provider,
                                account_id=self.account_id,
                                result="hit_db_suffix",
                            ).inc()
                            return row.name
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "symbol_resolver_db_lookup_failed",
                extra={"error": str(exc), "logical": logical},
            )

        # Layer 3: Live broker probe.
        names: list[str] = []
        try:
            names = await self.fetch_all_names()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "symbol_resolver_live_probe_failed",
                extra={"error": str(exc), "logical": logical},
            )
            names = []

        name_set = set(names)
        for suf in _SUFFIX_PROBES:
            candidate = f"{logical}{suf}"
            if candidate in name_set:
                await self._cache(logical, candidate)
                await self._persist_db(candidate)
                BROKER_SYMBOL_RESOLVE_TOTAL.labels(
                    provider=self.provider,
                    account_id=self.account_id,
                    result="hit_live",
                ).inc()
                return candidate

        BROKER_SYMBOL_RESOLVE_TOTAL.labels(
            provider=self.provider,
            account_id=self.account_id,
            result="miss",
        ).inc()
        raise ProviderResponseError(
            f"Symbol {logical!r} is not available on this broker",
            details={
                "provider": self.provider,
                "account_id": self.account_id,
                "logical": logical,
                "probes": list(_SUFFIX_PROBES),
                "available_count": len(names),
            },
        )

    async def _cache(self, logical: str, broker_name: str) -> None:
        try:
            await self.redis_client.set(
                self._redis_key(logical),
                broker_name,
                ex=self.cache_ttl_secs,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "symbol_resolver_cache_set_failed",
                extra={"error": str(exc)},
            )

    async def _persist_db(self, broker_name: str) -> None:
        try:
            async with self.uow_factory() as uow:
                await uow.broker_symbol_repo.upsert(
                    provider=self.provider,
                    account_id=self.account_id,
                    name=broker_name,
                    description=None,
                    path=broker_name,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "symbol_resolver_db_persist_failed",
                extra={"error": str(exc), "broker_name": broker_name},
            )
