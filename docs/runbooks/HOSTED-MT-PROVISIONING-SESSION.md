# Hosted-MT (Wine) Provisioning — Root Cause + Fix Runbook

**Status:** ROOT CAUSE CONFIRMED. Fix in progress.

This file supersedes all prior "resume here" notes. The earlier
hypotheses (missing `servers.dat` entries, re-zipped Deriv bundle, the
no-`Symbol=` chart wall, `#15b` startup.ini-not-honored) are **closed as
WRONG**. They were symptoms read at the wrong layer. The real, proven
blocker is the **MetaTrader 5 LiveUpdate self-restart loop**.

Environment: staging Contabo box `vmi3362776` / `13.140.164.173`, k3s
`v1.30.4+k3s1`, namespace `etradie-system`, engine deploy
`deploy/etradie-engine`, current image SHA `1735eeea`.

---

## 0. The problem, in one paragraph

Every hosted MT pod is stuck in an infinite restart loop because MT5
(`terminal64.exe`, build 5836) runs **LiveUpdate** on every boot: ~60s
in it contacts MetaQuotes' update servers, downloads a component
(`mt5onnx64`, ~15MB), and **self-restarts to apply it** (process exit
`143`). The in-pod supervisor relaunches it, and the cycle repeats
forever. Because the terminal never reaches the stage where it opens a
chart and loads the ZeroMQ EA, the EA's `OnInit` never runs, `:5555`
never binds, the watchdog `/healthz` never goes green, the pod never
reaches `3/3 Ready`, and the engine's 300s readiness gate expires and
tears the tenant down with `status=failed`. This is **broker-agnostic**:
Deriv and Exness fail identically.

---

## 1. Evidence trail (how this was proven, not guessed)

### 1.1 Cross-broker control
Deriv (`broker_id=deriv`, `Deriv-Demo`) and Exness (`broker_id=exness`,
`Exness-MT5Real9`) were both provisioned. **Identical** failure
signature on both:
```
build 5836 started
full recompilation finished: 0 file(s) compiled
LiveUpdate  new version build 5833 ... is available
LiveUpdate  'mt5onnx64' downloaded and updated (14688 kb)
Terminal    build 5836 started      <- self-restart (exit 143)
... repeats; restart_count climbs 0,1,2,...
```
Two unrelated brokers, one signature => the cause is platform-level
(the terminal updating itself), NOT broker config / servers.dat /
symbol. This single comparison invalidated every per-broker theory.

