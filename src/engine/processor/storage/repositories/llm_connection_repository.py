"""Repository for LLM connection CRUD operations.

All database operations for the llm_connections table.
API keys are stored encrypted using Fernet symmetric encryption.
The encryption key is derived from the DATABASE_URL to avoid
requiring a separate secret management system.
"""

from __future__ import annotations

import base64
import hashlib
import os
from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from engine.processor.storage.schemas.llm_connection_schema import LLMConnectionRow
from engine.shared.logging import get_logger

logger = get_logger(__name__)


def _derive_encryption_key() -> bytes:
    """Derive a Fernet encryption key from the LLM_ENCRYPTION_KEY env var.

    Falls back to a key derived from DATABASE_URL if the dedicated env var
    is not set. This ensures API keys are never stored in plaintext.
    """
    raw = os.environ.get("LLM_ENCRYPTION_KEY", "")
    if not raw:
        raw = os.environ.get("PROCESSOR_DATABASE_URL", "")
    if not raw:
        raw = os.environ.get("DATABASE_URL", "etradie-default-key")
    digest = hashlib.sha256(raw.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _encrypt(plaintext: str) -> str:
    """Encrypt a string using Fernet."""
    f = Fernet(_derive_encryption_key())
    return f.encrypt(plaintext.encode()).decode()


def _decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    f = Fernet(_derive_encryption_key())
    return f.decrypt(ciphertext.encode()).decode()


class LLMConnectionRepository:
    """CRUD operations for LLM connections."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        provider: str,
        model_name: str,
        api_key: str,
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        max_output_tokens: int = 16384,
        label: str = "",
        activate: bool = True,
    ) -> LLMConnectionRow:
        """Create a new LLM connection.

        If activate=True, deactivates all other connections first.
        """
        if activate:
            await self._deactivate_all()

        if not label:
            label = f"{provider} / {model_name}"

        row = LLMConnectionRow(
            id=str(uuid4()),
            provider=provider,
            model_name=model_name,
            api_key_encrypted=_encrypt(api_key),
            base_url=base_url,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            is_active=activate,
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
                "provider": provider,
                "model": model_name,
                "active": activate,
            },
        )
        return row

    async def get_active(self) -> Optional[LLMConnectionRow]:
        """Return the currently active LLM connection, or None."""
        stmt = select(LLMConnectionRow).where(
            LLMConnectionRow.is_active.is_(True)
        ).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self) -> list[LLMConnectionRow]:
        """Return all LLM connections ordered by most recent first."""
        stmt = (
            select(LLMConnectionRow)
            .order_by(LLMConnectionRow.updated_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, connection_id: str) -> Optional[LLMConnectionRow]:
        """Return a single connection by ID."""
        stmt = select(LLMConnectionRow).where(
            LLMConnectionRow.id == connection_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def activate(self, connection_id: str) -> Optional[LLMConnectionRow]:
        """Activate a connection (deactivates all others)."""
        await self._deactivate_all()

        stmt = (
            update(LLMConnectionRow)
            .where(LLMConnectionRow.id == connection_id)
            .values(is_active=True, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id)

    async def deactivate(self, connection_id: str) -> Optional[LLMConnectionRow]:
        """Deactivate a specific connection."""
        stmt = (
            update(LLMConnectionRow)
            .where(LLMConnectionRow.id == connection_id)
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id)

    async def delete(self, connection_id: str) -> bool:
        """Delete a connection by ID. Returns True if found and deleted."""
        row = await self.get_by_id(connection_id)
        if row is None:
            return False

        await self._session.delete(row)
        await self._session.flush()

        logger.info(
            "llm_connection_deleted",
            extra={"id": connection_id, "provider": row.provider},
        )
        return True

    async def update_connection(
        self,
        connection_id: str,
        *,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        label: Optional[str] = None,
    ) -> Optional[LLMConnectionRow]:
        """Update fields on an existing connection."""
        values: dict = {"updated_at": datetime.now(UTC)}

        if provider is not None:
            values["provider"] = provider
        if model_name is not None:
            values["model_name"] = model_name
        if api_key is not None:
            values["api_key_encrypted"] = _encrypt(api_key)
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
            .where(LLMConnectionRow.id == connection_id)
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id)

    async def _deactivate_all(self) -> None:
        """Deactivate all connections."""
        stmt = (
            update(LLMConnectionRow)
            .where(LLMConnectionRow.is_active.is_(True))
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)


def decrypt_api_key(encrypted: str) -> str:
    """Public helper to decrypt an API key from a connection row.

    Used by the processor config loader to get the plaintext key
    when building the LLM client from a saved connection.
    """
    return _decrypt(encrypted)
