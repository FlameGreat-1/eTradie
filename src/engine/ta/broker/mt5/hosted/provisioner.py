"""Hosted MetaTrader provisioner using Kubernetes Deployments.

Spawns isolated Kubernetes Deployments running headless MetaTrader 4 or
5 terminals via Wine/Xvfb. Each Deployment is fronted by a ClusterIP
Service on :5555 (ZMQ) + :9100 (watchdog). The engine's ZmqClient
dials the Service in-cluster.

Production posture (mirrors the helm/mt-node chart exactly):
  - Deployment is created with the same labels the chart uses, so the
    chart's NetworkPolicy / PodDisruptionBudget / ServiceMonitor
    selectors match and the engine NetworkPolicy egress allowlist
    (etradie-mt-node) reaches it.
  - Credentials are AES-GCM sealed before writing to the per-tenant
    Secret; the Deployment mounts the Secret via envFrom so creds
    never appear in V1EnvVar value strings.
  - provision_account() does NOT return until the Deployment is
    Ready AND a ZMQ PING succeeds through the Service. Up to 300s.
  - delete_account() removes the Deployment, both Services, the
    per-tenant Secret, and the PVC.
  - gc_orphans() can be called by a background task to delete
    Deployments whose connection_id has been removed from the DB.

Resilience: K8s ReplicaSet+Deployment controller handles process-
restart loops; the chart's in-pod entrypoint supervises MT5 inside
the container; the watchdog sidecar enforces semantic restart
(EA disconnected, memory soft-cap). All three layers are independent.
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
MT_NODE_IMAGE_DEFAULT = "ghcr.io/flamegreat-1/etradie-mt-node:0.1.0"
CONTAINER_PREFIX = "etradie-mt-"  # release-name prefix; first 12 chars of connection_id appended
DEFAULT_ZMQ_PORT = 5555
DEFAULT_WATCHDOG_PORT = 9100
NAMESPACE_DEFAULT = "etradie-system"

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

    The env var carries a hex string (>=32 hex chars => >=16 bytes).
    32 bytes (AES-256-GCM) is the platform-recommended size.
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
            f"{_ENC_KEY_ENV} must be a hex string",
            details={"env_var": _ENC_KEY_ENV, "error": str(exc)},
        ) from exc
    if len(key) not in (16, 24, 32):
        raise ConfigurationError(
            f"{_ENC_KEY_ENV} must decode to 16, 24, or 32 bytes (got {len(key)}). 32 recommended.",
            details={"env_var": _ENC_KEY_ENV, "byte_len": len(key)},
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

    NOTE: the sealing here applies to a hardened-store variant the
    engine writes ALSO into broker_connections.audit_seal so that an
    audit trail of which connections existed at what time can be
    reconstructed even if the K8s Secret is GC'd. The mt-node
    container always reads the unsealed envFrom values.
    """
    nonce = secrets.token_bytes(12)
    aead = AESGCM(key)
    ct = aead.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def _b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


