#!/usr/bin/env python3
"""Daily VolumeSnapshot pass for every mt-node Wine prefix PVC.

Invoked by the helm/mt-node CronJob template once per day. Idempotent
and safe to run more frequently if the operator changes the schedule.

Contract:
  - Lists every PVC in MT_NODE_NAMESPACE labeled
      app.kubernetes.io/name=etradie-mt-node AND
      app.kubernetes.io/component=wine-prefix
  - For each PVC, creates a VolumeSnapshot named
      <pvc>-<YYYYMMDD-HHMMSS>
    referencing the VolumeSnapshotClass named by
    MT_NODE_SNAPSHOT_CLASS_NAME.
  - Sweeps every existing VolumeSnapshot in MT_NODE_NAMESPACE labeled
      snapshotter=etradie-mt-node
    and deletes those whose creationTimestamp is older than
    MT_NODE_SNAPSHOT_RETENTION_DAYS.
  - Exits non-zero when ANY snapshot creation fails (so the CronJob's
    backoffLimit retries) but treats individual delete failures as
    soft-fail (an orphan snapshot from a previous failed prune is
    cheaper than a missing daily backup).

Environment contract:
  MT_NODE_NAMESPACE                  (default 'etradie-system')
  MT_NODE_SNAPSHOT_CLASS_NAME        (REQUIRED - no safe default)
  MT_NODE_SNAPSHOT_RETENTION_DAYS    (default '7')

The ServiceAccount this Pod runs under is
`etradie-mt-node-snapshotter` (see
helm/mt-node/templates/serviceaccount-snapshotter.yaml). Its Role
grants exactly:
  - persistentvolumeclaims: get, list
  - snapshot.storage.k8s.io/volumesnapshots: get, list, create, delete
Nothing else. No cluster-scoped verbs.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.exceptions import ApiException

_LABEL_APP_NAME = "app.kubernetes.io/name"
_LABEL_COMPONENT = "app.kubernetes.io/component"
_LABEL_SNAPSHOTTER = "snapshotter"
_SNAPSHOTTER_LABEL_VALUE = "etradie-mt-node"

_SNAPSHOT_API_GROUP = "snapshot.storage.k8s.io"
_SNAPSHOT_API_VERSION = "v1"
_SNAPSHOT_PLURAL = "volumesnapshots"


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default if default is not None else "").strip()
    if not value and default is None:
        print(f"FATAL: required env var {name} is not set", file=sys.stderr)
        sys.exit(2)
    return value


async def _load_kube_config() -> None:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        await config.load_kube_config()


async def _list_wine_prefix_pvcs(
    core_api: client.CoreV1Api, namespace: str
) -> list[client.V1PersistentVolumeClaim]:
    label_selector = (
        f"{_LABEL_APP_NAME}=etradie-mt-node,"
        f"{_LABEL_COMPONENT}=wine-prefix"
    )
    resp = await core_api.list_namespaced_persistent_volume_claim(
        namespace=namespace,
        label_selector=label_selector,
    )
    return resp.items


def _build_snapshot_manifest(
    pvc_name: str,
    snapshot_name: str,
    snapshot_class: str,
    namespace: str,
    release: str,
) -> dict:
    return {
        "apiVersion": f"{_SNAPSHOT_API_GROUP}/{_SNAPSHOT_API_VERSION}",
        "kind": "VolumeSnapshot",
        "metadata": {
            "name": snapshot_name,
            "namespace": namespace,
            "labels": {
                _LABEL_APP_NAME: "etradie-mt-node",
                _LABEL_COMPONENT: "wine-prefix-snapshot",
                _LABEL_SNAPSHOTTER: _SNAPSHOTTER_LABEL_VALUE,
                "app.kubernetes.io/instance": release,
            },
            "annotations": {
                "etradie.io/source-pvc": pvc_name,
                "etradie.io/snapshot-reason": "daily-wine-prefix-backup",
            },
        },
        "spec": {
            "volumeSnapshotClassName": snapshot_class,
            "source": {
                "persistentVolumeClaimName": pvc_name,
            },
        },
    }


async def _create_snapshot(
    custom_api: client.CustomObjectsApi,
    namespace: str,
    manifest: dict,
) -> None:
    name = manifest["metadata"]["name"]
    try:
        await custom_api.create_namespaced_custom_object(
            group=_SNAPSHOT_API_GROUP,
            version=_SNAPSHOT_API_VERSION,
            namespace=namespace,
            plural=_SNAPSHOT_PLURAL,
            body=manifest,
        )
        print(f"  created VolumeSnapshot/{name}")
    except ApiException as exc:
        if exc.status == 409:
            print(f"  VolumeSnapshot/{name} already exists (skipping)")
            return
        raise


async def _prune_old_snapshots(
    custom_api: client.CustomObjectsApi,
    namespace: str,
    retention_days: int,
) -> tuple[int, int]:
    """Returns (deleted_count, failure_count)."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=retention_days)
    label_selector = f"{_LABEL_SNAPSHOTTER}={_SNAPSHOTTER_LABEL_VALUE}"
    try:
        result = await custom_api.list_namespaced_custom_object(
            group=_SNAPSHOT_API_GROUP,
            version=_SNAPSHOT_API_VERSION,
            namespace=namespace,
            plural=_SNAPSHOT_PLURAL,
            label_selector=label_selector,
        )
    except ApiException as exc:
        print(f"  WARN: list VolumeSnapshots failed: {exc.reason} (status {exc.status})")
        return (0, 1)

    deleted = 0
    failures = 0
    for item in result.get("items", []):
        name = item.get("metadata", {}).get("name", "")
        created_str = item.get("metadata", {}).get("creationTimestamp", "")
        if not name or not created_str:
            continue
        try:
            # K8s timestamps end with 'Z' - normalise to UTC.
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if created >= cutoff:
            continue
        try:
            await custom_api.delete_namespaced_custom_object(
                group=_SNAPSHOT_API_GROUP,
                version=_SNAPSHOT_API_VERSION,
                namespace=namespace,
                plural=_SNAPSHOT_PLURAL,
                name=name,
            )
            print(f"  pruned VolumeSnapshot/{name} (age > {retention_days}d)")
            deleted += 1
        except ApiException as exc:
            if exc.status == 404:
                continue
            print(
                f"  WARN: delete VolumeSnapshot/{name} failed: "
                f"{exc.reason} (status {exc.status})"
            )
            failures += 1
    return (deleted, failures)


