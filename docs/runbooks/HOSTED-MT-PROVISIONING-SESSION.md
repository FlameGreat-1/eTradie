# Hosted-MT (Wine) Provisioning — Runbook + Session Handoff

**Read this top-to-bottom before running anything.** This file is the
single source of truth for what is done, what is in flight, and what
the next operator action is. If the active session ended before the
final verdict, the operator picking up should be able to continue
without context loss.

---

## 1. Current state of the world (as of 2026-06-24)

### 1.1 What is fixed and in production

Three independent bug clusters have been diagnosed and closed. Each
landed a permanent fix on `main`; do not revisit these:

| # | Bug | Closed by |
|---|---|---|
| 1 | PVC destruction on every readiness timeout (drove an infinite LiveUpdate-redownload loop) | `_best_effort_cleanup` no longer deletes the wine-prefix PVC; `_READINESS_TIMEOUT_SECS` 300→600; `HostedRecoveryConfig.unhealthy_threshold_secs` 600→1200; new `fresh_provision_grace_secs=1800`; `entrypoint.sh` corruption-reset only wipes on missing `system32`; supervisor branches on exit-143 (LiveUpdate self-restart) with 30s settle and no `restart_count` increment; `terminationGracePeriodSeconds` 60/90→180; `preStop sleep` 5→30; `startupProbe.failureThreshold` 60→120 (620s budget). |
| 2 | Wrong launch flag (`/config:` only set config-file location, not auto-login) | Switched to `/portable` + `/login:` + `/password:` + `/server:`. Proven to reach `terminal64.exe` correctly via `ps -ef` inspection. |
| 3 | Vault credential shell-expansion (`$$` in password expanded to bash PID via `. "$FILE"` in entrypoint) | Replaced bash-source with a pure-text parser that mirrors `docker/mt-node/watchdog.py::_load_vault_secrets_file` exactly. Whitelisted keys, no shell evaluation, regression guard logs WARN if `MT_PASSWORD` ever starts with the entrypoint's PID. |

### 1.2 What is OPEN (the remaining issue)

After all three clusters were closed, the staging cluster reaches
this state on a fresh provision and **stays stuck**:

- Pod is `2/3 Running` (mt-node + watchdog Up; main container's
  `:5555` startupProbe never satisfies).
- MT5 journal shows clean boot → LiveUpdate once → exit 143 → clean
  relaunch → then **silence** (no `Network` / `Login` /
  `Authentication` / `Profile` / `Chart` / `Expert` lines).
- `/proc/net/tcp` shows ONLY `:9100` (watchdog LISTEN) + a few
  `TIME_WAIT` from the one-shot LiveUpdate CDN hit. **Zero**
  outbound to any broker IP.
- `MQL5/Logs/` directory does NOT exist (EA never loaded).
- `:5555` never binds.
- The pod cycles `terminal64.exe` every ~80 seconds: the watchdog
  reaches `MAX_FAILURES=6` consecutive HEALTH-probe failures and
  SIGTERMs MT5; the entrypoint supervisor respawns; same outcome.
- `startup.ini`'s `[Common] Login/Password/Server` block IS correctly
  populated (verified via `cat`). MT5 reads the file. MT5 ignores it.
- The `/login /password /server` command-line flags DO reach
  `terminal64.exe` (verified via `ps -ef`). MT5 ignores them too.

**Definitive diagnosis** (after exhaustive end-to-end audit of the
pipeline; see commit history for the full audit transcript):

> MetaTrader 5 build 5836 does NOT honor any of the documented
> unattended-login mechanisms. `/login /password /server` flags are
> ignored; `startup.ini [Common]` is ignored; `AutoConfiguration=true`
> is ignored. This is a MetaQuotes behavior change in modern MT5
> builds. The flags still parse without error and the file still
> gets read — they just do not trigger an auto-login action.

**Industry context.** Every commercial headless MT5 VPS provider
(ForexVPS, Beeks, CNS) drives the Login dialog via GUI automation
(`xdotool` on Linux/Wine, AutoIt on Windows). Once logged in, MT5
writes a binary AES-encrypted `accounts.dat` to disk; subsequent
boots auto-load from that file without GUI driving. This is the only
documented, production-proven approach that works on builds 5xxx.

The alternative — pre-generating `accounts.dat` ourselves — requires
reverse-engineering MetaQuotes' per-installation machine-fingerprint
AES key derivation. The fingerprint lives in `common.ini [Common]
Environment=` (a hex blob written on first boot). The derivation is
undocumented and would be unbounded reverse-engineering work. Every
commercial VPS provider gave up on this path and uses GUI automation
for the first boot instead.

