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
import os

from fastapi import APIRouter, Depends, HTTPException, Request

from engine.dependencies import Container
from engine.helpers import _rate_limit
from engine.processor.storage.repositories.broker_connection_repository import (
    BrokerConnectionRepository,
    STATUS_CONNECTED,
    STATUS_ERROR,
    VALID_CONNECTION_TYPES,
    decrypt_credential,
)
from engine.schemas import CreateBrokerConnectionRequest, UpdateBrokerConnectionRequest
from engine.shared.auth import AuthenticatedUser, get_current_user
from engine.shared.logging import get_logger
from engine.ta.broker.mt5.factory import create_mt5_broker_from_connection
from engine.ta.broker.mt5.metaapi.provisioner import MetaApiProvisioner
from engine.ta.broker.mt5.hosted.provisioner import HostedProvisioner

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


def _serialize_broker_connection(row) -> dict:
    """Serialize a BrokerConnectionRow to a JSON-safe dict."""
    return {
        "id": str(row.id),
        "connection_type": row.connection_type,
        "name": row.name,
        "ea_host": row.ea_host,
        "ea_port": row.ea_port,
        "metaapi_account_id": row.metaapi_account_id,
        "metaapi_region": row.metaapi_region,
        "mt5_server": row.mt5_server,
        "mt5_login": row.mt5_login,
        "platform": getattr(row, "platform", "mt5"),
        "hosted_container_id": getattr(row, "hosted_container_id", None),
        "is_active": row.is_active,
        "is_primary": row.is_primary,
        "status": row.status,
        "status_message": row.status_message,
        "last_connected_at": (
            row.last_connected_at.isoformat() if row.last_connected_at else None
        ),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.post("/api/broker/connections")
async def create_broker_connection(
    request: Request,
    body: CreateBrokerConnectionRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
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
                    detail="MT5_METAAPI_TOKEN environment variable is not configured on the server."
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
                    detail=f"MetaAPI provisioning failed: {exc}"
                )

        elif body.connection_type == "hosted":
            # Provision a Dockerized headless MetaTrader container.
            if not body.mt5_login or not body.mt5_password or not body.mt5_server:
                raise HTTPException(
                    status_code=400,
                    detail="mt5_login, mt5_password, and mt5_server are required for Hosted connections",
                )

            from uuid import uuid4 as _uuid4
            temp_connection_id = str(_uuid4())

            try:
                provisioner = HostedProvisioner()
                hosted_result = await provisioner.provision_account(
                    connection_id=temp_connection_id,
                    login=body.mt5_login,
                    password=body.mt5_password,
                    server=body.mt5_server,
                    platform=body.platform,
                )
                hosted_container_id = hosted_result["container_id"]
                # For hosted connections, the Engine connects to the
                # Pod via ZeroMQ on the internal Kubernetes network.
                ea_host = hosted_result["zmq_host"]
                ea_port = hosted_result["zmq_port"]
            except Exception as exc:
                logger.error(
                    "hosted_provisioning_error_in_api",
                    extra={"error": str(exc)},
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Hosted provisioning failed: {exc}"
                )

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
                hosted_container_id=hosted_container_id
                    if body.connection_type == "hosted" else None,
                mt5_server=body.mt5_server,
                mt5_login=body.mt5_login,
                mt5_password=body.mt5_password,
                platform=body.platform,
                activate=body.activate,
            )
            result = _serialize_broker_connection(row)
            connection_id = str(row.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if body.activate:
        await container.invalidate_user_broker(user.user_id)

    result["message"] = (
        "Connection created and activated."
        if body.activate
        else "Connection created."
    )
    return result


@router.get("/api/broker/connections")
async def list_broker_connections(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
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
) -> dict:
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
) -> dict:
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
) -> dict:
    """Update an existing broker connection.

    Updates are saved to the database. The user's broker is resolved
    per-request from the DB, so the updated values take effect on
    the next trading operation automatically.
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

    await container.invalidate_user_broker(user.user_id)

    result = _serialize_broker_connection(row)
    result["message"] = "Connection updated."
    return result


@router.post("/api/broker/connections/{connection_id}/activate")
async def activate_broker_connection(
    request: Request,
    connection_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
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
) -> dict:
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
) -> dict:
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
) -> dict:
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

    # Decrypt credentials and create a temporary broker client.
    ea_auth_token = ""
    platform_token = ""
    if row.connection_type == "ea" and row.ea_auth_token_encrypted:
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
        # Update status in DB.
        async with container.db.session() as session:
            repo = BrokerConnectionRepository(session)
            await repo.update_status(
                connection_id,
                user_id=user.user_id,
                status=STATUS_ERROR,
                status_message=f"Failed to create client: {exc}",
            )
        return {
            "connection_id": connection_id,
            "healthy": False,
            "status": STATUS_ERROR,
            "message": f"Failed to create client: {exc}",
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
        try:
            await temp_client.shutdown()
        except Exception:
            pass

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
) -> dict:
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
            provisioner = HostedProvisioner()
            asyncio.create_task(provisioner.delete_account(hosted_container_id))
        except Exception as exc:
            logger.error("failed_to_start_hosted_cleanup", extra={"error": str(exc)})

    return {"deleted": True, "id": connection_id, "message": "Connection deleted."}
