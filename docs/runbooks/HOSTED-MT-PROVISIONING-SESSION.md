# Hosted-MT (Wine) Provisioning — In-Flight Session Runbook

**Status:** IN PROGRESS. Read this top-to-bottom before running anything.
This is the authoritative resume point for the hosted-MT provisioning
effort on the **staging** Contabo box (`vmi3362776`).

**Last updated:** 2026-06-21, session through **defect #16**. READ THE
DEFECT #16 BLOCK DIRECTLY BELOW FIRST — it supersedes #15b and every
older block (#14, #13, #10-12, #9, etc.), which are all FIXED.

> ============================================================
> SESSION UPDATE 2026-06-21 — DEFECT #16 (CURRENT, OPEN): BROKER
> LOGIN WALL. MT5 cannot log in because the broker's server is not
> in the tenant pod's servers.dat. READ THIS FIRST.
> ============================================================
>
> TL;DR: The tenant is FULLY PROVISIONED (pod, image, Wine, MT5
> terminal, libzmq+EA deps, LiveUpdate fixed, startup.ini with valid
> login/password/Server=Deriv-Demo, /config: honored). The ONLY thing
> broken is BROKER LOGIN. MT5 never logs in, so it never downloads
> symbols, so no chart can open, so the EA never attaches, so :5555
> never binds, so the startupProbe (tcp :5555, ~320s budget) SIGTERMs
> the container (exit 143) on a ~2.5min loop. Everything downstream of
> login is already built and will light up once login works.
>
> #15b HYPOTHESIS WAS DISPROVEN: '/config: not honored' was WRONG.
>   `ps -ef` proved the launch line is
>     terminal64.exe /config:/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/startup.ini
>   and startup.ini is correct + populated (Login=201415706,
>   Password set, Server=Deriv-Demo, [Charts] Template=expert,
>   [Experts] Enabled=true AllowDllImport=true). /config: IS read.
>
> THE PROVEN ROOT CAUSE (#16): the broker server is ABSENT from the
> pod's MT5 server directory.
>   - MT5 journal for the boot ends at:
>       build 5836 started / full recompilation finished: 0 file(s)
>     and then NOTHING — NO 'network'/'connect'/'login'/'authorized'
>     line at all (grep over the journal returns nothing). MT5 makes
>     ZERO network activity toward the broker.
>   - No lowercase bases/ dir (created only after a broker connects).
>     (There IS a capital Bases/ with Default symbols — case-sensitive
>     Linux; that is the baked default set, NOT the broker's symbols.)
>   - config/servers.dat exists (28544 bytes) but contains NO Deriv
>     entry (grep over both `strings` and `strings -el` => zero Deriv).
>   MT5 connects to the server NAME selected from servers.dat; if
>   Deriv-Demo is not in servers.dat, `Server=Deriv-Demo` resolves to
>   nothing and MT5 silently never attempts login.
>
> WHY (operator's authoritative description of real MT5 login — KEEP):
>   - To log into ANY broker you enter login + password and SELECT THE
>     SERVER FROM A DROPDOWN (brokers do not show a free-text server
>     field). That dropdown is populated from servers.dat.
>   - Mobile: a fresh MT5 shows 'Create Demo Account' (MT5 default
>     broker) OR 'Add existing account'. Add-existing opens a 'Find
>     Broker' search; typing e.g. 'Exness' lists Exness Technologies
>     Ltd, Exness (SC) Ltd, Exness B.V., Exness (KE) Limited, etc.
>     SELECTING one DOWNLOADS that broker's server list, THEN you get
>     login/password + the server dropdown; submitting opens the chart.
>   - PC: 'Login With Trading Account' -> login/password + server
>     dropdown -> connects + chart opens (sometimes you open the chart
>     manually). The PC dropdown is pre-populated because that PC's MT5
>     already had the broker added from prior use.
>   => CONCLUSION: the broker's server must be PRESENT in servers.dat
>     BEFORE login is possible. The operator's build machine had
>     Deriv-Demo (from prior manual use), so it works there; the
>     PORTABLE ZIP baked into the image did NOT carry it, so every
>     tenant pod's servers.dat lacks the broker the user picks. This
>     is broker-agnostic: it happens for EVERY broker.
>
>   LOCAL-TEST NOTE (operator, KEEP): when testing locally the operator
>   had to MANUALLY (a) open a chart at a specific timeframe, (b) attach
>   the EA, and (c) tick 'Allow DLL imports' (+ one other) before
>   submitting the attach. Our headless automation
>   ([Charts]/[Experts]/expert.tpl) must replicate that — but ONLY
>   AFTER login succeeds. None of it can work pre-login.
>
> ORDERED DEPENDENCY CHAIN (login is the prerequisite for everything):
>   broker server in servers.dat -> LOGIN -> symbols download ->
>   chart can open -> EA attaches (+Allow DLL) -> :5555 binds ->
>   watchdog Ready -> engine GET_ALL_SYMBOLS resolves real symbol ->
>   one roll (two-boot). The WALL is the very first arrow.
>   IMPORTANT: a chart CANNOT be attached before login (no symbols
>   exist pre-login). So MR !11 (attach EA on sentinel boot) and the
>   symbol two-boot are correct but DOWNSTREAM of login; they cannot
>   help until login works. Do NOT keep iterating on chart/EA attach.
>
> RULED OUT (do NOT re-chase): /config: ignored (false), LiveUpdate
>   (fixed), watchdog (innocent, in grace), libzmq/EA deps (baked),
>   terminal binary (baked), broker egress blocked (pod reaches the
>   internet: 1.1.1.1:443 OPEN, www.deriv.com:443 OPEN; and reaches
>   MetaQuotes: www.metaquotes.net + mql5.com -> 194.164.179.31), DNS
>   (works), chart-symbol format (irrelevant pre-login).
>
> THE OPEN QUESTION THAT PICKS THE FIX (confirm authoritatively, like
> the [LiveUpdate] key was, before coding):
>   On a FRESH MT5 (never used), does entering login + an unknown
>   server name auto-fetch/connect, or must the broker first be ADDED
>   (Find Broker -> select) so MT5 DOWNLOADS the server list into
>   servers.dat? Operator's description strongly indicates the latter:
>   you must select the broker first, which downloads its servers.
>
> CANDIDATE FIXES (broker-agnostic; the platform forces NO broker, so
> a hardcoded/single-broker bake is NOT acceptable):
>   A. Engine/entrypoint SEEDS the chosen broker's server into the pod
>      so servers.dat contains it before MT5 launches. The dashboard
>      connection already names the broker/server. Need: the source of
>      the broker server definition (the .srv/servers.dat entry) per
>      broker. This is the most robust multi-broker path.
>   B. Trigger MT5's headless broker/server auto-discovery from
>      MetaQuotes (the pod CAN reach MetaQuotes). Need: confirm build
>      5836 will fetch an unknown server via startup.ini headless, and
>      how to force it. If MT5 only auto-fetches via the GUI 'Find
>      Broker' flow, B is not viable headless and A is the fix.
>   C. Regenerate the portable MT5/MT4 zip from a prefix that has the
>      broker(s) added so servers.dat ships populated — but this bakes
>      specific brokers and does NOT scale to arbitrary user brokers;
>      only acceptable as a stopgap for a known broker set.
>
> >>> RESUME HERE (2026-06-21, defect #16) <<<
> Operator routine (two terminals; the tunnel drops often — always
> confirm `kubectl get nodes` is Ready before any exec):
>   T1 (leave open): ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173
>   T2: export KUBECONFIG=~/.kube/etradie-contabo.yaml; kubectl get nodes
>
> 1. Resolve the current pod (it ROLLS often; never hardcode):
>      POD=$(kubectl -n etradie-system get pods -o name | grep 'etradie-mt-' | head -1 | cut -d/ -f2); echo "$POD"
>    If empty, re-provision FROM THE DASHBOARD after cleaning:
>      kubectl -n etradie-system delete statefulset,svc,sa,configmap,pvc -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found
>      kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c "DELETE FROM broker_connections WHERE status IN ('failed','provisioning') RETURNING id;"
>
> 2. Re-confirm the wall (servers.dat lacks the broker; no login in
>    journal). NOTE: the pod has no `strings` binary — use grep -a:
>      kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c 'grep -aiE "deriv" "/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat" | head || echo "NO DERIV IN servers.dat"'
>      kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c 'J="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/logs"; f=$(ls -t "$J"/*.log|head -1); grep -iE "network|connect|login|authoriz|account|deriv" "$f" || echo "NO LOGIN/NETWORK LINE IN JOURNAL"'
>      kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c 'ls "/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/bases" 2>&1   # lowercase = post-login; absent = never logged in'
>
> 3. Decide A vs B by confirming how MT5 build 5836 obtains an unknown
>    broker server (operator knowledge + a test). Then implement the
>    broker-agnostic fix in the engine provisioner and/or
>    docker/mt-node/entrypoint.sh (seed the broker server / trigger
>    discovery). Cover BOTH MT5 and MT4.
>
> 4. After the fix: push to GitHub origin (CI source) -> CI rebuilds
>    mt-node + bumps staging pins -> confirm new MT_NODE_IMAGE SHA ->
>    clean failed tenant -> re-provision FROM THE DASHBOARD -> verify
>    the journal now shows a LOGIN/authorized line, lowercase bases/
>    appears, a chart opens, MQL5/Logs gets the EA
>    '=== eTradie ZeroMQ Bridge Started ===' / 'Endpoint: tcp://*:5555'
>    line, :5555 LISTEN, watchdog mt5_connected=1 + authenticated=1,
>    pod 3/3 Ready, then one roll for the symbol two-boot.
>
> GIT REMOTES: a local NOTE.md / CLOUDFLARE.md keep dirtying the tree —
>   `git stash` first. Then `git pull --rebase gitlab main`;
>   `git pull --rebase origin main`; `git push origin main`
>   (LOAD-BEARING — CI/ArgoCD build from GitHub FlameGreat-1/eTradie);
>   `git push --force-with-lease gitlab main`; `git stash pop`.
>   CI deploy-bump commit: `ci: pin staging image tags to <sha> [skip ci]`.
>
> SEPARATE NON-BLOCKING ITEM: GitHub Actions 'FATAL: Cloudflare AOP CA
>   fingerprint changed' — deployments/cloudflare/origin-pull/
>   aop-ca.sha256 was never bootstrapped (placeholder). Live CA
>   fingerprint = 9a1ac2b4be15f9f27eee20a734cba4e9898f61001b3bd7c84b69b56a3e25a2b9.
>   Does NOT gate the mt-node build. Resolve per docs/architecture/
>   edge-cloudflare-envoy.md (verify CA, bootstrap pin, write PEM to
>   Vault etradie/services/edge-ingress/<env>/cloudflare/aop_ca).
> ============================================================

> NOTE: the DEFECT #15 block below is partially SUPERSEDED by #16
> above. #15a (LiveUpdate) remains FIXED and accurate; the #15b
> 'startup.ini not honored' hypothesis in it is DISPROVEN — the real
> cause is #16 (broker not in servers.dat). Kept for audit trail.

> ============================================================
> SESSION UPDATE 2026-06-21 — DEFECT #15 (CURRENT, OPEN).
> READ THIS BLOCK FIRST. Everything below it is already FIXED.
> ============================================================
>
> WHAT IS NOW FIXED (do NOT re-debug these):
>   - #13 MT terminal binary baked into the image (portable MT5/MT4
>     zips, build-time terminal64.exe/terminal.exe assertions).
>   - #14 EA runtime deps baked: libzmq.dll (MT5 MQL5/Libraries +
>     MT4 MQL4/Libraries), Zmq include tree, JAson.mqh. Verified
>     present in the image with FATAL build-time assertions.
>   - #15a LiveUpdate self-restart loop: MT5/MT4 no longer phone
>     MetaQuotes and self-restart. Pinned via [LiveUpdate]
>     LastBuildDataPath in config/terminal.ini, BAKED into the image
>     template (Dockerfile, both program dirs) AND re-pinned at
>     runtime by entrypoint.sh. PROVEN: journal now shows NO
>     'LiveUpdate ... is available' line and '0 file(s) compiled'
>     (compiled state persists on the PVC; no more per-boot recompile
>     storm). This was MR !10 (merged).
>
> CURRENT IMAGE / PINS: mt-node + engine staging overlays pin git SHA
>   ab1b41d996ad8a65a94af3ab8de334f491839714 (CI commit
>   42a1136a 'ci: pin staging image tags to ab1b41d9... [skip ci]').
>   Engine runtime MT_NODE_IMAGE =
>   ghcr.io/flamegreat-1/etradie/mt-node:ab1b41d996ad8a65a94af3ab8de334f491839714
>   (verified live). This SHA carries MR !10 (LiveUpdate) AND MR !11
>   (EA-attach-on-sentinel-boot, no symbol pinned).
>
> THE OPEN BLOCKER (#15b — NOT yet fixed): the tenant pod still loops
>   on `MetaTrader exited with code 143` every ~2.5 min and never
>   reaches 3/3 Ready (sits 2/3). The kill source is PROVEN: the
>   mt-node container's startupProbe is `tcp :5555`
>   (delay=20s period=5s failure=60 => ~320s budget). :5555 never
>   binds, the probe exhausts, the kubelet SIGTERMs the container
>   (143), entrypoint relaunches, repeat. (`kubectl describe pod`:
>   'Startup probe failed: dial tcp <ip>:5555: connect: connection
>   refused'.) The watchdog is INNOCENT (it stays in its 180s startup
>   grace, logs 'NOT forcing restart', never Signalling).
>
> WHY :5555 NEVER BINDS — the DECISIVE evidence (MT5 journal for the
>   boot, /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/
>   logs/<date>.log):
>     MetaTrader 5 x64 build 5836 started
>     Compiler  full recompilation has been started
>     Compiler  full recompilation has been finished: 0 file(s) compiled
>     [ ... and then NOTHING. End of file. ]
>   There is NO login line, NO 'authorized on Deriv-Demo', NO network
>   connect, NO chart open, NO Expert load. AND on the running pod:
>     bases/    -> No such file or directory
>     profiles/ -> No such file or directory
>   bases/ and profiles/ are created by MT5 ONLY after it connects to a
>   broker / loads a profile. Their absence PROVES MT5 never logged in.
>   => MT5 starts + compiles, then does nothing. It is NOT consuming
>   startup.ini at all (no auto-login, no [Charts], no [Experts]).
>   This is why EVERY chart approach failed identically (chart vs no
>   chart, symbol vs no symbol): none of startup.ini is being honored.
>
> WHAT WAS RULED OUT (do NOT chase again):
>   - NOT LiveUpdate (fixed; gone from journal).
>   - NOT the watchdog (in grace; never sends SIGTERM here).
>   - NOT missing libzmq.dll (baked + verified).
>   - NOT a missing terminal binary (#13 fixed).
>   - NOT a chart-symbol problem. A bootstrap chart was tried two ways
>     and BOTH failed because login/startup.ini itself isn't honored:
>       * MR !11 attaches the EA on the sentinel boot via
>         [Charts] Template=expert with NO symbol pinned (broker-
>         agnostic; a hardcoded/placeholder symbol is REJECTED by
>         design because the platform supports many brokers with many
>         symbol formats). It did not help -> MT5 opened no chart
>         because it isn't reading startup.ini.
>   - A hardcoded bootstrap symbol is OFF THE TABLE: ~70% of users use
>     different brokers with different symbol formats; it would fail
>     provisioning for most users.
>
> ROOT-CAUSE HYPOTHESIS (NOT yet confirmed — do NOT guess the fix):
>   MT5 build 5836 under Wine is not honoring the startup config /
>   auto-login passed via the launch line
>     wine "$MT_EXE" "/config:$INI_FILE"
>   (entrypoint.sh writes $INI_FILE =
>    .../MetaTrader 5/config/startup.ini with [Common] Login/Password/
>    Server, [Charts], [Experts]). The terminal launches + compiles but
>    never acts on it. Candidate causes to verify against the ACTUAL
>    build before changing anything:
>     1. Wrong flag/format for this build (e.g. needs a bare positional
>        arg `terminal64.exe <file>.ini`, or `/portable`, vs `/config:`).
>     2. startup.ini must live at a different path for this build.
>     3. Auto-login needs creds in a different file (accounts/common.ini)
>        not [Common] in startup.ini.
>     4. Some other first-run gate.
>   The clean precedent: the [LiveUpdate] key was confirmed from the
>   REAL install before coding. Do the SAME here — confirm the correct
>   MT5 startup-config / auto-login invocation from the real install,
>   THEN fix entrypoint.sh. Do NOT iterate blindly.
>
> >>> RESUME HERE (2026-06-21, defect #15b) <<<
> Operator routine: two terminals.
>   Terminal 1 (leave open):  ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173
>   Terminal 2:               export KUBECONFIG=~/.kube/etradie-contabo.yaml
>                             kubectl get nodes   # vmi3362776 Ready -> tunnel live
>
> 1. Confirm the engine still runs the ab1b41d9 SHA (the fix image):
>      kubectl -n etradie-system exec deploy/etradie-engine -c engine -- printenv MT_NODE_IMAGE
>      # expect ...mt-node:ab1b41d996ad8a65a94af3ab8de334f491839714
>
> 2. Resolve the current tenant pod (it ROLLS often; never hardcode it):
>      POD=$(kubectl -n etradie-system get pods -o name | grep 'etradie-mt-' | head -1 | cut -d/ -f2); echo "$POD"
>      kubectl -n etradie-system get pods | grep etradie-mt-
>    If empty, re-provision FROM THE DASHBOARD (connection_type=hosted),
>    after cleaning the prior failed tenant:
>      kubectl -n etradie-system delete statefulset,svc,sa,configmap,pvc -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found
>      kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c "DELETE FROM broker_connections WHERE status IN ('failed','provisioning') RETURNING id;"
>
> 3. GATHER THE 3 FACTS that decide the fix (this is exactly where the
>    session stopped — these had not been captured yet because the pod
>    kept rolling / the tunnel dropped):
>      # a) the startup.ini we wrote (login/server populated? path right?)
>      kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c 'cat "/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/startup.ini"'
>      # b) the LITERAL launch args MT5 is running with (is /config: even passed?)
>      kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c 'ps -ef | grep -i terminal64 | grep -v grep'
>      # c) the MT5 journal for THIS boot (no login line == startup.ini not honored)
>      kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c 'J="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/logs"; f=$(ls -t "$J"/*.log | head -1); echo "=== $f ==="; cat "$f"'
>
> 4. CONFIRM the correct MT5 (build 5836) startup-config + auto-login
>    invocation from the real install (flag/format, file path, creds
>    location). THEN fix the launch line / config in
>    docker/mt-node/entrypoint.sh (the `wine "$MT_EXE" "/config:$INI_FILE"`
>    near the 'Supervised MT restart loop' section). Cover BOTH MT5 and
>    MT4 (their template paths differ: MT5 Profiles/Templates/expert.tpl,
>    MT4 templates/expert.tpl; MT4 .tpl syntax differs from MT5 and is
>    UNPROVEN — verify against an MT4 tenant before claiming MT4 works).
>
> 5. After any entrypoint fix: push to GitHub origin (CI source), let CI
>    rebuild mt-node + bump the staging pins, confirm the new SHA in
>    MT_NODE_IMAGE, clean the failed tenant, re-provision FROM THE
>    DASHBOARD, then verify:
>      POD=$(kubectl -n etradie-system get pods -o name | grep 'etradie-mt-' | head -1 | cut -d/ -f2)
>      P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"
>      kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c "cat \"$P/logs/\"*.log"          # expect a LOGIN line now
>      kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c "ls \"$P/MQL5/Logs\" 2>&1"        # exists => EA OnInit ran
>      kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c 'cat /proc/net/tcp | grep -i 15B3 && echo ":5555 LISTEN" || echo ":5555 not bound"'
>      kubectl -n etradie-system get pod "$POD" -o wide                                            # 3/3 Ready
>    SUCCESS = journal shows broker login/authorized, MQL5/Logs has the
>    EA '=== eTradie ZeroMQ Bridge Started ===' / 'Endpoint: tcp://*:5555'
>    line, :5555 LISTEN, watchdog mt5_connected=1 + authenticated=1, pod
>    3/3 Ready, then exactly ONE roll as the engine patches the resolved
>    symbol (documented two-boot).
>
> GIT REMOTES: merges land on the GitLab mirror (intelli1344225/exoper);
>   `git stash` (a local NOTE.md keeps dirtying the tree) then
>   `git pull --rebase gitlab main` then `git pull --rebase origin main`
>   then `git push origin main` (LOAD-BEARING; CI/ArgoCD build from
>   GitHub FlameGreat-1/eTradie) then `git push --force-with-lease
>   gitlab main`. CI runs on GitHub Actions; the deploy-bump commit
>   `ci: pin staging image tags to <sha> [skip ci]` pins the new image.
>
> SEPARATE, NON-BLOCKING ITEM (do not conflate with #15): a GitHub
>   Actions job 'FATAL: Cloudflare AOP CA fingerprint changed' fails
>   because deployments/cloudflare/origin-pull/aop-ca.sha256 was never
>   bootstrapped (placeholder, no fingerprint). Live Cloudflare AOP CA
>   fingerprint is
>   9a1ac2b4be15f9f27eee20a734cba4e9898f61001b3bd7c84b69b56a3e25a2b9.
>   This does NOT gate the mt-node image build (mt-node CI went green
>   and pinned ab1b41d9). Resolve per docs/architecture/
>   edge-cloudflare-envoy.md 'Rotation > Cloudflare AOP CA' (verify the
>   CA is genuinely Cloudflare's, then bootstrap the pin + write the PEM
>   to Vault etradie/services/edge-ingress/<env>/cloudflare/aop_ca).
>   Owner-gated; do NOT auto-bump.

**Older blocks below are HISTORICAL (all FIXED). Kept for audit only.**

**Last updated (historical):** 2026-06-21, session through defect #14 (EA runtime
dependency libzmq.dll missing from the portable MT image). READ THE
DEFECT #14 BLOCK BELOW FIRST.

> SESSION UPDATE 2026-06-21 (defect #14 - EA cannot bind :5555 because
> its libzmq.dll runtime dependency is NOT in the image). READ THIS
> BLOCK FIRST; it supersedes the defect #13 block below.
>
> WHERE WE ARE: defect #13 is FIXED - the portable MT5/MT4 terminal is
> now baked into the image (mt-node SHA d8a5b166 then d9425a4a;
> engine MT_NODE_IMAGE pins it; terminal64.exe runs, no more
> 'ShellExecuteEx failed: File not found'). But the tenant pod still
> never reaches 3/3 Ready. It sits at 2/3, mt5_connected=0,
> authenticated=0, and the watchdog HEALTH poll on tcp://127.0.0.1:5555
> fails forever ('Resource temporarily unavailable').
>
> WHAT WAS WRONG (defect #14 - PROVEN at the filesystem level, not a
> theory): the ZeroMQ EA is a DLL-import EA. It calls into
> `libzmq.dll` in OnInit() to create its ZMQ REP socket. That DLL,
> and the EA's MQL includes, are ABSENT from the baked portable
> prefix. Verified live on pod etradie-mt-cf6e2e6b-b80-0:
>     MQL5/Experts/ZeroMQ_EA.ex5     -> PRESENT (129 KB)
>     libzmq.dll (anywhere)          -> NOT PRESENT
>     MQL5/Include/Zmq/              -> MISSING
>     MQL5/Include/JAson.mqh         -> MISSING
> With no libzmq.dll the EA's OnInit DLL import fails, so the EA never
> initialises, never binds :5555, and never creates MQL5/Logs/
> (confirmed: `no MQL5/Logs - no expert ever ran`, `nothing on :5555`).
> NO chart/entrypoint/watchdog change can fix a missing runtime library.
>
> FIRST #14 ATTEMPT - WRONG, ALREADY REVERTED: I theorised the EA was
> simply not ATTACHED (sentinel boot wrote no [Charts] section) and
> committed an entrypoint change (attach EA on a bootstrap symbol +
> LiveUpdate=0) plus a watchdog startup-grace. A LIVE TEST disproved
> it: writing expert.tpl + [Charts] into the running prefix STILL gave
> no MQL5/Logs and nothing on :5555, because the real blocker is the
> missing libzmq.dll, not attachment. Those commits were reverted (see
> 'revert(mt-node): undo defect #14 ...' on main). Entrypoint +
> watchdog are back to their pre-#14 state. Do NOT re-apply that
> approach.
>
> SECONDARY OBSERVATION (real but not the blocker): MT5 build 5836
> runs LiveUpdate + a full 453-file recompilation on EVERY cold boot
> (journal: 'LiveUpdate new version build 5833', 'mt5onnx64 downloaded',
> 'full recompilation has been started/finished'). Non-deterministic +
> slow (~100s to usable) + a runtime MetaQuotes pull. Worth disabling
> (LiveUpdate=0) as a SEPARATE hardening once the libzmq blocker is
> fixed - but it is NOT why :5555 is down.
>
> THE CORRECT FIX (NOT yet implemented): bake the EA's runtime
> dependencies into the portable MT image, same class as defect #13
> (image was missing what the EA needs). Specifically the mt-node image
> must contain, inside the Wine prefix the entrypoint seeds:
>   - libzmq.dll on the EA's DLL search path. For MT5 the terminal
>     loads DLLs from `MQL5/Libraries/` (and the terminal dir); the
>     64-bit libzmq.dll MUST match MT5 x64 (terminal64.exe). MT4 uses
>     the 32-bit libzmq.dll under `MQL4/Libraries/`.
>   - the Zmq MQL include tree (MQL5/Include/Zmq/, MQL4/Include/Zmq/)
>     and JAson.mqh - REQUIRED to RE-COMPILE the EA from source, but if
>     we ship a prebuilt .ex5/.ex4 the includes are only needed if MT
>     recompiles; the .dll is needed at RUNTIME regardless.
>   - the prebuilt ZeroMQ_EA.ex5/.ex4 MUST be compiled against a build
>     compatible with the baked terminal (build 5836). An .ex5 from an
>     incompatible build can silently fail to load. SOURCE lives at
>     src/engine/ta/broker/mt5/zmq/ZeroMQ_EA.mq5 (+ .mq4); the committed
>     docker/mt-node/ea/ZeroMQ_EA.ex5 is the prebuilt artifact.
>
> OPEN QUESTIONS TO RESOLVE BEFORE COMMITTING THE FIX (do NOT guess):
>   1. Where does this MT5 build search for import DLLs under Wine -
>      MQL5/Libraries/ vs the terminal dir? (Determines where to place
>      libzmq.dll in the prefix / image.)
>   2. Is the committed ZeroMQ_EA.ex5 compiled for a build compatible
>      with 5836? If not, it must be recompiled (MetaEditor) against the
>      baked terminal, or the image must compile it at build time.
>   3. Which libzmq.dll build/ABI does the EA's #import expect (name +
>      bitness)? mql-zmq (github.com/dingmaotu/mql-zmq) ships a
>      libzmq.dll; the EA header references it.
>   4. Does shipping the .ex5 avoid needing the Zmq/JAson includes at
>      runtime, or does MT recompile on boot (the observed per-boot
>      'full recompilation') and thus NEED the includes present too?
>
> >>> RESUME HERE (2026-06-21, defect #14) <<<
> 1. NOTE: a manual probe override is live on the StatefulSet:
>      kubectl -n etradie-system set env statefulset/etradie-mt-cf6e2e6b-b80 -c watchdog WATCHDOG_MAX_FAILURES=9999
>    Drop it (or just delete the connection; a re-provision builds a
>    fresh StatefulSet from the chart):
>      kubectl -n etradie-system set env statefulset/etradie-mt-cf6e2e6b-b80 -c watchdog WATCHDOG_MAX_FAILURES-
> 2. Answer the four OPEN QUESTIONS above against mql-zmq + the EA
>    source + the live MT5 build. Determine the exact libzmq.dll
>    (name+bitness) and its required prefix location for MT5 (x64) AND
>    MT4 (x86).
> 3. Implement the CORRECT fix in docker/mt-node/Dockerfile (and/or the
>    portable-zip artifacts): place libzmq.dll on the EA DLL search path
>    in the baked Wine template for BOTH MT5 and MT4, add the Zmq/JAson
>    includes if recompile-on-boot needs them, and ensure the prebuilt
>    .ex5/.ex4 is build-compatible (recompile if not). Add a build-time
>    assertion that libzmq.dll is present (mirror the defect #13
>    terminal64.exe assertion) so a future image can never ship without
>    it.
> 4. Rebuild via CI (portable-zip flow, see defect #13 block), confirm
>    the new mt-node SHA pins (engine printenv MT_NODE_IMAGE), clean the
>    failed tenant + rows, re-provision FROM THE DASHBOARD, then verify
>    on the tenant pod:
>      kubectl -n etradie-system exec <pod> -c mt-node -- sh -c 'find /home/mt/.wine/prefix -iname libzmq*.dll'   # present
>      kubectl -n etradie-system exec <pod> -c mt-node -- sh -c 'ls "/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs"'   # EA ran
>      kubectl -n etradie-system exec <pod> -c mt-node -- sh -c 'ss -ltn | grep 5555'   # EA bound the socket
>    SUCCESS = MQL5/Logs/ exists with an EA OnInit line, :5555 LISTEN,
>    watchdog mt5_connected=1 + authenticated=1, pod 3/3 Ready.
> 5. THEN (separate hardening, not the blocker): disable MT5 LiveUpdate
>    + per-boot recompile for deterministic fast boots.
>
> CLEAN-BASE NOTE: entrypoint.sh + watchdog.py + helm/mt-node
> configmap-watchdog.yaml + values.yaml were reverted to their pre-#14
> state in this session. Start the correct fix from that clean base.

> SESSION UPDATE 2026-06-21 (defect #13 - MT terminal binary missing
> from the mt-node image). READ THIS BLOCK FIRST; it supersedes every
> older resume pointer below.
>
> WHAT WAS WRONG:
> - After defects #10/#11/#12 cleared (no more 'Read-only file system'
>   and no more 'is not owned by you'), the tenant pod's mt-node
>   container Wine-launched and immediately looped on
>   `ShellExecuteEx failed: File not found` / `Application could not be
>   started`, exhausted its 6x in-pod restart budget, and CrashLooped.
> - Filesystem-confirmed on the running pod: NO `terminal64.exe`
>   anywhere in `/opt/wine-template` or `/home/mt/.wine/prefix`, and NO
>   `MetaTrader 5` dir at all in the baked template (only Wine's
>   built-in stubs: iexplore/wmplayer/wordpad). The MT5/MT4 install
>   simply never happened during the image build.
> - ROOT CAUSE: `docker/mt-node/Dockerfile` ran
>   `wine /tmp/mtXsetup.exe /auto 2>/dev/null || true` at build time
>   with NO X display and ALL errors swallowed. MetaQuotes' mtXsetup.exe
>   is an interactive GUI web-installer; even with /auto it needs a
>   display and does not reliably complete unattended. With no display
>   and `|| true` it silently no-op'd, the build 'succeeded', and the
>   image shipped with no terminal. (The prior 'working' builds were an
>   illusion: the install was ALWAYS a no-op, hidden by `|| true`.)
>
> FIRST FIX ATTEMPT (insufficient, do NOT rely on it):
> - Ran the installer under `xvfb-run`, dropped `|| true`, added a hard
>   `terminal64.exe`/`terminal.exe` assertion. Result: the build no
>   longer silently ships broken, but the GUI web-installer HANGS
>   indefinitely under xvfb (waits on a prompt nobody clicks). CI stuck
>   30min+ on the MT5 install step. Confirms: running the installer in
>   `docker build` is the wrong design, period.
>
> PERMANENT FIX (in progress): do NOT run the installer in the build.
> Bake PRE-INSTALLED PORTABLE MT5 + MT4 directories into the image.
> - Generated once on a workstation with Wine 9.0 + Xvfb:
>     export WINEPREFIX=~/mt-portable/wine
>     wine wineboot --init; wineserver --wait
>     xvfb-run -a -s "-screen 0 1024x768x24" wine mt5setup.exe /auto; wineserver --wait
>     xvfb-run -a -s "-screen 0 1024x768x24" wine mt4setup.exe /auto; wineserver --wait
>   (the installer's post-install UI page-faults / 'X connection broken'
>   are COSMETIC; the files land before that.) Both binaries verified:
>     .../drive_c/Program Files/MetaTrader 5/terminal64.exe
>     .../drive_c/Program Files (x86)/MetaTrader 4/terminal.exe
> - Zipped from inside the respective Program Files dir so each zip has
>   a top-level `MetaTrader 5` / `MetaTrader 4` folder:
>     cd "$WINEPREFIX/drive_c/Program Files"       && zip -rq mt5-portable.zip "MetaTrader 5"
>     cd "$WINEPREFIX/drive_c/Program Files (x86)" && zip -rq mt4-portable.zip "MetaTrader 4"
> - Artifact sha256 (these are the NEW values for the *_INSTALLER_SHA256
>   secrets - the pins now fingerprint the PORTABLE ZIPS, not the .exe):
>     mt5-portable.zip  166M  32675431e68ab8715ee6e0b45d77d58b206fbbc8f610ad54d71b32c7f821ece3
>     mt4-portable.zip   41M  b2dcd86fcc658a41d677f0fee5d3b725ab8e6aa539929d5199a7d854210b7ff9
>
> HOSTING: both zips uploaded to a Cloudflare R2 public bucket
> (`etradie-installers`, r2.dev public subdomain). Any anonymous HTTPS
> host works; the URL just must NOT contain `download.mql5.com` (the CI
> production-build guard blocks that substring).
>
> GITHUB ACTIONS SECRETS after this change (repo FlameGreat-1/eTradie,
> Settings -> Secrets and variables -> Actions). Already present from
> deploy time: WINEHQ_VERSION, EA_EX5_SHA256, EA_EX4_SHA256,
> ETRADIE_ALLOW_PUBLIC_INSTALLER_CDN. REWIRED for defect #13:
>   MT5_INSTALLER_URL    = https://pub-<hash>.r2.dev/mt5-portable.zip
>   MT4_INSTALLER_URL    = https://pub-<hash>.r2.dev/mt4-portable.zip
>   MT5_INSTALLER_SHA256 = 32675431e68ab8715ee6e0b45d77d58b206fbbc8f610ad54d71b32c7f821ece3
>   MT4_INSTALLER_SHA256 = b2dcd86fcc658a41d677f0fee5d3b725ab8e6aa539929d5199a7d854210b7ff9
>
> DOCKERFILE CHANGE (docker/mt-node/Dockerfile): both MT install steps
> are being rewritten to: add `unzip` to apt; download the portable zip
> from MTx_INSTALLER_URL; verify sha256 against MTx_INSTALLER_SHA256;
> `unzip` into `$WINE_TEMPLATE/drive_c/Program Files/` (MT5) and
> `$WINE_TEMPLATE/drive_c/Program Files (x86)/` (MT4); keep the hard
> terminal64.exe / terminal.exe assertions; NO `wine ... /auto` run.
> Deterministic, reproducible, no hang.
>
> >>> RESUME HERE (2026-06-21) <<<
> 1. Confirm the two zips are live + byte-correct:
>      curl -fsI "$MT5_INSTALLER_URL" | head -1   # HTTP/2 200
>      curl -fsSL "$MT5_INSTALLER_URL" | sha256sum # == 32675431...ece3
>      curl -fsI "$MT4_INSTALLER_URL" | head -1   # HTTP/2 200
>      curl -fsSL "$MT4_INSTALLER_URL" | sha256sum # == b2dcd86f...7ff9
> 2. Confirm the four GitHub secrets above are set, then push the
>    Dockerfile rewrite to the GitLab mirror (propagates GitLab -> GitHub
>    -> CI). Watch the GitHub Actions `build (mt-node)` job: it must now
>    download+unzip (seconds), print `INFO: MT5 terminal64.exe verified`
>    and `INFO: MT4 terminal.exe verified`, and go GREEN with NO hang.
> 3. After CI green + deploy-bump, the new mt-node image SHA is pinned
>    into helm/mt-node/values-staging.yaml + helm/engine/values-staging
>    .yaml::config.mtNode.image. Confirm the engine picked it up:
>      export KUBECONFIG=~/.kube/etradie-contabo.yaml
>      kubectl -n etradie-system exec deploy/etradie-engine -c engine -- printenv MT_NODE_IMAGE
>    (must be the new git SHA, NOT 34a2dabd / 8deaafc2). NOTE: a stale
>    inline `MT_NODE_IMAGE` env on the Deployment can override envFrom -
>    if so, `kubectl -n etradie-system set env deploy/etradie-engine
>    MT_NODE_IMAGE-` to drop it and let the ConfigMap value win.
> 4. Clean the prior failed tenant + rows, re-provision FROM THE
>    DASHBOARD (connection_type=hosted), gate on the pod image, then
>    watch the decisive log:
>      kubectl -n etradie-system delete statefulset,svc,sa,configmap,pvc -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found
>      kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c "DELETE FROM broker_connections WHERE status IN ('failed','provisioning') RETURNING id;"
>      # submit in dashboard, then:
>      CONN=$(kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -t -A -c "SELECT left(id::text,12) FROM broker_connections ORDER BY created_at DESC LIMIT 1;")
>      kubectl -n etradie-system get pod etradie-mt-${CONN}-0 -o jsonpath='{.spec.containers[?(@.name=="mt-node")].image}{"\n"}'
>      kubectl -n etradie-system logs etradie-mt-${CONN}-0 -c mt-node --tail=40 -f
>    SUCCESS = `Launching terminal64.exe` is NOT followed by
>    `ShellExecuteEx failed: File not found`; MT5 actually starts.
> 5. Anticipated NEXT walls after Wine launches (not hit yet): MT5
>    broker login on Deriv-Demo, EA ZMQ bind on :5555, then the symbol
>    two-boot (one expected roll). Watchdog /healthz needs
>    mt5_connected=true AND authenticated=true to go Ready.
>
> CAUTION ON THE PORTABLE ARTIFACT: the zips carry a full MT5/MT4
> install (166M/41M). They are broker-agnostic (Deriv-Demo login is
> supplied at runtime via startup.ini). If a broker requires its own
> custom MT build, the portable terminal still connects to standard
> MT5/MT4 servers; only re-generate the zip if you intentionally change
> the MT base version (then recompute + update the *_INSTALLER_SHA256
> secrets).


> SESSION UPDATE 2026-06-20 (defects #10/#11/#12 + mt-node image
> delivery GitOps). Read this block FIRST; it supersedes older resume
> pointers below. Current GitHub `main` image SHA tag after this work:
> `8deaafc2d54e13ce614498573cd668dc13cd257d` (the mt-node image that
> carries ALL fixes below). The engine ConfigMap
> `etradie-engine-config::MT_NODE_IMAGE` already renders this SHA and
> the engine has rolled to it.
>
> WHAT WAS WRONG (cascade continued from #9):
> - Defect #10 - mt-node never re-pulled (GitOps gap). mt-node was the
>   ONLY CI-built/staging service NOT wired into the `deploy-bump`
>   immutable-SHA GitOps. Its image stayed pinned to mutable `0.1.0`
>   (helm/mt-node/values-image.yaml + engine config.mtNode.image). With
>   pullPolicy IfNotPresent and 0.1.0 already cached on the node, a
>   rebuilt image republished as 0.1.0 was NEVER re-pulled; ArgoCD saw
>   no diff. CI green did NOT mean fix-on-cluster.
> - Defect #11 - Wine prefix reset hit read-only FS. entrypoint.sh ran
>   `rm -rf "$WINE_PREFIX"` (the PVC mount point) on the fresh-PVC
>   "appears corrupted" path; under readOnlyRootFilesystem=true that
>   failed 'Read-only file system', exit 1, CrashLoopBackOff.
> - Defect #12 - Wine prefix ownership. After #11, Wine aborted:
>   `wine: '/home/mt/.wine' is not owned by you`. The PVC mount root is
>   owned by uid 0 (fsGroup sets group only); Wine requires WINEPREFIX
>   owned by the running euid (1000). Container is non-root under the
>   etradie-system RESTRICTED PodSecurity Standard, so NO root chown /
>   root init-container is possible.
>
> FIXES (all merged to `main`; flow GitLab mirror -> GitHub -> CI/ArgoCD):
> - #10 -> MR !2: wired mt-node into `deploy-bump` (staging-only,
>   lockstep). Added helm/mt-node/values-staging.yaml::image.tag and
>   helm/engine/values-staging.yaml::config.mtNode.image; CI rewrites
>   BOTH to the immutable git SHA each push. Production untouched (still
>   rolls on values-image.yaml RELEASE_TAG - the intended human-gated
>   invariant; this is the flagged prod cutover follow-up).
> - #11 -> MR !1 (commit 2601dbb2): reset the prefix CONTENTS, not the
>   mount point.
> - #12 -> MR !3 (commit 2225afbf): point WINEPREFIX at an OWNED
>   subdirectory /home/mt/.wine/prefix (created by uid 1000) instead of
>   the root-owned PVC mount root. Pure entrypoint.sh change; both MT4
>   and MT5 branches derive MT_DIR from $WINE_PREFIX so both are fixed;
>   no securityContext/PSS change. Permanent + environment-agnostic
>   (applies to staging AND production, chart + engine-runtime paths).
> - GitOps follow-ups MR !4 + MR !5: !4 consolidated a duplicate
>   config.mtNode block in helm/engine/values-staging.yaml (MR !2 had
>   created a second mtNode mapping). !5 made the CI `deploy-bump`
>   engine write idempotent/race-proof via `del(.config.mtNode.image)`
>   then set, so a checkout-timing race can never re-create a duplicate
>   and any existing GitHub duplicate self-heals on the next bump.
>
> >>> RESUME HERE (2026-06-20) <<<
> 1. ArgoCD is OutOfSync on engine-staging and mt-node-staging
>    (Healthy). selfHeal is on; confirm both flip to Synced. If they
>    stick OutOfSync, the engine-values duplicate-key (pre-!5 bump) can
>    keep ArgoCD detecting drift - the next deploy-bump run (post-!5)
>    collapses it; or force `argocd app sync engine-staging
>    mt-node-staging`. Verify after: both Synced + MT_NODE_IMAGE =
>    8deaafc2... (or a newer SHA if more pushes landed).
> 2. Confirm the GitOps lockstep is clean (after the next bump):
>      git show origin/main:helm/engine/values-staging.yaml | grep -c 'mt-node:'   # expect 1
>      git show origin/main:helm/mt-node/values-staging.yaml | grep -A1 '^image:'  # tag == engine SHA
> 3. Re-provision the tenant FROM THE DASHBOARD (connection_type=hosted;
>    NOT via kubectl). Before submitting, clean the prior failed tenant
>    (last under test: etradie-mt-f7cafe99-07c):
>      kubectl -n etradie-system delete statefulset etradie-mt-f7cafe99-07c --ignore-not-found
>      kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c "DELETE FROM broker_connections WHERE status IN ('failed','provisioning') RETURNING id;"
> 4. Watch the decisive log (expect NO 'Read-only file system' and NO
>    'is not owned by you'; then Xvfb ready -> Launching terminal64.exe
>    -> pod climbs to 3/3 Ready, one roll for the symbol two-boot):
>      CONN=$(kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -t -A -c "SELECT left(id::text,12) FROM broker_connections ORDER BY created_at DESC LIMIT 1;")
>      kubectl -n etradie-system get pod etradie-mt-${CONN}-0 -o jsonpath='{.spec.containers[?(@.name=="mt-node")].image}{"\n"}'   # must be 8deaafc2 (or newer) SHA
>      kubectl -n etradie-system logs etradie-mt-${CONN}-0 -c mt-node --tail=40 -f
> 5. Anticipated NEXT walls after Wine launches (not hit this session):
>    MT5 broker login on Deriv-Demo, EA ZMQ bind on :5555, then the
>    symbol two-boot (one expected roll). Watchdog /healthz needs
>    mt5_connected=true AND authenticated=true to go Ready.
>
> GIT REMOTES DANCE: merges land on the GitLab mirror;
> `git pull --rebase gitlab main` then `git pull --rebase origin main`
> then `git push origin main` propagates to GitHub (which carries the
> etradie-ci[bot] [skip ci] deploy-bump commit your local lacks). CI
> runs on GitHub Actions; the GitLab MR page shows no real pipeline.

> SESSION UPDATE (defect #9 + msgpack CVE): the engine image carrying
> the defect 7+8 fixes rolled (`0b5f2b5e…`) but the new engine pod
> crash-looped. Root cause was NOT a 7+8 regression (the rendered
> tenant StatefulSet spec is correct). It is a **new defect #9**: the
> eager hosted-recovery startup sweep was awaited synchronously BEFORE
> the lifespan `yield`. `run_once_at_startup() -> _sweep -> _reprovision
> -> HostedProvisioner.provision_account() -> _wait_ready` blocks up to
> `_READINESS_TIMEOUT_SECS` (300s) PER tenant on StatefulSet-Ready + ZMQ
> PING. During that window uvicorn never binds `:8000`, the engine
> `/health` startup probe gets connection-refused, the kubelet kills the
> pod, and the engine crash-loops -- which never gives the tenant Wine
> pod a stable parent to finish booting.
>
> FIX (on `main` via MR !157): in `src/engine/main.py` keep
> `start_background_loop()` + the construction/ConfigurationError guard
> on the boot path (both instant), but run the eager bypass-threshold
> sweep as a fire-and-forget background task via
> `container.background_tasks.schedule_once("lifespan:hosted_recovery_startup_sweep", ..., cooldown_s=3600, timeout_s=1800)`,
> mirroring the macro-cache warmup and the provisioner's own
> `_catalog_sync_runner` wave. `timeout_s=1800` comfortably exceeds the
> 300s per-tenant gate under the default `max_concurrent_reprovisions=4`.
> The engine now reaches `yield` and serves `/health` immediately, then
> converges hosted tenants in the background. The "full system restart
> recovery" guarantee is preserved (the eager sweep still runs, just not
> on the blocking boot path).
>
> ALSO: `requirements/base.txt` bumped `msgpack 1.1.0 -> 1.2.1`
> (GHSA-6v7p-g79w-8964) to clear the `pip-audit --strict` job
> (committed directly to `main`).

---

## TL;DR — where we are right now

We are provisioning the **first hosted-MT (Wine) tenant** via the dashboard
(`connection_type=hosted`). The engine's `HostedProvisioner` runs the
provisioning at runtime (not ArgoCD). Each dashboard submit creates a
`broker_connections` row; the engine then writes per-tenant creds to Vault
and creates a per-tenant StatefulSet + ServiceAccount + Services + watchdog
ConfigMap + PVC. The platform is healthy throughout — only hosted-MT
provisioning is affected. No outage.

Provisioning failed in a **cascade of 8 distinct defects**, each revealed
after the previous was fixed. **All 8 are now fixed in code on `main`.**
The infra fixes (egress, RBAC) are live and verified. The 4 most recent
fixes are **engine-image (Python) changes** that need CI to build + roll a
new engine image before the runtime `HostedProvisioner` produces correct
tenant pods.

### RESUME POINTER (read this first)

- **Last barrier:** tenant pod's Vault Agent login was failing
  `403 invalid audience` (defect #8). Fix: project an `aud=vault` SA
  token onto the tenant pod and have the agent read it. Two follow-on
  errors were fixed in turn:
  (a) agent pointed at token-path but volume not mounted on the agent
  container -> `no such file or directory`; fixed with
  `agent-copy-volume-mounts: "mt-node"`.
- **What we are waiting on RIGHT NOW:** CI to build a new engine image
  past `ghcr.io/flamegreat-1/etradie/engine:2e4aba9f...` and bump
  `helm/engine/values-staging.yaml::image.tag`, then ArgoCD rolls it.
  The provisioner fix only takes effect once that new engine pod runs.
- **Then:** delete the stuck connection from the dashboard, re-create,
  and verify the tenant pod's `vault-agent-init` logs
  `authentication successful` and the pod reaches `3/3 Ready`.
  See "RESUME HERE" below for exact commands.

### Fixes committed to `main` (GitLab mirror -> GitHub `origin` -> ArgoCD/CI)

| # | Defect | Layer | Needs engine image rebuild? | Status |
|---|---|---|---|---|
| 1 | engine egress to Vault `:8200` + `http` scheme | Helm values | No | DONE, live, verified |
| 2+3 | idempotent alembic migrate + read-path token decrypt for `hosted` (`_load_active_broker_connection` + `test` endpoint) | Engine image | **Yes** | DONE, rolled |
| 4 | engine projects `aud=vault` SA token (engine->Vault) | Helm pod-spec | No | DONE, live, verified |
| 5 | engine egress to K8s API (post-DNAT apiserver `:6443`, `0.0.0.0/0:6443`) | Helm values | No | DONE, live, verified (`6443 OPEN`) |
| 6 | RBAC: engine Role needs `configmaps` `create/update/patch/delete` for the per-tenant watchdog ConfigMap | Helm role | No | DONE, live, verified (`Forbidden` cleared) |
| 7 | tenant pod Vault Agent `aud=vault`: project token + mount + `auth-config-token-path` + `auth-config-audience` | Engine image (provisioner.py) + chart | **Yes** | DONE on main; **awaiting image roll** |
| 8 | tenant pod Vault Agent could not read token: `agent-copy-volume-mounts: "mt-node"` so the injector mounts the projected token onto the agent containers | Engine image (provisioner.py) + chart | **Yes** | DONE on main; **awaiting image roll (current step)** |

> NOTE: items 7+8 are the SAME wall (tenant Vault login) fixed in three
> increments: project aud=vault token -> point agent at it -> copy the
> mount onto the agent. All committed; they ride the next engine image.

### The failure cascade (each was a real, separate root cause)

1. **Empty `BROKER_ENCRYPTION_KEY`** — stale ESO render. Fixed live
   (force-sync ESO + engine restart); KEK 64 hex at
   `etradie/services/engine/staging:broker_encryption_key`.
2. **Alembic crash-loop** — empty `alembic_version` but tables existed.
   Fixed live (`stamp 0033`) + permanently in code (idempotent migrate).
3. **Vault unreachable** — engine egress had no rule to Vault `:8200`.
4. **`https` vs `http`** — in-cluster Vault is plain HTTP.
5. **Engine Vault 403** — default SA token aud was the API server, role
   needs `audience="vault"`. Fixed by projecting an `aud=vault` token.
6. **K8s API unreachable** — `10.43.0.1:443` DNATs to the node's
   apiserver `:6443` BEFORE kube-router egress eval; allowing the VIP
   never matched. Fixed by egress to `0.0.0.0/0:6443`. (kube-router
   REJECTs on policy deny, so it presented as `Connection refused`, not
   a timeout — that misled diagnosis early.)
7. **K8s API 403 Forbidden on create** — apiserver reachable but the
   engine Role lacked `create` on `configmaps` (the per-tenant watchdog
   ConfigMap). Fixed by granting configmaps create/update/patch/delete.
8. **Tenant pod Vault Agent 403 `invalid audience`** — the injected
   Vault Agent read the pod's DEFAULT SA token (aud=API server) but the
   `mt-node-tenant` role requires `audience="vault"`. Fixed (mirroring
   the engine) by projecting an `aud=vault` token + pointing the agent
   at it + copying the mount onto the agent containers. **<-- current.**

### Read-path note (separate from provisioning)

Even after a tenant pod is Ready, the dashboard's `GET /api/broker/symbols`
and positions endpoints raised `Hosted connection has no ea_auth_token`
because `_load_active_broker_connection` (and the `test` endpoint) only
decrypted `ea_auth_token_encrypted` for `connection_type=="ea"`. Fixed to
decrypt for `"hosted"` too (commits 2+3 group). Rides the engine image.

---

## Environment / identity (this session)

| Item | Value |
|---|---|
| Environment | `staging` |
| VPS / node | Contabo VPS 30 NVMe, node `vmi3362776`, public IP `13.140.164.173` |
| Namespace | `etradie-system` |
| Engine deploy | `deploy/etradie-engine` (mesh-OFF on staging per PHASE10.6 checkpoint) |
| Vault | `vault-0` in `vault` ns; KV-v2 mount `etradie`; `http://vault.vault.svc.cluster.local:8200` |
| Vault role (engine) | `mt-node-provisioner` (audience `vault`), policy `mt-node-provisioner-staging`, write on `etradie/data/tenants/mt-node/*` |
| Vault role (tenant pod) | `mt-node-tenant` (SA glob `etradie-mt-*`, read own path) |
| mt-node image | `ghcr.io/flamegreat-1/etradie-mt-node:0.1.0` (present in GHCR) |
| Dashboard user_id under test | `83d7fb874e2f9e8c091e07cf76ebaad8` |
| Git remotes | `origin` = GitHub (ArgoCD/CI source), `gitlab` = this MCP mirror (auto-pushes to origin) |

---

## Operator routine (every command below needs this)

Two terminals. Terminal 1 holds the SSH tunnel; Terminal 2 runs commands.

```bash
# Terminal 1 (leave open):
ssh -N -L 6443:127.0.0.1:6443 etradie@13.140.164.173

# Terminal 2:
export KUBECONFIG=~/.kube/etradie-contabo.yaml
kubectl get nodes   # vmi3362776 Ready -> tunnel is live
```

Vault root token (read-only use here):
```bash
ROOT_TOKEN=$(awk '/Initial Root Token:/ {print $NF}' ~/vault-init.txt)
# ... use ...
unset ROOT_TOKEN
```

---

## RESUME HERE — current step: roll engine image with defect 7+8 fix, then re-provision

**Why we wait:** defects 7+8 (tenant pod Vault `aud=vault`) live in
`src/engine/ta/broker/mt5/hosted/provisioner.py` (the runtime that stamps
the tenant pod spec). They only take effect once CI builds a NEW engine
image carrying those commits and ArgoCD rolls it. The Helm/infra fixes
(1,4,5,6) are already live. The chart copies of 7+8 are in
`helm/mt-node/templates/statefulset.yaml` for the by-hand/platform path.

### Step A — confirm the new engine image has rolled

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
# GitHub main must include the latest provisioner commits (defect 7+8):
git ls-remote https://github.com/FlameGreat-1/eTradie.git main
# The engine deployment image SHA must be NEWER than
# ghcr.io/flamegreat-1/etradie/engine:2e4aba9f... (the last pre-fix image)
kubectl -n etradie-system get deploy etradie-engine \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="engine")].image}{"\n"}'
kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine -o wide  # AGE fresh after roll
```
If the image SHA has NOT changed, CI has not built/bumped it yet. Wait
(or check the GitHub Actions pipeline). Do NOT re-provision until the
engine pod runs the new image, or the tenant pod will lack the projected
aud=vault token and loop on Vault 403 again.

### Step B — (one-time, already done this session) verify infra fixes live

```bash
# K8s API egress (defect 6): both should print OPEN.
GW=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine \
  --field-selector=status.phase=Running -o jsonpath='{.items[-1].metadata.name}')
kubectl -n etradie-system exec "$GW" -c engine -- python3 -c "
import socket
for h,p in [('10.43.0.1',443),('13.140.164.173',6443)]:
    s=socket.socket(); s.settimeout(5)
    try: s.connect((h,p)); print(h,p,'OPEN')
    except Exception as e: print(h,p,type(e).__name__,e)
    finally: s.close()"
# RBAC (defect 7-infra): configmaps must include create.
kubectl -n etradie-system get role etradie-engine \
  -o jsonpath='{range .rules[?(@.resources[0]=="configmaps")]}{.resources}{" -> "}{.verbs}{"\n"}{end}'
```
Expect: `10.43.0.1 443 OPEN`, `13.140.164.173 6443 OPEN`, and configmaps
verbs include `create,update,patch,delete`.

### Step B2 — DECISIVE: verify the tenant pod's Vault Agent authenticates

After the new engine image is live, delete the stuck connection from the
dashboard, re-create, then:

```bash
export KUBECONFIG=~/.kube/etradie-contabo.yaml
CONN=$(kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -t -A -c \
  "SELECT left(id::text,12) FROM broker_connections ORDER BY created_at DESC LIMIT 1;")
echo "CONN=$CONN"
# The agent's auto_auth config must show token_path=/var/run/secrets/vault/token:
kubectl -n etradie-system get pod etradie-mt-${CONN}-0 \
  -o jsonpath='{.spec.initContainers[?(@.name=="vault-agent-init")].env[?(@.name=="VAULT_CONFIG")].value}' \
  | base64 -d | python3 -m json.tool | grep -A5 auto_auth
# And the init log must show authentication SUCCESS (not 403 / no-such-file):
kubectl -n etradie-system logs etradie-mt-${CONN}-0 -c vault-agent-init --tail=15
```
Expect: `token_path` = `/var/run/secrets/vault/token`, and
`agent.auth.handler: authentication successful` (NOT
`invalid audience (aud) claim` and NOT `no such file or directory`).
Once that passes, the pod leaves `Init` -> `ContainerCreating` (Wine
pull) -> `3/3 Ready`. Proceed to Step C/D/E.

### Step C — confirm the prior fixes are STILL live (regression guard)

```bash
GW=$(kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-engine -o jsonpath='{.items[0].metadata.name}')
# Vault scheme + reachability
kubectl -n etradie-system exec "$GW" -c engine -- sh -c 'echo "VAULT_ADDR=$VAULT_ADDR"'   # http://...:8200
kubectl -n etradie-system exec "$GW" -c engine -- python3 -c "
import urllib.request
try:
    r=urllib.request.urlopen('http://vault.vault.svc.cluster.local:8200/v1/sys/health',timeout=5); print('VAULT HTTP',r.status)
except urllib.error.HTTPError as e: print('VAULT HTTP',e.code,'(reachable)')
except Exception as e: print('VAULT UNREACHABLE:',e)
"
# SA token audience
kubectl -n etradie-system exec "$GW" -c engine -- python3 -c "
import base64,json
t=open('/var/run/secrets/vault/token').read().split('.')[1]; t+='='*(-len(t)%4)
print('aud=', json.loads(base64.urlsafe_b64decode(t)).get('aud'))
"   # aud= ['vault']
```

### Step D — clean any failed row, then re-provision from the dashboard

```bash
# Delete the most recent failed row (id changes each attempt — list first):
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message FROM broker_connections ORDER BY created_at DESC LIMIT 3;"
# Then delete the failed one(s):
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE status='failed' RETURNING id, status;"
```

Now **submit the broker connection in the dashboard** (`connection_type=hosted`,
MT5 login/password/server). Then watch:

```bash
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message FROM broker_connections ORDER BY created_at DESC LIMIT 1;"
kubectl -n etradie-system get pod,statefulset,sa | grep -i 'mt-' || echo "none yet"
kubectl -n etradie-system logs deploy/etradie-engine -c engine --since=3m \
  | grep -iE 'hosted|provision|vault|statefulset' | grep -iv positions | tail -25
```

**Success signals:**
- Row `status` = `provisioning` then `active` (NOT `failed`).
- StatefulSet `etradie-mt-<id12>`, SA `etradie-mt-<id12>`, pod `etradie-mt-<id12>-0` appear.
- Engine log shows `hosted_*` progress, no `vault`/`403`/`Cannot connect` errors.
- First pod is slow (large Wine image pull) and rolls ONCE for the
  symbol-resolution two-boot dance (Phase 14.5.2 — expected, not a fault).

---

## Step E — tenant verification (run once the pod is up)

Set `CONN` to the first 12 chars of the connection_id (release =
`etradie-mt-<CONN>`):

```bash
CONN=<first-12-chars-of-connection-id>

# 1. Pod Ready + injected containers (mt-node, watchdog, vault-agent)
kubectl -n etradie-system get pod etradie-mt-${CONN}-0 -o wide
kubectl -n etradie-system get pod etradie-mt-${CONN}-0 \
  -o jsonpath='{range .spec.containers[*]}{.name}{"\n"}{end}'

# 2. Vault rendered per-tenant creds to tmpfs (no plaintext K8s Secret)
kubectl -n etradie-system exec etradie-mt-${CONN}-0 -c mt-node -- \
  sh -c 'test -s /vault/secrets/mt-credentials.env && echo creds-present'

# 3. EA health via the watchdog (both gauges should read 1)
kubectl -n etradie-system port-forward etradie-mt-${CONN}-0 9100:9100 &
curl -fsS http://localhost:9100/healthz && echo OK
curl -s http://localhost:9100/metrics | grep -E 'mt_node_ea_(mt5_connected|authenticated) '

# 4. Wine prefix PVC bound
kubectl -n etradie-system get pvc wine-prefix-etradie-mt-${CONN}-0

# 5. ZMQ bridge reachable from the engine
kubectl -n etradie-system logs deploy/etradie-engine -c engine | grep -i 'hosted_' | tail -20
```

---

## Known-good facts (verified live this session — don't re-debug)

- KEK present: `etradie/services/engine/staging:broker_encryption_key` = 64 hex; engine runtime `BROKER_ENCRYPTION_KEY` len 64.
- DB schema at Alembic `0033` (stamped); tables for 0001..0033 all present.
- Vault role `mt-node-provisioner` exists, bound to SA `etradie-engine` in `etradie-system`, policy `mt-node-provisioner-staging` grants write on `etradie/data/tenants/mt-node/*`. A manual `kubectl create token etradie-engine --audience=vault` -> login -> `vault kv put -mount=etradie tenants/mt-node/etradie-mt-probe` SUCCEEDS.
- Engine RBAC Role grants create/delete on statefulsets, serviceaccounts, services, and delete on pvc/secrets in `etradie-system`. `kubectl auth can-i create statefulsets/services --as=system:serviceaccount:etradie-system:etradie-engine` = yes.
- mt-node image `ghcr.io/flamegreat-1/etradie-mt-node:0.1.0` present in GHCR.
- Pre-flight ExternalSecret `etradie-mt-node-platform-platform` = SecretSynced/True.
- Vault reachable from engine: TCP 8200 OPEN, HTTP 200. Projected token `aud=['vault']`.

---

## Possible NEXT walls (anticipated, not yet hit)

1. **Per-tenant pod -> Vault**: the tenant pod uses the Vault Agent Injector
   (role `mt-node-tenant`, audience `vault`, injector handles token). It is a
   different pod/NetworkPolicy scope than the engine; watch its
   `vault-agent-init` if the pod sticks in `Init`.
2. **Wine image pull time**: first pull is large/slow; `ContainerCreating`
   for a couple minutes is normal, not a fault.
3. **Symbol two-boot**: one rolling restart shortly after Ready is expected
   (entrypoint resolves the broker's real symbol, patches `MT_SYMBOL`, K8s
   rolls once). Repeated rolling = fault (check entrypoint log).
4. **Capacity**: each tenant pod ~0.70 CPU; this box is sized ~1 prod MT user.

---

## Outstanding code follow-ups (proper fixes, not yet done)

- **Empty-KEK fail-closed**: engine should refuse to boot if
  `BROKER_ENCRYPTION_KEY` is empty/short (lives in `engine.shared.crypto` /
  the vault settings, NOT `config.py`). Prevents the silent-empty-KEK class.
- **Misleading provisioner error**: `dependencies.py:559` raises
  "broker connection vanished between metadata fetch and construction" for
  what is really "no ea_auth_token / KEK unreadable". Make it specific.
- **Migration image rollout**: commits 2+3 are on main but need the CI
  engine image to actually run in-cluster; until then the idempotent-migrate
  guard is not active (DB is already stamped, so not currently blocking).

---

## Rollback / safety notes

- All fixes 1,4,5 are Helm values/pod-spec only -> revert = `git revert` the
  commit + `argocd app sync engine-staging`. No data touched.
- The Alembic `stamp 0033` and the ESO KEK force-sync were one-time live
  rescues; they are also fixed in code so they won't recur.
- Failed `broker_connections` rows are safe to delete (no SA/STS/Vault path
  is created on a failed provision; verified `kubectl get sa | grep mt-` = none).
