
   fd5f342d..baedb924  main -> main
softverse@Softverse:~/eTradie$ git pull gitlab main
remote: Enumerating objects: 5, done.
remote: Counting objects: 100% (5/5), done.
remote: Compressing objects: 100% (3/3), done.
remote: Total 3 (delta 1), reused 0 (delta 0), pack-reused 0 (from 0)
Unpacking objects: 100% (3/3), 3.32 KiB | 242.00 KiB/s, done.
From https://gitlab.com/intelli1344225/exoper
 * branch              main       -> FETCH_HEAD
   34b8acab..38daf306  main       -> gitlab/main
Merge made by the 'ort' strategy.
 LICENSE.txt | 273 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----------------------------------------------------------------------------
 1 file changed, 119 insertions(+), 154 deletions(-)
softverse@Softverse:~/eTradie$ # ─────────────────────────────────────────────────────────────────────
# Hosted-MT staging verification — post-!24 / !25 / !26 merge cycle
#
# Targets this round's two ground-truth questions:
#   (a) Does the recovery loop now correctly skip status='failed' rows?
#       (verified by !25 — fix(hosted-recovery): skip rows in terminal
#        status='failed' state)
#   (b) Does the broker-bundle initContainer + entrypoint.sh install
#       actually deliver Exness servers.dat into $MT_DIR/config/?
#       (verified by !26 — obs(mt-node): deterministic broker-bundle
#        install logging in entrypoint.sh)
#
# Captures evidence at every stage. Saves all artifacts to a timestamped
# directory so previous runs are not overwritten.
# ─────────────────────────────────────────────────────────────────────

set -u

# Timestamped diagnostic dir
TS=$(date -u +%Y%m%dT%H%M%SZ)
DIAG_DIR="$HOME/phase2c-diagnostics/${TS}"
mkdir -p "$DIAG_DIR"
cd "$DIAG_DIR"
echo "Diagnostic dir: $DIAG_DIR"
echo "(All screenshots, logs, and journal captures land here)"

# ────────────────────────────────────────────────────────────────────
# STAGE 0 — confirm CI has built new images
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 0 — confirm latest commits + CI image pin"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

cd ~/eTradie
git fetch origin main
git pull --rebase origin main
git log --oneline -12

  "SELECT id, status FROM broker_connections WHERE connection_type='hosted';"ling 2>/dev/null \est.v2+json" \
Diagnostic dir: /home/softverse/phase2c-diagnostics/20260625T074926Z
(All screenshots, logs, and journal captures land here)

==================================================================
STAGE 0 — confirm latest commits + CI image pin
==================================================================
[ TAKE A SCREENSHOT after this stage ]
remote: Enumerating objects: 27, done.
remote: Counting objects: 100% (27/27), done.
remote: Compressing objects: 100% (6/6), done.
remote: Total 17 (delta 11), reused 17 (delta 11), pack-reused 0 (from 0)
Unpacking objects: 100% (17/17), 10.94 KiB | 105.00 KiB/s, done.
From https://github.com/FlameGreat-1/eTradie
 * branch              main       -> FETCH_HEAD
   baedb924..d77bbe4a  main       -> origin/main
error: cannot pull with rebase: You have unstaged changes.
error: Please commit or stash them.
05d9c410 (HEAD -> main) Merge branch 'main' of https://gitlab.com/intelli1344225/exoper
38daf306 (gitlab/main) chore(license): replace LICENSE.txt with proprietary license
baedb924 Merge branch 'main' of https://gitlab.com/intelli1344225/exoper
34b8acab Merge branch 'fix/cosign-rekor-duplicate-signature' into 'main'
a2fb8f38 ci: tolerate cosign Rekor duplicate-signature 404 on re-runs
cb85ba5e Merge branch 'duo-edit-20260625-065156' into 'main'
93f20296 runbook(HOSTED-MT): clarify MDI title shapes + document pending fixes
fd5f342d Merge branch 'main' of https://github.com/FlameGreat-1/eTradie
84ad115c Merge branch 'main' of https://gitlab.com/intelli1344225/exoper
44f5b15a updated
cf01f862 Merge branch 'duo-edit-20260625-060956' into 'main'
ccba7726 obs(mt-node): deterministic broker-bundle install logging in entrypoint.sh

Confirm the TOP commit is 'ci: pin staging image tags to ...'
(without that bot commit the CI has not finished building the
new mt-node + engine images yet — DO NOT PROCEED until you see it)

Press Enter ONLY if you confirmed the CI image-pin commit is on top:

==================================================================
STAGE 1 — read pinned image SHAs from values-staging.yaml
==================================================================
[ TAKE A SCREENSHOT after this stage ]
Pinned image SHA (engine + mt-node share the tag): baedb924de7b6757e53d1b33d83130eaf896010d

==================================================================
STAGE 2 — verify mt-node + engine images exist on GHCR
==================================================================
[ TAKE A SCREENSHOT after this stage ]
mt-node manifest HTTP: 200 (expect 200)
engine  manifest HTTP: 200 (expect 200)

==================================================================
STAGE 3 — confirm K3s tunnel + force ArgoCD sync
==================================================================
[ TAKE A SCREENSHOT after this stage ]

