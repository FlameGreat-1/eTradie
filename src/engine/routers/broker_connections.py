"""Broker connection management endpoints (dashboard CRUD).

Routes:
    POST   /api/broker/connections
    GET    /api/broker/connections
    GET    /api/broker/connections/active
    GET    /api/broker/connections/{connection_id}
    PUT    /api/broker/connections/{connection_id}
    POST   /api/broker/connections/{connection_id}/activate
    POST   /api/broker/connections/{connection_id}/deactivate
    POST   /api/broker/connections/{connection_id}/set-primary
    POST   /api/broker/connections/{connection_id}/test
    DELETE /api/broker/connections/{connection_id}
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from engine.dependencies import Container
from engine.helpers import _rate_limit
from engine.processor.storage.repositories.broker_connection_repository import (
    STATUS_CONNECTED,
    STATUS_ERROR,
    VALID_CONNECTION_TYPES,
    BrokerConnectionRepository,
    decrypt_credential,
)
from engine.schemas import CreateBrokerConnectionRequest, UpdateBrokerConnectionRequest
from engine.shared.auth import AuthenticatedUser, get_current_user
from engine.shared.exceptions import ConfigurationError
from engine.shared.logging import get_logger
from engine.ta.broker.mt5.factory import create_mt5_broker_from_connection
from engine.ta.broker.mt5.hosted.provisioner import HostedProvisioner
from engine.ta.broker.mt5.metaapi.provisioner import MetaApiProvisioner

logger = get_logger(__name__)
router = APIRouter()


def _ea_connection_type_disabled() -> bool:
    """Hardcoded rejection of connection_type='ea' in production / staging.

    connection_type='ea' is a LOCAL-DEVELOPMENT-ONLY path that reads
    single-tenant MT5_ZMQ_HOST / MT5_ZMQ_PORT / MT5_ZMQ_AUTH_TOKEN env
    vars from the engine's own environment. Those env vars have no
    meaning in a multi-tenant deployment, so the router refuses to
    create 'ea' rows whenever APP_ENV identifies a non-dev environment.

    This is intentionally a hardcoded decision, not an env-var
    kill-switch: there is exactly one correct answer per environment
    and no legitimate reason to override it. An operator who wants to
    test 'ea' against staging should use a local docker-compose dev
    profile instead.
    """
    env = os.environ.get("APP_ENV", "").strip().lower()
    return env in ("production", "staging")


def _serialize_broker_connection(row) -> dict[str, Any]:
    """Serialize a BrokerConnectionRow to a JSON-safe dict.

    For hosted connections ea_host/ea_port hold the cluster-internal
    Kubernetes service DNS and ZMQ port, so they are nulled; for the 'ea'
    type they are the user's own VPS endpoint and are returned.
    hosted_container_id is an internal identifier and is never serialized.
    """
    is_hosted = row.connection_type == "hosted"
    return {
        "id": str(row.id),
        "connection_type": row.connection_type,
        "name": row.name,
        "ea_host": None if is_hosted else row.ea_host,
        "ea_port": None if is_hosted else row.ea_port,
        "metaapi_account_id": row.metaapi_account_id,
        "metaapi_region": row.metaapi_region,
        "broker_id": getattr(row, "broker_id", None),
        "broker_entity_id": getattr(row, "broker_entity_id", None),
        "mt5_server": row.mt5_server,
        "mt5_login": row.mt5_login,
        "mt5_symbol": getattr(row, "mt5_symbol", None),
        "platform": getattr(row, "platform", "mt5"),
        "is_active": row.is_active,
        "is_primary": row.is_primary,
        "status": row.status,
        "status_message": row.status_message,
        "last_connected_at": (row.last_connected_at.isoformat() if row.last_connected_at else None),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("/api/broker/connections")
async def create_broker_connection(
    request: Request,
    body: CreateBrokerConnectionRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new broker connection (EA or MetaAPI).

    User selects connection type, enters credentials, and saves.
    If activate=True (default), this becomes the active connection.
    The user's broker is resolved per-request from the database
    when they call trading endpoints (/internal/broker/*).
    """
    await _rate_limit(request, "broker_create", max_requests=10, window_seconds=60)
    container: Container = request.app.state.container

    if body.connection_type not in VALID_CONNECTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"connection_type must be one of {sorted(VALID_CONNECTION_TYPES)}",
        )

    # connection_type='ea' is a local-development-only escape hatch
    # (it reads single-tenant MT5_ZMQ_* env vars from the engine's own
    # environment). Production and staging always reject it at the
    # router; dev and the docker-compose self-hosted profile always
    # accept it. See _ea_connection_type_disabled() above.
    if body.connection_type == "ea" and _ea_connection_type_disabled():
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ea_connection_disabled",
                "message": (
                    "connection_type='ea' is a local-development path only "
                    "and is not available in production or staging "
                    "deployments. Use connection_type='hosted' or "
                    "connection_type='metaapi'."
                ),
            },
        )

    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="name must not be empty")

    try:
        # Prepare fields based on connection type
        ea_host = None
        ea_port = None
        ea_auth_token = None
        metaapi_account_id = None
        metaapi_region = None

        if body.connection_type == "ea":
            # Pull server-side EA config
            ea_host = os.environ.get("MT5_ZMQ_HOST", "host.docker.internal")
            try:
                ea_port = int(os.environ.get("MT5_ZMQ_PORT", "5555"))
            except ValueError:
                ea_port = 5555
            ea_auth_token = os.environ.get("MT5_ZMQ_AUTH_TOKEN", "")

        elif body.connection_type == "metaapi":
            # Provision cloud MT5 account dynamically
            if not body.mt5_login or not body.mt5_password or not body.mt5_server:
                raise HTTPException(
                    status_code=400,
                    detail="mt5_login, mt5_password, and mt5_server are required for MetaAPI connections",
                )

            platform_token = os.environ.get("MT5_METAAPI_TOKEN", "")
            if not platform_token:
                raise HTTPException(
                    status_code=500,
                    detail="MT5_METAAPI_TOKEN environment variable is not configured on the server.",
                )

            provisioner = MetaApiProvisioner(
                http_client=container.http_client,
                platform_token=platform_token,
                magic_number=container.mt5_config.magic_number,
                region=container.mt5_config.metaapi_region,
            )

            try:
                metaapi_result = await provisioner.provision_account(
                    login=body.mt5_login,
                    password=body.mt5_password,
                    server=body.mt5_server,
                    name=body.name,
                    platform=body.platform,
                )
                metaapi_account_id = metaapi_result["account_id"]
                metaapi_region = metaapi_result.get("region")
            except Exception as exc:
                logger.error(
                    "metaapi_provisioning_error_in_api",
                    extra={"error": str(exc)},
                )
                raise HTTPException(
                    status_code=400,
                    detail="Broker provisioning failed. Check the broker server, login and password and try again.",
                )

        elif body.connection_type == "hosted":
            # Provision a Dockerized headless MetaTrader container.
            if not body.mt5_login or not body.mt5_password or not body.mt5_server:
                raise HTTPException(
                    status_code=400,
                    detail="mt5_login, mt5_password, and mt5_server are required for Hosted connections",
                )
            if not body.broker_id or not body.entity_id:
                raise HTTPException(
                    status_code=400,
                    detail="broker_id and entity_id are required for Hosted connections",
                )

            try:
                _resolved = container.broker_registry.resolve(body.broker_id, body.entity_id, body.platform)
            except ConfigurationError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            # Bundle reachability fail-fast (audit defect #4 / #17).
            #
            # If the catalog points at a missing/wrong R2 object, the
            # initContainer would crashloop forever AFTER the DB row
            # is committed - the row sits in 'provisioning' and the
            # HostedRecoveryService keeps re-trying a permanently broken
            # download. HEAD-probe the URL BEFORE committing the row so
            # the user gets a clean 422 they can act on ("the operator
            # has not uploaded this bundle yet") instead of a five-minute
            # silent failure surfaced via the dashboard's status banner.
            #
            # 422 is the right code: the broker_id + entity_id ARE valid
            # (resolve() passed), but the platform-side bundle for that
            # entity is unreachable. The user cannot self-correct; the
            # message tells operations exactly what to fix.
            #
            # We use the shared engine HttpClient so retries / circuit
            # breaker / metrics are inherited; a single HEAD with a tight
            # timeout is cheap. A 200/3xx is success (R2 / CDN may serve
            # an HTTP redirect chain to the actual object).
            try:
                _probe = await container.http_client.head(
                    _resolved.bundle_r2_path,
                    timeout=10.0,
                    follow_redirects=True,
                )
                if _probe.status_code >= 400:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "broker_bundle_unreachable",
                            "message": (
                                f"The broker bundle for {body.broker_id}/{body.entity_id} "
                                f"({body.platform}) is not reachable (HTTP {_probe.status_code}). "
                                "This is a platform-side configuration error; "
                                "please contact support."
                            ),
                            "bundle_url": _resolved.bundle_r2_path,
                            "http_status": _probe.status_code,
                        },
                    )
            except HTTPException:
                raise
            except Exception as _probe_exc:
                # Network-level failure (DNS, connection refused, TLS).
                # Same posture as the 4xx branch: fail-fast so a bad
                # URL never becomes a stuck row.
                logger.error(
                    "broker_bundle_reachability_probe_failed",
                    extra={
                        "broker_id": body.broker_id,
                        "entity_id": body.entity_id,
                        "platform": body.platform,
                        "bundle_url": _resolved.bundle_r2_path,
                        "error": str(_probe_exc),
                        "error_type": type(_probe_exc).__name__,
                    },
                )
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "broker_bundle_unreachable",
                        "message": (
                            f"The broker bundle for {body.broker_id}/{body.entity_id} "
                            f"({body.platform}) could not be reached. "
                            "This is a platform-side configuration error; "
                            "please contact support."
                        ),
                        "bundle_url": _resolved.bundle_r2_path,
                    },
                )

            # Per-user hosted connection quota. Each hosted connection
            # consumes a dedicated K8s StatefulSet (2 CPU cores + 2 GiB
            # RAM in production). Without a quota, a single user could
            # exhaust cluster capacity by creating many hosted connections.
            # The limit is configurable via MT_NODE_MAX_HOSTED_PER_USER
            # (default 1: one hosted account per user; raise per-tenant
            # via the Helm production overlay for power users).
            max_hosted = int(os.environ.get("MT_NODE_MAX_HOSTED_PER_USER", "1"))
            async with container.db.read_session() as session:
                repo = BrokerConnectionRepository(session)
                existing = await repo.get_all(user_id=user.user_id)
            hosted_count = sum(1 for c in existing if c.connection_type == "hosted")
            if hosted_count >= max_hosted:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "hosted_quota_exceeded",
                        "message": (
                            f"You have reached the maximum of {max_hosted} hosted "
                            "MetaTrader connection(s). Delete an existing hosted "
                            "connection before creating a new one."
                        ),
                    },
                )

            # Allocate the connection_id ONCE and pass the same value to
            # both the K8s provisioner and the DB row so the StatefulSet
            # name, the etradie.connection-id label, and broker_connections.id
            # all agree. HostedRecoveryService and gc_orphans key on the
            # row id; any mismatch breaks recovery and GC silently.
            from uuid import uuid4 as _uuid4

            allocated_connection_id = str(_uuid4())

            hosted_provisioner: HostedProvisioner = container.hosted_provisioner

            # Predict the runtime details immediately so the DB row can be
            # created synchronously.
            release = hosted_provisioner._release_name(allocated_connection_id)
            hosted_container_id = release
            ea_host = f"{release}.{hosted_provisioner._namespace}.svc.cluster.local"
            # ZMQ port is always DEFAULT_ZMQ_PORT (5555) for hosted nodes.
            ea_port = 5555

            # Generate a secure token upfront.
            import secrets

            ea_auth_token = secrets.token_hex(32)

            # Fire-and-forget provisioning. The engine will not block on
            # the Pod boot. The background task updates the DB when done.
            async def run_hosted_provisioner(
                conn_id: str,
                user_id: str,
                login: str,
                password: str,
                server: str,
                platform: str,
                token: str,
            ) -> None:
                try:
                    await hosted_provisioner.provision_account(
                        connection_id=conn_id,
                        user_id=user_id,
                        brand_id=body.broker_id,
                        entity_id=body.entity_id,
                        login=login,
                        password=password,
                        server=server,
                        platform=platform,
                        per_user_zmq_token=token,
                    )
                    async with container.db.session() as bg_session:
                        repo = BrokerConnectionRepository(bg_session)
                        await repo.update_status(
                            conn_id,
                            user_id,
                            status="ready",
                            status_message="Provisioned successfully",
                            connected=True,
                        )
                except Exception as exc:
                    logger.error(
                        "hosted_provisioning_background_error",
                        extra={"error": str(exc), "connection_id": conn_id},
                    )
                    async with container.db.session() as bg_session:
                        repo = BrokerConnectionRepository(bg_session)
                        await repo.update_status(
                            conn_id,
                            user_id,
                            status="failed",
                            status_message=f"Provisioning failed: {exc}",
                        )

            background_tasks.add_task(
                run_hosted_provisioner,
                conn_id=allocated_connection_id,
                user_id=user.user_id,
                login=body.mt5_login,
                password=body.mt5_password,
                server=body.mt5_server,
                platform=body.platform,
                token=ea_auth_token,
            )

        # Pin the row id to the pre-allocated connection_id for hosted
        # rows so the persisted id equals the K8s release suffix. Other
        # connection types let the repository allocate as before.
        _row_id_override = allocated_connection_id if body.connection_type == "hosted" else None
        async with container.db.session() as session:
            repo = BrokerConnectionRepository(session)
            row = await repo.create(
                user_id=user.user_id,
                connection_type=body.connection_type,
                name=body.name.strip(),
                ea_host=ea_host,
                ea_port=ea_port,
                ea_auth_token=ea_auth_token,
                metaapi_account_id=metaapi_account_id,
                metaapi_region=metaapi_region,
                hosted_container_id=(hosted_container_id if body.connection_type == "hosted" else None),
                broker_id=body.broker_id if body.connection_type == "hosted" else None,
                broker_entity_id=body.entity_id if body.connection_type == "hosted" else None,
                mt5_server=body.mt5_server,
                mt5_login=body.mt5_login,
                mt5_password=body.mt5_password,
                platform=body.platform,
                activate=body.activate,
                id=_row_id_override,
                status=("provisioning" if body.connection_type == "hosted" else "untested"),
                status_message=(
                    "Connecting to your broker... This may take up to 3 minutes."
                    if body.connection_type == "hosted"
                    else ""
                ),
            )
            result = _serialize_broker_connection(row)
            str(row.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if body.activate:
        await container.invalidate_user_broker(user.user_id)

    result["message"] = "Connection created and activated." if body.activate else "Connection created."
    return result


@router.get("/api/broker/connections")
async def list_broker_connections(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all saved broker connections."""
    container: Container = request.app.state.container

    async with container.db.read_session() as session:
        repo = BrokerConnectionRepository(session)
        rows = await repo.get_all(user_id=user.user_id)

    connections = [_serialize_broker_connection(row) for row in rows]
    return {"connections": connections, "count": len(connections)}


@router.get("/api/broker/connections/active")
async def get_active_broker_connection(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the currently active broker connection."""
    container: Container = request.app.state.container

    async with container.db.read_session() as session:
        repo = BrokerConnectionRepository(session)
        row = await repo.get_active(user_id=user.user_id)

    if row is None:
        return {
            "connection": None,
            "broker_configured": False,
            "message": "No active broker connection. Please set up a connection via the dashboard.",
        }

    return {
        "connection": _serialize_broker_connection(row),
        "broker_configured": True,
    }


@router.get("/api/broker/connections/{connection_id}")
async def get_broker_connection(
    request: Request,
    connection_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific broker connection by ID."""
    container: Container = request.app.state.container

    async with container.db.read_session() as session:
        repo = BrokerConnectionRepository(session)
        row = await repo.get_by_id(connection_id, user_id=user.user_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    return {"connection": _serialize_broker_connection(row)}


@router.put("/api/broker/connections/{connection_id}")
async def update_broker_connection(
    request: Request,
    connection_id: str,
    body: UpdateBrokerConnectionRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Update an existing broker connection.

    Updates are saved to the database. The user's broker is resolved
    per-request from the DB, so the updated values take effect on
    the next trading operation automatically.

    For hosted connections where mt5_password is changed, the per-tenant
    Kubernetes Secret is re-sealed immediately so the mt-node Pod picks
    up the new password on its next restart. Without this, the DB row
    would have the new password but the K8s Secret would retain the old
    one, causing the EA to fail broker authentication after any Pod
    restart until the HostedRecoveryService re-provisions the connection
    (up to ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS = 10 min).
    """
    container: Container = request.app.state.container

    try:
        async with container.db.session() as session:
            repo = BrokerConnectionRepository(session)
            row = await repo.update_connection(
                connection_id,
                user_id=user.user_id,
                name=body.name,
                mt5_server=body.mt5_server,
                mt5_login=body.mt5_login,
                mt5_password=body.mt5_password,
                platform=body.platform,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if row is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    # For hosted connections where credentials changed, re-seal the
    # per-tenant K8s Secret so the mt-node Pod picks up the new
    # password on its next restart. This is a best-effort operation:
    # if it fails, the HostedRecoveryService will re-provision the
    # connection on its next sweep, but the user may see up to
    # ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS of downtime.
    if row.connection_type == "hosted" and row.hosted_container_id and body.mt5_password is not None:
        # broker_id + broker_entity_id are REQUIRED by provision_account
        # so it can resolve the broker bundle. A row that pre-dates
        # migration 0034 has NULL on these columns; passing an empty
        # string would crash registry.resolve(). Skip the re-seal in
        # that case with a clear log; HostedRecoveryService converges
        # the Pod on its next sweep (and also skips with the same
        # guard until the user re-creates the connection).
        _brand_id = (getattr(row, "broker_id", None) or "").strip()
        _entity_id = (getattr(row, "broker_entity_id", None) or "").strip()
        if not _brand_id or not _entity_id:
            logger.warning(
                "hosted_password_rotation_skipped_missing_broker_identity",
                extra={
                    "connection_id": connection_id,
                    "user_id": user.user_id,
                    "has_broker_id": bool(_brand_id),
                    "has_broker_entity_id": bool(_entity_id),
                    "hint": (
                        "Hosted row pre-dates migration 0034; re-create the connection "
                        "via the dashboard to populate broker_id/broker_entity_id so "
                        "password rotation can re-seal the per-tenant Secret."
                    ),
                },
            )
        else:
            try:
                provisioner = container.hosted_provisioner
                ea_auth_token = ""  # nosec B105
                if row.ea_auth_token_encrypted:
                    ea_auth_token = decrypt_credential(row.ea_auth_token_encrypted)
                password_plain = decrypt_credential(row.mt5_password_encrypted) if row.mt5_password_encrypted else ""
                # Preserve the previously-resolved chart-attach symbol so
                # a password-rotation triggered re-provision does not
                # silently change the user's mt5_symbol. Same H-4 guard
                # as HostedRecoveryService._reprovision.
                existing_symbol = None
                if getattr(row, "mt5_symbol", None):
                    _stripped = str(row.mt5_symbol).strip()
                    if _stripped:
                        existing_symbol = _stripped

                await provisioner.provision_account(
                    connection_id=connection_id,
                    user_id=user.user_id,
                    brand_id=_brand_id,
                    entity_id=_entity_id,
                    login=row.mt5_login or "",
                    password=password_plain,
                    server=row.mt5_server or "",
                    platform=row.platform or "mt5",
                    per_user_zmq_token=ea_auth_token or None,
                    existing_chart_symbol=existing_symbol,
                )
                # provision_account() also re-runs symbol resolution on
                # the new credentials and persists the refreshed map, so
                # no extra call is needed here.
                logger.info(
                    "hosted_credentials_rotated_after_password_update",
                    extra={"connection_id": connection_id, "user_id": user.user_id},
                )
            except Exception as exc:
                # Non-fatal: log and continue. HostedRecoveryService
                # will converge the Pod state on its next sweep.
                logger.error(
                    "hosted_credentials_rotation_failed_after_password_update",
                    extra={"connection_id": connection_id, "error": str(exc)},
                )

    await container.invalidate_user_broker(user.user_id)

    result = _serialize_broker_connection(row)
    result["message"] = "Connection updated."
    return result


@router.post("/api/broker/connections/{connection_id}/activate")
async def activate_broker_connection(
    request: Request,
    connection_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Activate a broker connection.

    Deactivates all other connections for this user and marks
    this one as active. The user's broker is resolved per-request
    from the database when they call trading endpoints.
    """
    container: Container = request.app.state.container

    async with container.db.session() as session:
        repo = BrokerConnectionRepository(session)
        row = await repo.activate(connection_id, user_id=user.user_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    await container.invalidate_user_broker(user.user_id)

    result = _serialize_broker_connection(row)
    result["message"] = f"Connection activated. Broker now using {row.name}."
    return result


@router.post("/api/broker/connections/{connection_id}/deactivate")
async def deactivate_broker_connection(
    request: Request,
    connection_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Deactivate a broker connection without deleting it."""
    container: Container = request.app.state.container

    async with container.db.session() as session:
        repo = BrokerConnectionRepository(session)
        row = await repo.deactivate(connection_id, user_id=user.user_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    await container.invalidate_user_broker(user.user_id)

    result = _serialize_broker_connection(row)
    result["message"] = "Connection deactivated."
    return result


@router.post("/api/broker/connections/{connection_id}/set-primary")
async def set_primary_broker_connection(
    request: Request,
    connection_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Set a connection as primary (also activates it).

    The user's broker is resolved per-request from the database
    when they call trading endpoints.
    """
    container: Container = request.app.state.container

    async with container.db.session() as session:
        repo = BrokerConnectionRepository(session)
        row = await repo.set_primary(connection_id, user_id=user.user_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    await container.invalidate_user_broker(user.user_id)

    result = _serialize_broker_connection(row)
    result["message"] = f"Connection set as primary. Broker now using {row.name}."
    return result


@router.post("/api/broker/connections/{connection_id}/test")
async def test_broker_connection(
    request: Request,
    connection_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Test a broker connection's health.
    Rate limited to prevent flooding the broker with health checks.

    Creates a temporary broker client from the connection's credentials,
    runs a health check, and updates the connection's status in the DB.
    Does NOT activate the connection or change the active broker.
    """
    await _rate_limit(request, "broker_test", max_requests=5, window_seconds=60)
    container: Container = request.app.state.container

    async with container.db.read_session() as session:
        repo = BrokerConnectionRepository(session)
        row = await repo.get_by_id(connection_id, user_id=user.user_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Decrypt credentials and create a temporary broker client. Both
    # 'ea' and 'hosted' store a per-connection token in
    # ea_auth_token_encrypted (hosted = the per-tenant ZMQ token from
    # provision time), and create_mt5_broker_from_connection() requires
    # it non-empty for the hosted ZmqClient build, so decrypt it for
    # both. MetaAPI uses the platform token from env, never a per-row one.
    ea_auth_token = ""  # nosec B105
    platform_token = ""  # nosec B105
    if row.connection_type in ("ea", "hosted") and row.ea_auth_token_encrypted:
        ea_auth_token = decrypt_credential(row.ea_auth_token_encrypted)
    if row.connection_type == "metaapi":
        platform_token = os.environ.get("MT5_METAAPI_TOKEN", "")

    try:
        temp_client = create_mt5_broker_from_connection(
            row=row,
            http_client=container.http_client,
            ea_auth_token=ea_auth_token,
            platform_token=platform_token,
        )
    except Exception as exc:
        # The raw cause is logged for operators; the persisted
        # status_message is re-served on every later fetch, so keep it
        # generic.
        logger.error(
            "broker_test_create_client_failed",
            extra={"connection_id": connection_id, "error": str(exc)},
        )
        generic_msg = "Could not establish a broker client. Check the connection's credentials and try again."
        async with container.db.session() as session:
            repo = BrokerConnectionRepository(session)
            await repo.update_status(
                connection_id,
                user_id=user.user_id,
                status=STATUS_ERROR,
                status_message=generic_msg,
            )
        return {
            "connection_id": connection_id,
            "healthy": False,
            "status": STATUS_ERROR,
            "message": generic_msg,
        }

    # Run health check.
    try:
        healthy = await temp_client.health_check()
    except Exception as exc:
        healthy = False
        logger.error(
            "broker_test_health_check_failed",
            extra={"connection_id": connection_id, "error": str(exc)},
        )
    finally:
        with contextlib.suppress(Exception):
            await temp_client.shutdown()

    # Update status in DB.
    new_status = STATUS_CONNECTED if healthy else STATUS_ERROR
    status_msg = "Connection successful" if healthy else "Health check failed"

    async with container.db.session() as session:
        repo = BrokerConnectionRepository(session)
        await repo.update_status(
            connection_id,
            user_id=user.user_id,
            status=new_status,
            status_message=status_msg,
            connected=healthy,
        )

    return {
        "connection_id": connection_id,
        "healthy": healthy,
        "status": new_status,
        "message": status_msg,
    }


@router.delete("/api/broker/connections/{connection_id}")
async def delete_broker_connection(
    request: Request,
    connection_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Permanently delete a saved broker connection."""
    container: Container = request.app.state.container

    async with container.db.read_session() as session:
        repo = BrokerConnectionRepository(session)
        row = await repo.get_by_id(connection_id, user_id=user.user_id)

    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")

    is_metaapi = row.connection_type == "metaapi"
    metaapi_account_id = row.metaapi_account_id
    is_hosted = row.connection_type == "hosted"
    hosted_container_id = row.hosted_container_id

    async with container.db.session() as session:
        repo = BrokerConnectionRepository(session)
        deleted = await repo.delete(connection_id, user_id=user.user_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Connection not found")

    await container.invalidate_user_broker(user.user_id)

    # Clean up cloud/docker resources asynchronously after DB deletion
    if is_metaapi and metaapi_account_id:
        platform_token = os.environ.get("MT5_METAAPI_TOKEN", "")
        if platform_token:
            try:
                provisioner = MetaApiProvisioner(
                    http_client=container.http_client,
                    platform_token=platform_token,
                    magic_number=container.mt5_config.magic_number,
                    region=container.mt5_config.metaapi_region,
                )
                # Background task to avoid blocking the user API response
                asyncio.create_task(provisioner.cleanup_account(metaapi_account_id))
            except Exception as exc:
                logger.error("failed_to_start_metaapi_cleanup", extra={"error": str(exc)})
    elif is_hosted and hosted_container_id:
        try:
            provisioner = container.hosted_provisioner
            asyncio.create_task(provisioner.delete_account(hosted_container_id))
        except Exception as exc:
            logger.error("failed_to_start_hosted_cleanup", extra={"error": str(exc)})

    return {"deleted": True, "id": connection_id, "message": "Connection deleted."}


@router.get("/api/broker/registry")
async def list_broker_registry(request: Request) -> dict[str, Any]:
    """List active brokers from the catalog registry for the dashboard setup wizard."""
    container: Container = request.app.state.container
    brands = container.broker_registry.list_active()
    return {"brands": [b.model_dump() for b in brands]}
