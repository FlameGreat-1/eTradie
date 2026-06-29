=== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 07:46:22
=== STAGE 7: race to the pod ===
Release: etradie-mt-8d759d57-870
POD=etradie-mt-8d759d57-870-0
[1] mt-node state: {"waiting":{"reason":"PodInitializing"}}
[2] mt-node state: {"running":{"startedAt":"2026-06-28T07:46:27Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:86a8004a63699af10d373db2609d6d0b14eabc49
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:86a8004a63699af10d373db2609d6d0b14eabc49
=== STAGE 8: broker-bundle initContainer log ===
Downloading https://pub-5bdcacdedad6458298e8b8d5435f301a.r2.dev/broker-bundles/exness-portable.zip...
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

===== poll 1/16  07:46:55 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     44s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---

===== poll 2/16  07:47:38 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     88s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:47:08Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-28T07:47:08Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-28T07:47:08Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-28T07:47:08Z [INFO] overlay-normalize(mt5): scrubbing baked common.ini (removing foreign account context while preserving global expert settings)
2026-06-28T07:47:08Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-28T07:47:09Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-28T07:47:09Z [INFO] auto_login: hard-kill watchdog armed (pid=355, fires at +450s)
2026-06-28T07:47:09Z [INFO] auto_login: terminal process detected at +1s
2026-06-28T07:47:09Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:47:11Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:47:13Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:47:15Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:47:17Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:47:20Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:47:22Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:47:24Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:47:26Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:47:28Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T07:47:30Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T07:47:32Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T07:47:35Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T07:47:37Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T07:47:39Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T07:47:39Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-28T07:47:39Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-28T07:47:39Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-28T07:47:39Z [INFO] auto_login: main window is active; modals cleared
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  07:48:23 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     2m13s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:47:46Z [INFO] auto_login: deliver password: paste succeeded
2026-06-28T07:47:46Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-28T07:47:47Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-28T07:47:47Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-28T07:47:48Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-28T07:47:48Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T07:47:49Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T07:47:49Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T07:47:49Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T07:47:49Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T07:47:49Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T07:47:50Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T07:47:50Z [INFO] auto_login: clipboard scrubbed
2026-06-28T07:47:50Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:52Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:53Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:54Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:55Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:57Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:58Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:59Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:00Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:01Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:02Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:03Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:04Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:05Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:07Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:08Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:09Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:10Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:11Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:12Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:13Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:14Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:15Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:17Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:19Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:20Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:21Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:22Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:23Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:24Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:25Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:26Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  07:49:14 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     3m3s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:47:47Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-28T07:47:48Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-28T07:47:48Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T07:47:49Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T07:47:49Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T07:47:49Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T07:47:49Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T07:47:49Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T07:47:50Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T07:47:50Z [INFO] auto_login: clipboard scrubbed
2026-06-28T07:47:50Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:52Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:53Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:54Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:55Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:57Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:58Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:59Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:00Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:01Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:02Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:03Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:04Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:05Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:07Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:08Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:09Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:10Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:11Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:12Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:13Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:14Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:15Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:17Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:19Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:20Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:21Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:22Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:23Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:24Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:25Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:26Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:27Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:28Z [INFO] auto_login: login confirmed via journal at +33s: QE 0       07:47:52.885    Network '133978149': trading has been enabled - hedging mode
2026-06-28T07:48:28Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  07:50:02 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     3m51s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:47:48Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T07:47:49Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T07:47:49Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T07:47:49Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T07:47:49Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T07:47:49Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T07:47:50Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T07:47:50Z [INFO] auto_login: clipboard scrubbed
2026-06-28T07:47:50Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:52Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:53Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:54Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:55Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:57Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:58Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:59Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:00Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:01Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:02Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:03Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:04Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:05Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:07Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:08Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:09Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:10Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:11Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:12Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:13Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:14Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:15Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:17Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:19Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:20Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:21Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:22Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:23Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:24Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:25Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:26Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:27Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:28Z [INFO] auto_login: login confirmed via journal at +33s: QE 0       07:47:52.885    Network '133978149': trading has been enabled - hedging mode
2026-06-28T07:48:28Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T07:49:30Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T07:49:30Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  07:50:46 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     4m36s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:47:50Z [INFO] auto_login: clipboard scrubbed
2026-06-28T07:47:50Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:52Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:53Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:54Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:55Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:57Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:58Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:59Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:00Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:01Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:02Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:03Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:04Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:05Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:07Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:08Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:09Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:10Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:11Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:12Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:13Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:14Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:15Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:17Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:19Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:20Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:21Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:22Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:23Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:24Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:25Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:26Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:27Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:28Z [INFO] auto_login: login confirmed via journal at +33s: QE 0       07:47:52.885    Network '133978149': trading has been enabled - hedging mode
2026-06-28T07:48:28Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T07:49:30Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T07:49:30Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T07:50:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T07:50:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T07:50:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T07:50:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T07:50:44Z [INFO] auto_login: phase5: BEFORE typing template, active window is WID=12582949 NAME='Open'
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  07:51:31 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     5m21s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:47:52Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:53Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:54Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:55Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:57Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:58Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:59Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:00Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:01Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:02Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:03Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:04Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:05Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:07Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:08Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:09Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:10Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:11Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:12Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:13Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:14Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:15Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:17Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:19Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:20Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:21Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:22Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:23Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:24Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:25Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:26Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:27Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:28Z [INFO] auto_login: login confirmed via journal at +33s: QE 0       07:47:52.885    Network '133978149': trading has been enabled - hedging mode
2026-06-28T07:48:28Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T07:49:30Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T07:49:30Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T07:50:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T07:50:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T07:50:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T07:50:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T07:50:44Z [INFO] auto_login: phase5: BEFORE typing template, active window is WID=12582949 NAME='Open'
2026-06-28T07:51:18Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T07:51:18Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 8/16  07:52:21 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     6m10s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:47:52Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:53Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:54Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:55Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:57Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:58Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:59Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:00Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:01Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:02Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:03Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:04Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:05Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:07Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:08Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:09Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:10Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:11Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:12Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:13Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:14Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:15Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:17Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:19Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:20Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:21Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:22Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:23Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:24Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:25Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:26Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:27Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:28Z [INFO] auto_login: login confirmed via journal at +33s: QE 0       07:47:52.885    Network '133978149': trading has been enabled - hedging mode
2026-06-28T07:48:28Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T07:49:30Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T07:49:30Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T07:50:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T07:50:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T07:50:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T07:50:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T07:50:44Z [INFO] auto_login: phase5: BEFORE typing template, active window is WID=12582949 NAME='Open'
2026-06-28T07:51:18Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T07:51:18Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  07:53:04 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     6m54s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:47:52Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:53Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:54Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:55Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:57Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:58Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:59Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:00Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:01Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:02Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:03Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:04Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:05Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:07Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:08Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:09Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:10Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:11Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:12Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:13Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:14Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:15Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:17Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:19Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:20Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:21Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:22Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:23Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:24Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:25Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:26Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:27Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:28Z [INFO] auto_login: login confirmed via journal at +33s: QE 0       07:47:52.885    Network '133978149': trading has been enabled - hedging mode
2026-06-28T07:48:28Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T07:49:30Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T07:49:30Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T07:50:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T07:50:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T07:50:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T07:50:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T07:50:44Z [INFO] auto_login: phase5: BEFORE typing template, active window is WID=12582949 NAME='Open'
2026-06-28T07:51:18Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T07:51:18Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  07:53:47 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     7m37s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:47:52Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:53Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:54Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:55Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:57Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:58Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:59Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:00Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:01Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:02Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:03Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:04Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:05Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:07Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:08Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:09Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:10Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:11Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:12Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:13Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:14Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:15Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:17Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:19Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:20Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:21Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:22Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:23Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:24Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:25Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:26Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:27Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:28Z [INFO] auto_login: login confirmed via journal at +33s: QE 0       07:47:52.885    Network '133978149': trading has been enabled - hedging mode
2026-06-28T07:48:28Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T07:49:30Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T07:49:30Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T07:50:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T07:50:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T07:50:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T07:50:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T07:50:44Z [INFO] auto_login: phase5: BEFORE typing template, active window is WID=12582949 NAME='Open'
2026-06-28T07:51:18Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T07:51:18Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  07:54:31 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     8m21s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:47:53Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:54Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:55Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:57Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:58Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:59Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:00Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:01Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:02Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:03Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:04Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:05Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:07Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:08Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:09Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:10Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:11Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:12Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:13Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:14Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:15Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:17Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:19Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:20Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:21Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:22Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:23Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:24Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:25Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:26Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:27Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:28Z [INFO] auto_login: login confirmed via journal at +33s: QE 0       07:47:52.885    Network '133978149': trading has been enabled - hedging mode
2026-06-28T07:48:28Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T07:49:30Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T07:49:30Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T07:50:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T07:50:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T07:50:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T07:50:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T07:50:44Z [INFO] auto_login: phase5: BEFORE typing template, active window is WID=12582949 NAME='Open'
2026-06-28T07:51:18Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T07:51:18Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-28T07:54:09Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 12/16  07:55:17 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     9m6s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:47:54Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:55Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:57Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:58Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:47:59Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:00Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:01Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:02Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:03Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:04Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:05Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:07Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:08Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:09Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:10Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:11Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:12Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:13Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:14Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:15Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:17Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:19Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:20Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:21Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:22Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:23Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:24Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:25Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:26Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:27Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:28Z [INFO] auto_login: login confirmed via journal at +33s: QE 0       07:47:52.885    Network '133978149': trading has been enabled - hedging mode
2026-06-28T07:48:28Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T07:49:30Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T07:49:30Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T07:50:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T07:50:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T07:50:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T07:50:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T07:50:44Z [INFO] auto_login: phase5: BEFORE typing template, active window is WID=12582949 NAME='Open'
2026-06-28T07:51:18Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T07:51:18Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-28T07:54:09Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-28T07:55:13Z [WARN] MetaTrader exited with code 143
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 13/16  07:56:01 =====
etradie-mt-8d759d57-870-0   2/3   Running   0     9m51s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T07:48:19Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:20Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:21Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:22Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:23Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:24Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:25Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:26Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:27Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T07:48:28Z [INFO] auto_login: login confirmed via journal at +33s: QE 0       07:47:52.885    Network '133978149': trading has been enabled - hedging mode
2026-06-28T07:48:28Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T07:49:30Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T07:49:30Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T07:50:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T07:50:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T07:50:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T07:50:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T07:50:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T07:50:44Z [INFO] auto_login: phase5: BEFORE typing template, active window is WID=12582949 NAME='Open'
2026-06-28T07:51:18Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T07:51:18Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-28T07:54:09Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-28T07:55:13Z [WARN] MetaTrader exited with code 143
2026-06-28T07:55:43Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-28T07:55:43Z [INFO] auto_login: hard-kill watchdog armed (pid=4095, fires at +450s)
2026-06-28T07:55:43Z [INFO] auto_login: terminal process detected at +0s
2026-06-28T07:55:43Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:55:45Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:55:48Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:55:50Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:55:52Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:55:54Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:55:56Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T07:55:58Z [INFO] auto_login: liveupdate-handler: active WID=12582937 name='Login'
2026-06-28T07:55:58Z [INFO] auto_login: Login dialog WID=12582937 detected at +15s
2026-06-28T07:55:58Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582937 name=Login
2026-06-28T07:56:00Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582937 name=Login
2026-06-28T07:56:00Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582937 name=Login
2026-06-28T07:56:00Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-28T07:56:01Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-28T07:56:01Z [INFO] auto_login: deliver login: paste succeeded
2026-06-28T07:56:02Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582937 name=Login
2026-06-28T07:56:02Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582937 name=Login
2026-06-28T07:56:02Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 14/16  07:56:45 =====
Error from server (NotFound): pods "etradie-mt-8d759d57-870-0" not found
POD GONE
=== STAGE 12: final artifacts ===
FAIL convert screen-poll-01.xwd (imagemagick?)
OK: screen-poll-02.png
OK: screen-poll-03.png
OK: screen-poll-04.png
OK: screen-poll-05.png
OK: screen-poll-06.png
OK: screen-poll-07.png
OK: screen-poll-08.png
OK: screen-poll-09.png
OK: screen-poll-10.png
OK: screen-poll-11.png
OK: screen-poll-12.png
OK: screen-poll-13.png
=== STAGE 13: verdict ===
Error from server (NotFound): pods "etradie-mt-8d759d57-870-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-8d759d57-870-0" not found
--- journal head/tail (broker handshake) ---
(MT_DIR empty; journal/EA log not collected)
...
(MT_DIR empty; journal/EA log not collected)
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 8d759d57-870c-488e-8414-eca01ffbff42 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260628T074338Z ===
total 19240
drwxr-xr-x  2 softverse softverse    4096 Jun 28 08:56 .
drwxr-xr-x 33 softverse softverse    4096 Jun 28 08:43 ..
-rw-r--r--  1 softverse softverse     110 Jun 28 08:56 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 28 08:56 driver-log-full.txt
-rw-r--r--  1 softverse softverse      45 Jun 28 08:56 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 28 08:44 engine-env.txt
-rw-r--r--  1 softverse softverse       1 Jun 28 08:46 mt-config-dir.txt
-rw-r--r--  1 softverse softverse       1 Jun 28 08:46 mt-dir.txt
-rw-r--r--  1 softverse softverse      45 Jun 28 08:56 mt5-journal.txt
-rw-r--r--  1 softverse softverse      71 Jun 28 08:46 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse       0 Jun 28 08:46 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 28 08:43 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 28 08:46 release.txt
-rw-r--r--  1 softverse softverse      35 Jun 28 08:47 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   65916 Jun 28 08:56 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:47 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse   52945 Jun 28 08:56 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:48 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse   52763 Jun 28 08:56 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:49 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   52741 Jun 28 08:56 screen-poll-05.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:50 screen-poll-05.xwd
-rw-r--r--  1 softverse softverse   59725 Jun 28 08:56 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:50 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   59826 Jun 28 08:56 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:51 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse   60030 Jun 28 08:56 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:52 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse   60079 Jun 28 08:56 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:53 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse   59886 Jun 28 08:56 screen-poll-10.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:53 screen-poll-10.xwd
-rw-r--r--  1 softverse softverse   59788 Jun 28 08:56 screen-poll-11.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:54 screen-poll-11.xwd
-rw-r--r--  1 softverse softverse     278 Jun 28 08:56 screen-poll-12.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:55 screen-poll-12.xwd
-rw-r--r--  1 softverse softverse   66466 Jun 28 08:56 screen-poll-13.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 08:56 screen-poll-13.xwd
-rw-r--r--  1 softverse softverse      23 Jun 28 08:46 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 28 08:56 windows-final.txt
-rw-r--r--  1 softverse softverse       0 Jun 28 08:47 windows-poll-01.txt
-rw-r--r--  1 softverse softverse     168 Jun 28 08:47 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      80 Jun 28 08:48 windows-poll-03.txt
-rw-r--r--  1 softverse softverse      80 Jun 28 08:49 windows-poll-04.txt
-rw-r--r--  1 softverse softverse      80 Jun 28 08:50 windows-poll-05.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 08:51 windows-poll-06.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 08:51 windows-poll-07.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 08:52 windows-poll-08.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 08:53 windows-poll-09.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 08:54 windows-poll-10.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 08:54 windows-poll-11.txt
-rw-r--r--  1 softverse softverse       0 Jun 28 08:55 windows-poll-12.txt
-rw-r--r--  1 softverse softverse      42 Jun 28 08:56 windows-poll-13.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260628T074338Z
softverse@Softverse:~/hostedmt-diagnostics/20260628T074338Z$