Confirm the K3s SSH tunnel is alive in your second terminal.
Press Enter once the tunnel is alive:
NAME         STATUS   ROLES                  AGE   VERSION
vmi3362776   Ready    control-plane,master   11d   v1.30.4+k3s1
application.argoproj.io/engine-staging patched
application.argoproj.io/mt-node-staging patched

==================================================================
STAGE 4 — engine rollout + verify pinned image is live in-cluster
==================================================================
[ TAKE A SCREENSHOT after this stage ]
Waiting for deployment "etradie-engine" rollout to finish: 1 old replicas are pending termination...

Waiting for deployment "etradie-engine" rollout to finish: 1 old replicas are pending termination...
deployment "etradie-engine" successfully rolled out

--- engine env vars ---
ghcr.io/flamegreat-1/etradie/mt-node:baedb924de7b6757e53d1b33d83130eaf896010d
600
1200
1800

Expect MT_NODE_IMAGE to contain: baedb924de7b6757e53d1b33d83130eaf896010d
Expect MT_NODE_READINESS_TIMEOUT_SECS=600
Expect ENGINE_HOSTED_RECOVERY_UNHEALTHY_THRESHOLD_SECS=1200
Expect ENGINE_HOSTED_RECOVERY_FRESH_PROVISION_GRACE_SECS=1800

==================================================================
STAGE 5 — full cleanup
==================================================================
[ TAKE A SCREENSHOT after this stage ]

--- 5.1: drop hosted broker_connections rows ---
                  id                  | status
--------------------------------------+--------
 89660d92-9e35-42c3-8d89-a3d93fc87846 | failed
(1 row)

DELETE 1

--- 5.2: delete all mt-node K8s resources (PVC included this time) ---
persistentvolumeclaim "wine-prefix-etradie-mt-89660d92-9e3-0" deleted
serviceaccount "etradie-mt-89660d92-9e3" deleted
configmap "etradie-mt-89660d92-9e3-watchdog-config" deleted
service "etradie-mt-89660d92-9e3" deleted
service "etradie-mt-89660d92-9e3-headless" deleted
statefulset.apps "etradie-mt-89660d92-9e3" deleted

--- 5.3: force-remove finalizers on any stuck Terminating PVC ---

--- 5.4: clean Vault tenant paths for old releases ---
Success! Data deleted (if it existed) at: etradie/metadata/etradie/tenants/mt-node/etradie-mt-89660d92-9e3-0

--- 5.5: roll engine to invalidate per-user broker-client cache ---
deployment.apps/etradie-engine restarted
Waiting for deployment "etradie-engine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "etradie-engine" rollout to finish: 1 old replicas are pending termination...
deployment "etradie-engine" successfully rolled out

--- 5.6: verify clean state ---
No resources found in etradie-system namespace.
 id | status
----+--------
(0 rows)

softverse@Softverse:~/phase2c-diagnostics/20260625T074926Z$ # ────────────────────────────────────────────────────────────────────
# STAGE 6 — re-provision from dashboard
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 6 — RE-PROVISION FROM DASHBOARD NOW"
echo "=================================================================="
echo ""
echo "  Use Exness broker, primary entity, server Exness-MT5Real9,"
echo "  same login + password as before (133978149)."
echo ""
echo "  Press Enter the SECOND you click submit."
read -r
SUBMIT_TS=$(date -u +%H:%M:%S)
echo "Submit timestamp (UTC): $SUBMIT_TS" | tee submit-timestamp.txt

# ────────────────────────────────────────────────────────────────────
# STAGE 7 — race to the pod
# ────────────────────────────────────────────────────────────────────
echo ""
echo "=================================================================="
echo "STAGE 7 — race to the pod"
echo "=================================================================="
echo "[ TAKE A SCREENSHOT after this stage ]"

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
echo "REL=$REL" > release.txt
echo "POD=$POD" >> release.txt

