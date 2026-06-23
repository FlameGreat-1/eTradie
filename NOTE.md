Important — read the row status carefully. This is **not** "taking time," it's a **failure**:

```
status  | failed
status_message | Provisioning failed: mt-node StatefulSet did not become Ready within timeout
```

So provisioning hit the **300s readiness timeout** and `_best_effort_cleanup` deleted the StatefulSet. The pod you see re-initializing (`Init:1/2`, AGE 6s, new resourceVersion) is the StatefulSet controller recreating the pod during teardown — it's being torn down, not progressing.

#### Where exactly we are in the chain

Big progress, then a wall at a **new, later** stage:
- ✅ bundle init: `OK` / "Bundle extracted successfully."
- ✅ mt-node started (you saw `2/3 Running` briefly)
- ❌ **never reached `3/3 Ready` within 300s** → `_wait_ready` timed out.

`_wait_ready` has two phases: (1) StatefulSet has a Ready replica, (2) ZMQ PING returns `ok`. The message says "StatefulSet did not become Ready" — so it's **phase 1**: the pod never went `3/3 Ready`. The pod readiness gates on the watchdog `/healthz`, which only goes green when the EA reports `mt5_connected=1 AND authenticated=1` — i.e. **MT5 logged in and the EA bound :5555.** That didn't happen in 300s.

So we've moved the wall from "bundle/servers.dat" to "MT5 login + EA bind." Now I need to know **why** — and whether servers.dat actually got installed before the terminal was killed. But the StatefulSet is being deleted, so we must catch the **next** pod's logs, or read the journal before cleanup removes it.

#### Why it might genuinely be slow on first boot (your question)

First boot is the slowest by far:
- `broker-bundle` init downloads **264MB** + unzips (~1-2 min alone).
- Wine prefix seed from the 166MB template (`cp -a` + `wineboot -u`) — minutes.
- MT5 cold boot + **full 453-file MQL5 recompilation** (~100s, per the watchdog grace comment).
- Then login → symbols → chart → EA bind.

That can legitimately approach or exceed the **300s** `_READINESS_TIMEOUT_SECS`, especially with the 264MB bundle eating time the old design didn't have. **The bundle download may be pushing total boot past the 300s gate.** That's a real possibility, not just login failure.

#### What to do — capture the real cause before it's torn down

The row is `failed` and cleanup runs, but the engine will likely retry (recovery sweep) or you re-provision. Either way, **catch a live pod's MT5 journal** to see whether it's (a) slow boot hitting the timeout, or (b) an actual login failure. Run this in a tight loop so you grab it while a pod exists:

```bash
# Watch for any mt-node pod and grab its journal + entrypoint log the moment it's up
POD=$(kubectl -n etradie-system get pods -o name | grep 'etradie-mt-' | head -1 | cut -d/ -f2); echo "$POD"

# A) did servers.dat actually install? (proves defect B end-to-end on a live pod)
kubectl -n etradie-system logs $POD -c mt-node 2>/dev/null | grep -iE 'Installed broker servers.dat|Launching|seeded|Xvfb'

# B) the MT5 journal — is it logging in, or stuck compiling?
kubectl -n etradie-system exec $POD -c mt-node -- sh -c \
  'J="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/logs"; f=$(ls -t "$J"/*.log 2>/dev/null|head -1); echo "=== $f ==="; tail -40 "$f"' 2>/dev/null
```

And critically — **raise the readiness timeout** so a slow-but-correct first boot can finish, separating "slow" from "broken." The provisioner reads `MT_NODE_READINESS_TIMEOUT_SECS` (default 300). Bump it on the engine so the next provision has room:

```bash
kubectl -n etradie-system set env deploy/etradie-engine MT_NODE_READINESS_TIMEOUT_SECS=900
kubectl -n etradie-system rollout status deploy/etradie-engine
```
(900s = 15 min. This is a runtime env override, no rebuild. If the pod reaches 3/3 with the longer window, the cause was slow first-boot, not login failure. We can then tune properly.)

