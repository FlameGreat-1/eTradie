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
CONNECTION_TYPE_HOSTED = "hosted"
VALID_CONNECTION_TYPES = {CONNECTION_TYPE_EA, CONNECTION_TYPE_METAAPI, CONNECTION_TYPE_HOSTED}

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

    Reads BROKER_ENCRYPTION_KEY exclusively. No fallback chain to
    DATABASE_URL or hardcoded defaults — those patterns silently
    produce different keys across environments and make every
    existing ciphertext undecryptable after a legitimate key rotation.

    In production/staging, fails fast if the key is not set.
    In development, falls back to a well-known dev-only literal so
    docker-compose and pytest work without secrets management, but
    logs a loud warning so the gap is visible.

    The key is SHA-256 hashed to produce a URL-safe base64 Fernet key
    regardless of the raw value's length.
    """
    raw = os.environ.get("BROKER_ENCRYPTION_KEY", "").strip()
    if not raw:
        app_env = os.environ.get("APP_ENV", "development").lower()
        if app_env in ("production", "staging"):
            raise ValueError(
                "BROKER_ENCRYPTION_KEY is required in production/staging. "
                "Set it via the engine ExternalSecret "
                "(Vault path etradie/services/engine/<env>:broker_encryption_key)."
            )
        # Dev-only fallback. Loud warning so it is never missed.
        logger.warning(
            "broker_encryption_key_missing_using_dev_fallback",
            extra={
                "warning": (
                    "BROKER_ENCRYPTION_KEY is not set. Using the dev-only fallback. "
                    "DO NOT use this in production or staging."
                )
            },
        )
        raw = "etradie-dev-only-broker-key-do-not-use-in-production"
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
        mt5_symbol: str = "EURUSD",
        platform: str = "mt5",
        # Activation
        activate: bool = True,
        # Optional explicit row id. When supplied, the row is persisted with
        # this exact UUID instead of a freshly-generated one. The hosted path
        # uses this to make the broker_connections.id, the K8s release name
        # (etradie-mt-<id[:12]>), and the etradie.connection-id label on
        # every Kubernetes resource agree on a single identifier for the
        # entire lifecycle of the row. Must be a valid UUID string when set.
        # Audit ref: CHECKLIST Section 8 Step 2 (C1).
        id: Optional[str] = None,
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

        # Encrypt sensitive credentials.
        encrypted_ea_token: Optional[str] = None
        if ea_auth_token and ea_auth_token.strip():
            encrypted_ea_token = _encrypt(ea_auth_token)

        encrypted_mt5_password: Optional[str] = None
        if mt5_password and mt5_password.strip():
            encrypted_mt5_password = _encrypt(mt5_password)

        # Honor an explicit caller-supplied id so the hosted provisioning path
        # can pre-allocate the UUID and pass the same value to both the K8s
        # provisioner and the DB row. Anyone other than that path leaves id=None
        # and gets the legacy uuid4() behaviour. Validate the format up front so
        # an invalid string fails the request cleanly rather than at INSERT time.
        row_id: str
        if id is not None:
            try:
                # Round-trip through UUID to reject anything that isn't a
                # well-formed UUID; preserve the caller's exact string form.
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
            mt5_symbol=mt5_symbol,
            platform=platform,
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
