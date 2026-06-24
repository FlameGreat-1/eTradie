# Hosted-MT (Wine) Provisioning — Operator Runbook

**Single source of truth for operating the hosted-MT provisioning
system. Read top-to-bottom. Every command is copy-paste verbatim.**

Historical context (Cluster 1-4 diagnoses, Issue #1-5 fixes, the
xdotool/fluxbox/paste evolution) lives in `git log`. This runbook
is strictly for operating the system as it stands today.

---

## 1. Current state

The hosted-MT pipeline runs MetaTrader 5 (build 5836) under Wine +
Xvfb + fluxbox inside a per-tenant Kubernetes StatefulSet. A
background `auto_login_driver` shell function in
`docker/mt-node/entrypoint.sh` drives MT5's Login dialog using
xdotool window control + xclip clipboard paste to deliver broker
credentials. On first successful login MT5 writes `accounts.dat`;
every subsequent pod boot auto-loads from that file silently.

The driver state machine:

  - **Phase 1**: wait for `terminal64.exe` (max 60s).
  - **Phase 2a**: poll for a Login-shaped dialog (max 30s; happy path).
    Precedence guard: if `:5555` is already LISTEN when a Login
    dialog is observed, exit success without driving Phase 3. This
    closes the subsequent-boot double-paste race where MT5 raises a
    residual Login dialog after a LiveUpdate-induced restart even
    though the EA from boot 1 has already bound the socket.
  - **Phase 2b**: `:5555` LISTEN fast-path (subsequent boots via
    `accounts.dat`; exit success immediately).
  - **Phase 2c**: main UI window detected without a dialog (MT5 build
    5836 + pre-staged config). Three-attempt cascade to surface the
    Login dialog via `File -> Login to Trade Account`:
      1. Alt+F then L (Win32 mnemonic).
      2. Alt+F then 9× Down then Return.
      3. Alt+F then 10× Down then Return.
    Pre-step: dismiss `Welcome to LiveUpdate` modal via Escape →
    Return → windowunmap cascade.
  - **Phase 3**: paste credentials into Login / Password / Server
    fields via X CLIPBOARD + Ctrl+V (atomic, no per-character drops).
    On paste failure, fall back to xdotool type with 150ms/char delay.
    Tick `Save account information` checkbox. Submit via Return.
    Final clipboard scrub.
  - **Phase 5**: chart-attach via Ctrl+M Market Watch (with Alt+F
    File menu as last-resort fallback). On build 5836 + `/portable`
    + a fresh Wine prefix MT5 does NOT open a chart on its own
    after login; without a chart the `startup.ini [Charts]
    Template=expert` directive has nowhere to apply, so the EA
    never loads and `:5555` never binds. Phase 5 uses Ctrl+M to
    open Market Watch (empirically verified working on build 5836)
    then keyboard-navigates to open a chart on the broker-default
    first-row symbol. MT5 has NO documented hotkey for New Chart
    (Ctrl+N toggles the Navigator panel, NOT a chart dialog).
    Three-attempt cascade, ordered by empirical certainty, each
    preceded by a modal-clear sweep:
      1. `Ctrl+M` `Tab` `Home` `Return` (highest certainty:
         Ctrl+M opens Market Watch, Tab focuses the list, Home
         selects the first symbol row, Return triggers MT5's
         default action which ships as 'Chart Window' on every
         fresh install per MetaQuotes documentation).
      2. `Ctrl+M` `Tab` `Home` `Menu` `Down` `Return` (high
         certainty: same Ctrl+M + Tab + Home focus path, then the
         XKB Menu key opens the right-click context menu in place,
         Down moves from 'New Order' to 'Chart Window' at
         position 2 per MetaQuotes default order, Return
         activates).
      3. `Alt+F` `Right` `Right` `Return` (last resort: File menu
         + nested symbol-group submenu navigation, defence-in-depth
         for cases where both Ctrl+M paths fail).
    Each attempt waits up to `AUTO_LOGIN_PHASE5_CHART_WINDOW_WAIT_SECS`
    (20s default) for a chart window WID matching the WM_NAME
    pattern `<SYMBOL>,<TIMEFRAME>` (e.g. `EURUSD,H1` or `XAUUSD.m,H1`)
    to appear, then polls `:5555` for up to
    `AUTO_LOGIN_PHASE5_BIND_WAIT_SECS` (30s default). MT5 auto-applies
    `expert.tpl` to the new chart per the `[Charts] Template=expert`
    directive (which applies to charts opened both at startup AND
    interactively post-launch), the EA OnInit runs, and the EA binds
    `tcp://*:5555`. Phase 5 is best-effort: any failure logs WARN
    and falls through to Phase 4 so the remaining budget is still
    spent polling `:5555`. Skipped when `:5555` is already LISTEN
    (idempotent on the `accounts.dat` fast path). Settles
    `AUTO_LOGIN_PHASE5_POST_LOGIN_SETTLE_SECS` (25s default) before
    keystroking to let MT5's post-login broker handshake +
    Market Watch population + Welcome-to-LiveUpdate modal
    materialisation all complete -- the modal is dismissed by the
    pre-keystroke sweep on each attempt.
  - **Phase 4**: dismiss follow-up dialogs (EULA, Welcome, news) for
    60s while polling `:5555` LISTEN.
  - **Total budget**: 240s (`AUTO_LOGIN_TOTAL_BUDGET_SECS`).
  - **Hard-kill watchdog**: forked at driver entry; SIGTERMs the
    driver at +270s if anything wedges past the budget.

