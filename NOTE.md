────────────ee attempts failed' driver-log-full.txt | tail -10 -20ll present' driver-log-full.txt
=== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 20:24:35
=== STAGE 7: race to the pod ===
Release: etradie-mt-e7c75bcb-d6e
POD=etradie-mt-e7c75bcb-d6e-0
[1] mt-node state: {"running":{"startedAt":"2026-06-26T20:24:38Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:6f01951cd964cf01fd16ffa6883a884f3f8afdaf
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:6f01951cd964cf01fd16ffa6883a884f3f8afdaf
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

===== poll 1/16  20:25:05 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     43s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
tar: Removing leading `/' from member names

===== poll 2/16  20:25:46 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     83s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:25:15Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T20:25:15Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T20:25:15Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T20:25:15Z [INFO] overlay-normalize(mt5): deleting baked common.ini (foreign [Common] account context blocked by trusted-device check on fresh Wine prefix -- surfaces demo-registration wizard; MT5 recreates the file after Phase 3's per-tenant login)
2026-06-26T20:25:15Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-26T20:25:16Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T20:25:16Z [INFO] auto_login: hard-kill watchdog armed (pid=345, fires at +450s)
2026-06-26T20:25:16Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T20:25:16Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T20:25:18Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T20:25:20Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T20:25:22Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T20:25:25Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T20:25:27Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T20:25:29Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T20:25:31Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T20:25:33Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T20:25:35Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T20:25:37Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T20:25:39Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T20:25:41Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T20:25:43Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T20:25:45Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T20:25:48Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T20:25:48Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-26T20:25:48Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-26T20:25:48Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-26T20:25:48Z [INFO] auto_login: main window is active; modals cleared
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  20:26:30 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     2m7s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:25:55Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-26T20:25:55Z [INFO] auto_login: deliver password: paste succeeded
2026-06-26T20:25:55Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-26T20:25:55Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-26T20:25:55Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-26T20:25:56Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-26T20:25:56Z [INFO] auto_login: deliver server: paste succeeded
2026-06-26T20:25:56Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-26T20:25:57Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-26T20:25:58Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-26T20:25:58Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-26T20:25:58Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-26T20:25:59Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-26T20:25:59Z [INFO] auto_login: clipboard scrubbed
2026-06-26T20:25:59Z [INFO] auto_login: login-auth wait +0s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:00Z [INFO] auto_login: login-auth wait +1s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:01Z [INFO] auto_login: login-auth wait +2s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:02Z [INFO] auto_login: login-auth wait +3s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:03Z [INFO] auto_login: login-auth wait +4s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:05Z [INFO] auto_login: login-auth wait +5s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:06Z [INFO] auto_login: login-auth wait +6s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:07Z [INFO] auto_login: login-auth wait +7s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:08Z [INFO] auto_login: login-auth wait +8s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:09Z [INFO] auto_login: login-auth wait +9s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:10Z [INFO] auto_login: login-auth wait +10s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:11Z [INFO] auto_login: login-auth wait +11s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:12Z [INFO] auto_login: login-auth wait +12s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:14Z [INFO] auto_login: login-auth wait +13s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:15Z [INFO] auto_login: login-auth wait +14s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:16Z [INFO] auto_login: login-auth wait +15s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:17Z [INFO] auto_login: login-auth wait +16s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:18Z [INFO] auto_login: login-auth wait +17s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:19Z [INFO] auto_login: login-auth wait +18s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:20Z [INFO] auto_login: login-auth wait +19s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:21Z [INFO] auto_login: login-auth wait +20s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:23Z [INFO] auto_login: login-auth wait +21s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:24Z [INFO] auto_login: login-auth wait +22s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:26Z [INFO] auto_login: login-auth wait +23s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:27Z [INFO] auto_login: login-auth wait +24s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:28Z [INFO] auto_login: login-auth wait +25s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:29Z [INFO] auto_login: login-auth wait +26s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:30Z [INFO] auto_login: login-auth wait +27s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:31Z [INFO] auto_login: login-auth wait +28s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:32Z [INFO] auto_login: login-auth wait +29s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:33Z [INFO] auto_login: login-auth wait +30s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  20:27:20 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     2m58s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:26:35Z [INFO] auto_login: login-auth wait +32s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:37Z [INFO] auto_login: login-auth wait +33s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:38Z [INFO] auto_login: login-auth wait +34s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:39Z [INFO] auto_login: login-auth wait +35s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:40Z [INFO] auto_login: login-auth wait +36s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:41Z [INFO] auto_login: login-auth wait +37s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:42Z [INFO] auto_login: login-auth wait +38s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:43Z [INFO] auto_login: login-auth wait +39s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:44Z [INFO] auto_login: login-auth wait +40s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:45Z [INFO] auto_login: login-auth wait +41s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:46Z [INFO] auto_login: login-auth wait +42s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:48Z [INFO] auto_login: login-auth wait +43s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:49Z [INFO] auto_login: login-auth wait +44s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:50Z [INFO] auto_login: login-auth wait +45s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:51Z [INFO] auto_login: login-auth wait +46s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:52Z [INFO] auto_login: login-auth wait +47s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:53Z [INFO] auto_login: login-auth wait +48s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:54Z [INFO] auto_login: login-auth wait +49s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:55Z [INFO] auto_login: login-auth wait +50s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:56Z [INFO] auto_login: login-auth wait +51s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:57Z [INFO] auto_login: login-auth wait +52s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:26:58Z [INFO] auto_login: login-auth wait +53s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:00Z [INFO] auto_login: login-auth wait +54s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:01Z [INFO] auto_login: login-auth wait +55s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:02Z [INFO] auto_login: login-auth wait +56s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:03Z [INFO] auto_login: login-auth wait +57s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:04Z [INFO] auto_login: login-auth wait +58s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:05Z [INFO] auto_login: login-auth wait +59s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:06Z [INFO] auto_login: login-auth wait +60s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:07Z [INFO] auto_login: login-auth wait +61s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:08Z [INFO] auto_login: login-auth wait +62s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:10Z [INFO] auto_login: login-auth wait +63s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:11Z [INFO] auto_login: login-auth wait +64s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:12Z [INFO] auto_login: login-auth wait +65s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:13Z [INFO] auto_login: login-auth wait +66s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:14Z [INFO] auto_login: login-auth wait +67s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:15Z [INFO] auto_login: login-auth wait +68s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:16Z [INFO] auto_login: login-auth wait +69s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:17Z [INFO] auto_login: login-auth wait +70s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:18Z [INFO] auto_login: login-auth wait +71s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:19Z [INFO] auto_login: login-auth wait +72s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:20Z [INFO] auto_login: login-auth wait +73s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:22Z [INFO] auto_login: login-auth wait +74s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:23Z [INFO] auto_login: login-auth wait +75s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:24Z [INFO] auto_login: login-auth wait +76s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  20:28:06 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     3m43s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:27:19Z [INFO] auto_login: login-auth wait +72s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:20Z [INFO] auto_login: login-auth wait +73s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:22Z [INFO] auto_login: login-auth wait +74s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:23Z [INFO] auto_login: login-auth wait +75s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:24Z [INFO] auto_login: login-auth wait +76s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:25Z [INFO] auto_login: login-auth wait +77s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:26Z [INFO] auto_login: login-auth wait +78s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:27Z [INFO] auto_login: login-auth wait +79s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:28Z [INFO] auto_login: login-auth wait +80s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:29Z [INFO] auto_login: login-auth wait +81s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:30Z [INFO] auto_login: login-auth wait +82s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:32Z [INFO] auto_login: login-auth wait +83s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:33Z [INFO] auto_login: login-auth wait +84s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:34Z [INFO] auto_login: login-auth wait +85s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:35Z [INFO] auto_login: login-auth wait +86s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:36Z [INFO] auto_login: login-auth wait +87s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:37Z [INFO] auto_login: login-auth wait +88s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:38Z [INFO] auto_login: login-auth wait +89s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:39Z [INFO] auto_login: login-auth wait +90s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:40Z [INFO] auto_login: login-auth wait +91s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:41Z [INFO] auto_login: login-auth wait +92s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:43Z [INFO] auto_login: login-auth wait +93s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:44Z [INFO] auto_login: login-auth wait +94s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:45Z [INFO] auto_login: login-auth wait +95s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:46Z [INFO] auto_login: login-auth wait +96s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:47Z [INFO] auto_login: login-auth wait +97s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:48Z [INFO] auto_login: login-auth wait +98s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:49Z [INFO] auto_login: login-auth wait +99s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:50Z [INFO] auto_login: login-auth wait +100s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:51Z [INFO] auto_login: login-auth wait +101s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:52Z [INFO] auto_login: login-auth wait +102s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:53Z [INFO] auto_login: login-auth wait +103s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:54Z [INFO] auto_login: login-auth wait +104s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:56Z [INFO] auto_login: login-auth wait +105s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:57Z [INFO] auto_login: login-auth wait +106s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:58Z [INFO] auto_login: login-auth wait +107s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:59Z [INFO] auto_login: login-auth wait +108s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:00Z [INFO] auto_login: login-auth wait +109s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:01Z [INFO] auto_login: login-auth wait +110s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:02Z [INFO] auto_login: login-auth wait +111s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:03Z [INFO] auto_login: login-auth wait +112s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:05Z [INFO] auto_login: login-auth wait +113s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:06Z [INFO] auto_login: login-auth wait +114s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:07Z [INFO] auto_login: login-auth wait +115s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:08Z [INFO] auto_login: login-auth wait +116s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  20:28:53 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     4m30s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:27:24Z [INFO] auto_login: login-auth wait +76s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:25Z [INFO] auto_login: login-auth wait +77s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:26Z [INFO] auto_login: login-auth wait +78s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:27Z [INFO] auto_login: login-auth wait +79s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:28Z [INFO] auto_login: login-auth wait +80s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:29Z [INFO] auto_login: login-auth wait +81s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:30Z [INFO] auto_login: login-auth wait +82s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:32Z [INFO] auto_login: login-auth wait +83s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:33Z [INFO] auto_login: login-auth wait +84s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:34Z [INFO] auto_login: login-auth wait +85s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:35Z [INFO] auto_login: login-auth wait +86s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:36Z [INFO] auto_login: login-auth wait +87s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:37Z [INFO] auto_login: login-auth wait +88s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:38Z [INFO] auto_login: login-auth wait +89s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:39Z [INFO] auto_login: login-auth wait +90s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:40Z [INFO] auto_login: login-auth wait +91s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:41Z [INFO] auto_login: login-auth wait +92s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:43Z [INFO] auto_login: login-auth wait +93s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:44Z [INFO] auto_login: login-auth wait +94s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:45Z [INFO] auto_login: login-auth wait +95s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:46Z [INFO] auto_login: login-auth wait +96s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:47Z [INFO] auto_login: login-auth wait +97s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:48Z [INFO] auto_login: login-auth wait +98s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:49Z [INFO] auto_login: login-auth wait +99s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:50Z [INFO] auto_login: login-auth wait +100s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:51Z [INFO] auto_login: login-auth wait +101s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:52Z [INFO] auto_login: login-auth wait +102s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:53Z [INFO] auto_login: login-auth wait +103s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:54Z [INFO] auto_login: login-auth wait +104s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:56Z [INFO] auto_login: login-auth wait +105s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:57Z [INFO] auto_login: login-auth wait +106s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:58Z [INFO] auto_login: login-auth wait +107s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:59Z [INFO] auto_login: login-auth wait +108s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:00Z [INFO] auto_login: login-auth wait +109s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:01Z [INFO] auto_login: login-auth wait +110s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:02Z [INFO] auto_login: login-auth wait +111s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:03Z [INFO] auto_login: login-auth wait +112s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:05Z [INFO] auto_login: login-auth wait +113s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:06Z [INFO] auto_login: login-auth wait +114s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:07Z [INFO] auto_login: login-auth wait +115s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:08Z [INFO] auto_login: login-auth wait +116s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:09Z [INFO] auto_login: login-auth wait +117s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:10Z [INFO] auto_login: login-auth wait +118s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:11Z [INFO] auto_login: login-auth wait +119s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:12Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  20:29:41 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     5m19s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:27:24Z [INFO] auto_login: login-auth wait +76s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:25Z [INFO] auto_login: login-auth wait +77s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:26Z [INFO] auto_login: login-auth wait +78s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:27Z [INFO] auto_login: login-auth wait +79s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:28Z [INFO] auto_login: login-auth wait +80s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:29Z [INFO] auto_login: login-auth wait +81s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:30Z [INFO] auto_login: login-auth wait +82s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:32Z [INFO] auto_login: login-auth wait +83s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:33Z [INFO] auto_login: login-auth wait +84s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:34Z [INFO] auto_login: login-auth wait +85s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:35Z [INFO] auto_login: login-auth wait +86s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:36Z [INFO] auto_login: login-auth wait +87s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:37Z [INFO] auto_login: login-auth wait +88s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:38Z [INFO] auto_login: login-auth wait +89s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:39Z [INFO] auto_login: login-auth wait +90s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:40Z [INFO] auto_login: login-auth wait +91s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:41Z [INFO] auto_login: login-auth wait +92s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:43Z [INFO] auto_login: login-auth wait +93s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:44Z [INFO] auto_login: login-auth wait +94s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:45Z [INFO] auto_login: login-auth wait +95s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:46Z [INFO] auto_login: login-auth wait +96s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:47Z [INFO] auto_login: login-auth wait +97s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:48Z [INFO] auto_login: login-auth wait +98s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:49Z [INFO] auto_login: login-auth wait +99s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:50Z [INFO] auto_login: login-auth wait +100s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:51Z [INFO] auto_login: login-auth wait +101s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:52Z [INFO] auto_login: login-auth wait +102s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:53Z [INFO] auto_login: login-auth wait +103s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:54Z [INFO] auto_login: login-auth wait +104s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:56Z [INFO] auto_login: login-auth wait +105s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:57Z [INFO] auto_login: login-auth wait +106s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:58Z [INFO] auto_login: login-auth wait +107s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:59Z [INFO] auto_login: login-auth wait +108s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:00Z [INFO] auto_login: login-auth wait +109s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:01Z [INFO] auto_login: login-auth wait +110s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:02Z [INFO] auto_login: login-auth wait +111s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:03Z [INFO] auto_login: login-auth wait +112s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:05Z [INFO] auto_login: login-auth wait +113s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:06Z [INFO] auto_login: login-auth wait +114s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:07Z [INFO] auto_login: login-auth wait +115s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:08Z [INFO] auto_login: login-auth wait +116s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:09Z [INFO] auto_login: login-auth wait +117s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:10Z [INFO] auto_login: login-auth wait +118s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:11Z [INFO] auto_login: login-auth wait +119s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:12Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 8/16  20:30:28 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     6m4s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:27:24Z [INFO] auto_login: login-auth wait +76s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:25Z [INFO] auto_login: login-auth wait +77s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:26Z [INFO] auto_login: login-auth wait +78s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:27Z [INFO] auto_login: login-auth wait +79s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:28Z [INFO] auto_login: login-auth wait +80s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:29Z [INFO] auto_login: login-auth wait +81s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:30Z [INFO] auto_login: login-auth wait +82s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:32Z [INFO] auto_login: login-auth wait +83s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:33Z [INFO] auto_login: login-auth wait +84s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:34Z [INFO] auto_login: login-auth wait +85s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:35Z [INFO] auto_login: login-auth wait +86s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:36Z [INFO] auto_login: login-auth wait +87s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:37Z [INFO] auto_login: login-auth wait +88s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:38Z [INFO] auto_login: login-auth wait +89s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:39Z [INFO] auto_login: login-auth wait +90s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:40Z [INFO] auto_login: login-auth wait +91s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:41Z [INFO] auto_login: login-auth wait +92s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:43Z [INFO] auto_login: login-auth wait +93s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:44Z [INFO] auto_login: login-auth wait +94s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:45Z [INFO] auto_login: login-auth wait +95s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:46Z [INFO] auto_login: login-auth wait +96s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:47Z [INFO] auto_login: login-auth wait +97s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:48Z [INFO] auto_login: login-auth wait +98s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:49Z [INFO] auto_login: login-auth wait +99s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:50Z [INFO] auto_login: login-auth wait +100s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:51Z [INFO] auto_login: login-auth wait +101s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:52Z [INFO] auto_login: login-auth wait +102s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:53Z [INFO] auto_login: login-auth wait +103s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:54Z [INFO] auto_login: login-auth wait +104s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:56Z [INFO] auto_login: login-auth wait +105s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:57Z [INFO] auto_login: login-auth wait +106s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:58Z [INFO] auto_login: login-auth wait +107s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:59Z [INFO] auto_login: login-auth wait +108s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:00Z [INFO] auto_login: login-auth wait +109s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:01Z [INFO] auto_login: login-auth wait +110s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:02Z [INFO] auto_login: login-auth wait +111s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:03Z [INFO] auto_login: login-auth wait +112s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:05Z [INFO] auto_login: login-auth wait +113s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:06Z [INFO] auto_login: login-auth wait +114s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:07Z [INFO] auto_login: login-auth wait +115s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:08Z [INFO] auto_login: login-auth wait +116s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:09Z [INFO] auto_login: login-auth wait +117s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:10Z [INFO] auto_login: login-auth wait +118s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:11Z [INFO] auto_login: login-auth wait +119s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:12Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  20:31:16 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     6m56s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:27:24Z [INFO] auto_login: login-auth wait +76s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:25Z [INFO] auto_login: login-auth wait +77s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:26Z [INFO] auto_login: login-auth wait +78s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:27Z [INFO] auto_login: login-auth wait +79s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:28Z [INFO] auto_login: login-auth wait +80s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:29Z [INFO] auto_login: login-auth wait +81s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:30Z [INFO] auto_login: login-auth wait +82s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:32Z [INFO] auto_login: login-auth wait +83s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:33Z [INFO] auto_login: login-auth wait +84s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:34Z [INFO] auto_login: login-auth wait +85s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:35Z [INFO] auto_login: login-auth wait +86s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:36Z [INFO] auto_login: login-auth wait +87s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:37Z [INFO] auto_login: login-auth wait +88s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:38Z [INFO] auto_login: login-auth wait +89s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:39Z [INFO] auto_login: login-auth wait +90s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:40Z [INFO] auto_login: login-auth wait +91s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:41Z [INFO] auto_login: login-auth wait +92s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:43Z [INFO] auto_login: login-auth wait +93s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:44Z [INFO] auto_login: login-auth wait +94s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:45Z [INFO] auto_login: login-auth wait +95s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:46Z [INFO] auto_login: login-auth wait +96s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:47Z [INFO] auto_login: login-auth wait +97s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:48Z [INFO] auto_login: login-auth wait +98s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:49Z [INFO] auto_login: login-auth wait +99s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:50Z [INFO] auto_login: login-auth wait +100s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:51Z [INFO] auto_login: login-auth wait +101s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:52Z [INFO] auto_login: login-auth wait +102s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:53Z [INFO] auto_login: login-auth wait +103s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:54Z [INFO] auto_login: login-auth wait +104s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:56Z [INFO] auto_login: login-auth wait +105s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:57Z [INFO] auto_login: login-auth wait +106s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:58Z [INFO] auto_login: login-auth wait +107s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:59Z [INFO] auto_login: login-auth wait +108s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:00Z [INFO] auto_login: login-auth wait +109s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:01Z [INFO] auto_login: login-auth wait +110s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:02Z [INFO] auto_login: login-auth wait +111s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:03Z [INFO] auto_login: login-auth wait +112s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:05Z [INFO] auto_login: login-auth wait +113s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:06Z [INFO] auto_login: login-auth wait +114s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:07Z [INFO] auto_login: login-auth wait +115s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:08Z [INFO] auto_login: login-auth wait +116s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:09Z [INFO] auto_login: login-auth wait +117s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:10Z [INFO] auto_login: login-auth wait +118s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:11Z [INFO] auto_login: login-auth wait +119s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:12Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  20:32:07 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     7m45s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:27:24Z [INFO] auto_login: login-auth wait +76s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:25Z [INFO] auto_login: login-auth wait +77s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:26Z [INFO] auto_login: login-auth wait +78s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:27Z [INFO] auto_login: login-auth wait +79s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:28Z [INFO] auto_login: login-auth wait +80s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:29Z [INFO] auto_login: login-auth wait +81s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:30Z [INFO] auto_login: login-auth wait +82s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:32Z [INFO] auto_login: login-auth wait +83s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:33Z [INFO] auto_login: login-auth wait +84s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:34Z [INFO] auto_login: login-auth wait +85s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:35Z [INFO] auto_login: login-auth wait +86s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:36Z [INFO] auto_login: login-auth wait +87s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:37Z [INFO] auto_login: login-auth wait +88s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:38Z [INFO] auto_login: login-auth wait +89s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:39Z [INFO] auto_login: login-auth wait +90s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:40Z [INFO] auto_login: login-auth wait +91s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:41Z [INFO] auto_login: login-auth wait +92s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:43Z [INFO] auto_login: login-auth wait +93s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:44Z [INFO] auto_login: login-auth wait +94s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:45Z [INFO] auto_login: login-auth wait +95s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:46Z [INFO] auto_login: login-auth wait +96s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:47Z [INFO] auto_login: login-auth wait +97s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:48Z [INFO] auto_login: login-auth wait +98s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:49Z [INFO] auto_login: login-auth wait +99s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:50Z [INFO] auto_login: login-auth wait +100s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:51Z [INFO] auto_login: login-auth wait +101s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:52Z [INFO] auto_login: login-auth wait +102s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:53Z [INFO] auto_login: login-auth wait +103s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:54Z [INFO] auto_login: login-auth wait +104s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:56Z [INFO] auto_login: login-auth wait +105s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:57Z [INFO] auto_login: login-auth wait +106s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:58Z [INFO] auto_login: login-auth wait +107s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:59Z [INFO] auto_login: login-auth wait +108s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:00Z [INFO] auto_login: login-auth wait +109s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:01Z [INFO] auto_login: login-auth wait +110s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:02Z [INFO] auto_login: login-auth wait +111s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:03Z [INFO] auto_login: login-auth wait +112s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:05Z [INFO] auto_login: login-auth wait +113s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:06Z [INFO] auto_login: login-auth wait +114s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:07Z [INFO] auto_login: login-auth wait +115s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:08Z [INFO] auto_login: login-auth wait +116s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:09Z [INFO] auto_login: login-auth wait +117s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:10Z [INFO] auto_login: login-auth wait +118s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:11Z [INFO] auto_login: login-auth wait +119s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:12Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  20:32:54 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     8m32s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:27:24Z [INFO] auto_login: login-auth wait +76s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:25Z [INFO] auto_login: login-auth wait +77s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:26Z [INFO] auto_login: login-auth wait +78s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:27Z [INFO] auto_login: login-auth wait +79s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:28Z [INFO] auto_login: login-auth wait +80s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:29Z [INFO] auto_login: login-auth wait +81s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:30Z [INFO] auto_login: login-auth wait +82s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:32Z [INFO] auto_login: login-auth wait +83s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:33Z [INFO] auto_login: login-auth wait +84s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:34Z [INFO] auto_login: login-auth wait +85s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:35Z [INFO] auto_login: login-auth wait +86s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:36Z [INFO] auto_login: login-auth wait +87s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:37Z [INFO] auto_login: login-auth wait +88s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:38Z [INFO] auto_login: login-auth wait +89s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:39Z [INFO] auto_login: login-auth wait +90s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:40Z [INFO] auto_login: login-auth wait +91s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:41Z [INFO] auto_login: login-auth wait +92s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:43Z [INFO] auto_login: login-auth wait +93s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:44Z [INFO] auto_login: login-auth wait +94s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:45Z [INFO] auto_login: login-auth wait +95s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:46Z [INFO] auto_login: login-auth wait +96s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:47Z [INFO] auto_login: login-auth wait +97s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:48Z [INFO] auto_login: login-auth wait +98s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:49Z [INFO] auto_login: login-auth wait +99s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:50Z [INFO] auto_login: login-auth wait +100s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:51Z [INFO] auto_login: login-auth wait +101s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:52Z [INFO] auto_login: login-auth wait +102s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:53Z [INFO] auto_login: login-auth wait +103s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:54Z [INFO] auto_login: login-auth wait +104s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:56Z [INFO] auto_login: login-auth wait +105s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:57Z [INFO] auto_login: login-auth wait +106s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:58Z [INFO] auto_login: login-auth wait +107s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:59Z [INFO] auto_login: login-auth wait +108s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:00Z [INFO] auto_login: login-auth wait +109s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:01Z [INFO] auto_login: login-auth wait +110s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:02Z [INFO] auto_login: login-auth wait +111s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:03Z [INFO] auto_login: login-auth wait +112s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:05Z [INFO] auto_login: login-auth wait +113s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:06Z [INFO] auto_login: login-auth wait +114s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:07Z [INFO] auto_login: login-auth wait +115s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:08Z [INFO] auto_login: login-auth wait +116s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:09Z [INFO] auto_login: login-auth wait +117s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:10Z [INFO] auto_login: login-auth wait +118s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:11Z [INFO] auto_login: login-auth wait +119s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:12Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 12/16  20:33:54 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Running   0     9m32s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:27:30Z [INFO] auto_login: login-auth wait +82s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:32Z [INFO] auto_login: login-auth wait +83s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:33Z [INFO] auto_login: login-auth wait +84s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:34Z [INFO] auto_login: login-auth wait +85s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:35Z [INFO] auto_login: login-auth wait +86s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:36Z [INFO] auto_login: login-auth wait +87s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:37Z [INFO] auto_login: login-auth wait +88s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:38Z [INFO] auto_login: login-auth wait +89s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:39Z [INFO] auto_login: login-auth wait +90s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:40Z [INFO] auto_login: login-auth wait +91s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:41Z [INFO] auto_login: login-auth wait +92s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:43Z [INFO] auto_login: login-auth wait +93s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:44Z [INFO] auto_login: login-auth wait +94s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:45Z [INFO] auto_login: login-auth wait +95s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:46Z [INFO] auto_login: login-auth wait +96s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:47Z [INFO] auto_login: login-auth wait +97s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:48Z [INFO] auto_login: login-auth wait +98s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:49Z [INFO] auto_login: login-auth wait +99s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:50Z [INFO] auto_login: login-auth wait +100s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:51Z [INFO] auto_login: login-auth wait +101s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:52Z [INFO] auto_login: login-auth wait +102s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:53Z [INFO] auto_login: login-auth wait +103s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:54Z [INFO] auto_login: login-auth wait +104s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:56Z [INFO] auto_login: login-auth wait +105s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:57Z [INFO] auto_login: login-auth wait +106s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:58Z [INFO] auto_login: login-auth wait +107s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:27:59Z [INFO] auto_login: login-auth wait +108s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:00Z [INFO] auto_login: login-auth wait +109s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:01Z [INFO] auto_login: login-auth wait +110s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:02Z [INFO] auto_login: login-auth wait +111s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:03Z [INFO] auto_login: login-auth wait +112s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:05Z [INFO] auto_login: login-auth wait +113s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:06Z [INFO] auto_login: login-auth wait +114s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:07Z [INFO] auto_login: login-auth wait +115s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:08Z [INFO] auto_login: login-auth wait +116s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:09Z [INFO] auto_login: login-auth wait +117s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:10Z [INFO] auto_login: login-auth wait +118s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:11Z [INFO] auto_login: login-auth wait +119s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:28:12Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
2026-06-26T20:33:24Z [WARN] MetaTrader exited with code 143
2026-06-26T20:33:55Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T20:33:55Z [INFO] auto_login: hard-kill watchdog armed (pid=4134, fires at +450s)
2026-06-26T20:33:55Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T20:33:55Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T20:33:57Z [INFO] auto_login: liveupdate-handler: no active window (skip)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names


===== poll 13/16  20:34:41 =====
etradie-mt-e7c75bcb-d6e-0   2/3   Terminating   0     10m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T20:34:11Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-26T20:34:12Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-26T20:34:12Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-26T20:34:13Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-26T20:34:13Z [INFO] auto_login: deliver login: paste succeeded
2026-06-26T20:34:13Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-26T20:34:14Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-26T20:34:14Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-26T20:34:15Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-26T20:34:15Z [INFO] auto_login: deliver password: paste succeeded
2026-06-26T20:34:15Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-26T20:34:15Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-26T20:34:15Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-26T20:34:16Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-26T20:34:16Z [INFO] auto_login: deliver server: paste succeeded
2026-06-26T20:34:16Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-26T20:34:17Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-26T20:34:18Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-26T20:34:18Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-26T20:34:18Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-26T20:34:19Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-26T20:34:19Z [INFO] auto_login: clipboard scrubbed
2026-06-26T20:34:19Z [INFO] auto_login: login-auth wait +0s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:20Z [INFO] auto_login: login-auth wait +1s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:21Z [INFO] auto_login: login-auth wait +2s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:22Z [INFO] auto_login: login-auth wait +3s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:23Z [INFO] auto_login: login-auth wait +4s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:24Z [INFO] auto_login: login-auth wait +5s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:25Z [INFO] auto_login: login-auth wait +6s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:26Z [INFO] auto_login: login-auth wait +7s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:27Z [INFO] auto_login: login-auth wait +8s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:29Z [INFO] auto_login: login-auth wait +9s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:30Z [INFO] auto_login: login-auth wait +10s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:31Z [INFO] auto_login: login-auth wait +11s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:32Z [INFO] auto_login: login-auth wait +12s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:33Z [INFO] auto_login: login-auth wait +13s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:34Z [INFO] auto_login: login-auth wait +14s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:35Z [INFO] auto_login: login-auth wait +15s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:36Z [INFO] auto_login: login-auth wait +16s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:37Z [INFO] auto_login: login-auth wait +17s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:38Z [INFO] auto_login: login-auth wait +18s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:40Z [INFO] auto_login: login-auth wait +19s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:41Z [INFO] auto_login: login-auth wait +20s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:42Z [INFO] auto_login: login-auth wait +21s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T20:34:43Z [INFO] auto_login: login-auth wait +22s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 14/16  20:35:27 =====
Error from server (NotFound): pods "etradie-mt-e7c75bcb-d6e-0" not found
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
Error from server (NotFound): pods "etradie-mt-e7c75bcb-d6e-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-e7c75bcb-d6e-0" not found
--- journal head/tail (broker handshake) ---
(MT_DIR empty; journal/EA log not collected)
...
(MT_DIR empty; journal/EA log not collected)
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 e7c75bcb-d6e7-41db-afc8-43bb47a98490 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260626T202212Z ===
total 19328
drwxr-xr-x  2 softverse softverse    4096 Jun 26 21:35 .
drwxr-xr-x 19 softverse softverse    4096 Jun 26 21:22 ..
-rw-r--r--  1 softverse softverse     110 Jun 26 21:35 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 26 21:35 driver-log-full.txt
-rw-r--r--  1 softverse softverse      45 Jun 26 21:35 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 26 21:22 engine-env.txt
-rw-r--r--  1 softverse softverse       1 Jun 26 21:24 mt-config-dir.txt
-rw-r--r--  1 softverse softverse       1 Jun 26 21:24 mt-dir.txt
-rw-r--r--  1 softverse softverse      45 Jun 26 21:35 mt5-journal.txt
-rw-r--r--  1 softverse softverse      71 Jun 26 21:25 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse       0 Jun 26 21:25 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 26 21:22 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 26 21:24 release.txt
-rw-r--r--  1 softverse softverse      35 Jun 26 21:25 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   65164 Jun 26 21:35 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:25 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse   67865 Jun 26 21:35 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:26 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse   67868 Jun 26 21:35 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:27 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   67868 Jun 26 21:35 screen-poll-05.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:28 screen-poll-05.xwd
-rw-r--r--  1 softverse softverse   67867 Jun 26 21:35 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:29 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   67869 Jun 26 21:35 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:29 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse   67869 Jun 26 21:35 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:30 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse   67874 Jun 26 21:35 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:31 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse   67876 Jun 26 21:35 screen-poll-10.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:32 screen-poll-10.xwd
-rw-r--r--  1 softverse softverse   67868 Jun 26 21:35 screen-poll-11.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:33 screen-poll-11.xwd
-rw-r--r--  1 softverse softverse     278 Jun 26 21:35 screen-poll-12.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:34 screen-poll-12.xwd
-rw-r--r--  1 softverse softverse   59568 Jun 26 21:35 screen-poll-13.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 21:34 screen-poll-13.xwd
-rw-r--r--  1 softverse softverse      23 Jun 26 21:24 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 26 21:35 windows-final.txt
-rw-r--r--  1 softverse softverse       0 Jun 26 21:25 windows-poll-01.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 21:25 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 21:26 windows-poll-03.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 21:27 windows-poll-04.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 21:28 windows-poll-05.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 21:29 windows-poll-06.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 21:29 windows-poll-07.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 21:30 windows-poll-08.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 21:31 windows-poll-09.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 21:32 windows-poll-10.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 21:33 windows-poll-11.txt
-rw-r--r--  1 softverse softverse      72 Jun 26 21:34 windows-poll-12.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 21:34 windows-poll-13.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260626T202212Z
softverse@Softverse:~/hostedmt-diagnostics/20260626T202212Z

















EXAMINE THE NOTE.md THOROUGHLY FROM THE START TO THE END.


FROM WHAT WE HAVE, xdg-open screen-poll-02.png SHOWED THIS :


File
View
Tools
Help
Market Watch
X
IDE (0)
Algo Trading
New Order
+
Symbol
Bid
3333.667
3334.638
Ask
Daily Ch...
XAUUSDM
115786,40
115923.04
0.21%
BTCUSDm
1.16680
1.16689
-1.37%
EURUSDM
USDJPYm
147.890
147.898
-0.32%
0.45%
ETHUSDM
4314.20
4331.40
-3.42%
XAUUSD
3334.210
3334.380
-0.06%
Symbols
Details Trading
Ticks
Navigator
Exness
Accounts
Indicators
Expert Advisors
Scripts
Services
Market
***
Authorization allows to get access to the trade account
Login:
133978149
Password:
Save password
Common
Favorites
Server:
Exness-MT5Real
OK
Cancel
X Time
Source
2026.06.26 20:25:20.312
Terminal
2026.06.26 20:25:20.313
Terminal
2026.06.26 20:25:20.313
Terminal
Windows 10 build 19045 on Wine 11.0 Linux 6.8.0-124-generic, 8 x AMD EPYC (with IBPB), AVX2, 17/23 Gb memory, 67/192 Gb...
C:\Program Files\MetaTrader 5 EXNESS
Toolbox
News |
Mailbox
Calendar |
Alerts |
Articles |
Code Base |
Experts
Journal
0000.00.00 00:00
0:000.000
H: 000.000
L: 000.000
C: 000.000
Market (0)
Sigrials VPS
V: 00000
Tester
0/0 Kb
For Help, press F1
Default





BUT xdg-open screen-poll-03.png TO xdg-open screen-poll-10.png ALL SHOWED THIS BELOW:


File View
Tools
Help
IDE
(0)
Algo Trading
New Order
Market Watch
X
Symbol
Bid
Ask
Daily Ch... ^
XAUUSDM
3333.667
3334.638
0.21%
BTCUSDm
115786.40
115923.04.
-1.37%
7 EURUSDm
1.16680
1.16689
-0.32%
USDJPYm
147.890
147.898
0.45%
ETHUSDM
4314.20 4331.40
-3.42%
XAUUSD
3334.210
3334.380
-0.06%
Symbols Details
Trading
Ticks
Navigator
Exness
Accounts
Indicators
Expert Advisors
Scripts
Services
Market
Common Favorites
X
X Time
2026.06.26 20:25:20.312
2026.06.26 20:25:20.313
2026.06.26 20:25:20.313
2026.06.26 20:26:20.990
2026.06.26 20:26:22.305
LiveUpdate
2026.06.26 20:26:22.308
Source
Terminal
Terminal
Terminal
LiveUpdate
LiveUpdate
م
Message
MetaTrader 5 EXNESS x64 build 5836 started for Exness Technologies Ltd.
Windows 10 build 19045 on Wine 11.0 Linux 6.8.0-124-generic, 8 x AMD EPYC (with IBPB), AVX2, 17/23 Gb memory, 67/192 Gb...
C:\Program Files\MetaTrader 5 EXNESS
new version build 5833 (IDE: 5833, Tester: 5833) is available
'mt5onnx64' downloaded and updated (14688 kb)
downloaded successfully
Toolbox
News
Mailbox
Calendar
Alerts
Articles |
Code Base
Experts Journal
0000.00.00 00:00
0: 000.000
H: 000.000
L: 000.000
C: 000.000
Market (1)
Sigrials VPS
V: 00000
0/0 Kb
Tester
For Help, press F1
Default