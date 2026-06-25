# Hosted-MT (Wine) Provisioning — Operator Runbook

**Single source of truth for operating the hosted-MT provisioning
system. Read top-to-bottom. Every command is copy-paste verbatim.**

Historical context (Cluster 1-4 diagnoses, Issue #1-5 fixes, the
xdotool/fluxbox/paste evolution, Phase 5 iterations) lives in
`git log`. This runbook is strictly for operating the system as it
stands today.

---

## A. Current Verified Ground Truth (read first)

Evidence captured 2026-06-24 / 2026-06-25:

### A.1 What is verified working

- The Vault Agent renders broker credentials to
  `/vault/secrets/mt-credentials.env` correctly. Parsed by both
  `entrypoint.sh` (literal-text parser, never `source`) and
  `watchdog.py`. The historical `$$`-PID-prefix regression cannot
  recur from this code path.
- Fluxbox starts under Xvfb and publishes `_NET_ACTIVE_WINDOW` /
  `_NET_SUPPORTED` within ~200ms (`fluxbox ready` line in driver log).
- Phase 1 (terminal wait) reliably detects `terminal64.exe` at +0s.
- Phase 2a (Login dialog poll) and Phase 2c (`Alt+F` + `L` menu
  mnemonic) both work. The 2026-06-24 18:11 run captured Phase 2c
  attempt 1 succeeding at +33s after main UI detection.
- Phase 3 (paste credentials via X CLIPBOARD + Ctrl+V) works. The
  same run delivered login (len=9), password (len=13), server
  (len=15) atomically with no per-char drops. `accounts.dat`
  (4635 bytes) was written by MT5 indicating the Save checkbox
  was correctly ticked.
- Phase 3 submit closes the Login dialog cleanly and MT5's MDI
  frame title transitions to `<login> -   - Netting` (the
  post-submit title shape on the headless pod).
- The hard-kill watchdog (`AUTO_LOGIN_TOTAL_BUDGET_SECS +
  AUTO_LOGIN_HARD_KILL_GRACE_SECS = 270s`) reliably reaps the
  driver subshell.
- Broker catalog registry (`infrastructure/broker-catalog/`) is
  loaded fail-closed at engine boot via
  `src/engine/ta/broker/registry.py`. Exness + Deriv entries are
  present with `status: active`. Phase-1 bakes are uploaded to R2:
    - Exness: `https://pub-5bdcacdedad6458298e8b8d5435f301a.r2.dev/broker-bundles/exness-portable.zip`
      sha256 `eadee9c7a152514f9c904b381a9416cf3d88dc5e480a12a62544079743c5e11c`
      (size 149 MB, contains `MetaTrader 5 EXNESS/Config/servers.dat`
      at 471,796 bytes — verified by direct download + unzip
      against the catalog pin).
    - Deriv: similarly uploaded and pinned.
- The `HostedProvisioner` attaches the `broker-bundle`
  initContainer to every per-tenant StatefulSet. K8s events on
  the 2026-06-25 05:39 pod recreation explicitly show
  `Created container broker-bundle` and `Started container
  broker-bundle` immediately before the `mt-node` container.
  The broker bundle initContainer IS being delivered.

### A.2 What is verified about MT5's post-login behaviour

Verified on operator's workstation 2026-06-25 (interactive Wine +
real X display, NOT Xvfb), with both branded MT5 builds launched
via `wine terminal64.exe /portable` (same flag the pod uses).
MT5 emits TWO distinct MDI frame title shapes post-login, and the
regex / title-detection code must handle both:

**Shape A — immediately after login, BEFORE any chart is focused:**
  - Exness: `133978149 - Exness - MT5Real9 -Hedge - Exness Technologies Limited Ltd`
  - Deriv:  `201415706 - Deriv - Demo: Demo Account - Hedge -Deriv.com Limited`

**Shape B — when a default chart is FOCUSED (after MT5 opens its
4-5 default charts and the user/automation clicks one):**
  - Exness: `133978149 - Exness - MT5Real9 -Hedge - Exness Technologies Limited Ltd -XAUUSDm,1h`
  - Deriv:  `201415706 - Deriv - Demo: Demo Account - Hedge -Deriv.com Limited - EURUSD,1h`

