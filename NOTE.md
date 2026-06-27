=== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 11:37:50
=== STAGE 7: race to the pod ===
Release: etradie-mt-3a726160-860
POD=etradie-mt-3a726160-860-0
[1] mt-node state: {"running":{"startedAt":"2026-06-27T11:37:44Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:b599bbb10726e0f16c03150b94d2173d2848a47e
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:b599bbb10726e0f16c03150b94d2173d2848a47e
=== STAGE 8: broker-bundle initContainer log ===
Downloading https://pub-5bdcacdedad6458298e8b8d5435f301a.r2.dev/broker-bundles/exness-portable.zip...
/broker-bundle/bundle.zip: OK
Bundle extracted successfully.
Expect: 'Downloading ...exness-portable.zip', 'eadee9c7... OK', 'Bundle extracted successfully.'
=== STAGE 8b: discover MT_DIR (branded root) + MT_CONFIG_DIR ===
MT_DIR/MT_CONFIG_DIR resolved from entrypoint log.
Discovered MT_DIR: '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS'
Discovered MT_CONFIG_DIR: '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
=== STAGE 9: tools + fluxbox EWMH ===
/usr/bin/xdotool
/usr/bin/xclip
/usr/bin/xprop
/usr/bin/xwd
/usr/bin/fluxbox
---
xclip version 0.13
2026-06-27T11:38:16Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-27T11:38:16Z [INFO] fluxbox ready (pid=192); _NET_ACTIVE_WINDOW available
2026-06-27T11:38:17Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T11:38:17Z [INFO] auto_login: hard-kill watchdog armed (pid=292, fires at +450s)
 _NET_ACTIVE_WINDOW
=== STAGE 10: overlay normalizer + config-resolve log lines ===
2026-06-27T11:38:16Z [INFO] broker-bundle overlay: cp -a '/broker-bundle/MetaTrader 5 EXNESS/.' -> '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/'
2026-06-27T11:38:17Z [INFO] broker-bundle overlay: complete; sentinel written at '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/.bundle-installed-from-eadee9c7a152514f9c904b381a9416cf3d88dc5e480a12a62544079743c5e11c'
2026-06-27T11:38:17Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-27T11:38:17Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-27T11:38:17Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-27T11:38:17Z [INFO] overlay-normalize(mt5): deleting baked common.ini (foreign [Common] account context blocked by trusted-device check on fresh Wine prefix -- surfaces demo-registration wizard; MT5 recreates the file after Phase 3's per-tenant login)
2026-06-27T11:38:17Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-27T11:38:17Z [INFO] broker-bundle overlay summary: branded_terminal='/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/terminal64.exe', size=118840944, sha256=e87e8b77fa415fc91e9acbe692826e76b7907fb53db4244aed36618f9af30b9e, bundle_sha256=eadee9c7a152514f9c904b381a9416cf3d88dc5e480a12a62544079743c5e11c

Expect lines like:
  overlay-normalize(mt5): stripping baked Profiles/Charts workspace
  overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
  overlay-normalize(mt5): removing baked common.ini ...
  overlay-normalize(mt5): removing baked accounts.dat ...
  overlay-normalize: canonical config dir resolved to '<MT_DIR>/Config'
=== STAGE 10b: assert baked state was actually neutralized ===
--- Profiles/Charts (MUST be absent or empty) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Profiles/Charts': No such file or directory
total 12
drwxr-sr-x 3 mt mt 4096 Jun 27 11:38 .
drwxr-sr-x 7 mt mt 4096 Jun 27 11:38 ..
--- common.ini (MUST be absent until MT5 recreates it) ---
-rw-r--r-- 1 mt mt 586 Jun 27 11:38 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/common.ini
--- stray lowercase config dir (MUST be absent on Deriv after de-dup) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/config': No such file or directory
--- expert.tpl co-located with the .set (BOTH MUST exist) ---
-rw-r--r-- 1 mt mt 224 Jun 27 11:38 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/MQL5/Profiles/Templates/ZeroMQ_EA.set
-rw-r--r-- 1 mt mt  64 Jun 27 11:38 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/MQL5/Profiles/Templates/expert.tpl
--- expert.tpl legacy mirror ---
-rw-r--r-- 1 mt mt 64 Jun 27 11:38 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Profiles/Templates/expert.tpl
--- our startup.ini in the resolved config dir ---
-rw-r--r-- 1 mt mt 238 Jun 27 11:38 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/startup.ini
--- servers.dat present (broker server list) ---
-rw-r--r-- 1 mt mt 472364 Jun 27 11:38 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/servers.dat
=== STAGE 11: poll loop ===

===== poll 1/16  11:38:50 =====
etradie-mt-3a726160-860-0   2/3   Running   0     82s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T11:38:17Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-27T11:38:17Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-27T11:38:17Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-27T11:38:17Z [INFO] overlay-normalize(mt5): deleting baked common.ini (foreign [Common] account context blocked by trusted-device check on fresh Wine prefix -- surfaces demo-registration wizard; MT5 recreates the file after Phase 3's per-tenant login)
2026-06-27T11:38:17Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-27T11:38:17Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T11:38:17Z [INFO] auto_login: hard-kill watchdog armed (pid=292, fires at +450s)
2026-06-27T11:38:17Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T11:38:18Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T11:38:20Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T11:38:22Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T11:38:24Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T11:38:26Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T11:38:28Z [INFO] auto_login: liveupdate-handler: active WID=10485784 name=''
2026-06-27T11:38:30Z [INFO] auto_login: liveupdate-handler: active WID=10485784 name=''
2026-06-27T11:38:32Z [INFO] auto_login: liveupdate-handler: active WID=10485784 name=''
2026-06-27T11:38:35Z [INFO] auto_login: liveupdate-handler: active WID=10485784 name=''
2026-06-27T11:38:37Z [INFO] auto_login: liveupdate-handler: active WID=10485784 name=''
2026-06-27T11:38:39Z [INFO] auto_login: liveupdate-handler: active WID=10485784 name=''
2026-06-27T11:38:41Z [INFO] auto_login: liveupdate-handler: active WID=10485784 name=''
2026-06-27T11:38:43Z [INFO] auto_login: liveupdate-handler: active WID=10485784 name=''
2026-06-27T11:38:45Z [INFO] auto_login: liveupdate-handler: active WID=10485784 name=''
2026-06-27T11:38:47Z [INFO] auto_login: liveupdate-handler: active WID=10485784 name=''
2026-06-27T11:38:47Z [INFO] auto_login: main UI window WID=10485761 detected at +30s; entering Phase 2c (3-attempt menu invocation)
2026-06-27T11:38:47Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=10485761, Alt+F then L)
2026-06-27T11:38:47Z [INFO] auto_login: blocking modal detected (WID=10485784, NAME=); attempting dismiss
2026-06-27T11:38:47Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:38:49Z [INFO] auto_login: Login dialog WID=10485786 appeared after mnemonic at +32s
2026-06-27T11:38:49Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=10485786 name=Login
2026-06-27T11:38:50Z [INFO] auto_login: phase3 stage=post_activate focused_wid=10485786 name=Login
2026-06-27T11:38:51Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=10485786 name=Login
2026-06-27T11:38:51Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-27T11:38:52Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-27T11:38:52Z [INFO] auto_login: deliver login: paste succeeded
2026-06-27T11:38:52Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=10485786 name=Login
2026-06-27T11:38:53Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=10485786 name=Login
2026-06-27T11:38:53Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
-rw-r--r-- 1 mt mt 6279 Jun 27 11:39 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/accounts.dat
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 2/16  11:39:50 =====
etradie-mt-3a726160-860-0   2/3   Running   0     2m24s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T11:38:53Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-27T11:38:54Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T11:38:54Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T11:38:54Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=10485786 name=Login
2026-06-27T11:38:54Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=10485786 name=Login
2026-06-27T11:38:55Z [INFO] auto_login: phase3 stage=after_space focused_wid=10485786 name=Login
2026-06-27T11:38:55Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=10485786 name=Login
2026-06-27T11:38:55Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T11:38:57Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T11:38:57Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T11:38:57Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=10485786 name=Login
2026-06-27T11:38:57Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=10485786 name=Login
2026-06-27T11:38:57Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T11:38:58Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=10485761 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T11:38:58Z [INFO] auto_login: clipboard scrubbed
2026-06-27T11:38:58Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T11:38:59Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:00Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:02Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:03Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:04Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:05Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:06Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:07Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:09Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:10Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:11Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:12Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:13Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:14Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:15Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:16Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:17Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:18Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:20Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:21Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:22Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:23Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:25Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:26Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:27Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:28Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:29Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:30Z [INFO] auto_login: login confirmed via journal at +28s: LE 0       11:38:59.798    Network '133978149': trading has been enabled - hedging mode
2026-06-27T11:39:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
-rw-r--r-- 1 mt mt 6279 Jun 27 11:39 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/accounts.dat
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  11:41:25 =====
etradie-mt-3a726160-860-0   2/3   Running   0     3m55s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T11:38:54Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T11:38:54Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=10485786 name=Login
2026-06-27T11:38:54Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=10485786 name=Login
2026-06-27T11:38:55Z [INFO] auto_login: phase3 stage=after_space focused_wid=10485786 name=Login
2026-06-27T11:38:55Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=10485786 name=Login
2026-06-27T11:38:55Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T11:38:57Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T11:38:57Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T11:38:57Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=10485786 name=Login
2026-06-27T11:38:57Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=10485786 name=Login
2026-06-27T11:38:57Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T11:38:58Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=10485761 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T11:38:58Z [INFO] auto_login: clipboard scrubbed
2026-06-27T11:38:58Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T11:38:59Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:00Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:02Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:03Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:04Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:05Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:06Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:07Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:09Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:10Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:11Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:12Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:13Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:14Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:15Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:16Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:17Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:18Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:20Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:21Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:22Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:23Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:25Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:26Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:27Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:28Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:29Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:30Z [INFO] auto_login: login confirmed via journal at +28s: LE 0       11:38:59.798    Network '133978149': trading has been enabled - hedging mode
2026-06-27T11:39:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T11:40:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T11:40:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
-rw-r--r-- 1 mt mt 6279 Jun 27 11:39 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/accounts.dat
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  11:42:29 =====
etradie-mt-3a726160-860-0   2/3   Running   0     5m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T11:38:57Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T11:38:58Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=10485761 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T11:38:58Z [INFO] auto_login: clipboard scrubbed
2026-06-27T11:38:58Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T11:38:59Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:00Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:02Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:03Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:04Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:05Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:06Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:07Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:09Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:10Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:11Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:12Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:13Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:14Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:15Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:16Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:17Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:18Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:20Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:21Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:22Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:23Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:25Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:26Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:27Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:28Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:29Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:30Z [INFO] auto_login: login confirmed via journal at +28s: LE 0       11:38:59.798    Network '133978149': trading has been enabled - hedging mode
2026-06-27T11:39:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T11:40:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T11:40:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T11:41:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T11:41:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T11:41:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:42:07Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T11:42:12Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T11:42:12Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:42:13Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T11:42:15Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=10485761 visible after keystroke sequence
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
-rw-r--r-- 1 mt mt 6279 Jun 27 11:39 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/accounts.dat
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  11:43:24 =====
etradie-mt-3a726160-860-0   2/3   Running   0     5m55s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T11:39:04Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:05Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:06Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:07Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:09Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:10Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:11Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:12Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:13Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:14Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:15Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:16Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:17Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:18Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:20Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:21Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:22Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:23Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:25Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:26Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:27Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:28Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:29Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:30Z [INFO] auto_login: login confirmed via journal at +28s: LE 0       11:38:59.798    Network '133978149': trading has been enabled - hedging mode
2026-06-27T11:39:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T11:40:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T11:40:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T11:41:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T11:41:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T11:41:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:42:07Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T11:42:12Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T11:42:12Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:42:13Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T11:42:15Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:42:45Z [WARN] auto_login: phase5: attempt 2: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T11:42:50Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): clearing modals + activating main window
2026-06-27T11:42:50Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:42:51Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): dispatching keystroke sequence [alt+f Right Down Right Return]
2026-06-27T11:42:53Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:43:23Z [WARN] auto_login: phase5: attempt 3: chart opened but :5555 not bound within budget
2026-06-27T11:43:23Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T11:43:23Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
-rw-r--r-- 1 mt mt 6279 Jun 27 11:39 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/accounts.dat
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  11:44:18 =====
etradie-mt-3a726160-860-0   2/3   Running   0     6m49s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T11:39:04Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:05Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:06Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:07Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:09Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:10Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:11Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:12Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:13Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:14Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:15Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:16Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:17Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:18Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:20Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:21Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:22Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:23Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:25Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:26Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:27Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:28Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:29Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:30Z [INFO] auto_login: login confirmed via journal at +28s: LE 0       11:38:59.798    Network '133978149': trading has been enabled - hedging mode
2026-06-27T11:39:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T11:40:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T11:40:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T11:41:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T11:41:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T11:41:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:42:07Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T11:42:12Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T11:42:12Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:42:13Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T11:42:15Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:42:45Z [WARN] auto_login: phase5: attempt 2: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T11:42:50Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): clearing modals + activating main window
2026-06-27T11:42:50Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:42:51Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): dispatching keystroke sequence [alt+f Right Down Right Return]
2026-06-27T11:42:53Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:43:23Z [WARN] auto_login: phase5: attempt 3: chart opened but :5555 not bound within budget
2026-06-27T11:43:23Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T11:43:23Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
-rw-r--r-- 1 mt mt 6279 Jun 27 11:39 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/accounts.dat
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  11:45:11 =====
etradie-mt-3a726160-860-0   2/3   Running   0     7m42s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T11:39:04Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:05Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:06Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:07Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:09Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:10Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:11Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:12Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:13Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:14Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:15Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:16Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:17Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:18Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:20Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:21Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:22Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:23Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:25Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:26Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:27Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:28Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:29Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:30Z [INFO] auto_login: login confirmed via journal at +28s: LE 0       11:38:59.798    Network '133978149': trading has been enabled - hedging mode
2026-06-27T11:39:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T11:40:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T11:40:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T11:41:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T11:41:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T11:41:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:42:07Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T11:42:12Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T11:42:12Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:42:13Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T11:42:15Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:42:45Z [WARN] auto_login: phase5: attempt 2: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T11:42:50Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): clearing modals + activating main window
2026-06-27T11:42:50Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:42:51Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): dispatching keystroke sequence [alt+f Right Down Right Return]
2026-06-27T11:42:53Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:43:23Z [WARN] auto_login: phase5: attempt 3: chart opened but :5555 not bound within budget
2026-06-27T11:43:23Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T11:43:23Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
-rw-r--r-- 1 mt mt 6279 Jun 27 11:39 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/accounts.dat
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names
m
===== poll 8/16  11:46:08 =====
etradie-mt-3a726160-860-0   2/3   Running   0     8m39s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T11:39:05Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:06Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:07Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:09Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:10Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:11Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:12Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:13Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:14Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:15Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:16Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:17Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:18Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:20Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:21Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:22Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:23Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:25Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:26Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:27Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:28Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:29Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:30Z [INFO] auto_login: login confirmed via journal at +28s: LE 0       11:38:59.798    Network '133978149': trading has been enabled - hedging mode
2026-06-27T11:39:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T11:40:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T11:40:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T11:41:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T11:41:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T11:41:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:42:07Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T11:42:12Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T11:42:12Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:42:13Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T11:42:15Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:42:45Z [WARN] auto_login: phase5: attempt 2: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T11:42:50Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): clearing modals + activating main window
2026-06-27T11:42:50Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:42:51Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): dispatching keystroke sequence [alt+f Right Down Right Return]
2026-06-27T11:42:53Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:43:23Z [WARN] auto_login: phase5: attempt 3: chart opened but :5555 not bound within budget
2026-06-27T11:43:23Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T11:43:23Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T11:45:18Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
-rw-r--r-- 1 mt mt 6279 Jun 27 11:39 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/accounts.dat
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  11:47:02 =====
etradie-mt-3a726160-860-0   2/3   Running   0     9m34s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T11:39:15Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:16Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:17Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:18Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:20Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:21Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:22Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:23Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:25Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:26Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:27Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:28Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:29Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T11:39:30Z [INFO] auto_login: login confirmed via journal at +28s: LE 0       11:38:59.798    Network '133978149': trading has been enabled - hedging mode
2026-06-27T11:39:30Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T11:40:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T11:40:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T11:41:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-27T11:41:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:41:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-27T11:41:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:42:07Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T11:42:12Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): clearing modals + activating main window
2026-06-27T11:42:12Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:42:13Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T11:42:15Z [INFO] auto_login: phase5: attempt 2 (Alt+F New Chart → first category): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:42:45Z [WARN] auto_login: phase5: attempt 2: chart opened but :5555 not bound within budget; falling through to next attempt
2026-06-27T11:42:50Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): clearing modals + activating main window
2026-06-27T11:42:50Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T11:42:51Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): dispatching keystroke sequence [alt+f Right Down Right Return]
2026-06-27T11:42:53Z [INFO] auto_login: phase5: attempt 3 (Alt+F New Chart → second category): chart window WID=10485761 visible after keystroke sequence
2026-06-27T11:43:23Z [WARN] auto_login: phase5: attempt 3: chart opened but :5555 not bound within budget
2026-06-27T11:43:23Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T11:43:23Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T11:45:18Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T11:46:30Z [WARN] MetaTrader exited with code 143
2026-06-27T11:47:00Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T11:47:00Z [INFO] auto_login: hard-kill watchdog armed (pid=4044, fires at +450s)
2026-06-27T11:47:00Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T11:47:00Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T11:47:03Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T11:47:05Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T11:47:07Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T11:47:09Z [INFO] auto_login: liveupdate-handler: no active window (skip)
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
-rw-r--r-- 1 mt mt 6279 Jun 27 11:47 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config/accounts.dat
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  11:48:05 =====
Error from server (NotFound): pods "etradie-mt-3a726160-860-0" not found
POD GONE
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
=== STAGE 13: verdict ===
Error from server (NotFound): pods "etradie-mt-3a726160-860-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-3a726160-860-0" not found
--- journal head/tail (broker handshake) ---
Error from server (NotFound): pods "etradie-mt-3a726160-860-0" not found
...
Error from server (NotFound): pods "etradie-mt-3a726160-860-0" not found
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 3a726160-8609-4a37-a224-c02e6ae99336 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260627T113355Z ===
total 14568
drwxr-xr-x  2 softverse softverse    4096 Jun 27 12:48 .
drwxr-xr-x 23 softverse softverse    4096 Jun 27 12:33 ..
-rw-r--r--  1 softverse softverse     110 Jun 27 12:48 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 27 12:48 driver-log-full.txt
-rw-r--r--  1 softverse softverse      73 Jun 27 12:48 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 27 12:34 engine-env.txt
-rw-r--r--  1 softverse softverse      71 Jun 27 12:38 mt-config-dir.txt
-rw-r--r--  1 softverse softverse      64 Jun 27 12:38 mt-dir.txt
-rw-r--r--  1 softverse softverse      73 Jun 27 12:48 mt5-journal.txt
-rw-r--r--  1 softverse softverse    1472 Jun 27 12:38 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse    1484 Jun 27 12:38 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 27 12:33 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 27 12:37 release.txt
-rw-r--r--  1 softverse softverse   57678 Jun 27 12:48 screen-poll-01.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 12:39 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   57475 Jun 27 12:48 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 12:40 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse   64209 Jun 27 12:48 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 12:41 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse   72163 Jun 27 12:48 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 12:42 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   71957 Jun 27 12:48 screen-poll-05.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 12:43 screen-poll-05.xwd
-rw-r--r--  1 softverse softverse   72003 Jun 27 12:48 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 12:44 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   71864 Jun 27 12:48 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 12:45 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse   71986 Jun 27 12:48 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 12:46 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse   72795 Jun 27 12:48 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 12:47 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse      23 Jun 27 12:37 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 27 12:48 windows-final.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 12:39 windows-poll-01.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 12:40 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      93 Jun 27 12:41 windows-poll-03.txt
-rw-r--r--  1 softverse softverse      93 Jun 27 12:42 windows-poll-04.txt
-rw-r--r--  1 softverse softverse      93 Jun 27 12:43 windows-poll-05.txt
-rw-r--r--  1 softverse softverse      93 Jun 27 12:44 windows-poll-06.txt
-rw-r--r--  1 softverse softverse      93 Jun 27 12:45 windows-poll-07.txt
-rw-r--r--  1 softverse softverse       0 Jun 27 12:46 windows-poll-08.txt
-rw-r--r--  1 softverse softverse      42 Jun 27 12:47 windows-poll-09.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260627T113355Z
softverse@Softverse:~/hostedmt-diagnostics/20260627T113355Z$