Lockstep invariants (DO NOT TOUCH without updating all three):

| Setting | Value | Locations |
|---|---|---|
| `WATCHDOG_STARTUP_GRACE_SECONDS` | 300 | `helm/mt-node/values.yaml`, `helm/mt-node/templates/configmap-watchdog.yaml`, `provisioner.py::_upsert_watchdog_configmap` |
| `startupProbe.failure_threshold` | 120 | `helm/mt-node/values.yaml`, `provisioner.py::_upsert_statefulset` |
| `terminationGracePeriodSeconds` | 180 | `helm/mt-node/values.yaml`, `provisioner.py::_upsert_statefulset` |
| `lifecycle.preStop` | `sleep 30` | same |

---

## 2. Next action (incoming operator starts here)

If you are picking this up cold:

1. Confirm CI is green on the latest `main` commit.
2. Read step 3 below and run the **§3.1 operator routine**.
3. Run **§3.2 cleanup**.
4. Re-provision a hosted connection from the dashboard.
5. Run **§3.5 verdict block** and match against the **§3.6 decision
   matrix**.
6. On success, run **§3.8 smoking-gun proof**.
7. On failure, consult **§3.7 driver diagnostic** + **§3.9 fault map**.

---

## 3. Proven command sequences

### 3.1 Operator routine (start every session here)

```bash
# Terminal 1: SSH tunnel to the K3s API
ssh -N -L 6443:127.0.0.1:6443 etradie@<staging-host-ip>

# Terminal 2:
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes      # vmi3362776 Ready => tunnel live

cd ~/eTradie
git fetch origin main
git pull --rebase origin main
git log --oneline -6

# Read pinned mt-node SHA from staging values.
PIN=$(git show origin/main:helm/engine/values-staging.yaml \
  | grep -E '^[[:space:]]*tag:' | head -1 | tr -d ' "' | cut -d: -f2)
echo "Pinned mt-node SHA: $PIN"

# Force ArgoCD sync so the new SHA reaches the cluster.
kubectl -n argocd patch application engine-staging --type merge -p '{
  "operation": {"sync": {"revision": "HEAD", "syncOptions": ["Force=true", "Replace=true"]}}
}'
kubectl -n argocd patch application mt-node-staging --type merge -p '{
  "operation": {"sync": {"revision": "HEAD", "syncOptions": ["Force=true", "Replace=true"]}}
}' 2>/dev/null || true

kubectl -n etradie-system rollout status deploy/etradie-engine --timeout=180s
kubectl -n etradie-system exec deploy/etradie-engine -c engine -- printenv MT_NODE_IMAGE
# Expect: ghcr.io/flamegreat-1/etradie/mt-node:<PIN>
```