for i in $(seq 1 60); do
  state=$(kubectl -n etradie-system get pod "$POD" \
echo "================================================================"="d-kill|exiting|BOTH paste and type failed|all three attempts failed' \" 2>/dev/null

==================================================================
STAGE 6 — RE-PROVISION FROM DASHBOARD NOW
==================================================================

  Use Exness broker, primary entity, server Exness-MT5Real9,
  same login + password as before (133978149).

  Press Enter the SECOND you click submit.

Submit timestamp (UTC): 07:54:59

==================================================================
STAGE 7 — race to the pod
==================================================================
[ TAKE A SCREENSHOT after this stage ]
Release: etradie-mt-e35d6bcd-e7d
POD=etradie-mt-e35d6bcd-e7d-0
[1] mt-node state: {"running":{"startedAt":"2026-06-25T07:54:36Z"}}

--- image of running mt-node container ---
ghcr.io/flamegreat-1/etradie/mt-node:baedb924de7b6757e53d1b33d83130eaf896010d
Expect: ghcr.io/flamegreat-1/etradie/mt-node:baedb924de7b6757e53d1b33d83130eaf896010d

==================================================================
-bash: !26: event not found
==================================================================
[ TAKE A SCREENSHOT after this stage ]

--- broker-bundle init log ---
Downloading https://pub-5bdcacdedad6458298e8b8d5435f301a.r2.dev/broker-bundles/exness-portable.zip...
/broker-bundle/bundle.zip: OK
Bundle extracted successfully.

Expected lines:
  Downloading https://pub-5bdcacde.../broker-bundles/exness-portable.zip...
  eadee9c7...  /broker-bundle/bundle.zip: OK
  Bundle extracted successfully.

==================================================================
STAGE 9 — tool availability + fluxbox EWMH readiness
==================================================================
[ TAKE A SCREENSHOT after this stage ]
/usr/bin/xdotool
/usr/bin/xclip
/usr/bin/xprop
/usr/bin/xwd
/usr/bin/fluxbox
---
xclip version 0.13

--- fluxbox + EWMH ---
2026-06-25T07:55:02Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-25T07:55:02Z [INFO] fluxbox ready (pid=189); _NET_ACTIVE_WINDOW available
2026-06-25T07:55:03Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-25T07:55:03Z [INFO] auto_login: hard-kill watchdog armed (pid=272, fires at +270s)
 _NET_ACTIVE_WINDOW

==================================================================
STAGE 10 — broker-bundle install log inside entrypoint.sh
==================================================================
[ TAKE A SCREENSHOT after this stage ]

--- broker-bundle install structured log lines ---
2026-06-25T07:55:02Z [INFO] broker-bundle volume present at /broker-bundle; top-level listing: total 12|drwxrwsrwx 3 root mt   4096 Jun 25 07:54 .|drwxr-xr-x 1 root root 4096 Jun 25 07:54 ..|drwxr-sr-x 9 mt   mt   4096 Jun 21 23:51 MetaTrader 5 EXNESS
2026-06-25T07:55:02Z [INFO] broker-bundle find for servers.dat matched 1 file(s):
2026-06-25T07:55:02Z [INFO]   - /broker-bundle/MetaTrader 5 EXNESS/Config/servers.dat
2026-06-25T07:55:02Z [INFO] Installed broker servers.dat from bundle (src='/broker-bundle/MetaTrader 5 EXNESS/Config/servers.dat', src_size=471796, dst='/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat', dst_size=471796, dst_sha256=9ad333071f3b45b61842dc672f1d93e32a5e730e53beb600ba807f0888d1b276)
2026-06-25T07:55:02Z [INFO] broker-bundle find for *.srv: no .srv companion files (this is normal for most brokers)
2026-06-25T07:55:02Z [INFO] broker-bundle install summary: servers_installed=1, srv_installed=0, final_servers_dat='/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat', final_servers_dat_size=471796

Expected (in order):
  1. 'broker-bundle volume present at /broker-bundle; top-level listing: ...'
  2. 'broker-bundle find for servers.dat matched N file(s)' followed by paths
  3. 'Installed broker servers.dat from bundle (src=..., dst=..., dst_size=...)'
  4. 'broker-bundle install summary: servers_installed=1, ...'

If ANY of those is missing the install path is broken and that is the bug.

==================================================================
STAGE 11 — 8-minute poll loop with per-poll screenshot
==================================================================
(Take screenshots periodically as you watch this loop)

============ poll 1 / 16  (07:55:21) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Running   0     60s

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T07:55:02Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-25T07:55:02Z [INFO] fluxbox ready (pid=189); _NET_ACTIVE_WINDOW available
2026-06-25T07:55:02Z [INFO] broker-bundle volume present at /broker-bundle; top-level listing: total 12|drwxrwsrwx 3 root mt   4096 Jun 25 07:54 .|drwxr-xr-x 1 root root 4096 Jun 25 07:54 ..|drwxr-sr-x 9 mt   mt   4096 Jun 21 23:51 MetaTrader 5 EXNESS
2026-06-25T07:55:02Z [INFO] broker-bundle find for servers.dat matched 1 file(s):
2026-06-25T07:55:02Z [INFO]   - /broker-bundle/MetaTrader 5 EXNESS/Config/servers.dat
2026-06-25T07:55:02Z [INFO] Installed broker servers.dat from bundle (src='/broker-bundle/MetaTrader 5 EXNESS/Config/servers.dat', src_size=471796, dst='/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat', dst_size=471796, dst_sha256=9ad333071f3b45b61842dc672f1d93e32a5e730e53beb600ba807f0888d1b276)
2026-06-25T07:55:02Z [INFO] broker-bundle find for *.srv: no .srv companion files (this is normal for most brokers)
2026-06-25T07:55:02Z [INFO] broker-bundle install summary: servers_installed=1, srv_installed=0, final_servers_dat='/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat', final_servers_dat_size=471796
2026-06-25T07:55:03Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-25T07:55:03Z [INFO] auto_login: hard-kill watchdog armed (pid=272, fires at +270s)
2026-06-25T07:55:03Z [INFO] auto_login: terminal process detected at +0s

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- servers.dat in MT_DIR (was bundle install successful?) ---
-rw-r--r-- 1 mt mt 472364 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat
28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b  /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat

--- capturing framebuffer (poll 1) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 2 / 16  (07:56:09) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Running   0     108s

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T07:55:02Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-25T07:55:02Z [INFO] fluxbox ready (pid=189); _NET_ACTIVE_WINDOW available
2026-06-25T07:55:02Z [INFO] broker-bundle volume present at /broker-bundle; top-level listing: total 12|drwxrwsrwx 3 root mt   4096 Jun 25 07:54 .|drwxr-xr-x 1 root root 4096 Jun 25 07:54 ..|drwxr-sr-x 9 mt   mt   4096 Jun 21 23:51 MetaTrader 5 EXNESS
2026-06-25T07:55:02Z [INFO] broker-bundle find for servers.dat matched 1 file(s):
2026-06-25T07:55:02Z [INFO]   - /broker-bundle/MetaTrader 5 EXNESS/Config/servers.dat
2026-06-25T07:55:02Z [INFO] Installed broker servers.dat from bundle (src='/broker-bundle/MetaTrader 5 EXNESS/Config/servers.dat', src_size=471796, dst='/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat', dst_size=471796, dst_sha256=9ad333071f3b45b61842dc672f1d93e32a5e730e53beb600ba807f0888d1b276)
2026-06-25T07:55:02Z [INFO] broker-bundle find for *.srv: no .srv companion files (this is normal for most brokers)
2026-06-25T07:55:02Z [INFO] broker-bundle install summary: servers_installed=1, srv_installed=0, final_servers_dat='/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat', final_servers_dat_size=471796
2026-06-25T07:55:03Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-25T07:55:03Z [INFO] auto_login: hard-kill watchdog armed (pid=272, fires at +270s)
2026-06-25T07:55:03Z [INFO] auto_login: terminal process detected at +0s
2026-06-25T07:55:34Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-25T07:55:34Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-25T07:55:34Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-25T07:55:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:55:37Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s
2026-06-25T07:55:37Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-25T07:55:38Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-25T07:55:38Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-25T07:55:38Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-25T07:55:39Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-25T07:55:39Z [INFO] auto_login: deliver login: paste succeeded
2026-06-25T07:55:39Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:40Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-25T07:55:40Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T07:55:41Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T07:55:41Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T07:55:41Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T07:55:43Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T07:55:43Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T07:55:45Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T07:55:45Z [INFO] auto_login: clipboard scrubbed
2026-06-25T07:55:45Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- servers.dat in MT_DIR (was bundle install successful?) ---
-rw-r--r-- 1 mt mt 472364 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat
28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b  /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat

--- capturing framebuffer (poll 2) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 3 / 16  (07:56:56) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Running   0     2m34s

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T07:55:03Z [INFO] auto_login: hard-kill watchdog armed (pid=272, fires at +270s)
2026-06-25T07:55:03Z [INFO] auto_login: terminal process detected at +0s
2026-06-25T07:55:34Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-25T07:55:34Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-25T07:55:34Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-25T07:55:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:55:37Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s
2026-06-25T07:55:37Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-25T07:55:38Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-25T07:55:38Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-25T07:55:38Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-25T07:55:39Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-25T07:55:39Z [INFO] auto_login: deliver login: paste succeeded
2026-06-25T07:55:39Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:40Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-25T07:55:40Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T07:55:41Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T07:55:41Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T07:55:41Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T07:55:43Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T07:55:43Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T07:55:45Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T07:55:45Z [INFO] auto_login: clipboard scrubbed
2026-06-25T07:55:45Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-25T07:56:12Z [INFO] auto_login: phase5: settle early-exit at +26s (Welcome modal observed); proceeding to keystroke cascade
2026-06-25T07:56:12Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-25T07:56:12Z [INFO] auto_login: blocking modal detected (WID=12582941, NAME=Welcome to LiveUpdate); attempting dismiss
2026-06-25T07:56:13Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:56:13Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-25T07:56:36Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-25T07:56:41Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-25T07:56:41Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:56:42Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- servers.dat in MT_DIR (was bundle install successful?) ---
-rw-r--r-- 1 mt mt 472364 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat
28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b  /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat

--- capturing framebuffer (poll 3) ---
3148907 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 4 / 16  (07:57:42) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Running   0     3m21s

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T07:55:39Z [INFO] auto_login: deliver login: paste succeeded
2026-06-25T07:55:39Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:40Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-25T07:55:40Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T07:55:41Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T07:55:41Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T07:55:41Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T07:55:43Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T07:55:43Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T07:55:45Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T07:55:45Z [INFO] auto_login: clipboard scrubbed
2026-06-25T07:55:45Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-25T07:56:12Z [INFO] auto_login: phase5: settle early-exit at +26s (Welcome modal observed); proceeding to keystroke cascade
2026-06-25T07:56:12Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-25T07:56:12Z [INFO] auto_login: blocking modal detected (WID=12582941, NAME=Welcome to LiveUpdate); attempting dismiss
2026-06-25T07:56:13Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:56:13Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-25T07:56:36Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-25T07:56:41Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-25T07:56:41Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:56:42Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-25T07:57:06Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-25T07:57:11Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-25T07:57:11Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:12Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:14Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-25T07:57:15Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-25T07:57:37Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-25T07:57:37Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-25T07:57:37Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- servers.dat in MT_DIR (was bundle install successful?) ---
-rw-r--r-- 1 mt mt 472364 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat
28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b  /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat

--- capturing framebuffer (poll 4) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 5 / 16  (07:58:29) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Running   0     4m8s

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T07:55:39Z [INFO] auto_login: deliver login: paste succeeded
2026-06-25T07:55:39Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:40Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-25T07:55:40Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T07:55:41Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T07:55:41Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T07:55:41Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T07:55:43Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T07:55:43Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T07:55:45Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T07:55:45Z [INFO] auto_login: clipboard scrubbed
2026-06-25T07:55:45Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-25T07:56:12Z [INFO] auto_login: phase5: settle early-exit at +26s (Welcome modal observed); proceeding to keystroke cascade
2026-06-25T07:56:12Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-25T07:56:12Z [INFO] auto_login: blocking modal detected (WID=12582941, NAME=Welcome to LiveUpdate); attempting dismiss
2026-06-25T07:56:13Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:56:13Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-25T07:56:36Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-25T07:56:41Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-25T07:56:41Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:56:42Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-25T07:57:06Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-25T07:57:11Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-25T07:57:11Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:12Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:14Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-25T07:57:15Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-25T07:57:37Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-25T07:57:37Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-25T07:57:37Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- servers.dat in MT_DIR (was bundle install successful?) ---
-rw-r--r-- 1 mt mt 472364 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat
28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b  /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat

--- capturing framebuffer (poll 5) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 6 / 16  (07:59:20) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Running   0     5m1s

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T07:55:39Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:40Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-25T07:55:40Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T07:55:41Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T07:55:41Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T07:55:41Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T07:55:43Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T07:55:43Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T07:55:45Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T07:55:45Z [INFO] auto_login: clipboard scrubbed
2026-06-25T07:55:45Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-25T07:56:12Z [INFO] auto_login: phase5: settle early-exit at +26s (Welcome modal observed); proceeding to keystroke cascade
2026-06-25T07:56:12Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-25T07:56:12Z [INFO] auto_login: blocking modal detected (WID=12582941, NAME=Welcome to LiveUpdate); attempting dismiss
2026-06-25T07:56:13Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:56:13Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-25T07:56:36Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-25T07:56:41Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-25T07:56:41Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:56:42Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-25T07:57:06Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-25T07:57:11Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-25T07:57:11Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:12Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:14Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-25T07:57:15Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-25T07:57:37Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-25T07:57:37Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-25T07:57:37Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-25T07:59:03Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- servers.dat in MT_DIR (was bundle install successful?) ---
-rw-r--r-- 1 mt mt 472364 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat
28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b  /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat

--- capturing framebuffer (poll 6) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 7 / 16  (08:00:11) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Running   0     5m50s

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T07:55:40Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-25T07:55:40Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T07:55:41Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T07:55:41Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T07:55:41Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-25T07:55:42Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T07:55:43Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T07:55:43Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-25T07:55:43Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-25T07:55:44Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T07:55:45Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T07:55:45Z [INFO] auto_login: clipboard scrubbed
2026-06-25T07:55:45Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-25T07:56:12Z [INFO] auto_login: phase5: settle early-exit at +26s (Welcome modal observed); proceeding to keystroke cascade
2026-06-25T07:56:12Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-25T07:56:12Z [INFO] auto_login: blocking modal detected (WID=12582941, NAME=Welcome to LiveUpdate); attempting dismiss
2026-06-25T07:56:13Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:56:13Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-25T07:56:36Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-25T07:56:41Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-25T07:56:41Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T07:56:42Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-25T07:57:06Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-25T07:57:11Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-25T07:57:11Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:12Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:14Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-25T07:57:15Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-25T07:57:37Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-25T07:57:37Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-25T07:57:37Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-25T07:59:03Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-25T08:00:06Z [WARN] MetaTrader exited with code 143

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- servers.dat in MT_DIR (was bundle install successful?) ---
-rw-r--r-- 1 mt mt 472364 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat
28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b  /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat

--- capturing framebuffer (poll 7) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 8 / 16  (08:01:11) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Running   0     6m50s

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T07:57:11Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:12Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:14Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-25T07:57:15Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-25T07:57:37Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-25T07:57:37Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-25T07:57:37Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-25T07:59:03Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-25T08:00:06Z [WARN] MetaTrader exited with code 143
2026-06-25T08:00:36Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-25T08:00:36Z [INFO] auto_login: hard-kill watchdog armed (pid=2232, fires at +270s)
2026-06-25T08:00:36Z [INFO] auto_login: terminal process detected at +0s
2026-06-25T08:00:47Z [INFO] auto_login: Login dialog WID=12582936 detected at +11s
2026-06-25T08:00:47Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-25T08:00:49Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-25T08:00:50Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-25T08:00:50Z [INFO] auto_login: deliver login: paste succeeded
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T08:00:51Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T08:00:51Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T08:00:51Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T08:00:53Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T08:00:53Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T08:00:53Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T08:00:55Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T08:00:55Z [INFO] auto_login: clipboard scrubbed
2026-06-25T08:00:55Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 25 08:00 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- servers.dat in MT_DIR (was bundle install successful?) ---
-rw-r--r-- 1 mt mt 472364 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat
28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b  /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat

--- capturing framebuffer (poll 8) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 9 / 16  (08:02:01) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Running   0     7m40s

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T07:57:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-25T07:57:14Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-25T07:57:15Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-25T07:57:37Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-25T07:57:37Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-25T07:57:37Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-25T07:59:03Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-25T08:00:06Z [WARN] MetaTrader exited with code 143
2026-06-25T08:00:36Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-25T08:00:36Z [INFO] auto_login: hard-kill watchdog armed (pid=2232, fires at +270s)
2026-06-25T08:00:36Z [INFO] auto_login: terminal process detected at +0s
2026-06-25T08:00:47Z [INFO] auto_login: Login dialog WID=12582936 detected at +11s
2026-06-25T08:00:47Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-25T08:00:49Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-25T08:00:50Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-25T08:00:50Z [INFO] auto_login: deliver login: paste succeeded
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T08:00:51Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T08:00:51Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T08:00:51Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T08:00:53Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T08:00:53Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T08:00:53Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T08:00:55Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T08:00:55Z [INFO] auto_login: clipboard scrubbed
2026-06-25T08:00:55Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-25T08:01:58Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-25T08:01:58Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 25 08:00 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- servers.dat in MT_DIR (was bundle install successful?) ---
-rw-r--r-- 1 mt mt 472364 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat
28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b  /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat

--- capturing framebuffer (poll 9) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 10 / 16  (08:03:02) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Running   0     8m41s

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T08:00:36Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-25T08:00:36Z [INFO] auto_login: hard-kill watchdog armed (pid=2232, fires at +270s)
2026-06-25T08:00:36Z [INFO] auto_login: terminal process detected at +0s
2026-06-25T08:00:47Z [INFO] auto_login: Login dialog WID=12582936 detected at +11s
2026-06-25T08:00:47Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-25T08:00:49Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-25T08:00:50Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-25T08:00:50Z [INFO] auto_login: deliver login: paste succeeded
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T08:00:51Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T08:00:51Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T08:00:51Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T08:00:53Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T08:00:53Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T08:00:53Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T08:00:55Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T08:00:55Z [INFO] auto_login: clipboard scrubbed
2026-06-25T08:00:55Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-25T08:01:58Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-25T08:01:58Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-25T08:02:21Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-25T08:02:26Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-25T08:02:26Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:02:27Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-25T08:02:51Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-25T08:02:56Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-25T08:02:56Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:02:57Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 25 08:00 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- servers.dat in MT_DIR (was bundle install successful?) ---
-rw-r--r-- 1 mt mt 472364 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat
28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b  /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat

--- capturing framebuffer (poll 10) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 11 / 16  (08:03:59) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Running   0     9m38s

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T08:00:47Z [INFO] auto_login: Login dialog WID=12582936 detected at +11s
2026-06-25T08:00:47Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-25T08:00:49Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-25T08:00:50Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-25T08:00:50Z [INFO] auto_login: deliver login: paste succeeded
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T08:00:51Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T08:00:51Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T08:00:51Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T08:00:53Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T08:00:53Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T08:00:53Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T08:00:55Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T08:00:55Z [INFO] auto_login: clipboard scrubbed
2026-06-25T08:00:55Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-25T08:01:58Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-25T08:01:58Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-25T08:02:21Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-25T08:02:26Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-25T08:02:26Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:02:27Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-25T08:02:51Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-25T08:02:56Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-25T08:02:56Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:02:57Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-25T08:03:19Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-25T08:03:19Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-25T08:03:19Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 25 08:00 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- servers.dat in MT_DIR (was bundle install successful?) ---
-rw-r--r-- 1 mt mt 472364 Jun 25 07:55 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat
28ac48adebcbcd4c41b13806c749f09bafc90bff2b2c72c3a00a907be509083b  /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/servers.dat

--- capturing framebuffer (poll 11) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 12 / 16  (08:05:02) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Terminating   0     10m

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-25T08:00:49Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-25T08:00:50Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-25T08:00:50Z [INFO] auto_login: deliver login: paste succeeded
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T08:00:51Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T08:00:51Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T08:00:51Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T08:00:53Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T08:00:53Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T08:00:53Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T08:00:55Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T08:00:55Z [INFO] auto_login: clipboard scrubbed
2026-06-25T08:00:55Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-25T08:01:58Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-25T08:01:58Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-25T08:02:21Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-25T08:02:26Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-25T08:02:26Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:02:27Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-25T08:02:51Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-25T08:02:56Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-25T08:02:56Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:02:57Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-25T08:03:19Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-25T08:03:19Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-25T08:03:19Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-25T08:04:37Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-25T08:04:54Z [INFO] Caught shutdown signal, terminating auto-login driver + MetaTrader + fluxbox + Xvfb

--- :5555 socket state ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- accounts.dat presence ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- MQL5/Logs (EA OnInit ran?) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- servers.dat in MT_DIR (was bundle install successful?) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- capturing framebuffer (poll 12) ---

============ poll 13 / 16  (08:05:49) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Terminating   0     11m

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-25T08:00:49Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-25T08:00:50Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-25T08:00:50Z [INFO] auto_login: deliver login: paste succeeded
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T08:00:51Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T08:00:51Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T08:00:51Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T08:00:53Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T08:00:53Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T08:00:53Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T08:00:55Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T08:00:55Z [INFO] auto_login: clipboard scrubbed
2026-06-25T08:00:55Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-25T08:01:58Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-25T08:01:58Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-25T08:02:21Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-25T08:02:26Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-25T08:02:26Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:02:27Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-25T08:02:51Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-25T08:02:56Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-25T08:02:56Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:02:57Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-25T08:03:19Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-25T08:03:19Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-25T08:03:19Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-25T08:04:37Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-25T08:04:54Z [INFO] Caught shutdown signal, terminating auto-login driver + MetaTrader + fluxbox + Xvfb

--- :5555 socket state ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- accounts.dat presence ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- MQL5/Logs (EA OnInit ran?) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- servers.dat in MT_DIR (was bundle install successful?) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- capturing framebuffer (poll 13) ---

============ poll 14 / 16  (08:06:37) ============
etradie-mt-e35d6bcd-e7d-0   2/3   Terminating   0     12m

--- driver log (auto_login + paste/type + phase5 + broker-bundle) ---
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-25T08:00:48Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-25T08:00:49Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-25T08:00:50Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-25T08:00:50Z [INFO] auto_login: deliver login: paste succeeded
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-25T08:00:50Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-25T08:00:51Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-25T08:00:51Z [INFO] auto_login: deliver password: paste succeeded
2026-06-25T08:00:51Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-25T08:00:52Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-25T08:00:53Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-25T08:00:53Z [INFO] auto_login: deliver server: paste succeeded
2026-06-25T08:00:53Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-25T08:00:54Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-25T08:00:55Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-25T08:00:55Z [INFO] auto_login: clipboard scrubbed
2026-06-25T08:00:55Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-25T08:01:58Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-25T08:01:58Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:01:58Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-25T08:02:21Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-25T08:02:26Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-25T08:02:26Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:02:27Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-25T08:02:51Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-25T08:02:56Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-25T08:02:56Z [INFO] auto_login: main window is active; modals cleared
2026-06-25T08:02:57Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-25T08:03:19Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-25T08:03:19Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-25T08:03:19Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-25T08:04:37Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-25T08:04:54Z [INFO] Caught shutdown signal, terminating auto-login driver + MetaTrader + fluxbox + Xvfb

--- :5555 socket state ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- accounts.dat presence ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- MQL5/Logs (EA OnInit ran?) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- servers.dat in MT_DIR (was bundle install successful?) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- capturing framebuffer (poll 14) ---

============ poll 15 / 16  (08:07:28) ============
Error from server (NotFound): pods "etradie-mt-e35d6bcd-e7d-0" not found
POD GONE

==================================================================
STAGE 12 — final artifacts
==================================================================
[ TAKE A SCREENSHOT after this stage ]
driver-log-full.txt: 1 lines
broker-bundle-init.log: 1 lines
mt5-journal.txt: 1 lines
ea-log.txt: 1 lines
Error from server (NotFound): pods "etradie-mt-e35d6bcd-e7d-0" not found

--- converting screenshots ---
OK: screen-poll-01.png (13654 bytes)
OK: screen-poll-02.png (3745 bytes)
OK: screen-poll-03.png (20851 bytes)
OK: screen-poll-04.png (3691 bytes)
OK: screen-poll-05.png (3691 bytes)
OK: screen-poll-06.png (3691 bytes)
OK: screen-poll-07.png (278 bytes)
OK: screen-poll-08.png (3691 bytes)
OK: screen-poll-09.png (3745 bytes)
OK: screen-poll-10.png (3691 bytes)
OK: screen-poll-11.png (3691 bytes)

==================================================================
STAGE 13 — verdict
==================================================================
[ TAKE A SCREENSHOT after this stage ]

--- pod state ---
Error from server (NotFound): pods "etradie-mt-e35d6bcd-e7d-0" not found

--- accounts.dat (Phase 3 succeeded?) ---
Error from server (NotFound): pods "etradie-mt-e35d6bcd-e7d-0" not found

--- MQL5/Logs (EA OnInit ran?) ---
Error from server (NotFound): pods "etradie-mt-e35d6bcd-e7d-0" not found

--- :5555 socket (the goal) ---
Error from server (NotFound): pods "etradie-mt-e35d6bcd-e7d-0" not found

--- MT5 journal head + tail (broker handshake?) ---
Error from server (NotFound): pods "etradie-mt-e35d6bcd-e7d-0" not found
...
Error from server (NotFound): pods "etradie-mt-e35d6bcd-e7d-0" not found

--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 e35d6bcd-e7d5-451b-b632-96886064152e | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)