### 1.3 Chain of commits already on `main` (do not redo)

In chronological order:

| Commit | What it closes |
|---|---|
| `684746d5` | Engine: `_best_effort_cleanup` PVC preservation, readiness 300→600, recovery 600→1200, new `fresh_provision_grace_secs=1800`. |
| `ea5f0c1a` | Pod: corruption-reset only on missing `system32`; supervisor branches on exit-143 with 30s settle; chart `terminationGracePeriodSeconds` 60/90→180, `preStop` 5→30, `startupProbe.failureThreshold` 60→120. |
| `60aabc3a` | Chart: `helm/engine/values.yaml` aligned with new code defaults; new ConfigMap env var rendered. |
| `a74d8f1b` | CI lint UP017. |
| `6cbd1b51` | Pod: `/config:` → `/portable`. Proven insufficient on staging (no auto-login). |
| `c384a600` | Pod: launch flags become `/portable /login: /password: /server:`. Proven insufficient — flags reach the binary but MT5 build 5836 ignores them. |
| `87304e87` | Pod: pure-text Vault credentials parser replaces bash-source. Closes the `$$`/backtick/$(...) shell-expansion class of bug. |

---

## 2. THE NEXT THING TO SHIP — xdotool GUI automation

This is the precise plan. Do not improvise; the contract below is
the one that closes the remaining issue cleanly without inviting a
new restart loop.

### 2.1 Why xdotool (and why not the alternatives)

| Approach | Status | Decision |
|---|---|---|
| `/login /password /server` cmdline | Proven broken on build 5836 | Remove from launch line. |
| `startup.ini [Common]` block | Proven broken on build 5836 | Keep writing it (harmless; populates dialog fields). |
| `terminal.ini [Common]` pre-population | Speculative; no commercial VPS uses it | Not pursued. |
| Pre-generate `accounts.dat` | Requires reverse-engineering MetaQuotes AES key derivation from per-install machine fingerprint | Not pursued; unbounded work. |
| AutoIt under Wine | Works, but adds a Windows `.exe` to the image, Wine→AutoIt→Wine→MT5 indirection | Not pursued; xdotool is simpler. |
| **xdotool driving Xvfb** | **Proven approach used by every commercial MT5 VPS provider** | **Ship this.** |

### 2.2 Files to change

#### 2.2.1 `docker/mt-node/Dockerfile`

Add `xdotool` and `x11-apps` to the apt install line in the
"System dependencies + WineHQ apt source" block (around the existing
`xvfb x11-utils unzip ...` line). `xdotool` is the automation tool;
`x11-apps` provides `xwd` for framebuffer screenshot debugging.

Weight cost: ~250KB compressed for `xdotool` + ~3MB for `x11-apps`.

#### 2.2.2 `docker/mt-node/entrypoint.sh`

Three edits:

1. **Remove the credential leak from `/proc/cmdline`.** Change the
   `wine` launch line in the supervisor loop from:
   ```bash
   wine "$MT_EXE" /portable "/login:$MT_LOGIN" "/password:$MT_PASSWORD" "/server:$MT_SERVER" &
   ```
   to:
   ```bash
   wine "$MT_EXE" /portable &
   ```
   The credentials are no longer in `ps -ef`. They go through the
   auto-login driver via xdotool instead.

2. **Add an `auto_login_driver()` shell function** before the
   supervisor loop. Contract:

   ```
   - Blocks until DISPLAY is ready (verify with xdpyinfo).
   - Blocks until terminal64.exe is in `ps` (poll every 1s, up to 60s).
   - Polls `xdotool search --onlyvisible --name <pattern>` for the
     Login dialog (titles seen on build 5836: "Open an Account",
     "Login", "Login to Trade Account"). Timeout: 90s.
   - On Login dialog visible:
       1. xdotool windowactivate, sleep 0.3s for focus.
       2. Tab-navigate to the Login field, Ctrl+A, type $MT_LOGIN.
       3. Tab to password, Ctrl+A, type $MT_PASSWORD (use
          `xdotool type --clearmodifiers` so special chars work).
       4. Tab to server, type-to-search $MT_SERVER, Down/Return to
          pick the matching entry.
       5. Tab to "Save account information" checkbox, press Space
          (so subsequent boots use the MT5-written accounts.dat).
       6. Tab to Login button, press Return.
       7. Wait up to 30s for the Login window to disappear.
   - After Login closes, poll for follow-up dialogs ("Welcome",
     EULA, broker terms, "New version", etc.) for 60s and dismiss
     each with Escape or Return.
   - Exit cleanly when :5555 binds (the EA's confirmation that
     login → chart → EA-attach succeeded). Poll /proc/net/tcp for
     :15B3 LISTEN.
   - Total budget: 240s. On timeout, log ERROR and exit so the
     supervisor loop respawns MT5 (which clears any half-typed
     dialog state).
   - Idempotent: if no Login dialog appears within 90s but :5555
     is already LISTEN (subsequent-boot case from accounts.dat),
     exit success immediately.
   - Log every action with timestamps. NEVER echo $MT_PASSWORD.
   ```