### 3.2 Cleanup — wipe failed state before re-provisioning

```bash
# 1. Drop the failed DB row.
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE connection_type='hosted' RETURNING id, status;"

# 2. Clean every K8s resource (PVC preserved by design; old PVC orphan).
kubectl -n etradie-system delete pvc,sa,configmap,svc,statefulset \
  -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found

# 3. Force-remove finalizers on any stuck Terminating PVC.
for pvc in $(kubectl -n etradie-system get pvc \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
  kubectl -n etradie-system patch pvc "$pvc" \
    -p '{"metadata":{"finalizers":null}}' --type=merge
done

# 4. Clean Vault tenant paths for old releases (best-effort).
ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
for old in $(kubectl -n etradie-system get events --field-selector reason=Killing 2>/dev/null \
  | grep -oE 'etradie-mt-[a-f0-9-]+' | sort -u); do
  timeout 15 kubectl -n vault exec -i vault-0 -- \
    env VAULT_TOKEN="$ROOT_TOKEN" \
    vault kv metadata delete -mount=etradie \
    "etradie/tenants/mt-node/$old" 2>/dev/null || true
done

# 5. Roll the engine to invalidate per-user broker-client cache.
kubectl -n etradie-system rollout restart deploy/etradie-engine
kubectl -n etradie-system rollout status deploy/etradie-engine --timeout=180s

# 6. Verify clean state.
kubectl -n etradie-system get pvc,sa,configmap,svc,statefulset \
  -l app.kubernetes.io/name=etradie-mt-node
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "SELECT id, status FROM broker_connections WHERE connection_type='hosted';"
```

Now re-provision a hosted connection from the dashboard.

### 3.3 Race to the pod after provision

```bash
REL=""
for i in $(seq 1 30); do
  REL=$(kubectl -n etradie-system get statefulset -o name 2>/dev/null \
    | grep 'etradie-mt-' | head -1 | cut -d/ -f2)
  [ -n "$REL" ] && { echo "Release: $REL"; break; }
  echo "waiting for StatefulSet... ($i)"
  sleep 2
done
POD="${REL}-0"
echo "POD=$POD"

# Wait until mt-node container is Running.
for i in $(seq 1 60); do
  state=$(kubectl -n etradie-system get pod "$POD" \
    -o jsonpath='{.status.containerStatuses[?(@.name=="mt-node")].state}' 2>/dev/null)
  echo "[$i] mt-node state: $state"
  echo "$state" | grep -q running && break
  sleep 2
done

# Confirm new image is live.
kubectl -n etradie-system get pod "$POD" \
  -o jsonpath='{.spec.containers[?(@.name=="mt-node")].image}{"\n"}'
```

### 3.4 Verify env on the running engine pod

```bash
EPOD=$(kubectl -n etradie-system get pod \
  -l app.kubernetes.io/name=etradie-engine -o name | head -1)
kubectl -n etradie-system exec "$EPOD" -c engine -- printenv \
  MT_NODE_READINESS_TIMEOUT_SECS \
  ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS \
  ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS \
  MT_NODE_IMAGE
# Expect:
#   MT_NODE_READINESS_TIMEOUT_SECS=600
#   ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS=1200
#   ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS=1800
#   MT_NODE_IMAGE=ghcr.io/flamegreat-1/etradie/mt-node:<PIN>
```

### 3.5 Verdict block — the 6-step success check

