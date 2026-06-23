# Hosted-MT (Wine) Provisioning — Root Cause + Fix Runbook

**Status:** ROOT CAUSE CONFIRMED. All config/DNS disables are DISPROVEN
(see DEAD ENDS below) and have been REVERTED from the codebase. The
Layer 4 self-restart detector is retained. The ONLY working control is
Layer 2 (network egress block), which is the next and final fix.

---

## DEAD ENDS — DO NOT RE-IMPLEMENT (all empirically DISPROVEN)

Every one of these was implemented, deployed to the live cluster on a
real image build, and observed to FAIL (LiveUpdate still downloaded
`mt5onnx64`, terminal self-restarted exit 143, `:5555` never bound).
Do not try them again:

1. **`terminal.ini [LiveUpdate] LastBuildDataPath=5836`** (defect-#15
   original "fix"). Confirmed present in the exact `terminal.ini` the
   terminal reads; LiveUpdate ran anyway. INEFFECTIVE.
2. **`hostAliases` / DNS sinkhole of `download.mql5.com` -> 127.0.0.1.**
   `/etc/hosts` carried the entry; the updater still reached MetaQuotes
   on :443. The updater dials by HARDCODED IP, bypassing DNS.
   INEFFECTIVE.
3. **`common.ini [Common] Source=` empty (+ `NewsEnable=0`), baked into
   the image AND re-asserted every boot, Environment blob preserved.**
   Deployed in image `dfef71bc` (build 5836). Confirmed written in the
   running prefix; entrypoint logged `LiveUpdate Source neutralized`.
   MT5 STILL logged `'mt5onnx64' downloaded` and self-restarted.
   INEFFECTIVE. REVERTED.

**Conclusion: NO in-container config or DNS lever stops LiveUpdate on
build 5836. Stop trying config. The fix is network egress (Layer 2).**

---

## Layer 2 — the ONLY working fix (network egress block)

### Enforcement is CONFIRMED viable
A deny-all-egress-except-DNS NetworkPolicy put the terminal's MetaQuotes
:443 connection into SYN_SENT with no ESTABLISHED => this k3s cluster
DOES enforce NetworkPolicy. CIDR egress control works here.

### The hazard to design around
MetaQuotes-hosted brokers' access servers share the `194.164.179.x`
range with the updater (observed `194.164.179.28` for the Exness broker
hop). A blunt "block MetaQuotes ranges" would sever the broker. The
updater's COMPONENT download is a separate Cloudflare CDN hit
(`download.mql5.com`, observed `104.18.x`); the broker does NOT need
Cloudflare.

### The design (default-deny egress + broker allowlist)
Deny all egress except: cluster DNS, the linkerd control plane, and the
broker entity's published access-server CIDRs on 443/1950/1951. The pod
can then reach ONLY its broker, so LiveUpdate (any IP, Cloudflare or
MetaQuotes) is dead by construction. Implementation:
- Add a per-entity `network_cidrs` allowlist to the broker catalog
  (`infrastructure/broker-catalog/<brand>.json`) + the registry model.
- Render it into the per-tenant NetworkPolicy egress in BOTH
  `helm/mt-node/templates/networkpolicy.yaml` (+ values) AND the engine
  provisioner path, in parity.
- Seed Exness with the observed `194.164.179.0/24`; expand if a broker's
  login probes other ranges (the Layer-4 log will say so).
- Keep cluster DNS + linkerd egress (the pod needs them to start).

> Do NOT ship a blunt MetaQuotes range-block, and do NOT add another
> config/DNS "disable" — see DEAD ENDS.

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

## 4a. Build, roll, and verify the LiveUpdate config fix (step-by-step)

