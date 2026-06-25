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
- Fresh provisions (younger than fresh_provision_grace_secs) are
  protected from the eager startup sweep so a legitimate first-boot
  cold start (Wine init + LiveUpdate + MQL5 recompile, can take 5-10
  minutes) is not torn down by a coincidental engine restart. See
  docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md for the loop this
  guard prevents.
- All four metrics are bounded-cardinality (see prometheus.py
  comments). Per-connection detail goes to structured logs.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
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
    # A freshly-provisioned connection is legitimately mid-first-boot
    # for ~5-10 minutes (Wine init + MT5 launch + LiveUpdate download +
    # exit-143 self-restart + 453-file MQL5 recompile + EA OnInit). If
    # the engine pod restarts inside that window, run_once_at_startup
    # used to fire with bypass_threshold=True and tear the connection
    # down before it could converge. The fresh-provision grace window
    # below skips connections younger than this threshold during the
    # bypass-threshold path; the normal periodic sweep still applies
    # (with its longer unhealthy_threshold_secs gate). Default 30min
    # = 2x the worst-case first-boot envelope (15min) plus a 15min
    # operability margin. Set to 0 to restore the pre-fix behaviour.
    fresh_provision_grace_secs: float = 1800.0

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
            # 1200s default sits well above the new provisioner readiness
            # gate (_READINESS_TIMEOUT_SECS=600) so the recovery sweep
            # cannot trigger a re-provision against a Pod that is still
            # legitimately cold-booting through its FIRST LiveUpdate +
            # MQL5 recompile cycle. The previous 600s value matched the
            # readiness gate exactly, which created a race where the
            # sweep fired at the same instant the readiness gate
            # expired. See docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md.
            unhealthy_threshold_secs=_pos_float("ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS", "1200", 30.0),
            reprovision_cooldown_secs=_pos_float("ENGINE_HOSTED_RECOVERY_REPROVISION_COOLDOWN_SECS", "300", 30.0),
            max_concurrent_reprovisions=_pos_int("ENGINE_HOSTED_RECOVERY_MAX_CONCURRENT", "4", 1),
            # 0 disables the guard (pre-fix behaviour); the production
            # default protects fresh provisions through their genuine
            # first-boot window.
            fresh_provision_grace_secs=_pos_float("ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS", "1800", 0.0),
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
        # Register the sweep with the BackgroundTaskCoordinator so engine
        # shutdown drains it cleanly (the documented design invariant) and
        # the coordinator owns task lifecycle/error tracking. The
        # coordinator returns the created asyncio.Task; we retain it so the
        # idempotency guard above and stop() can observe its state.
        self._task = coordinator.create_task(
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

            # FRESH-PROVISION GUARD.
            # A connection younger than fresh_provision_grace_secs is
            # legitimately mid-first-boot (Wine init + LiveUpdate +
            # exit-143 self-restart + 453-file MQL5 recompile +
            # EA OnInit). The PROVISION call's own readiness gate
            # (_READINESS_TIMEOUT_SECS=600s) is the authoritative
            # check during this window; recovery must NOT tear it
            # down. Without this guard, a coincidental engine
            # restart during a user's first provision used to fire
            # the bypass-threshold startup sweep and re-provision
            # the connection from scratch, destroying the in-flight
            # LiveUpdate state and feeding the loop documented in
            # docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md.
            grace = self._config.fresh_provision_grace_secs
            if grace > 0.0:
                created_at = self._row_created_at_seconds(row)
                if created_at is not None:
                    age_since_created = max(0.0, time.time() - created_at)
                    if age_since_created < grace:
                        logger.info(
                            "hosted_recovery_fresh_provision_grace",
                            extra={
                                "connection_id": connection_id,
                                "user_id": user_id,
                                "release": release,
                                "status": sts_status,
                                "reason": reason,
                                "phase": phase,
                                "age_since_created_secs": round(age_since_created, 1),
                                "grace_secs": grace,
                            },
                        )
                        continue

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

    @staticmethod
    def _row_created_at_seconds(row: BrokerConnectionRow) -> float | None:
        """Return row.created_at as a UNIX epoch seconds float, or None.

        Robust to None, naive datetimes (assumed UTC), and aware
        datetimes (normalised to UTC). A None or unparseable value
        means we cannot evaluate the fresh-provision grace; the
        caller falls through to the normal recovery path.
        """
        created = getattr(row, "created_at", None)
        if created is None:
            return None
        if isinstance(created, datetime):
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            try:
                return created.timestamp()
            except (OverflowError, OSError, ValueError):
                return None
        # Best-effort numeric coercion for surprise types (epoch ints/
        # strings). Any failure -> None means "cannot apply grace",
        # which is safe (the connection is then evaluated by the
        # normal thresholds, not torn down inappropriately).
        try:
            return float(created)
        except (TypeError, ValueError):
            return None

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

        # Terminal-failure state guard.
        #
        # broker_connections.status tracks the LAST RECORDED PROVISION /
        # OPERATOR OUTCOME, independently of the live K8s readiness state:
        #   'provisioning' -> initial state on POST /api/broker/connections
        #   'ready'        -> background provision succeeded
        #   'failed'       -> background provision raised
        #   'connected' / 'disconnected' / 'error' / 'untested'
        #                  -> set by test/activate/health paths
        # A row marked 'failed' represents a terminal failure outcome
        # that the router has already recorded for the operator (and
        # surfaced on the dashboard). The recovery loop was ignoring
        # this column entirely and rebuilding such rows every
        # reprovision_cooldown_secs (300s default), which:
        #   1. Polluted the preserved PVC journal with repeated
        #      cold-boot banners (2026-06-25 captured 63 fresh
        #      'MetaTrader 5 x64 build 5836 started' lines in 1.5h)
        #      making operator diagnostics substantially harder.
        #   2. Wasted cluster resources rebuilding a pod that the
        #      preceding provision flow already determined was broken.
        #   3. Masked the original failure (the row's status_message
        #      kept getting reset on each re-provision attempt).
        # Recovery here is for HEALTHY rows whose K8s state drifted
        # (StatefulSet evicted, namespace wipe, node drain leaving a
        # stuck Pending). For status='failed' the operator must take
        # explicit action -- delete the row and re-create from the
        # dashboard, or POST /api/broker/connections/{id}/test if they
        # believe the underlying broker side is now fixed. Either path
        # transitions the row off 'failed' and the next sweep picks it
        # back up.
        row_status = (getattr(row, "status", None) or "").strip().lower()
        if row_status == "failed":
            logger.warning(
                "hosted_recovery_skipped_terminal_failure_status",
                extra={
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "reason": reason,
                    "phase": phase,
                    "row_status": row_status,
                    "row_status_message": (getattr(row, "status_message", "") or "")[:300],
                    "hint": "Row is marked 'failed' from a previous provision attempt. Recovery will NOT rebuild it. Operator must delete + re-create the connection from the dashboard, or POST /api/broker/connections/{id}/test to transition off the failed state.",
                },
            )
            return

        # broker_id + broker_entity_id are REQUIRED by
        # HostedProvisioner.provision_account so it can resolve the
        # broker bundle (bundle_r2_path + bundle_sha256) from the
        # BrokerRegistry and layer it into the per-tenant pod. Migration
        # 0034 added these columns nullable for backfill safety, so a
        # row created before that migration (or a row with an unknown
        # brand) carries NULL. Skipping the recovery in that case is the
        # only safe choice: re-provisioning without a broker_id would
        # crash at registry.resolve(), and provisioning with an empty
        # string would silently boot a Pod with no servers.dat layered
        # in. The operator must re-create the connection via the
        # dashboard to populate these columns. The skip is logged loud
        # so the dashboard / on-call sees it.
        brand_id = (getattr(row, "broker_id", None) or "").strip()
        entity_id = (getattr(row, "broker_entity_id", None) or "").strip()
        if not brand_id or not entity_id:
            logger.warning(
                "hosted_recovery_skipped_missing_broker_identity",
                extra={
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "reason": reason,
                    "phase": phase,
                    "has_broker_id": bool(brand_id),
                    "has_broker_entity_id": bool(entity_id),
                    "hint": "The row pre-dates the broker registry rollout (migration 0034) or was created via a path that did not persist broker_id/broker_entity_id. The user must re-create this hosted connection from the dashboard so the new columns get populated.",
                },
            )
            return

        await self._provisioner.provision_account(
            connection_id=connection_id,
            user_id=user_id,
            brand_id=brand_id,
            entity_id=entity_id,
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
