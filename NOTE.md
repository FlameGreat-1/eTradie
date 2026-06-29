=== STAGE 7: race to the pod ===
Release: etradie-mt-2a44a12e-ee0
POD=etradie-mt-2a44a12e-ee0-0
[1] mt-node state: {"waiting":{"reason":"PodInitializing"}}
[2] mt-node state: {"waiting":{"reason":"PodInitializing"}}
[3] mt-node state: {"running":{"startedAt":"2026-06-28T09:09:20Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:5a3ba21f0ed5eed7ad15a48df0628be5e5c68254
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:5a3ba21f0ed5eed7ad15a48df0628be5e5c68254
=== STAGE 8: broker-bundle initContainer log ===
Downloading https://pub-5bdcacdedad6458298e8b8d5435f301a.r2.dev/broker-bundles/deriv-portable.zip...
/broker-bundle/bundle.zip: OK
Bundle extracted successfully.
Expect: 'Downloading ...exness-portable.zip', 'eadee9c7... OK', 'Bundle extracted successfully.'
=== STAGE 8b: discover MT_DIR (branded root) + MT_CONFIG_DIR ===
Entrypoint log did not yield MT_DIR; falling back to find().
Discovered MT_DIR: ''
WARN: could not discover branded MT root from log OR find(). Downstream
      on-disk asserts that need MT_DIR will be SKIPPED (not run against '/').
Discovered MT_CONFIG_DIR: ''
=== STAGE 9: tools + fluxbox EWMH ===
/usr/bin/xdotool
/usr/bin/xclip
/usr/bin/xprop
/usr/bin/xwd
/usr/bin/fluxbox
---
xclip version 0.13
=== STAGE 10: overlay normalizer + config-resolve log lines ===

Expect lines like:
  overlay-normalize(mt5): stripping baked Profiles/Charts workspace
  overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
  overlay-normalize(mt5): removing baked common.ini ...
  overlay-normalize(mt5): removing baked accounts.dat ...
  overlay-normalize: canonical config dir resolved to '<MT_DIR>/Config'
=== STAGE 10b: assert baked state was actually neutralized ===
SKIPPED: MT_DIR empty (see STAGE 8b WARN); not running ls against '/'.
=== STAGE 11: poll loop ===

===== poll 1/16  09:09:48 =====
etradie-mt-2a44a12e-ee0-0   2/3   Running   0     46s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 2/16  09:10:33 =====
etradie-mt-2a44a12e-ee0-0   2/3   Running   0     23s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T09:10:25Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-28T09:10:25Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-28T09:10:25Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/Config'
2026-06-28T09:10:25Z [INFO] overlay-normalize(mt5): stripping foreign [Common] account context from common.ini and enabling DLLs while preserving global settings
2026-06-28T09:10:25Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-28T09:10:25Z [INFO] auto_login: start (budget=420s, login=201415706, server=Deriv-Demo)
2026-06-28T09:10:25Z [INFO] auto_login: hard-kill watchdog armed (pid=201, fires at +450s)
2026-06-28T09:10:25Z [INFO] auto_login: terminal process detected at +0s
2026-06-28T09:10:25Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T09:10:27Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T09:10:30Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T09:10:32Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T09:10:34Z [INFO] auto_login: liveupdate-handler: no active window (skip)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  09:11:24 =====
etradie-mt-2a44a12e-ee0-0   2/3   Running   0     19s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T09:11:21Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-28T09:11:21Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-28T09:11:21Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/Config'
2026-06-28T09:11:21Z [INFO] overlay-normalize(mt5): stripping foreign [Common] account context from common.ini and enabling DLLs while preserving global settings
2026-06-28T09:11:21Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-28T09:11:21Z [INFO] auto_login: start (budget=420s, login=201415706, server=Deriv-Demo)
2026-06-28T09:11:21Z [INFO] auto_login: hard-kill watchdog armed (pid=197, fires at +450s)
2026-06-28T09:11:21Z [INFO] auto_login: terminal process detected at +0s
2026-06-28T09:11:21Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T09:11:23Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T09:11:26Z [INFO] auto_login: liveupdate-handler: no active window (skip)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  09:12:17 =====
etradie-mt-2a44a12e-ee0-0   0/3   Init:1/2   0     7s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  09:13:03 =====
etradie-mt-2a44a12e-ee0-0   2/3   Running   0     53s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

===== poll 6/16  09:13:47 =====
etradie-mt-2a44a12e-ee0-0   2/3   Running   0     41s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  09:14:29 =====
etradie-mt-2a44a12e-ee0-0   2/3   Running   0     18s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T09:14:25Z [INFO] auto_login: start (budget=420s, login=201415706, server=Deriv-Demo)
2026-06-28T09:14:25Z [INFO] auto_login: hard-kill watchdog armed (pid=181, fires at +450s)
2026-06-28T09:14:25Z [INFO] auto_login: terminal process detected at +0s
2026-06-28T09:14:25Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T09:14:27Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T09:14:29Z [INFO] auto_login: liveupdate-handler: no active window (skip)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 8/16  09:15:15 =====
etradie-mt-2a44a12e-ee0-0   0/3   Init:1/2   0     10s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  09:15:58 =====
etradie-mt-2a44a12e-ee0-0   2/3   Running   0     53s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T09:15:49Z [INFO] auto_login: login-auth wait +7s: active title='201415706 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T09:15:51Z [INFO] auto_login: login-auth wait +8s: active title='201415706 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T09:15:52Z [INFO] auto_login: login-auth wait +9s: active title='201415706 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T09:15:53Z [INFO] auto_login: login-auth wait +10s: active title='201415706 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T09:15:54Z [INFO] auto_login: login-auth wait +11s: active title='201415706 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T09:15:55Z [INFO] auto_login: login-auth wait +12s: active title='201415706 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T09:15:56Z [INFO] auto_login: login-auth wait +13s: active title='201415706 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T09:15:57Z [INFO] auto_login: login-auth wait +14s: active title='201415706 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T09:15:58Z [INFO] auto_login: login-auth wait +15s: active title='201415706 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T09:15:59Z [INFO] auto_login: login-auth wait +16s: active title='201415706 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T09:16:00Z [INFO] auto_login: login-auth wait +17s: active title='201415706 -   - Netting' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  09:16:43 =====
etradie-mt-2a44a12e-ee0-0   2/3   Running   0     32s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  09:17:25 =====
etradie-mt-2a44a12e-ee0-0   2/3   Running   0     18s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T09:17:22Z [INFO] auto_login: start (budget=420s, login=201415706, server=Deriv-Demo)
2026-06-28T09:17:22Z [INFO] auto_login: hard-kill watchdog armed (pid=185, fires at +450s)
2026-06-28T09:17:22Z [INFO] auto_login: terminal process detected at +0s
2026-06-28T09:17:22Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T09:17:24Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T09:17:26Z [INFO] auto_login: liveupdate-handler: no active window (skip)
--- :5555 LISTEN state (0A) ---
3148907 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 12/16  09:18:11 =====
etradie-mt-2a44a12e-ee0-0   2/3   Running   0     64s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

===== poll 13/16  09:18:51 =====
etradie-mt-2a44a12e-ee0-0   2/3   Running   0     105s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

===== poll 14/16  09:19:35 =====
etradie-mt-2a44a12e-ee0-0   2/3   Terminating   0     2m28s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

===== poll 15/16  09:20:18 =====
etradie-mt-2a44a12e-ee0-0   2/3   Terminating   0     3m11s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

===== poll 16/16  09:20:59 =====
Error from server (NotFound): pods "etradie-mt-2a44a12e-ee0-0" not found
POD GONE
=== STAGE 12: final artifacts ===
OK: screen-poll-01.png
OK: screen-poll-02.png
OK: screen-poll-03.png
OK: screen-poll-04.png
OK: screen-poll-06.png
OK: screen-poll-07.png
OK: screen-poll-08.png
OK: screen-poll-09.png
OK: screen-poll-10.png
OK: screen-poll-11.png
=== STAGE 13: verdict ===
Error from server (NotFound): pods "etradie-mt-2a44a12e-ee0-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-2a44a12e-ee0-0" not found
--- journal head/tail (broker handshake) ---
(MT_DIR empty; journal/EA log not collected)
...
(MT_DIR empty; journal/EA log not collected)
--- DB row ---
                  id                  | status |                                status_message                                | broker_id | broker_entity_id  | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------+------------+-----------
 2a44a12e-ee0d-413d-89da-6afb20a0c060 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | deriv     | deriv_com_limited |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260628T090637Z ===
total 17388
drwxr-xr-x  2 softverse softverse    4096 Jun 28 10:21 .
drwxr-xr-x 35 softverse softverse    4096 Jun 28 10:06 ..
-rw-r--r--  1 softverse softverse     110 Jun 28 10:21 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 28 10:21 driver-log-full.txt
-rw-r--r--  1 softverse softverse      45 Jun 28 10:21 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 28 10:07 engine-env.txt
-rw-r--r--  1 softverse softverse       1 Jun 28 10:09 mt-config-dir.txt
-rw-r--r--  1 softverse softverse       1 Jun 28 10:09 mt-dir.txt
-rw-r--r--  1 softverse softverse      45 Jun 28 10:21 mt5-journal.txt
-rw-r--r--  1 softverse softverse      71 Jun 28 10:09 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse       0 Jun 28 10:09 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 28 10:06 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 28 10:09 release.txt
-rw-r--r--  1 softverse softverse     278 Jun 28 10:21 screen-poll-01.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 10:10 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   74688 Jun 28 10:21 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 10:10 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse     278 Jun 28 10:21 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 10:11 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse     278 Jun 28 10:21 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 10:12 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   57657 Jun 28 10:21 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 10:13 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   55296 Jun 28 10:21 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 10:14 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse     278 Jun 28 10:21 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 10:15 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse   57691 Jun 28 10:21 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 10:16 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse   57732 Jun 28 10:21 screen-poll-10.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 10:16 screen-poll-10.xwd
-rw-r--r--  1 softverse softverse   10417 Jun 28 10:21 screen-poll-11.png
-rw-r--r--  1 softverse softverse 3148907 Jun 28 10:17 screen-poll-11.xwd
-rw-r--r--  1 softverse softverse      23 Jun 28 10:09 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 28 10:21 windows-final.txt
-rw-r--r--  1 softverse softverse      31 Jun 28 10:10 windows-poll-01.txt
-rw-r--r--  1 softverse softverse      41 Jun 28 10:10 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      41 Jun 28 10:11 windows-poll-03.txt
-rw-r--r--  1 softverse softverse       0 Jun 28 10:12 windows-poll-04.txt
-rw-r--r--  1 softverse softverse      94 Jun 28 10:13 windows-poll-05.txt
-rw-r--r--  1 softverse softverse      42 Jun 28 10:13 windows-poll-06.txt
-rw-r--r--  1 softverse softverse      42 Jun 28 10:14 windows-poll-07.txt
-rw-r--r--  1 softverse softverse      31 Jun 28 10:15 windows-poll-08.txt
-rw-r--r--  1 softverse softverse      94 Jun 28 10:16 windows-poll-09.txt
-rw-r--r--  1 softverse softverse      42 Jun 28 10:16 windows-poll-10.txt
-rw-r--r--  1 softverse softverse      65 Jun 28 10:17 windows-poll-11.txt
-rw-r--r--  1 softverse softverse      94 Jun 28 10:18 windows-poll-12.txt
-rw-r--r--  1 softverse softverse      94 Jun 28 10:19 windows-poll-13.txt
-rw-r--r--  1 softverse softverse      94 Jun 28 10:19 windows-poll-14.txt
-rw-r--r--  1 softverse softverse      94 Jun 28 10:20 windows-poll-15.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260628T090637Z
softverse@Softverse:~/hostedmt-diagnostics/20260628T090637Z