In other words: Shape B = Shape A + ` -<SYMBOL>,<TIMEFRAME>`
appended. The spacing of the trailing chart suffix varies between
brokers (Exness uses ` -<sym>`, Deriv uses ` - <sym>`), so the
regex must tolerate optional spaces around the trailing dash.

Full observation per broker:

- **Exness branded MT5**: relaunched against the preserved bake
  prefix → auto-loaded login from `accounts.dat` (saved during
  the bake 3 days earlier) → MDI frame title shown in Shape A →
  **opened 5 default charts on its own** (`XAUUSDm,H1` and
  variants; only the first symbol's chart visually painted
  because the others are broker-specific prefixed symbols whose
  data was not in the local prefix) → Market Watch panel open
  with 5 symbols → Navigator panel open. Clicking a child chart
  updates the MDI frame title from Shape A to Shape B with
  `-XAUUSDm,1h` appended. **No keystroke driving was needed;
  MT5 opened charts by itself.**
- **Deriv branded MT5**: identical behaviour. Auto-loaded login
  → MDI title in Shape A → **opened 4 default charts** (all
  visible: `EURUSD,H1` etc.) → Market Watch open with 9 symbols
  → Navigator open. Clicking a chart appends ` - EURUSD,1h`
  (Shape B). A one-shot residual `Login to Trade Account`
  popup appeared on first relaunch but disappeared on the next
  relaunch; this is the same residual dialog Phase 2a's `:5555`
  precedence guard was designed to handle.

**Conclusion:** branded MT5 builds with their own `servers.dat`
DO auto-open charts after login. The original Phase 5 hypothesis
("MT5 never opens a chart on its own") was based on the pod's
behaviour with a GENERIC servers.dat. We do not yet know
whether the branded MT5 in the headless Wine+Xvfb pod also
auto-opens charts; that is what the next diagnostic must
determine (Section C). The title-regex implications are tracked
in Section F.1.

### A.3 What is verified broken / unknown on the pod

2026-06-24 18:11 staging run captured in NOTE.md (14 polls,
both boots of pod `etradie-mt-89660d92-9e3-0`):

- Boot 1 (17:00:34 → 17:06:17): Phase 2c attempt 1 succeeded
  (`Login dialog WID=12582938 detected at +33s`). Phase 3
  paste delivered all three fields. Submit succeeded. Title
  changed to `133978149 -   - Netting`. `accounts.dat` was
  written.
- **Then Phase 5 ran all three keystroke cascades and ALL
  three failed.** Framebuffer screenshots from polls 4-12
  are identical 3691-byte blanks (nothing rendering visually
  for 4+ minutes). `MQL5/Logs/` never appeared. `:5555` never
  bound. The supervisor saw the driver exit, MT5 was SIGTERM'd
  at +270s by the hard-kill, exit code 143.
- Phase 5 attempt 3 explicitly UNMAPPED `WID=18874369
  NAME=logs` (MT5's own Journal/Toolbox panel materialising
  post-login). This is destructive to MT5's UI assembly.
- Boot 2 (17:06:47 → pod terminated by engine readiness
  timeout): `accounts.dat` fast path. Login dialog at +9s,
  paste succeeded. But Phase 5 logged `no main window WID
  provided; cannot drive menu navigation` (the boot-2 title
  regex bug fixed in commit 29f29a6f). Phase 4 polled `:5555`
  to no avail. Pod killed at ~600s.

### A.4 What was found on the preserved PVC (2026-06-25 05:30)

Wine-prefix PVC `wine-prefix-etradie-mt-89660d92-9e3-0`
survived all pod recreations (StatefulSet retention policy
`Retain`). Inspected via a one-shot debug pod:

- `config/servers.dat`: present, 472,364 bytes, sha256
  `28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b`.
  Same size as the workstation's local Exness bake's
  `servers.dat` (472,364 bytes) — strongly suggests the Exness
  bundle's `servers.dat` WAS installed by entrypoint.sh's
  copy block, then mutated by MT5 on its own subsequent runs.
- `config/accounts.dat`: present, 4,635 bytes (proves Phase 3
  paste + Save-checkbox succeeded at SOME boot).
