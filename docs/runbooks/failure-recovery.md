# Section 8 - Failure Recovery Runbook

Operator-facing recovery procedures for the four CHECKLIST Section 8
disaster scenarios. The engine's `HostedRecoveryService` automates
most of these; this runbook covers the diagnostic signal and the
manual escalation path when automation does not heal within the
expected window.

---

## Automated recovery architecture

Three independent layers handle mt-node failures:

| Layer | Owner | Failure mode handled |
|---|---|---|
| In-pod supervisor (`docker/mt-node/entrypoint.sh`) | The Pod itself | MT5/MT4 process crash; Wine prefix corruption; up to 5 restarts per 5-min window |
| Watchdog sidecar (`docker/mt-node/watchdog.py`) | The Pod itself | Memory soft-cap; CPU soft-cap; EA disconnect; broker disconnect |
| Kubelet | The K8s node | Pod liveness probe failure; container OOM kill |
| StatefulSet controller | K8s control plane | Pod deletion; node failure; scheduling |
| `HostedRecoveryService` (this layer) | The engine | StatefulSet missing entirely; StatefulSet stuck not-Ready past the kubelet's backoff envelope |

`HostedRecoveryService` runs an eager sweep on engine startup and a
periodic sweep every `ENGINE_HOSTED_RECOVERY_SWEEP_INTERVAL_SECS`
(default 60s). A StatefulSet is reprovisioned when it is missing OR
has been not-Ready longer than
`ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS` (default 600s).
A per-connection cooldown of
`ENGINE_HOSTED_RECOVERY_REPROVISION_COOLDOWN_SECS` (default 300s)
prevents stampeding a permanently broken connection.

---

## Scenario 1: VPS reboot recovery

**What happens automatically:**

1. Node reboots; K8s control plane marks node `NotReady`.
2. After `--pod-eviction-timeout` (default 5m), the StatefulSet
   controller schedules Pods on healthy nodes (per-tenant Pods
   migrate; their `wine-prefix` PVC is rebound on the new node
   if the StorageClass supports `WaitForFirstConsumer`).
3. The engine pod, if it was on the rebooted node, restarts on a
   healthy node. On boot, lifespan calls
   `HostedRecoveryService.run_once_at_startup()` which sweeps every
   active hosted connection.
4. Any StatefulSet still missing or not-Ready is reprovisioned.

**Expected recovery time:** 5-10 minutes (kubelet eviction +
image pull + Wine startup + ZMQ PING).

**Diagnostic signal:**

```bash
kubectl -n etradie-system get nodes
kubectl -n etradie-system get sts -l app.kubernetes.io/name=etradie-mt-node
kubectl -n etradie-system logs deploy/engine -c engine | grep hosted_recovery_sweep_complete
```

The `hosted_recovery_sweep_complete` log line carries
`phase=startup` and `scanned`/`reprovisioned`/`failed` counts.

**Manual escalation:** if the startup sweep reports `failed > 0`,
find the failing connections:

```bash
kubectl -n etradie-system logs deploy/engine -c engine \
  | grep hosted_recovery_reprovision_failed \
  | jq -r '.connection_id'
```

For each failing connection, inspect the corresponding StatefulSet:

```bash
kubectl -n etradie-system describe sts etradie-mt-<connection_id[:12]>
kubectl -n etradie-system logs sts/etradie-mt-<connection_id[:12]> -c mt-node --tail=200
```

---

## Scenario 2: Network outage recovery

**What happens automatically:**

- ZmqClient detects EA-side disconnect via the heartbeat layer
  (`engine.ta.broker.connectivity.heartbeat`). Reconnect is driven
  by `engine.ta.broker.connectivity.reconnect.ReconnectPolicy`
  with full-jitter exponential backoff (base 1s, cap 30s,
  max 10 attempts).
- Outbound limiter (`outbound_limiter.py`) shields the EA from a
  retry storm when many users are affected at once.
- Tick freshness check (`freshness.py`) rejects stale ticks.

**Expected recovery time:** depends on outage duration. Reconnect
starts within ~1s of network return; up to 10 retries (~5-10 min
worst case) before the engine surfaces a permanent failure.

**Diagnostic signal:**

- Grafana: `etradie_broker_reconnect_attempts_total` rate spikes.
- Logs: `reconnect_policy_retry` entries.

**Manual escalation:**

When reconnect exhausts (`reconnect_policy_exhausted` log entry),
the per-user broker client must be invalidated so the next request
builds a fresh one:

```bash
# Force the engine to rebuild a user's broker client.
curl -X POST -H "X-Internal-Auth: $ENGINE_INTERNAL_SECRET" \
  http://engine.etradie-system.svc.cluster.local:8000/internal/broker/invalidate \
  -d '{"user_id":"<user>"}'
```

If the issue is at the cluster egress (NetworkPolicy or CNI),
check cluster networking before invalidating clients:

```bash
kubectl -n etradie-system get networkpolicy
kubectl -n etradie-system exec deploy/engine -c engine -- \
  curl -sv https://<broker-host>:443
```

---

## Scenario 3: Broker outage recovery

**What happens automatically:**

- Broker returns errors or stops accepting connections.
- The execution service's order placement path catches the broker
  error and surfaces it to the gateway as a `503` with
  `broker_unavailable` reason.
- The execution reconciler logs but does NOT alter engine state
  on a single failed cycle. After 3 consecutive failures the
  connection is marked degraded in the dashboard.
- When the broker returns, the next reconcile cycle adopts the
  broker's view (Section 3 + Section 7 contract).

**Expected behaviour during outage:**

- No orders placed.
- No spurious position deletions (the reconciler does not flip
  positions to closed just because the broker is unreachable).
- Open positions remain in engine memory; reconciliation resumes
  when the broker recovers.

**Diagnostic signal:**

- Alert: `MTNodeBrokerDisconnected` from the mt-node
  PrometheusRule (3 min sustained EA-reported disconnect).
- Logs: `broker_call_failed` with `error_type=ProviderUnavailableError`.

**Manual escalation:**

If the broker is healthy on its status page but the engine still
reports disconnect, force a fresh connection by recycling the
mt-node Pod (which will replay the broker login):

```bash
kubectl -n etradie-system delete pod etradie-mt-<connection_id[:12]>-0
```

The StatefulSet will recreate the Pod; the EA will re-login. The
Wine prefix PVC survives so first-boot is skipped (~30s recovery,
not the cold 3-5min).

---

## Scenario 4: Corrupted terminal recovery

**What happens automatically:**

On Pod boot, `entrypoint.sh` checks the Wine prefix for two
signatures of corruption:

1. Missing `drive_c/windows/system32` directory.
2. Stuck `.update-timestamp.lock` file from a prior
   kill-mid-write.

If either is present, the prefix is wiped and `wineboot --init`
runs to rebuild it. MT5 first-boot then runs cleanly. The Pod's
readiness gate (chart's startupProbe with 320s failure budget)
absorbs this.

**Expected recovery time:** 3-5 minutes (Wine first-boot +
broker re-login).

**Diagnostic signal:**

- Log line: `Wine prefix appears corrupted; resetting`.
- Metric: the Pod's startupProbe success delay extends to several
  minutes for the affected Pod only.

**Manual escalation:**

If the auto-reset path fails (e.g. PVC has filesystem corruption
that persists across Wine wipe), delete the PVC and recycle:

```bash
# Stop the StatefulSet temporarily so the PVC can be deleted.
kubectl -n etradie-system scale sts etradie-mt-<id[:12]> --replicas=0
kubectl -n etradie-system delete pvc wine-prefix-etradie-mt-<id[:12]>-0
kubectl -n etradie-system scale sts etradie-mt-<id[:12]> --replicas=1
```

The StatefulSet will recreate the PVC from the volumeClaimTemplate
and the next Pod boot runs cold-start.

---

## Alert reference (anchors used by PrometheusRule annotations)

### `#reprovisions-high`

Fires when `etradie_hosted_recovery_reprovisions_total` rate >
1/h sustained 2h. Means either external reaping of StatefulSets
or `provision_account` consistently failing the readiness gate.

1. Check for external reaper:
   `kubectl get events -A --sort-by=.lastTimestamp | grep -i sts | head -50`
2. If reaping is from ArgoCD, check sync policy on
   `deployments/argocd/children/mt-node-*.yaml` - the chart
   should NOT be auto-syncing per-tenant StatefulSets (those are
   created by the engine, not GitOps).
3. If no external reaper, check engine logs for
   `hosted_recovery_reprovision_failed`. Common root causes:
   - Image pull failure (registry down).
   - PVC binding stuck (StorageClass quota).
   - Broker login timeout (broker maintenance window).

### `#service-stuck`

Fires when `etradie_hosted_recovery_last_run_timestamp_seconds`
lag exceeds 5 minutes. Sweep loop is wedged.

1. `kubectl rollout restart deploy/engine` is the canonical fix.
2. Capture engine pod logs first so the wedge cause is preserved:
   `kubectl logs deploy/engine -c engine --previous > engine-wedge.log`
3. File a bug if the wedge recurs.

### `#pods-unhealthy-persistent`

Fires when `etradie_hosted_recovery_pods_unhealthy > 0` for 30m.
Recovery attempts are landing but the resulting Pods are not
becoming Ready.

1. List the affected connections from engine logs.
2. For each, inspect the Pod's events:
   `kubectl describe pod etradie-mt-<id[:12]>-0`
3. Common causes:
   - Bad broker credentials (re-prompt user via dashboard).
   - Resource quota exhausted (`kubectl describe ns etradie-system`).
   - PVC stuck Pending (StorageClass capacity issue).
