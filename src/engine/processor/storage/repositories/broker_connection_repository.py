"""Repository for broker connection CRUD operations.

All database operations for the broker_connections table.

Credentials (MT5 password, EA auth token) are encrypted at rest by the
shared credential cipher (engine.shared.crypto): versioned envelope
encryption with an AES-256-GCM data layer (per-record 256-bit DEK
wrapped by a versioned KEK), the same cipher and the same KEK path the
LLM connection repository uses, so there is exactly one encryption
implementation across the engine's credential stores. The wrapping KEK
version is recorded in the row's key_version column for rotation
observability (see migration 0033 and
docs/security/TIER3_CREDENTIAL_ENCRYPTION.md).

NOTE: This module lives under processor/storage/ (not ta/broker/)
because it shares the same SQLAlchemy Base and session management as
the LLM connection repository. Both broker and LLM connections are
user-configured via the dashboard and follow the same CRUD + encryption
pattern.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from engine.processor.storage.schemas.broker_connection_schema import (
    BrokerConnectionRow,
)
from engine.shared.crypto import (
    active_key_version,
    decrypt_credential as _decrypt,
    encrypt_credential as _encrypt,
    key_version_of,
)
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Valid connection types.
CONNECTION_TYPE_EA = "ea"
CONNECTION_TYPE_METAAPI = "metaapi"
CONNECTION_TYPE_HOSTED = "hosted"
VALID_CONNECTION_TYPES = {CONNECTION_TYPE_EA, CONNECTION_TYPE_METAAPI, CONNECTION_TYPE_HOSTED}

# Valid status values.
STATUS_UNTESTED = "untested"
STATUS_CONNECTED = "connected"
STATUS_DISCONNECTED = "disconnected"
STATUS_ERROR = "error"


# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------
#
# Credential encryption lives in engine.shared.crypto (the single source
# of truth shared with the LLM connection repository). This module binds
# the shared functions to the local names the repository body already
# uses (_encrypt / _decrypt) and re-exports the public decrypt_credential
# helper so existing importers (routers/broker_connections.py, the mt5
# broker factory) keep working unchanged.
#
# New writes use versioned envelope encryption; legacy bare-Fernet
# ciphertext written by the previous implementation decrypts
# transparently (see engine.shared.crypto.credential_cipher).


def decrypt_credential(encrypted: str) -> str:
    """Public helper to decrypt a credential from a connection row.

    Used by the broker factory and the broker-connections router to get
    the plaintext token when building a broker client from a saved
    connection. Delegates to the shared envelope cipher.
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
    mt5_login: Optional[str] = None,
    mt5_password: Optional[str] = None,
    mt5_server: Optional[str] = None,
) -> None:
    """Validate that required fields are present for the connection type.

    EA connections: ea_host and ea_port are required (auto-populated
    from server-side env vars, never user-provided).

    MetaAPI connections: mt5_login, mt5_password, and mt5_server are
    required (user-provided MT5 broker credentials). The metaapi_account_id
    is NOT validated here because it is generated AFTER provisioning.
    """
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
        if not mt5_login or not mt5_login.strip():
            raise ValueError("mt5_login is required for MetaAPI connections")
        if not mt5_password or not mt5_password.strip():
            raise ValueError("mt5_password is required for MetaAPI connections")
        if not mt5_server or not mt5_server.strip():
            raise ValueError("mt5_server is required for MetaAPI connections")

    if connection_type == CONNECTION_TYPE_HOSTED:
        if not mt5_login or not mt5_login.strip():
            raise ValueError("mt5_login is required for Hosted connections")
        if not mt5_password or not mt5_password.strip():
            raise ValueError("mt5_password is required for Hosted connections")
        if not mt5_server or not mt5_server.strip():
            raise ValueError("mt5_server is required for Hosted connections")


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class BrokerConnectionRepository:
    """CRUD operations for broker connections.

    Every method requires a user_id parameter to enforce multi-tenant
    data isolation. Users can only see and manage their own connections.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- Create ----------------------------------------------------------------

    async def create(
        self,
        *,
        user_id: str,
        connection_type: str,
        name: str,
        # EA fields (auto-populated from env, not user-provided)
        ea_host: Optional[str] = None,
        ea_port: Optional[int] = None,
        ea_auth_token: Optional[str] = None,
        # MetaAPI: account_id and region come from provisioning, not user input
        metaapi_account_id: Optional[str] = None,
        metaapi_region: Optional[str] = None,
        # Hosted: container_id comes from Docker provisioner
        hosted_container_id: Optional[str] = None,
        # Common MT5 info
        mt5_server: Optional[str] = None,
        mt5_login: Optional[str] = None,
        mt5_password: Optional[str] = None,
        mt5_symbol: Optional[str] = None,
        platform: str = "mt5",
        # Activation
        activate: bool = True,
        # Optional explicit row id (UUID string). When supplied, the row
        # is persisted with this exact id so the hosted-connection path
        # can pre-allocate it and pass the same value to the K8s
        # provisioner. The broker_connections.id, the StatefulSet name,
        # and the etradie.connection-id label all line up.
        id: Optional[str] = None,
        # Status overrides
        status: str = STATUS_UNTESTED,
        status_message: str = "",
    ) -> BrokerConnectionRow:
        """Create a new broker connection.

        For MetaAPI connections:
          - mt5_login, mt5_password, mt5_server are required (user credentials)
          - metaapi_account_id is set after provisioning via the API
          - Platform token comes from env (MT5_METAAPI_TOKEN), NOT stored per-row

        For EA connections:
          - ea_host, ea_port, ea_auth_token come from server-side env vars
          - User only provides the connection name

        If activate=True, deactivates all other connections first
        and marks this one as both active and primary.
        """
        _validate_connection(
            connection_type,
            ea_host=ea_host,
            ea_port=ea_port,
            mt5_login=mt5_login,
            mt5_password=mt5_password,
            mt5_server=mt5_server,
        )

        if activate:
            await self._deactivate_all(user_id)
            await self._unprimary_all(user_id)

        # Encrypt sensitive credentials. key_version records which KEK
        # version wrapped the ciphertext written below; it stays None
        # when the row carries no secret at all.
        encrypted_ea_token: Optional[str] = None
        if ea_auth_token and ea_auth_token.strip():
            encrypted_ea_token = _encrypt(ea_auth_token)

        encrypted_mt5_password: Optional[str] = None
        if mt5_password and mt5_password.strip():
            encrypted_mt5_password = _encrypt(mt5_password)

        # Both ciphertexts are freshly written under the active KEK here,
        # so this resolves to the active version when either secret is
        # present and None when neither is. Routed through the shared
        # helper so create() and update_connection() derive key_version
        # the same way.
        row_key_version: Optional[int] = self._effective_key_version(
            encrypted_mt5_password, encrypted_ea_token
        )

        # Validate any caller-supplied id up front so an invalid value
        # fails the request cleanly rather than at INSERT time.
        row_id: str
        if id is not None:
            try:
                from uuid import UUID as _UUIDValidate
                _UUIDValidate(str(id))
                row_id = str(id)
            except (ValueError, AttributeError, TypeError) as _id_exc:
                raise ValueError(
                    f"broker_connections.id must be a valid UUID; got {id!r}"
                ) from _id_exc
        else:
            row_id = str(uuid4())

        now = datetime.now(UTC)
        row = BrokerConnectionRow(
            id=row_id,
            user_id=user_id,
            connection_type=connection_type,
            name=name,
            ea_host=ea_host,
            ea_port=ea_port,
            ea_auth_token_encrypted=encrypted_ea_token,
            metaapi_account_id=metaapi_account_id,
            metaapi_region=metaapi_region,
            hosted_container_id=hosted_container_id,
            mt5_server=mt5_server,
            mt5_login=mt5_login,
            mt5_password_encrypted=encrypted_mt5_password,
            key_version=row_key_version,
            mt5_symbol=mt5_symbol,
            platform=platform,
            is_active=activate,
            is_primary=activate,
            status=status,
            status_message=status_message,
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
                "user_id": user_id,
                "type": connection_type,
                "name": name,
                "active": activate,
            },
        )
        return row

    # -- Read ------------------------------------------------------------------

    async def get_by_id(
        self,
        connection_id: str,
        user_id: str,
    ) -> Optional[BrokerConnectionRow]:
        """Return a single connection by ID, scoped to user."""
        stmt = select(BrokerConnectionRow).where(
            BrokerConnectionRow.id == connection_id,
            BrokerConnectionRow.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active(self, user_id: str) -> Optional[BrokerConnectionRow]:
        """Return the currently active broker connection for this user, or None."""
        stmt = (
            select(BrokerConnectionRow)
            .where(
                BrokerConnectionRow.user_id == user_id,
                BrokerConnectionRow.is_active.is_(True),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_primary(self, user_id: str) -> Optional[BrokerConnectionRow]:
        """Return the primary broker connection for this user, or None."""
        stmt = (
            select(BrokerConnectionRow)
            .where(
                BrokerConnectionRow.user_id == user_id,
                BrokerConnectionRow.is_primary.is_(True),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, user_id: str) -> list[BrokerConnectionRow]:
        """Return all broker connections for this user, ordered by most recent first."""
        stmt = (
            select(BrokerConnectionRow)
            .where(BrokerConnectionRow.user_id == user_id)
            .order_by(BrokerConnectionRow.updated_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -- Update ----------------------------------------------------------------

    async def update_connection(
        self,
        connection_id: str,
        user_id: str,
        *,
        name: Optional[str] = None,
        ea_host: Optional[str] = None,
        ea_port: Optional[int] = None,
        ea_auth_token: Optional[str] = None,
        metaapi_account_id: Optional[str] = None,
        metaapi_region: Optional[str] = None,
        hosted_container_id: Optional[str] = None,
        mt5_server: Optional[str] = None,
        mt5_login: Optional[str] = None,
        mt5_password: Optional[str] = None,
        mt5_symbol: Optional[str] = None,
        platform: Optional[str] = None,
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
                raise ValueError(f"ea_port must be 1024..65535, got {ea_port}")
            values["ea_port"] = ea_port
        if ea_auth_token is not None:
            values["ea_auth_token_encrypted"] = _encrypt(ea_auth_token)
            values["key_version"] = active_key_version()
        if metaapi_account_id is not None:
            values["metaapi_account_id"] = metaapi_account_id
        if metaapi_region is not None:
            values["metaapi_region"] = metaapi_region
        if hosted_container_id is not None:
            values["hosted_container_id"] = hosted_container_id
        if mt5_server is not None:
            values["mt5_server"] = mt5_server
        if mt5_login is not None:
            values["mt5_login"] = mt5_login
        if mt5_password is not None:
            values["mt5_password_encrypted"] = _encrypt(mt5_password)
            values["key_version"] = active_key_version()
        if mt5_symbol is not None:
            # Empty string is rejected upstream by the resolver; we only
            # arrive here with a non-empty stripped string when a
            # privileged caller wants to override the resolver's pick.
            values["mt5_symbol"] = mt5_symbol.strip()
        if platform is not None:
            values["platform"] = platform

        stmt = (
            update(BrokerConnectionRow)
            .where(
                BrokerConnectionRow.id == connection_id,
                BrokerConnectionRow.user_id == user_id,
            )
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id, user_id)

    async def update_chart_symbol(
        self,
        connection_id: str,
        *,
        chart_symbol: str,
    ) -> Optional[BrokerConnectionRow]:
        """Persist the chart-attach symbol picked by the provisioner.

        Called once per (re-)provision after BrokerSyncService has
        populated the broker_symbols catalog. user_id is intentionally
        omitted because the provisioner runs server-side without a user
        session; connection_id is sufficient and the call is internal.
        """
        values: dict = {
            "mt5_symbol": chart_symbol.strip(),
            "updated_at": datetime.now(UTC),
        }
        stmt = (
            update(BrokerConnectionRow)
            .where(BrokerConnectionRow.id == connection_id)
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.flush()
        result = await self._session.execute(
            select(BrokerConnectionRow).where(
                BrokerConnectionRow.id == connection_id,
            )
        )
        return result.scalar_one_or_none()

    # -- Activate / Deactivate / Set Primary -----------------------------------

    async def activate(self, connection_id: str, user_id: str) -> Optional[BrokerConnectionRow]:
        """Activate a connection (deactivates all others for this user)."""
        await self._deactivate_all(user_id)

        stmt = (
            update(BrokerConnectionRow)
            .where(
                BrokerConnectionRow.id == connection_id,
                BrokerConnectionRow.user_id == user_id,
            )
            .values(is_active=True, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id, user_id)

    async def deactivate(self, connection_id: str, user_id: str) -> Optional[BrokerConnectionRow]:
        """Deactivate a specific connection, scoped to user."""
        stmt = (
            update(BrokerConnectionRow)
            .where(
                BrokerConnectionRow.id == connection_id,
                BrokerConnectionRow.user_id == user_id,
            )
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id, user_id)

    async def set_primary(self, connection_id: str, user_id: str) -> Optional[BrokerConnectionRow]:
        """Set a connection as primary (unsets all others for this user).

        Also activates the connection if it is not already active.
        """
        await self._unprimary_all(user_id)
        await self._deactivate_all(user_id)

        stmt = (
            update(BrokerConnectionRow)
            .where(
                BrokerConnectionRow.id == connection_id,
                BrokerConnectionRow.user_id == user_id,
            )
            .values(
                is_primary=True,
                is_active=True,
                updated_at=datetime.now(UTC),
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id, user_id)

    # -- Health status ---------------------------------------------------------

    async def update_status(
        self,
        connection_id: str,
        user_id: str,
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
            .where(
                BrokerConnectionRow.id == connection_id,
                BrokerConnectionRow.user_id == user_id,
            )
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.flush()

        return await self.get_by_id(connection_id, user_id)

    # -- Delete ----------------------------------------------------------------

    async def delete(self, connection_id: str, user_id: str) -> bool:
        """Delete a connection by ID, scoped to user. Returns True if found and deleted."""
        row = await self.get_by_id(connection_id, user_id)
        if row is None:
            return False

        await self._session.delete(row)
        await self._session.flush()

        logger.info(
            "broker_connection_deleted",
            extra={
                "id": connection_id,
                "user_id": user_id,
                "type": row.connection_type,
                "name": row.name,
            },
        )
        return True

    # -- Internal helpers ------------------------------------------------------

    @staticmethod
    def _effective_key_version(*ciphertexts: Optional[str]) -> Optional[int]:
        """Truthful key_version for a row from its stored ciphertexts.

        broker_connections has two encrypted columns but a single
        key_version column, so the column must answer "is this row FULLY
        on the active KEK?". Given the ciphertext values that WILL be
        stored (None for an absent secret):

          - returns None when ANY non-null ciphertext is legacy / non-v2
            (no versioned wrap), so the re-wrap job still selects the
            row; otherwise
          - returns the MINIMUM KEK version across all non-null
            ciphertexts, so the row reads 'active' only when every secret
            it holds is wrapped under the active KEK.

        Returns None when the row carries no secret at all.
        """
        versions: list[int] = []
        for ciphertext in ciphertexts:
            if not ciphertext:
                continue  # absent secret -- does not constrain the version
            version = key_version_of(ciphertext)
            if version is None:
                # A legacy / non-v2 token is present: the row is not
                # fully on any versioned KEK.
                return None
            versions.append(version)
        if not versions:
            return None
        return min(versions)

    async def _deactivate_all(self, user_id: str) -> None:
        """Deactivate all connections for this user."""
        stmt = (
            update(BrokerConnectionRow)
            .where(
                BrokerConnectionRow.user_id == user_id,
                BrokerConnectionRow.is_active.is_(True),
            )
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)

    async def _unprimary_all(self, user_id: str) -> None:
        """Remove primary flag from all connections for this user."""
        stmt = (
            update(BrokerConnectionRow)
            .where(
                BrokerConnectionRow.user_id == user_id,
                BrokerConnectionRow.is_primary.is_(True),
            )
            .values(is_primary=False, updated_at=datetime.now(UTC))
        )
        await self._session.execute(stmt)
