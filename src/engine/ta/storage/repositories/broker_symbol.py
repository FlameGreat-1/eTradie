from datetime import UTC, datetime
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from engine.shared.logging import get_logger
from engine.ta.storage.schemas.broker_symbol import BrokerSymbolSchema

logger = get_logger(__name__)


class BrokerSymbolRepository:
    """
    Repository for persistent broker symbol metadata.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        provider: str,
        account_id: str,
        name: str,
        description: Optional[str],
        path: Optional[str],
        digits: Optional[int] = None,
        point: Optional[float] = None,
    ) -> BrokerSymbolSchema:
        """Upsert a broker symbol record."""
        stmt = insert(BrokerSymbolSchema).values(
            provider=provider,
            account_id=account_id,
            name=name,
            description=description,
            path=path,
            digits=digits,
            point=point,
            last_synced_at=datetime.now(UTC),
        )

        update_stmt = stmt.on_conflict_do_update(
            index_elements=["provider", "account_id", "name"],
            set_={
                "description": stmt.excluded.description,
                "path": stmt.excluded.path,
                "digits": stmt.excluded.digits,
                "point": stmt.excluded.point,
                "last_synced_at": stmt.excluded.last_synced_at,
            },
        )

        await self.session.execute(update_stmt)
        await self.session.flush()

        result = await self.session.execute(
            select(BrokerSymbolSchema).where(
                and_(
                    BrokerSymbolSchema.provider == provider,
                    BrokerSymbolSchema.account_id == account_id,
                    BrokerSymbolSchema.name == name,
                )
            )
        )
        return result.scalar_one()

    async def get_all_by_account(
        self, provider: str, account_id: str
    ) -> list[BrokerSymbolSchema]:
        """Retrieve all symbols for a specific broker account."""
        result = await self.session.execute(
            select(BrokerSymbolSchema).where(
                and_(
                    BrokerSymbolSchema.provider == provider,
                    BrokerSymbolSchema.account_id == account_id,
                )
            )
        )
        return list(result.scalars().all())

    async def get_by_name(
        self, provider: str, account_id: str, name: str
    ) -> Optional[BrokerSymbolSchema]:
        """Retrieve a specific symbol by name."""
        result = await self.session.execute(
            select(BrokerSymbolSchema).where(
                and_(
                    BrokerSymbolSchema.provider == provider,
                    BrokerSymbolSchema.account_id == account_id,
                    BrokerSymbolSchema.name == name,
                )
            )
        )
        return result.scalar_one_or_none()