- `MQL5/Logs/`: **DOES NOT EXIST**. Proves no EA's OnInit has
  ever run successfully on this PVC.
- `logs/<date>.log` (MT5 journal): **63 fresh `MetaTrader 5
  x64 build 5836 started for MetaQuotes Ltd.` cold-boot banners
  spanning 04:00 → 05:35 UTC on 2026-06-25, with NOTHING ELSE
  between them.** Not a single `Network 'Exness-MT5Real9':
  connecting` line. Not a single login attempt log entry.
  MT5 launched 63 times and exited each time before doing
  anything past cold boot.

### A.5 What we learned about `strings | grep` as a verification gate

The `strings | grep -i <brand>` gate from §3.5 of the
MT5 Multi-Broker Provisioning Architecture document is
**NOT a reliable signal**. The local Exness bake's
`servers.dat` ALSO returns zero matches for
`strings | grep -ic exness`, yet the workstation MT5 logged
in successfully to Exness and rendered the full account
title including `Exness Technologies Limited Ltd`. MetaTrader
stores broker server names in `servers.dat` in an
obfuscated/encrypted binary form that `strings` cannot
recover. The only reliable verification is to LAUNCH MT5
against the bundle and watch it actually connect.

### A.6 Engine recovery was re-creating the failed pod (FIXED by MR !25)

K8s events on 2026-06-25 05:39, 05:50, 06:00 (and continuing)
show `recovery.py` re-creating the StatefulSet's pod on a
~10-minute cadence even though the DB row is `failed`.
Each pod runs the bake's startup, MT5 launches, MT5 exits
immediately after writing the cold-boot banner (as observed
in A.4), startup probe fails, kubelet kills the container,
recovery rebuilds. The 2026-06-25 preserved-PVC inspection
captured 63 such fresh cold-boot banners in 1.5 hours.

**Fixed in MR !25 (merged 2026-06-25):** `_reprovision()` now
skips rows where `broker_connections.status='failed'`. Recovery
only fires for rows in `ready / connected / disconnected /
error / untested / provisioning` states. To re-test a failed
connection an operator must DELETE the row + re-create from
the dashboard (which writes a fresh row with
`status='provisioning'`), or POST `/api/broker/connections/{id}/test`
to transition off `failed`.

### A.7 First reprovision after MR !25 + !26 merged (operator-reported)

Operator confirmed (just before this runbook update) that a
reprovision they ran after merging MRs !24 / !25 / !26
**completed the login step and created the broker profile**
on MT5's side (Vault credentials reached MT5, broker accepted
the login, profile was created in MT5's account store).

This indicates that MR !25 alone unblocked the destructive
recovery-rebuild loop that was preventing MT5 from completing
its post-login internal setup. The previous 63 cold-boot
banners on the preserved PVC are now explained as: each pod
was being killed by the startup probe (because :5555 had not
yet bound) AND immediately re-created by recovery, leaving
MT5 no contiguous window to finish its work.

What is STILL unverified (the next staging run must capture):

  - Whether the post-MR-!25 pod has reached :5555 LISTEN.
  - Whether the pod's MDI frame title shows Shape A (full)
    or the degraded `<login> -   - Netting`. The previous
    staging run captured the degraded shape but that pod
    was being thrashed by recovery; the post-!25 pod may
    now produce Shape A.
  - Whether the headless MT5 also auto-opens charts (and how
    many, on what symbols).
  - Whether `MQL5/Logs/` populated (proves EA OnInit ran).

The operator will reprovision and capture this evidence via
the full instrumented script in the new session. The pending
fixes in Section F are gated on that evidence.

---

## B. Open Questions (the diagnostic gap)

We cannot yet explain why MT5 launches and immediately exits
after writing only the cold-boot banner. Candidates:

1. **The Exness `servers.dat` from the bundle is not actually
   recognised by MT5 inside the Wine+Xvfb pod environment.**
   On the workstation MT5 worked because `accounts.dat` was
   present and accounts.dat carries enough state to short-
   circuit server-resolution. In the pod, `accounts.dat`
   does not exist on the FIRST boot of a fresh PVC, so MT5
   must resolve `Server=Exness-MT5Real9` against `servers.dat`,
   and if that resolution fails MT5 may silently exit
   (no journal entry beyond cold-boot banner). NEEDS
   VERIFICATION: read the pod's mt-node container log to see
   whether `entrypoint.sh` actually logged
   `Installed broker servers.dat from bundle ($_sd)`.