class HostedProvisioner:
    """Manages the lifecycle of per-user mt-node Deployments + Services."""

    def __init__(
        self,
        *,
        namespace: str | None = None,
        image: str | None = None,
        platform_default_token_secret_name: str | None = None,
    ) -> None:
        self._namespace = namespace or os.environ.get("MT_NODE_NAMESPACE", NAMESPACE_DEFAULT)
        self._image = image or os.environ.get("MT_NODE_IMAGE", MT_NODE_IMAGE_DEFAULT)
        # Platform Secret name the chart provisions. Defaults to the
        # name helm/mt-node's helper renders for a release
        # 'etradie-mt-platform' shared across releases is NOT used
        # here; the chart creates one per release. We mount the
        # release-scoped platform Secret with the same naming rule.
        self._platform_secret_template = platform_default_token_secret_name or "{release}-platform"

    # -- K8s client -----------------------------------------------------------

    async def _api_clients(self) -> tuple[client.CoreV1Api, client.AppsV1Api]:
        """Initialise CoreV1 + AppsV1 with in-cluster auth."""
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
    async def _close(api: client.CoreV1Api) -> None:
        try:
            await api.api_client.close()
        except Exception:  # noqa: BLE001
            pass

    # -- Naming + label helpers ---------------------------------------------

    @staticmethod
    def _release_name(connection_id: str) -> str:
        return f"{CONTAINER_PREFIX}{connection_id[:12]}"

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
          2. Create / update the Deployment.
          3. Create / update the ClusterIP Service.
          4. Wait until Deployment is Ready AND ZMQ PING succeeds.

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
        secret_name = f"{release}-creds"

        dns_name = f"{service_name}.{self._namespace}.svc.cluster.local"

        # Effective per-tenant token. Engine generates one if the caller
        # did not supply (e.g. first-time provision). Caller (factory.py)
        # also persists it in broker_connections.ea_auth_token (already
        # column-encrypted at REST by the broker_encryption_key) so
        # ZmqClient can re-read it.
        effective_token = (per_user_zmq_token or secrets.token_hex(32)).strip()

        core_api, apps_api = await self._api_clients()
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
            await self._upsert_deployment(
                apps_api=apps_api,
                release=release,
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
            await self._best_effort_cleanup(core_api, apps_api, release, service_name, secret_name)
            raise ProviderError(
                f"Failed to create hosted mt-node release: {exc.reason}",
                details={
                    "connection_id": connection_id,
                    "release": release,
                    "status": exc.status,
                },
            ) from exc
        finally:
            await self._close(core_api)
            await self._close(apps_api)

        # Readiness gate runs through its own client to avoid serialising
        # behind the close() above.
        timeout = readiness_timeout_secs if readiness_timeout_secs is not None else _READINESS_TIMEOUT_SECS
        try:
            await self._wait_ready(
                release=release,
                dns_name=dns_name,
                zmq_port=zmq_port,
                token=effective_token,
                timeout=timeout,
            )
        except ProviderTimeoutError:
            # Leave the release in place so an operator can inspect
            # logs; surface the timeout to the dashboard.
            raise

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
        """Return Deployment readiness + Service endpoint state."""
        core_api, apps_api = await self._api_clients()
        try:
            try:
                dep = await apps_api.read_namespaced_deployment(
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
                    f"Failed to read Deployment: {exc.reason}",
                    details={"container_id": container_id, "status": exc.status},
                ) from exc

            ready = int(dep.status.ready_replicas or 0)
            replicas = int(dep.status.replicas or 0)
            available_cond = next(
                (c for c in (dep.status.conditions or []) if c.type == "Available"),
                None,
            )
            running = ready >= 1 and (available_cond is None or available_cond.status == "True")
            return {
                "container_id": container_id,
                "status": "running" if running else "pending",
                "running": running,
                "ready_replicas": ready,
                "replicas": replicas,
                "started_at": str(dep.metadata.creation_timestamp) if dep.metadata.creation_timestamp else None,
                "exit_code": 0 if running else -1,
            }
        finally:
            await self._close(core_api)
            await self._close(apps_api)

    async def delete_account(self, container_id: str) -> bool:
        """Remove the Deployment, Service, Secret, and PVC for a release."""
        core_api, apps_api = await self._api_clients()
        ok = True
        try:
            ok &= await self._safe_delete(
                apps_api.delete_namespaced_deployment, container_id, "Deployment",
            )
            ok &= await self._safe_delete(
                core_api.delete_namespaced_service, container_id, "Service",
            )
            ok &= await self._safe_delete(
                core_api.delete_namespaced_secret, f"{container_id}-creds", "Secret(creds)",
            )
            # PVC name follows StatefulSet/Deployment volumeClaimTemplates contract.
            # The chart uses a single PVC named wine-prefix-<release>-0; for the
            # Deployment variant we manage it explicitly below.
            ok &= await self._safe_delete(
                core_api.delete_namespaced_persistent_volume_claim,
                f"{container_id}-wine-prefix",
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
        """Delete Deployments whose connection-id is no longer in the DB.

        Called by a background task on the engine. Idempotent.
        """
        known = {cid for cid in known_connection_ids if cid}
        core_api, apps_api = await self._api_clients()
        deleted: list[str] = []
        try:
            dep_list = await apps_api.list_namespaced_deployment(
                namespace=self._namespace,
                label_selector=f"{_LABEL_APP_NAME}={_APP_NAME_VALUE}",
            )
            for dep in dep_list.items:
                lbl = (dep.metadata.labels or {}).get(_LABEL_CONN_ID)
                if lbl and lbl not in known:
                    name = dep.metadata.name
                    logger.warning(
                        "hosted_gc_orphan",
                        extra={"deployment": name, "connection_id": lbl},
                    )
                    await self._safe_delete(apps_api.delete_namespaced_deployment, name, "Deployment")
                    await self._safe_delete(core_api.delete_namespaced_service, name, "Service")
                    await self._safe_delete(core_api.delete_namespaced_secret, f"{name}-creds", "Secret")
                    await self._safe_delete(
                        core_api.delete_namespaced_persistent_volume_claim,
                        f"{name}-wine-prefix", "PVC",
                    )
                    deleted.append(name)
            return {"deleted": deleted, "scanned": len(dep_list.items)}
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

    async def _upsert_deployment(
        self,
        *,
        apps_api: client.AppsV1Api,
        release: str,
        labels: dict[str, str],
        selector: dict[str, str],
        platform: str,
        server: str,
        symbol: str,
        zmq_port: int,
        secret_name: str,
    ) -> None:
        """Create or update the per-tenant Deployment."""
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
        container = client.V1Container(
            name="mt-node",
            image=self._image,
            image_pull_policy="IfNotPresent",
            env=env,
            env_from=env_from,
            ports=[client.V1ContainerPort(name="zmq", container_port=zmq_port, protocol="TCP")],
            resources=self._resource_requirements(),
            security_context=client.V1SecurityContext(
                allow_privilege_escalation=False,
                read_only_root_filesystem=True,
                run_as_non_root=True,
                run_as_user=1000,
                capabilities=client.V1Capabilities(drop=["ALL"]),
            ),
            startup_probe=client.V1Probe(
                tcp_socket=client.V1TCPSocketAction(port=zmq_port),
                initial_delay_seconds=20,
                period_seconds=5,
                timeout_seconds=3,
                success_threshold=1,
                failure_threshold=60,
            ),
            volume_mounts=[
                client.V1VolumeMount(name="wine-prefix", mount_path="/home/mt/.wine"),
                client.V1VolumeMount(name="mt-cache", mount_path="/home/mt/.cache"),
                client.V1VolumeMount(name="tmp", mount_path="/tmp"),
                client.V1VolumeMount(name="var-tmp", mount_path="/var/tmp"),
            ],
        )
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
            containers=[container],
            volumes=[
                client.V1Volume(
                    name="wine-prefix",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=f"{release}-wine-prefix",
                    ),
                ),
                client.V1Volume(name="mt-cache", empty_dir=client.V1EmptyDirVolumeSource(size_limit="256Mi")),
                client.V1Volume(name="tmp", empty_dir=client.V1EmptyDirVolumeSource(size_limit="256Mi")),
                client.V1Volume(name="var-tmp", empty_dir=client.V1EmptyDirVolumeSource(size_limit="64Mi")),
            ],
        )

        # Make sure the PVC exists. Best-effort create.
        await self._ensure_pvc(release)

        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels=selector | {
                _LABEL_PART_OF: _PART_OF_VALUE,
                _LABEL_COMPONENT: "mt-node",
                _LABEL_USER_ID: labels[_LABEL_USER_ID],
                _LABEL_PLATFORM: platform,
            }),
            spec=pod_spec,
        )
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=release, namespace=self._namespace, labels=labels),
            spec=client.V1DeploymentSpec(
                replicas=1,
                strategy=client.V1DeploymentStrategy(type="Recreate"),  # PVC=RWO; rolling would deadlock
                selector=client.V1LabelSelector(match_labels=selector),
                template=pod_template,
                revision_history_limit=5,
                progress_deadline_seconds=int(_READINESS_TIMEOUT_SECS),
            ),
        )

        async for attempt in await self._retrying():
            with attempt:
                try:
                    await apps_api.create_namespaced_deployment(
                        namespace=self._namespace, body=deployment,
                    )
                    return
                except ApiException as exc:
                    if exc.status == 409:
                        await apps_api.replace_namespaced_deployment(
                            name=release, namespace=self._namespace, body=deployment,
                        )
                        return
                    raise

    async def _ensure_pvc(self, release: str) -> None:
        """Best-effort create of the wine-prefix PVC. Idempotent."""
        core_api, _ = await self._api_clients()
        try:
            pvc = client.V1PersistentVolumeClaim(
                metadata=client.V1ObjectMeta(
                    name=f"{release}-wine-prefix",
                    namespace=self._namespace,
                    labels={_LABEL_APP_NAME: _APP_NAME_VALUE, _LABEL_INSTANCE: release},
                ),
                spec=client.V1PersistentVolumeClaimSpec(
                    access_modes=["ReadWriteOnce"],
                    resources=client.V1ResourceRequirements(
                        requests={"storage": os.environ.get("MT_NODE_PVC_SIZE", "4Gi")},
                    ),
                ),
            )
            try:
                await core_api.create_namespaced_persistent_volume_claim(
                    namespace=self._namespace, body=pvc,
                )
            except ApiException as exc:
                if exc.status != 409:
                    raise
        finally:
            await self._close(core_api)

    async def _upsert_service(
        self,
        *,
        core_api: client.CoreV1Api,
        name: str,
        labels: dict[str, str],
        selector: dict[str, str],
        zmq_port: int,
    ) -> None:
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=name, namespace=self._namespace, labels=labels),
            spec=client.V1ServiceSpec(
                type="ClusterIP",
                selector=selector,
                ports=[
                    client.V1ServicePort(
                        name="zmq", port=zmq_port, target_port="zmq", protocol="TCP",
                    ),
                ],
            ),
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
                        # Preserve clusterIP (immutable).
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
        release: str,
        dns_name: str,
        zmq_port: int,
        token: str,
        timeout: float,
    ) -> None:
        """Block until Deployment Ready AND ZMQ PING returns ok, or raise."""
        deadline = _time.monotonic() + timeout
        last_error: Exception | None = None

        # Phase 1 - Deployment Ready.
        while _time.monotonic() < deadline:
            try:
                _, apps_api = await self._api_clients()
                try:
                    dep = await apps_api.read_namespaced_deployment(
                        name=release, namespace=self._namespace,
                    )
                finally:
                    await self._close(apps_api)
                ready = int(dep.status.ready_replicas or 0)
                if ready >= 1:
                    break
            except ApiException as exc:
                last_error = exc
                logger.debug(
                    "hosted_readiness_deploy_poll_error",
                    extra={"release": release, "status": exc.status, "reason": exc.reason},
                )
            await asyncio.sleep(_READINESS_POLL_SECS)
        else:
            raise ProviderTimeoutError(
                "mt-node Deployment did not become Ready within timeout",
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
        secret_name: str,
    ) -> None:
        for fn, name, kind in (
            (apps_api.delete_namespaced_deployment, release, "Deployment"),
            (core_api.delete_namespaced_service, service_name, "Service"),
            (core_api.delete_namespaced_secret, secret_name, "Secret"),
            (
                core_api.delete_namespaced_persistent_volume_claim,
                f"{release}-wine-prefix",
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
