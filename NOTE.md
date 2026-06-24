1/etradie/mt-node/manifests/$PIN"
# Expect: 200

# ── Step 3: tunnel + ArgoCD sync ─────────────────────────────────────
echo "Confirm tunnel is alive in second terminal, then press Enter."
read -r

  "SELECT id, status FROM broker_connections WHERE connection_type='hosted';"ling 2>/dev/null \
From https://github.com/FlameGreat-1/eTradie
 * branch              main       -> FETCH_HEAD
From https://github.com/FlameGreat-1/eTradie
 * branch              main       -> FETCH_HEAD
Already up to date.
a585c746 (HEAD -> main, origin/main) ci: pin staging image tags to 45ace426705c013c44c952ed8d75450cec7212f0 [skip ci]
45ace426 fix(mt-node): resolve infinite 143 restart loop caused by nameless wizard modals
aa1005b9 ci: pin staging image tags to 9b88dcf3282c981c7cb05e55015d98fed724e8fb [skip ci]
9b88dcf3 fix(mt-node): switch Phase 3 from xdotool type to clipboard paste and add typing fallback when clipboard paste fails
906b4f58 (gitlab/main) ci: pin staging image tags to b74c3b818b7d3fcb58328f26cb208a3e58bc6aa3 [skip ci]
85619dad fix(mt-node): add fluxbox window manager so xdotool can actually drive MT5
06f8c1dd fix(mt-node): add fluxbox window manager so xdotool can actually drive MT5
d800f94e docs(runbook): rewrite HOSTED-MT-PROVISIONING-SESSION.md as operator-first
Pinned mt-node SHA: 45ace426705c013c44c952ed8d75450cec7212f0
200
Confirm tunnel is alive in second terminal, then press Enter.

NAME         STATUS   ROLES                  AGE   VERSION
vmi3362776   Ready    control-plane,master   10d   v1.30.4+k3s1
application.argoproj.io/engine-staging patched
application.argoproj.io/mt-node-staging patched
Waiting for deployment "etradie-engine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "etradie-engine" rollout to finish: 1 old replicas are pending termination...
deployment "etradie-engine" successfully rolled out
ghcr.io/flamegreat-1/etradie/mt-node:45ace426705c013c44c952ed8d75450cec7212f0
 id | status
----+--------
(0 rows)

DELETE 0
No resources found
Success! Data deleted (if it existed) at: etradie/metadata/etradie/tenants/mt-node/etradie-mt-aadbc8f4-a0e-0
deployment.apps/etradie-engine restarted
Waiting for deployment "etradie-engine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "etradie-engine" rollout to finish: 1 old replicas are pending termination...
deployment "etradie-engine" successfully rolled out
No resources found in etradie-system namespace.
 id | status
----+--------
(0 rows)

softverse@Softverse:~/eTradie$ echo ""
echo "================================================================"
echo "RE-PROVISION FROM DASHBOARD NOW."
echo "Press Enter the SECOND you click submit."
echo "================================================================"
read -r

# ── Step 6: race to pod ─────────────────────────────────────────────
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

for i in $(seq 1 60); do
  state=$(kubectl -n etradie-system get pod "$POD" \
    -o jsonpath='{.status.containerStatuses[?(@.name=="mt-node")].state}' 2>/dev/null)
  echo "[$i] mt-node state: $state"
  echo "$state" | grep -q running && break
  sleep 2
done

kubectl -n etradie-system get pod "$POD" \
  -o jsonpath='{.spec.containers[?(@.name=="mt-node")].image}{"\n"}'

# ── Step 7: CRITICAL — verify fluxbox + xclip + xdotool installed ───
echo ""
echo "================================================================"
echo "TOOL AVAILABILITY CHECK"
echo "================================================================"
sleep 15
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'which xdotool xclip xprop xwd fluxbox; echo "---"; xclip -version 2>&1 | head -1'

# ── Step 8: verify fluxbox started + EWMH atoms ─────────────────────
echo "  explorer.exe ~/phase2c-diagnostics/screen-final.png    (end state)")" dialog)"g|BOTH paste and type failed' driver-log-full.txt | tail -10>/dev/null

================================================================
RE-PROVISION FROM DASHBOARD NOW.
Press Enter the SECOND you click submit.
================================================================

