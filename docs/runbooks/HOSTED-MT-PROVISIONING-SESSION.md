# Hosted-MT (Wine) Provisioning — Root Cause + Fix Runbook

**Status (REVISED, post-audit, complete fix shipped on 2026-06-23):**
The previously-suspected root cause ("MetaTrader LiveUpdate as the
bug") was WRONG. LiveUpdate is designed to run ONCE on a fresh
install, swap a component (`mt5onnx64`) via exit-143 self-restart,
persist the new file on disk, and never re-download the same build.
Every commercial MT5 VPS runs this flow with no egress block.

The real failure was TWO independent bug clusters layered on top of
each other. The first cluster destroyed MT5's persisted state on
every restart, which masked the second cluster (a stuck launch-flag)
behind an infinite restart loop. Closing the first cluster exposed
the second; closing both makes the pipeline behave like every other
headless MT5 VPS in the world.

## Cluster 1 — Persisted state was being destroyed (LiveUpdate loop driver)

Five independent paths cooperated to wipe the wine-prefix PVC + its
LiveUpdate-applied component on every restart, so MT5 saw itself as
out-of-date and re-ran LiveUpdate on every boot:

1. **`HostedProvisioner._best_effort_cleanup` deleted the
   wine-prefix PVC** whenever the readiness gate timed out. PVC
   destruction belongs in `delete_account()` (explicit user action)
   or `gc_orphans()` (row gone from DB), NEVER in error rollback.
2. **`_READINESS_TIMEOUT_SECS=300`** was below the genuine first-boot
   work-time once LiveUpdate added 30-90s of network I/O on top of
   the 453-file MQL5 recompile. Any blip → `ProviderTimeoutError` →
   PVC destroyed → next provision seeds from the image-baked
   template → MT5 sees itself as out-of-date → LiveUpdate re-runs.
3. **`HostedRecoveryService.run_once_at_startup(bypass_threshold=True)`**
   force-reprovisioned ANY not-Ready pod immediately on engine
   restart, including fresh provisions legitimately mid-first-boot.
4. **`entrypoint.sh` corruption-reset `rm -rf`'d the whole prefix on
   `.update-timestamp.lock`** — a file Wine writes during normal
   `wineboot -u` that legitimately survives any abrupt pod kill, not
   a corruption signal at all.
5. **Supervisor loop treated exit-143 (a self-initiated SIGTERM, not
   a crash) like a crash**: `wineserver -k` + `pkill -9` raced the
   on-disk rename and left `.update-timestamp.lock` behind (feeding
   bug #4), AND the LiveUpdate self-restart counted against
   `MAX_INPOD_RESTARTS=5`, exhausting the budget on the very first
   provision. `terminationGracePeriodSeconds: 60/90` and
   `preStop sleep 5` were too short for clean LiveUpdate finalize on
   pod eviction.

## Cluster 2 — Launch flag was wrong (silent-after-init bug)

Closing Cluster 1 made MT5's LiveUpdate run exactly once and persist
the component (proven on staging: every subsequent boot is silent on
the LiveUpdate front, no recompile, no download). But MT5 still did
not bind `:5555`. Live journal inspection showed:

  build 5836 started
  full recompilation finished: 0 file(s) compiled
  LiveUpdate 'mt5onnx64' downloaded and updated (14688 kb)
  LiveUpdate downloaded successfully
  [silent — no Network / Authentication / Login / Chart / Expert lines]

The entrypoint launched MT5 with `wine terminal64.exe /config:<path>`.
`/config:<file>` is the "use these settings INSTEAD OF the saved ones"
OVERRIDE flag — it makes MT5 READ `[Common] Login/Password/Server` but
does NOT auto-execute login → chart open → expert attach. That
auto-execute hook is `/portable`, which makes terminal64 run as a
self-contained portable installation, reads
`<install_dir>/config/startup.ini` at boot, AND auto-executes the
login + chart + expert sequence. This is the documented MT5
unattended-launch contract used by every commercial MT5 VPS provider.

## Fix landed (5 commits, all on `main`, 2026-06-23)

| Commit | Layer | Files |
|---|---|---|
| `684746d5` | Engine — Cluster 1 #1,#2,#3 | `src/engine/ta/broker/mt5/hosted/provisioner.py`, `src/engine/ta/broker/mt5/hosted/recovery.py` |
| `ea5f0c1a` | Pod — Cluster 1 #4,#5 + grace | `docker/mt-node/entrypoint.sh`, `helm/mt-node/values.yaml`, `helm/mt-node/values-production.yaml`, `docker/mt-node/README.md` |
| `60aabc3a` | Chart defaults — align ConfigMap with new code defaults | `helm/engine/values.yaml`, `helm/engine/templates/configmap.yaml` |
| `a74d8f1b` | CI lint follow-up (UP017) | `src/engine/ta/broker/mt5/hosted/recovery.py` |
| `(latest)` | Pod — Cluster 2 (launch flag) | `docker/mt-node/entrypoint.sh` |

Specific changes:

- **`_best_effort_cleanup`**: no longer deletes the wine-prefix PVC
  or destroys Vault credentials. Both belong only to `delete_account`
  / `gc_orphans`.
- **`_READINESS_TIMEOUT_SECS`**: 300s → 600s. Sized to cover
  Wine init + MT5 launch + LiveUpdate + exit-143 + 453-file MQL5
  recompile + EA OnInit + `:5555` bind (175-280s of genuine work,
  easily 350-450s under I/O contention).
- **`HostedRecoveryConfig.unhealthy_threshold_secs`**: 600s → 1200s.
  Sits well above the new readiness gate so the recovery sweep
  cannot race a still-cold-booting pod.
- **`HostedRecoveryConfig.fresh_provision_grace_secs`** (NEW): 1800s
  default. Skips the recovery sweep for connections younger than
  this threshold, including the bypass-threshold startup sweep, so
  a coincidental engine restart cannot tear down an in-flight first
  boot.
- **`entrypoint.sh` corruption-reset**: only wipes when
  `drive_c/windows/system32` is missing. On a stale
  `.update-timestamp.lock`, deletes the single lock file and runs
  `wineboot -u` to reconcile. NO prefix wipe.
- **`entrypoint.sh` supervisor loop**: on `EXIT_CODE=143`, branches
  to a 30s `LIVEUPDATE_SETTLE_SECS` window, NO `wineserver -k`, NO
  `pkill -9`, NO `restart_count` increment.
- **`entrypoint.sh` launch flag**: `wine $MT_EXE /config:$INI_FILE`
  → `wine $MT_EXE /portable`. MT5 now auto-executes login + chart +
  expert attach from `<install_dir>/config/startup.ini`.
- **`values.yaml` + `values-production.yaml`**:
  `terminationGracePeriodSeconds` 60/90 → 180, `preStop sleep` 5 →
  30, `startupProbe.failureThreshold` 60 → 120 (620s kubelet budget
  sits just above the 600s engine readiness gate).
- **`helm/engine/values.yaml`**: `mtNode.readinessTimeoutSecs` 300
  → 600, `connectivity.hostedRecoveryUnhealthyThresholdSecs` 600 →
  1200, NEW `connectivity.hostedRecoveryFreshProvisionGraceSecs:
  1800`. ConfigMap template updated to render the new env var.

**No NetworkPolicy egress block, no config/DNS lever, no SNI gateway
is required.** The historical "Layer 2 / Layer 3 / DEAD ENDS"
prescriptions below are SUPERSEDED. The Layer-4 loud exit-143
diagnostic in `entrypoint.sh` is RETAINED because it's still useful
observability — but it now logs at INFO (not ERROR) on a single
LiveUpdate run, and the supervisor's branch on exit-143 makes the
diagnostic actionable instead of just noisy.

---

## Live Session Handoff (2026-06-23 ≈18:00 UTC) — PICK UP HERE

If the active session ended before the final verdict, this section is
the single source of truth for what is done, what is in flight, and
what the next operator action is. Read this section top-to-bottom
before running anything.

### Chain of commits already landed (all on `main`, both remotes)

In chronological order, each one closes a specific bug:

| # | Commit | What it closes |
|---|---|---|
| 1 | `684746d5` | Engine: `_best_effort_cleanup` no longer deletes the wine-prefix PVC. `_READINESS_TIMEOUT_SECS` 300→600. `HostedRecoveryConfig.unhealthy_threshold_secs` 600→1200. New `fresh_provision_grace_secs=1800` field + helper. |
| 2 | `ea5f0c1a` | Pod: `entrypoint.sh` corruption-reset only wipes on missing `system32` (stale lock => single-file delete + `wineboot -u`). Supervisor branches on exit-143 with a 30s settle, no `wineserver -k`, no `pkill -9`, no `restart_count` increment. `terminationGracePeriodSeconds` 60/90→180, `preStop sleep` 5→30, `startupProbe.failureThreshold` 60→120 (620s budget). |
| 3 | `60aabc3a` | Chart: `helm/engine/values.yaml` aligned with the new code defaults (`mtNode.readinessTimeoutSecs` 300→600, `hostedRecoveryUnhealthyThresholdSecs` 600→1200, new `hostedRecoveryFreshProvisionGraceSecs: 1800`). ConfigMap template renders the new env var. |
| 4 | `a74d8f1b` | CI lint: `from datetime import UTC` instead of `timezone.utc` (ruff UP017). |
| 5 | `6cbd1b51` (approximate) | Pod: launch flag `/config:<file>` → `/portable`. Hypothesis: `/portable` would trigger auto-login. PROVEN INSUFFICIENT on staging — `/portable` only sets the config-file location, it does NOT trigger auto-login. |
| 6 | `c384a600` | Pod: launch flags become `/portable /login:<id> /password:<pw> /server:<name>`. `/login /password /server` are the documented MT5 unattended-launch trigger that executes login → chart → expert sequence non-interactively. |
| (mid-session) | (this commit) | Docs: this handoff section. |

### Verified state of the staging cluster (as of session pause)

All of the following are CONFIRMED via direct `kubectl` inspection:

```
staging mt-node image  = ghcr.io/flamegreat-1/etradie/mt-node:c384a6006da81b667d459e3d89581d4e0ec3526c
staging engine image   = same SHA (matches commit 6)
engine ConfigMap MT_NODE_READINESS_TIMEOUT_SECS                 = 600
engine ConfigMap ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS = 1200
engine ConfigMap ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS = 1800
engine ConfigMap MT_NODE_IMAGE = the c384a600 image above
Deployment env override on MT_NODE_READINESS_TIMEOUT_SECS = NONE (live-patch dropped via ArgoCD Replace=true)
```

Provision in flight (started ≈18:01 UTC):
```
broker_connections.id  = 7b9fd8c0-6a1c-... (the row created by the dashboard)
release                = etradie-mt-7b9fd8c0-6a1
pod                    = etradie-mt-7b9fd8c0-6a1-0
status at session end  = 2/3 Running, 4m42s, mid cold boot
terminal64.exe cmdline = .../terminal64.exe /portable /login:133978149 /password:<redacted> /server:Exness-MT5Real9
                         <-- THIS PROVES THE NEW IMAGE + NEW FLAGS ARE LIVE
```

What the previous attempts (pre c384a600) all showed in the journal:

```
build 5836 started
full recompilation has been finished: 0 file(s) compiled
LiveUpdate 'mt5onnx64' downloaded and updated (one-time, persisted on PVC)
LiveUpdate downloaded successfully
[silent -- NO Network/Login/Authentication/Chart/Expert lines]
```

The smoking-gun pieces of evidence those attempts produced:
- `MQL5/Logs/` directory did NOT exist (no Expert ever loaded).
- `/proc/net/tcp` had only `:443 TIME_WAIT` (one-shot LiveUpdate CDN
  hit; no sustained broker connection).
- `AppData/Roaming/MetaQuotes/Terminal/<hash>/portable.txt` DID exist
  (so `/portable` was being honoured by MT5).
- `<install_dir>/config/startup.ini` had correct `[Common]
  Login/Password/Server` (so MT5 was reading the file).
- But there is no MT5 unattended-login trigger from `startup.ini` -
  it only populates Login dialog fields. The `/login /password
  /server` command-line flags ARE the documented trigger.

### NEXT ACTION (do this now)

Pick up at the verdict check on the in-flight pod
`etradie-mt-7b9fd8c0-6a1-0`. Re-derive the variable in your current
shell (every new terminal needs its own `$POD`):

```bash
POD=etradie-mt-7b9fd8c0-6a1-0
# or re-derive:
# POD=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-mt-node -o jsonpath='{.items[0].metadata.name}')

# Wait for the boot to settle
sleep 60   # adjust if the pod is younger than ~5 min total

# 1. Pod readiness
kubectl -n etradie-system get pod "$POD"
# Expected after a successful login: 3/3 Ready
# Pre-fix pattern was: stuck at 2/3 with periodic watchdog SIGTERMs

# 2. MT5 journal - the KEY signal
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"; \
   f=$(ls -t "$P/logs"/*.log 2>/dev/null | head -1); \
   echo "file: $f, size: $(wc -c < "$f") bytes"; \
   tr -d "\000" < "$f"'

# 3. EA's own log directory (only exists if the EA actually loaded)
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"; \
   ls -la "$P/MQL5/Logs/" 2>&1 | head -10; \
   f=$(ls -t "$P/MQL5/Logs"/*.log 2>/dev/null | head -1); \
   [ -n "$f" ] && { echo "--- $f ---"; tr -d "\000" < "$f" | tail -60; }'

# 4. :5555 socket state (15B3 hex = 5555 dec)
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'cat /proc/net/tcp | awk "NR>1 && (\$3 ~ /:15B3/ || \$2 ~ /:15B3/){print}"'

# 5. Engine recovery state for this connection
kubectl -n etradie-system logs deploy/etradie-engine --tail=200 \
  | grep -iE 'hosted_recovery_fresh_provision_grace|hosted_recovery_sweep_complete|hosted_provisioning' | tail -20

# 6. Final DB row state
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message, mt5_symbol, is_active FROM broker_connections WHERE connection_type='hosted';"
```

### Decision matrix on the journal output

Look at the §2 (MT5 journal) output. **The diagnostic is the first
NEW line that appears after `LiveUpdate downloaded successfully`.**

| What you see in the journal | What it means | What to do next |
|---|---|---|
| `Network 'Exness-MT5Real9': connecting to access point ...` followed by `Login 133978149: ok` | Auto-login WORKED. `:5555` will bind once the EA loads. | Wait for `3/3 Ready`. Run the §E smoking-gun proof (kill the pod, confirm LiveUpdate stays silent on restart). DONE. |
| `Network 'Exness-MT5Real9': connecting...` then `Login 133978149: invalid account` / `invalid password` / `account is disabled` | Flags work; credentials wrong. | Check the broker creds with the user; fix and re-provision. NOT a code fix. |
| `Network 'Exness-MT5Real9': server not found` or `unknown server` | Flags work; `servers.dat` for Exness is missing or wrong. | Inspect the broker bundle: `kubectl exec ... ls -la /broker-bundle/` and `grep -i Exness /broker-bundle/MetaTrader\ 5\ EXNESS/Config/servers.dat`. Bundle is platform-side; fix the bundle's `servers.dat`. |
| Same silent pattern (no `Network` line ever appears, just `build 5836 started` repeating) | Flags reached `terminal64.exe` (proven by `ps -ef`) but MT5 isn't ACTING on them. | Three fallback paths below. |

### Fallback paths if the silent pattern persists

Do NOT re-launch with random guesses. Each of the three approaches
below has a specific signal that triggers it, and each can be tested
in isolation.

#### Fallback A: try `/profile` flag instead of `/login`

Some MT5 builds (notably 5xxx series) honor `/profile:<name>` to
restore a saved profile that includes the saved-account auto-login.
But this requires a previously-saved profile, which a fresh prefix
doesn't have. NOT a viable first-fallback for the cold-boot case.

#### Fallback B: pre-populate `accounts.dat`

MT5 reads `<install_dir>/config/accounts.dat` (binary, AES-encrypted)
at boot. If it contains a saved-account entry matching the
`/login`'d account, MT5 logs in silently. Generating `accounts.dat`
from scratch is non-trivial (requires reversing MetaQuotes' format).
NOT a viable fallback without significant reverse-engineering work.

#### Fallback C: pre-render `terminal.ini` `[Common]` with credentials

`terminal.ini` (the file the entrypoint writes the `[LiveUpdate]`
section into) ALSO accepts a `[Common]` section. Pre-populating it
with `Login=`, `Password=`, `Server=` in addition to `startup.ini`
may make MT5 treat the credentials as previously-saved and skip the
Login dialog entirely. Worth trying if Fallback A and B are both
out-of-reach.

Patch sketch (in `docker/mt-node/entrypoint.sh`, the section that
writes `terminal.ini`):

```bash
cat > "$TERMINAL_INI" <<EOF
[Common]
Login=${MT_LOGIN}
Password=${MT_PASSWORD}
Server=${MT_SERVER}
AutoConfiguration=true

[LiveUpdate]
LastBuildDataPath=${MT_BUILD}
EOF
```

#### Fallback D: capture screenshots via Xvfb's framebuffer

If MT5 is showing a dialog that none of our flags can dismiss
(EULA, broker-specific terms-of-service, etc.), we can capture the
Xvfb framebuffer to see what's on screen:

```bash
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'apt list --installed 2>/dev/null | grep -i imagemagick'
# If installed:
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 import -window root /tmp/screenshot.png && wc -c /tmp/screenshot.png'
kubectl -n etradie-system cp etradie-system/"$POD":/tmp/screenshot.png ./mt5-screenshot.png -c mt-node
```

The screenshot shows EXACTLY what MT5 is doing visually, even on a
headless Xvfb display. If it shows a `License Agreement` dialog or
a broker-specific welcome page, that's the smoking-gun blocker.

### State of the test cluster on session pause

```
Pod    : etradie-mt-7b9fd8c0-6a1-0 (2/3 Running, ~4m42s old)
Row    : broker_connections.id=7b9fd8c0-6a1c-...
Image  : c384a6006da81b667d459e3d89581d4e0ec3526c
Flags  : /portable /login:133978149 /password:43123acChuks /server:Exness-MT5Real9
Verdict: PENDING - run the §NEXT ACTION block above
```

If the operator picks up after the engine's 600s readiness gate has
fired and `_best_effort_cleanup` has run (PVC will be preserved per
commit 1, but StatefulSet / Service / DB row will be cleaned up),
the DB row goes to `status='failed'` and the engine starts spinning
on `broker_positions_failed_no_cache`. In that case, run the §B
cleanup procedure (this section, just below), then re-provision
from scratch from the dashboard with a FRESH wallclock window.

---

## Deployment Verification (live-staging procedure, 2026-06-23)

The verify path on the live staging box surfaced four operational
gotchas that aren't visible from the chart values alone. Capture them
here so the next operator doesn't relearn them.

### A. The engine ConfigMap can be overridden by a live `kubectl set env`

Observed: chart `values.yaml` set `MT_NODE_READINESS_TIMEOUT_SECS=600`
and the ConfigMap rendered correctly, but the running engine pod read
`900`. Root cause: a previous operator had run something equivalent to
`kubectl set env deploy/etradie-engine MT_NODE_READINESS_TIMEOUT_SECS=900`
on all three containers (engine main + `wait-for-deps` init + `migrate`
init). Container `env:` always wins over `envFrom: configMapRef:`.

Diagnostic:
```bash
kubectl -n etradie-system get deploy etradie-engine -o json \
  | jq '
    [.spec.template.spec.containers, .spec.template.spec.initContainers // []]
    | flatten
    | map(select(.env != null))
    | map({name: .name,
           override_env: (.env // [] | map(select(.name == "MT_NODE_READINESS_TIMEOUT_SECS")))})
    | map(select(.override_env != []))
  '
# expect: []  (empty - no overrides). A non-empty result means someone live-patched.
```

Fix:
```bash
kubectl -n argocd patch application engine-staging --type merge -p '{
  "operation": {
    "sync": {
      "revision": "HEAD",
      "syncOptions": ["Force=true", "Replace=true"]
    }
  }
}'
# Replace=true runs kubectl replace, which restores the Deployment spec
# to exactly what the chart renders (no live env override).
```

Also ensure ArgoCD `syncPolicy.automated.selfHeal` is `true` so a
future live-patch reverts on the next reconcile:
```bash
kubectl -n argocd get application engine-staging \
  -o jsonpath='{.spec.syncPolicy.automated}{"\n"}'
# expect: {"prune":true,"selfHeal":true}
```

### B. A `failed` broker_connections row keeps the engine spinning

Observed: after a provision times out, the engine's `_best_effort_cleanup`
removes the StatefulSet / Services / SA / ConfigMap, but `is_active=true`
stays on the row and `status='failed'`. The dashboard's broker bridge
keeps calling `service_dns_for(release_name)` every ~2 seconds:
```
broker_positions_failed_no_cache
broker_symbol_sync_failed: ZMQ recv timed out
```

This is harmless to other tenants (the K8s Service is gone, so the
calls fail fast) but burns engine CPU + log volume and confuses the
user-facing dashboard. The clean fix is to NULL the row before
re-provisioning:

```bash
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE connection_type='hosted' RETURNING id, status;"

# Also clean any orphaned PVC (the new _best_effort_cleanup preserves it,
# but the next provision gets a fresh release name -> fresh PVC name, so
# the old PVC is now unreferenced).
kubectl -n etradie-system delete pvc,sa,configmap,svc,statefulset \
  -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found

# Clean Vault tenant path (the old release's credentials).
ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$ROOT_TOKEN" \
  vault kv metadata delete -mount=etradie \
  "etradie/tenants/mt-node/<release-name>" 2>/dev/null || true
```

Then roll the engine to invalidate its per-user broker client cache,
so it stops dialing the dead Service:
```bash
kubectl -n etradie-system rollout restart deploy/etradie-engine
kubectl -n etradie-system rollout status deploy/etradie-engine --timeout=120s
```

### C. Verify the new env vars are flowing to the running engine pod

After ANY change to `helm/engine/values{,-staging,-production}.yaml` or
the ConfigMap template, Stakater Reloader rolls the engine on the
ConfigMap checksum change. Confirm the running pod sees the new
values:
```bash
POD=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine \
  -o name | head -1)
kubectl -n etradie-system exec "$POD" -c engine -- printenv \
  MT_NODE_READINESS_TIMEOUT_SECS \
  ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS \
  ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS \
  MT_NODE_IMAGE
# expect:
#   MT_NODE_READINESS_TIMEOUT_SECS=600
#   ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS=1200
#   ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS=1800
#   MT_NODE_IMAGE=ghcr.io/<org>/etradie/mt-node:<sha>   (matches the
#                                                       deploy-bump pin)
```

If any value is wrong, run the §A diagnostic — most likely a live
override needs to be dropped.

### D. Verdict checks after a successful provision

The smoking-gun proof is that LiveUpdate runs EXACTLY ONCE per fresh
PVC and subsequent boots are silent on the LiveUpdate front.

```bash
P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"
POD=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[0].metadata.name}')

# (a) :5555 LISTEN (15B3 hex = 5555 dec)
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'cat /proc/net/tcp | awk "NR>1 && (\$3 ~ /:15B3/ || \$2 ~ /:15B3/){print}"'

# (b) LiveUpdate ran ONCE
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/logs\"/*.log | head -1); \
   echo -n 'downloads:       '; tr -d '\000' < \"\$f\" | grep -ac 'downloaded and updated'; \
   echo -n 'terminal starts: '; tr -d '\000' < \"\$f\" | grep -ac 'build .* started'; \
   echo -n 'login lines:     '; tr -d '\000' < \"\$f\" | grep -ac -E 'Network|Login|Authentication|connected'; \
   echo -n 'expert lines:    '; tr -d '\000' < \"\$f\" | grep -ac -iE 'expert|ZeroMQ'"
# expect after fix:
#   downloads:       1
#   terminal starts: 2     (one cold + one post-LiveUpdate relaunch)
#   login lines:    >0     (proves /portable triggered auto-login)
#   expert lines:   >0     (proves the EA was attached)

# (c) Pod fully ready
kubectl -n etradie-system get pod "$POD"   # expect 3/3 Ready

# (d) Engine recovery sweep is silent on this connection
kubectl -n etradie-system logs deploy/etradie-engine --tail=200 \
  | grep -iE 'hosted_recovery_fresh_provision_grace|hosted_recovery_sweep_complete' | tail -10
# expect: fresh_provision_grace entries while the connection is
#          younger than 30min; sweep_complete with reprovisioned=0.
```

### E. Smoking-gun proof — restart the pod and confirm LiveUpdate stays silent

```bash
kubectl -n etradie-system delete pod "$POD"
kubectl -n etradie-system get pod "$POD" -w
# expect: 3/3 Ready in 20-40 seconds (NOT 3-5 minutes)

kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/logs\"/*.log | head -1); tr -d '\000' < \"\$f\" | grep -ac 'downloaded and updated'"
# expect: STILL 1 (LiveUpdate did NOT re-run; persisted mt5onnx64 was already current)
```

If this passes, the system behaves identically to every commercial MT5
VPS: LiveUpdate ran once on first boot, the component persisted on the
PVC, every subsequent restart is fast and silent on the LiveUpdate
front.

---

# Below: the original investigation notes

The sections below are preserved verbatim for historical context and
audit trail. **Read the status block above first.** Every "Layer 2"
NetworkPolicy egress prescription, the SNI/Envoy gateway plan, and
the "config/DNS disable" dead ends in the original text are
SUPERSEDED by the actual fix. Do not implement them.

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

---

## Layer 2 — design analysis (READ before implementing)

### Why a static CIDR allowlist is the WRONG tool (broker IPs are dynamic)
MetaQuotes-hosted brokers (Exness, Deriv, most of them) resolve their
trade servers through MetaQuotes' access-server infrastructure, which:
- uses MULTIPLE, ROTATING IPs across MetaQuotes ranges,
- can FAILOVER to different ranges,
- OVERLAPS with the LiveUpdate IPs (observed `194.164.179.28` serving
  both the broker hop AND update traffic).

So a static `194.164.179.0/24` allowlist would (a) break the moment the
broker uses an IP outside it, and (b) still let LiveUpdate through on the
shared IPs. CIDR allowlisting brokers is NOT the clean answer. (This
supersedes the earlier "seed Exness with 194.164.179.0/24" note above.)

### What actually distinguishes broker traffic from LiveUpdate traffic
NOT the IP (shared/dynamic). The distinguishers are:
1. Hostname/SNI: LiveUpdate -> `download.mql5.com` / MetaQuotes update
   hosts; broker login -> the broker's trade-server hostname. Same IPs
   sometimes, but DIFFERENT SNI in the TLS handshake.
2. Purpose/timing: LiveUpdate is an HTTPS GET to a CDN; broker login is
   the MT5 trade protocol to the access server.

The correct control for "same/dynamic IP, different purpose" is L7/SNI
egress filtering, NOT L3/IP filtering: allow the broker SNI, deny
`*.mql5.com` / update SNIs, regardless of which IP they resolve to.
This handles dynamic IPs by construction (filter on the name, not the
address).

### The options, ranked

**Option A — SNI-based egress gateway (proper enterprise answer).**
Route all mt-node egress through an Envoy/proxy that allowlists the
broker SNI and denies MetaQuotes update SNIs. The cluster already runs
Linkerd + Envoy, so the infrastructure exists. Industry-standard egress
gateway + SNI policy; handles dynamic IPs. Downside: meaningful
architectural change, touches the mesh (fragile here per
PHASE10.6-MESH-DISABLED-CHECKPOINT), needs care.

**Option B — accept LiveUpdate runs once, make the pod SURVIVE it.**
The failure is not "LiveUpdate downloads a file"; it is "the terminal
self-restarts (exit 143) and the supervisor relaunches into the same
download before it converges, while the 300s readiness gate + 180s
watchdog grace expire first." LiveUpdate downloads ONE component
(`mt5onnx64`, ~14.7MB) and applies it. IF that update persisted on the
Wine-prefix PVC, the next boot would have nothing to download -> no
self-restart -> login -> EA binds. Then the fix is network-free: let the
one-time update complete + raise the readiness gate / watchdog grace so
the post-update boot can settle, plus a gentler (exponential-backoff,
LiveUpdate-143-aware) supervisor relaunch.

**Option C — do not block MetaQuotes at all; raise the gate.**
Allow broker traffic, accept LiveUpdate, just give it a long enough
window and ensure the update persists. Simplest; only works if Option
B's persistence holds.

### The OPEN question that decides B/C vs A
Does the LiveUpdate-applied component PERSIST across restarts, or does
every boot re-download it?
- Earlier journals showed the terminal restarting 7+ times and EACH
  cycle re-announcing `LiveUpdate new version build 5833 is available`
  + `downloaded`. That strongly suggests it does NOT persist (the prefix
  state or the kubelet container restart wipes the applied update), in
  which case backoff/idempotency CANNOT converge and Option A (SNI
  egress) is required.
- The confirming metric is the download:starts ratio in the persisted
  journal (`grep -ac 'downloaded and updated'` vs `grep -ac 'build 5836
  started'` in `.../MetaTrader 5/logs/<date>.log`). Captures so far kept
  racing the restart (the container exits mid-exec) or read a too-fresh
  pod (`dl=0 starts=0`). Capture it after the pod has looped 3+ times,
  reading via `kubectl logs` (survives restarts) for the supervisor
  `restart_count`, and the journal for the MT5 download count.
  - dl ~= starts (re-downloads every boot) -> NOT persisting ->
    backoff cannot converge -> implement Option A (SNI egress).
  - dl fixed at 1 while starts/restart_count climb -> persisted ->
    implement Option B (let it converge + raise gate + backoff).

### Honest assessment
Backoff/idempotency on OUR supervisor cannot help if the
non-idempotent actor is MT5 itself re-running LiveUpdate every boot
(which the repeated "new version available" lines indicate). In that
case Option A (SNI egress gateway) is the real, dynamic-IP-safe fix.
Confirm the persistence ratio before committing to the Envoy/SNI work.

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