### 1.2 The existing disable does nothing
`entrypoint.sh` + the Dockerfile pin `[LiveUpdate] LastBuildDataPath=5836`
in `config/terminal.ini` (defect #15 "fix"). Confirmed on the live pod:
the key IS present in the exact `terminal.ini` the terminal reads
(`$MT_DIR/config/terminal.ini`, the only one in the prefix), and
LiveUpdate **still runs**. So `LastBuildDataPath` is the WRONG mechanism
for build 5836. This "fix" was never actually verified to work and does
not.

### 1.3 startup.ini / EA / servers.dat are all FINE
- `ps`: `terminal64.exe /config:.../config/startup.ini` launched correctly.
- `startup.ini`: `[Common] Login/Password/Server` correct,
  `[Charts] Template=expert`, `[Experts]` correct.
- EA present (`MQL5/Experts/ZeroMQ_EA.ex5`), `expert.tpl` written with
  `name=ZeroMQ_EA`.
- `servers.dat` installed from the bundle. (The earlier `grep -i deriv`
  returning 0 is a red herring: MT5's `servers.dat` is binary/obfuscated
  and not plain-ASCII/UTF-16 greppable; the bundle's `Bases/<server>/`
  tree proves the bake DID connect once.)
None of these are the blocker. The terminal simply never gets far enough
to use them because LiveUpdate kills it first.

### 1.4 LiveUpdate uses HARDCODED IPs (DNS/hosts block proven useless)
Applied `hostAliases: download.mql5.com -> 127.0.0.1` to the StatefulSet
and booted clean. `/etc/hosts` carried the sinkhole, yet the terminal
still connected to MetaQuotes on :443 and LiveUpdate still downloaded.
Observed peers (`/proc/net/tcp`, :01BB = 443):
```
104.18.50.34    (Cloudflare CDN — download.mql5.com; the component fetch)
194.164.179.28  (MetaQuotes access-server range)
194.164.179.33  (MetaQuotes access-server range)
66.203.112.227  (MetaQuotes)
36.255.79.249   (MetaQuotes APAC edge)
94.130.2.36     (MetaQuotes / Hetzner)
```
Conclusion: the updater dials by IP, bypassing DNS. Therefore
`hostAliases` (and any FQDN/hostname NetworkPolicy) is INSUFFICIENT on
its own. Only a CIDR-based egress control can stop an IP-dialing updater.

> CAUTION: `194.164.179.x` is MetaQuotes' access-server range, which may
> ALSO carry the broker login/discovery hop for MetaQuotes-hosted
> servers. A naive "block all MetaQuotes ranges" risks killing the
> broker connection too. The block must be precise (separate the
> updater CDN hit from the broker access hop) OR inverted to a
> broker-only allowlist (see §3).

---

## 2. OPEN verification before Layer 2 is trusted (do this first)

k3s bundles a NetworkPolicy controller (kube-router) INSIDE the server
process; it is enforced by default unless k3s was started with
`--disable-network-policy`. This was NOT yet cleanly confirmed (the
deny-all test polled a pod that was mid-restart). Confirm enforcement
empirically BEFORE writing the real egress policy, because a silently-
ignored NetworkPolicy (e.g. Flannel-only, no controller) would make all
of Layer 2 a no-op:

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
REL=$(kubectl -n etradie-system get statefulset -o name | grep 'etradie-mt-' | head -1 | cut -d/ -f2)

# deny-all-egress-except-DNS, then boot clean and WAIT for Running
cat <<'EOF' | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: ztest-denyegress, namespace: etradie-system }
spec:
  podSelector: { matchLabels: { app.kubernetes.io/name: etradie-mt-node } }
  policyTypes: [Egress]
  egress:
    - to: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } } }]
      ports: [{ protocol: UDP, port: 53 }, { protocol: TCP, port: 53 }]
EOF
kubectl -n etradie-system delete pod "${REL}-0"
kubectl -n etradie-system wait --for=condition=ContainersReady pod "${REL}-0" --timeout=180s 2>/dev/null || true
sleep 75
kubectl -n etradie-system exec "${REL}-0" -c mt-node -- sh -c \
  'cat /proc/net/tcp | awk "NR>1 && \$3 ~ /:01BB/{print \$3\" \"\$4}"'
