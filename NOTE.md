== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 09:22:33
=== STAGE 7: race to the pod ===
Release: etradie-mt-b810d1db-9d5
POD=etradie-mt-b810d1db-9d5-0
[1] mt-node state: {"waiting":{"reason":"PodInitializing"}}
[2] mt-node state: {"running":{"startedAt":"2026-06-27T09:22:37Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:e17be3e29e689752d1085c2d3d12d660796f4c73
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:e17be3e29e689752d1085c2d3d12d660796f4c73
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

===== poll 1/16  09:23:01 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     40s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
tar: Removing leading `/' from member names

===== poll 2/16  09:23:43 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     81s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:23:15Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-27T09:23:15Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-27T09:23:15Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-27T09:23:15Z [INFO] overlay-normalize(mt5): deleting baked common.ini (foreign [Common] account context blocked by trusted-device check on fresh Wine prefix -- surfaces demo-registration wizard; MT5 recreates the file after Phase 3's per-tenant login)
2026-06-27T09:23:15Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-27T09:23:16Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T09:23:16Z [INFO] auto_login: hard-kill watchdog armed (pid=347, fires at +450s)
2026-06-27T09:23:16Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T09:23:16Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:23:18Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:23:20Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:23:22Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:23:25Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:23:27Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:23:29Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:23:31Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T09:23:33Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T09:23:35Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T09:23:37Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T09:23:39Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T09:23:42Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T09:23:44Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T09:23:46Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T09:23:46Z [INFO] auto_login: main UI window WID=12582913 detected at +30s; entering Phase 2c (3-attempt menu invocation)
2026-06-27T09:23:46Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-27T09:23:46Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  09:24:26 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     2m5s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:23:52Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-27T09:23:52Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-27T09:23:53Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T09:23:53Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T09:23:53Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-27T09:23:53Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-27T09:23:54Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-27T09:23:55Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-27T09:23:55Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T09:23:56Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T09:23:56Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T09:23:56Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T09:23:56Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T09:23:56Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T09:23:57Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T09:23:57Z [INFO] auto_login: clipboard scrubbed
2026-06-27T09:23:57Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T09:23:58Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T09:23:59Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:01Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:02Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:03Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:04Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:05Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:06Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:07Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:09Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:10Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:11Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:12Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:13Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:14Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:15Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:16Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:17Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:18Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:20Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:21Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:22Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:24Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:25Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:26Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:27Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:28Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:29Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  09:25:13 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     2m51s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:23:53Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-27T09:23:53Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-27T09:23:54Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-27T09:23:55Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-27T09:23:55Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T09:23:56Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T09:23:56Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T09:23:56Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T09:23:56Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T09:23:56Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T09:23:57Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T09:23:57Z [INFO] auto_login: clipboard scrubbed
2026-06-27T09:23:57Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T09:23:58Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T09:23:59Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:01Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:02Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:03Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:04Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:05Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:06Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:07Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:09Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:10Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:11Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:12Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:13Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:14Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:15Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:16Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:17Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:18Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:20Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:21Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:22Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:24Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:25Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:26Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:27Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:28Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:29Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:30Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:32Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:33Z [INFO] auto_login: login confirmed via journal at +31s: FK 0       09:23:59.289    Network '133978149': trading has been enabled - hedging mode
2026-06-27T09:24:33Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  09:25:56 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     3m34s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:23:54Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-27T09:23:55Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-27T09:23:55Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T09:23:56Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T09:23:56Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T09:23:56Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T09:23:56Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T09:23:56Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T09:23:57Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T09:23:57Z [INFO] auto_login: clipboard scrubbed
2026-06-27T09:23:57Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T09:23:58Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T09:23:59Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:01Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:02Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:03Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:04Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:05Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:06Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:07Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:09Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:10Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:11Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:12Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:13Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:14Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:15Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:16Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:17Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:18Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:20Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:21Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:22Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:24Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:25Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:26Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:27Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:28Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:29Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:30Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:32Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:33Z [INFO] auto_login: login confirmed via journal at +31s: FK 0       09:23:59.289    Network '133978149': trading has been enabled - hedging mode
2026-06-27T09:24:33Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T09:25:34Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T09:25:34Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  09:26:39 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     4m17s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:23:56Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T09:23:56Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T09:23:56Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T09:23:56Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T09:23:57Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T09:23:57Z [INFO] auto_login: clipboard scrubbed
2026-06-27T09:23:57Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T09:23:58Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T09:23:59Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:01Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:02Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:03Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:04Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:05Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:06Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:07Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:09Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:10Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:11Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:12Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:13Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:14Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:15Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:16Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:17Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:18Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:20Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:21Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:22Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:24Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:25Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:26Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:27Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:28Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:29Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:30Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:32Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:33Z [INFO] auto_login: login confirmed via journal at +31s: FK 0       09:23:59.289    Network '133978149': trading has been enabled - hedging mode
2026-06-27T09:24:33Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T09:25:34Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T09:25:34Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T09:26:37Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T09:26:37Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T09:26:37Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:26:38Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  09:27:21 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     4m59s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:23:57Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T09:23:57Z [INFO] auto_login: clipboard scrubbed
2026-06-27T09:23:57Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T09:23:58Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T09:23:59Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:01Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:02Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:03Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:04Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:05Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:06Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:07Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:09Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:10Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:11Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:12Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:13Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:14Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:15Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:16Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:17Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:18Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:20Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:21Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:22Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:24Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:25Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:26Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:27Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:28Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:29Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:30Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:32Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:33Z [INFO] auto_login: login confirmed via journal at +31s: FK 0       09:23:59.289    Network '133978149': trading has been enabled - hedging mode
2026-06-27T09:24:33Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T09:25:34Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T09:25:34Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T09:26:37Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T09:26:37Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T09:26:37Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:26:38Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T09:27:00Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T09:27:06Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T09:27:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:07Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 8/16  09:28:16 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     5m55s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:24:03Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:04Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:05Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:06Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:07Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:09Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:10Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:11Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:12Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:13Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:14Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:15Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:16Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:17Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:18Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:20Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:21Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:22Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:24Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:25Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:26Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:27Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:28Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:29Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:30Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:32Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:33Z [INFO] auto_login: login confirmed via journal at +31s: FK 0       09:23:59.289    Network '133978149': trading has been enabled - hedging mode
2026-06-27T09:24:33Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T09:25:34Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T09:25:34Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T09:26:37Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T09:26:37Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T09:26:37Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:26:38Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T09:27:00Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T09:27:06Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T09:27:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:07Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T09:27:31Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T09:27:36Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T09:27:36Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:37Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T09:27:59Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T09:28:00Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T09:28:00Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  09:29:04 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     6m43s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:24:03Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:04Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:05Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:06Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:07Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:09Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:10Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:11Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:12Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:13Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:14Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:15Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:16Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:17Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:18Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:20Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:21Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:22Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:24Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:25Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:26Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:27Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:28Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:29Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:30Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:32Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:33Z [INFO] auto_login: login confirmed via journal at +31s: FK 0       09:23:59.289    Network '133978149': trading has been enabled - hedging mode
2026-06-27T09:24:33Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T09:25:34Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T09:25:34Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T09:26:37Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T09:26:37Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T09:26:37Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:26:38Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T09:27:00Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T09:27:06Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T09:27:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:07Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T09:27:31Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T09:27:36Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T09:27:36Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:37Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T09:27:59Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T09:28:00Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T09:28:00Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  09:29:50 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     7m29s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:24:03Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:04Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:05Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:06Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:07Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:09Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:10Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:11Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:12Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:13Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:14Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:15Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:16Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:17Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:18Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:20Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:21Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:22Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:24Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:25Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:26Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:27Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:28Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:29Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:30Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:32Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:33Z [INFO] auto_login: login confirmed via journal at +31s: FK 0       09:23:59.289    Network '133978149': trading has been enabled - hedging mode
2026-06-27T09:24:33Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T09:25:34Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T09:25:34Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T09:26:37Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T09:26:37Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T09:26:37Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:26:38Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T09:27:00Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T09:27:06Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T09:27:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:07Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T09:27:31Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T09:27:36Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T09:27:36Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:37Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T09:27:59Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T09:28:00Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T09:28:00Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  09:30:35 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     8m14s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:24:04Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:05Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:06Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:07Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:09Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:10Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:11Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:12Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:13Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:14Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:15Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:16Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:17Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:18Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:20Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:21Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:22Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:24Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:25Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:26Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:27Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:28Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:29Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:30Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:32Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:33Z [INFO] auto_login: login confirmed via journal at +31s: FK 0       09:23:59.289    Network '133978149': trading has been enabled - hedging mode
2026-06-27T09:24:33Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T09:25:34Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T09:25:34Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T09:26:37Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T09:26:37Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T09:26:37Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:26:38Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T09:27:00Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T09:27:06Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T09:27:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:07Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T09:27:31Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T09:27:36Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T09:27:36Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:37Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T09:27:59Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T09:28:00Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T09:28:00Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T09:30:16Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 12/16  09:31:24 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     9m2s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:24:05Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:06Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:07Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:09Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:10Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:11Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:12Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:13Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:14Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:15Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:16Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:17Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:18Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:20Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:21Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:22Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:24Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:25Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:26Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:27Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:28Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:29Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:30Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:32Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:33Z [INFO] auto_login: login confirmed via journal at +31s: FK 0       09:23:59.289    Network '133978149': trading has been enabled - hedging mode
2026-06-27T09:24:33Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T09:25:34Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T09:25:34Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T09:26:37Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T09:26:37Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T09:26:37Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:26:38Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T09:27:00Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T09:27:06Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T09:27:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:07Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T09:27:31Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T09:27:36Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T09:27:36Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:37Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T09:27:59Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T09:28:00Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T09:28:00Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T09:30:16Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T09:31:24Z [WARN] MetaTrader exited with code 143
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 13/16  09:32:09 =====
etradie-mt-b810d1db-9d5-0   2/3   Running   0     9m46s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T09:24:17Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:18Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:20Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:21Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:22Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:24Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:25Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:26Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:27Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:28Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:29Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:30Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:32Z [INFO] auto_login: login-auth wait +30s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T09:24:33Z [INFO] auto_login: login confirmed via journal at +31s: FK 0       09:23:59.289    Network '133978149': trading has been enabled - hedging mode
2026-06-27T09:24:33Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T09:25:34Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T09:25:34Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T09:26:37Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T09:26:37Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T09:26:37Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:26:38Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T09:27:00Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T09:27:06Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T09:27:06Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:07Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T09:27:31Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T09:27:36Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T09:27:36Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T09:27:37Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T09:27:59Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T09:28:00Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T09:28:00Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T09:30:16Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T09:31:24Z [WARN] MetaTrader exited with code 143
2026-06-27T09:31:54Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T09:31:54Z [INFO] auto_login: hard-kill watchdog armed (pid=4225, fires at +450s)
2026-06-27T09:31:54Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T09:31:54Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:31:56Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:31:58Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:32:01Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:32:03Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:32:05Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:32:08Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T09:32:10Z [INFO] auto_login: liveupdate-handler: no active window (skip)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 14/16  09:32:56 =====
Error from server (NotFound): pods "etradie-mt-b810d1db-9d5-0" not found
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
Error from server (NotFound): pods "etradie-mt-b810d1db-9d5-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-b810d1db-9d5-0" not found
--- journal head/tail (broker handshake) ---
(MT_DIR empty; journal/EA log not collected)
...
(MT_DIR empty; journal/EA log not collected)
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 b810d1db-9d58-43a9-8728-8fe386156291 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260627T091937Z ===
total 19224
drwxr-xr-x  2 softverse softverse    4096 Jun 27 10:33 .
drwxr-xr-x 21 softverse softverse    4096 Jun 27 10:19 ..
-rw-r--r--  1 softverse softverse     110 Jun 27 10:33 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 27 10:32 driver-log-full.txt
-rw-r--r--  1 softverse softverse      45 Jun 27 10:33 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 27 10:20 engine-env.txt
-rw-r--r--  1 softverse softverse       1 Jun 27 10:22 mt-config-dir.txt
-rw-r--r--  1 softverse softverse       1 Jun 27 10:22 mt-dir.txt
-rw-r--r--  1 softverse softverse      45 Jun 27 10:33 mt5-journal.txt
-rw-r--r--  1 softverse softverse      71 Jun 27 10:23 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse       0 Jun 27 10:23 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 27 10:19 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 27 10:22 release.txt
-rw-r--r--  1 softverse softverse      35 Jun 27 10:23 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   67624 Jun 27 10:33 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:23 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse   57361 Jun 27 10:33 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:24 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse   57921 Jun 27 10:33 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:25 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   58429 Jun 27 10:33 screen-poll-05.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:26 screen-poll-05.xwd
-rw-r--r--  1 softverse softverse   42865 Jun 27 10:33 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:26 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   57103 Jun 27 10:33 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:27 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse   56489 Jun 27 10:33 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:28 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse   56498 Jun 27 10:33 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:29 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse   56819 Jun 27 10:33 screen-poll-10.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:30 screen-poll-10.xwd
-rw-r--r--  1 softverse softverse   56525 Jun 27 10:33 screen-poll-11.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:30 screen-poll-11.xwd
-rw-r--r--  1 softverse softverse     278 Jun 27 10:33 screen-poll-12.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:31 screen-poll-12.xwd
-rw-r--r--  1 softverse softverse   63481 Jun 27 10:33 screen-poll-13.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 10:32 screen-poll-13.xwd
-rw-r--r--  1 softverse softverse      23 Jun 27 10:22 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 27 10:33 windows-final.txt
-rw-r--r--  1 softverse softverse       0 Jun 27 10:23 windows-poll-01.txt
-rw-r--r--  1 softverse softverse      72 Jun 27 10:23 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 10:24 windows-poll-03.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 10:25 windows-poll-04.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 10:26 windows-poll-05.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 10:26 windows-poll-06.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 10:27 windows-poll-07.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 10:28 windows-poll-08.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 10:29 windows-poll-09.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 10:30 windows-poll-10.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 10:30 windows-poll-11.txt
-rw-r--r--  1 softverse softverse       0 Jun 27 10:31 windows-poll-12.txt
-rw-r--r--  1 softverse softverse      42 Jun 27 10:32 windows-poll-13.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260627T091937Z
softverse@Softverse:~/hostedmt-diagnostics/20260627T091937Z$