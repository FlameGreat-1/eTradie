# Hosted-MT (Wine) Provisioning — Runbook + Session Handoff

**Read this top-to-bottom before running anything.** This file is the
single source of truth for what is done, what is in flight, and what
the next operator action is. If the active session ended before the
final verdict, the operator picking up should be able to continue
without context loss.

---

## 1. Current state of the world (as of 2026-06-24, post-xdotool ship)

### 1.1 What is fixed and shipped on `main`

Four independent bug clusters have been diagnosed and closed. Each
landed a permanent fix on `main`; do not revisit these:

| # | Bug | Closed by |
|---|---|---|
| 1 | PVC destruction on every readiness timeout (drove an infinite LiveUpdate-redownload loop) | `_best_effort_cleanup` no longer deletes the wine-prefix PVC; `_READINESS_TIMEOUT_SECS` 300→600; `HostedRecoveryConfig.unhealthy_threshold_secs` 600→1200; new `fresh_provision_grace_secs=1800`; `entrypoint.sh` corruption-reset only wipes on missing `system32`; supervisor branches on exit-143 (LiveUpdate self-restart) with 30s settle and no `restart_count` increment; `terminationGracePeriodSeconds` 60/90→180; `preStop sleep` 5→30; `startupProbe.failureThreshold` 60→120 (620s budget). |
| 2 | Wrong launch flag (`/config:` only set config-file location, not auto-login) | Switched to `/portable`. The `/login /password /server` flags were tried as part of the same diagnosis chain but proven ineffective on build 5836 (see Cluster 4); they have since been removed. |
| 3 | Vault credential shell-expansion (`$$` in password expanded to bash PID via `. "$FILE"` in entrypoint) | Replaced bash-source with a pure-text parser that mirrors `docker/mt-node/watchdog.py::_load_vault_secrets_file` exactly. Whitelisted keys, no shell evaluation, regression guard logs WARN if `MT_PASSWORD` ever starts with the entrypoint's PID. |
| 4 | MT5 build 5836 ignores `/login /password /server` cmdline flags AND `startup.ini [Common]` auto-login block; broker connection never initiated; pod cycles every ~80s on watchdog SIGTERM | xdotool-driven GUI automation: `docker/mt-node/entrypoint.sh::auto_login_driver()` forks after the wine launch, waits for MT5's Login dialog, types credentials with `--clearmodifiers --delay 50`, ticks "Save account information" so MT5 writes `accounts.dat`, presses Return, dismisses follow-up dialogs (EULA, Welcome, broker terms). Subsequent boots use the MT5-written `accounts.dat` and the driver's idempotent fast-path exits on the immediate `:5555` LISTEN. Wine launch line is now `wine "$MT_EXE" /portable &` (no credential flags - strict improvement vs the previous `/password:$MT_PASSWORD` cmdline exposure). Cold-boot grace bumped 180→300s across the chart base values, the chart configmap-watchdog default, and the engine-runtime provisioner (LOCKSTEP INVARIANT). |

### 1.2 What is PENDING VERIFICATION (the only thing left)

Cluster 4 is the most recent ship. The image has been built off `main`
HEAD but the operator has NOT yet:

  1. Confirmed CI is green on the new SHA.
  2. Confirmed the new image SHA is pinned in
     `helm/engine/values-staging.yaml` and
     `helm/mt-node/values-staging.yaml` via the deploy-bump bot.
  3. Confirmed ArgoCD rolled both `engine-staging` and `mt-node-staging`
     to the new SHA.
  4. Re-provisioned a hosted connection from the dashboard.
  5. Confirmed via `ps -ef` that the wine cmdline is now
     `terminal64.exe /portable` only (no `/login` flags).
  6. Confirmed via journal that `Network ... connecting` and
     `Login ... ok` appear after `LiveUpdate downloaded successfully`.
  7. Confirmed `:5555` LISTEN + pod `3/3 Ready` + `accounts.dat`
     written to the PVC.
  8. Run the §3.8 smoking-gun proof (delete pod, comes back
     `3/3 Ready` in 20-40s via the accounts.dat fast path).