async def main_async() -> int:
    namespace = _env("MT_NODE_NAMESPACE", "etradie-system")
    snapshot_class = _env("MT_NODE_SNAPSHOT_CLASS_NAME")
    retention_days_raw = _env("MT_NODE_SNAPSHOT_RETENTION_DAYS", "7")
    try:
        retention_days = int(retention_days_raw)
    except ValueError:
        print(
            f"FATAL: MT_NODE_SNAPSHOT_RETENTION_DAYS must be an int, got {retention_days_raw!r}",
            file=sys.stderr,
        )
        return 2
    if retention_days < 1:
        print(
            f"FATAL: MT_NODE_SNAPSHOT_RETENTION_DAYS must be >= 1, got {retention_days}",
            file=sys.stderr,
        )
        return 2

    print(
        f"[snapshot-wine-prefixes] namespace={namespace} "
        f"snapshot_class={snapshot_class} retention_days={retention_days}"
    )

    await _load_kube_config()
    core_api = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()
    failures = 0
    snapshots_created = 0
    try:
        pvcs = await _list_wine_prefix_pvcs(core_api, namespace)
        print(f"[snapshot-wine-prefixes] discovered {len(pvcs)} Wine prefix PVCs")

        date_suffix = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
        for pvc in pvcs:
            pvc_name = pvc.metadata.name
            release = (pvc.metadata.labels or {}).get(
                "app.kubernetes.io/instance", pvc_name
            )
            snapshot_name = f"{pvc_name}-{date_suffix}"
            manifest = _build_snapshot_manifest(
                pvc_name=pvc_name,
                snapshot_name=snapshot_name,
                snapshot_class=snapshot_class,
                namespace=namespace,
                release=release,
            )
            try:
                await _create_snapshot(custom_api, namespace, manifest)
                snapshots_created += 1
            except ApiException as exc:
                print(
                    f"  ERROR: create VolumeSnapshot/{snapshot_name} failed: "
                    f"{exc.reason} (status {exc.status})",
                    file=sys.stderr,
                )
                failures += 1
            except Exception as exc:  # noqa: BLE001
                print(
                    f"  ERROR: create VolumeSnapshot/{snapshot_name} unexpected: {exc}",
                    file=sys.stderr,
                )
                failures += 1

        deleted, prune_failures = await _prune_old_snapshots(
            custom_api, namespace, retention_days,
        )
        print(
            f"[snapshot-wine-prefixes] created={snapshots_created} "
            f"pruned={deleted} create_failures={failures} prune_failures={prune_failures}"
        )
    finally:
        try:
            await core_api.api_client.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await custom_api.api_client.close()
        except Exception:  # noqa: BLE001
            pass

    return 1 if failures else 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