kubectl -n etradie-system delete networkpolicy ztest-denyegress
```
- :01BB MetaQuotes peers VANISH => NetworkPolicy IS enforced => Layer 2
  (CIDR egress) is viable. PROCEED with §3.
- :01BB peers PERSIST => NetworkPolicy NOT enforced on this cluster =>
  Layer 2 is a no-op; the fix must be an egress gateway / proxy or a
  cluster-level policy-controller fix. STOP and escalate.

---

## 3. The enterprise fix (layered, all in code, automatic for every tenant)

NO per-user manual steps, ever. Both render paths
(`src/engine/ta/broker/mt5/hosted/provisioner.py::_upsert_statefulset`
and `helm/mt-node/templates/statefulset.yaml`) must change in parity.

### Layer 2 (PRIMARY, app-proof) — default-deny egress + broker allowlist
The robust control is NOT whack-a-mole on MetaQuotes update IPs (they
failover). Invert it: **deny all egress except cluster DNS, the linkerd
control plane, and the broker entity's published trade-server CIDRs on
443/1950/1951.** The pod can then reach its broker and NOTHING else, so
LiveUpdate (any IP, Cloudflare or MetaQuotes) is dead by construction.
- Add broker access-server CIDRs to the broker catalog
  (`infrastructure/broker-catalog/<brand>.json`) per entity, alongside
  the existing server name lists.
- Render them into the per-tenant NetworkPolicy egress via the chart +
  provisioner.
- REQUIRES the §2 enforcement confirmation AND a correlated capture
  separating updater CDN IPs from broker-login IPs so the allowlist is
  correct (the broker hop must stay open).

### Layer 1 (config disable, RE-ASSERTED EVERY BOOT — not baked once)
MT5 rewrites its own `common.ini`/`terminal.ini` on shutdown (proven:
the `awk` edit was clobbered, and the baked `LastBuildDataPath` drifts).
So `entrypoint.sh` MUST rewrite the disable config FRESH immediately
before each `wine terminal64.exe` launch — idempotent enforcement, not
an image property. Candidate keys to set every boot (low confidence
alone; defense-in-depth only): `common.ini [Common] Source=` neutralised,
and keep the `terminal.ini` pin as harmless tertiary. Do NOT rely on
this layer by itself — §1.4 proves the updater ignores config.

### Layer 3 (hostAliases sinkhole) — cheap DNS backstop, ships regardless
`download.mql5.com`/`www.mql5.com`/`mql5.com` -> 127.0.0.1 in the
PodSpec (both render paths). Proven INSUFFICIENT alone (§1.4) but
harmless and closes the DNS path if a future build uses it.

### Layer 4 (operability) — loud, LiveUpdate-aware failure, ships regardless
The supervisor already caps at MAX_INPOD_RESTARTS=5 / 300s then exits
for a kubelet pod restart, but it cannot tell a LiveUpdate self-restart
from a crash, so it loops blindly. Make `entrypoint.sh` detect the
LiveUpdate-driven `exit 143` pattern and emit a distinct, loud failure
(`mt-node: LiveUpdate self-restart detected; egress block likely not
effective`) so this symptom is never misdiagnosed again and fails fast
rather than silently burning the 300s gate.

---

## 4. Files the fix touches

- `helm/mt-node/values.yaml` + `helm/mt-node/templates/statefulset.yaml`
  — NetworkPolicy egress (Layer 2) + hostAliases (Layer 3) + (Layer 2
  consumes broker CIDRs from values rendered by the engine).
- `src/engine/ta/broker/mt5/hosted/provisioner.py` `_upsert_statefulset`
  — hostAliases + (if NP rendered here) egress, in parity with the chart.
- `infrastructure/broker-catalog/*.json` + `src/engine/ta/broker/registry.py`
  — per-entity broker access-server CIDR allowlist.
- `docker/mt-node/entrypoint.sh` — Layer 1 re-assert every boot + Layer 4
  loud failure; correct the false `LastBuildDataPath` comments.
- `docker/mt-node/Dockerfile` — correct the false defect-#15 comments
  (the bake-time pin is NOT the disable mechanism).
- `MT5_Multi_Broker_Provisioning_Architecture.md` — supersede the
  servers.dat root-cause claim with the LiveUpdate finding.

---

## 5. Operator routine (unchanged)

```bash
# Terminal 1: SSH tunnel to the K3s API
ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173
# Terminal 2:
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes        # vmi3362776 Ready => tunnel live
```

Cleanup a failed tenant before re-provisioning (quota is 1/user):
```bash
kubectl -n etradie-system delete statefulset,svc,sa,configmap,pvc \
  -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE connection_type='hosted' AND status IN ('failed','provisioning','active') RETURNING id;"
```

---

## 6. Quick fault map (updated)

| Symptom | Meaning |
|---|---|
| Journal: `LiveUpdate ... downloaded` then `build 5836 started` again; restart_count climbing; `:5555 not bound` | THE root cause: LiveUpdate self-restart loop. Fix = §3 egress block. |
| `/etc/hosts` has `download.mql5.com 127.0.0.1` but :443 to MetaQuotes IPs still appears | Updater dials by IP; hostAliases insufficient; need CIDR egress (§2/§3). |
| `ztest-denyegress` applied and :01BB peers persist | NetworkPolicy NOT enforced on this cluster; Layer 2 is a no-op — escalate. |
| `0 file(s) compiled` then silence, no LiveUpdate line | Different issue; do NOT assume LiveUpdate — re-capture. |