**THE NEXT ACTION the operator must take is documented in §2.6 below.**

### 1.3 Why this design (Cluster 4 background, for future-you)

When Clusters 1-3 were closed, the staging cluster reached this state
on a fresh provision and stayed stuck:

- Pod was `2/3 Running` (mt-node + watchdog Up; main's `:5555`
  startupProbe never satisfied).
- MT5 journal showed clean boot → LiveUpdate once → exit 143 → clean
  relaunch → then **silence** (no `Network` / `Login` /
  `Authentication` / `Profile` / `Chart` / `Expert` lines).
- `/proc/net/tcp` showed ONLY `:9100` (watchdog LISTEN) + a few
  `TIME_WAIT` from the one-shot LiveUpdate CDN hit. **Zero**
  outbound to any broker IP.
- `MQL5/Logs/` directory did NOT exist (EA never loaded).
- The pod cycled `terminal64.exe` every ~80 seconds via watchdog
  SIGTERM + supervisor respawn.
- `startup.ini`'s `[Common] Login/Password/Server` block WAS correctly
  populated. MT5 read the file. MT5 ignored it.
- The `/login /password /server` command-line flags DID reach
  `terminal64.exe`. MT5 ignored them too.

Definitive diagnosis (after exhaustive end-to-end audit of the
pipeline):

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

### 1.4 Chain of commits already on `main` (do not redo)

In chronological order:

| Commit | What it closes |
|---|---|
| `684746d5` | Cluster 1 - Engine: `_best_effort_cleanup` PVC preservation, readiness 300→600, recovery 600→1200, new `fresh_provision_grace_secs=1800`. |
| `ea5f0c1a` | Cluster 1 - Pod: corruption-reset only on missing `system32`; supervisor branches on exit-143 with 30s settle; chart `terminationGracePeriodSeconds` 60/90→180, `preStop` 5→30, `startupProbe.failureThreshold` 60→120. |
| `60aabc3a` | Cluster 1 - Chart: `helm/engine/values.yaml` aligned with new code defaults; new ConfigMap env var rendered. |
| `a74d8f1b` | CI lint UP017. |
| `6cbd1b51` | Cluster 2 - Pod: `/config:` → `/portable`. Proven insufficient on staging (no auto-login). |
| `c384a600` | Cluster 2 - Pod: launch flags become `/portable /login: /password: /server:`. Proven insufficient — flags reach the binary but MT5 build 5836 ignores them. SUPERSEDED by xdotool ship below; the `/login /password /server` flags were REMOVED in commit `2c675386`. |
| `87304e87` | Cluster 3 - Pod: pure-text Vault credentials parser replaces bash-source. Closes the `$$`/backtick/$(...) shell-expansion class of bug. |
| `fb17b7be` | Cluster 4 - Dockerfile: add `xdotool` + `x11-apps`. Chart: `startupGraceSeconds` 180→300 + `default "300"` in configmap-watchdog. Provisioner: `WATCHDOG_STARTUP_GRACE_SECONDS` 180→300 (LOCKSTEP). |
| `2248f1f7` | Cluster 4 - `entrypoint.sh`: add `DRIVER_PID` variable; extend `_shutdown` trap to tear the driver down BEFORE MT5 (xdotool mid-type into a closing window would otherwise inject keystrokes into nothing). |
| `695f1116` | Cluster 4 - `entrypoint.sh`: add `auto_login_driver()` function (~190 lines). Full contract documented in the function's docstring; summary in §2.3. |
| `2c675386` | Cluster 4 - `entrypoint.sh`: remove `/login /password /server` from wine launch (build 5836 ignores them; password no longer leaks into `/proc/<pid>/cmdline`). Fork `auto_login_driver` after MT5 launch; reap it (6s grace → SIGTERM → SIGKILL) on MT5 exit. |
| `26bf53b2` | Cluster 4 - `entrypoint.sh`: cleanup stale launch-flag comments in the supervisor loop so the documentation matches the code that actually runs. |
| `b49500dd` | Cluster 4 (Phase 2c, part 1/2) - `entrypoint.sh`: extend `auto_login_driver()` contract docstring with Phase 2a/2b/2c/2-final state machine; add three new bash defaults (`AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS=30`, `AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS=15`, `AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX='^MetaTrader [45] - (Netting|Hedging)'`). |
| `c6a180c1` | Issue #1 (LOCKSTEP) - `src/engine/ta/broker/mt5/hosted/provisioner.py`: `startupProbe.failure_threshold` 60→120 to match `helm/mt-node/values.yaml`. Closes the engine-runtime / chart-rendered drift that was killing the mt-node container at +320s on every fresh provision. |
| `f5b5a13c` + follow-ups | Issue #2 - `docker/mt-node/watchdog.py`: watchdog startup grace now measured per-MT-launch instead of per-pod. Adds `STATE.mt_launch_ts` + `STATE.mt_observed_running` + `update_mt_launch_tracker()` helper, called at the top of every poll. Replaces both `in_startup_grace` checks (happy-path + exception-handler) with the per-launch gate. Every supervisor respawn now gets the full 300s grace window from launch time. |
| (issue #3) | Issue #3 - `docker/mt-node/entrypoint.sh`: LiveUpdate self-restart classifier scoped to current MT5 boot via journal line-number comparison. The new discriminator: is the LAST `Terminal ... build NNNN started` line in the journal AFTER the LAST `LiveUpdate ... downloaded successfully` line? If yes, MT5 has already booted past that LiveUpdate event and exit-143 must be external (watchdog SIGTERM, kubelet preStop, etc) → count against `restart_count`. If no, MT5 has not yet booted past the most recent LiveUpdate event → wait `LIVEUPDATE_SETTLE_SECS` without incrementing. Closes the infinite supervisor respawn loop that occurred when issue #2's watchdog SIGTERMs were mis-classified as LiveUpdate self-restarts. |
| (issue #4) | Issue #4 - `docker/mt-node/entrypoint.sh`: Phase 2c keystroke sequence rewritten based on Claude Research evidence (no Ctrl+Shift+L accelerator exists on build 5836). New three-attempt order: (1) Alt+F → L mnemonic, (2) Alt+F → 9× Down → Return, (3) Alt+F → 10× Down → Return. The Ctrl+Shift+L attempt is REMOVED. New driver log sentinel lines: `Login dialog ... appeared after mnemonic` / `after 9-down menu` / `after 10-down menu` / `all three Phase 2c attempts ... failed`. |
| (issue #5) | Issue #5 - `docker/mt-node/entrypoint.sh`: Phase 3 stage-by-stage observability. Adds `_drv_phase3_log` helper that logs `phase3 stage=<name> focused_wid=<wid> name=<name>` at each Tab/type transition. NEVER logs `MT_PASSWORD`. Lets the operator pinpoint exactly which Tab transition went wrong if the dialog's actual Tab order differs from the assumed Login → Password → Server → Save → Login button. |
| `88d1b64c` | Cluster 4 (Phase 2c, part 2/2) - `entrypoint.sh`: implement the Phase 2c state machine. Adds helpers `_drv_find_window_by_regex` / `_drv_find_login_dialog` / `_drv_find_main_window` / `_drv_dismiss_welcome_modal` / `_drv_wait_for_dialog` / `_drv_invoke_login_via_hotkey` / `_drv_invoke_login_via_menu`. Driver now: (Phase 2a) polls for a Login-shaped dialog up to 30s; (Phase 2b) :5555 fast-path unchanged; (Phase 2c) on MT5 only, if the main UI window (`MetaTrader 5 - Netting|Hedging`) is visible, dismisses the `Welcome to LiveUpdate` modal, sends `Ctrl+Shift+L`, waits up to 15s, falls back to `Alt+F` → 9× `Down` → `Return` menu navigation, waits another 15s, and on dialog visible falls through to the unchanged Phase 3 typing logic. Phase 2-final keeps the original 120s budget for MT4 and any slow-render variant that does not match the main-window regex. Diagnosed from staging xwininfo (`MetaTrader 5 - Netting` + `Welcome to LiveUpdate` visible, no Login dialog ever rendered on build 5836 + pre-staged servers.dat + startup.ini). |

---

## 2. WHAT WAS SHIPPED — xdotool GUI automation

This section was "THE NEXT THING TO SHIP" in the previous runbook
revision. The fix is now landed on `main` across five files in four
commits (plus a comment-cleanup follow-up). The shipping plan is
preserved below as a historical record so future readers understand
why each change exists; the actual verification path is in §2.6 and
the command sequences are in §3.

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
| Login dialog never appears within 120s | MT5 crashed silently; OR `/portable` mode opening main UI without dialog | Log ERROR, exit; supervisor respawns. The 120s budget comes from `AUTO_LOGIN_DIALOG_WAIT_SECS`. |
| Login dialog appears but typing produces wrong chars | Wine keyboard layout drift | Driver calls `xdotool keyup Shift Control Alt Meta` before each type and uses `--clearmodifiers --delay 50` on every `xdotool type` call. |
| Login dialog accepts creds but broker rejects | Invalid creds (user-side error) | The dialog stays on screen; `:5555` never binds; the driver's 240s total budget expires; the supervisor SIGTERMs MT5 and respawns; same outcome until the user fixes their broker creds via the dashboard. NOT a code fix. |
| Login succeeds, but :5555 doesn't bind within 240s total | EA didn't load (template issue, EA binary missing) | Driver logs ERROR and exits 1; the watchdog will SIGTERM MT5 on its own loop and the supervisor will retry. Inspect `$MT_DIR/MQL5/Logs/*.log` for the EA's OnInit output. |
| Multiple identical follow-up dialogs (e.g. EULA + Terms + Welcome) | Broker first-launch wizard | Driver loop dismisses each non-MetaTrader-titled visible window via Return for `AUTO_LOGIN_FOLLOWUP_DISMISS_SECS=60`s. |
| Driver itself crashes | xdotool segfault, X server hiccup | The driver runs as a background child of entrypoint. The supervisor reaps it on MT5 exit (6s grace → SIGTERM → SIGKILL → `wait` to drain zombie); a driver crash does NOT force an MT5 respawn. |
| MT5 opens straight to main UI without a Login dialog (build 5836 + pre-staged `servers.dat` + `startup.ini [Common]`) | Modern MT5 builds treat a populated config dir as a returning installation and skip the first-run wizard; commercial VPS providers' xdotool drivers were written for the bare-prefix path and never see this case. | Phase 2c fires automatically. Driver logs `main UI window WID=... detected at +Ns; entering Phase 2c (menu-driven Login invocation)`, dismisses `Welcome to LiveUpdate`, sends `Ctrl+Shift+L`, falls back to `Alt+F` → 9× `Down` → `Return` if the hotkey is absorbed. On dialog visible, Phase 3 typing runs unchanged. NOT a code fix - the production behaviour. |

### 2.6 NEXT ACTION (operator picking up cold reads here)

The code is shipped on `main`. The operator's job from this point is
to deploy the new image and verify the fix end-to-end on staging.
Follow these steps in order; do not skip.

```bash
# Step 1 - Confirm CI built the new image off `main` HEAD.
cd ~/eTradie
git fetch origin main
git pull --rebase origin main
git log --oneline -8
# Expect to see (chronological, newest first):
#   <latest>  docs(runbook): xdotool fix is SHIPPED; ...
#   <latest>  docs(mt-node): rewrite stale launch-flag comment block ...
#   2c675386  fix(mt-node): launch wine /portable only; fork auto_login_driver ...
#   695f1116  fix(mt-node): add auto_login_driver() function for xdotool GUI automation
#   2248f1f7  fix(mt-node): add DRIVER_PID tracking and propagate SIGTERM to driver
#   fb17b7be  fix(mt-node): xdotool-driven auto-login for MT5 build 5836
#   ...

# Step 2 - Read the pinned mt-node SHA from staging values.
PIN=$(git show origin/main:helm/engine/values-staging.yaml \
  | grep -E '^[[:space:]]*tag:' | head -1 | tr -d ' "' | cut -d: -f2)
echo "Pinned mt-node SHA: $PIN"
# Expect: a SHA newer than the previous one. If the bot has not yet
# pushed the deploy-bump commit, wait and re-run this step.

# Step 3 - Verify the new image exists on GHCR (returns 200).
GH_OWNER=FlameGreat-1
GH_PAT=$(cat ~/.ghcr_pat)
token=$(curl -sS -u "$GH_OWNER:$GH_PAT" \
  "https://ghcr.io/token?service=ghcr.io&scope=repository:flamegreat-1/etradie/mt-node:pull" \
  | jq -r .token)
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $token" \
  -H "Accept: application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.v2+json" \
  "https://ghcr.io/v2/flamegreat-1/etradie/mt-node/manifests/$PIN"
# Expect: 200

# Step 4 - Establish SSH tunnel + ArgoCD sync (uses §3.1 routine).
ssh -N -L 6443:127.0.0.1:6443 etradie@<staging-host-ip> &
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes   # vmi3362776 Ready => tunnel live

kubectl -n argocd patch application engine-staging --type merge -p '{
  "operation": {
    "sync": {
      "revision": "HEAD",
      "syncOptions": ["Force=true", "Replace=true"]
    }
  }
}'
kubectl -n argocd patch application mt-node-staging --type merge -p '{
  "operation": {
    "sync": {
      "revision": "HEAD",
      "syncOptions": ["Force=true", "Replace=true"]
    }
  }
}' 2>/dev/null || true

# Step 5 - Confirm the engine picked up the new MT_NODE_IMAGE.
kubectl -n etradie-system rollout status deploy/etradie-engine --timeout=180s
kubectl -n etradie-system exec deploy/etradie-engine -c engine -- \
  printenv MT_NODE_IMAGE
# Expect: ghcr.io/flamegreat-1/etradie/mt-node:<PIN from step 2>

# Step 6 - Run §3.2 cleanup verbatim (drops any failed DB row,
# wipes orphan K8s objects + PVCs + Vault paths, rolls the engine).
# Then verify clean state per the same section.

# Step 7 - Re-provision from the dashboard. Enter the broker
# credentials. The provision is async; the StatefulSet will appear
# within seconds.

# Step 8 - Pre-flight check: confirm the new image is live on the
# new pod AND the wine cmdline NO LONGER carries credential flags.
REL=$(kubectl -n etradie-system get statefulset -o name \
  | grep 'etradie-mt-' | head -1 | cut -d/ -f2)
POD="${REL}-0"
kubectl -n etradie-system get pod "$POD" \
  -o jsonpath='{.spec.containers[?(@.name=="mt-node")].image}{"\n"}'
# Expect: ghcr.io/flamegreat-1/etradie/mt-node:<PIN>

sleep 30   # let terminal64.exe spawn
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'ps -ef | grep terminal64.exe | grep -v grep'
# Expect (NEW): C:\Program Files\MetaTrader 5\terminal64.exe /portable
# DO NOT expect: any /login: /password: /server: flags on the cmdline.
# If you see /login flags, the new image did NOT roll - back to Step 5.

# Step 9 - Watch the driver run. Tail the entrypoint log; the driver
# emits 'auto_login: ...' messages as it progresses.
kubectl -n etradie-system logs "$POD" -c mt-node -f \
  | grep -E 'auto_login|MetaTrader exited|LiveUpdate'
# Expected sequence on a successful first boot:
#   auto_login: start (budget=240s, login=..., server=...)
#   auto_login: terminal process detected at +Ns
#   LiveUpdate ... downloaded successfully       (from the MT5 journal mirror)
#   auto_login: Login dialog WID=... detected at +Ns
#   auto_login: credentials typed and submitted (server=..., save-account=on)
#   auto_login: dismiss follow-up window: 'Welcome ...' (WID=...)   [optional]
#   auto_login: :5555 LISTEN at +Ns; exit success

# Step 10 - Run the §3.5 NEXT-ACTION verdict block. Match the
# journal output against the §3.6 decision matrix.

# Step 11 - On success (login worked, :5555 bound, pod 3/3 Ready),
# run the §3.8 smoking-gun proof: delete the pod, confirm it returns
# to 3/3 Ready in 20-40s via the accounts.dat fast path. If the
# driver log shows 'auto_login: :5555 LISTEN ... (no dialog needed;
# accounts.dat path); exit success', the steady-state is correct.
```

If any step fails, drop to §3.7 (driver-diagnostic) and §3.9 (quick
fault map) for the recovery paths. Do NOT improvise outside the
documented decision matrix without a hard reason.

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

Look at the first NEW line that appears AFTER `LiveUpdate downloaded successfully`. For the silent cases, ALSO grep the driver log (`kubectl ... logs ... | grep -iE 'auto_login'`) so you can discriminate between Phase 2a, Phase 2c hotkey, Phase 2c menu, and total-no-prompt.

| Journal + driver log | Meaning | Next |
|---|---|---|
| Journal: `Network '<server>': connecting to access point` + `Login <id>: ok`. Driver: `Login dialog WID=... detected` (Phase 2a) OR `Login dialog WID=... appeared after mnemonic` (Phase 2c attempt 1) OR `Login dialog WID=... appeared after 9-down menu` (Phase 2c attempt 2) OR `Login dialog WID=... appeared after 10-down menu` (Phase 2c attempt 3). | Auto-login WORKED via whichever path. `:5555` will bind once the EA loads. Read the Phase 3 `phase3 stage=*` log lines to confirm typing went into the dialog (not the main window). | Wait for `3/3 Ready`. Run the §3.8 smoking-gun proof. DONE. |
| Journal: `Network ...` + `Login <id>: invalid account` / `invalid password` / `account is disabled` | GUI driver worked; credentials wrong (NOT a code fix). | Check broker creds with the user via the dashboard. |
| Journal: `Network '<server>': server not found` / `unknown server` | GUI driver worked; `servers.dat` for the broker is missing or wrong. | Inspect bundle: `kubectl exec ... ls -la /broker-bundle/`. Fix the bundle's `servers.dat` upstream. |
| Journal: silent after `LiveUpdate downloaded successfully`. Driver: `main UI window WID=... detected ... entering Phase 2c`, then either `appeared after ctrl+shift+l` or `appeared after alt+f menu` line within 30-45s of the Phase 2c entry. | Phase 2c invoked the dialog successfully and Phase 3 is mid-typing the credentials. Slightly slower than Phase 2a but converging. | Wait up to the §3.5 6-min poll cycle for the journal to add `Network ... connecting` + `Login ... ok`. |
| Journal: silent. Driver: `main UI window WID=... detected ... entering Phase 2c` followed by `both ctrl+shift+l and alt+f menu path failed to surface Login dialog`. | Phase 2c invoked but MT5 absorbed both the hotkey and the menu navigation (build-specific menu position drift, foreign keyboard layout under Wine, or modal grabbed focus mid-invoke). | Run §3.7 driver-diagnostic. Capture `xwininfo` after Phase 2c to see what windows were on the framebuffer when the hotkey/menu fired. If the `File` menu position has drifted from build 5836, tune the `Down` keypress count in `_drv_invoke_login_via_menu`. If the keyboard layout is misinterpreting `Ctrl+Shift+L`, set `AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS=0` to skip the hotkey attempt and go straight to menu navigation. |
| Journal: silent. Driver: NO `main UI window WID=... detected` line at all, but `Login dialog never appeared within 120s and :5555 not bound` at +120s. | MT5 main UI never rendered with a matching title; OR the dialog never appeared with a matching title. | Run §3.7 driver-diagnostic. Inspect `xwininfo` for what windows ARE present. If `MetaTrader 5 -` appears with a different suffix (e.g. neither `Netting` nor `Hedging`), broaden `AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX`. If a Login-shaped window IS present but with an unexpected title, broaden `AUTO_LOGIN_DIALOG_TITLE_REGEX`. |
| Journal: silent. Driver: NO `main UI window WID=...` line AND NO `Login dialog WID=...` line, then exits at +120s. | Neither path matched anything visible on the framebuffer. Likely Wine/Xvfb is genuinely broken (X server failed to start, or wineserver hung). | Run §3.7 driver-diagnostic + §3.9 quick fault map row for `Pod RESTARTS climbing every ~80s`. |

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

#### Phase 2c verification sub-routine

After the staging diagnostic on commits b49500dd + 88d1b64c, the
driver MUST emit one of the following sentinel lines on any boot
that does not hit the Phase 2b accounts.dat fast path. Use this
sub-routine to verify the Phase 2c state machine actually ran the
way it was designed to:

```bash
POD=$(kubectl -n etradie-system get pod \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[0].metadata.name}')

# Did Phase 2a find the dialog on its own? (Path the original
# design assumed; happy path on fresh prefixes.)
kubectl -n etradie-system logs "$POD" -c mt-node \
  | grep -E 'auto_login:.*Login dialog WID=.* detected at \+[0-9]+s$' || \
  echo 'Phase 2a did NOT find the dialog'

# Did Phase 2c fire (build-5836 + pre-staged-config path)?
kubectl -n etradie-system logs "$POD" -c mt-node \
  | grep -E 'auto_login: main UI window WID=.* entering Phase 2c' || \
  echo 'Phase 2c was NOT triggered (either Phase 2a won, or main UI never rendered)'

# Which Phase 2c sub-path resolved the dialog?
kubectl -n etradie-system logs "$POD" -c mt-node \
  | grep -E 'auto_login: Login dialog WID=.* appeared after (ctrl\+shift\+l|alt\+f menu)' || \
  echo 'Neither Phase 2c sub-path produced the dialog'

# Did Phase 2c fail both sub-paths? (Indicates menu drift or
# keyboard-layout problem.)
kubectl -n etradie-system logs "$POD" -c mt-node \
  | grep -E 'auto_login: both ctrl\+shift\+l and alt\+f menu path failed' && \
  echo 'PHASE 2C FAILURE - tune _drv_invoke_login_via_menu Down count or AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX'

# Capture the framebuffer state at the moment Phase 2c was supposed
# to fire so you can see whether the main window really had a
# matching title. Run this BEFORE the supervisor respawns MT5.
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xdotool search --onlyvisible --name ".+" 2>&1 | while read wid; do echo "WID=$wid name=$(DISPLAY=:99 xdotool getwindowname "$wid" 2>/dev/null)"; done'
```

If the visible-window list shows a `MetaTrader 5 -` title with a
suffix that is NOT `Netting` or `Hedging` (e.g. some brokers tag the
window with the account number, like `MetaTrader 5 - 12345678`),
broaden `AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX` to match. Until then,
Phase 2c will not fire and the driver will sit at the 120s Phase
2-final timeout.

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