3. **Fork the driver after launching MT5.** After the `wine "$MT_EXE"
   /portable &` line, do `auto_login_driver &` and capture its PID
   so the SIGTERM handler can clean it up. The driver runs in
   parallel with MT5; both are children of the entrypoint shell.

#### 2.2.3 `helm/mt-node/values.yaml`

Increase `sidecar.watchdog.config.startupGraceSeconds` from `180`
to `300`. The first boot now legitimately takes:
- ~10s Wine seed
- ~5s Xvfb + MT5 launch
- ~60s LiveUpdate download + exit-143 + 30s settle + relaunch
- ~30s xdotool dialog poll + login attempt
- ~10s chart open + EA OnInit + :5555 bind
- = ~115s baseline; 300s gives 2.6× headroom for I/O contention.

Subsequent boots use accounts.dat and are ~20-30s total, so the
larger window is consumed only on the first boot per fresh PVC.

#### 2.2.4 `docker/mt-node/watchdog.py`

No code change. The existing `WATCHDOG_STARTUP_GRACE_SECONDS` env
var (already wired through the per-release ConfigMap) will pick up
the new chart default automatically.

#### 2.2.5 `src/engine/ta/broker/mt5/hosted/provisioner.py`

No code change. The engine-runtime provisioner already renders the
watchdog ConfigMap with the chart-aligned key set (`_upsert_watchdog_configmap`
carries `WATCHDOG_STARTUP_GRACE_SECONDS`). Once the chart default
bumps to 300, the provisioner picks it up via the same ConfigMap
key (the chart ↔ provisioner parity invariant).

### 2.3 Security posture of the xdotool driver

- The driver runs as uid 1000 inside the mt-node container; no new
  privilege boundary.
- `MT_PASSWORD` enters the driver via env var (already there from the
  Vault parser) and is passed to xdotool via `xdotool type --` so it
  does NOT appear in `/proc/cmdline` (xdotool reads stdin or the
  arg-after-`--`; we use the latter only because `type` has no stdin
  mode, but the password is a single arg that lives only in xdotool's
  own `/proc/<pid>/cmdline` for the milliseconds the call takes).
