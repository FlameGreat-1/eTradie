"""Hosted MetaTrader provisioner using Kubernetes StatefulSets.

Spawns isolated Kubernetes StatefulSets running headless MetaTrader 4
or 5 terminals via Wine/Xvfb. Each StatefulSet is fronted by both a
ClusterIP Service on :5555 (ZMQ) + :9100 (watchdog) AND a headless
Service that gives the per-replica pod a stable DNS name. The
engine's ZmqClient dials the regular ClusterIP Service in-cluster.

Production posture (mirrors the helm/mt-node chart EXACTLY):
  - StatefulSet is created with the same labels the chart uses, so
    the chart's NetworkPolicy / PodDisruptionBudget / ServiceMonitor
    selectors match and the engine NetworkPolicy egress allowlist
    (etradie-mt-node) reaches it.
  - volumeClaimTemplates owns the Wine prefix PVC. K8s produces the
    per-replica PVC named 'wine-prefix-<release>-0' automatically.
    There is NO explicit _ensure_pvc helper; the STS reconcile loop
    creates the PVC as part of the StatefulSet's first pod scheduling.
  - Credentials are AES-GCM sealed before writing to the per-tenant
    Secret; the StatefulSet mounts the Secret via envFrom so creds
    never appear in V1EnvVar value strings.
  - provision_account() does NOT return until the StatefulSet has at
    least one Ready replica AND a ZMQ PING succeeds through the
    Service. Up to 300s.
  - delete_account() removes the StatefulSet, both Services, the
    per-tenant Secret, and the per-replica PVC (StatefulSet GC does
    NOT cascade to volumeClaimTemplate PVCs by design - we delete
    them explicitly here).
  - gc_orphans() can be called by a background task to delete
    StatefulSets whose connection_id has been removed from the DB.

Resilience: the K8s StatefulSet controller handles process-restart
loops; the chart's in-pod entrypoint supervises MT5 inside the
container; the watchdog sidecar enforces semantic restart
(EA disconnected, memory soft-cap, CPU soft-cap). All three layers
are independent.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import secrets
import time as _time
from typing import Any, Iterable, Optional

import zmq
import zmq.asyncio as zmq_async
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.exceptions import ApiException
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from engine.shared.exceptions import (
    ConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------
# Chart contract (must match helm/mt-node)
# ---------------------------------------------------------------------
# Dev-only fallback. Production / staging MUST set MT_NODE_IMAGE in
# the engine ConfigMap (helm/engine/templates/configmap.yaml +
# helm/engine/values.yaml::config.mtNode.image). The constructor
# enforces this contract via _resolve_image() below.
MT_NODE_IMAGE_DEV_FALLBACK = "etradie-mt-node:dev"
CONTAINER_PREFIX = "etradie-mt-"  # release-name prefix; first 12 chars of connection_id appended
DEFAULT_ZMQ_PORT = 5555
DEFAULT_WATCHDOG_PORT = 9100
NAMESPACE_DEFAULT = "etradie-system"

# volumeClaimTemplate name MUST match helm/mt-node/templates/statefulset.yaml.
# StatefulSet produces per-replica PVCs named '<tmpl>-<sts>-<ordinal>'.
# With template 'wine-prefix' + sts '<release>' + ordinal 0, the PVC is
# 'wine-prefix-<release>-0'. Both the chart and this provisioner
# converge on this name; an operator can flip a tenant between
# GitOps-managed (chart) and runtime-managed (this provisioner)
# without losing the Wine prefix.
_PVC_TEMPLATE_NAME = "wine-prefix"

# Labels matching helm/mt-node's selectorLabels + labels helpers.
_LABEL_APP_NAME = "app.kubernetes.io/name"
_LABEL_INSTANCE = "app.kubernetes.io/instance"
_LABEL_PART_OF = "app.kubernetes.io/part-of"
_LABEL_COMPONENT = "app.kubernetes.io/component"
_LABEL_MANAGED_BY = "app.kubernetes.io/managed-by"
_LABEL_CONN_ID = "etradie.connection-id"
_LABEL_USER_ID = "etradie.user-id"
_LABEL_PLATFORM = "etradie.platform"

_APP_NAME_VALUE = "etradie-mt-node"
_PART_OF_VALUE = "etradie"
_MANAGED_BY_VALUE = "etradie-engine"

# Environment-bound resource sizing (overridable via env, with chart-aligned defaults).
_MEM_LIMIT = os.environ.get("MT_NODE_MEM_LIMIT", "1536Mi")
_MEM_REQUEST = os.environ.get("MT_NODE_MEM_REQUEST", "1Gi")
_CPU_LIMIT = os.environ.get("MT_NODE_CPU_LIMIT", "1500m")
_CPU_REQUEST = os.environ.get("MT_NODE_CPU_REQUEST", "500m")
_EPHEMERAL_LIMIT = os.environ.get("MT_NODE_EPHEMERAL_LIMIT", "1Gi")
_EPHEMERAL_REQUEST = os.environ.get("MT_NODE_EPHEMERAL_REQUEST", "512Mi")

# Readiness gate.
_READINESS_TIMEOUT_SECS = float(os.environ.get("MT_NODE_READINESS_TIMEOUT_SECS", "300"))
_READINESS_POLL_SECS = float(os.environ.get("MT_NODE_READINESS_POLL_SECS", "3"))
_ZMQ_PROBE_TIMEOUT_SECS = float(os.environ.get("MT_NODE_ZMQ_PROBE_TIMEOUT_SECS", "5"))

# Vault-sourced platform key for credential sealing. Required at
# engine boot; absence means connection_type='hosted' is unusable
# and the factory must surface a ConfigurationError to the dashboard.
_ENC_KEY_ENV = "MT_NODE_CREDENTIAL_ENCRYPTION_KEY"


def _load_encryption_key() -> bytes:
    """Return a 32-byte key derived from MT_NODE_CREDENTIAL_ENCRYPTION_KEY.

    The env var carries a hex string. Production MUST use exactly 32 bytes
    (AES-256-GCM, 64 hex chars). Development accepts 16 or 24 bytes for
    convenience but logs a warning. The key is validated at call time so
    a misconfigured engine pod fails its first hosted provision attempt
    with a clear ConfigurationError rather than silently using a weak key.
    """
    raw = os.environ.get(_ENC_KEY_ENV, "").strip()
    if not raw:
        raise ConfigurationError(
            f"{_ENC_KEY_ENV} is not set. Populate Vault path "
            "etradie/services/mt-node/<env>:mt_node_credential_encryption_key "
            "(openssl rand -hex 32) before any user can pick connection_type=hosted.",
            details={"env_var": _ENC_KEY_ENV},
        )
    try:
        key = bytes.fromhex(raw)
    except ValueError as exc:
        raise ConfigurationError(
            f"{_ENC_KEY_ENV} must be a hex string (e.g. output of 'openssl rand -hex 32')",
            details={"env_var": _ENC_KEY_ENV, "error": str(exc)},
        ) from exc

    app_env = os.environ.get("APP_ENV", "development").strip().lower()
    is_prod_like = app_env in ("production", "staging")

    if is_prod_like and len(key) != 32:
        raise ConfigurationError(
            f"{_ENC_KEY_ENV} must decode to exactly 32 bytes (AES-256-GCM) in "
            f"production/staging. Got {len(key)} bytes. "
            "Generate with: openssl rand -hex 32",
            details={"env_var": _ENC_KEY_ENV, "byte_len": len(key)},
        )
    if len(key) not in (16, 24, 32):
        raise ConfigurationError(
            f"{_ENC_KEY_ENV} must decode to 16, 24, or 32 bytes (got {len(key)}). "
            "32 bytes (AES-256-GCM) is required in production.",
            details={"env_var": _ENC_KEY_ENV, "byte_len": len(key)},
        )
    if not is_prod_like and len(key) != 32:
        logger.warning(
            "mt_node_credential_encryption_key_not_32_bytes",
            extra={
                "byte_len": len(key),
                "warning": (
                    f"{_ENC_KEY_ENV} is {len(key)} bytes. "
                    "Production requires exactly 32 bytes (AES-256-GCM). "
                    "Generate with: openssl rand -hex 32"
                ),
            },
        )
    return key


def _seal(plaintext: str, key: bytes) -> str:
    """AES-GCM seal a string. Returns base64(nonce|ciphertext|tag).

    The Kubernetes Secret stores the sealed string. The mt-node
    container does NOT unseal - the engine writes the PLAIN values
    into the Secret here (the seal is engine-side defense-in-depth
    in case the engine pod is dumped). The container receives the
    plain MT_LOGIN/MT_PASSWORD/MT_ZMQ_AUTH_TOKEN via envFrom; that
    is acceptable because the Pod is per-tenant + read-only-rootfs
    + non-root.
    """
    nonce = secrets.token_bytes(12)
    aead = AESGCM(key)
    ct = aead.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def _b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _pvc_name_for(release: str) -> str:
    """Return the per-replica PVC name that the StatefulSet's
    volumeClaimTemplate produces. The format is
    '<template-name>-<sts-name>-<ordinal>' and ordinal is always 0
    because the chart runs a single replica per tenant.
    """
    return f"{_PVC_TEMPLATE_NAME}-{release}-0"


class HostedProvisioner:
    """Manages the lifecycle of per-user mt-node StatefulSets + Services."""

    def __init__(
        self,
        *,
        namespace: str | None = None,
        image: str | None = None,
        platform_default_token_secret_name: str | None = None,
    ) -> None:
        self._namespace = namespace or os.environ.get("MT_NODE_NAMESPACE", NAMESPACE_DEFAULT)
        self._image = image or self._resolve_image()
        # Platform Secret name the chart provisions. Defaults to the
        # release-scoped name helm/mt-node renders for a release.
        self._platform_secret_template = platform_default_token_secret_name or "{release}-platform"

    @staticmethod
    def _resolve_image() -> str:
        """Resolve the mt-node container image with environment-aware
        strictness.

        Production + staging MUST set MT_NODE_IMAGE explicitly. The
        helm/engine chart wires this via ConfigMap from
        config.mtNode.image. Failing to set it in a hosted-MT-node
        deployment is a deployment misconfiguration that must surface
        immediately at engine boot - not silently use a dev fallback
        and ship the wrong image to tenants.

        Dev (APP_ENV != production/staging) keeps the
        MT_NODE_IMAGE_DEV_FALLBACK so docker-compose, pytest, and
        ad-hoc engine runs continue to work without ceremony.

        Same posture pattern as
        broker_connection_repository._derive_encryption_key().
        """
        explicit = os.environ.get("MT_NODE_IMAGE", "").strip()
        if explicit:
            return explicit
        app_env = os.environ.get("APP_ENV", "development").strip().lower()
        if app_env in ("production", "staging"):
            raise ConfigurationError(
                "MT_NODE_IMAGE is required when APP_ENV is 'production' or 'staging'. "
                "Set helm/engine/values.yaml::config.mtNode.image (rendered into the "
                "engine ConfigMap as MT_NODE_IMAGE) to the pinned mt-node image, "
                "e.g. ghcr.io/<your-org>/etradie-mt-node@sha256:<digest>.",
                details={"env_var": "MT_NODE_IMAGE", "app_env": app_env},
            )
        return MT_NODE_IMAGE_DEV_FALLBACK

    # -- K8s client -----------------------------------------------------------

    async def _api_clients(self) -> tuple[client.CoreV1Api, client.AppsV1Api]:
        """Initialise CoreV1 + AppsV1 with in-cluster auth.

        Construction is NOT cheap (parses kubeconfig OR reads
        the in-cluster service-account token + builds the
        ApiClient + per-resource client). Callers should hold the
        returned pair for the duration of a logical operation
        rather than reopening per-iteration.
        """
        try:
            try:
                config.load_incluster_config()
            except config.ConfigException:
                await config.load_kube_config()
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(
                "Kubernetes API is not reachable",
                details={"error": str(exc)},
            ) from exc
        return client.CoreV1Api(), client.AppsV1Api()

    @staticmethod
    async def _close(api) -> None:
        try:
            await api.api_client.close()
        except Exception:  # noqa: BLE001
            pass

    # -- Naming + label helpers ---------------------------------------------

    @staticmethod
    def _release_name(connection_id: str) -> str:
        return f"{CONTAINER_PREFIX}{connection_id[:12]}"

    @staticmethod
    def _headless_service_name(release: str) -> str:
        return f"{release}-headless"

    @classmethod
    def _labels(
        cls,
        connection_id: str,
        user_id: str,
        platform: str,
        release: str,
    ) -> dict[str, str]:
        return {
            _LABEL_APP_NAME: _APP_NAME_VALUE,
            _LABEL_INSTANCE: release,
            _LABEL_PART_OF: _PART_OF_VALUE,
            _LABEL_COMPONENT: "mt-node",
            _LABEL_MANAGED_BY: _MANAGED_BY_VALUE,
            _LABEL_CONN_ID: connection_id,
            _LABEL_USER_ID: user_id,
            _LABEL_PLATFORM: platform,
        }

    @classmethod
    def _selector_labels(cls, connection_id: str, release: str) -> dict[str, str]:
        # Mirrors helm/mt-node's selectorLabels exactly.
        return {
            _LABEL_APP_NAME: _APP_NAME_VALUE,
            _LABEL_INSTANCE: release,
            _LABEL_CONN_ID: connection_id,
        }

    @staticmethod
    def _resource_requirements() -> client.V1ResourceRequirements:
        return client.V1ResourceRequirements(
            requests={
                "cpu": _CPU_REQUEST,
                "memory": _MEM_REQUEST,
                "ephemeral-storage": _EPHEMERAL_REQUEST,
            },
            limits={
                "cpu": _CPU_LIMIT,
                "memory": _MEM_LIMIT,
                "ephemeral-storage": _EPHEMERAL_LIMIT,
            },
        )

    # -- Public API ---------------------------------------------------------

    async def provision_account(
        self,
        *,
        connection_id: str,
        user_id: str,
        login: str,
        password: str,
        server: str,
        symbol: str = "EURUSD",
        platform: str = "mt5",
        zmq_port: int = DEFAULT_ZMQ_PORT,
        per_user_zmq_token: str | None = None,
        readiness_timeout_secs: float | None = None,
    ) -> dict[str, Any]:
        """Provision a new hosted mt-node release.

        Side effects (idempotent w.r.t. an existing release of the same name):
          1. Create / update the per-tenant Secret with sealed creds.
          2. Create / update the StatefulSet (volumeClaimTemplates
             owns the Wine prefix PVC).
          3. Create / update the regular ClusterIP Service AND the
             headless Service the StatefulSet needs for stable pod-DNS.
          4. Wait until the StatefulSet has at least one Ready replica
             AND a ZMQ PING succeeds.

        Raises:
            ConfigurationError    - missing platform encryption key.
            ProviderUnavailableError - K8s API not reachable.
            ProviderTimeoutError  - readiness gate timed out.
            ProviderError         - K8s mutation failed.
        """
        if platform not in ("mt4", "mt5"):
            raise ConfigurationError(
                f"platform must be mt4 or mt5 (got {platform!r})",
                details={"platform": platform, "connection_id": connection_id},
            )

        key = _load_encryption_key()
        release = self._release_name(connection_id)
        labels = self._labels(connection_id, user_id, platform, release)
        selector = self._selector_labels(connection_id, release)
        service_name = release
        headless_service_name = self._headless_service_name(release)
        secret_name = f"{release}-creds"

        dns_name = f"{service_name}.{self._namespace}.svc.cluster.local"

        # Effective per-tenant token. Engine generates one if the caller
        # did not supply (e.g. first-time provision). Caller (factory.py)
        # also persists it in broker_connections.ea_auth_token (already
        # column-encrypted at REST by the broker_encryption_key) so
        # ZmqClient can re-read it.
        effective_token = (per_user_zmq_token or secrets.token_hex(32)).strip()

        # Persistent api clients for the WHOLE provision flow including
        # the readiness gate. Without this, each readiness poll opened
        # a fresh ApiClient and closed it - up to ~100 client churns
        # per provision at 3s poll interval / 300s timeout. The
        # persistent client also keeps the kube-apiserver connection
        # warm for the duration.
        core_api, apps_api = await self._api_clients()
        try:
            try:
                await self._upsert_secret(
                    core_api=core_api,
                    name=secret_name,
                    labels=labels,
                    login=login,
                    password=password,
                    token=effective_token,
                    seal_key=key,
                )
                await self._upsert_statefulset(
                    apps_api=apps_api,
                    release=release,
                    headless_service_name=headless_service_name,
                    labels=labels,
                    selector=selector,
                    platform=platform,
                    server=server,
                    symbol=symbol,
                    zmq_port=zmq_port,
                    secret_name=secret_name,
                )
                await self._upsert_service(
                    core_api=core_api,
                    name=service_name,
                    labels=labels,
                    selector=selector,
                    zmq_port=zmq_port,
                    headless=False,
                )
                await self._upsert_service(
                    core_api=core_api,
                    name=headless_service_name,
                    labels=labels,
                    selector=selector,
                    zmq_port=zmq_port,
                    headless=True,
                )
            except ApiException as exc:
                logger.error(
                    "hosted_provisioning_k8s_error",
                    extra={
                        "connection_id": connection_id,
                        "release": release,
                        "status": exc.status,
                        "reason": exc.reason,
                        "body": (exc.body or "")[:500],
                    },
                )
                # Best-effort rollback so we do not leak orphans on a
                # partial failure.
                await self._best_effort_cleanup(
                    core_api, apps_api, release,
                    service_name, headless_service_name, secret_name,
                )
                raise ProviderError(
                    f"Failed to create hosted mt-node release: {exc.reason}",
                    details={
                        "connection_id": connection_id,
                        "release": release,
                        "status": exc.status,
                    },
                ) from exc

            # Readiness gate uses the SAME api clients - no churn.
            timeout = readiness_timeout_secs if readiness_timeout_secs is not None else _READINESS_TIMEOUT_SECS
            await self._wait_ready(
                core_api=core_api,
                apps_api=apps_api,
                release=release,
                dns_name=dns_name,
                zmq_port=zmq_port,
                token=effective_token,
                timeout=timeout,
            )
        finally:
            await self._close(core_api)
            await self._close(apps_api)

        logger.info(
            "hosted_provisioning_success",
            extra={
                "connection_id": connection_id,
                "release": release,
                "service": service_name,
                "dns": dns_name,
            },
        )

        return {
            "container_id": release,  # callers store this in broker_connections.hosted_container_id
            "container_name": release,
            "zmq_host": dns_name,
            "zmq_port": zmq_port,
            "zmq_auth_token": effective_token,
            "state": "running",
        }

    async def get_account_status(self, container_id: str) -> dict[str, Any]:
        """Return StatefulSet readiness + Service endpoint state."""
        core_api, apps_api = await self._api_clients()
        try:
            try:
                sts = await apps_api.read_namespaced_stateful_set(
                    name=container_id, namespace=self._namespace,
                )
            except ApiException as exc:
                if exc.status == 404:
                    return {
                        "container_id": container_id,
                        "status": "removed",
                        "running": False,
                        "ready_replicas": 0,
                        "started_at": None,
                        "exit_code": -1,
                    }
                raise ProviderError(
                    f"Failed to read StatefulSet: {exc.reason}",
                    details={"container_id": container_id, "status": exc.status},
                ) from exc

            ready = int(sts.status.ready_replicas or 0)
            replicas = int(sts.status.replicas or 0)
            current = int(sts.status.current_replicas or 0) if hasattr(sts.status, "current_replicas") else replicas
            running = ready >= 1
            return {
                "container_id": container_id,
                "status": "running" if running else "pending",
                "running": running,
                "ready_replicas": ready,
                "replicas": replicas,
                "current_replicas": current,
                "started_at": str(sts.metadata.creation_timestamp) if sts.metadata.creation_timestamp else None,
                "exit_code": 0 if running else -1,
            }
        finally:
            await self._close(core_api)
            await self._close(apps_api)

    async def delete_account(self, container_id: str) -> bool:
        """Remove the StatefulSet, both Services, the per-tenant Secret,
        and the per-replica Wine-prefix PVC for a release.

        StatefulSet GC does NOT cascade to its volumeClaimTemplate
        PVCs by design (the K8s authors decided that stateful data
        deletion must be explicit). We delete the wine-prefix-<release>-0
        PVC here so the engine's connection-delete flow is complete.
        """
        core_api, apps_api = await self._api_clients()
        ok = True
        try:
            ok &= await self._safe_delete(
                apps_api.delete_namespaced_stateful_set, container_id, "StatefulSet",
            )
            ok &= await self._safe_delete(
                core_api.delete_namespaced_service, container_id, "Service",
            )
            ok &= await self._safe_delete(
                core_api.delete_namespaced_service,
                self._headless_service_name(container_id),
                "Service(headless)",
            )
            ok &= await self._safe_delete(
                core_api.delete_namespaced_secret, f"{container_id}-creds", "Secret(creds)",
            )
            # Per-replica PVC the StatefulSet's volumeClaimTemplate produced.
            ok &= await self._safe_delete(
                core_api.delete_namespaced_persistent_volume_claim,
                _pvc_name_for(container_id),
                "PVC(wine-prefix)",
            )
            logger.info(
                "hosted_release_deleted",
                extra={"container_id": container_id, "all_ok": ok},
            )
            return ok
        finally:
            await self._close(core_api)
            await self._close(apps_api)

    def resolve_zmq_host(self, container_id: str) -> Optional[str]:
        return f"{container_id}.{self._namespace}.svc.cluster.local"

    async def gc_orphans(self, known_connection_ids: Iterable[str]) -> dict[str, Any]:
        """Delete StatefulSets whose connection-id is no longer in the DB.

        Called by a background task on the engine. Idempotent.
        """
        known = {cid for cid in known_connection_ids if cid}
        core_api, apps_api = await self._api_clients()
        deleted: list[str] = []
        try:
            sts_list = await apps_api.list_namespaced_stateful_set(
                namespace=self._namespace,
                label_selector=f"{_LABEL_APP_NAME}={_APP_NAME_VALUE}",
            )
            for sts in sts_list.items:
                lbl = (sts.metadata.labels or {}).get(_LABEL_CONN_ID)
                if lbl and lbl not in known:
                    name = sts.metadata.name
                    logger.warning(
                        "hosted_gc_orphan",
                        extra={"statefulset": name, "connection_id": lbl},
                    )
                    await self._safe_delete(
                        apps_api.delete_namespaced_stateful_set, name, "StatefulSet",
                    )
                    await self._safe_delete(
                        core_api.delete_namespaced_service, name, "Service",
                    )
                    await self._safe_delete(
                        core_api.delete_namespaced_service,
                        self._headless_service_name(name),
                        "Service(headless)",
                    )
                    await self._safe_delete(
                        core_api.delete_namespaced_secret, f"{name}-creds", "Secret",
                    )
                    await self._safe_delete(
                        core_api.delete_namespaced_persistent_volume_claim,
                        _pvc_name_for(name), "PVC",
                    )
                    deleted.append(name)
            return {"deleted": deleted, "scanned": len(sts_list.items)}
        finally:
            await self._close(core_api)
            await self._close(apps_api)

    # -- Internal: upsert helpers (idempotent) ------------------------------

    async def _retrying(self) -> AsyncRetrying:
        return AsyncRetrying(
            reraise=True,
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            retry=retry_if_exception_type(ApiException),
        )

    async def _upsert_secret(
        self,
        *,
        core_api: client.CoreV1Api,
        name: str,
        labels: dict[str, str],
        login: str,
        password: str,
        token: str,
        seal_key: bytes,
    ) -> None:
        """Idempotent create-or-update of the per-tenant Secret.

        Keys written:
          MT_LOGIN, MT_PASSWORD, MT_ZMQ_AUTH_TOKEN  -> envFrom in chart
          ETRADIE_SEAL                              -> defense-in-depth
                                                       audit blob
        """
        sealed_blob = json.dumps({
            "login": _seal(login, seal_key),
            "password": _seal(password, seal_key),
            "token": _seal(token, seal_key),
        })
        body = client.V1Secret(
            metadata=client.V1ObjectMeta(name=name, namespace=self._namespace, labels=labels),
            type="Opaque",
            data={
                "MT_LOGIN": _b64(login),
                "MT_PASSWORD": _b64(password),
                "MT_ZMQ_AUTH_TOKEN": _b64(token),
                "ETRADIE_SEAL": _b64(sealed_blob),
            },
        )
        async for attempt in await self._retrying():
            with attempt:
                try:
                    await core_api.create_namespaced_secret(namespace=self._namespace, body=body)
                    return
                except ApiException as exc:
                    if exc.status == 409:
                        await core_api.replace_namespaced_secret(
                            name=name, namespace=self._namespace, body=body,
                        )
                        return
                    raise

    async def _upsert_statefulset(
        self,
        *,
        apps_api: client.AppsV1Api,
        release: str,
        headless_service_name: str,
        labels: dict[str, str],
        selector: dict[str, str],
        platform: str,
        server: str,
        symbol: str,
        zmq_port: int,
        secret_name: str,
    ) -> None:
        """Create or update the per-tenant StatefulSet.

        Wire shape is identical to helm/mt-node/templates/statefulset.yaml.
        Any operator-facing inspection (kubectl describe sts <release>)
        produces an identical resource regardless of whether the chart
        or this provisioner created it. Both paths are wire-compatible:
          - Same labels / selectorLabels.
          - Same volumeClaimTemplate name ('wine-prefix').
          - Same watchdog sidecar with /healthz readiness + /livez liveness.
          - Same lifecycle.preStop (5s sleep for Wine journal flush).
          - Same terminationGracePeriodSeconds (60s).
          - Same security context (non-root, drop ALL, readOnlyRootFilesystem).
        """
        # Watchdog port (matches chart default service.watchdogPort).
        watchdog_port = DEFAULT_WATCHDOG_PORT

        # ── mt-node container env ──────────────────────────────────────────
        env = [
            client.V1EnvVar(name="MT_PLATFORM", value=platform),
            client.V1EnvVar(name="MT_SERVER", value=server),
            client.V1EnvVar(name="MT_SYMBOL", value=symbol),
            client.V1EnvVar(name="ZMQ_PORT", value=str(zmq_port)),
            client.V1EnvVar(
                name="POD_NAME",
                value_from=client.V1EnvVarSource(
                    field_ref=client.V1ObjectFieldSelector(field_path="metadata.name"),
                ),
            ),
            client.V1EnvVar(
                name="POD_NAMESPACE",
                value_from=client.V1EnvVarSource(
                    field_ref=client.V1ObjectFieldSelector(field_path="metadata.namespace"),
                ),
            ),
        ]
        env_from = [
            client.V1EnvFromSource(
                secret_ref=client.V1SecretEnvSource(name=secret_name, optional=False),
            ),
        ]

        # ── Shared security context (both containers) ──────────────────────
        container_security_ctx = client.V1SecurityContext(
            allow_privilege_escalation=False,
            read_only_root_filesystem=True,
            run_as_non_root=True,
            run_as_user=1000,
            capabilities=client.V1Capabilities(drop=["ALL"]),
        )

        # ── Shared lifecycle preStop (Wine journal flush) ──────────────────
        # Mirrors chart lifecycle.preStop: give Wine 5s to flush its
        # journal cleanly when the Pod is being terminated. Combined
        # with entrypoint.sh's SIGTERM trap this gives a clean shutdown.
        lifecycle = client.V1Lifecycle(
            pre_stop=client.V1LifecycleHandler(
                _exec=client.V1ExecAction(command=["/bin/sh", "-c", "sleep 5"]),
            ),
        )

        # ── mt-node main container ─────────────────────────────────────────
        # startupProbe: TCP on ZMQ port. Budgets 20 + 5*60 = 320s for
        # cold Wine boot (first-time MT5 install into the Wine prefix).
        # readinessProbe + livenessProbe: HTTP on watchdog /healthz and
        # /livez. Readiness only turns true once the EA reports
        # mt5_connected=true AND authenticated=true within the last 30s.
        container = client.V1Container(
            name="mt-node",
            image=self._image,
            image_pull_policy="IfNotPresent",
            env=env,
            env_from=env_from,
            ports=[
                client.V1ContainerPort(name="zmq", container_port=zmq_port, protocol="TCP"),
            ],
            resources=self._resource_requirements(),
            security_context=container_security_ctx,
            startup_probe=client.V1Probe(
                tcp_socket=client.V1TCPSocketAction(port=zmq_port),
                initial_delay_seconds=20,
                period_seconds=5,
                timeout_seconds=3,
                success_threshold=1,
                failure_threshold=60,
            ),
            readiness_probe=client.V1Probe(
                http_get=client.V1HTTPGetAction(
                    path="/healthz",
                    port=watchdog_port,
                    scheme="HTTP",
                ),
                initial_delay_seconds=0,
                period_seconds=10,
                timeout_seconds=5,
                success_threshold=1,
                failure_threshold=3,
            ),
            liveness_probe=client.V1Probe(
                http_get=client.V1HTTPGetAction(
                    path="/livez",
                    port=watchdog_port,
                    scheme="HTTP",
                ),
                initial_delay_seconds=0,
                period_seconds=30,
                timeout_seconds=5,
                success_threshold=1,
                failure_threshold=3,
            ),
            lifecycle=lifecycle,
            volume_mounts=[
                # wine-prefix is supplied by volumeClaimTemplates below;
                # K8s wires the per-replica PVC automatically.
                client.V1VolumeMount(name=_PVC_TEMPLATE_NAME, mount_path="/home/mt/.wine"),
                client.V1VolumeMount(name="mt-cache", mount_path="/home/mt/.cache"),
                client.V1VolumeMount(name="tmp", mount_path="/tmp"),
                client.V1VolumeMount(name="var-tmp", mount_path="/var/tmp"),
            ],
        )

        # ── Watchdog sidecar ───────────────────────────────────────────────
        # Mirrors chart sidecar.watchdog. Polls the EA HEALTH command,
        # exposes /healthz + /livez + /metrics on :9100. Enforces
        # memory soft-cap (RSS > 0.8 × cgroup limit → restart MT5) and
        # CPU soft-cap (CFS throttled > 0.5 of periods for 60s → restart).
        # Reuses the same mt-node image (watchdog.py is baked in at
        # /opt/watchdog/watchdog.py by the Dockerfile).
        #
        # Watchdog resource sizing mirrors chart values-production.yaml:
        # requests == limits (Guaranteed QoS for the Pod) with sub-core
        # CPU so the watchdog stays in the shared pool while the mt-node
        # container can get exclusive cores via static CPU manager.
        watchdog_resources = client.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "64Mi"},
            limits={"cpu": "100m", "memory": "64Mi"},
        )
        # Watchdog env: reads auth token from the same per-tenant Secret
        # (MT_ZMQ_AUTH_TOKEN) and the platform Secret (DEFAULT_ZMQ_AUTH_TOKEN).
        watchdog_env_from = [
            client.V1EnvFromSource(
                secret_ref=client.V1SecretEnvSource(name=secret_name, optional=False),
            ),
        ]
        watchdog_env = [
            client.V1EnvVar(
                name="WATCHDOG_ZMQ_ENDPOINT",
                value=f"tcp://127.0.0.1:{zmq_port}",
            ),
            client.V1EnvVar(
                name="WATCHDOG_HTTP_PORT",
                value=str(watchdog_port),
            ),
            client.V1EnvVar(
                name="WATCHDOG_SYMBOL",
                value=symbol,
            ),
            client.V1EnvVar(
                name="WATCHDOG_POLL_INTERVAL_SECONDS",
                value="10",
            ),
            client.V1EnvVar(
                name="WATCHDOG_MAX_FAILURES",
                value="6",
            ),
            client.V1EnvVar(
                name="WATCHDOG_MEMORY_SOFT_CAP_FRACTION",
                value="0.8",
            ),
            client.V1EnvVar(
                name="WATCHDOG_CPU_THROTTLE_SOFT_CAP_FRACTION",
                value="0.5",
            ),
            client.V1EnvVar(
                name="WATCHDOG_CPU_THROTTLE_CONSECUTIVE_POLLS",
                value="6",
            ),
            client.V1EnvVar(
                name="WATCHDOG_LIVEZ_GRACE_SECONDS",
                value="60",
            ),
            client.V1EnvVar(
                name="POD_NAME",
                value_from=client.V1EnvVarSource(
                    field_ref=client.V1ObjectFieldSelector(field_path="metadata.name"),
                ),
            ),
            client.V1EnvVar(
                name="POD_NAMESPACE",
                value_from=client.V1EnvVarSource(
                    field_ref=client.V1ObjectFieldSelector(field_path="metadata.namespace"),
                ),
            ),
        ]
        watchdog_container = client.V1Container(
            name="watchdog",
            image=self._image,
            image_pull_policy="IfNotPresent",
            command=[
                "/usr/bin/tini",
                "--",
                "/usr/bin/env",
                "python3",
                "/opt/watchdog/watchdog.py",
            ],
            env=watchdog_env,
            env_from=watchdog_env_from,
            ports=[
                client.V1ContainerPort(name="watchdog", container_port=watchdog_port, protocol="TCP"),
            ],
            resources=watchdog_resources,
            security_context=container_security_ctx,
            volume_mounts=[
                # Watchdog only needs /tmp (for any transient writes).
                client.V1VolumeMount(name="tmp", mount_path="/tmp"),
            ],
        )

        # ── Pod spec ───────────────────────────────────────────────────────
        pod_spec = client.V1PodSpec(
            service_account_name="default",  # mt-node never calls K8s API
            automount_service_account_token=False,
            security_context=client.V1PodSecurityContext(
                run_as_non_root=True,
                run_as_user=1000,
                run_as_group=1000,
                fs_group=1000,
                seccomp_profile=client.V1SeccompProfile(type="RuntimeDefault"),
            ),
            termination_grace_period_seconds=60,
            containers=[container, watchdog_container],
            # Inline volumes only; the wine-prefix volume is supplied by
            # volumeClaimTemplates below.
            volumes=[
                client.V1Volume(name="mt-cache", empty_dir=client.V1EmptyDirVolumeSource(size_limit="256Mi")),
                client.V1Volume(name="tmp", empty_dir=client.V1EmptyDirVolumeSource(size_limit="256Mi")),
                client.V1Volume(name="var-tmp", empty_dir=client.V1EmptyDirVolumeSource(size_limit="64Mi")),
            ],
        )

        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels=selector | {
                _LABEL_PART_OF: _PART_OF_VALUE,
                _LABEL_COMPONENT: "mt-node",
                _LABEL_USER_ID: labels[_LABEL_USER_ID],
                _LABEL_PLATFORM: platform,
            }),
            spec=pod_spec,
        )

        # volumeClaimTemplate. K8s materialises this into a per-replica
        # PVC named '<template>-<sts>-<ordinal>' = 'wine-prefix-<release>-0'.
        # The reclaim policy is set at the StorageClass level; the chart's
        # convention is Retain so the Wine prefix survives a helm uninstall.
        pvc_template = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(
                name=_PVC_TEMPLATE_NAME,
                labels={
                    _LABEL_APP_NAME: _APP_NAME_VALUE,
                    _LABEL_INSTANCE: release,
                    _LABEL_COMPONENT: "wine-prefix",
                },
            ),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(
                    requests={"storage": os.environ.get("MT_NODE_PVC_SIZE", "4Gi")},
                ),
            ),
        )

        sts = client.V1StatefulSet(
            metadata=client.V1ObjectMeta(name=release, namespace=self._namespace, labels=labels),
            spec=client.V1StatefulSetSpec(
                replicas=1,
                service_name=headless_service_name,
                pod_management_policy="OrderedReady",
                update_strategy=client.V1StatefulSetUpdateStrategy(
                    type="RollingUpdate",
                    rolling_update=client.V1RollingUpdateStatefulSetStrategy(partition=0),
                ),
                revision_history_limit=5,
                selector=client.V1LabelSelector(match_labels=selector),
                template=pod_template,
                volume_claim_templates=[pvc_template],
            ),
        )

        async for attempt in await self._retrying():
            with attempt:
                try:
                    await apps_api.create_namespaced_stateful_set(
                        namespace=self._namespace, body=sts,
                    )
                    return
                except ApiException as exc:
                    if exc.status == 409:
                        await apps_api.replace_namespaced_stateful_set(
                            name=release, namespace=self._namespace, body=sts,
                        )
                        return
                    raise

    async def _upsert_service(
        self,
        *,
        core_api: client.CoreV1Api,
        name: str,
        labels: dict[str, str],
        selector: dict[str, str],
        zmq_port: int,
        headless: bool,
    ) -> None:
        """Idempotent create-or-update of a Service.

        When headless=True, sets clusterIP='None' so the Service is
        used only for stable per-pod DNS by the StatefulSet. When
        False (the regular ClusterIP Service), engine ZmqClient
        traffic flows through this Service AND Prometheus scrapes
        the watchdog /metrics on :9100.
        """
        watchdog_port = DEFAULT_WATCHDOG_PORT
        # The headless Service is for stable pod-DNS only; it does not
        # need to expose the watchdog port because Prometheus discovers
        # the watchdog via the regular ClusterIP Service's ServiceMonitor.
        ports = [
            client.V1ServicePort(
                name="zmq", port=zmq_port, target_port="zmq", protocol="TCP",
            ),
        ]
        if not headless:
            ports.append(
                client.V1ServicePort(
                    name="watchdog", port=watchdog_port, target_port="watchdog", protocol="TCP",
                ),
            )
        service_spec = client.V1ServiceSpec(
            type="ClusterIP",
            cluster_ip="None" if headless else None,
            publish_not_ready_addresses=False,
            selector=selector,
            ports=ports,
        )
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=name, namespace=self._namespace, labels=labels),
            spec=service_spec,
        )
        async for attempt in await self._retrying():
            with attempt:
                try:
                    await core_api.create_namespaced_service(
                        namespace=self._namespace, body=service,
                    )
                    return
                except ApiException as exc:
                    if exc.status == 409:
                        existing = await core_api.read_namespaced_service(
                            name=name, namespace=self._namespace,
                        )
                        # Preserve clusterIP (immutable). For a headless
                        # service the existing clusterIP is 'None' and
                        # we keep it; for a regular service it's the
                        # allocated IP and we must also keep it.
                        service.spec.cluster_ip = existing.spec.cluster_ip
                        service.metadata.resource_version = existing.metadata.resource_version
                        await core_api.replace_namespaced_service(
                            name=name, namespace=self._namespace, body=service,
                        )
                        return
                    raise

    # -- Internal: readiness gate -------------------------------------------

    async def _wait_ready(
        self,
        *,
        core_api: client.CoreV1Api,
        apps_api: client.AppsV1Api,
        release: str,
        dns_name: str,
        zmq_port: int,
        token: str,
        timeout: float,
    ) -> None:
        """Block until StatefulSet has a Ready replica AND ZMQ PING
        returns ok, or raise.

        Uses the api clients provided by the caller - no per-iteration
        construction/close churn. The caller (provision_account) owns
        the lifecycle.
        """
        del core_api  # unused here; reserved for future use
        deadline = _time.monotonic() + timeout
        last_error: Exception | None = None

        # Phase 1 - StatefulSet has at least one Ready replica.
        while _time.monotonic() < deadline:
            try:
                sts = await apps_api.read_namespaced_stateful_set(
                    name=release, namespace=self._namespace,
                )
                ready = int(sts.status.ready_replicas or 0)
                if ready >= 1:
                    break
            except ApiException as exc:
                last_error = exc
                logger.debug(
                    "hosted_readiness_sts_poll_error",
                    extra={"release": release, "status": exc.status, "reason": exc.reason},
                )
            await asyncio.sleep(_READINESS_POLL_SECS)
        else:
            raise ProviderTimeoutError(
                "mt-node StatefulSet did not become Ready within timeout",
                details={
                    "release": release,
                    "timeout_secs": timeout,
                    "last_error": str(last_error) if last_error else None,
                },
            )

        # Phase 2 - ZMQ PING through Service DNS.
        while _time.monotonic() < deadline:
            try:
                ok = await self._zmq_ping(dns_name=dns_name, port=zmq_port, token=token)
                if ok:
                    return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.debug(
                    "hosted_readiness_ping_error",
                    extra={"release": release, "dns": dns_name, "error": str(exc)},
                )
            await asyncio.sleep(_READINESS_POLL_SECS)

        raise ProviderTimeoutError(
            "mt-node ZMQ PING did not succeed within timeout",
            details={
                "release": release,
                "dns": dns_name,
                "timeout_secs": timeout,
                "last_error": str(last_error) if last_error else None,
            },
        )

    async def _zmq_ping(self, *, dns_name: str, port: int, token: str) -> bool:
        endpoint = f"tcp://{dns_name}:{port}"
        ctx = zmq_async.Context.instance()
        sock = ctx.socket(zmq.REQ)
        sock.setsockopt(zmq.LINGER, 0)
        sock.setsockopt(zmq.RCVTIMEO, int(_ZMQ_PROBE_TIMEOUT_SECS * 1000))
        sock.setsockopt(zmq.SNDTIMEO, int(_ZMQ_PROBE_TIMEOUT_SECS * 1000))
        try:
            sock.connect(endpoint)
            await asyncio.wait_for(
                sock.send_string(json.dumps({"command": "PING", "auth_token": token})),
                timeout=_ZMQ_PROBE_TIMEOUT_SECS,
            )
            raw = await asyncio.wait_for(sock.recv(), timeout=_ZMQ_PROBE_TIMEOUT_SECS)
            reply = json.loads(raw.decode("utf-8"))
            return isinstance(reply, dict) and reply.get("status") == "ok"
        finally:
            try:
                sock.close(linger=0)
            except Exception:  # noqa: BLE001
                pass

    # -- Internal: deletion helpers -----------------------------------------

    async def _safe_delete(self, fn, name: str, kind: str) -> bool:
        try:
            await fn(name=name, namespace=self._namespace)
            logger.info("hosted_resource_deleted", extra={"kind": kind, "name": name})
            return True
        except ApiException as exc:
            if exc.status == 404:
                return True
            logger.warning(
                "hosted_resource_delete_failed",
                extra={"kind": kind, "name": name, "status": exc.status, "reason": exc.reason},
            )
            return False

    async def _best_effort_cleanup(
        self,
        core_api: client.CoreV1Api,
        apps_api: client.AppsV1Api,
        release: str,
        service_name: str,
        headless_service_name: str,
        secret_name: str,
    ) -> None:
        for fn, name, kind in (
            (apps_api.delete_namespaced_stateful_set, release, "StatefulSet"),
            (core_api.delete_namespaced_service, service_name, "Service"),
            (core_api.delete_namespaced_service, headless_service_name, "Service(headless)"),
            (core_api.delete_namespaced_secret, secret_name, "Secret"),
            (
                core_api.delete_namespaced_persistent_volume_claim,
                _pvc_name_for(release),
                "PVC",
            ),
        ):
            try:
                await fn(name=name, namespace=self._namespace)
            except ApiException as exc:
                if exc.status != 404:
                    logger.warning(
                        "hosted_rollback_warning",
                        extra={"kind": kind, "name": name, "status": exc.status},
                    )