Release: etradie-mt-f9cbebc5-b60
POD=etradie-mt-f9cbebc5-b60-0
[1] mt-node state: {"waiting":{"reason":"PodInitializing"}}
[2] mt-node state: {"running":{"startedAt":"2026-06-24T11:26:25Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:45ace426705c013c44c952ed8d75450cec7212f0

================================================================
TOOL AVAILABILITY CHECK
================================================================
/usr/bin/xdotool
/usr/bin/xclip
/usr/bin/xprop
/usr/bin/xwd
/usr/bin/fluxbox
---
xclip version 0.13

================================================================
FLUXBOX + EWMH READINESS
================================================================

============ poll 1 / 16  (11:26:50) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   0     42s

--- driver log (auto_login + paste/type sentinels) ---

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 2 / 16  (11:27:27) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   0     78s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:26:59Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T11:26:59Z [INFO] fluxbox ready (pid=227); _NET_ACTIVE_WINDOW available
2026-06-24T11:26:59Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:26:59Z [INFO] auto_login: hard-kill watchdog armed (pid=280, fires at +270s)
2026-06-24T11:27:00Z [INFO] auto_login: terminal process detected at +1s
2026-06-24T11:27:29Z [INFO] auto_login: main UI window WID=12582913 detected at +30s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:27:29Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:27:29Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 3 / 16  (11:28:04) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   0     116s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:26:59Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T11:26:59Z [INFO] fluxbox ready (pid=227); _NET_ACTIVE_WINDOW available
2026-06-24T11:26:59Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:26:59Z [INFO] auto_login: hard-kill watchdog armed (pid=280, fires at +270s)
2026-06-24T11:27:00Z [INFO] auto_login: terminal process detected at +1s
2026-06-24T11:27:29Z [INFO] auto_login: main UI window WID=12582913 detected at +30s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:27:29Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:27:29Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:27:30Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:27:32Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T11:27:32Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 4 / 16  (11:28:42) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   0     2m33s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:26:59Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T11:26:59Z [INFO] fluxbox ready (pid=227); _NET_ACTIVE_WINDOW available
2026-06-24T11:26:59Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:26:59Z [INFO] auto_login: hard-kill watchdog armed (pid=280, fires at +270s)
2026-06-24T11:27:00Z [INFO] auto_login: terminal process detected at +1s
2026-06-24T11:27:29Z [INFO] auto_login: main UI window WID=12582913 detected at +30s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:27:29Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:27:29Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:27:30Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:27:32Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T11:27:32Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

--- capturing framebuffer (poll 4) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 5 / 16  (11:29:26) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   0     3m17s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:26:59Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T11:26:59Z [INFO] fluxbox ready (pid=227); _NET_ACTIVE_WINDOW available
2026-06-24T11:26:59Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:26:59Z [INFO] auto_login: hard-kill watchdog armed (pid=280, fires at +270s)
2026-06-24T11:27:00Z [INFO] auto_login: terminal process detected at +1s
2026-06-24T11:27:29Z [INFO] auto_login: main UI window WID=12582913 detected at +30s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:27:29Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:27:29Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:27:30Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:27:32Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T11:27:32Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 6 / 16  (11:30:04) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   0     3m55s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:26:59Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T11:26:59Z [INFO] fluxbox ready (pid=227); _NET_ACTIVE_WINDOW available
2026-06-24T11:26:59Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:26:59Z [INFO] auto_login: hard-kill watchdog armed (pid=280, fires at +270s)
2026-06-24T11:27:00Z [INFO] auto_login: terminal process detected at +1s
2026-06-24T11:27:29Z [INFO] auto_login: main UI window WID=12582913 detected at +30s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:27:29Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:27:29Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:27:30Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:27:32Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T11:27:32Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 7 / 16  (11:30:41) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   0     4m32s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:26:59Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T11:26:59Z [INFO] fluxbox ready (pid=227); _NET_ACTIVE_WINDOW available
2026-06-24T11:26:59Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:26:59Z [INFO] auto_login: hard-kill watchdog armed (pid=280, fires at +270s)
2026-06-24T11:27:00Z [INFO] auto_login: terminal process detected at +1s
2026-06-24T11:27:29Z [INFO] auto_login: main UI window WID=12582913 detected at +30s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:27:29Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:27:29Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:27:30Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:27:32Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T11:27:32Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 8 / 16  (11:31:19) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   0     5m10s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:26:59Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T11:26:59Z [INFO] fluxbox ready (pid=227); _NET_ACTIVE_WINDOW available
2026-06-24T11:26:59Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:26:59Z [INFO] auto_login: hard-kill watchdog armed (pid=280, fires at +270s)
2026-06-24T11:27:00Z [INFO] auto_login: terminal process detected at +1s
2026-06-24T11:27:29Z [INFO] auto_login: main UI window WID=12582913 detected at +30s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:27:29Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:27:29Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:27:30Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:27:32Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T11:27:32Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T11:27:33Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

--- capturing framebuffer (poll 8) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 9 / 16  (11:32:02) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   1 (30s ago)   5m53s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:31:34Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T11:31:34Z [INFO] fluxbox ready (pid=811); _NET_ACTIVE_WINDOW available
2026-06-24T11:31:34Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:31:34Z [INFO] auto_login: hard-kill watchdog armed (pid=864, fires at +270s)
2026-06-24T11:31:34Z [INFO] auto_login: terminal process detected at +0s

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 10 / 16  (11:32:41) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   1 (69s ago)   6m32s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:31:34Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T11:31:34Z [INFO] fluxbox ready (pid=811); _NET_ACTIVE_WINDOW available
2026-06-24T11:31:34Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:31:34Z [INFO] auto_login: hard-kill watchdog armed (pid=864, fires at +270s)
2026-06-24T11:31:34Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T11:32:05Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:32:05Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:32:05Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:32:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:32:08Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s
2026-06-24T11:32:08Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=unknown name=unknown
2026-06-24T11:32:09Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T11:32:16Z [WARN] MetaTrader exited with code 143
2026-06-24T11:32:23Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:32:23Z [INFO] auto_login: hard-kill watchdog armed (pid=1265, fires at +270s)
2026-06-24T11:32:23Z [INFO] auto_login: terminal process detected at +0s

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 11 / 16  (11:33:18) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   1 (106s ago)   7m9s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:31:34Z [INFO] auto_login: hard-kill watchdog armed (pid=864, fires at +270s)
2026-06-24T11:31:34Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T11:32:05Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:32:05Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:32:05Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:32:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:32:08Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s
2026-06-24T11:32:08Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=unknown name=unknown
2026-06-24T11:32:09Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T11:32:16Z [WARN] MetaTrader exited with code 143
2026-06-24T11:32:23Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:32:23Z [INFO] auto_login: hard-kill watchdog armed (pid=1265, fires at +270s)
2026-06-24T11:32:23Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T11:32:54Z [INFO] auto_login: main UI window WID=14680065 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:32:54Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=14680065, Alt+F then L)
2026-06-24T11:32:54Z [INFO] auto_login: blocking modal detected (WID=14680088, NAME=); attempting dismiss
2026-06-24T11:32:55Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:32:56Z [INFO] auto_login: Login dialog WID=14680090 appeared after mnemonic at +33s
2026-06-24T11:32:56Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: phase3 stage=post_activate focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T11:32:59Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T11:32:59Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T11:32:59Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T11:32:59Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=14680090 name=Login
2026-06-24T11:33:00Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=14680090 name=Login
2026-06-24T11:33:00Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 12 / 16  (11:33:57) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   1 (2m25s ago)   7m48s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:31:34Z [INFO] auto_login: hard-kill watchdog armed (pid=864, fires at +270s)
2026-06-24T11:31:34Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T11:32:05Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:32:05Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:32:05Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:32:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:32:08Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s
2026-06-24T11:32:08Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=unknown name=unknown
2026-06-24T11:32:09Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T11:32:16Z [WARN] MetaTrader exited with code 143
2026-06-24T11:32:23Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:32:23Z [INFO] auto_login: hard-kill watchdog armed (pid=1265, fires at +270s)
2026-06-24T11:32:23Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T11:32:54Z [INFO] auto_login: main UI window WID=14680065 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:32:54Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=14680065, Alt+F then L)
2026-06-24T11:32:54Z [INFO] auto_login: blocking modal detected (WID=14680088, NAME=); attempting dismiss
2026-06-24T11:32:55Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:32:56Z [INFO] auto_login: Login dialog WID=14680090 appeared after mnemonic at +33s
2026-06-24T11:32:56Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: phase3 stage=post_activate focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T11:32:59Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T11:32:59Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T11:32:59Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T11:32:59Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=14680090 name=Login
2026-06-24T11:33:00Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=14680090 name=Login
2026-06-24T11:33:00Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