==================================================================
STAGE 14 — driver sentinels (mapped to runbook §D decision tree)
==================================================================
[ TAKE A SCREENSHOT after this stage ]

-bash: !26: event not found

--- fluxbox readiness ---

--- Welcome modal handling ---

--- Phase 2c (Login dialog open) ---

--- Phase 3 strategy + per-field outcome ---

--- Phase 3 stage transitions ---

--- Phase 5 (chart attach) ---

--- Final outcome (success or failure mode) ---

==================================================================
STAGE 15 — diagnostic files in /home/softverse/phase2c-diagnostics/20260625T074926Z
==================================================================
[ TAKE A SCREENSHOT after this stage ]
total 18644
drwxr-xr-x 2 softverse softverse    4096 Jun 25 09:07 .
drwxr-xr-x 3 softverse softverse    4096 Jun 25 08:49 ..
-rw-r--r-- 1 softverse softverse     110 Jun 25 09:07 broker-bundle-init.log
-rw-r--r-- 1 softverse softverse    1085 Jun 25 08:55 broker-bundle-install.log
-rw-r--r-- 1 softverse softverse     110 Jun 25 09:07 driver-log-full.txt
-rw-r--r-- 1 softverse softverse      73 Jun 25 09:07 ea-log.txt
-rw-r--r-- 1 softverse softverse      73 Jun 25 09:07 mt5-journal.txt
-rw-r--r-- 1 softverse softverse      58 Jun 25 08:55 release.txt
-rw-r--r-- 1 softverse softverse   13654 Jun 25 09:07 screen-poll-01.png
-rw-r--r-- 1 softverse softverse 1573739 Jun 25 08:55 screen-poll-01.xwd
-rw-r--r-- 1 softverse softverse    3745 Jun 25 09:07 screen-poll-02.png
-rw-r--r-- 1 softverse softverse 1573739 Jun 25 08:56 screen-poll-02.xwd
-rw-r--r-- 1 softverse softverse   20851 Jun 25 09:07 screen-poll-03.png
-rw-r--r-- 1 softverse softverse 3148907 Jun 25 08:57 screen-poll-03.xwd
-rw-r--r-- 1 softverse softverse    3691 Jun 25 09:07 screen-poll-04.png
-rw-r--r-- 1 softverse softverse 1573739 Jun 25 08:57 screen-poll-04.xwd
-rw-r--r-- 1 softverse softverse    3691 Jun 25 09:07 screen-poll-05.png
-rw-r--r-- 1 softverse softverse 1573739 Jun 25 08:58 screen-poll-05.xwd
-rw-r--r-- 1 softverse softverse    3691 Jun 25 09:07 screen-poll-06.png
-rw-r--r-- 1 softverse softverse 1573739 Jun 25 08:59 screen-poll-06.xwd
-rw-r--r-- 1 softverse softverse     278 Jun 25 09:07 screen-poll-07.png
-rw-r--r-- 1 softverse softverse 1573739 Jun 25 09:00 screen-poll-07.xwd
-rw-r--r-- 1 softverse softverse    3691 Jun 25 09:07 screen-poll-08.png
-rw-r--r-- 1 softverse softverse 1573739 Jun 25 09:01 screen-poll-08.xwd
-rw-r--r-- 1 softverse softverse    3745 Jun 25 09:07 screen-poll-09.png
-rw-r--r-- 1 softverse softverse 1573739 Jun 25 09:02 screen-poll-09.xwd
-rw-r--r-- 1 softverse softverse    3691 Jun 25 09:07 screen-poll-10.png
-rw-r--r-- 1 softverse softverse 1573739 Jun 25 09:03 screen-poll-10.xwd
-rw-r--r-- 1 softverse softverse    3691 Jun 25 09:07 screen-poll-11.png
-rw-r--r-- 1 softverse softverse 1573739 Jun 25 09:04 screen-poll-11.xwd
-rw-r--r-- 1 softverse softverse      33 Jun 25 08:54 submit-timestamp.txt
-rw-r--r-- 1 softverse softverse      73 Jun 25 09:07 windows-final.txt
-rw-r--r-- 1 softverse softverse      65 Jun 25 08:55 windows-poll-01.txt
-rw-r--r-- 1 softverse softverse      42 Jun 25 08:56 windows-poll-02.txt
-rw-r--r-- 1 softverse softverse      65 Jun 25 08:57 windows-poll-03.txt
-rw-r--r-- 1 softverse softverse      42 Jun 25 08:57 windows-poll-04.txt
-rw-r--r-- 1 softverse softverse      42 Jun 25 08:58 windows-poll-05.txt
-rw-r--r-- 1 softverse softverse      42 Jun 25 08:59 windows-poll-06.txt
-rw-r--r-- 1 softverse softverse       0 Jun 25 09:00 windows-poll-07.txt
-rw-r--r-- 1 softverse softverse      42 Jun 25 09:01 windows-poll-08.txt
-rw-r--r-- 1 softverse softverse      42 Jun 25 09:02 windows-poll-09.txt
-rw-r--r-- 1 softverse softverse      42 Jun 25 09:03 windows-poll-10.txt
-rw-r--r-- 1 softverse softverse      42 Jun 25 09:04 windows-poll-11.txt
-rw-r--r-- 1 softverse softverse      94 Jun 25 09:05 windows-poll-12.txt
-rw-r--r-- 1 softverse softverse      94 Jun 25 09:06 windows-poll-13.txt
-rw-r--r-- 1 softverse softverse      94 Jun 25 09:06 windows-poll-14.txt

