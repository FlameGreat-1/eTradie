"""Hosted MT-node Failure Recovery Service.

Audit ref: CHECKLIST Section 8 - 'Full system restart recovery',
'Partial system recovery', 'No manual repair required for normal
failures'.

This service runs inside the engine pod and continuously enforces the
invariant:

  For every broker_connections row where is_active=true AND
  connection_type='hosted', there MUST be a healthy K8s StatefulSet
  named 'etradie-mt-<connection_id[:12]>' in the mt-node namespace
  with at least one Ready replica.

The K8s StatefulSet controller + the in-pod entrypoint + the watchdog
sidecar handle Pod-level crashes already. This service handles the
ORTHOGONAL failure modes:

  1. The StatefulSet itself is missing (operator kubectl delete,
     ArgoCD prune, namespace wipe). The Pod-level controllers cannot
     heal this because there is no controller for them to run inside.

  2. The StatefulSet exists but has been Pending / not-Ready for so
     long that the kubelet's exponential restart backoff (capped at
     5m) is no longer making meaningful progress. The recovery
     service replaces the StatefulSet by re-running
     HostedProvisioner.provision_account() which is idempotent.

Design invariants
-----------------
- The service NEVER mutates the broker_connections row itself.
- Re-provision is idempotent: HostedProvisioner.provision_account()
  upserts the Secret + StatefulSet + Services, waits for Ready +
  ZMQ PING.
- The recovery loop is decoupled from the FastAPI request path. It
  runs under BackgroundTaskCoordinator so engine shutdown drains it
  cleanly.
- A per-connection cooldown prevents stampeding a permanently broken
  connection. The cooldown is in-memory only (intentional - on
  engine restart the cooldown resets, which is the desired behavior
  for the eager startup sweep).
- All four metrics are bounded-cardinality (see prometheus.py
  comments). Per-connection detail goes to structured logs.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from engine.processor.storage.repositories.broker_connection_repository import (
    CONNECTION_TYPE_HOSTED,
    decrypt_credential,
)
from engine.processor.storage.schemas.broker_connection_schema import (
    BrokerConnectionRow,
)
from engine.shared.exceptions import (
    ConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    HOSTED_RECOVERY_LAST_RUN_TS,
    HOSTED_RECOVERY_PODS_UNHEALTHY,
    HOSTED_RECOVERY_REPROVISIONS_TOTAL,
    HOSTED_RECOVERY_RUNS_TOTAL,
)
from engine.ta.broker.mt5.hosted.provisioner import HostedProvisioner

logger = get_logger(__name__)


@dataclass(frozen=True)
class HostedRecoveryConfig:
    """Immutable configuration read once at construction time.

    All fields validated by __post_init__ analogue (Python frozen
    dataclasses cannot define __post_init__ that mutates self, so the
    classmethod from_env() does the validation and returns the
    frozen instance).
    """

    enabled: bool
    sweep_interval_secs: float
    unhealthy_threshold_secs: float
    reprovision_cooldown_secs: float
    # Caps concurrent reprovision calls inside one sweep so a cluster-
    # wide outage does not issue N parallel readiness gates against the
    # kube-apiserver. Status checks remain unbounded. Defaults to 4 to
    # match from_env()'s ENGINE_HOSTED_RECOVERY_MAX_CONCURRENT fallback
    # so direct constructors stay backward-compatible.
    max_concurrent_reprovisions: int = 4

    @classmethod
    def from_env(cls) -> HostedRecoveryConfig:
        """Construct from process env. Bounds-checks every numeric.

        Env var names mirror helm/engine/templates/configmap.yaml so
        an operator can tune the loop without code changes.
        """
        enabled = os.environ.get("ENGINE_HOSTED_RECOVERY_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")

        def _pos_float(name: str, default: str, minimum: float) -> float:
            raw = (os.environ.get(name, default) or default).strip()
            try:
                value = float(raw)
            except ValueError as exc:
                raise ConfigurationError(
                    f"{name} must be a number",
                    details={"env_var": name, "value": raw, "error": str(exc)},
                ) from exc
            if value < minimum:
                raise ConfigurationError(
                    f"{name} must be >= {minimum} (got {value})",
                    details={"env_var": name, "value": value, "minimum": minimum},
                )
            return value

        def _pos_int(name: str, default: str, minimum: int) -> int:
            raw = (os.environ.get(name, default) or default).strip()
            try:
                value = int(raw)
            except ValueError as exc:
                raise ConfigurationError(
                    f"{name} must be an int",
                    details={"env_var": name, "value": raw, "error": str(exc)},
                ) from exc
            if value < minimum:
                raise ConfigurationError(
                    f"{name} must be >= {minimum} (got {value})",
                    details={"env_var": name, "value": value, "minimum": minimum},
                )
            return value

        return cls(
            enabled=enabled,
            sweep_interval_secs=_pos_float("ENGINE_HOSTED_RECOVERY_SWEEP_INTERVAL_SECS", "60", 5.0),
            unhealthy_threshold_secs=_pos_float("ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS", "600", 30.0),
            reprovision_cooldown_secs=_pos_float("ENGINE_HOSTED_RECOVERY_REPROVISION_COOLDOWN_SECS", "300", 30.0),
            max_concurrent_reprovisions=_pos_int("ENGINE_HOSTED_RECOVERY_MAX_CONCURRENT", "4", 1),
        )


class HostedRecoveryService:
    """Background service that heals missing or unhealthy hosted mt-node Pods.

    Wiring (see engine.dependencies.Container):
      container.hosted_recovery_service = HostedRecoveryService(
          provisioner=HostedProvisioner(...),
          db=container.db,
          config=HostedRecoveryConfig.from_env(),
      )

    Lifecycle (see engine.main.lifespan):
      await container.hosted_recovery_service.run_once_at_startup()
      container.hosted_recovery_service.start_background_loop(
          coordinator=container.background_tasks,
      )

    The startup sweep is awaited synchronously so FastAPI does not
    start accepting traffic until every hosted connection has been
    verified (or scheduled for retry on the background loop).

    Thread-safety: the service is single-threaded by asyncio. All
    state lives on the instance; no external locking is required.
    """

    def __init__(
        self,
        *,
        provisioner: HostedProvisioner,
        db: Any,  # engine.shared.db.DatabaseManager, untyped here to avoid an import cycle
        config: HostedRecoveryConfig,
    ) -> None:
        self._provisioner = provisioner
        self._db = db
        self._config = config
        # Per-connection cooldown: connection_id -> last-attempt monotonic ts.
        self._last_reprovision: dict[str, float] = {}
        # Per-connection 'first observed unhealthy' monotonic ts. The
        # service waits at least unhealthy_threshold_secs before
        # treating a not-Ready StatefulSet as actionable.
        self._first_unhealthy: dict[str, float] = {}
        # Bounds the number of in-flight reprovision calls inside one
        # sweep. Sized at construction from the config so a misconfig
        # surfaces at engine boot rather than at the first incident.
        self._reprovision_gate = asyncio.Semaphore(
            self._config.max_concurrent_reprovisions,
        )
        self._task: asyncio.Task | None = None
        self._stopped = False

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    # ---- Lifecycle -----------------------------------------------------

    async def run_once_at_startup(self) -> dict[str, int]:
        """Eager sweep called from lifespan before yield.

        Differs from the background sweep in two ways:
          1. The unhealthy_threshold is bypassed: every missing or
             not-Ready StatefulSet is reprovisioned immediately. This
             is what 'Full system restart recovery' means - on engine
             pod restart, we have just lost up to N minutes of
             liveness signal so we cannot afford to wait another
             10 minutes to decide.
          2. The cooldown table is fresh (empty) so the first attempt
             always fires.

        Returns a small dict of counts for the caller to log.
        """
        if not self._config.enabled:
            logger.info("hosted_recovery_disabled", extra={"phase": "startup"})
            HOSTED_RECOVERY_RUNS_TOTAL.labels(outcome="skipped").inc()
            return {"scanned": 0, "reprovisioned": 0, "failed": 0}
        return await self._sweep(phase="startup", bypass_threshold=True)

    def start_background_loop(self, *, coordinator: Any) -> None:
        """Register the periodic sweep with BackgroundTaskCoordinator.

        coordinator is engine.shared.concurrency.BackgroundTaskCoordinator;
        passed untyped to avoid an import cycle with dependencies.py.
        Idempotent: a second call is a no-op once the task is running.
        """
        if not self._config.enabled:
            logger.info("hosted_recovery_disabled", extra={"phase": "background"})
            return
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(
            self._loop(),
            name="hosted-recovery-sweep",
        )
        logger.info(
            "hosted_recovery_background_loop_started",
            extra={
                "sweep_interval_secs": self._config.sweep_interval_secs,
                "unhealthy_threshold_secs": self._config.unhealthy_threshold_secs,
                "reprovision_cooldown_secs": self._config.reprovision_cooldown_secs,
            },
        )

    async def stop(self) -> None:
        """Idempotent stop. Called by Container.shutdown()
        (background_tasks.shutdown() actually cancels the task; this
        method exists for explicit-stop call sites and tests).
        """
        self._stopped = True
        task = self._task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        self._task = None

    # ---- Loop ----------------------------------------------------------

    async def _loop(self) -> None:
        """Periodic sweep loop. Exits cleanly on CancelledError."""
        try:
            while not self._stopped:
                try:
                    await self._sweep(phase="periodic", bypass_threshold=False)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    # NEVER let a sweep failure kill the loop. Log,
                    # increment the error counter, and wait until the
                    # next tick.
                    HOSTED_RECOVERY_RUNS_TOTAL.labels(outcome="error").inc()
                    logger.error(
                        "hosted_recovery_sweep_failed",
                        extra={"error": str(exc), "error_type": type(exc).__name__},
                    )
                await asyncio.sleep(self._config.sweep_interval_secs)
        except asyncio.CancelledError:
            logger.info("hosted_recovery_loop_cancelled")
            return

    # ---- Core sweep ----------------------------------------------------

    async def _sweep(self, *, phase: str, bypass_threshold: bool) -> dict[str, int]:
        """One pass over every active hosted broker_connections row."""
        rows = await self._list_active_hosted_rows()
        scanned = len(rows)
        reprovisioned = 0
        failed = 0
        unhealthy_now = 0

        now_mono = time.monotonic()

        for row in rows:
            connection_id = str(row.id)
            user_id = row.user_id
            release = self._provisioner._release_name(connection_id)  # mirror chart's release name

            try:
                status = await self._provisioner.get_account_status(release)
            except Exception as exc:  # noqa: BLE001
                # K8s API is unreachable. Record but do not retry this
                # row in the current sweep - the next sweep will pick
                # it up. Do NOT count this as an unhealthy connection
                # (the StatefulSet may be perfectly fine).
                logger.warning(
                    "hosted_recovery_status_check_failed",
                    extra={
                        "connection_id": connection_id,
                        "user_id": user_id,
                        "release": release,
                        "error": str(exc),
                    },
                )
                continue

            running = bool(status.get("running", False))
            sts_status = str(status.get("status", "unknown"))

            if running:
                # Healthy. Clear any first-unhealthy timestamp; do NOT
                # clear the cooldown timestamp because that one is for
                # the reprovision back-off (a flapping connection
                # should still respect the cooldown).
                self._first_unhealthy.pop(connection_id, None)
                continue

            unhealthy_now += 1

            # Decide the reason and whether we are allowed to act.
            reason = "missing" if sts_status == "removed" else "unhealthy"

            # First-observed-unhealthy bookkeeping.
            first_seen = self._first_unhealthy.setdefault(connection_id, now_mono)
            age_secs = now_mono - first_seen

            if not bypass_threshold and reason == "unhealthy":
                if age_secs < self._config.unhealthy_threshold_secs:
                    # Still inside the kubelet's normal backoff envelope.
                    logger.info(
                        "hosted_recovery_unhealthy_below_threshold",
                        extra={
                            "connection_id": connection_id,
                            "user_id": user_id,
                            "release": release,
                            "status": sts_status,
                            "age_secs": round(age_secs, 1),
                            "threshold_secs": self._config.unhealthy_threshold_secs,
                        },
                    )
                    continue

            # Cooldown check.
            last_attempt = self._last_reprovision.get(connection_id)
            if last_attempt is not None:
                since = now_mono - last_attempt
                if since < self._config.reprovision_cooldown_secs:
                    logger.info(
                        "hosted_recovery_cooldown_active",
                        extra={
                            "connection_id": connection_id,
                            "user_id": user_id,
                            "release": release,
                            "since_last_attempt_secs": round(since, 1),
                            "cooldown_secs": self._config.reprovision_cooldown_secs,
                        },
                    )
                    continue

            # The cooldown gate above this point already filtered out
            # connections still inside their back-off window, so the
            # semaphore acquire here only competes with rows that are
            # genuinely ready to be reprovisioned.
            async with self._reprovision_gate:
                self._last_reprovision[connection_id] = time.monotonic()
                HOSTED_RECOVERY_REPROVISIONS_TOTAL.labels(reason=reason).inc()
                try:
                    await self._reprovision(row=row, reason=reason, phase=phase)
                    reprovisioned += 1
                    # Reset the first-unhealthy timestamp so a future
                    # failure starts a fresh threshold window.
                    self._first_unhealthy.pop(connection_id, None)
                except (
                    ConfigurationError,
                    ProviderError,
                    ProviderTimeoutError,
                    ProviderUnavailableError,
                ) as exc:
                    failed += 1
                    logger.error(
                        "hosted_recovery_reprovision_failed",
                        extra={
                            "connection_id": connection_id,
                            "user_id": user_id,
                            "release": release,
                            "reason": reason,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    logger.error(
                        "hosted_recovery_reprovision_unexpected",
                        extra={
                            "connection_id": connection_id,
                            "user_id": user_id,
                            "release": release,
                            "reason": reason,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )

        # Metrics + summary.
        HOSTED_RECOVERY_PODS_UNHEALTHY.set(unhealthy_now)
        HOSTED_RECOVERY_LAST_RUN_TS.set(time.time())
        outcome = "ok" if failed == 0 else ("partial" if reprovisioned > 0 else "error")
        HOSTED_RECOVERY_RUNS_TOTAL.labels(outcome=outcome).inc()
        logger.info(
            "hosted_recovery_sweep_complete",
            extra={
                "phase": phase,
                "scanned": scanned,
                "unhealthy": unhealthy_now,
                "reprovisioned": reprovisioned,
                "failed": failed,
                "outcome": outcome,
            },
        )
        return {"scanned": scanned, "reprovisioned": reprovisioned, "failed": failed}

    # ---- Internal helpers ---------------------------------------------

    async def _list_active_hosted_rows(self) -> list[BrokerConnectionRow]:
        """Return every active row with connection_type='hosted'.

        The query is bounded by `is_active=true AND connection_type='hosted'`.
        Both columns are indexed; on a 100-tenant cluster this is
        a single index scan over a handful of rows.
        """
        try:
            async with self._db.read_session() as session:
                stmt = select(BrokerConnectionRow).where(
                    BrokerConnectionRow.is_active.is_(True),
                    BrokerConnectionRow.connection_type == CONNECTION_TYPE_HOSTED,
                )
                result = await session.execute(stmt)
                return list(result.scalars().all())
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "hosted_recovery_db_query_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            return []

    async def _reprovision(
        self,
        *,
        row: BrokerConnectionRow,
        reason: str,
        phase: str,
    ) -> None:
        """Call HostedProvisioner.provision_account() with the row's data.

        The provisioner is idempotent: it upserts the Secret, the
        StatefulSet, both Services, and waits for Ready + ZMQ PING.
        For a 'missing' row it creates everything from scratch; for
        an 'unhealthy' row it replaces the StatefulSet spec and the
        readiness gate verifies the new Pod comes up.
        """
        connection_id = str(row.id)
        user_id = row.user_id

        if not row.mt5_server or not row.mt5_login or not row.mt5_password_encrypted:
            raise ConfigurationError(
                "hosted broker_connections row missing mt5_server/mt5_login/mt5_password_encrypted",
                details={
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "has_server": bool(row.mt5_server),
                    "has_login": bool(row.mt5_login),
                    "has_password": bool(row.mt5_password_encrypted),
                },
            )

        password = decrypt_credential(row.mt5_password_encrypted)

        # Forward the existing per-tenant ZMQ auth token so the
        # provisioner re-seals the SAME secret in Vault. Without this,
        # provision_account() would generate a fresh token and the
        # engine's ZmqClient would keep authenticating with the stale
        # token stored in broker_connections.ea_auth_token_encrypted -
        # the Pod would look healthy but every command would fail.
        existing_token: str | None = None
        if row.ea_auth_token_encrypted:
            existing_token = decrypt_credential(row.ea_auth_token_encrypted)

        logger.info(
            "hosted_recovery_reprovision_starting",
            extra={
                "connection_id": connection_id,
                "user_id": user_id,
                "reason": reason,
                "phase": phase,
                "platform": row.platform,
                "server": row.mt5_server,
                "token_propagated": existing_token is not None,
            },
        )

        # Preserve the previously-resolved chart-attach symbol so a
        # broker-side Market Watch reshuffle does not silently change
        # the user's mt5_symbol on every recovery sweep. The audit's
        # H-4 guard. None / empty falls through to the resolver pick
        # for connections that were created before this column was
        # populated.
        existing_symbol: str | None = None
        if getattr(row, "mt5_symbol", None):
            existing_symbol = str(row.mt5_symbol).strip() or None

        await self._provisioner.provision_account(
            connection_id=connection_id,
            user_id=user_id,
            login=row.mt5_login,
            password=password,
            server=row.mt5_server,
            platform=row.platform,
            per_user_zmq_token=existing_token,
            existing_chart_symbol=existing_symbol,
        )

        logger.info(
            "hosted_recovery_reprovision_success",
            extra={
                "connection_id": connection_id,
                "user_id": user_id,
                "reason": reason,
                "phase": phase,
            },
        )