--- capturing framebuffer (poll 12) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 13 / 16  (11:34:42) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   1 (3m10s ago)   8m33s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:31:34Z [INFO] auto_login: hard-kill watchdog armed (pid=864, fires at +270s)
2026-06-24T11:31:34Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T11:32:05Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:32:05Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:32:05Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:32:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:32:08Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s
2026-06-24T11:32:08Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=unknown name=unknown
2026-06-24T11:32:09Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T11:32:16Z [WARN] MetaTrader exited with code 143
2026-06-24T11:32:23Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:32:23Z [INFO] auto_login: hard-kill watchdog armed (pid=1265, fires at +270s)
2026-06-24T11:32:23Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T11:32:54Z [INFO] auto_login: main UI window WID=14680065 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:32:54Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=14680065, Alt+F then L)
2026-06-24T11:32:54Z [INFO] auto_login: blocking modal detected (WID=14680088, NAME=); attempting dismiss
2026-06-24T11:32:55Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:32:56Z [INFO] auto_login: Login dialog WID=14680090 appeared after mnemonic at +33s
2026-06-24T11:32:56Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: phase3 stage=post_activate focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T11:32:59Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T11:32:59Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T11:32:59Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T11:32:59Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=14680090 name=Login
2026-06-24T11:33:00Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=14680090 name=Login
2026-06-24T11:33:00Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 14 / 16  (11:35:20) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   1 (3m48s ago)   9m11s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:31:34Z [INFO] auto_login: hard-kill watchdog armed (pid=864, fires at +270s)
2026-06-24T11:31:34Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T11:32:05Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:32:05Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:32:05Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:32:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:32:08Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s
2026-06-24T11:32:08Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=unknown name=unknown
2026-06-24T11:32:09Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T11:32:16Z [WARN] MetaTrader exited with code 143
2026-06-24T11:32:23Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:32:23Z [INFO] auto_login: hard-kill watchdog armed (pid=1265, fires at +270s)
2026-06-24T11:32:23Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T11:32:54Z [INFO] auto_login: main UI window WID=14680065 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:32:54Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=14680065, Alt+F then L)
2026-06-24T11:32:54Z [INFO] auto_login: blocking modal detected (WID=14680088, NAME=); attempting dismiss
2026-06-24T11:32:55Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:32:56Z [INFO] auto_login: Login dialog WID=14680090 appeared after mnemonic at +33s
2026-06-24T11:32:56Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: phase3 stage=post_activate focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T11:32:59Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T11:32:59Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T11:32:59Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T11:32:59Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=14680090 name=Login
2026-06-24T11:33:00Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=14680090 name=Login
2026-06-24T11:33:00Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 15 / 16  (11:35:58) ============
etradie-mt-f9cbebc5-b60-0   2/3   Running   1 (4m26s ago)   9m49s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T11:31:34Z [INFO] auto_login: hard-kill watchdog armed (pid=864, fires at +270s)
2026-06-24T11:31:34Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T11:32:05Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:32:05Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T11:32:05Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T11:32:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:32:08Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s
2026-06-24T11:32:08Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T11:32:09Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=unknown name=unknown
2026-06-24T11:32:09Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T11:32:16Z [WARN] MetaTrader exited with code 143
2026-06-24T11:32:23Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T11:32:23Z [INFO] auto_login: hard-kill watchdog armed (pid=1265, fires at +270s)
2026-06-24T11:32:23Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T11:32:54Z [INFO] auto_login: main UI window WID=14680065 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T11:32:54Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=14680065, Alt+F then L)
2026-06-24T11:32:54Z [INFO] auto_login: blocking modal detected (WID=14680088, NAME=); attempting dismiss
2026-06-24T11:32:55Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T11:32:56Z [INFO] auto_login: Login dialog WID=14680090 appeared after mnemonic at +33s
2026-06-24T11:32:56Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: phase3 stage=post_activate focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=14680090 name=Login
2026-06-24T11:32:58Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T11:32:59Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T11:32:59Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T11:32:59Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T11:32:59Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=14680090 name=Login
2026-06-24T11:33:00Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=14680090 name=Login
2026-06-24T11:33:00Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 16 / 16  (11:36:35) ============
Error from server (NotFound): pods "etradie-mt-f9cbebc5-b60-0" not found
POD GONE