================================================================
Screenshots to review:
================================================================
  explorer.exe /home/softverse/phase2c-diagnostics/20260625T074926Z/screen-poll-01.png
  explorer.exe /home/softverse/phase2c-diagnostics/20260625T074926Z/screen-poll-02.png
  explorer.exe /home/softverse/phase2c-diagnostics/20260625T074926Z/screen-poll-03.png
  explorer.exe /home/softverse/phase2c-diagnostics/20260625T074926Z/screen-poll-04.png
  explorer.exe /home/softverse/phase2c-diagnostics/20260625T074926Z/screen-poll-05.png
  explorer.exe /home/softverse/phase2c-diagnostics/20260625T074926Z/screen-poll-06.png
  explorer.exe /home/softverse/phase2c-diagnostics/20260625T074926Z/screen-poll-07.png
  explorer.exe /home/softverse/phase2c-diagnostics/20260625T074926Z/screen-poll-08.png
  explorer.exe /home/softverse/phase2c-diagnostics/20260625T074926Z/screen-poll-09.png
  explorer.exe /home/softverse/phase2c-diagnostics/20260625T074926Z/screen-poll-10.png
  explorer.exe /home/softverse/phase2c-diagnostics/20260625T074926Z/screen-poll-11.png

================================================================
DONE. Diagnostic dir: /home/softverse/phase2c-diagnostics/20260625T074926Z
================================================================
softverse@Softverse:~/phase2c-diagnostics/20260625T074926Z$