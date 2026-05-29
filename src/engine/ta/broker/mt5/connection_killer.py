"""Kill-switch helper.

A single chokepoint to disable a broker connection when the engine
detects a divergence the operator must review (identity mismatch,
sustained clock skew, repeated authentication failure, etc.).

Three things happen on disable:
  1. broker_connections.active is flipped to false in the database
     so the factory will refuse to construct a client from this row
     on the next attempt.
  2. An audit log entry is written via the alert publisher (Redis
     pub/sub) so the gateway forwards a connection-disabled event
     to the dashboard for the user to see.
  3. The reason is logged with full context (provider, account_id,
     mismatched fields, kind of violation) so an operator running
     `kubectl logs` can diagnose without consulting Prometheus.

The function is async and accepts the uow factory + alert publisher
as injected dependencies so tests drive it without infrastructure.

Audit ref: CHECKLIST Section 4 'Kill-switch if EA diverges from
expected logic'.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Protocol

from engine.shared.logging import get_logger

logger = get_logger(__name__)


class _BrokerConnectionRepo(Protocol):
    """Narrow subset of the broker-connection repo we need."""

    async def disable_by_id(self, connection_id: str, *, reason: str) -> bool:
        ...


class _AlertPublisher(Protocol):
    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        ...


@dataclass(frozen=True)
class KillSwitchTrip:
    """Description of a kill-switch trigger."""

    connection_id: str
    provider: str
    account_id: str
    kind: str  # "identity_mismatch" | "clock_skew" | "auth_failure" | etc.
    reason: str
    details: dict[str, Any]


async def disable_connection(
    trip: KillSwitchTrip,
    *,
    repo: _BrokerConnectionRepo,
    alerts: Optional[_AlertPublisher] = None,
) -> bool:
    """Disable a broker connection. Returns True when the DB row was
    flipped (or already false); False on DB failure (the caller
    should NOT swallow this - it means the kill-switch did not
    actually fire).

    Idempotent: a connection that is already inactive does not
    re-publish the alert.
    """
    logger.error(
        "broker_connection_kill_switch_fired",
        extra={
            "connection_id": trip.connection_id,
            "provider": trip.provider,
            "account_id": trip.account_id,
            "kind": trip.kind,
            "reason": trip.reason,
            "details": trip.details,
        },
    )
    try:
        changed = await repo.disable_by_id(trip.connection_id, reason=trip.reason)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "broker_connection_disable_db_failed",
            extra={
                "connection_id": trip.connection_id,
                "error": str(exc),
            },
            exc_info=True,
        )
        return False

    if changed and alerts is not None:
        try:
            await alerts.publish(
                "etradie:alerts",
                {
                    "type": "broker_connection_disabled",
                    "connection_id": trip.connection_id,
                    "provider": trip.provider,
                    "account_id": trip.account_id,
                    "kind": trip.kind,
                    "reason": trip.reason,
                    "details": trip.details,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "broker_connection_disable_alert_failed",
                extra={
                    "connection_id": trip.connection_id,
                    "error": str(exc),
                },
            )
    return True