```bash
POD=$(kubectl -n etradie-system get pod \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[0].metadata.name}')
P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"

# 1. Pod readiness.
kubectl -n etradie-system get pod "$POD"
# Success: 3/3 Ready.

# 2. MT5 journal.
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/logs\"/*.log 2>/dev/null | head -1); \
   echo \"file: \$f, size: \$(wc -c < \"\$f\") bytes\"; \
   tr -d '\000' < \"\$f\""

# 3. EA's log directory (proves OnInit ran).
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "ls -la \"$P/MQL5/Logs/\" 2>&1 | head -10; \
   f=\$(ls -t \"$P/MQL5/Logs\"/*.log 2>/dev/null | head -1); \
   [ -n \"\$f\" ] && { echo \"--- \$f ---\"; tr -d '\000' < \"\$f\" | tail -60; }"

# 4. :5555 socket state.
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'cat /proc/net/tcp | awk "NR>1 && (\$3 ~ /:15B3/ || \$2 ~ /:15B3/){print}"'

# 5. accounts.dat presence (proves MT5 saved the login).
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "ls -la \"$P/config/accounts.dat\" 2>&1"

# 6. Final DB row state.
kubectl -n etradie-system exec -i postgres-0 -c postgres \
  -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message, mt5_symbol, is_active \
   FROM broker_connections WHERE connection_type='hosted';"

# Driver sentinels:
kubectl -n etradie-system logs "$POD" -c mt-node 2>&1 | grep -iE \
  'fluxbox ready|hard-kill watchdog armed|welcome modal|appeared after|deliver|paste|type|phase3 stage|phase5|LISTEN.*exit success|never bound|exiting|residual post-restart|attempt [123]|all three attempts'
```

### 3.6 Decision matrix

Look at the FIRST new line in the MT5 journal AFTER
`LiveUpdate downloaded successfully`. Cross-reference with driver log.

| Journal + driver log | Meaning | Next |
|---|---|---|
| Driver: `phase5: :5555 LISTEN at +<N>s after attempt <1\|2\|3>; EA OnInit succeeded` | Phase 5 chart-attach succeeded. EA bound. The attempt number tells you which mechanism worked (1=Ctrl+M default, 2=Ctrl+M context menu, 3=Alt+F fallback). | Wait for `3/3 Ready`. Run §3.8. DONE. |
| Driver: `phase5: attempt <N>: chart window WID=... visible after keystroke sequence` + `phase5: attempt <N>: chart opened but :5555 not bound within ...` | Chart opened but EA template did not auto-apply, OR EA OnInit failed silently. | Inspect EA log: §3.5 step 3. If `MQL5/Logs` is empty, the template directive in `startup.ini` did not apply -- check `config/startup.ini` `[Charts] Template=expert` is present. If EA log exists, look for an OnInit error. |
| Driver: `phase5: all three attempts failed to open a chart` | None of the three keystroke cascades produced a chart window. Either a modal stole focus on every attempt, the broker's Market Watch is empty (no symbols to chart on), or build 5836's Market Watch default action has been changed away from 'Chart Window' AND the File menu structure changed. | Run §3.7 with framebuffer screenshots from polls 4/8/12. Confirm Market Watch contains symbols. Check whether any persistent modal owns focus. |
| Driver: `phase5: attempt <N>: no chart window appeared within <N>s` (every attempt) + `phase5: all three attempts failed` | The broker has not populated Market Watch yet (the broker symbol-catalogue download has not landed by Phase 5 entry). | Raise `AUTO_LOGIN_PHASE5_POST_LOGIN_SETTLE_SECS` via `kubectl set env statefulset/$REL -c mt-node AUTO_LOGIN_PHASE5_POST_LOGIN_SETTLE_SECS=45`. |
| Driver: `Login dialog WID=... observed at +<N>s BUT :5555 already LISTEN; treating as residual post-restart dialog` | Phase 2a precedence guard fired. Subsequent boot, EA already bound, MT5 raised a residual Login dialog after LiveUpdate restart. | Healthy. DONE. |
| Journal: `Network '<server>': connecting` + `Login <id>: ok`. Driver: `Login dialog WID=... detected` (Phase 2a) OR `appeared after mnemonic / 9-down menu / 10-down menu` (Phase 2c) AND `deliver login: paste succeeded` etc. | Auto-login worked. `:5555` will bind once Phase 5 opens a chart and EA loads. | Wait for `3/3 Ready`. Run §3.8. DONE. |
| Journal: `Network ... connecting` + `Login <id>: invalid account` / `invalid password` / `account is disabled` | Auto-login worked; broker rejected credentials. | Check credentials with the user via the dashboard. NOT a code issue. |
| Journal: `Network '<server>': server not found` / `unknown server` | Server name reached MT5 but broker access-server resolution failed. | Inspect `/broker-bundle/` `servers.dat`. May indicate the server typed/pasted does not match a `servers.dat` entry. Fix the bundle upstream. |
| Journal: silent (no `Network` line at all). Driver: `deliver X: paste succeeded` + `phase3 stage=post_submit_1s focused_wid=<main>` | Phase 3 submit landed and the Login dialog closed, but MT5 never dispatched the broker connect. Field contents likely wrong (check §3.7 screenshot). | Run §3.7 driver-diagnostic with screenshot capture. |
| Driver: `deliver X: paste failed, falling back to type` + `deliver X: type fallback succeeded after paste failure` | Paste path failed but typing fallback recovered. Investigate paste failure cause but the user is unblocked. | Inspect xclip behaviour in the pod. May indicate xclip package issue. |
| Driver: `deliver X: BOTH paste and type failed` | Total Phase 3 delivery failure. | Run §3.7 driver-diagnostic. Check `kubectl exec ... which xclip xdotool` confirms binaries exist. Verify fluxbox `_NET_ACTIVE_WINDOW` via xprop. |
| Driver: `all three Phase 2c attempts ... failed` | Login dialog never opened. Could be menu position drift, focus issue, or fluxbox failed. | Run §3.7 with screenshot of MT5 main window post-Phase-2c. |
| Driver: `:5555 never bound within 240s total budget; exiting` (Phase 5 also failed) | Driver completed but EA didn't load. Could be: login succeeded but broker rejected, OR chart didn't open in Phase 5, OR template didn't auto-apply, OR EA `.set` issue. | Inspect Phase 5 sentinels first (`phase5:` lines). Then journal (case 2/3 above). If journal is silent AND Phase 5 reported chart open, the template directive did not apply -- check `config/startup.ini`. |

