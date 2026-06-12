"""Repository for LLM connection CRUD operations.

All database operations for the llm_connections table. API keys are
stored encrypted at rest using the shared credential cipher
(engine.shared.crypto) -- the same versioned envelope encryption and
the same KEK (BROKER_ENCRYPTION_KEY) as the broker connection
repository, so there is exactly one cipher and one key path across the
engine's credential stores.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from engine.processor.config import get_processor_config
from engine.processor.storage.schemas.llm_connection_schema import LLMConnectionRow
from engine.shared.crypto import (
    active_key_version,
)
from engine.shared.crypto import (
    decrypt_credential as _decrypt,
)
from engine.shared.crypto import (
    encrypt_credential as _encrypt,
)
from engine.shared.logging import get_logger

logger = get_logger(__name__)


class LLMConnectionRepository:
    """CRUD operations for LLM connections.

    Every method requires a user_id parameter to enforce multi-tenant
    data isolation. Users can only see and manage their own connections.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: str,
        provider: str,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
        temperature: float = 0.0,
        max_output_tokens: int | None = None,
        label: str = "",
        activate: bool = True,
    ) -> LLMConnectionRow:
        """Create a new LLM connection owned by user_id.

        If activate=True, deactivates all other connections for this
        user first. Both the deactivation and the insert happen inside
        a row-level lock on the user's existing rows so concurrent
        callers (e.g. a double-clicked Save button, or React strict-
        mode dev refire) serialise on the lock rather than racing
        through the deactivation and both ending up active. The
        partial unique index created by Alembic 0022 is the hard
        guarantee; this lock keeps the happy path lock-free of
        IntegrityError retries.
        """
        if activate:
            await self._lock_user_active_rows(user_id)
            await self._deactivate_all(user_id)

        if max_output_tokens is None:
            max_output_tokens = get_processor_config().max_output_tokens

        if not label:
            label = f"{provider} / {model_name}"

        row = LLMConnectionRow(
            id=str(uuid4()),
            user_id=user_id,
            provider=provider,
            model_name=model_name,
            api_key_encrypted=_encrypt(api_key),
            key_version=active_key_version(),
            base_url=base_url,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            is_active=activate,
            is_platform=False,
            label=label,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()

        logger.info(
            "llm_connection_created",
            extra={
                "id": row.id,
                "user_id": user_id,
                "provider": provider,
                "model": model_name,
                "active": activate,
                "is_platform": False,
            },
        )
        return row

    async def create_platform(
        self,
        *,
        provider: str,
        model_name: str,
        api_key: str,
        base_url: str | None = None,
        temperature: float = 0.0,
        max_output_tokens: int | None = None,
    ) -> LLMConnectionRow:
        """Create or update the platform-level LLM connection.

        Overwrites the existing platform connection if one exists.
        """
        # Remove any existing platform connection
        await self.delete_platform()

        if max_output_tokens is None:
            max_output_tokens = get_processor_config().max_output_tokens

        row = LLMConnectionRow(
            id=str(uuid4()),
            user_id=None,
            provider=provider,
            model_name=model_name,
            api_key_encrypted=_encrypt(api_key),
            key_version=active_key_version(),
            base_url=base_url,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            is_active=True,
            is_platform=True,
            label=f"Platform: {provider} / {model_name}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()

        logger.info(
            "platform_llm_connection_created",
            extra={
                "id": row.id,
                "provider": provider,
                "model": model_name,
            },
        )
        return row

    async def get_active(self, user_id: str) -> LLMConnectionRow | None:
        """Return the currently active LLM connection for this user, or None.

        Deterministic ordering (most recently updated, then id) so the
        loader picks the same row across container restarts even if a
        future bug ever bypasses the partial unique index and leaves
        duplicates behind.
        """
        stmt = (
            select(LLMConnectionRow)
            .where(
                LLMConnectionRow.user_id == user_id,
                LLMConnectionRow.is_platform.is_(False),
                LLMConnectionRow.is_active.is_(True),
            )
            .order_by(
                LLMConnectionRow.updated_at.desc(),
                LLMConnectionRow.id.asc(),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_platform(self) -> LLMConnectionRow | None:
        """Return the platform-level LLM connection, if any.

        Deterministic ordering for the same reason as get_active.
        """
        stmt = (
            select(LLMConnectionRow)
            .where(LLMConnectionRow.is_platform.is_(True))
            .order_by(
                LLMConnectionRow.is_active.desc(),
                LLMConnectionRow.updated_at.desc(),
                LLMConnectionRow.id.asc(),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, user_id: str) -> list[LLMConnectionRow]:
        """Return all LLM connections for this user, ordered by most recent first."""
        stmt = (
            select(LLMConnectionRow)
            .where(
                LLMConnectionRow.user_id == user_id,
                LLMConnectionRow.is_platform.is_(False),
            )
            .order_by(LLMConnectionRow.updated_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, connection_id: str, user_id: str) -> LLMConnectionRow | None:
        """Return a single connection by ID, scoped to user."""
        stmt = select(LLMConnectionRow).where(
            LLMConnectionRow.id == connection_id,
            LLMConnectionRow.user_id == user_id,
            LLMConnectionRow.is_platform.is_(False),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def activate(self, connection_id: str, user_id: str) -> LLMConnectionRow | None:
        """Activate a connection (deactivates all others for this user).

        Takes a row-level lock on the user's existing active rows
        before deactivating + activating so concurrent activate()
        calls from the same user serialise instead of racing past the
        bare UPDATE. The partial unique index created by Alembic 0022
        is the hard guarantee; this lock keeps the happy path lock-
        free of IntegrityError retries.
        """
        await self._lock_user_active_rows(user_id)
        await self._deactivate_all(user_id)

        stmt = (
            update(LLMConnectionRow)
            .where(
                LLMConnectionRow.id == connection_id,
                LLMConnectionRow.user_id == user_id,
            )
            .values(is_active=True, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id, user_id)

    async def deactivate(self, connection_id: str, user_id: str) -> LLMConnectionRow | None:
        """Deactivate a specific connection, scoped to user."""
        stmt = (
            update(LLMConnectionRow)
            .where(
                LLMConnectionRow.id == connection_id,
                LLMConnectionRow.user_id == user_id,
            )
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id, user_id)

    async def delete(self, connection_id: str, user_id: str) -> bool:
        """Delete a connection by ID, scoped to user. Returns True if found and deleted."""
        row = await self.get_by_id(connection_id, user_id)
        if row is None:
            return False

        await self._session.delete(row)
        await self._session.flush()

        logger.info(
            "llm_connection_deleted",
            extra={"id": connection_id, "user_id": user_id, "provider": row.provider},
        )
        return True

    async def delete_platform(self) -> bool:
        """Delete the platform-level connection. Returns True if found and deleted."""
        row = await self.get_platform()
        if row is None:
            return False

        await self._session.delete(row)
        await self._session.flush()

        logger.info(
            "platform_llm_connection_deleted",
            extra={"id": str(row.id), "provider": row.provider},
        )
        return True

    async def update_connection(
        self,
        connection_id: str,
        user_id: str,
        *,
        provider: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        label: str | None = None,
    ) -> LLMConnectionRow | None:
        """Update fields on an existing connection, scoped to user."""
        values: dict = {"updated_at": datetime.now(UTC)}

        if provider is not None:
            values["provider"] = provider
        if model_name is not None:
            values["model_name"] = model_name
        if api_key is not None:
            values["api_key_encrypted"] = _encrypt(api_key)
            values["key_version"] = active_key_version()
        if base_url is not None:
            values["base_url"] = base_url
        if temperature is not None:
            values["temperature"] = temperature
        if max_output_tokens is not None:
            values["max_output_tokens"] = max_output_tokens
        if label is not None:
            values["label"] = label

        stmt = (
            update(LLMConnectionRow)
            .where(
                LLMConnectionRow.id == connection_id,
                LLMConnectionRow.user_id == user_id,
            )
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id, user_id)

    async def _deactivate_all(self, user_id: str) -> None:
        """Deactivate all connections for this user."""
        stmt = (
            update(LLMConnectionRow)
            .where(
                LLMConnectionRow.user_id == user_id,
                LLMConnectionRow.is_active.is_(True),
            )
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)

    async def _lock_user_active_rows(self, user_id: str) -> None:
        """Take a row-level lock on the user's existing active rows.

        Called before the deactivate + insert/update sequence in
        ``create`` and ``activate`` to serialise concurrent callers.
        Two simultaneous requests from the same user will queue at
        the row lock instead of both passing the deactivation step
        and racing toward the partial unique index, which would
        otherwise reject the loser with an IntegrityError that the
        caller would have to map to a 409.

        The lock is released when the surrounding transaction commits
        or rolls back -- i.e. when the caller's ``async with
        container.db.session()`` block exits. SQLAlchemy translates
        ``with_for_update()`` to ``SELECT ... FOR UPDATE`` on
        PostgreSQL, which is the canonical mechanism for this pattern.
        """
        stmt = (
            select(LLMConnectionRow.id)
            .where(
                LLMConnectionRow.user_id == user_id,
                LLMConnectionRow.is_active.is_(True),
            )
            .with_for_update()
        )
        await self._session.execute(stmt)


def decrypt_api_key(encrypted: str) -> str:
    """Public helper to decrypt an API key from a connection row.

    Used by the processor config loader to get the plaintext key
    when building the LLM client from a saved connection. Delegates to
    the shared envelope cipher (engine.shared.crypto).
    """
    return _decrypt(encrypted)