2. **The broker-bundle initContainer extracted the zip to a
   path the entrypoint's find() does not locate.** The bundle
   contains `MetaTrader 5 EXNESS/Config/servers.dat` (note the
   capital `C`). The entrypoint runs
   `find /broker-bundle -type f -iname 'servers.dat'` which IS
   case-insensitive, but the install line copies the FIRST
   match — if the bundle also contains some other
   servers.dat earlier in the find order (unlikely from the
   listing, but possible), the wrong file could win.
3. **MT5 is crashing on launch under Wine+Xvfb specifically.**
   The 63 cold-boot banners with nothing after them is
   consistent with MT5 crashing immediately after writing
   the banner. The workstation's interactive X display
   doesn't reproduce this. A specific Wine+Xvfb interaction
   that the branded Exness installer needs could be missing.
4. **Phase 5's keystroke cascade is no longer the suspect**
   for the cold-boot-only journal pattern. Phase 5 only
   runs AFTER Phase 3 submit produces a Login dialog. The
   2026-06-25 journal shows NO Login dialog was ever
   surfaced on those 63 pod restarts — MT5 didn't get that
   far. Phase 5 cannot affect a boot that exits before the
   Login dialog opens. Phase 5 IS still suspected for the
   original 18:11 boot-1 failure (where MT5 DID get to a
   Login dialog and Phase 3 succeeded but Phase 5 then
   disrupted post-login chart attach), but that is a
   separate, downstream failure mode.

---

## C. Immediate Next Steps (run these next, in order)

### C.1 Stop the recovery loop from clobbering diagnostics

Before reading the live pod logs, pause the engine's recovery
sweep so the pod does not get killed mid-`kubectl logs`. The
recovery sweep restarts unhealthy pods after
`ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS` (1200s) but
the startupProbe is what's killing them. Easiest path: scale
the StatefulSet to 0 (the connection_id stays in the DB,
recovery rebuilds it but we have a window to grab logs from
the current running pod first).

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes

