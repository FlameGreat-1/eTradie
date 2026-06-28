=== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 01:08:45
=== STAGE 7: race to the pod ===
Release: etradie-mt-694e3827-4f9
POD=etradie-mt-694e3827-4f9-0
[1] mt-node state: {"waiting":{"reason":"PodInitializing"}}
[2] mt-node state: {"running":{"startedAt":"2026-06-28T01:08:49Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:78f3371bcacb640451ede1ef5b174096f8448fb0
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:78f3371bcacb640451ede1ef5b174096f8448fb0
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

===== poll 1/16  01:09:15 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     41s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 2/16  01:09:59 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     85s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:09:19Z [INFO] auto_login: hard-kill watchdog armed (pid=324, fires at +450s)
2026-06-28T01:09:19Z [INFO] auto_login: terminal process detected at +0s
2026-06-28T01:09:19Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T01:09:21Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T01:09:24Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T01:09:26Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T01:09:28Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T01:09:30Z [INFO] auto_login: liveupdate-handler: active WID=12582913 name='MetaTrader 5 EXNESS - Netting'
2026-06-28T01:09:32Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T01:09:34Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T01:09:36Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T01:09:38Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T01:09:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T01:09:42Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T01:09:44Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T01:09:46Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T01:09:48Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T01:09:50Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-28T01:09:51Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-28T01:09:51Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-28T01:09:51Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-28T01:09:51Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T01:09:53Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s
2026-06-28T01:09:53Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-28T01:09:54Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-28T01:09:55Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-28T01:09:55Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-28T01:09:56Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-28T01:09:56Z [INFO] auto_login: deliver login: paste succeeded
2026-06-28T01:09:56Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-28T01:09:56Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-28T01:09:56Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-28T01:09:57Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-28T01:09:57Z [INFO] auto_login: deliver password: paste succeeded
2026-06-28T01:09:57Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-28T01:09:58Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T01:10:00Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  01:10:43 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     2m9s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:09:56Z [INFO] auto_login: deliver login: paste succeeded
2026-06-28T01:09:56Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-28T01:09:56Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-28T01:09:56Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-28T01:09:57Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-28T01:09:57Z [INFO] auto_login: deliver password: paste succeeded
2026-06-28T01:09:57Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-28T01:09:58Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T01:10:00Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T01:10:02Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:10:02Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:03Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:05Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:06Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:07Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:08Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:09Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:11Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:12Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:13Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:14Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:15Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:16Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:17Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:18Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:19Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:20Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:22Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:23Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:24Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:26Z [INFO] auto_login: login-auth wait +20s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:27Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:28Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:29Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:30Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:31Z [INFO] auto_login: login confirmed via journal at +25s: QE 0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:10:31Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  01:11:25 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     2m51s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:09:56Z [INFO] auto_login: deliver login: paste succeeded
2026-06-28T01:09:56Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-28T01:09:56Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-28T01:09:56Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-28T01:09:57Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-28T01:09:57Z [INFO] auto_login: deliver password: paste succeeded
2026-06-28T01:09:57Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-28T01:09:58Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T01:10:00Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T01:10:02Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:10:02Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:03Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:05Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:06Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:07Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:08Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:09Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:11Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:12Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:13Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:14Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:15Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:16Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:17Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:18Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:19Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:20Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:22Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:23Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:24Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:26Z [INFO] auto_login: login-auth wait +20s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:27Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:28Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:29Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:30Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:31Z [INFO] auto_login: login confirmed via journal at +25s: QE 0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:10:31Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  01:12:08 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     3m33s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:09:56Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-28T01:09:56Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-28T01:09:57Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-28T01:09:57Z [INFO] auto_login: deliver password: paste succeeded
2026-06-28T01:09:57Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-28T01:09:58Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T01:10:00Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T01:10:02Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:10:02Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:03Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:05Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:06Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:07Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:08Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:09Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:11Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:12Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:13Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:14Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:15Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:16Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:17Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:18Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:19Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:20Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:22Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:23Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:24Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:26Z [INFO] auto_login: login-auth wait +20s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:27Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:28Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:29Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:30Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:31Z [INFO] auto_login: login confirmed via journal at +25s: QE 0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:10:31Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T01:11:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T01:11:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  01:12:50 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     4m15s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:09:59Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-28T01:09:59Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T01:10:00Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T01:10:02Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:10:02Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:03Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:05Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:06Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:07Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:08Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:09Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:11Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:12Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:13Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:14Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:15Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:16Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:17Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:18Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:19Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:20Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:22Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:23Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:24Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:26Z [INFO] auto_login: login-auth wait +20s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:27Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:28Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:29Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:30Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:31Z [INFO] auto_login: login confirmed via journal at +25s: QE 0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:10:31Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T01:11:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T01:11:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T01:12:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T01:12:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T01:12:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T01:12:37Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  01:13:31 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     4m57s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:09:59Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T01:10:00Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T01:10:02Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:10:02Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:03Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:05Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:06Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:07Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:08Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:09Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:11Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:12Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:13Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:14Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:15Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:16Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:17Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:18Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:19Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:20Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:22Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:23Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:24Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:26Z [INFO] auto_login: login-auth wait +20s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:27Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:28Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:29Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:30Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:31Z [INFO] auto_login: login confirmed via journal at +25s: QE 0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:10:31Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T01:11:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T01:11:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T01:12:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T01:12:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T01:12:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T01:12:37Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T01:13:12Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T01:13:12Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 8/16  01:14:12 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     5m38s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:09:59Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T01:10:00Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T01:10:02Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:10:02Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:03Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:05Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:06Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:07Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:08Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:09Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:11Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:12Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:13Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:14Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:15Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:16Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:17Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:18Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:19Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:20Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:22Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:23Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:24Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:26Z [INFO] auto_login: login-auth wait +20s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:27Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:28Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:29Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:30Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:31Z [INFO] auto_login: login confirmed via journal at +25s: QE 0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:10:31Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T01:11:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T01:11:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T01:12:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T01:12:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T01:12:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T01:12:37Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T01:13:12Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T01:13:12Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  01:15:04 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     6m30s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:09:59Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T01:10:00Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T01:10:02Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:10:02Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:03Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:05Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:06Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:07Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:08Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:09Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:11Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:12Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:13Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:14Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:15Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:16Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:17Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:18Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:19Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:20Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:22Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:23Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:24Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:26Z [INFO] auto_login: login-auth wait +20s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:27Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:28Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:29Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:30Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:31Z [INFO] auto_login: login confirmed via journal at +25s: QE 0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:10:31Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T01:11:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T01:11:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T01:12:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T01:12:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T01:12:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T01:12:37Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T01:13:12Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T01:13:12Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  01:15:46 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     7m12s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:09:59Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T01:10:00Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T01:10:02Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:10:02Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:03Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:05Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:06Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:07Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:08Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:09Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:11Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:12Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:13Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:14Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:15Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:16Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:17Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:18Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:19Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:20Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:22Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:23Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:24Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:26Z [INFO] auto_login: login-auth wait +20s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:27Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:28Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:29Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:30Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:31Z [INFO] auto_login: login confirmed via journal at +25s: QE 0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:10:31Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T01:11:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T01:11:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T01:12:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T01:12:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T01:12:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T01:12:37Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T01:13:12Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T01:13:12Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  01:16:28 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     7m54s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:10:00Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T01:10:02Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:10:02Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:03Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:05Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:06Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:07Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:08Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:09Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:11Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:12Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:13Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:14Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:15Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:16Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:17Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:18Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:19Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:20Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:22Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:23Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:24Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:26Z [INFO] auto_login: login-auth wait +20s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:27Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:28Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:29Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:30Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:31Z [INFO] auto_login: login confirmed via journal at +25s: QE 0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:10:31Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T01:11:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T01:11:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T01:12:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T01:12:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T01:12:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T01:12:37Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T01:13:12Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T01:13:12Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-28T01:16:21Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 12/16  01:17:11 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     8m37s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:10:00Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T01:10:02Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:10:02Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:03Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:05Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:06Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:07Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:08Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:09Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:11Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:12Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:13Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:14Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:15Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:16Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:17Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:18Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:19Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:20Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:22Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:23Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:24Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:26Z [INFO] auto_login: login-auth wait +20s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:27Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:28Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:29Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:30Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:31Z [INFO] auto_login: login confirmed via journal at +25s: QE 0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:10:31Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T01:11:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T01:11:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T01:12:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T01:12:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T01:12:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T01:12:37Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T01:13:12Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T01:13:12Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-28T01:16:21Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 13/16  01:17:54 =====
etradie-mt-694e3827-4f9-0   2/3   Running   0     9m20s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:10:00Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-28T01:10:00Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:10:01Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 - Exness-MT5Real9 - Netting
2026-06-28T01:10:02Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:10:02Z [INFO] auto_login: login-auth wait +0s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:03Z [INFO] auto_login: login-auth wait +1s: active title='133978149 - Exness-MT5Real9 - Netting' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:05Z [INFO] auto_login: login-auth wait +2s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:06Z [INFO] auto_login: login-auth wait +3s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:07Z [INFO] auto_login: login-auth wait +4s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:08Z [INFO] auto_login: login-auth wait +5s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:09Z [INFO] auto_login: login-auth wait +6s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:11Z [INFO] auto_login: login-auth wait +7s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:12Z [INFO] auto_login: login-auth wait +8s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:13Z [INFO] auto_login: login-auth wait +9s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:14Z [INFO] auto_login: login-auth wait +10s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:15Z [INFO] auto_login: login-auth wait +11s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:16Z [INFO] auto_login: login-auth wait +12s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:17Z [INFO] auto_login: login-auth wait +13s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:18Z [INFO] auto_login: login-auth wait +14s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:19Z [INFO] auto_login: login-auth wait +15s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:20Z [INFO] auto_login: login-auth wait +16s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:22Z [INFO] auto_login: login-auth wait +17s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:23Z [INFO] auto_login: login-auth wait +18s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:24Z [INFO] auto_login: login-auth wait +19s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:26Z [INFO] auto_login: login-auth wait +20s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:27Z [INFO] auto_login: login-auth wait +21s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:28Z [INFO] auto_login: login-auth wait +22s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:29Z [INFO] auto_login: login-auth wait +23s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:30Z [INFO] auto_login: login-auth wait +24s: active title='133978149 - Exness-MT5Real9 - Hedge - Exness Technologies Ltd' (awaiting broker connect/authorize line in journal)
2026-06-28T01:10:31Z [INFO] auto_login: login confirmed via journal at +25s: QE 0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:10:31Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
2026-06-28T01:11:32Z [WARN] auto_login: deterministic attach: NO chart+EA attached and :5555 not bound within 60s; engaging keystroke chart-attach fallback (genuine no-chart state)
2026-06-28T01:11:32Z [INFO] auto_login: phase5: settling up to 60s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)
2026-06-28T01:12:35Z [WARN] auto_login: phase5: settle upper bound (60s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T01:12:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T01:12:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T01:12:37Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T01:13:12Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T01:13:12Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-28T01:16:21Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-28T01:17:35Z [WARN] MetaTrader exited with code 143
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 14/16  01:18:41 =====
etradie-mt-694e3827-4f9-0   2/3   Terminating   0     10m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): clearing modals + activating main window
2026-06-28T01:12:35Z [INFO] auto_login: main window is active; modals cleared
2026-06-28T01:12:35Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): dispatching keystroke sequence [alt+f Right Return]
2026-06-28T01:12:37Z [INFO] auto_login: phase5: attempt 1 (Alt+F New Chart → recently-used): chart window WID=12582913 visible after keystroke sequence
2026-06-28T01:12:37Z [INFO] auto_login: phase5: explicitly loading expert template via keystrokes
2026-06-28T01:13:12Z [WARN] auto_login: phase5: attempt 1: chart opened but :5555 not bound within budget; aborting Phase 5 loop to prevent errant menu navigation
2026-06-28T01:13:12Z [INFO] auto_login: phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-28T01:16:21Z [ERROR] auto_login: :5555 never bound within 420s total budget; exiting
2026-06-28T01:17:35Z [WARN] MetaTrader exited with code 143
2026-06-28T01:18:05Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-28T01:18:05Z [INFO] auto_login: hard-kill watchdog armed (pid=3914, fires at +450s)
2026-06-28T01:18:05Z [INFO] auto_login: terminal process detected at +0s
2026-06-28T01:18:05Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T01:18:07Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T01:18:10Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T01:18:12Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T01:18:14Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T01:18:16Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-28T01:18:18Z [INFO] auto_login: liveupdate-handler: active WID=12582937 name='Login'
2026-06-28T01:18:18Z [INFO] auto_login: Login dialog WID=12582937 detected at +13s
2026-06-28T01:18:18Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582937 name=Login
2026-06-28T01:18:19Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582937 name=Login
2026-06-28T01:18:20Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582937 name=Login
2026-06-28T01:18:20Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-28T01:18:21Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-28T01:18:21Z [INFO] auto_login: deliver login: paste succeeded
2026-06-28T01:18:21Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582937 name=Login
2026-06-28T01:18:22Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582937 name=Login
2026-06-28T01:18:22Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-28T01:18:23Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-28T01:18:23Z [INFO] auto_login: deliver password: paste succeeded
2026-06-28T01:18:23Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582937 name=Login
2026-06-28T01:18:24Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582937 name=Login
2026-06-28T01:18:24Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582937 name=Login
2026-06-28T01:18:25Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582937 name=Login
2026-06-28T01:18:25Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-28T01:18:26Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-28T01:18:26Z [INFO] auto_login: deliver server: paste succeeded
2026-06-28T01:18:26Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582937 name=Login
2026-06-28T01:18:26Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582937 name=Login
2026-06-28T01:18:26Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-28T01:18:27Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-28T01:18:27Z [INFO] auto_login: clipboard scrubbed
2026-06-28T01:18:27Z [INFO] auto_login: login confirmed via journal at +0s: QE  0       01:10:04.640    Network '133978149': trading has been enabled - hedging mode
2026-06-28T01:18:27Z [INFO] auto_login: login gate: broker authentication confirmed; proceeding to chart-attach
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 15/16  01:19:25 =====
Error from server (NotFound): pods "etradie-mt-694e3827-4f9-0" not found
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
OK: screen-poll-13.png
OK: screen-poll-14.png
=== STAGE 13: verdict ===
Error from server (NotFound): pods "etradie-mt-694e3827-4f9-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-694e3827-4f9-0" not found
--- journal head/tail (broker handshake) ---
(MT_DIR empty; journal/EA log not collected)
...
(MT_DIR empty; journal/EA log not collected)
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 694e3827-4f9d-4948-8ee2-6ccba57e2062 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260628T010531Z ===
total 22372
drwxr-xr-x  2 softverse softverse    4096 Jun 28 02:19 .
drwxr-xr-x 29 softverse softverse    4096 Jun 28 02:05 ..
-rw-r--r--  1 softverse softverse     110 Jun 28 02:19 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 28 02:19 driver-log-full.txt
-rw-r--r--  1 softverse softverse      45 Jun 28 02:19 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 28 02:07 engine-env.txt
-rw-r--r--  1 softverse softverse       1 Jun 28 02:09 mt-config-dir.txt
-rw-r--r--  1 softverse softverse       1 Jun 28 02:09 mt-dir.txt
-rw-r--r--  1 softverse softverse      45 Jun 28 02:19 mt5-journal.txt
-rw-r--r--  1 softverse softverse      71 Jun 28 02:09 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse       0 Jun 28 02:09 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 28 02:05 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 28 02:08 release.txt
-rw-r--r--  1 softverse softverse     278 Jun 28 02:19 screen-poll-01.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:09 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   52420 Jun 28 02:19 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:10 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse   52704 Jun 28 02:19 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:10 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse   52636 Jun 28 02:19 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:11 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   52741 Jun 28 02:19 screen-poll-05.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:12 screen-poll-05.xwd
-rw-r--r--  1 softverse softverse   59482 Jun 28 02:19 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:12 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   59654 Jun 28 02:19 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:13 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse   59838 Jun 28 02:19 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:14 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse   59654 Jun 28 02:19 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:15 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse   59671 Jun 28 02:19 screen-poll-10.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:15 screen-poll-10.xwd
-rw-r--r--  1 softverse softverse   59946 Jun 28 02:19 screen-poll-11.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:16 screen-poll-11.xwd
-rw-r--r--  1 softverse softverse   59485 Jun 28 02:19 screen-poll-12.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:17 screen-poll-12.xwd
-rw-r--r--  1 softverse softverse     278 Jun 28 02:19 screen-poll-13.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:18 screen-poll-13.xwd
-rw-r--r--  1 softverse softverse   66166 Jun 28 02:19 screen-poll-14.png
-rw-r--r--  1 softverse softverse 1573739 Jun 28 02:18 screen-poll-14.xwd
-rw-r--r--  1 softverse softverse      23 Jun 28 02:08 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 28 02:19 windows-final.txt
-rw-r--r--  1 softverse softverse      31 Jun 28 02:09 windows-poll-01.txt
-rw-r--r--  1 softverse softverse      80 Jun 28 02:10 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      80 Jun 28 02:10 windows-poll-03.txt
-rw-r--r--  1 softverse softverse      80 Jun 28 02:11 windows-poll-04.txt
-rw-r--r--  1 softverse softverse      80 Jun 28 02:12 windows-poll-05.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 02:13 windows-poll-06.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 02:13 windows-poll-07.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 02:14 windows-poll-08.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 02:15 windows-poll-09.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 02:15 windows-poll-10.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 02:16 windows-poll-11.txt
-rw-r--r--  1 softverse softverse      93 Jun 28 02:17 windows-poll-12.txt
-rw-r--r--  1 softverse softverse       0 Jun 28 02:18 windows-poll-13.txt
-rw-r--r--  1 softverse softverse      42 Jun 28 02:18 windows-poll-14.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260628T010531Z
softverse@Softverse:~/hostedmt-diagnostics/20260628T010531Z$