### 3.7 Driver diagnostic

```bash
POD=$(kubectl -n etradie-system get pod \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[0].metadata.name}')

# Driver log full.
kubectl -n etradie-system logs "$POD" -c mt-node \
  | grep -iE 'auto_login|fluxbox|MetaTrader exited|welcome modal|deliver|paste|type'

# Current visible windows on Xvfb.
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xdotool search --onlyvisible --name ".+" 2>&1 | while read wid; do echo "WID=$wid name=$(DISPLAY=:99 xdotool getwindowname "$wid" 2>/dev/null)"; done'

# Fluxbox EWMH atoms present?
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xprop -root _NET_SUPPORTED 2>&1 | tr "," "\n" | grep -iE "_NET_ACTIVE_WINDOW" | head -3'

# Tools available?
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c 'which xdotool xclip xprop xwd fluxbox'

# Framebuffer screenshot.
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xwd -root -silent > /tmp/screen.xwd && wc -c /tmp/screen.xwd'
kubectl -n etradie-system cp etradie-system/"$POD":/tmp/screen.xwd \
  ./mt5-screen.xwd -c mt-node
convert mt5-screen.xwd mt5-screen.png  # requires imagemagick on operator host
# View locally: xdg-open mt5-screen.png
```

#### Force the typing strategy (operator override)

If paste is silently failing without falling back correctly, force
typing-only:

```bash
kubectl -n etradie-system set env statefulset/"$REL" \
  -c mt-node AUTO_LOGIN_INPUT_STRATEGY=type
# StatefulSet will roll the pod with the override.
```

Reverting:

```bash
kubectl -n etradie-system set env statefulset/"$REL" \
  -c mt-node AUTO_LOGIN_INPUT_STRATEGY-     # trailing dash = unset
```

