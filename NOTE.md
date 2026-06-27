=== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 23:25:49
=== STAGE 7: race to the pod ===
Release: etradie-mt-4cd46a6a-5d7
POD=etradie-mt-4cd46a6a-5d7-0
[1] mt-node state: {"running":{"startedAt":"2026-06-27T23:25:45Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:d9fc61503bdc5e4a0f5d95ced39e3c091bc55088
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:d9fc61503bdc5e4a0f5d95ced39e3c091bc55088
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
 _NET_ACTIVE_WINDOW
=== STAGE 10: overlay normalizer + config-resolve log lines ===
2026-06-27T23:26:16Z [INFO] broker-bundle overlay: cp -a '/broker-bundle/MetaTrader 5 EXNESS/.' -> '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/'
2026-06-27T23:26:16Z [INFO] broker-bundle overlay: complete; sentinel written at '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/.bundle-installed-from-eadee9c7a152514f9c904b381a9416cf3d88dc5e480a12a62544079743c5e11c'
2026-06-27T23:26:16Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-27T23:26:16Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-27T23:26:16Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-27T23:26:16Z [INFO] overlay-normalize(mt5): deleting baked common.ini (foreign [Common] account context blocked by trusted-device check on fresh Wine prefix -- surfaces demo-registration wizard; MT5 recreates the file after Phase 3's per-tenant login)
2026-06-27T23:26:16Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-27T23:26:17Z [INFO] broker-bundle overlay summary: branded_terminal='/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/terminal64.exe', size=118840944, sha256=e87e8b77fa415fc91e9acbe692826e76b7907fb53db4244aed36618f9af30b9e, bundle_sha256=eadee9c7a152514f9c904b381a9416cf3d88dc5e480a12a62544079743c5e11c

Expect lines like:
  overlay-normalize(mt5): stripping baked Profiles/Charts workspace
  overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
  overlay-normalize(mt5): removing baked common.ini ...
  overlay-normalize(mt5): removing baked accounts.dat ...
  overlay-normalize: canonical config dir resolved to '<MT_DIR>/Config'
=== STAGE 10b: assert baked state was actually neutralized ===
SKIPPED: MT_DIR empty (see STAGE 8b WARN); not running ls against '/'.
=== STAGE 11: poll loop ===

===== poll 1/16  23:26:18 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     48s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:26:16Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-27T23:26:16Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-27T23:26:16Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-27T23:26:16Z [INFO] overlay-normalize(mt5): deleting baked common.ini (foreign [Common] account context blocked by trusted-device check on fresh Wine prefix -- surfaces demo-registration wizard; MT5 recreates the file after Phase 3's per-tenant login)
2026-06-27T23:26:16Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-27T23:26:17Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T23:26:17Z [INFO] auto_login: hard-kill watchdog armed (pid=322, fires at +450s)
2026-06-27T23:26:17Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T23:26:17Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:26:19Z [INFO] auto_login: liveupdate-handler: no active window (skip)
--- :5555 LISTEN state (0A) ---
3148907 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 2/16  23:27:06 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     96s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:26:32Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T23:26:34Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T23:26:36Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T23:26:38Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T23:26:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T23:26:42Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T23:26:44Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T23:26:46Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T23:26:48Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-27T23:26:48Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-27T23:26:48Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-27T23:26:48Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-27T23:26:49Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T23:26:51Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s
2026-06-27T23:26:51Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-27T23:26:52Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-27T23:26:52Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-27T23:26:52Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-27T23:26:54Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-27T23:26:54Z [INFO] auto_login: deliver login: paste succeeded
2026-06-27T23:26:54Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-27T23:26:54Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-27T23:26:54Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-27T23:26:55Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T23:26:55Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T23:26:55Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-27T23:26:56Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T23:26:58Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T23:26:58Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T23:26:58Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T23:26:58Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T23:26:58Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T23:26:59Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T23:26:59Z [INFO] auto_login: clipboard scrubbed
2026-06-27T23:26:59Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:01Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:02Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:03Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:04Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:06Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:07Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:08Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  23:27:49 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     2m19s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:26:54Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-27T23:26:54Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-27T23:26:55Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T23:26:55Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T23:26:55Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-27T23:26:56Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T23:26:58Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T23:26:58Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T23:26:58Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T23:26:58Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T23:26:58Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T23:26:59Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T23:26:59Z [INFO] auto_login: clipboard scrubbed
2026-06-27T23:26:59Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:01Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:02Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:03Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:04Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:06Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:07Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:08Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:09Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:10Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:11Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:12Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:13Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:14Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:15Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:16Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:17Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:19Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:20Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:21Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:22Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:24Z [INFO] auto_login: login-auth wait +21s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:25Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:26Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:27Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:28Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:29Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:30Z [INFO] auto_login: login confirmed via journal at +27s: LR 0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:27:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  23:28:34 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     3m3s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:26:55Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T23:26:55Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T23:26:55Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-27T23:26:56Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T23:26:58Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T23:26:58Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T23:26:58Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T23:26:58Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T23:26:58Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T23:26:59Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T23:26:59Z [INFO] auto_login: clipboard scrubbed
2026-06-27T23:26:59Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:01Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:02Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:03Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:04Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:06Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:07Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:08Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:09Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:10Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:11Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:12Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:13Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:14Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:15Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:16Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:17Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:19Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:20Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:21Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:22Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:24Z [INFO] auto_login: login-auth wait +21s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:25Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:26Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:27Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:28Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:29Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:30Z [INFO] auto_login: login confirmed via journal at +27s: LR 0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:27:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T23:28:31Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T23:28:31Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  23:29:22 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     3m52s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:26:55Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T23:26:55Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T23:26:55Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-27T23:26:56Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-27T23:26:57Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T23:26:58Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T23:26:58Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T23:26:58Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T23:26:58Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T23:26:58Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T23:26:59Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T23:26:59Z [INFO] auto_login: clipboard scrubbed
2026-06-27T23:26:59Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:01Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:02Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:03Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:04Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:06Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:07Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:08Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:09Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:10Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:11Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:12Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:13Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:14Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:15Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:16Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:17Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:19Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:20Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:21Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:22Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:24Z [INFO] auto_login: login-auth wait +21s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:25Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:26Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:27Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:28Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:29Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:30Z [INFO] auto_login: login confirmed via journal at +27s: LR 0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:27:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T23:28:31Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T23:28:31Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  23:30:09 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     4m40s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:26:58Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T23:26:58Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T23:26:59Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T23:26:59Z [INFO] auto_login: clipboard scrubbed
2026-06-27T23:26:59Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:01Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:02Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:03Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:04Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:06Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:07Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:08Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:09Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:10Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:11Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:12Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:13Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:14Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:15Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:16Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:17Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:19Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:20Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:21Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:22Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:24Z [INFO] auto_login: login-auth wait +21s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:25Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:26Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:27Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:28Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:29Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:30Z [INFO] auto_login: login confirmed via journal at +27s: LR 0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:27:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T23:28:31Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T23:28:31Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T23:29:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T23:29:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T23:29:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T23:29:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-27T23:30:11Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-27T23:30:11Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T23:30:11Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:13Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  23:30:59 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     5m29s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:27:17Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:19Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:20Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:21Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:22Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:24Z [INFO] auto_login: login-auth wait +21s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:25Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:26Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:27Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:28Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:29Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:30Z [INFO] auto_login: login confirmed via journal at +27s: LR 0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:27:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T23:28:31Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T23:28:31Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T23:29:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T23:29:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T23:29:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T23:29:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-27T23:30:11Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-27T23:30:11Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T23:30:11Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:13Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:15Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:18Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:20Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:22Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:24Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:27Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:29Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:31Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:34Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:36Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:38Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:41Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:43Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:45Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:47Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:50Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:52Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:54Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:57Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:59Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 8/16  23:31:41 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     6m12s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:27:22Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:24Z [INFO] auto_login: login-auth wait +21s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:25Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:26Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:27Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:28Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:29Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:30Z [INFO] auto_login: login confirmed via journal at +27s: LR 0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:27:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T23:28:31Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T23:28:31Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T23:29:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T23:29:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T23:29:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T23:29:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-27T23:30:11Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-27T23:30:11Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T23:30:11Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:13Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:15Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:18Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:20Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:22Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:24Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:27Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:29Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:31Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:34Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:36Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:38Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:41Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:43Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:45Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:47Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:50Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:52Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:54Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:57Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:59Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:01Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:04Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:06Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:08Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  23:32:30 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     7m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:27:22Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:24Z [INFO] auto_login: login-auth wait +21s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:25Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:26Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:27Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:28Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:29Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:30Z [INFO] auto_login: login confirmed via journal at +27s: LR 0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:27:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T23:28:31Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T23:28:31Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T23:29:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T23:29:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T23:29:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T23:29:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-27T23:30:11Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-27T23:30:11Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T23:30:11Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:13Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:15Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:18Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:20Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:22Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:24Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:27Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:29Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:31Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:34Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:36Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:38Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:41Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:43Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:45Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:47Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:50Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:52Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:54Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:57Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:59Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:01Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:04Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:06Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:08Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  23:33:18 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     7m48s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:27:24Z [INFO] auto_login: login-auth wait +21s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:25Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:26Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:27Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:28Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:29Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:30Z [INFO] auto_login: login confirmed via journal at +27s: LR 0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:27:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T23:28:31Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T23:28:31Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T23:29:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T23:29:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T23:29:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T23:29:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-27T23:30:11Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-27T23:30:11Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T23:30:11Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:13Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:15Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:18Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:20Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:22Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:24Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:27Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:29Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:31Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:34Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:36Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:38Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:41Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:43Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:45Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:47Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:50Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:52Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:54Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:57Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:59Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:01Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:04Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:06Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:08Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:33:18Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  23:34:01 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     8m31s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:27:24Z [INFO] auto_login: login-auth wait +21s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:25Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:26Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:27Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:28Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:29Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:30Z [INFO] auto_login: login confirmed via journal at +27s: LR 0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:27:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T23:28:31Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T23:28:31Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T23:29:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T23:29:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T23:29:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T23:29:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-27T23:30:11Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-27T23:30:11Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T23:30:11Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:13Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:15Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:18Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:20Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:22Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:24Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:27Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:29Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:31Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:34Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:36Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:38Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:41Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:43Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:45Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:47Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:50Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:52Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:54Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:57Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:59Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:01Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:04Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:06Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:08Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:33:18Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 12/16  23:34:44 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     9m14s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:27:25Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:26Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:27Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:28Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:29Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T23:27:30Z [INFO] auto_login: login confirmed via journal at +27s: LR 0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:27:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T23:28:31Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T23:28:31Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T23:29:34Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T23:29:34Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T23:29:34Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T23:29:36Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-27T23:29:36Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-27T23:30:11Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-27T23:30:11Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T23:30:11Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:13Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:15Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:18Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:20Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:22Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:24Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:27Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:29Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:31Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:34Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:36Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:38Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:41Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:43Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:45Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:47Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:50Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:52Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:54Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:57Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:30:59Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:01Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:04Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:06Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:08Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:33:18Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T23:34:31Z [WARN] MetaTrader exited with code 143
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 13/16  23:35:29 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Running   0     9m59s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:31:01Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:04Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:06Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:08Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:33:18Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T23:34:31Z [WARN] MetaTrader exited with code 143
2026-06-27T23:35:01Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T23:35:01Z [INFO] auto_login: hard-kill watchdog armed (pid=4138, fires at +450s)
2026-06-27T23:35:01Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T23:35:01Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:03Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:05Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:08Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:10Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:12Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:14Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:16Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:18Z [INFO] auto_login: liveupdate-handler: active WID=12582913 name='133978149 - Exness-MT5Real9 - Netting - Exness Technologies Ltd - XAUUSDm,H1'
2026-06-27T23:35:21Z [INFO] auto_login: liveupdate-handler: active WID=12582937 name='Login'
2026-06-27T23:35:21Z [INFO] auto_login: Login dialog WID=12582937 detected at +20s
2026-06-27T23:35:21Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-27T23:35:24Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-27T23:35:24Z [INFO] auto_login: deliver login: paste succeeded
2026-06-27T23:35:24Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:24Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582937 name=Login
2026-06-27T23:35:24Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-27T23:35:25Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T23:35:25Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T23:35:25Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:26Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582937 name=Login
2026-06-27T23:35:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582937 name=Login
2026-06-27T23:35:27Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582937 name=Login
2026-06-27T23:35:27Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T23:35:28Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T23:35:28Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T23:35:28Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:28Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582937 name=Login
2026-06-27T23:35:28Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T23:35:29Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-27T23:35:29Z [INFO] auto_login: clipboard scrubbed
2026-06-27T23:35:29Z [INFO] auto_login: login confirmed via journal at +0s: LR  0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:35:29Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 14/16  23:36:18 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Terminating   0     10m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:31:01Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:04Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:06Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:08Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:33:18Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T23:34:31Z [WARN] MetaTrader exited with code 143
2026-06-27T23:35:01Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T23:35:01Z [INFO] auto_login: hard-kill watchdog armed (pid=4138, fires at +450s)
2026-06-27T23:35:01Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T23:35:01Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:03Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:05Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:08Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:10Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:12Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:14Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:16Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:18Z [INFO] auto_login: liveupdate-handler: active WID=12582913 name='133978149 - Exness-MT5Real9 - Netting - Exness Technologies Ltd - XAUUSDm,H1'
2026-06-27T23:35:21Z [INFO] auto_login: liveupdate-handler: active WID=12582937 name='Login'
2026-06-27T23:35:21Z [INFO] auto_login: Login dialog WID=12582937 detected at +20s
2026-06-27T23:35:21Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-27T23:35:24Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-27T23:35:24Z [INFO] auto_login: deliver login: paste succeeded
2026-06-27T23:35:24Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:24Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582937 name=Login
2026-06-27T23:35:24Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-27T23:35:25Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T23:35:25Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T23:35:25Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:26Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582937 name=Login
2026-06-27T23:35:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582937 name=Login
2026-06-27T23:35:27Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582937 name=Login
2026-06-27T23:35:27Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T23:35:28Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T23:35:28Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T23:35:28Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:28Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582937 name=Login
2026-06-27T23:35:28Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T23:35:29Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-27T23:35:29Z [INFO] auto_login: clipboard scrubbed
2026-06-27T23:35:29Z [INFO] auto_login: login confirmed via journal at +0s: LR  0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:35:29Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

===== poll 15/16  23:37:13 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Terminating   0     11m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:31:01Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:04Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:06Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:08Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:33:18Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T23:34:31Z [WARN] MetaTrader exited with code 143
2026-06-27T23:35:01Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T23:35:01Z [INFO] auto_login: hard-kill watchdog armed (pid=4138, fires at +450s)
2026-06-27T23:35:01Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T23:35:01Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:03Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:05Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:08Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:10Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:12Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:14Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:16Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:18Z [INFO] auto_login: liveupdate-handler: active WID=12582913 name='133978149 - Exness-MT5Real9 - Netting - Exness Technologies Ltd - XAUUSDm,H1'
2026-06-27T23:35:21Z [INFO] auto_login: liveupdate-handler: active WID=12582937 name='Login'
2026-06-27T23:35:21Z [INFO] auto_login: Login dialog WID=12582937 detected at +20s
2026-06-27T23:35:21Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-27T23:35:24Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-27T23:35:24Z [INFO] auto_login: deliver login: paste succeeded
2026-06-27T23:35:24Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:24Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582937 name=Login
2026-06-27T23:35:24Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-27T23:35:25Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T23:35:25Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T23:35:25Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:26Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582937 name=Login
2026-06-27T23:35:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582937 name=Login
2026-06-27T23:35:27Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582937 name=Login
2026-06-27T23:35:27Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T23:35:28Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T23:35:28Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T23:35:28Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:28Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582937 name=Login
2026-06-27T23:35:28Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T23:35:29Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-27T23:35:29Z [INFO] auto_login: clipboard scrubbed
2026-06-27T23:35:29Z [INFO] auto_login: login confirmed via journal at +0s: LR  0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:35:29Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

===== poll 16/16  23:38:02 =====
etradie-mt-4cd46a6a-5d7-0   2/3   Terminating   0     12m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T23:31:01Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:04Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:06Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:31:08Z [INFO] auto_login: dismiss follow-up window: 'Open' (WID=12582949)
2026-06-27T23:33:18Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T23:34:31Z [WARN] MetaTrader exited with code 143
2026-06-27T23:35:01Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T23:35:01Z [INFO] auto_login: hard-kill watchdog armed (pid=4138, fires at +450s)
2026-06-27T23:35:01Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T23:35:01Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:03Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:05Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:08Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:10Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:12Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:14Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:16Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T23:35:18Z [INFO] auto_login: liveupdate-handler: active WID=12582913 name='133978149 - Exness-MT5Real9 - Netting - Exness Technologies Ltd - XAUUSDm,H1'
2026-06-27T23:35:21Z [INFO] auto_login: liveupdate-handler: active WID=12582937 name='Login'
2026-06-27T23:35:21Z [INFO] auto_login: Login dialog WID=12582937 detected at +20s
2026-06-27T23:35:21Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582937 name=Login
2026-06-27T23:35:22Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-27T23:35:24Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-27T23:35:24Z [INFO] auto_login: deliver login: paste succeeded
2026-06-27T23:35:24Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:24Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582937 name=Login
2026-06-27T23:35:24Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-27T23:35:25Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T23:35:25Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T23:35:25Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:26Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582937 name=Login
2026-06-27T23:35:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582937 name=Login
2026-06-27T23:35:27Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582937 name=Login
2026-06-27T23:35:27Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T23:35:28Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T23:35:28Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T23:35:28Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582937 name=Login
2026-06-27T23:35:28Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582937 name=Login
2026-06-27T23:35:28Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T23:35:29Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-27T23:35:29Z [INFO] auto_login: clipboard scrubbed
2026-06-27T23:35:29Z [INFO] auto_login: login confirmed via journal at +0s: LR  0       23:27:02.108    Network '133978149': trading has been enabled - hedging mode
2026-06-27T23:35:29Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")
=== STAGE 12: final artifacts ===
OK: screen-poll-01.png
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
Error from server (NotFound): pods "etradie-mt-4cd46a6a-5d7-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-4cd46a6a-5d7-0" not found
--- journal head/tail (broker handshake) ---
(MT_DIR empty; journal/EA log not collected)
...
(MT_DIR empty; journal/EA log not collected)
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 4cd46a6a-5d72-495d-9c69-75302aec391f | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260627T232305Z ===
total 22368
drwxr-xr-x  2 softverse softverse    4096 Jun 28 00:38 .
drwxr-xr-x 27 softverse softverse    4096 Jun 28 00:23 ..
-rw-r--r--  1 softverse softverse     110 Jun 28 00:38 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 28 00:38 driver-log-full.txt
-rw-r--r--  1 softverse softverse      45 Jun 28 00:38 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 28 00:23 engine-env.txt
-rw-r--r--  1 softverse softverse       1 Jun 28 00:26 mt-config-dir.txt
-rw-r--r--  1 softverse softverse       1 Jun 28 00:26 mt-dir.txt
-rw-r--r--  1 softverse softverse      45 Jun 28 00:38 mt5-journal.txt
-rw-r--r--  1 softverse softverse      71 Jun 28 00:26 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse    1484 Jun 28 00:26 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 28 00:23 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 28 00:25 release.txt
-rw-r--r--  1 softverse softverse    3676 Jun 28 00:38 screen-poll-01.png
-rw-r--r--  1 softverse softverse 3148907 Jun 28 00:26 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   52734 Jun 28 00:38 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:27 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse   52696 Jun 28 00:38 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:28 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse   53119 Jun 28 00:38 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:28 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   52755 Jun 28 00:38 screen-poll-05.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:29 screen-poll-05.xwd
-rw-r--r--  1 softverse softverse   67661 Jun 28 00:38 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:30 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   67846 Jun 28 00:38 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:31 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse   67745 Jun 28 00:38 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:31 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse   67639 Jun 28 00:38 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:32 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse   67759 Jun 28 00:38 screen-poll-10.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:33 screen-poll-10.xwd
-rw-r--r--  1 softverse softverse   67753 Jun 28 00:38 screen-poll-11.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:34 screen-poll-11.xwd
-rw-r--r--  1 softverse softverse     278 Jun 28 00:38 screen-poll-12.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:34 screen-poll-12.xwd
-rw-r--r--  1 softverse softverse   66459 Jun 28 00:38 screen-poll-13.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 00:35 screen-poll-13.xwd
-rw-r--r--  1 softverse softverse      23 Jun 28 00:25 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 28 00:38 windows-final.txt
-rw-r--r--  1 softverse softverse      48 Jun 28 00:26 windows-poll-01.txt
-rw-r--r--  1 softverse softverse      80 Jun 28 00:27 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      80 Jun 28 00:28 windows-poll-03.txt
-rw-r--r--  1 softverse softverse      80 Jun 28 00:28 windows-poll-04.txt
-rw-r--r--  1 softverse softverse     116 Jun 28 00:29 windows-poll-05.txt
-rw-r--r--  1 softverse softverse     116 Jun 28 00:30 windows-poll-06.txt
-rw-r--r--  1 softverse softverse     116 Jun 28 00:31 windows-poll-07.txt
-rw-r--r--  1 softverse softverse     116 Jun 28 00:32 windows-poll-08.txt
-rw-r--r--  1 softverse softverse     116 Jun 28 00:32 windows-poll-09.txt
-rw-r--r--  1 softverse softverse     116 Jun 28 00:33 windows-poll-10.txt
-rw-r--r--  1 softverse softverse     116 Jun 28 00:34 windows-poll-11.txt
-rw-r--r--  1 softverse softverse       0 Jun 28 00:34 windows-poll-12.txt
-rw-r--r--  1 softverse softverse      42 Jun 28 00:35 windows-poll-13.txt
-rw-r--r--  1 softverse softverse      94 Jun 28 00:36 windows-poll-14.txt
-rw-r--r--  1 softverse softverse      94 Jun 28 00:37 windows-poll-15.txt
-rw-r--r--  1 softverse softverse      94 Jun 28 00:38 windows-poll-16.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260627T232305Z
softverse@Softverse:~/hostedmt-diagnostics/20260627T232305Z$