# Get the current pod NOW while it's alive
POD=$(kubectl -n etradie-system get pod \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
echo "POD=$POD"
```

Do NOT scale to 0 yet — grab logs first.

### C.2 Capture the FULL mt-node container log + the broker-bundle initContainer log

This is the smoking-gun evidence we are missing. The
entrypoint logs to stderr; mt-node container's `kubectl logs`
output is the full picture from container start.

```bash
# Full mt-node container log
kubectl -n etradie-system logs "$POD" -c mt-node > /tmp/mt-node-full.log 2>&1
wc -l /tmp/mt-node-full.log

# Lines that prove broker-bundle handling
grep -nE 'Vault credentials file|Loaded.*Vault-rendered|Installed broker|broker-bundle|servers.dat|Wine prefix|Xvfb ready|fluxbox ready|Launching|MetaTrader exited|auto_login: start|terminal process detected|Login dialog|Phase 2c|phase3 stage|deliver login|paste login|credentials delivered|phase5' /tmp/mt-node-full.log

# broker-bundle initContainer log
kubectl -n etradie-system logs "$POD" -c broker-bundle > /tmp/broker-bundle.log 2>&1
cat /tmp/broker-bundle.log
```

Expected lines that PROVE the bundle was installed:
  - broker-bundle log: `Downloading https://pub-5bdcacde.../exness-portable.zip...`
  - broker-bundle log: `<sha>  /broker-bundle/bundle.zip: OK`
  - broker-bundle log: `Bundle extracted successfully.`
  - mt-node log: `Installed broker servers.dat from bundle (/broker-bundle/MetaTrader 5 EXNESS/Config/servers.dat)`

If any of those four lines is missing, that is the bug.

### C.3 Capture the MT5 journal AND directory listing from the live pod

```bash
P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"

kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c "
  echo '=== MT_DIR contents ==='
  ls -la \"$P/config\"
  echo
  echo '=== Is the EXNESS bundle dir present at /broker-bundle/MetaTrader 5 EXNESS? ==='
  ls -la '/broker-bundle/' 2>&1
  echo
  echo '=== servers.dat resolution ==='
  find /broker-bundle -type f -iname 'servers.dat' 2>/dev/null
  echo
  echo '=== servers.dat installed in MT_DIR ==='
  ls -la \"$P/config/servers.dat\" 2>&1
  echo
  echo '=== MT5 journal (latest 100 lines, NULL-stripped) ==='
  f=\$(ls -t \"$P/logs\"/*.log 2>/dev/null | head -1)
  if [ -n \"\$f\" ]; then
    echo \"journal: \$f\"
    tr -d '\\000' < \"\$f\" | tail -100
  else
    echo 'No journal yet'
  fi
  echo
  echo '=== :5555 socket state ==='
  awk 'NR>1 && (\$2 ~ /:15B3/ || \$3 ~ /:15B3/){print}' /proc/net/tcp
"
```

### C.4 Decision based on C.2 / C.3 output

See Section D below.

---

## D. Decision Tree (what to commit / what to test based on C output)

### D.1 If broker-bundle log shows `Bundle extracted successfully.` AND mt-node log shows `Installed broker servers.dat from bundle ...`

The bundle install path is working. The bug is elsewhere
(MT5 crashing under Wine+Xvfb post-install, or some other
post-bundle-install pipeline issue). Next diagnostic:

  - Compare the size of `$MT_DIR/config/servers.dat` on the
    pod against the local workstation Exness bake's
    `servers.dat`. Should be identical (472,364 bytes).
  - If sizes match, MT5 is launching with a perfectly good
    servers.dat but still exiting after the cold-boot banner.
    That points to a Wine+Xvfb runtime issue with the branded
    binary. Possible next test: launch the EXNESS-baked
    `terminal64.exe` under `xvfb-run` on the workstation to
    reproduce the crash locally.

### D.2 If broker-bundle log shows a failure (404, sha256 mismatch, unzip error)

The initContainer is broken. Fix the initContainer's
command string in
`src/engine/ta/broker/mt5/hosted/provisioner.py::_upsert_statefulset`
and mirror it in `helm/mt-node/templates/statefulset.yaml`.

### D.3 If broker-bundle log shows success but mt-node log does NOT show `Installed broker servers.dat from bundle ...`

The entrypoint's find() is not locating the bundle's
`servers.dat`. Fix `docker/mt-node/entrypoint.sh` — possibly
the `iname 'servers.dat'` find or the `<<EOF` heredoc loop.
Run the find manually inside the pod to see what it would
pick. The bundle's known path is
`/broker-bundle/MetaTrader 5 EXNESS/Config/servers.dat`.

### D.4 If servers.dat IS installed and MT5 STILL exits without Login dialog

This is a real Wine+Xvfb runtime issue with the branded
binary. Two options:

  - Option 1: launch the branded binary on the workstation
    under `xvfb-run` (not interactive X) to reproduce. If it
    crashes there too, the bake itself has a Wine
    incompatibility we missed. Likely fix: re-bake against
    the exact WineHQ pin from `docker/mt-node/Dockerfile`
    (`WINEHQ_VERSION` build-arg).
  - Option 2: layer ONLY `servers.dat` (and any other config
    files MT5 needs to resolve the broker) into the existing
    GENERIC mt-node image, instead of running the broker-
    branded `terminal64.exe`. Per the MT5 Multi-Broker
    Provisioning Architecture doc §7.5, this was the
    intended design from the start: "the chosen design layers
    ONLY `servers.dat` (+ companions) via the bundle volume
    and keeps the generic portable terminal as the base."
    Check whether the current bundle is layering the WHOLE
    branded MT5 install or just the config files.

### D.5 If C.2 / C.3 reveal that boot-1 of the recovery-recreated pod actually DID get past cold-boot (Login dialog, Phase 3, etc.) and only failed in Phase 5

Then Phase 5 is still the suspect. The fix path is:
  - Disable Phase 5 by default
    (`AUTO_LOGIN_PHASE5_ENABLED=0`).
  - Trust MT5 to open its own charts after login (verified on
    workstation for both Exness and Deriv).
  - Phase 4 polls `:5555` for the remaining budget while
    dismissing follow-up dialogs (already correct).
  - One-line code change in `docker/mt-node/entrypoint.sh`,
    no image rebuild needed for testing (override via
    `kubectl set env statefulset/<release> -c mt-node
    AUTO_LOGIN_PHASE5_ENABLED=0`).

---

## F. Pending Fixes — Not Yet Committed (decision criteria from next run)

Two fixes have been identified but NOT yet committed because they
depend on evidence we will only have after the next staging run
completes against the post-MR-!25-merge image. Documenting them
here so an incoming operator can commit the right fix without
re-deriving the analysis from chat history.

### F.1 Update AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX to match real titles

Current regex (committed in commit `29f29a6f` via MR !23):

```
^(MetaTrader [45] - (Netting|Hedging)|[0-9]+ - +- (Netting|Hedging))
```

The two alternations are:
  - PRE-login: `MetaTrader 5 - Netting` (correct, retained)
  - POST-login degraded: `<login> -   - Netting` (the shape the
    failed staging pod was producing under recovery thrashing;
    likely NOT the shape a healthy pod will produce).

The REAL post-login title shapes (per Section A.2) are:

  - Shape A (post-login, no chart focused):
    `<login> - <broker> - <server> -<account_type> -<entity>`
    e.g. `133978149 - Exness - MT5Real9 -Hedge - Exness Technologies Limited Ltd`

  - Shape B (chart focused):
    Shape A + ` -<SYMBOL>,<TIMEFRAME>`
    e.g. `133978149 - Exness - MT5Real9 -Hedge - Exness Technologies Limited Ltd -XAUUSDm,1h`

#### Why this fix is NOT yet committed

The regex must match whatever the POD actually emits, not what
the workstation emits. The headless Wine+Xvfb runtime may produce
a slightly different title shape (different spacing, different
entity-name rendering, broker-specific quirks). Committing a
regex that matches the workstation title but not the pod title
would repeat the original mistake from `29f29a6f`.

#### Decision criteria from next run

In the next staging run, capture the running pod's MDI frame
title via:

```bash
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xdotool search --onlyvisible --name ".+" 2>&1 \
   | while read wid; do echo "WID=$wid name=$(DISPLAY=:99 xdotool getwindowname "$wid" 2>/dev/null)"; done'
```

Then update `AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX` to add a third
alternation matching the observed title. The expected commit
shape, assuming the pod produces something close to Shape A:

```
^(MetaTrader [45] - (Netting|Hedging)|[0-9]+ - +- (Netting|Hedging)|[0-9]+ - [A-Za-z0-9.][A-Za-z0-9. _-]* - .+ -+(Hedge|Netting) ?-+ ?[A-Za-z0-9.,()' _-]+( -+ ?[A-Za-z0-9._#@!^+\-]+,[A-Za-z][0-9]+)?$)
```

The third alternation is intentionally permissive on the entity
name (varies by broker / regulator) and on the trailing chart
suffix (optional, Shape A vs Shape B). It is anchored at
start-and-end so log-window titles ('logs', 'Toolbox', ...) cannot
match.

Verify the proposed regex against the pod's captured title with:

```bash
echo '133978149 - Exness - MT5Real9 -Hedge - Exness Technologies Limited Ltd' \
  | grep -E '<proposed regex>'
```

before committing.

### F.2 Phase 5 (keystroke chart-attach) — disable by default?

Current default: `AUTO_LOGIN_PHASE5_ENABLED=1` (Phase 5 ACTIVE).
Phase 5 runs a 3-attempt keystroke cascade (Ctrl+M Market Watch
flow + File menu fallback) AFTER Phase 3 submit, on the theory
that MT5 needs help to open a chart that loads the EA template.

#### Why this fix is NOT yet committed

The workstation verification proved branded MT5 builds DO
auto-open charts on their own after login (Section A.2). This
strongly suggests Phase 5 is unnecessary in the broker-branded
MT5 path. But we have not yet verified the SAME behaviour in
the headless Wine+Xvfb pod. The failed staging pod never
reached the post-login state (Section A.4) so we have no
in-pod evidence of whether headless branded MT5 auto-opens
charts the way the workstation does.

Committing `AUTO_LOGIN_PHASE5_ENABLED=0` as default before the
in-pod evidence is captured risks: if the pod does NOT auto-open
charts (Wine+Xvfb quirk), disabling Phase 5 would leave the pod
with no chart-attach mechanism at all, and `:5555` would never
bind even on a fully-working broker handshake.

#### Decision criteria from next run

From the next staging run, look at:

  1. The visible-windows list in `windows-poll-NN.txt` after
     Phase 3 submit succeeded.
  2. The `MQL5/Logs/` directory presence.
  3. Whether `:5555` bound WITHOUT Phase 5 ever running.

Commit decision table:

| Pod observation | Action |
|---|---|
| MT5 in pod auto-opens charts (Shape B title with chart suffix appears in the windows list) AND `MQL5/Logs/` populates AND `:5555` binds before Phase 5 dispatches any keystrokes | Commit `AUTO_LOGIN_PHASE5_ENABLED=0` as default. Phase 5 keystrokes are racing MT5's own chart-open. |
| MT5 in pod stays on Shape A title (no chart opens on its own) AND Phase 5 attempts 1/2/3 individually open a chart matching `<symbol>,<timeframe>` AND `:5555` then binds | Keep Phase 5 ON. Validates the original Phase 5 design. |
| MT5 in pod stays on Shape A title AND Phase 5 attempts all fail AND `:5555` never binds | Keep Phase 5 ON for now; the real bug is elsewhere (Wine+Xvfb quirk preventing keystroke dispatch). Investigate with framebuffer screenshots. |
| MT5 in pod gets past login but `MQL5/Logs/` populates and `:5555` binds within seconds AFTER Phase 5 disrupts the Toolbox panel (the boot-1 18:11 pattern) | Commit `AUTO_LOGIN_PHASE5_ENABLED=0` as default — Phase 5 was the disruptor, the auto-open WAS happening but was being interrupted. |

The Phase 5 code itself is RETAINED in `entrypoint.sh` regardless
of which default we commit; only the env-var default flips.
Operator can always override per-pod with
`kubectl -n etradie-system set env statefulset/<release> -c mt-node
AUTO_LOGIN_PHASE5_ENABLED=0|1` without an image rebuild.

---

## E. Lockstep invariants (DO NOT TOUCH without updating all locations)

| Setting | Value | Locations |
|---|---|---|
| `WATCHDOG_STARTUP_GRACE_SECONDS` | 300 | `helm/mt-node/values.yaml`, `helm/mt-node/templates/configmap-watchdog.yaml`, `provisioner.py::_upsert_watchdog_configmap` |
| `startupProbe.failure_threshold` | 120 | `helm/mt-node/values.yaml`, `provisioner.py::_upsert_statefulset` |
| `terminationGracePeriodSeconds` | 180 | `helm/mt-node/values.yaml`, `provisioner.py::_upsert_statefulset` |
| `lifecycle.preStop` | `sleep 30` | same |
| `AUTO_LOGIN_TOTAL_BUDGET_SECS` | 240 | `entrypoint.sh` |
| `AUTO_LOGIN_HARD_KILL_GRACE_SECS` | 30 | `entrypoint.sh` |
| `MT_NODE_READINESS_TIMEOUT_SECS` | 600 | engine ConfigMap |
| `ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS` | 1200 | engine ConfigMap |
| `ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS` | 1800 | engine ConfigMap |

---

## 1. Step-by-step commands (operator reference)

All the command blocks below are preserved from the previous
runbook version and remain accurate as operational primitives.
They are organised so the operator can run them in sequence
for a clean diagnostic cycle.

### 1.1 Operator routine (start every session here)

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

### 1.2 Cleanup — wipe failed state before re-provisioning

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

### 1.3 Race to the pod after provision

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

### 1.4 Verify env on the running engine pod

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

### 1.5 Verdict block — 6-step success check

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
  'fluxbox ready|hard-kill watchdog armed|welcome modal|appeared after|deliver|paste|type|phase3 stage|phase5|LISTEN.*exit success|never bound|exiting|residual post-restart|attempt [123]|all three attempts|Installed broker servers.dat|Bundle extracted'
```

### 1.6 Driver diagnostic (when verdict fails)

```bash
POD=$(kubectl -n etradie-system get pod \
  -l app.kubernetes.io/name=etradie-mt-node \
  -o jsonpath='{.items[0].metadata.name}')

# Full mt-node container log (the actual smoking gun)
kubectl -n etradie-system logs "$POD" -c mt-node 2>&1 \
  | grep -iE 'Vault credentials|Loaded.*Vault|Installed broker|servers.dat|Wine prefix|Xvfb|fluxbox|MetaTrader|auto_login|paste|type|deliver|phase[2-5]|exited with code|in-pod restart'

# broker-bundle initContainer log
kubectl -n etradie-system logs "$POD" -c broker-bundle 2>&1

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
```

Force typing strategy (operator override):

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

Disable Phase 5 (if D.5 is the diagnosis):

```bash
kubectl -n etradie-system set env statefulset/"$REL" \
  -c mt-node AUTO_LOGIN_PHASE5_ENABLED=0
```

### 1.7 Smoking-gun proof — second-boot is fast and silent

Only run this AFTER the first provision reaches 3/3 Ready.

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

---

## 2. Mounting the preserved PVC for offline inspection

When a pod is gone but the PVC survived (`whenDeleted: Retain`
invariant), inspect its contents via a one-shot debug pod.
This was used 2026-06-25 05:30 to discover the
63-cold-boot-banner pattern documented in Section A.4.

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

# Verify the broker bundle servers.dat was installed (binary file;
# strings | grep is NOT reliable — see Section A.5).
kubectl -n etradie-system exec mt-debug-reader -- sh -c '
  P="/mnt/wine/prefix/drive_c/Program Files/MetaTrader 5/config"
  ls -la "$P"
  echo
  if [ -f "$P/servers.dat" ]; then
    echo "=== servers.dat size + sha256 ==="
    wc -c "$P/servers.dat"
    sha256sum "$P/servers.dat"
  fi
'

# Cleanup.
kubectl -n etradie-system delete pod mt-debug-reader --ignore-not-found
```

---

## 3. References

- `docker/mt-node/entrypoint.sh` — driver state machine + helpers,
  broker-bundle install block, Vault credential parser, supervised
  MT restart loop.
- `docker/mt-node/watchdog.py` — health-probe sidecar, mirrors the
  same Vault credential parser semantics.
- `docker/mt-node/Dockerfile` — image build (xvfb, fluxbox, xdotool,
  xclip, generic MT5 portable zip, generic MT4 portable zip, EA,
  watchdog).
- `helm/mt-node/values.yaml` — chart defaults (lockstep with
  provisioner).
- `helm/mt-node/templates/configmap-watchdog.yaml` — watchdog
  runtime tunables.
- `helm/mt-node/templates/statefulset.yaml` — pod spec template,
  including the conditional `broker-bundle` initContainer and the
  `emptyDir` volume.
- `src/engine/ta/broker/mt5/hosted/provisioner.py` — engine-runtime
  provisioner (creates StatefulSets via K8s API, attaches the
  broker-bundle initContainer unconditionally for hosted releases).
- `src/engine/ta/broker/mt5/hosted/recovery.py` — background recovery
  sweep (rebuilds missing/unhealthy pods; currently re-creating the
  failed 89660d92 pod on a ~10-minute cadence).
- `src/engine/ta/broker/registry.py` — broker catalog loader
  (resolves `brand_id` + `entity_id` → bundle R2 URL + sha256).
- `infrastructure/broker-catalog/exness.json` /
  `infrastructure/broker-catalog/deriv.json` — Phase-1 broker bake
  registry entries.
- `MT5_Multi_Broker_Provisioning_Architecture.md` — authoritative
  design + bake procedure.
- `NOTE.md` — most recent staging diagnostic capture
  (2026-06-24 18:11).

Git history holds the full evolution. For the diagnostic narrative
that led to the current design, read `git log --grep='mt-node'` and
`git log --grep='hosted'` on `main`.