#### Then clean + re-provision with the longer window

```bash
kubectl -n etradie-system delete statefulset,svc,sa,configmap,pvc -l app.kubernetes.io/name=etradie-mt-node --ignore-not-found
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "DELETE FROM broker_connections WHERE status IN ('failed','provisioning','active') RETURNING id;"
```
Re-submit from the dashboard, then **immediately** start tailing the journal (B above) so you watch the login attempt live.

#### Direct answers to your questions

- **"Is it taking time / first time?"** Partly yes — first boot is genuinely slow (264MB bundle + prefix seed + 453-file recompile), and that may be exceeding the 300s gate. But the row says `failed`, so right now it's not "just slow," it timed out and got cleaned up.
- **"At what point are we?"** Past servers.dat/bundle (those work now), stuck at **MT5 login → EA :5555 bind → pod 3/3 Ready** within the readiness window. Either login isn't completing, or the whole boot is too slow for 300s.

Bump the timeout to 900s, re-provision, and tail the MT5 journal live. Paste the journal `tail -40` — that tells us definitively whether MT5 is logging into Deriv (slow but working) or failing to log in (real problem). That's the next fork.






THIS IS THE OUTPUT OF THE COMMANDS:



softverse@Softverse:~/eTradie$
softverse@Softverse:~/eTradie$ # Watch for any mt-node pod and grab its journal + entrypoint log the moment it's up
POD=$(kubectl -n etradie-system get pods -o name | grep 'etradie-mt-' | head -1 | cut -d/ -f2); echo "$POD"

# A) did servers.dat actually install? (proves defect B end-to-end on a live pod)
kubectl -n etradie-system logs $POD -c mt-node 2>/dev/null | grep -iE 'Installed broker servers.dat|Launching|seeded|Xvfb'

# B) the MT5 journal — is it logging in, or stuck compiling?
kubectl -n etradie-system exec $POD -c mt-node -- sh -c \
  'J="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/logs"; f=$(ls -t "$J"/*.log 2>/dev/null|head -1); echo "=== $f ==="; tail -40 "$f"' 2>/dev/null
etradie-mt-f5807ee7-e8c-0
2026-06-22T12:09:46Z [INFO] Starting Xvfb on :99
2026-06-22T12:09:46Z [INFO] Xvfb ready
2026-06-22T12:09:46Z [INFO] Installed broker servers.dat from bundle (/broker-bundle/MetaTrader 5/Config/servers.dat)
2026-06-22T12:09:46Z [INFO] Installed broker servers.dat from bundle (/broker-bundle/MetaTrader 5/config/servers.dat)
2026-06-22T12:09:46Z [INFO] Launching terminal64.exe (platform=mt5, server=Deriv-Demo, login=201415706, symbol=__pending__, symbol_resolved=false, zmq_port=5555, restart_count=0)
=== /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/logs/20260622.log ===
��GO    0       12:07:11.014    Terminal        MetaTrader 5 x64 build 5836 started for MetaQuotes Ltd.
HH      0       12:07:11.015    Terminal        Windows 10 build 19045 on Wine 11.0 Linux 6.8.0-124-generic, 8 x AMD EPYC (with IBPB), AVX2, 17 / 23 Gb memory, 108 / 192 Gb disk, GMT+0
FH      0       12:07:11.015    Terminal        C:\Program Files\MetaTrader 5
JR      0       12:07:11.137    Compiler        full recompilation has been started
MK      0       12:07:13.310    Compiler        full recompilation has been finished:  0 file(s) compiled
OF      0       12:07:54.569    Terminal        MetaTrader 5 x64 build 5836 started for MetaQuotes Ltd.
JQ      0       12:07:54.573    Terminal        Windows 10 build 19045 on Wine 11.0 Linux 6.8.0-124-generic, 8 x AMD EPYC (with IBPB), AVX2, 17 / 23 Gb memory, 108 / 192 Gb disk, GMT+0
HG      0       12:07:54.573    Terminal        C:\Program Files\MetaTrader 5
HH      0       12:08:52.316    Terminal        MetaTrader 5 x64 build 5836 started for MetaQuotes Ltd.
NH      0       12:08:52.318    Terminal        Windows 10 build 19045 on Wine 11.0 Linux 6.8.0-124-generic, 8 x AMD EPYC (with IBPB), AVX2, 17 / 23 Gb memory, 108 / 192 Gb disk, GMT+0
PI      0       12:08:52.318    Terminal        C:\Program Files\MetaTrader 5
softverse@Softverse:~/eTradie$ kubectl -n etradie-system set env deploy/etradie-engine MT_NODE_READINESS_TIMEOUT_SECS=900
kubectl -n etradie-system rollout status deploy/etradie-engine
deployment.apps/etradie-engine env updated
Waiting for deployment "etradie-engine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "etradie-engine" rollout to finish: 1 old replicas are pending termination...
deployment "etradie-engine" successfully rolled out
softverse@Softverse:~/eTradie