### 3.8 Smoking-gun proof — second-boot is fast and silent

After the first successful provision (`3/3 Ready`, `accounts.dat`
written), delete the pod and verify it returns to `3/3 Ready` in
20-40 seconds via the `accounts.dat` fast path.

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

kubectl -n etradie-system get pod "$POD"
# Success: 3/3 Ready in 20-40s.

# LiveUpdate did NOT re-run.
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  "f=\$(ls -t \"$P/logs\"/*.log | head -1); \
   echo -n 'downloads:       '; tr -d '\000' < \"\$f\" | grep -ac 'downloaded and updated'; \
   echo -n 'terminal starts: '; tr -d '\000' < \"\$f\" | grep -ac 'build .* started'; \
   echo -n 'login lines:     '; tr -d '\000' < \"\$f\" | grep -ac -E 'Network|Login|Authentication|connected'"

# Driver hit the fast path.
kubectl -n etradie-system logs "$POD" -c mt-node | grep -iE \
  ':5555 LISTEN.*(accounts.dat path|exit success)'
```

### 3.9 Quick fault map

| Symptom | Likely cause | First action |
|---|---|---|
| `LiveUpdate ... downloaded` repeating every boot; `restart_count` climbing | Cluster 1 regression (PVC destruction). | Verify `_best_effort_cleanup` in `provisioner.py` does NOT delete the wine-prefix PVC. |
| `MT_PASSWORD` shows as `<pid><restofpassword>` in `ps -ef` (legacy artefact only — unreachable now that paste is default and typing is via argv only briefly) | Cluster 3 regression (bash-source of Vault file reintroduced). | Check `entrypoint.sh` for `. "$VAULT_SECRETS_FILE"` reappearance. |
| Driver log: `Your windowmanager claims not to support _NET_ACTIVE_WINDOW` | fluxbox did not start or didn't publish EWMH atoms. | Check driver log for `fluxbox ready` line. If absent, fluxbox crashed; check the kubelet event log. |
| Driver log: `welcome modal still visible after Escape+Return; unmapping` | Welcome to LiveUpdate modal is sticky beyond Escape/Return. | Confirmed working: unmap path runs and the modal disappears. No action required unless Phase 2c also fails. |
| Driver log: `all three Phase 2c attempts ... failed to surface Login dialog` | File menu navigation isn't reaching Login. | Capture §3.7 screenshot. Inspect what's actually on the framebuffer. May need to tune `_drv_invoke_login_via_menu_n` Down count if MT5 build changes. |
| Driver log: `deliver X: BOTH paste and type failed` | xclip and xdotool both failed. | Check `kubectl exec ... which xclip xdotool`. Verify fluxbox is up. |
| Driver log: `:5555 never bound within 240s total budget` + journal silent | Login dialog actions never reached the broker connect layer. | Run §3.7. Compare paste vs type strategy via `AUTO_LOGIN_INPUT_STRATEGY=type`. |
| Driver log: `phase5: all three attempts failed to open a chart` | None of the three keystroke cascades (Ctrl+M default, Ctrl+M context menu, Alt+F File menu) produced a chart window. Possible causes: a persistent modal stole focus on every attempt, the broker's Market Watch is empty, or build 5836's Market Watch default action has been changed by an upstream Wine prefix mutation. | Capture §3.7 framebuffer screenshots. Inspect for focus-stealing modals and confirm Market Watch has symbols. If Market Watch is empty post-login, raise `AUTO_LOGIN_PHASE5_POST_LOGIN_SETTLE_SECS` to 45s. |
| Driver log: `phase5: attempt <N>: chart window WID=... visible after keystroke sequence` + `:5555 not LISTEN within 30s after attempt <N>` | Chart opened but EA template did not auto-apply, OR EA OnInit failed silently. | Check `config/startup.ini` carries `[Charts] Template=expert`. Check `MQL5/Logs` for an EA OnInit error. |
| Driver log: `Login dialog ... BUT :5555 already LISTEN; ... residual post-restart dialog` | Phase 2a precedence guard fired (subsequent-boot, EA already bound, MT5 raised a residual dialog after LiveUpdate restart). | Healthy -- no action. |
| Pod terminates at exactly 600s | Engine readiness gate fired. Boot didn't complete in budget. | Inspect driver log on the now-gone pod's PVC (preserved by design). |
| `:5555 LISTEN` present but pod still 2/3 | Watchdog HEALTH probe failing despite `:5555` bound. Usually means EA's AUTH_TOKEN doesn't match. | Inspect EA `.set` file: `MQL5/Profiles/Templates/ZeroMQ_EA.set`. |

---

## 4. Mounting the preserved PVC for offline inspection

When a pod is gone but the PVC survived (`_best_effort_cleanup`
invariant), inspect its contents via a one-shot debug pod:

```bash
PVC=$(kubectl -n etradie-system get pvc \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[0].metadata.name}')
echo "Preserved PVC: $PVC"