============ FINAL ARTIFACTS ============
1 driver-log-full.txt
Error from server (NotFound): pods "etradie-mt-f9cbebc5-b60-0" not found
mt5-journal.txt: 0 lines
Error from server (NotFound): pods "etradie-mt-f9cbebc5-b60-0" not found
Error from server (NotFound): pods "etradie-mt-f9cbebc5-b60-0" not found
OK: screen-poll-4.png
OK: screen-poll-8.png
OK: screen-poll-12.png
OK: screen-final.png

============ VERDICT ============
Error from server (NotFound): pods "etradie-mt-f9cbebc5-b60-0" not found

--- accounts.dat (login completed?) ---
Error from server (NotFound): pods "etradie-mt-f9cbebc5-b60-0" not found

--- MQL5/Logs (EA loaded?) ---
Error from server (NotFound): pods "etradie-mt-f9cbebc5-b60-0" not found

--- :5555 socket ---
Error from server (NotFound): pods "etradie-mt-f9cbebc5-b60-0" not found

--- MT5 journal (broker response is here) ---
Error from server (NotFound): pods "etradie-mt-f9cbebc5-b60-0" not found

--- DB row ---
                  id                  | status |                                status_message                                | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+------------+-----------
 f9cbebc5-b606-480d-b4b7-a3199aa6f32a | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout |            | t