### Step 1 — confirm the fix is on the GitHub tip, then nudge CI
```bash
cd ~/eTradie
git fetch gitlab main && git reset --hard gitlab/main
git push --force-with-lease origin main
# Confirm the fix actually landed on GitHub (cross-remote rebases can drop commits):
git show origin/main:docker/mt-node/entrypoint.sh | grep -n 'LiveUpdate Source neutralized' \
  || echo '!!! FIX MISSING ON GITHUB TIP'
git show origin/main:docker/mt-node/Dockerfile | grep -n 'common.ini.*Source' \
  || echo '!!! Dockerfile fix missing'
# Nudge CI if the tip is a [skip ci] pin or CI did not trigger:
git commit --allow-empty -m 'ci: rebuild mt-node for LiveUpdate Source fix'
git push origin main
```

### Step 2 — wait for CI green, confirm GHCR image, sync ArgoCD
```bash
gh run list --repo FlameGreat-1/eTradie --branch main --limit 5
gh run watch --repo FlameGreat-1/eTradie

cd ~/eTradie
git fetch origin main && git pull --rebase origin main
PIN=$(git show origin/main:helm/engine/values-staging.yaml | grep -E '^[[:space:]]*tag:' | head -1 | tr -d ' "' | cut -d: -f2)
echo "pinned SHA = $PIN"
GH_OWNER=FlameGreat-1; GH_PAT=$(cat ~/.ghcr_pat)
token=$(curl -sS -u "$GH_OWNER:$GH_PAT" "https://ghcr.io/token?service=ghcr.io&scope=repository:flamegreat-1/etradie/mt-node:pull" | jq -r .token)
curl -sS -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $token" \
  -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.v2+json" \
  "https://ghcr.io/v2/flamegreat-1/etradie/mt-node/manifests/$PIN"   # expect 200

export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl -n argocd patch application engine-staging  --type merge -p '{"operation":{"sync":{"revision":"HEAD"}}}'
kubectl -n argocd patch application mt-node-staging --type merge -p '{"operation":{"sync":{"revision":"HEAD"}}}' 2>/dev/null || true
kubectl -n etradie-system rollout status deploy/etradie-engine
kubectl -n etradie-system exec deploy/etradie-engine -c engine -- printenv MT_NODE_IMAGE   # must == $PIN
# Mirror back to GitLab: git push gitlab main
```

### Step 3 — clean, re-provision, and verify (the real test)
```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl -n etradie-system delete statefulset,svc,sa,configmap,pvc \
  -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE connection_type='hosted' AND status IN ('failed','provisioning','active') RETURNING id;"

# Re-provision Exness demo from the dashboard (Exness-MT5Trial9 + valid demo creds), then:
REL=$(kubectl -n etradie-system get statefulset -o name | grep 'etradie-mt-' | head -1 | cut -d/ -f2); echo "$REL"
P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"

# (a) NEW image wrote common.ini Source= with Environment preserved:
kubectl -n etradie-system exec "${REL}-0" -c mt-node -- sh -c "head -6 \"$P/config/common.ini\""
# (b) entrypoint logged the neutralization (and watch for the loud self-restart ERROR):
kubectl -n etradie-system logs "${REL}-0" -c mt-node | grep -iE 'LiveUpdate Source neutralized|LiveUpdate self-restart detected'
# (c) THE VERDICT — no LiveUpdate download, terminal not re-restarting:
kubectl -n etradie-system exec "${REL}-0" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/logs\"/*.log|head -1); tr -d '\000' < \"\$f\" | grep -aiE 'liveupdate|build 5836 started|compiled'"
# (d) :5555 bound + pod Ready:
kubectl -n etradie-system exec "${REL}-0" -c mt-node -- sh -c 'cat /proc/net/tcp|grep -i 15B3 && echo ":5555 LISTEN" || echo "not bound"'
kubectl -n etradie-system get pod "${REL}-0"
```

**Verdict:** no `LiveUpdate ... downloaded` + `:5555 LISTEN` + pod `3/3`
=> config disable WORKS, done. If LiveUpdate STILL downloads (the loud
Layer-4 ERROR fires) => proceed to Layer 2 egress (§2/§3).

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
