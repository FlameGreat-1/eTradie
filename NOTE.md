== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 14:59:53
=== STAGE 7: race to the pod ===
Release: etradie-mt-7f6d1c36-d36
POD=etradie-mt-7f6d1c36-d36-0
[1] mt-node state: {"running":{"startedAt":"2026-06-27T14:59:57Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:73e96cb97ecfc9e47c79acdf2efdf745009e87e0
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:73e96cb97ecfc9e47c79acdf2efdf745009e87e0
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

===== poll 1/16  15:00:34 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     52s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
tar: Removing leading `/' from member names

===== poll 2/16  15:01:19 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     99s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:00:47Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-27T15:00:47Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-27T15:00:47Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-27T15:00:47Z [INFO] overlay-normalize(mt5): deleting baked common.ini (foreign [Common] account context blocked by trusted-device check on fresh Wine prefix -- surfaces demo-registration wizard; MT5 recreates the file after Phase 3's per-tenant login)
2026-06-27T15:00:47Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-27T15:00:47Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T15:00:47Z [INFO] auto_login: hard-kill watchdog armed (pid=344, fires at +450s)
2026-06-27T15:00:47Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T15:00:47Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:00:49Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:00:51Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:00:54Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:00:56Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:00:58Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:01:00Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:01:02Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:01:05Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:01:07Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:01:09Z [INFO] auto_login: liveupdate-handler: active WID=12582913 name='MetaTrader 5 EXNESS - Netting'
2026-06-27T15:01:11Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T15:01:13Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T15:01:15Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T15:01:17Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T15:01:17Z [INFO] auto_login: main UI window WID=12582913 detected at +30s; entering Phase 2c (3-attempt menu invocation)
2026-06-27T15:01:18Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-27T15:01:18Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-27T15:01:18Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:01:20Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-27T15:01:20Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-27T15:01:21Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-27T15:01:22Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-27T15:01:22Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-27T15:01:23Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-27T15:01:23Z [INFO] auto_login: deliver login: paste succeeded
2026-06-27T15:01:23Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-27T15:01:24Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-27T15:01:24Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  15:02:18 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     2m37s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:01:28Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T15:01:28Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T15:01:28Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T15:01:28Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T15:01:29Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T15:01:29Z [INFO] auto_login: clipboard scrubbed
2026-06-27T15:01:29Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:30Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:31Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:32Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:33Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:35Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:36Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:37Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:38Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:39Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:40Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:41Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:42Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:44Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:45Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:46Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:47Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:48Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:49Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:50Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:51Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:52Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:54Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:55Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:57Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:58Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:59Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:00Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:01Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:03Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:04Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:05Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:06Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:07Z [INFO] auto_login: login-auth wait +33s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:08Z [INFO] auto_login: login-auth wait +34s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:09Z [INFO] auto_login: login-auth wait +35s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:10Z [INFO] auto_login: login-auth wait +36s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:11Z [INFO] auto_login: login confirmed via journal at +37s: IE 0       15:01:30.899    Network '133978149': trading has been enabled - hedging mode
2026-06-27T15:02:11Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  15:03:03 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     3m22s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:01:28Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T15:01:28Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T15:01:28Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T15:01:28Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T15:01:29Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T15:01:29Z [INFO] auto_login: clipboard scrubbed
2026-06-27T15:01:29Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:30Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:31Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:32Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:33Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:35Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:36Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:37Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:38Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:39Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:40Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:41Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:42Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:44Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:45Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:46Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:47Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:48Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:49Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:50Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:51Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:52Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:54Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:55Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:57Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:58Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:59Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:00Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:01Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:03Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:04Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:05Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:06Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:07Z [INFO] auto_login: login-auth wait +33s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:08Z [INFO] auto_login: login-auth wait +34s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:09Z [INFO] auto_login: login-auth wait +35s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:10Z [INFO] auto_login: login-auth wait +36s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:11Z [INFO] auto_login: login confirmed via journal at +37s: IE 0       15:01:30.899    Network '133978149': trading has been enabled - hedging mode
2026-06-27T15:02:11Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  15:03:49 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     4m10s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:01:28Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T15:01:28Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T15:01:29Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T15:01:29Z [INFO] auto_login: clipboard scrubbed
2026-06-27T15:01:29Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:30Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:31Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:32Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:33Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:35Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:36Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:37Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:38Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:39Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:40Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:41Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:42Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:44Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:45Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:46Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:47Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:48Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:49Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:50Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:51Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:52Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:54Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:55Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:57Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:58Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:59Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:00Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:01Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:03Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:04Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:05Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:06Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:07Z [INFO] auto_login: login-auth wait +33s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:08Z [INFO] auto_login: login-auth wait +34s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:09Z [INFO] auto_login: login-auth wait +35s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:10Z [INFO] auto_login: login-auth wait +36s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:11Z [INFO] auto_login: login confirmed via journal at +37s: IE 0       15:01:30.899    Network '133978149': trading has been enabled - hedging mode
2026-06-27T15:02:11Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T15:03:13Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T15:03:13Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  15:04:37 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     4m56s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:01:30Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:31Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:32Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:33Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:35Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:36Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:37Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:38Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:39Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:40Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:41Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:42Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:44Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:45Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:46Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:47Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:48Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:49Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:50Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:51Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:52Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:54Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:55Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:57Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:58Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:59Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:00Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:01Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:03Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:04Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:05Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:06Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:07Z [INFO] auto_login: login-auth wait +33s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:08Z [INFO] auto_login: login-auth wait +34s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:09Z [INFO] auto_login: login-auth wait +35s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:10Z [INFO] auto_login: login-auth wait +36s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:11Z [INFO] auto_login: login confirmed via journal at +37s: IE 0       15:01:30.899    Network '133978149': trading has been enabled - hedging mode
2026-06-27T15:02:11Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T15:03:13Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T15:03:13Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T15:04:16Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T15:04:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T15:04:18Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  15:05:22 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     5m41s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:01:36Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:37Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:38Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:39Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:40Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:41Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:42Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:44Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:45Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:46Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:47Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:48Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:49Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:50Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:51Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:52Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:54Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:55Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:57Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:58Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:59Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:00Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:01Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:03Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:04Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:05Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:06Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:07Z [INFO] auto_login: login-auth wait +33s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:08Z [INFO] auto_login: login-auth wait +34s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:09Z [INFO] auto_login: login-auth wait +35s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:10Z [INFO] auto_login: login-auth wait +36s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:11Z [INFO] auto_login: login confirmed via journal at +37s: IE 0       15:01:30.899    Network '133978149': trading has been enabled - hedging mode
2026-06-27T15:02:11Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T15:03:13Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T15:03:13Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T15:04:16Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T15:04:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T15:04:18Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:04:48Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T15:04:53Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T15:04:53Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:54Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T15:04:56Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=12582913 visible after keystroke sequence
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 8/16  15:06:11 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     6m29s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:01:45Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:46Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:47Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:48Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:49Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:50Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:51Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:52Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:54Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:55Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:57Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:58Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:59Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:00Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:01Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:03Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:04Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:05Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:06Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:07Z [INFO] auto_login: login-auth wait +33s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:08Z [INFO] auto_login: login-auth wait +34s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:09Z [INFO] auto_login: login-auth wait +35s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:10Z [INFO] auto_login: login-auth wait +36s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:11Z [INFO] auto_login: login confirmed via journal at +37s: IE 0       15:01:30.899    Network '133978149': trading has been enabled - hedging mode
2026-06-27T15:02:11Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T15:03:13Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T15:03:13Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T15:04:16Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T15:04:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T15:04:18Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:04:48Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T15:04:53Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T15:04:53Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:54Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T15:04:56Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:05:26Z [WARN] auto_login: phase5: attempt 2: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T15:05:31Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): clearing modals + activating main window
2026-06-27T15:05:31Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:05:32Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): dispatching keystroke sequence [alt+f Right Down Right Return]
2026-06-27T15:05:34Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:06:05Z [WARN] auto_login: phase5: attempt 3: chart opened but :5555 not bound within budget
2026-06-27T15:06:05Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T15:06:05Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  15:07:00 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     7m19s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:01:45Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:46Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:47Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:48Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:49Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:50Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:51Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:52Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:54Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:55Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:57Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:58Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:59Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:00Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:01Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:03Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:04Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:05Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:06Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:07Z [INFO] auto_login: login-auth wait +33s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:08Z [INFO] auto_login: login-auth wait +34s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:09Z [INFO] auto_login: login-auth wait +35s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:10Z [INFO] auto_login: login-auth wait +36s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:11Z [INFO] auto_login: login confirmed via journal at +37s: IE 0       15:01:30.899    Network '133978149': trading has been enabled - hedging mode
2026-06-27T15:02:11Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T15:03:13Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T15:03:13Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T15:04:16Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T15:04:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T15:04:18Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:04:48Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T15:04:53Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T15:04:53Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:54Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T15:04:56Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:05:26Z [WARN] auto_login: phase5: attempt 2: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T15:05:31Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): clearing modals + activating main window
2026-06-27T15:05:31Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:05:32Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): dispatching keystroke sequence [alt+f Right Down Right Return]
2026-06-27T15:05:34Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:06:05Z [WARN] auto_login: phase5: attempt 3: chart opened but :5555 not bound within budget
2026-06-27T15:06:05Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T15:06:05Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  15:07:46 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     8m6s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:01:46Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:47Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:48Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:49Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:50Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:51Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:52Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:54Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:55Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:57Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:58Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:59Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:00Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:01Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:03Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:04Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:05Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:06Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:07Z [INFO] auto_login: login-auth wait +33s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:08Z [INFO] auto_login: login-auth wait +34s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:09Z [INFO] auto_login: login-auth wait +35s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:10Z [INFO] auto_login: login-auth wait +36s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:11Z [INFO] auto_login: login confirmed via journal at +37s: IE 0       15:01:30.899    Network '133978149': trading has been enabled - hedging mode
2026-06-27T15:02:11Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T15:03:13Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T15:03:13Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T15:04:16Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T15:04:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T15:04:18Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:04:48Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T15:04:53Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T15:04:53Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:54Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T15:04:56Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:05:26Z [WARN] auto_login: phase5: attempt 2: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T15:05:31Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): clearing modals + activating main window
2026-06-27T15:05:31Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:05:32Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): dispatching keystroke sequence [alt+f Right Down Right Return]
2026-06-27T15:05:34Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:06:05Z [WARN] auto_login: phase5: attempt 3: chart opened but :5555 not bound within budget
2026-06-27T15:06:05Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T15:06:05Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T15:07:47Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  15:08:35 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     8m55s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:01:46Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:47Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:48Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:49Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:50Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:51Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:52Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:54Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:55Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:57Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:58Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:59Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:00Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:01Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:03Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:04Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:05Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:06Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:07Z [INFO] auto_login: login-auth wait +33s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:08Z [INFO] auto_login: login-auth wait +34s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:09Z [INFO] auto_login: login-auth wait +35s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:10Z [INFO] auto_login: login-auth wait +36s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:11Z [INFO] auto_login: login confirmed via journal at +37s: IE 0       15:01:30.899    Network '133978149': trading has been enabled - hedging mode
2026-06-27T15:02:11Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T15:03:13Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T15:03:13Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T15:04:16Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T15:04:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T15:04:18Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:04:48Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T15:04:53Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T15:04:53Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:54Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T15:04:56Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:05:26Z [WARN] auto_login: phase5: attempt 2: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T15:05:31Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): clearing modals + activating main window
2026-06-27T15:05:31Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:05:32Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): dispatching keystroke sequence [alt+f Right Down Right Return]
2026-06-27T15:05:34Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:06:05Z [WARN] auto_login: phase5: attempt 3: chart opened but :5555 not bound within budget
2026-06-27T15:06:05Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T15:06:05Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T15:07:47Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 12/16  15:09:22 =====
etradie-mt-7f6d1c36-d36-0   2/3   Running   0     9m40s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:01:47Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:48Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:49Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:50Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:51Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:52Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:54Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:55Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:57Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:58Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:01:59Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:00Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:01Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:03Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:04Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:05Z [INFO] auto_login: login-auth wait +31s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:06Z [INFO] auto_login: login-auth wait +32s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:07Z [INFO] auto_login: login-auth wait +33s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:08Z [INFO] auto_login: login-auth wait +34s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:09Z [INFO] auto_login: login-auth wait +35s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:10Z [INFO] auto_login: login-auth wait +36s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T15:02:11Z [INFO] auto_login: login confirmed via journal at +37s: IE 0       15:01:30.899    Network '133978149': trading has been enabled - hedging mode
2026-06-27T15:02:11Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T15:03:13Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T15:03:13Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T15:04:16Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T15:04:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:16Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T15:04:18Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:04:48Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T15:04:53Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T15:04:53Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:04:54Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T15:04:56Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:05:26Z [WARN] auto_login: phase5: attempt 2: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T15:05:31Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): clearing modals + activating main window
2026-06-27T15:05:31Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:05:32Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): dispatching keystroke sequence [alt+f Right Down Right Return]
2026-06-27T15:05:34Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:06:05Z [WARN] auto_login: phase5: attempt 3: chart opened but :5555 not bound within budget
2026-06-27T15:06:05Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T15:06:05Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T15:07:47Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T15:08:57Z [WARN] MetaTrader exited with code 143
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 13/16  15:10:08 =====
etradie-mt-7f6d1c36-d36-0   2/3   Terminating   0     10m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T15:05:31Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T15:05:32Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): dispatching keystroke sequence [alt+f Right Down Right Return]
2026-06-27T15:05:34Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): chart window WID=12582913 visible after keystroke sequence
2026-06-27T15:06:05Z [WARN] auto_login: phase5: attempt 3: chart opened but :5555 not bound within budget
2026-06-27T15:06:05Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T15:06:05Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T15:07:47Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T15:08:57Z [WARN] MetaTrader exited with code 143
2026-06-27T15:09:27Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T15:09:27Z [INFO] auto_login: hard-kill watchdog armed (pid=4176, fires at +450s)
2026-06-27T15:09:27Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T15:09:27Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:09:29Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:09:31Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:09:33Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:09:35Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:09:37Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:09:40Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T15:09:42Z [INFO] auto_login: liveupdate-handler: active WID=12582937 name='Login'
2026-06-27T15:09:42Z [INFO] auto_login: Login dialog WID=12582937 detected at +15s
2026-06-27T15:09:42Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582937 name=Login
2026-06-27T15:09:43Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582937 name=Login
2026-06-27T15:09:44Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582937 name=Login
2026-06-27T15:09:44Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-27T15:09:45Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-27T15:09:45Z [INFO] auto_login: deliver login: paste succeeded
2026-06-27T15:09:45Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582937 name=Login
2026-06-27T15:09:46Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582937 name=Login
2026-06-27T15:09:46Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-27T15:09:47Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T15:09:47Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T15:09:47Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582937 name=Login
2026-06-27T15:09:47Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582937 name=Login
2026-06-27T15:09:48Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582937 name=Login
2026-06-27T15:09:48Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582937 name=Login
2026-06-27T15:09:48Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T15:09:50Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T15:09:50Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T15:09:50Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582937 name=Login
2026-06-27T15:09:50Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582937 name=Login
2026-06-27T15:09:50Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T15:09:51Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-27T15:09:51Z [INFO] auto_login: clipboard scrubbed
2026-06-27T15:09:51Z [INFO] auto_login: login confirmed via journal at +0s: IE  0       15:01:30.899    Network '133978149': trading has been enabled - hedging mode
2026-06-27T15:09:51Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd

===== poll 14/16  15:10:48 =====
Error from server (NotFound): pods "etradie-mt-7f6d1c36-d36-0" not found
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
=== STAGE 13: verdict ===
Error from server (NotFound): pods "etradie-mt-7f6d1c36-d36-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-7f6d1c36-d36-0" not found
--- journal head/tail (broker handshake) ---
(MT_DIR empty; journal/EA log not collected)
...
(MT_DIR empty; journal/EA log not collected)
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 7f6d1c36-d367-44ff-87d9-4e8491955589 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260627T144436Z ===
total 17732
drwxr-xr-x  2 softverse softverse    4096 Jun 27 16:10 .
drwxr-xr-x 25 softverse softverse    4096 Jun 27 15:44 ..
-rw-r--r--  1 softverse softverse     110 Jun 27 16:10 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 27 16:10 driver-log-full.txt
-rw-r--r--  1 softverse softverse      45 Jun 27 16:10 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 27 15:45 engine-env.txt
-rw-r--r--  1 softverse softverse       1 Jun 27 16:00 mt-config-dir.txt
-rw-r--r--  1 softverse softverse       1 Jun 27 16:00 mt-dir.txt
-rw-r--r--  1 softverse softverse      45 Jun 27 16:10 mt5-journal.txt
-rw-r--r--  1 softverse softverse      71 Jun 27 16:00 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse       0 Jun 27 16:00 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 27 15:44 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 27 16:00 release.txt
-rw-r--r--  1 softverse softverse      35 Jun 27 16:00 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   78162 Jun 27 16:10 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 16:01 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse   57101 Jun 27 16:10 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 16:02 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse   57586 Jun 27 16:10 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 16:03 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   57823 Jun 27 16:10 screen-poll-05.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 16:04 screen-poll-05.xwd
-rw-r--r--  1 softverse softverse   64642 Jun 27 16:10 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 16:04 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   72065 Jun 27 16:10 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 16:05 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse   71695 Jun 27 16:10 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 16:06 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse   71861 Jun 27 16:10 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 16:07 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse   72185 Jun 27 16:10 screen-poll-10.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 16:08 screen-poll-10.xwd
-rw-r--r--  1 softverse softverse   71998 Jun 27 16:10 screen-poll-11.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 16:08 screen-poll-11.xwd
-rw-r--r--  1 softverse softverse     278 Jun 27 16:10 screen-poll-12.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 16:09 screen-poll-12.xwd
-rw-r--r--  1 softverse softverse      23 Jun 27 15:59 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 27 16:10 windows-final.txt
-rw-r--r--  1 softverse softverse       0 Jun 27 16:00 windows-poll-01.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 16:01 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 16:02 windows-poll-03.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 16:03 windows-poll-04.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 16:04 windows-poll-05.txt
-rw-r--r--  1 softverse softverse      93 Jun 27 16:04 windows-poll-06.txt
-rw-r--r--  1 softverse softverse      93 Jun 27 16:05 windows-poll-07.txt
-rw-r--r--  1 softverse softverse      93 Jun 27 16:06 windows-poll-08.txt
-rw-r--r--  1 softverse softverse      93 Jun 27 16:07 windows-poll-09.txt
-rw-r--r--  1 softverse softverse      93 Jun 27 16:08 windows-poll-10.txt
-rw-r--r--  1 softverse softverse      93 Jun 27 16:08 windows-poll-11.txt
-rw-r--r--  1 softverse softverse      31 Jun 27 16:09 windows-poll-12.txt
-rw-r--r--  1 softverse softverse      73 Jun 27 16:10 windows-poll-13.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260627T144436Z
softverse@Softverse:~/hostedmt-diagnostics/20260627T144436Z$