Now we have the decisive evidence, and it points to a **real login failure**, not slow boot. Read the journal carefully:

```
12:07:11  build 5836 started
12:07:13  full recompilation finished: 0 file(s) compiled
12:07:54  build 5836 started   ← restarted
12:08:52  build 5836 started   ← restarted again
```

Three things stand out:

1. **servers.dat IS installed** — and from BOTH `Config/` and `config/` (Wine case-insensitivity; harmless). Defect #16/#17 fully closed. ✅

2. **The journal ends at `0 file(s) compiled` then NOTHING** — no `network`, no `login`, no `authorized`, no `connect` line. MT5 starts, compiles, and **never attempts a broker connection.** Same signature as the original defect #16, but now servers.dat HAS Deriv. So the server name resolves, yet MT5 still isn't logging in.

3. **MT5 is restarting every ~40-60s** (12:07:11 → 12:07:54 → 12:08:52) — the in-pod supervised loop is relaunching it. It's not hanging; it's launching, doing nothing, exiting, relaunching.

So this is **not** a timeout-due-to-slowness problem. Raising the timeout to 900s won't help — MT5 makes zero login attempt regardless of how long you wait. The `__pending__` sentinel boot path is launching the terminal but it's never connecting.

#### This is exactly the defect #15b signature — `/config:startup.ini` not being acted on

Look back at the runbook history: defect #15b was "MT5 starts + compiles, then does nothing; startup.ini not honored," and the journal ended identically at `0 file(s) compiled`. That was *hypothesised* to be servers.dat (#16). We fixed servers.dat — but the journal is STILL ending at `0 file(s) compiled` with no login. That means **#15b was a real, separate issue that servers.dat did not resolve**: MT5 build 5836 under Wine is launching but not auto-logging-in from the `startup.ini` `[Common]` Login/Password/Server.

I must not guess the fix. The next step is to capture the **actual launch + config state on the live pod** to confirm whether startup.ini is correct and whether `/config:` is being honored. Get these from the running pod (it exists now, AGE is recent):

