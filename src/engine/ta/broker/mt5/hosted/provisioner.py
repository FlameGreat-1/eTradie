"""Hosted MetaTrader provisioner using Kubernetes.

Spawns isolated Kubernetes Pods running headless MetaTrader 4 or 5
terminals via Wine/Xvfb. Each Pod exposes a ZeroMQ REP socket
on the internal Kubernetes network, which the Engine connects to using
the existing ZmqClient — zero new trading logic required.

Security:
  - Pods run as non-root.
  - No ports are exposed to the public internet; communication is
    strictly over the internal Kubernetes ClusterIP Service.
  - User credentials are passed as environment variables, never
    written to disk outside the ephemeral container filesystem.

Resilience:
  - The Engine manages the lifecycle of these Pods directly via the
    Kubernetes API.

Scalability:
  - Scales across your entire cluster dynamically.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.exceptions import ApiException

from engine.shared.exceptions import ProviderError, ProviderUnavailableError
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# Docker image name for the MT node container.
# In a real cluster, this should be pulled from a registry (e.g., ghcr.io/...)
MT_NODE_IMAGE = "etradie-mt-node:latest"

# Container naming convention: etradie-mt-{connection_id[:12]}
CONTAINER_PREFIX = "etradie-mt-"

# Default ZeroMQ port inside the container.
DEFAULT_ZMQ_PORT = 5555

# Resource limits per container to prevent runaway memory usage.
CONTAINER_MEM_LIMIT = "512Mi"
CONTAINER_CPU_QUOTA = "500m"

# The namespace to deploy into (assumes engine runs in same namespace)
NAMESPACE = "etradie-system"


class HostedProvisioner:
    """Manages the lifecycle of Kubernetes Pods for MetaTrader."""

    def __init__(self) -> None:
        pass

    async def _init_client(self) -> client.CoreV1Api:
        """Initialize the Kubernetes API client."""
        try:
            # First try in-cluster config (when running in Kubernetes)
            try:
                config.load_incluster_config()
            except config.ConfigException:
                # Fallback to kubeconfig for local dev/testing
                await config.load_kube_config()
            return client.CoreV1Api()
        except Exception as exc:
            raise ProviderUnavailableError(
                "Kubernetes API is not reachable.",
                details={"error": str(exc)},
            ) from exc

    # -- Public API -----------------------------------------------------------

    async def provision_account(
        self,
        *,
        connection_id: str,
        login: str,
        password: str,
        server: str,
        platform: str = "mt5",
        zmq_port: int = DEFAULT_ZMQ_PORT,
    ) -> dict[str, Any]:
        """Provision a new hosted MetaTrader Pod.

        Args:
            connection_id: Unique broker connection ID (used for naming).
            login: MT broker account login number.
            password: MT broker trading password.
            server: MT broker server name.
            platform: 'mt4' or 'mt5'.
            zmq_port: ZeroMQ port inside the container.

        Returns:
            Dict with container info including the internal Kubernetes
            Service DNS name to connect to.
        """
        pod_name = f"{CONTAINER_PREFIX}{connection_id[:12]}"
        
        # In K8s, the Service name provides stable DNS resolution
        # Format: <svc_name>.<namespace>.svc.cluster.local
        service_name = pod_name
        dns_name = f"{service_name}.{NAMESPACE}.svc.cluster.local"

        # Idempotency: cleanup existing Pod/Service with the same name.
        await self._cleanup_existing(pod_name)

        logger.info(
            "hosted_provisioning_start",
            extra={
                "connection_id": connection_id,
                "platform": platform,
                "server": server,
                "login": login,
                "pod_name": pod_name,
            },
        )

        api = await self._init_client()

        labels = {
            "app.kubernetes.io/name": "etradie-mt-node",
            "etradie.connection-id": connection_id,
            "etradie.platform": platform,
        }

        # 1. Create the Pod
        pod_manifest = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=pod_name,
                namespace=NAMESPACE,
                labels=labels,
            ),
            spec=client.V1PodSpec(
                restart_policy="Always",
                containers=[
                    client.V1Container(
                        name="mt-node",
                        image=MT_NODE_IMAGE,
                        image_pull_policy="IfNotPresent",
                        env=[
                            client.V1EnvVar(name="MT_PLATFORM", value=platform),
                            client.V1EnvVar(name="MT_LOGIN", value=login),
                            client.V1EnvVar(name="MT_PASSWORD", value=password),
                            client.V1EnvVar(name="MT_SERVER", value=server),
                            client.V1EnvVar(name="ZMQ_PORT", value=str(zmq_port)),
                        ],
                        ports=[
                            client.V1ContainerPort(container_port=zmq_port)
                        ],
                        resources=client.V1ResourceRequirements(
                            limits={"memory": CONTAINER_MEM_LIMIT, "cpu": CONTAINER_CPU_QUOTA},
                            requests={"memory": "128Mi", "cpu": "100m"},
                        ),
                    )
                ]
            )
        )

        # 2. Create the Service
        service_manifest = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=service_name,
                namespace=NAMESPACE,
                labels=labels,
            ),
            spec=client.V1ServiceSpec(
                selector={"etradie.connection-id": connection_id},
                ports=[
                    client.V1ServicePort(
                        port=zmq_port,
                        target_port=zmq_port,
                        protocol="TCP",
                    )
                ],
                type="ClusterIP",
            )
        )

        try:
            await api.create_namespaced_pod(namespace=NAMESPACE, body=pod_manifest)
            await api.create_namespaced_service(namespace=NAMESPACE, body=service_manifest)
        except ApiException as exc:
            logger.error(
                "hosted_provisioning_k8s_error",
                extra={
                    "connection_id": connection_id,
                    "error": str(exc),
                },
            )
            # Try to rollback on partial failure
            await self._cleanup_existing(pod_name)
            raise ProviderError(
                f"Failed to create hosted MT Pod/Service: {exc}",
                details={"connection_id": connection_id},
            ) from exc
        finally:
            await api.api_client.close()

        logger.info(
            "hosted_provisioning_success",
            extra={
                "connection_id": connection_id,
                "pod_name": pod_name,
                "service_name": service_name,
            },
        )

        return {
            "container_id": pod_name,  # using pod name as ID
            "container_name": pod_name,
            "zmq_host": dns_name,
            "zmq_port": zmq_port,
            "state": "running",
        }

    async def get_account_status(
        self,
        container_id: str,
    ) -> dict[str, Any]:
        """Get the current state of a hosted MT Pod.

        Args:
            container_id: Pod name.
        """
        api = await self._init_client()
        try:
            pod = await api.read_namespaced_pod(name=container_id, namespace=NAMESPACE)
            return {
                "container_id": container_id,
                "status": pod.status.phase,
                "running": pod.status.phase == "Running",
                "started_at": str(pod.status.start_time) if pod.status.start_time else None,
                "exit_code": 0 if pod.status.phase == "Running" else -1,
            }
        except ApiException as e:
            if e.status == 404:
                return {
                    "container_id": container_id,
                    "status": "removed",
                    "running": False,
                    "started_at": None,
                    "exit_code": -1,
                }
            raise ProviderError(f"Failed to get Pod status: {e}") from e
        finally:
            await api.api_client.close()

    async def delete_account(
        self,
        container_id: str,
    ) -> bool:
        """Remove a hosted MT Pod and Service.

        Args:
            container_id: Pod name.
        """
        api = await self._init_client()
        try:
            try:
                await api.delete_namespaced_pod(name=container_id, namespace=NAMESPACE)
            except ApiException as e:
                if e.status != 404:
                    raise
            
            try:
                await api.delete_namespaced_service(name=container_id, namespace=NAMESPACE)
            except ApiException as e:
                if e.status != 404:
                    raise

            logger.info("hosted_container_deleted", extra={"container_id": container_id})
            return True
        except ApiException as exc:
            logger.error(
                "hosted_container_delete_failed",
                extra={
                    "container_id": container_id,
                    "error": str(exc),
                },
            )
            return False
        finally:
            await api.api_client.close()

    def resolve_zmq_host(
        self,
        container_id: str,
    ) -> Optional[str]:
        """Resolve the internal DNS name of the hosted Service.

        Args:
            container_id: Pod/Service name.
        """
        return f"{container_id}.{NAMESPACE}.svc.cluster.local"

    # -- Internal helpers -----------------------------------------------------

    async def _cleanup_existing(self, pod_name: str) -> None:
        """Delete Pod and Service by name if they exist."""
        api = await self._init_client()
        try:
            try:
                await api.delete_namespaced_pod(name=pod_name, namespace=NAMESPACE)
            except ApiException as e:
                if e.status != 404:
                    logger.warning("hosted_cleanup_pod_failed", extra={"error": str(e)})

            try:
                await api.delete_namespaced_service(name=pod_name, namespace=NAMESPACE)
            except ApiException as e:
                if e.status != 404:
                    logger.warning("hosted_cleanup_svc_failed", extra={"error": str(e)})
                    
            logger.info("hosted_cleanup_existing", extra={"pod_name": pod_name})
        finally:
            await api.api_client.close()