cat <<EOF | kubectl -n etradie-system apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: mt-debug-reader
spec:
  restartPolicy: Never
  securityContext:
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: reader
      image: ubuntu:24.04
      command: ["sleep", "1800"]
      volumeMounts:
        - name: wine-prefix
          mountPath: /mnt/wine
      securityContext:
        allowPrivilegeEscalation: false
        runAsNonRoot: true
        runAsUser: 1000
        capabilities:
          drop: ["ALL"]
        seccompProfile:
          type: RuntimeDefault
  volumes:
    - name: wine-prefix
      persistentVolumeClaim:
        claimName: $PVC
EOF

kubectl -n etradie-system wait --for=condition=Ready pod/mt-debug-reader --timeout=60s

# Read MT5 journal.
kubectl -n etradie-system exec mt-debug-reader -- sh -c '
  JOURNAL_DIR="/mnt/wine/prefix/drive_c/Program Files/MetaTrader 5/logs"
  ls -la "$JOURNAL_DIR"
  LATEST=$(ls -t "$JOURNAL_DIR"/*.log 2>/dev/null | head -1)
  echo "=== $LATEST ==="
  tr -d "\000" < "$LATEST"
'

# Read EA log (if it loaded).
kubectl -n etradie-system exec mt-debug-reader -- sh -c '
  EALOG="/mnt/wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs"
  ls -la "$EALOG" 2>&1
  LATEST=$(ls -t "$EALOG"/*.log 2>/dev/null | head -1)
  [ -n "$LATEST" ] && tr -d "\000" < "$LATEST" | tail -60
'

# Read startup.ini (redacted).
kubectl -n etradie-system exec mt-debug-reader -- sh -c '
  cat "/mnt/wine/prefix/drive_c/Program Files/MetaTrader 5/config/startup.ini" \
    | sed -E "s/(Password=).*/\1<REDACTED>/"
'

# Cleanup.
kubectl -n etradie-system delete pod mt-debug-reader --ignore-not-found
```

---

## 5. References

- `docker/mt-node/entrypoint.sh` — driver state machine + helpers.
- `docker/mt-node/watchdog.py` — health-probe sidecar.
- `docker/mt-node/Dockerfile` — image build (xvfb, fluxbox, xdotool,
  xclip, MT5, MT4, EA, watchdog).
- `helm/mt-node/values.yaml` — chart defaults (lockstep with
  provisioner).
- `helm/mt-node/templates/configmap-watchdog.yaml` — watchdog
  runtime tunables.
- `helm/mt-node/templates/statefulset.yaml` — pod spec template.
- `src/engine/ta/broker/mt5/hosted/provisioner.py` — engine-runtime
  provisioner (creates StatefulSets via K8s API).
- `src/engine/ta/broker/mt5/hosted/recovery.py` — background recovery
  sweep (rebuilds missing/unhealthy pods).

Git history holds the full evolution. For the diagnostic narrative
that led to the current design, read `git log --grep='mt-node'` and
`git log --grep='hosted'` on `main`.
