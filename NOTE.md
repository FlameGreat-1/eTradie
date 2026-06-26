"_DIR ==="────────────────────────ee attempts failed' driver-log-full.txt | tail -10 -20ll present' driver-log-full.txt
=== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 19:41:40
=== STAGE 7: race to the pod ===
Release: etradie-mt-f10b18de-c1e
POD=etradie-mt-f10b18de-c1e-0
[1] mt-node state: {"running":{"startedAt":"2026-06-26T19:41:42Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:cc4df219c02a8b6e4842837a8b9b89e78acddf97
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:cc4df219c02a8b6e4842837a8b9b89e78acddf97
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

===== poll 1/16  19:42:07 =====
etradie-mt-f10b18de-c1e-0   2/3   Running   0     41s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---

===== poll 2/16  19:42:48 =====
etradie-mt-f10b18de-c1e-0   2/3   Running   0     82s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T19:42:18Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T19:42:18Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T19:42:18Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T19:42:18Z [INFO] overlay-normalize(mt5): deleting baked common.ini (foreign [Common] account context blocked by trusted-device check on fresh Wine prefix -- surfaces demo-registration wizard; MT5 recreates the file after Phase 3's per-tenant login)
2026-06-26T19:42:18Z [INFO] overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)
2026-06-26T19:42:18Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T19:42:18Z [INFO] auto_login: hard-kill watchdog armed (pid=348, fires at +450s)
2026-06-26T19:42:18Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T19:42:18Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:42:20Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:42:22Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:42:25Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:42:27Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:42:29Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:42:31Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:42:33Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:42:35Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T19:42:38Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T19:42:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T19:42:42Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T19:42:44Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T19:42:46Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T19:42:48Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T19:42:48Z [INFO] auto_login: main UI window WID=12582913 detected at +30s; entering Phase 2c (3-attempt menu invocation)
2026-06-26T19:42:48Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-26T19:42:48Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-26T19:42:49Z [INFO] auto_login: main window is active; modals cleared
2026-06-26T19:42:51Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-26T19:42:51Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  19:43:45 =====
etradie-mt-f10b18de-c1e-0   2/3   Running   0     2m19s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T19:43:01Z [INFO] auto_login: login-auth wait +2s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:03Z [INFO] auto_login: login-auth wait +3s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:04Z [INFO] auto_login: login-auth wait +4s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:05Z [INFO] auto_login: login-auth wait +5s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:06Z [INFO] auto_login: login-auth wait +6s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:07Z [INFO] auto_login: login-auth wait +7s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:08Z [INFO] auto_login: login-auth wait +8s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:09Z [INFO] auto_login: login-auth wait +9s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:10Z [INFO] auto_login: login-auth wait +10s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:11Z [INFO] auto_login: login-auth wait +11s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:12Z [INFO] auto_login: login-auth wait +12s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:13Z [INFO] auto_login: login-auth wait +13s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:14Z [INFO] auto_login: login-auth wait +14s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:15Z [INFO] auto_login: login-auth wait +15s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:16Z [INFO] auto_login: login-auth wait +16s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:17Z [INFO] auto_login: login-auth wait +17s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:18Z [INFO] auto_login: login-auth wait +18s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:20Z [INFO] auto_login: login-auth wait +19s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:21Z [INFO] auto_login: login-auth wait +20s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:22Z [INFO] auto_login: login-auth wait +21s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:23Z [INFO] auto_login: login-auth wait +22s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:24Z [INFO] auto_login: login-auth wait +23s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:25Z [INFO] auto_login: login-auth wait +24s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:26Z [INFO] auto_login: login-auth wait +25s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:27Z [INFO] auto_login: login-auth wait +26s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:28Z [INFO] auto_login: login-auth wait +27s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:29Z [INFO] auto_login: login-auth wait +28s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:30Z [INFO] auto_login: login-auth wait +29s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:31Z [INFO] auto_login: login-auth wait +30s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:32Z [INFO] auto_login: login-auth wait +31s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:33Z [INFO] auto_login: login-auth wait +32s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:34Z [INFO] auto_login: login-auth wait +33s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:35Z [INFO] auto_login: login-auth wait +34s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:36Z [INFO] auto_login: login-auth wait +35s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:37Z [INFO] auto_login: login-auth wait +36s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:38Z [INFO] auto_login: login-auth wait +37s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:39Z [INFO] auto_login: login-auth wait +38s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:41Z [INFO] auto_login: login-auth wait +39s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:42Z [INFO] auto_login: login-auth wait +40s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:43Z [INFO] auto_login: login-auth wait +41s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:44Z [INFO] auto_login: login-auth wait +42s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:45Z [INFO] auto_login: login-auth wait +43s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:46Z [INFO] auto_login: login-auth wait +44s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:47Z [INFO] auto_login: login-auth wait +45s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:43:48Z [INFO] auto_login: login-auth wait +46s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  19:44:59 =====
etradie-mt-f10b18de-c1e-0   2/3   Running   0     3m33s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T19:44:16Z [INFO] auto_login: login-auth wait +73s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:17Z [INFO] auto_login: login-auth wait +74s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:18Z [INFO] auto_login: login-auth wait +75s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:20Z [INFO] auto_login: login-auth wait +76s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:21Z [INFO] auto_login: login-auth wait +77s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:22Z [INFO] auto_login: login-auth wait +78s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:23Z [INFO] auto_login: login-auth wait +79s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:24Z [INFO] auto_login: login-auth wait +80s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:25Z [INFO] auto_login: login-auth wait +81s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:26Z [INFO] auto_login: login-auth wait +82s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:27Z [INFO] auto_login: login-auth wait +83s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:28Z [INFO] auto_login: login-auth wait +84s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:29Z [INFO] auto_login: login-auth wait +85s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:30Z [INFO] auto_login: login-auth wait +86s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:31Z [INFO] auto_login: login-auth wait +87s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:32Z [INFO] auto_login: login-auth wait +88s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:33Z [INFO] auto_login: login-auth wait +89s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:34Z [INFO] auto_login: login-auth wait +90s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:35Z [INFO] auto_login: login-auth wait +91s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:36Z [INFO] auto_login: login-auth wait +92s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:37Z [INFO] auto_login: login-auth wait +93s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:38Z [INFO] auto_login: login-auth wait +94s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:40Z [INFO] auto_login: login-auth wait +95s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:41Z [INFO] auto_login: login-auth wait +96s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:42Z [INFO] auto_login: login-auth wait +97s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:43Z [INFO] auto_login: login-auth wait +98s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:44Z [INFO] auto_login: login-auth wait +99s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:45Z [INFO] auto_login: login-auth wait +100s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:46Z [INFO] auto_login: login-auth wait +101s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:47Z [INFO] auto_login: login-auth wait +102s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:48Z [INFO] auto_login: login-auth wait +103s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:49Z [INFO] auto_login: login-auth wait +104s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:50Z [INFO] auto_login: login-auth wait +105s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:51Z [INFO] auto_login: login-auth wait +106s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:52Z [INFO] auto_login: login-auth wait +107s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:53Z [INFO] auto_login: login-auth wait +108s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:54Z [INFO] auto_login: login-auth wait +109s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:55Z [INFO] auto_login: login-auth wait +110s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:56Z [INFO] auto_login: login-auth wait +111s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:57Z [INFO] auto_login: login-auth wait +112s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:58Z [INFO] auto_login: login-auth wait +113s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:59Z [INFO] auto_login: login-auth wait +114s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:01Z [INFO] auto_login: login-auth wait +115s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:02Z [INFO] auto_login: login-auth wait +116s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:03Z [INFO] auto_login: login-auth wait +117s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  19:46:13 =====
etradie-mt-f10b18de-c1e-0   2/3   Running   0     4m47s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T19:44:20Z [INFO] auto_login: login-auth wait +76s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:21Z [INFO] auto_login: login-auth wait +77s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:22Z [INFO] auto_login: login-auth wait +78s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:23Z [INFO] auto_login: login-auth wait +79s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:24Z [INFO] auto_login: login-auth wait +80s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:25Z [INFO] auto_login: login-auth wait +81s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:26Z [INFO] auto_login: login-auth wait +82s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:27Z [INFO] auto_login: login-auth wait +83s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:28Z [INFO] auto_login: login-auth wait +84s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:29Z [INFO] auto_login: login-auth wait +85s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:30Z [INFO] auto_login: login-auth wait +86s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:31Z [INFO] auto_login: login-auth wait +87s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:32Z [INFO] auto_login: login-auth wait +88s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:33Z [INFO] auto_login: login-auth wait +89s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:34Z [INFO] auto_login: login-auth wait +90s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:35Z [INFO] auto_login: login-auth wait +91s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:36Z [INFO] auto_login: login-auth wait +92s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:37Z [INFO] auto_login: login-auth wait +93s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:38Z [INFO] auto_login: login-auth wait +94s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:40Z [INFO] auto_login: login-auth wait +95s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:41Z [INFO] auto_login: login-auth wait +96s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:42Z [INFO] auto_login: login-auth wait +97s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:43Z [INFO] auto_login: login-auth wait +98s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:44Z [INFO] auto_login: login-auth wait +99s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:45Z [INFO] auto_login: login-auth wait +100s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:46Z [INFO] auto_login: login-auth wait +101s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:47Z [INFO] auto_login: login-auth wait +102s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:48Z [INFO] auto_login: login-auth wait +103s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:49Z [INFO] auto_login: login-auth wait +104s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:50Z [INFO] auto_login: login-auth wait +105s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:51Z [INFO] auto_login: login-auth wait +106s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:52Z [INFO] auto_login: login-auth wait +107s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:53Z [INFO] auto_login: login-auth wait +108s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:54Z [INFO] auto_login: login-auth wait +109s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:55Z [INFO] auto_login: login-auth wait +110s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:56Z [INFO] auto_login: login-auth wait +111s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:57Z [INFO] auto_login: login-auth wait +112s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:58Z [INFO] auto_login: login-auth wait +113s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:59Z [INFO] auto_login: login-auth wait +114s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:01Z [INFO] auto_login: login-auth wait +115s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:02Z [INFO] auto_login: login-auth wait +116s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:03Z [INFO] auto_login: login-auth wait +117s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:04Z [INFO] auto_login: login-auth wait +118s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:05Z [INFO] auto_login: login-auth wait +119s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:06Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  19:47:33 =====
etradie-mt-f10b18de-c1e-0   2/3   Running   0     6m6s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T19:44:20Z [INFO] auto_login: login-auth wait +76s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:21Z [INFO] auto_login: login-auth wait +77s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:22Z [INFO] auto_login: login-auth wait +78s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:23Z [INFO] auto_login: login-auth wait +79s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:24Z [INFO] auto_login: login-auth wait +80s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:25Z [INFO] auto_login: login-auth wait +81s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:26Z [INFO] auto_login: login-auth wait +82s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:27Z [INFO] auto_login: login-auth wait +83s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:28Z [INFO] auto_login: login-auth wait +84s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:29Z [INFO] auto_login: login-auth wait +85s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:30Z [INFO] auto_login: login-auth wait +86s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:31Z [INFO] auto_login: login-auth wait +87s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:32Z [INFO] auto_login: login-auth wait +88s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:33Z [INFO] auto_login: login-auth wait +89s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:34Z [INFO] auto_login: login-auth wait +90s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:35Z [INFO] auto_login: login-auth wait +91s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:36Z [INFO] auto_login: login-auth wait +92s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:37Z [INFO] auto_login: login-auth wait +93s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:38Z [INFO] auto_login: login-auth wait +94s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:40Z [INFO] auto_login: login-auth wait +95s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:41Z [INFO] auto_login: login-auth wait +96s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:42Z [INFO] auto_login: login-auth wait +97s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:43Z [INFO] auto_login: login-auth wait +98s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:44Z [INFO] auto_login: login-auth wait +99s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:45Z [INFO] auto_login: login-auth wait +100s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:46Z [INFO] auto_login: login-auth wait +101s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:47Z [INFO] auto_login: login-auth wait +102s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:48Z [INFO] auto_login: login-auth wait +103s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:49Z [INFO] auto_login: login-auth wait +104s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:50Z [INFO] auto_login: login-auth wait +105s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:51Z [INFO] auto_login: login-auth wait +106s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:52Z [INFO] auto_login: login-auth wait +107s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:53Z [INFO] auto_login: login-auth wait +108s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:54Z [INFO] auto_login: login-auth wait +109s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:55Z [INFO] auto_login: login-auth wait +110s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:56Z [INFO] auto_login: login-auth wait +111s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:57Z [INFO] auto_login: login-auth wait +112s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:58Z [INFO] auto_login: login-auth wait +113s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:59Z [INFO] auto_login: login-auth wait +114s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:01Z [INFO] auto_login: login-auth wait +115s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:02Z [INFO] auto_login: login-auth wait +116s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:03Z [INFO] auto_login: login-auth wait +117s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:04Z [INFO] auto_login: login-auth wait +118s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:05Z [INFO] auto_login: login-auth wait +119s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:06Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
--- :5555 LISTEN state (0A) ---

1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names


===== poll 7/16  19:48:31 =====
etradie-mt-f10b18de-c1e-0   2/3   Running   0     7m7s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T19:44:20Z [INFO] auto_login: login-auth wait +76s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:21Z [INFO] auto_login: login-auth wait +77s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:22Z [INFO] auto_login: login-auth wait +78s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:23Z [INFO] auto_login: login-auth wait +79s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:24Z [INFO] auto_login: login-auth wait +80s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:25Z [INFO] auto_login: login-auth wait +81s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:26Z [INFO] auto_login: login-auth wait +82s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:27Z [INFO] auto_login: login-auth wait +83s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:28Z [INFO] auto_login: login-auth wait +84s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:29Z [INFO] auto_login: login-auth wait +85s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:30Z [INFO] auto_login: login-auth wait +86s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:31Z [INFO] auto_login: login-auth wait +87s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:32Z [INFO] auto_login: login-auth wait +88s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:33Z [INFO] auto_login: login-auth wait +89s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:34Z [INFO] auto_login: login-auth wait +90s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:35Z [INFO] auto_login: login-auth wait +91s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:36Z [INFO] auto_login: login-auth wait +92s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:37Z [INFO] auto_login: login-auth wait +93s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:38Z [INFO] auto_login: login-auth wait +94s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:40Z [INFO] auto_login: login-auth wait +95s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:41Z [INFO] auto_login: login-auth wait +96s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:42Z [INFO] auto_login: login-auth wait +97s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:43Z [INFO] auto_login: login-auth wait +98s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:44Z [INFO] auto_login: login-auth wait +99s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:45Z [INFO] auto_login: login-auth wait +100s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:46Z [INFO] auto_login: login-auth wait +101s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:47Z [INFO] auto_login: login-auth wait +102s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:48Z [INFO] auto_login: login-auth wait +103s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:49Z [INFO] auto_login: login-auth wait +104s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:50Z [INFO] auto_login: login-auth wait +105s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:51Z [INFO] auto_login: login-auth wait +106s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:52Z [INFO] auto_login: login-auth wait +107s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:53Z [INFO] auto_login: login-auth wait +108s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:54Z [INFO] auto_login: login-auth wait +109s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:55Z [INFO] auto_login: login-auth wait +110s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:56Z [INFO] auto_login: login-auth wait +111s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:57Z [INFO] auto_login: login-auth wait +112s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:58Z [INFO] auto_login: login-auth wait +113s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:59Z [INFO] auto_login: login-auth wait +114s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:01Z [INFO] auto_login: login-auth wait +115s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:02Z [INFO] auto_login: login-auth wait +116s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:03Z [INFO] auto_login: login-auth wait +117s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:04Z [INFO] auto_login: login-auth wait +118s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:05Z [INFO] auto_login: login-auth wait +119s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:06Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names


===== poll 8/16  19:49:43 =====
etradie-mt-f10b18de-c1e-0   2/3   Running   0     8m17s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T19:44:20Z [INFO] auto_login: login-auth wait +76s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:21Z [INFO] auto_login: login-auth wait +77s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:22Z [INFO] auto_login: login-auth wait +78s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:23Z [INFO] auto_login: login-auth wait +79s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:24Z [INFO] auto_login: login-auth wait +80s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:25Z [INFO] auto_login: login-auth wait +81s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:26Z [INFO] auto_login: login-auth wait +82s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:27Z [INFO] auto_login: login-auth wait +83s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:28Z [INFO] auto_login: login-auth wait +84s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:29Z [INFO] auto_login: login-auth wait +85s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:30Z [INFO] auto_login: login-auth wait +86s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:31Z [INFO] auto_login: login-auth wait +87s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:32Z [INFO] auto_login: login-auth wait +88s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:33Z [INFO] auto_login: login-auth wait +89s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:34Z [INFO] auto_login: login-auth wait +90s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:35Z [INFO] auto_login: login-auth wait +91s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:36Z [INFO] auto_login: login-auth wait +92s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:37Z [INFO] auto_login: login-auth wait +93s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:38Z [INFO] auto_login: login-auth wait +94s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:40Z [INFO] auto_login: login-auth wait +95s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:41Z [INFO] auto_login: login-auth wait +96s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:42Z [INFO] auto_login: login-auth wait +97s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:43Z [INFO] auto_login: login-auth wait +98s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:44Z [INFO] auto_login: login-auth wait +99s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:45Z [INFO] auto_login: login-auth wait +100s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:46Z [INFO] auto_login: login-auth wait +101s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:47Z [INFO] auto_login: login-auth wait +102s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:48Z [INFO] auto_login: login-auth wait +103s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:49Z [INFO] auto_login: login-auth wait +104s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:50Z [INFO] auto_login: login-auth wait +105s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:51Z [INFO] auto_login: login-auth wait +106s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:52Z [INFO] auto_login: login-auth wait +107s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:53Z [INFO] auto_login: login-auth wait +108s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:54Z [INFO] auto_login: login-auth wait +109s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:55Z [INFO] auto_login: login-auth wait +110s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:56Z [INFO] auto_login: login-auth wait +111s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:57Z [INFO] auto_login: login-auth wait +112s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:58Z [INFO] auto_login: login-auth wait +113s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:59Z [INFO] auto_login: login-auth wait +114s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:01Z [INFO] auto_login: login-auth wait +115s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:02Z [INFO] auto_login: login-auth wait +116s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:03Z [INFO] auto_login: login-auth wait +117s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:04Z [INFO] auto_login: login-auth wait +118s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:05Z [INFO] auto_login: login-auth wait +119s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:06Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  19:50:46 =====
etradie-mt-f10b18de-c1e-0   2/3   Running   0     9m22s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T19:44:21Z [INFO] auto_login: login-auth wait +77s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:22Z [INFO] auto_login: login-auth wait +78s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:23Z [INFO] auto_login: login-auth wait +79s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:24Z [INFO] auto_login: login-auth wait +80s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:25Z [INFO] auto_login: login-auth wait +81s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:26Z [INFO] auto_login: login-auth wait +82s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:27Z [INFO] auto_login: login-auth wait +83s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:28Z [INFO] auto_login: login-auth wait +84s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:29Z [INFO] auto_login: login-auth wait +85s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:30Z [INFO] auto_login: login-auth wait +86s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:31Z [INFO] auto_login: login-auth wait +87s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:32Z [INFO] auto_login: login-auth wait +88s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:33Z [INFO] auto_login: login-auth wait +89s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:34Z [INFO] auto_login: login-auth wait +90s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:35Z [INFO] auto_login: login-auth wait +91s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:36Z [INFO] auto_login: login-auth wait +92s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:37Z [INFO] auto_login: login-auth wait +93s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:38Z [INFO] auto_login: login-auth wait +94s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:40Z [INFO] auto_login: login-auth wait +95s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:41Z [INFO] auto_login: login-auth wait +96s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:42Z [INFO] auto_login: login-auth wait +97s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:43Z [INFO] auto_login: login-auth wait +98s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:44Z [INFO] auto_login: login-auth wait +99s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:45Z [INFO] auto_login: login-auth wait +100s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:46Z [INFO] auto_login: login-auth wait +101s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:47Z [INFO] auto_login: login-auth wait +102s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:48Z [INFO] auto_login: login-auth wait +103s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:49Z [INFO] auto_login: login-auth wait +104s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:50Z [INFO] auto_login: login-auth wait +105s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:51Z [INFO] auto_login: login-auth wait +106s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:52Z [INFO] auto_login: login-auth wait +107s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:53Z [INFO] auto_login: login-auth wait +108s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:54Z [INFO] auto_login: login-auth wait +109s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:55Z [INFO] auto_login: login-auth wait +110s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:56Z [INFO] auto_login: login-auth wait +111s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:57Z [INFO] auto_login: login-auth wait +112s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:58Z [INFO] auto_login: login-auth wait +113s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:44:59Z [INFO] auto_login: login-auth wait +114s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:01Z [INFO] auto_login: login-auth wait +115s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:02Z [INFO] auto_login: login-auth wait +116s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:03Z [INFO] auto_login: login-auth wait +117s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:04Z [INFO] auto_login: login-auth wait +118s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:05Z [INFO] auto_login: login-auth wait +119s: active title='Welcome to LiveUpdate' (awaiting broker connect/authorize line in journal)
2026-06-26T19:45:06Z [ERROR] auto_login: login gate: broker authentication NOT confirmed within 120s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns.
2026-06-26T19:50:28Z [WARN] MetaTrader exited with code 143
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  19:51:35 =====
etradie-mt-f10b18de-c1e-0   2/3   Terminating   0     10m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T19:51:01Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:51:03Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:51:05Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:51:08Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:51:10Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:51:12Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:51:14Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T19:51:16Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name='Login'
2026-06-26T19:51:16Z [INFO] auto_login: Login dialog WID=12582936 detected at +18s
2026-06-26T19:51:16Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-26T19:51:17Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-26T19:51:18Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-26T19:51:18Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-26T19:51:19Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-26T19:51:19Z [INFO] auto_login: deliver login: paste succeeded
2026-06-26T19:51:19Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-26T19:51:20Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-26T19:51:20Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-26T19:51:21Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-26T19:51:21Z [INFO] auto_login: deliver password: paste succeeded
2026-06-26T19:51:21Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-26T19:51:22Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-26T19:51:22Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-26T19:51:23Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-26T19:51:23Z [INFO] auto_login: deliver server: paste succeeded
2026-06-26T19:51:23Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-26T19:51:23Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-26T19:51:24Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-26T19:51:24Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-26T19:51:24Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-26T19:51:25Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-26T19:51:25Z [INFO] auto_login: clipboard scrubbed
2026-06-26T19:51:25Z [INFO] auto_login: login-auth wait +0s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:26Z [INFO] auto_login: login-auth wait +1s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:27Z [INFO] auto_login: login-auth wait +2s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:28Z [INFO] auto_login: login-auth wait +3s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:29Z [INFO] auto_login: login-auth wait +4s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:30Z [INFO] auto_login: login-auth wait +5s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:31Z [INFO] auto_login: login-auth wait +6s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:32Z [INFO] auto_login: login-auth wait +7s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:33Z [INFO] auto_login: login-auth wait +8s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:34Z [INFO] auto_login: login-auth wait +9s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:35Z [INFO] auto_login: login-auth wait +10s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:36Z [INFO] auto_login: login-auth wait +11s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
2026-06-26T19:51:38Z [INFO] auto_login: login-auth wait +12s: active title='133978149 -   - Netting' (awaiting broker connect/authorize line in journal)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  19:52:28 =====
Error from server (NotFound): pods "etradie-mt-f10b18de-c1e-0" not found
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
=== STAGE 13: verdict ===
Error from server (NotFound): pods "etradie-mt-f10b18de-c1e-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-f10b18de-c1e-0" not found
--- journal head/tail (broker handshake) ---
(MT_DIR empty; journal/EA log not collected)
...
(MT_DIR empty; journal/EA log not collected)
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 f10b18de-c1e2-4c0c-a198-e99548d87098 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260626T193854Z ===
total 14532
drwxr-xr-x  2 softverse softverse    4096 Jun 26 20:52 .
drwxr-xr-x 18 softverse softverse    4096 Jun 26 20:38 ..
-rw-r--r--  1 softverse softverse     110 Jun 26 20:52 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 26 20:52 driver-log-full.txt
-rw-r--r--  1 softverse softverse      45 Jun 26 20:52 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 26 20:39 engine-env.txt
-rw-r--r--  1 softverse softverse       1 Jun 26 20:42 mt-config-dir.txt
-rw-r--r--  1 softverse softverse       1 Jun 26 20:42 mt-dir.txt
-rw-r--r--  1 softverse softverse      45 Jun 26 20:52 mt5-journal.txt
-rw-r--r--  1 softverse softverse      71 Jun 26 20:42 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse       0 Jun 26 20:42 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 26 20:38 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 26 20:41 release.txt
-rw-r--r--  1 softverse softverse      35 Jun 26 20:42 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   59657 Jun 26 20:52 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 20:43 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse   75997 Jun 26 20:52 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 20:44 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse   76004 Jun 26 20:52 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 20:45 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   75997 Jun 26 20:52 screen-poll-05.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 20:46 screen-poll-05.xwd
-rw-r--r--  1 softverse softverse   75994 Jun 26 20:52 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 20:47 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   75997 Jun 26 20:52 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 20:49 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse   76004 Jun 26 20:52 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 20:50 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse     278 Jun 26 20:52 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 20:51 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse   59334 Jun 26 20:52 screen-poll-10.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 20:51 screen-poll-10.xwd
-rw-r--r--  1 softverse softverse      23 Jun 26 20:41 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 26 20:52 windows-final.txt
-rw-r--r--  1 softverse softverse       0 Jun 26 20:42 windows-poll-01.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 20:43 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      82 Jun 26 20:44 windows-poll-03.txt
-rw-r--r--  1 softverse softverse      82 Jun 26 20:45 windows-poll-04.txt
-rw-r--r--  1 softverse softverse      82 Jun 26 20:47 windows-poll-05.txt
-rw-r--r--  1 softverse softverse      82 Jun 26 20:48 windows-poll-06.txt
-rw-r--r--  1 softverse softverse      82 Jun 26 20:49 windows-poll-07.txt
-rw-r--r--  1 softverse softverse      65 Jun 26 20:50 windows-poll-08.txt
-rw-r--r--  1 softverse softverse       0 Jun 26 20:51 windows-poll-09.txt
-rw-r--r--  1 softverse softverse      42 Jun 26 20:51 windows-poll-10.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260626T193854Z
softverse@Softverse:~/hostedmt-diagnostics/20260626T193854Z$ 