```bash
POD=etradie-mt-f5807ee7-e8c-0
P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"

# 1. The EXACT launch args — is /config: being passed?
kubectl -n etradie-system exec $POD -c mt-node -- sh -c 'ps -ef | grep -i terminal64 | grep -v grep'

# 2. The startup.ini we wrote — Login/Password/Server populated?
kubectl -n etradie-system exec $POD -c mt-node -- sh -c "cat \"$P/config/startup.ini\""

# 3. Does servers.dat actually contain Deriv-Demo specifically (the server we set)?
kubectl -n etradie-system exec $POD -c mt-node -- sh -c \
  "grep -aiE 'Deriv-Demo' \"$P/config/servers.dat\" && echo FOUND || echo 'Deriv-Demo NOT in servers.dat'"

# 4. Full journal (not just tail) — any 'login'/'auth'/'connect'/'invalid account'/'no connection' anywhere?
kubectl -n etradie-system exec $POD -c mt-node -- sh -c \
  "cat \"$P/logs/\"*.log | grep -iE 'login|auth|connect|account|network|invalid|fail|deriv' || echo 'NO connection-related line at all'"

# 5. Was a Deriv-Demo Bases dir created? (only after a real connect)
kubectl -n etradie-system exec $POD -c mt-node -- sh -c "ls \"$P/bases\" 2>&1; ls \"$P/Bases\" 2>&1"
```

What each tells us:
- **#1** — if `/config:` is in the args but no login happens, the build isn't honoring auto-login via startup.ini (the #15b root cause confirmed). If `/config:` is *missing*, the entrypoint isn't passing it.
- **#2** — if Login/Password/Server are blank, the Vault creds didn't render into the env (different bug). If populated correctly, the config is right and MT5 just isn't acting on it.
- **#3** — confirms `Deriv-Demo` (the exact server string) is in the installed servers.dat, not just "deriv" something.
- **#4** — the authoritative "did it ever try to connect" check across the whole journal.

Note: I'd hold off re-provisioning for now — this pod is still alive and is the best evidence we have. The 900s timeout bump is fine to keep (harmless), but it won't fix a no-login-attempt. 

Paste #1–#5. That determines whether the next fix is in `entrypoint.sh` (launch line / startup.ini format / creds), and it's the genuinely unsolved part of the original blocker (#15b) that the servers.dat work revealed was independent. This is real diagnosis territory now — no guessing until we see the launch args + startup.ini.




THIS IS THE OUTPUT OF THE COMMAND:



eTradie$ POD=etradie-mt-f5807ee7-e8c-0
P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"

# 1. The EXACT launch args — is /config: being passed?
kubectl -n etradie-system exec $POD -c mt-node -- sh -c 'ps -ef | grep -i terminal64 | grep -v grep'

# 2. The startup.ini we wrote — Login/Password/Server populated?
kubectl -n etradie-system exec $POD -c mt-node -- sh -c "cat \"$P/config/startup.ini\""

# 3. Does servers.dat actually contain Deriv-Demo specifically (the server we set)?
kubectl -n etradie-system exec $POD -c mt-node -- sh -c \
  "grep -aiE 'Deriv-Demo' \"$P/config/servers.dat\" && echo FOUND || echo 'Deriv-Demo NOT in servers.dat'"

# 4. Full journal (not just tail) — any 'login'/'auth'/'connect'/'invalid account'/'no connection' anywhere?
kubectl -n etradie-system exec $POD -c mt-node -- sh -c \
  "cat \"$P/logs/\"*.log | grep -iE 'login|auth|connect|account|network|invalid|fail|deriv' || echo 'NO connection-related line at all'"

# 5. Was a Deriv-Demo Bases dir created? (only after a real connect)
kubectl -n etradie-system exec $POD -c mt-node -- sh -c "ls \"$P/bases\" 2>&1; ls \"$P/Bases\" 2>&1"
mt           100      43  0 12:11 ?        00:00:00 start.exe /exec terminal64.exe
mt           188       1 13 12:11 ?        00:00:04 C:\Program Files\MetaTrader 5\terminal64.exe /config:/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/startup.ini
[Common]
Login=201415706
Password=43123abcchuks
Server=Deriv-Demo
AutoConfiguration=true

[Charts]
Period=H1
Template=expert

[Experts]
AllowLive=true
AllowDllImport=true
Enabled=true
Account=201415706
Profile=default
Deriv-Demo NOT in servers.dat
NO connection-related line at all
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")
softverse@Softverse:~/eTradie





























