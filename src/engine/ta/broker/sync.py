from typing import Any
import asyncio

from engine.shared.logging import get_logger
from engine.ta.broker.base import BrokerBase
from engine.ta.storage.uow import TAUOWFactory

logger = get_logger(__name__)


class BrokerSyncService:
    """
    Enterprise service for synchronizing broker metadata to the local registry.

    Handles rate-limiting, batching, and persistence of symbol specifications.
    This ensures we have the full MT5 'path' for every symbol without
    triggering 429 errors from MetaAPI.
    """

    def __init__(
        self,
        broker_client: BrokerBase,
        uow_factory: TAUOWFactory,
        concurrency: int = 2,  # Very conservative to avoid MetaAPI bans
        batch_delay: float = 0.5,
    ) -> None:
        self._broker = broker_client
        self._uow = uow_factory
        self._concurrency = concurrency
        self._batch_delay = batch_delay

    async def sync_all_symbols(self) -> None:
        """Fetch all symbols and their specifications from the broker and persist locally."""
        logger.info(
            "broker_symbol_sync_started",
            extra={
                "provider": self._broker.provider_name,
                "account_id": self._broker.account_id,
            },
        )

        try:
            # 1. Fetch raw symbol list (names only) - this is fast
            symbol_names = await self._broker.get_all_symbol_names()
            if not symbol_names:
                logger.warning("broker_sync_no_symbols_found")
                return

            # 2. Fetch specifications in limited concurrency batches
            semaphore = asyncio.Semaphore(self._concurrency)

            async def sync_one(name: str) -> Any:
                async with semaphore:
                    try:
                        # Fetch full spec (path, digits, etc)
                        info = await self._broker.get_symbol_info(name)

                        async with self._uow() as uow:
                            await uow.broker_symbol_repo.upsert(
                                provider=self._broker.provider_name,
                                account_id=self._broker.account_id,
                                name=name,
                                description=info.get("description"),
                                path=info.get("path", name),
                                digits=info.get("digits"),
                                point=info.get("point"),
                            )

                        # Small delay between individual requests to be safe
                        await asyncio.sleep(self._batch_delay)
                    except Exception as e:
                        logger.warning(
                            "broker_symbol_sync_failed_for_item",
                            extra={"symbol": name, "error": str(e)},
                        )

            # We don't use gather directly to avoid overwhelming the event loop with 1000 tasks
            # Instead, we'll process in small chunks of work
            for i in range(0, len(symbol_names), 50):
                batch = symbol_names[i : i + 50]
                await asyncio.gather(*(sync_one(name) for name in batch))
                # Extra breather between batches
                await asyncio.sleep(2.0)

            logger.info(
                "broker_symbol_sync_completed",
                extra={
                    "provider": self._broker.provider_name,
                    "count": len(symbol_names),
                },
            )

        except Exception as e:
            logger.exception("broker_symbol_sync_failed", extra={"error": str(e)})
