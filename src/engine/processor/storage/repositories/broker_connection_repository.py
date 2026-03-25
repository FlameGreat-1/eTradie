"""Repository for broker connection CRUD operations.

All database operations for the broker_connections table.
Credentials (EA auth tokens, MetaAPI tokens) are stored encrypted
using the same Fernet symmetric encryption as LLM connections.

The encryption key is derived identically to the LLM connection
repository so both use the same key derivation path.

NOTE: This module lives under processor/storage/ (not ta/broker/)
because it shares the same SQLAlchemy Base, session management,
and encryption infrastructure as the LLM connection repository.
Both broker and LLM connections are user-configured via the
dashboard and follow the same CRUD + encryption pattern.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from engine.processor.storage.schemas.broker_connection_schema import (
    BrokerConnectionRow,
)
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Valid connection types.
CONNECTION_TYPE_EA = "ea"
CONNECTION_TYPE_METAAPI = "metaapi"
VALID_CONNECTION_TYPES = {CONNECTION_TYPE_EA, CONNECTION_TYPE_METAAPI}

# Valid status values.
STATUS_UNTESTED = "untested"
STATUS_CONNECTED = "connected"
STATUS_DISCONNECTED = "disconnected"
STATUS_ERROR = "error"


# ---------------------------------------------------------------------------
# Encryption helpers (same derivation as LLM connection repository)
# ---------------------------------------------------------------------------

def _derive_encryption_key() -> bytes:
    """Derive a Fernet encryption key for credential encryption.

    Uses the same derivation chain as the LLM connection repository
    so both share the same key. Priority:
      1. BROKER_ENCRYPTION_KEY env var (shared across all credential stores)
      2. LLM_ENCRYPTION_KEY env var (legacy alias)
      3. DATABASE_URL env var
      4. Hardcoded fallback (dev only, never in production)
    """
    raw = os.environ.get("BROKER_ENCRYPTION_KEY", "")
    if not raw:
        raw = os.environ.get("LLM_ENCRYPTION_KEY", "")
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


def decrypt_credential(encrypted: str) -> str:
    """Public helper to decrypt a credential from a connection row.

    Used by the broker factory to get the plaintext token
    when building a broker client from a saved connection.
    """
    return _decrypt(encrypted)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Regex for validating hostnames and IP addresses.
# Matches: IPv4 (192.168.1.1), hostnames (my-vps.example.com),
# Docker service names (host.docker.internal), localhost.
_HOST_PATTERN = re.compile(
    r"^(?:"
    r"(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)"  # IPv4
    r"|(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"  # hostname
    r")$"
)


def _validate_host(host: str) -> None:
    """Validate that a host string is a valid IP address or hostname."""
    if len(host) > 253:
        raise ValueError(f"ea_host too long ({len(host)} chars, max 253)")
    if not _HOST_PATTERN.match(host):
        raise ValueError(
            f"ea_host must be a valid IP address or hostname, got '{host}'"
        )


def _validate_connection(
    connection_type: str,
    *,
    ea_host: Optional[str] = None,
    ea_port: Optional[int] = None,
    metaapi_token: Optional[str] = None,
    metaapi_account_id: Optional[str] = None,
) -> None:
    """Validate that required fields are present for the connection type."""
    if connection_type not in VALID_CONNECTION_TYPES:
        raise ValueError(
            f"connection_type must be one of {VALID_CONNECTION_TYPES}, "
            f"got '{connection_type}'"
        )

    if connection_type == CONNECTION_TYPE_EA:
        if not ea_host or not ea_host.strip():
            raise ValueError("ea_host is required for EA connections")
        _validate_host(ea_host.strip())
        if ea_port is None or ea_port < 1024 or ea_port > 65535:
            raise ValueError(
                f"ea_port must be 1024..65535 for EA connections, got {ea_port}"
            )

    if connection_type == CONNECTION_TYPE_METAAPI:
        if not metaapi_token or not metaapi_token.strip():
            raise ValueError("metaapi_token is required for MetaAPI connections")
        if not metaapi_account_id or not metaapi_account_id.strip():
            raise ValueError(
                "metaapi_account_id is required for MetaAPI connections"
            )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class BrokerConnectionRepository:
    """CRUD operations for broker connections."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- Create ----------------------------------------------------------------

    async def create(
        self,
        *,
        connection_type: str,
        name: str,
        # EA fields
        ea_host: Optional[str] = None,
        ea_port: Optional[int] = None,
        ea_auth_token: Optional[str] = None,
        # MetaAPI fields
        metaapi_token: Optional[str] = None,
        metaapi_account_id: Optional[str] = None,
        # Common MT5 info
        mt5_server: Optional[str] = None,
        mt5_login: Optional[str] = None,
        # Activation
        activate: bool = True,
    ) -> BrokerConnectionRow:
        """Create a new broker connection.

        If activate=True, deactivates all other connections first
        and marks this one as both active and primary.
        """
        _validate_connection(
            connection_type,
            ea_host=ea_host,
            ea_port=ea_port,
            metaapi_token=metaapi_token,
            metaapi_account_id=metaapi_account_id,
        )

        if activate:
            await self._deactivate_all()
            await self._unprimary_all()

        # Encrypt sensitive credentials.
        encrypted_ea_token: Optional[str] = None
        if ea_auth_token and ea_auth_token.strip():
            encrypted_ea_token = _encrypt(ea_auth_token)

        encrypted_metaapi_token: Optional[str] = None
        if metaapi_token and metaapi_token.strip():
            encrypted_metaapi_token = _encrypt(metaapi_token)

        now = datetime.now(UTC)
        row = BrokerConnectionRow(
            id=str(uuid4()),
            connection_type=connection_type,
            name=name,
            ea_host=ea_host,
            ea_port=ea_port,
            ea_auth_token_encrypted=encrypted_ea_token,
            metaapi_token_encrypted=encrypted_metaapi_token,
            metaapi_account_id=metaapi_account_id,
            mt5_server=mt5_server,
            mt5_login=mt5_login,
            is_active=activate,
            is_primary=activate,
            status=STATUS_UNTESTED,
            status_message="",
            last_connected_at=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()

        logger.info(
            "broker_connection_created",
            extra={
                "id": row.id,
                "type": connection_type,
                "name": name,
                "active": activate,
            },
        )
        return row

    # -- Read ------------------------------------------------------------------

    async def get_by_id(
        self, connection_id: str,
    ) -> Optional[BrokerConnectionRow]:
        """Return a single connection by ID."""
        stmt = select(BrokerConnectionRow).where(
            BrokerConnectionRow.id == connection_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active(self) -> Optional[BrokerConnectionRow]:
        """Return the currently active broker connection, or None."""
        stmt = (
            select(BrokerConnectionRow)
            .where(BrokerConnectionRow.is_active.is_(True))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_primary(self) -> Optional[BrokerConnectionRow]:
        """Return the primary broker connection, or None."""
        stmt = (
            select(BrokerConnectionRow)
            .where(BrokerConnectionRow.is_primary.is_(True))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self) -> list[BrokerConnectionRow]:
        """Return all broker connections ordered by most recent first."""
        stmt = (
            select(BrokerConnectionRow)
            .order_by(BrokerConnectionRow.updated_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -- Update ----------------------------------------------------------------

    async def update_connection(
        self,
        connection_id: str,
        *,
        name: Optional[str] = None,
        ea_host: Optional[str] = None,
        ea_port: Optional[int] = None,
        ea_auth_token: Optional[str] = None,
        metaapi_token: Optional[str] = None,
        metaapi_account_id: Optional[str] = None,
        mt5_server: Optional[str] = None,
        mt5_login: Optional[str] = None,
    ) -> Optional[BrokerConnectionRow]:
        """Update fields on an existing connection.

        Only non-None values are updated. Credentials are re-encrypted
        if provided.
        """
        values: dict = {"updated_at": datetime.now(UTC)}

        if name is not None:
            values["name"] = name
        if ea_host is not None:
            _validate_host(ea_host.strip())
            values["ea_host"] = ea_host.strip()
        if ea_port is not None:
            if ea_port < 1024 or ea_port > 65535:
                raise ValueError(
                    f"ea_port must be 1024..65535, got {ea_port}"
                )
            values["ea_port"] = ea_port
        if ea_auth_token is not None:
            values["ea_auth_token_encrypted"] = _encrypt(ea_auth_token)
        if metaapi_token is not None:
            values["metaapi_token_encrypted"] = _encrypt(metaapi_token)
        if metaapi_account_id is not None:
            values["metaapi_account_id"] = metaapi_account_id
        if mt5_server is not None:
            values["mt5_server"] = mt5_server
        if mt5_login is not None:
            values["mt5_login"] = mt5_login

        stmt = (
            update(BrokerConnectionRow)
            .where(BrokerConnectionRow.id == connection_id)
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id)

    # -- Activate / Deactivate / Set Primary -----------------------------------

    async def activate(self, connection_id: str) -> Optional[BrokerConnectionRow]:
        """Activate a connection (deactivates all others)."""
        await self._deactivate_all()

        stmt = (
            update(BrokerConnectionRow)
            .where(BrokerConnectionRow.id == connection_id)
            .values(is_active=True, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id)

    async def deactivate(self, connection_id: str) -> Optional[BrokerConnectionRow]:
        """Deactivate a specific connection."""
        stmt = (
            update(BrokerConnectionRow)
            .where(BrokerConnectionRow.id == connection_id)
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id)

    async def set_primary(self, connection_id: str) -> Optional[BrokerConnectionRow]:
        """Set a connection as primary (unsets all others).

        Also activates the connection if it is not already active.
        """
        await self._unprimary_all()
        await self._deactivate_all()

        stmt = (
            update(BrokerConnectionRow)
            .where(BrokerConnectionRow.id == connection_id)
            .values(
                is_primary=True,
                is_active=True,
                updated_at=datetime.now(UTC),
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id)

    # -- Health status ---------------------------------------------------------

    async def update_status(
        self,
        connection_id: str,
        *,
        status: str,
        status_message: str = "",
        connected: bool = False,
    ) -> Optional[BrokerConnectionRow]:
        """Update the health status of a connection after a test or connect."""
        values: dict = {
            "status": status,
            "status_message": status_message,
            "updated_at": datetime.now(UTC),
        }
        if connected:
            values["last_connected_at"] = datetime.now(UTC)

        stmt = (
            update(BrokerConnectionRow)
            .where(BrokerConnectionRow.id == connection_id)
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id)

    # -- Delete ----------------------------------------------------------------

    async def delete(self, connection_id: str) -> bool:
        """Delete a connection by ID. Returns True if found and deleted."""
        row = await self.get_by_id(connection_id)
        if row is None:
            return False

        await self._session.delete(row)
        await self._session.flush()

        logger.info(
            "broker_connection_deleted",
            extra={
                "id": connection_id,
                "type": row.connection_type,
                "name": row.name,
            },
        )
        return True

    # -- Internal helpers ------------------------------------------------------

    async def _deactivate_all(self) -> None:
        """Deactivate all connections."""
        stmt = (
            update(BrokerConnectionRow)
            .where(BrokerConnectionRow.is_active.is_(True))
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)

    async def _unprimary_all(self) -> None:
        """Remove primary flag from all connections."""
        stmt = (
            update(BrokerConnectionRow)
            .where(BrokerConnectionRow.is_primary.is_(True))
            .values(is_primary=False, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