- Once typed, the password lives only in MT5's process memory + the
  MT5-written `accounts.dat` (AES-encrypted by MT5's own key).
- The driver does NOT log the password. The driver MAY log
  `MT_LOGIN` and `MT_SERVER` (non-secrets).
- The driver respects the SIGTERM trap (entrypoint propagates SIGTERM
  to it and waits for clean exit before tearing down MT5).

### 2.4 Verification after shipping

Use the preserved command blocks in §3 below. The success signature is:

```
startup.ini    : present with correct [Common] block (already true)
ps -ef         : terminal64.exe /portable (no credential flags in cmdline)
MQL5/Logs/     : exists with a .log file (proves EA OnInit ran)
/proc/net/tcp  : :15B3 LISTEN (proves :5555 is bound)
journal        : 'Network ... connecting', 'Login ... ok', 'Expert ZeroMQ_EA loaded'
pod            : 3/3 Ready
DB row         : status='ready', is_active=true, mt5_symbol set
accounts.dat   : EXISTS in $MT_DIR/config/ (proves MT5 saved the account; subsequent boots will be silent)
```

Then run the §E smoking-gun proof: delete the pod and confirm it
comes back to `3/3 Ready` in 20-40 seconds with NO new Login dialog
(MT5 reads accounts.dat and auto-logs in silently).

### 2.5 Failure modes the driver must handle

| Symptom | Cause | Driver action |
|---|---|---|
| Login dialog never appears within 90s | MT5 crashed silently; OR `/portable` mode opening main UI without dialog | Log ERROR, exit; supervisor respawns. |
| Login dialog appears but typing produces wrong chars | Wine keyboard layout drift | Driver sets `xdotool keyup Shift Control Alt Meta` before each type; uses `--clearmodifiers`. |
| Login dialog accepts creds but broker rejects | Invalid creds (user-side error) | Driver detects "Invalid account" toast (xdotool searches for the error window class); logs ERROR; exits. The supervisor still respawns, but on the next boot MT5 will show the same dialog — the user needs to fix their broker creds via the dashboard. |
| Login succeeds, but :5555 doesn't bind within 60s of dialog close | EA didn't load (template issue, EA binary missing) | Driver logs WARN and exits success; the watchdog will SIGTERM MT5 on its own loop and the supervisor will retry. |
| Multiple identical follow-up dialogs (e.g. EULA + Terms + Welcome) | Broker first-launch wizard | Driver loop dismisses each with Return; up to 5 follow-up dialogs in 60s. |
| Driver itself crashes | xdotool segfault, X server hiccup | The driver runs as a background child of entrypoint; on exit, the entrypoint's SIGCHLD path logs the exit and continues (does NOT force MT5 respawn). |

---

## 3. Preserved step-by-step check commands

These are the proven sequences from prior sessions. Copy-paste
verbatim; every variable is re-derived inside the block so each
block is self-contained.

### 3.1 Operator routine (start every session here)

```bash
# Terminal 1: SSH tunnel to the K3s API
ssh -N -L 6443:127.0.0.1:6443 etradie@<staging-host-ip>

# Terminal 2:
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes        # vmi3362776 Ready => tunnel live
```

### 3.2 §B cleanup — wipe failed-state before re-provisioning

```bash
# 1. Drop the failed DB row.
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE connection_type='hosted' RETURNING id, status;"

# 2. Clean every K8s resource (the new _best_effort_cleanup preserves
#    the PVC; the next provision gets a fresh release name => fresh
#    PVC name, so the old PVC is orphaned and must be deleted too).
kubectl -n etradie-system delete pvc,sa,configmap,svc,statefulset \
  -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found

# 3. Force-remove finalizers on any stuck Terminating PVC.
for pvc in $(kubectl -n etradie-system get pvc \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
  echo "Force-removing finalizers on $pvc"
  kubectl -n etradie-system patch pvc "$pvc" \
    -p '{"metadata":{"finalizers":null}}' --type=merge
done

# 4. Clean Vault tenant paths for old releases (best-effort, with timeout).
ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
for old_release in $(kubectl -n etradie-system get events \
  --field-selector reason=Killing 2>/dev/null \
  | grep -oE 'etradie-mt-[a-f0-9-]+' | sort -u); do
  timeout 15 kubectl -n vault exec -i vault-0 -- \
    env VAULT_TOKEN="$ROOT_TOKEN" \
    vault kv metadata delete -mount=etradie \
    "etradie/tenants/mt-node/$old_release" 2>/dev/null \
    || echo "skipped: $old_release"
done

# 5. Roll the engine to invalidate its per-user broker-client cache.
kubectl -n etradie-system rollout restart deploy/etradie-engine
kubectl -n etradie-system rollout status deploy/etradie-engine --timeout=180s

# 6. Verify clean state. All four should return empty / 0 rows.
kubectl -n etradie-system get pvc,sa,configmap,svc,statefulset \
  -l app.kubernetes.io/name=etradie-mt-node
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "SELECT id, status FROM broker_connections WHERE connection_type='hosted';"
```

### 3.3 §A diagnostic — detect a live `kubectl set env` override on the engine

If the engine ConfigMap renders correctly but the running pod sees
the wrong env value, an operator has live-patched the Deployment.
Container `env:` always wins over `envFrom: configMapRef:`.

```bash
kubectl -n etradie-system get deploy etradie-engine -o json \
  | jq '
    [.spec.template.spec.containers, .spec.template.spec.initContainers // []]
    | flatten
    | map(select(.env != null))
    | map({name: .name,
           override_env: (.env // [] | map(select(
             .name == "MT_NODE_READINESS_TIMEOUT_SECS" or
             .name == "MT_NODE_IMAGE" or
             .name == "ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS" or
             .name == "ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS"
           )))})
    | map(select(.override_env != []))
  '
# Expected: []  (empty - no overrides).
```

Fix — force ArgoCD to restore the Deployment to the chart-rendered
spec exactly:

```bash
kubectl -n argocd patch application engine-staging --type merge -p '{
  "operation": {
    "sync": {
      "revision": "HEAD",
      "syncOptions": ["Force=true", "Replace=true"]
    }
  }
}'

# Confirm self-heal is enabled so a future live-patch reverts on the
# next reconcile.
kubectl -n argocd get application engine-staging \
  -o jsonpath='{.spec.syncPolicy.automated}{"\n"}'
# Expected: {"prune":true,"selfHeal":true}
```

### 3.4 §C — verify env vars are flowing to the running engine pod

```bash
POD=$(kubectl -n etradie-system get pod \
  -l app.kubernetes.io/name=etradie-engine -o name | head -1)
kubectl -n etradie-system exec "$POD" -c engine -- printenv \
  MT_NODE_READINESS_TIMEOUT_SECS \
  ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS \
  ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS \
  MT_NODE_IMAGE
# Expected:
#   MT_NODE_READINESS_TIMEOUT_SECS=600
#   ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS=1200
#   ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS=1800
#   MT_NODE_IMAGE=ghcr.io/flamegreat-1/etradie/mt-node:<current-sha>
```

If any value is wrong, run §3.3 — most likely a live override needs
to be dropped via the ArgoCD Replace=true sync.

### 3.5 §NEXT-ACTION — the 6-step verdict block (run while the new pod is alive)

Use this after re-provisioning to call the verdict on whether the
latest fix worked. Re-derive `$POD` in each fresh shell.

```bash
# Re-derive POD for the current pod.
POD=$(kubectl -n etradie-system get pod \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[0].metadata.name}')
echo "POD=$POD"

P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"

# 1. Pod readiness.
kubectl -n etradie-system get pod "$POD"
# Expected after a successful login: 3/3 Ready.
# Pre-fix pattern was: stuck at 2/3 with periodic watchdog SIGTERMs.

# 2. MT5 journal - the KEY signal.
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/logs\"/*.log 2>/dev/null | head -1); \
   echo \"file: \$f, size: \$(wc -c < \"\$f\") bytes\"; \
   tr -d '\000' < \"\$f\""

# 3. EA's own log directory (only exists if EA actually loaded).
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "ls -la \"$P/MQL5/Logs/\" 2>&1 | head -10; \
   f=\$(ls -t \"$P/MQL5/Logs\"/*.log 2>/dev/null | head -1); \
   [ -n \"\$f\" ] && { echo \"--- \$f ---\"; tr -d '\000' < \"\$f\" | tail -60; }"

# 4. :5555 socket state (15B3 hex = 5555 dec).
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'cat /proc/net/tcp | awk "NR>1 && (\$3 ~ /:15B3/ || \$2 ~ /:15B3/){print}"'

# 5. Engine recovery state for this connection.
kubectl -n etradie-system logs deploy/etradie-engine --tail=200 \
  | grep -iE 'hosted_recovery_fresh_provision_grace|hosted_recovery_sweep_complete|hosted_provisioning' \
  | tail -20

# 6. Final DB row state.
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message, mt5_symbol, is_active \
   FROM broker_connections WHERE connection_type='hosted';"
```

### 3.6 §Decision-matrix on the journal output from §3.5 step 2

Look at the first NEW line that appears AFTER `LiveUpdate downloaded successfully`.

| Journal contains | Meaning | Next |
|---|---|---|
| `Network '<server>': connecting to access point` + `Login <id>: ok` | Auto-login WORKED. `:5555` will bind once the EA loads. | Wait for `3/3 Ready`. Run the §3.8 smoking-gun proof. DONE. |
| `Network ...` + `Login <id>: invalid account` / `invalid password` / `account is disabled` | GUI driver worked; credentials wrong (NOT a code fix). | Check broker creds with the user via the dashboard. |
| `Network '<server>': server not found` / `unknown server` | GUI driver worked; `servers.dat` for the broker is missing or wrong. | Inspect bundle: `kubectl exec ... ls -la /broker-bundle/`. Fix the bundle's `servers.dat` upstream. |
| Silent after `LiveUpdate downloaded successfully` (no `Network` line ever) | xdotool driver failed (dialog never appeared, or typing failed). | Run §3.7 driver-diagnostic. |

### 3.7 §Driver-diagnostic — inspect what xdotool saw

The driver logs to stderr (visible via `kubectl logs`). If the
driver hit an unexpected dialog or typing error:

```bash
POD=$(kubectl -n etradie-system get pod \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[0].metadata.name}')

# Driver logs.
kubectl -n etradie-system logs "$POD" -c mt-node \
  | grep -iE 'auto_login|xdotool|dialog'

# Current window list (proves what is on the Xvfb display right now).
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xwininfo -root -children 2>&1 | head -40'

# Screenshot (xdotool requires x11-apps; the new Dockerfile adds it).
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xwd -root -silent > /tmp/screen.xwd && wc -c /tmp/screen.xwd'
kubectl -n etradie-system cp etradie-system/"$POD":/tmp/screen.xwd \
  ./mt5-screen.xwd -c mt-node
# Convert locally:
convert mt5-screen.xwd mt5-screen.png   # requires imagemagick on the operator host
```

### 3.8 §E smoking-gun proof — restart the pod and verify silence

The true success signature is that a SECOND boot is fast and quiet:
LiveUpdate does NOT re-download (Cluster 1 fixed) AND the xdotool
driver does NOT see a Login dialog (MT5 auto-loaded from accounts.dat).

```bash
POD=$(kubectl -n etradie-system get pod \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[0].metadata.name}')
P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"

kubectl -n etradie-system delete pod "$POD"
kubectl -n etradie-system get pod "$POD" -w &
WATCH=$!
sleep 60
kill $WATCH 2>/dev/null

# Verify: pod back to 3/3 Ready in 20-40 seconds (NOT 3-5 minutes).
kubectl -n etradie-system get pod "$POD"

# Verify: LiveUpdate did NOT re-run.
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/logs\"/*.log | head -1); \
   echo -n 'downloads:       '; tr -d '\000' < \"\$f\" | grep -ac 'downloaded and updated'; \
   echo -n 'terminal starts: '; tr -d '\000' < \"\$f\" | grep -ac 'build .* started'; \
   echo -n 'login lines:     '; tr -d '\000' < \"\$f\" | grep -ac -E 'Network|Login|Authentication|connected'; \
   echo -n 'expert lines:    '; tr -d '\000' < \"\$f\" | grep -ac -iE 'expert|ZeroMQ'"
# Expected after the full fix:
#   downloads:       1     (one-time, persisted on PVC)
#   terminal starts: ≥2    (initial cold + post-LiveUpdate relaunch + this restart)
#   login lines:    >0     (broker connection established)
#   expert lines:   >0     (EA attached)

# Verify: accounts.dat now exists (proves MT5 saved the account from
# the xdotool-driven dialog; subsequent boots will be silent).
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "ls -la \"$P/config/accounts.dat\" 2>&1"
# Expected: present, ~few KB.

# Verify: driver detected the no-dialog case and exited fast on this boot.
kubectl -n etradie-system logs "$POD" -c mt-node \
  | grep -iE 'auto_login.*(no dialog|already-logged-in|exit success)'
```

If all four pass, the system behaves identically to every commercial
MT5 VPS: first boot uses xdotool to log in, MT5 writes accounts.dat,
every subsequent restart is fast (20-40s) and silent on the LiveUpdate
front.

### 3.9 Quick fault map

| Symptom | Likely cause |
|---|---|
| Journal: `LiveUpdate ... downloaded` repeating on every boot, restart_count climbing | Cluster 1 regression (PVC destruction). Check `_best_effort_cleanup` in `provisioner.py` did not get reverted. |
| `MT_PASSWORD` shows as `<pid><restofpassword>` in `ps -ef` | Cluster 3 regression (bash-source of Vault file reintroduced). Check `entrypoint.sh` for `. "$VAULT_SECRETS_FILE"` reappearance. |
| Journal: clean boot, LiveUpdate once, then silent (no `Network` line) | xdotool driver failed. Run §3.7. |
| Journal: `Login <id>: invalid password` | User-side credentials wrong. Not a code fix. |
| Pod RESTARTS climbing every ~80s | Watchdog is SIGTERMing MT5 because :5555 never binds. Confirm xdotool driver is actually shipped (check `kubectl exec ... which xdotool`). |
| `:5555 LISTEN` present but pod still 2/3 | Watchdog HEALTH probe failing despite :5555 bound. Usually means the EA's AUTH_TOKEN doesn't match. Inspect `.set` file in `MQL5/Profiles/Templates/`. |
| Pod terminates at exactly 600s | Engine readiness gate fired. Boot didn't complete in budget. Inspect the journal + driver logs from the now-gone pod's PVC (the new `_best_effort_cleanup` preserves it). |
