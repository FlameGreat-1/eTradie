$DIAG_DIR"_DIR ==="────────────────────────ee attempts failed' driver-log-full.txt | tail -10 -20ll present' driver-log-full.txt | head -30> w
=== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 08:18:16
=== STAGE 7: race to the pod ===
Release: etradie-mt-aa415fa7-d59
POD=etradie-mt-aa415fa7-d59-0
[1] mt-node state: {"running":{"startedAt":"2026-06-27T08:18:12Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:f51e7cfcdb19a57dd90c07f5d6de333df48a7de2
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:f51e7cfcdb19a57dd90c07f5d6de333df48a7de2
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
2026-06-27T08:18:43Z [INFO] broker-bundle overlay: cp -a '/broker-bundle/MetaTrader 5 EXNESS/.' -> '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/'

Expect lines like:
  overlay-normalize(mt5): stripping baked Profiles/Charts workspace
  overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
  overlay-normalize(mt5): removing baked common.ini ...
  overlay-normalize(mt5): removing baked accounts.dat ...
  overlay-normalize: canonical config dir resolved to '<MT_DIR>/Config'
=== STAGE 10b: assert baked state was actually neutralized ===
SKIPPED: MT_DIR empty (see STAGE 8b WARN); not running ls against '/'.
=== STAGE 11: poll loop ===

===== poll 1/16  08:18:43 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     49s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:18:44Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-27T08:18:44Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-27T08:18:44Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-27T08:18:44Z [INFO] overlay-normalize(mt5): deleting baked common.ini (foreign [Common] account context blocked by trusted-device check on fresh Wine prefix -- surfaces demo-registration wizard; MT5 recreates the file after Phase 3's per-tenant login)
2026-06-27T08:18:44Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-27T08:18:44Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T08:18:44Z [INFO] auto_login: hard-kill watchdog armed (pid=318, fires at +450s)
2026-06-27T08:18:44Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T08:18:44Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T08:18:46Z [INFO] auto_login: liveupdate-handler: no active window (skip)
--- :5555 LISTEN state (0A) ---
3148907 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 2/16  08:19:43 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     108s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:19:14Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-27T08:19:15Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:19:16Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +32s
2026-06-27T08:19:16Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-27T08:19:18Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-27T08:19:18Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-27T08:19:18Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-27T08:19:19Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-27T08:19:19Z [INFO] auto_login: deliver login: paste succeeded
2026-06-27T08:19:19Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-27T08:19:20Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-27T08:19:20Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-27T08:19:21Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T08:19:21Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T08:19:21Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-27T08:19:22Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-27T08:19:22Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-27T08:19:23Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-27T08:19:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T08:19:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T08:19:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T08:19:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T08:19:24Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T08:19:24Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T08:19:25Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T08:19:25Z [INFO] auto_login: clipboard scrubbed
2026-06-27T08:19:25Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:26Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:28Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:29Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:30Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:31Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:32Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:33Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:34Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:35Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:36Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:37Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:39Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:40Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:41Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:42Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:43Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:44Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:45Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  08:20:28 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     2m33s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:19:21Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T08:19:21Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-27T08:19:22Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-27T08:19:22Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-27T08:19:23Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-27T08:19:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T08:19:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T08:19:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T08:19:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T08:19:24Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T08:19:24Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T08:19:25Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T08:19:25Z [INFO] auto_login: clipboard scrubbed
2026-06-27T08:19:25Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:26Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:28Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:29Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:30Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:31Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:32Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:33Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:34Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:35Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:36Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:37Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:39Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:40Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:41Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:42Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:43Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:44Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:45Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:46Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:47Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:48Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:49Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:51Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:52Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:53Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:54Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:55Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:57Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:58Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:59Z [INFO] auto_login: login confirmed via journal at +30s: JR 0       08:19:27.307    Network '133978149': trading has been enabled - hedging mode
2026-06-27T08:19:59Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  08:21:09 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     3m15s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:19:22Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-27T08:19:22Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-27T08:19:23Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-27T08:19:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T08:19:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T08:19:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T08:19:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T08:19:24Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T08:19:24Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T08:19:25Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T08:19:25Z [INFO] auto_login: clipboard scrubbed
2026-06-27T08:19:25Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:26Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:28Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:29Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:30Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:31Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:32Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:33Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:34Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:35Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:36Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:37Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:39Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:40Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:41Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:42Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:43Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:44Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:45Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:46Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:47Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:48Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:49Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:51Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:52Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:53Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:54Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:55Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:57Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:58Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:59Z [INFO] auto_login: login confirmed via journal at +30s: JR 0       08:19:27.307    Network '133978149': trading has been enabled - hedging mode
2026-06-27T08:19:59Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T08:21:00Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T08:21:00Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  08:21:56 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     4m1s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:19:22Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-27T08:19:22Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-27T08:19:23Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-27T08:19:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T08:19:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T08:19:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T08:19:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-27T08:19:24Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-27T08:19:24Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T08:19:25Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T08:19:25Z [INFO] auto_login: clipboard scrubbed
2026-06-27T08:19:25Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:26Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:28Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:29Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:30Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:31Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:32Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:33Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:34Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:35Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:36Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:37Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:39Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:40Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:41Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:42Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:43Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:44Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:45Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:46Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:47Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:48Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:49Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:51Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:52Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:53Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:54Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:55Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:57Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:58Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:59Z [INFO] auto_login: login confirmed via journal at +30s: JR 0       08:19:27.307    Network '133978149': trading has been enabled - hedging mode
2026-06-27T08:19:59Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T08:21:00Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T08:21:00Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  08:22:39 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     4m45s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:19:24Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T08:19:25Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-27T08:19:25Z [INFO] auto_login: clipboard scrubbed
2026-06-27T08:19:25Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:26Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:28Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:29Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:30Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:31Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:32Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:33Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:34Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:35Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:36Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:37Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:39Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:40Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:41Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:42Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:43Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:44Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:45Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:46Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:47Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:48Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:49Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:51Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:52Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:53Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:54Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:55Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:57Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:58Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:59Z [INFO] auto_login: login confirmed via journal at +30s: JR 0       08:19:27.307    Network '133978149': trading has been enabled - hedging mode
2026-06-27T08:19:59Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T08:21:00Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T08:21:00Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T08:22:03Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T08:22:03Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T08:22:03Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:04Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T08:22:26Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T08:22:32Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  08:23:25 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     5m30s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:19:30Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:31Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:32Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:33Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:34Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:35Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:36Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:37Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:39Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:40Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:41Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:42Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:43Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:44Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:45Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:46Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:47Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:48Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:49Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:51Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:52Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:53Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:54Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:55Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:57Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:58Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:59Z [INFO] auto_login: login confirmed via journal at +30s: JR 0       08:19:27.307    Network '133978149': trading has been enabled - hedging mode
2026-06-27T08:19:59Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T08:21:00Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T08:21:00Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T08:22:03Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T08:22:03Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T08:22:03Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:04Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T08:22:26Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T08:22:32Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T08:22:56Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T08:23:02Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T08:23:02Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:23:03Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T08:23:25Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T08:23:26Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T08:23:26Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 8/16  08:24:14 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     6m20s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:19:30Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:31Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:32Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:33Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:34Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:35Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:36Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:37Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:39Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:40Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:41Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:42Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:43Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:44Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:45Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:46Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:47Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:48Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:49Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:51Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:52Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:53Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:54Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:55Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:57Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:58Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:59Z [INFO] auto_login: login confirmed via journal at +30s: JR 0       08:19:27.307    Network '133978149': trading has been enabled - hedging mode
2026-06-27T08:19:59Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T08:21:00Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T08:21:00Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T08:22:03Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T08:22:03Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T08:22:03Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:04Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T08:22:26Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T08:22:32Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T08:22:56Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T08:23:02Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T08:23:02Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:23:03Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T08:23:25Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T08:23:26Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T08:23:26Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  08:24:59 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     7m4s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:19:30Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:31Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:32Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:33Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:34Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:35Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:36Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:37Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:39Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:40Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:41Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:42Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:43Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:44Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:45Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:46Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:47Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:48Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:49Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:51Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:52Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:53Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:54Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:55Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:57Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:58Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:59Z [INFO] auto_login: login confirmed via journal at +30s: JR 0       08:19:27.307    Network '133978149': trading has been enabled - hedging mode
2026-06-27T08:19:59Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T08:21:00Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T08:21:00Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T08:22:03Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T08:22:03Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T08:22:03Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:04Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T08:22:26Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T08:22:32Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T08:22:56Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T08:23:02Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T08:23:02Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:23:03Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T08:23:25Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T08:23:26Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T08:23:26Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  08:25:42 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     7m48s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:19:31Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:32Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:33Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:34Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:35Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:36Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:37Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:39Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:40Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:41Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:42Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:43Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:44Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:45Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:46Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:47Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:48Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:49Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:51Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:52Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:53Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:54Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:55Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:57Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:58Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:59Z [INFO] auto_login: login confirmed via journal at +30s: JR 0       08:19:27.307    Network '133978149': trading has been enabled - hedging mode
2026-06-27T08:19:59Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T08:21:00Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T08:21:00Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T08:22:03Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T08:22:03Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T08:22:03Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:04Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T08:22:26Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T08:22:32Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T08:22:56Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T08:23:02Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T08:23:02Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:23:03Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T08:23:25Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T08:23:26Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T08:23:26Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T08:25:44Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  08:26:33 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     8m39s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:19:31Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:32Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:33Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:34Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:35Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:36Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:37Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:39Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:40Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:41Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:42Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:43Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:44Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:45Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:46Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:47Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:48Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:49Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:51Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:52Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:53Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:54Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:55Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:57Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:58Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:59Z [INFO] auto_login: login confirmed via journal at +30s: JR 0       08:19:27.307    Network '133978149': trading has been enabled - hedging mode
2026-06-27T08:19:59Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T08:21:00Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T08:21:00Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T08:22:03Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T08:22:03Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T08:22:03Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:04Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T08:22:26Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T08:22:32Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T08:22:56Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T08:23:02Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T08:23:02Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:23:03Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T08:23:25Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T08:23:26Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T08:23:26Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T08:25:44Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 12/16  08:27:23 =====
etradie-mt-aa415fa7-d59-0   2/3   Running   0     9m29s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:19:32Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:33Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:34Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:35Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:36Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:37Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:39Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:40Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:41Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:42Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:43Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:44Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:45Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:46Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:47Z [INFO] auto_login: login-auth wait +20s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:48Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:49Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:51Z [INFO] auto_login: login-auth wait +23s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:52Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:53Z [INFO] auto_login: login-auth wait +25s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:54Z [INFO] auto_login: login-auth wait +26s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:55Z [INFO] auto_login: login-auth wait +27s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:57Z [INFO] auto_login: login-auth wait +28s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:58Z [INFO] auto_login: login-auth wait +29s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-27T08:19:59Z [INFO] auto_login: login confirmed via journal at +30s: JR 0       08:19:27.307    Network '133978149': trading has been enabled - hedging mode
2026-06-27T08:19:59Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-27T08:21:00Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-27T08:21:00Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-27T08:22:03Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-27T08:22:03Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-27T08:22:03Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:04Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-27T08:22:26Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-27T08:22:32Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:22:32Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-27T08:22:56Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-27T08:23:02Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-27T08:23:02Z [INFO] auto_login: main window is active; modals cleared
2026-06-27T08:23:03Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T08:23:25Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T08:23:26Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T08:23:26Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T08:25:44Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T08:26:58Z [WARN] MetaTrader exited with code 143
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 13/16  08:28:14 =====
etradie-mt-aa415fa7-d59-0   2/3   Terminating   0     10m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-27T08:23:03Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-27T08:23:25Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-27T08:23:26Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-27T08:23:26Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-27T08:25:44Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-27T08:26:58Z [WARN] MetaTrader exited with code 143
2026-06-27T08:27:28Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-27T08:27:28Z [INFO] auto_login: hard-kill watchdog armed (pid=4187, fires at +450s)
2026-06-27T08:27:28Z [INFO] auto_login: terminal process detected at +0s
2026-06-27T08:27:28Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T08:27:31Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T08:27:33Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T08:27:35Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T08:27:37Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T08:27:39Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T08:27:42Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T08:27:44Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-27T08:27:46Z [INFO] auto_login: liveupdate-handler: active WID=12582913 name='133978149 - Exness-MT5Real9 - Netting - Exness Technologies Ltd'
2026-06-27T08:27:48Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name='Login'
2026-06-27T08:27:48Z [INFO] auto_login: Login dialog WID=12582936 detected at +20s
2026-06-27T08:27:48Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-27T08:27:50Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-27T08:27:50Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-27T08:27:50Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-27T08:27:51Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-27T08:27:51Z [INFO] auto_login: deliver login: paste succeeded
2026-06-27T08:27:51Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-27T08:27:52Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-27T08:27:52Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-27T08:27:53Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-27T08:27:53Z [INFO] auto_login: deliver password: paste succeeded
2026-06-27T08:27:53Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-27T08:27:54Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-27T08:27:54Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-27T08:27:55Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-27T08:27:55Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-27T08:27:56Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-27T08:27:56Z [INFO] auto_login: deliver server: paste succeeded
2026-06-27T08:27:56Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-27T08:27:56Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-27T08:27:56Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-27T08:27:57Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-27T08:27:57Z [INFO] auto_login: clipboard scrubbed
2026-06-27T08:27:57Z [INFO] auto_login: login confirmed via journal at +0s: JR  0       08:19:27.307    Network '133978149': trading has been enabled - hedging mode
2026-06-27T08:27:57Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
Error from server (NotFound): pods "etradie-mt-aa415fa7-d59-0" not found

===== poll 14/16  08:29:10 =====
Error from server (NotFound): pods "etradie-mt-aa415fa7-d59-0" not found
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
OK: screen-poll-10.png
OK: screen-poll-11.png
OK: screen-poll-12.png
=== STAGE 13: verdict ===
Error from server (NotFound): pods "etradie-mt-aa415fa7-d59-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-aa415fa7-d59-0" not found
--- journal head/tail (broker handshake) ---
(MT_DIR empty; journal/EA log not collected)
...
(MT_DIR empty; journal/EA log not collected)
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 aa415fa7-d592-431b-8902-bf4aff9e2d51 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260627T081411Z ===
total 20736
drwxr-xr-x  2 softverse softverse    4096 Jun 27 09:29 .
drwxr-xr-x 20 softverse softverse    4096 Jun 27 09:14 ..
-rw-r--r--  1 softverse softverse      65 Jun 27 09:29 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 27 09:29 driver-log-full.txt
-rw-r--r--  1 softverse softverse      45 Jun 27 09:29 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 27 09:16 engine-env.txt
-rw-r--r--  1 softverse softverse       1 Jun 27 09:18 mt-config-dir.txt
-rw-r--r--  1 softverse softverse       1 Jun 27 09:18 mt-dir.txt
-rw-r--r--  1 softverse softverse      45 Jun 27 09:29 mt5-journal.txt
-rw-r--r--  1 softverse softverse      71 Jun 27 09:18 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse     166 Jun 27 09:18 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 27 09:14 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 27 09:18 release.txt
-rw-r--r--  1 softverse softverse    3676 Jun 27 09:29 screen-poll-01.png
-rw-r--r--  1 softverse softverse 3148907 Jun 27 09:19 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   65461 Jun 27 09:29 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 09:19 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse   57650 Jun 27 09:29 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 09:20 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse   57890 Jun 27 09:29 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 09:21 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   58048 Jun 27 09:29 screen-poll-05.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 09:22 screen-poll-05.xwd
-rw-r--r--  1 softverse softverse   77404 Jun 27 09:29 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 09:22 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   56596 Jun 27 09:29 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 09:23 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse   56483 Jun 27 09:29 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 09:24 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse   56878 Jun 27 09:29 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 09:25 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse   56563 Jun 27 09:29 screen-poll-10.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 09:25 screen-poll-10.xwd
-rw-r--r--  1 softverse softverse   56563 Jun 27 09:29 screen-poll-11.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 09:26 screen-poll-11.xwd
-rw-r--r--  1 softverse softverse     278 Jun 27 09:29 screen-poll-12.png
-rw-r--r--  1 softverse softverse 1573739 Jun 27 09:27 screen-poll-12.xwd
-rw-r--r--  1 softverse softverse      23 Jun 27 09:18 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 27 09:29 windows-final.txt
-rw-r--r--  1 softverse softverse      48 Jun 27 09:19 windows-poll-01.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 09:19 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 09:20 windows-poll-03.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 09:21 windows-poll-04.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 09:22 windows-poll-05.txt
-rw-r--r--  1 softverse softverse     136 Jun 27 09:22 windows-poll-06.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 09:23 windows-poll-07.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 09:24 windows-poll-08.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 09:25 windows-poll-09.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 09:26 windows-poll-10.txt
-rw-r--r--  1 softverse softverse      80 Jun 27 09:26 windows-poll-11.txt
-rw-r--r--  1 softverse softverse      31 Jun 27 09:27 windows-poll-12.txt
-rw-r--r--  1 softverse softverse      73 Jun 27 09:28 windows-poll-13.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260627T081411Z
softverse@Softverse:~/hostedmt-diagnostics/20260627T081411Z$ 