(1 row)


============ DRIVER SENTINELS ============

--- fluxbox readiness ---

--- Welcome modal handling ---

--- Phase 2c (Login dialog open) ---

--- Phase 3 strategy + per-field outcome ---

--- Phase 3 stage transitions ---

--- Final outcome ---

============ FILES ============
-rw-r--r-- 1 softverse softverse  3674 Jun 24 09:11 /home/softverse/phase2c-diagnostics/after-10down.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 09:11 /home/softverse/phase2c-diagnostics/after-9down.png
-rw-r--r-- 1 softverse softverse 14204 Jun 24 09:52 /home/softverse/phase2c-diagnostics/after-altf-l.png
-rw-r--r-- 1 softverse softverse 13654 Jun 24 09:52 /home/softverse/phase2c-diagnostics/after-altf.png
-rw-r--r-- 1 softverse softverse 24872 Jun 24 08:57 /home/softverse/phase2c-diagnostics/driver-log-full-v2.txt
-rw-r--r-- 1 softverse softverse   110 Jun 24 12:36 /home/softverse/phase2c-diagnostics/driver-log-full.txt
-rw-r--r-- 1 softverse softverse  1292 Jun 24 08:57 /home/softverse/phase2c-diagnostics/mt5-journal-v2.txt
-rw-r--r-- 1 softverse softverse     0 Jun 24 12:36 /home/softverse/phase2c-diagnostics/mt5-journal.txt
-rw-r--r-- 1 softverse softverse 19633 Jun 24 08:52 /home/softverse/phase2c-diagnostics/pod-state.txt
-rw-r--r-- 1 softverse softverse  7397 Jun 24 09:00 /home/softverse/phase2c-diagnostics/screen-final-now.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 12:36 /home/softverse/phase2c-diagnostics/screen-final.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 08:57 /home/softverse/phase2c-diagnostics/screen-now.png
-rw-r--r-- 1 softverse softverse 14313 Jun 24 12:36 /home/softverse/phase2c-diagnostics/screen-poll-12.png
-rw-r--r-- 1 softverse softverse 19066 Jun 24 12:36 /home/softverse/phase2c-diagnostics/screen-poll-4.png
-rw-r--r-- 1 softverse softverse 19066 Jun 24 12:36 /home/softverse/phase2c-diagnostics/screen-poll-8.png
-rw-r--r-- 1 softverse softverse     0 Jun 24 12:36 /home/softverse/phase2c-diagnostics/windows-final.txt
-rw-r--r-- 1 softverse softverse    41 Jun 24 08:50 /home/softverse/phase2c-diagnostics/windows-poll-1.txt
-rw-r--r-- 1 softverse softverse    41 Jun 24 08:51 /home/softverse/phase2c-diagnostics/windows-poll-2.txt
-rw-r--r-- 1 softverse softverse  2374 Jun 24 08:52 /home/softverse/phase2c-diagnostics/xwininfo-final.txt

Open these screenshots to visually verify:
  explorer.exe ~/phase2c-diagnostics/screen-poll-4.png   (early - Login dialog)
  explorer.exe ~/phase2c-diagnostics/screen-poll-8.png   (mid-Phase-3)
  explorer.exe ~/phase2c-diagnostics/screen-final.png    (end state)
softverse@Softverse:~/phase2c-diagnostics$