# mt-node CPU pinning runbook

Operator procedure for enabling exclusive-core pinning on production
mt-node Pods. This is the chart-side fix for CHECKLIST Section 1
'Indicator recalculation spikes do not freeze system' + the audit's
`⚠️ Load balancing across cores` warning.

The chart half is already done: `helm/mt-node/values-production.yaml`
renders every per-tenant Pod with Guaranteed QoS + integer CPU on
the mt-node container. This runbook documents the kubelet half.

## Why pinning matters for an MT terminal

MT5 indicators run on OnTimer callbacks at TIMER_MS cadence (default
50ms). The EA's expected behaviour is exactly one OnTimer tick per
50ms wall-clock interval. The Linux CFS scheduler tries hard to keep
that promise but, when other workloads on the same node compete for
cores, the cadence can slip to 200-500ms. From the broker's
perspective the EA's HEALTH replies arrive late; from the strategy's
perspective the entry signal fires AFTER the price has moved.

The watchdog's CPU soft-cap (`mt_node_watchdog_cpu_soft_cap_trips_total`)
catches the failure mode AFTER it has already affected trading. CPU
pinning prevents the saturation in the first place: by binding each
mt-node container to its own exclusive cores, no neighbouring workload
can steal them.

## Cluster pre-requisites

The kubelet must run with `--cpu-manager-policy=static`. This is a
NODE-LEVEL flag, not a Pod-level one. Enabling it requires:

1. Sufficient unallocated cores. The static CPU manager reserves
   shared-pool cores for system Pods + the kubelet itself. Plan for:
     reserved_cores = ceil(node_total / 16)  # ~1 core per 16
     shared_pool    = max(2, reserved_cores)
     pinnable_cores = node_total - shared_pool

2. `--reserved-cpus` (or `--kube-reserved` + `--system-reserved`)
   set on the kubelet so the shared pool is bounded.

3. A node-pool drain + kubelet restart on every node. Workloads do
   NOT need to be deleted; they reschedule onto remaining nodes
   during the drain.

## Enabling on the production cluster

```bash
# 1. Verify current policy on a sample node.
kubectl debug node/<node-name> -it --image=busybox -- \
  cat /host/var/lib/kubelet/cpu_manager_state 2>/dev/null || \
  echo "cpu_manager_state file absent - policy is 'none'"

# Expected output BEFORE the change: 'cpu_manager_state file absent'.
# AFTER the change: a JSON document listing exclusive-core assignments.

# 2. For OCI OKE: update the node-pool's kubelet config via the OCI
#    console / terraform module. The exact knob is
#    nodeKubeletConfig.cpuManagerPolicy='static'.
#    For Contabo K3s or any vanilla cluster: edit
#    /etc/systemd/system/kubelet.service.d/10-cpu-manager.conf on
#    every node:
#
#      [Service]
#      Environment="KUBELET_CPU_MANAGER_ARGS=\\
#         --cpu-manager-policy=static \\
#         --reserved-cpus=0-1\"
#
#    Then on each node, in turn:
#      kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
#      systemctl daemon-reload && systemctl restart kubelet
#      kubectl uncordon <node>
#
# 3. Verify a fresh mt-node Pod gets exclusive cores.
kubectl -n etradie-system delete pod etradie-mt-<id[:12]>-0
kubectl -n etradie-system wait pod etradie-mt-<id[:12]>-0 \
  --for=condition=Ready --timeout=5m
kubectl -n etradie-system exec etradie-mt-<id[:12]>-0 -c mt-node -- \
  cat /sys/fs/cgroup/cpuset.cpus.effective
# Expected: a non-empty CPU range like '4-5' (two specific cores),
# NOT the full '0-15' that an unpinned Pod gets.
```

## Verifying the chart side

The chart produces a Guaranteed Pod when `kubectl describe pod`
shows:

```
QoS Class: Guaranteed
```

If you see `QoS Class: Burstable`, one of the containers has
unequal requests/limits. Diff the rendered Pod spec against
`helm/mt-node/values-production.yaml`; the mt-node + watchdog
container resource blocks should match exactly.

## Rollback

If the static CPU manager is destabilising a node pool (e.g.
over-provisioning errors, kubelet restart loops), the rollback is
chart-only:

```bash
# 1. Revert mt-node Pods to Burstable QoS by overriding the
#    production overlay.
helm upgrade etradie-mt-platform helm/mt-node \
  -f helm/mt-node/values.yaml \
  -f helm/mt-node/values-production.yaml \
  --set resources.requests.cpu=500m \
  --set resources.limits.cpu=1500m

# 2. The kubelet flag can stay on; Burstable Pods just run in the
#    shared pool. There is no urgency to revert the kubelet side.
```

The watchdog's CPU soft-cap continues to catch saturation incidents
in the Burstable mode; pinning is the OPTIMISATION, not the safety
net.

## Why 2 cores, not 1 or 4

From the production-soak test data referenced in the audit
(`tests/chaos/test_mt_node_soak.py`):

- p50 mt-node CPU under steady load: 0.3 cores
- p95 under steady load: 0.8 cores
- p95 during indicator recalc burst: 1.4 cores
- p99 during indicator recalc burst: 1.7 cores

2 cores gives ~15% headroom over p99, ~40% headroom over p95. 1 core
would throttle on every burst (regression to the failure mode this
commit addresses). 4 cores would be 2.5x over-provisioned and double
the per-tenant cost.

For tenants running an unusually heavy indicator load (e.g. a custom
NN-based EA that pegs CPU), the per-tenant override path is:

  `helm upgrade <tenant-release> --set resources.requests.cpu="4" --set resources.limits.cpu="4" --set resources.requests.memory="4Gi" --set resources.limits.memory="4Gi"`

Documented in the per-tenant tier matrix (separate operator doc).
