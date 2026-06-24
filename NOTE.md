
# ── Step 8: verify fluxbox started + EWMH atoms ─────────────────────
echo "  explorer.exe ~/phase2c-diagnostics/screen-final.png    (end state)")" dialog)"g|BOTH paste and type failed' driver-log-full.txt | tail -10>/dev/null

================================================================
RE-PROVISION FROM DASHBOARD NOW.
Press Enter the SECOND you click submit.
================================================================

Release: etradie-mt-f89501e8-e63
POD=etradie-mt-f89501e8-e63-0
[1] mt-node state: {"waiting":{"reason":"PodInitializing"}}
[2] mt-node state: {"running":{"startedAt":"2026-06-24T13:09:28Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:acccb4cc9cf7750a07e92ea61eb51c519eb9267b

================================================================
TOOL AVAILABILITY CHECK
================================================================
/usr/bin/xdotool
/usr/bin/xclip
/usr/bin/xprop
/usr/bin/xwd
/usr/bin/fluxbox
---
xclip version 0.13

================================================================
FLUXBOX + EWMH READINESS
================================================================

============ poll 1 / 16  (13:09:53) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     41s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:09:55Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T13:09:55Z [INFO] fluxbox ready (pid=212); _NET_ACTIVE_WINDOW available

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory


============ poll 2 / 16  (13:10:31) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     79s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:09:55Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T13:09:55Z [INFO] fluxbox ready (pid=212); _NET_ACTIVE_WINDOW available
2026-06-24T13:09:56Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T13:09:56Z [INFO] auto_login: hard-kill watchdog armed (pid=262, fires at +270s)
2026-06-24T13:09:56Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T13:10:27Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T13:10:27Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T13:10:27Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T13:10:28Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T13:10:30Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s
2026-06-24T13:10:30Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T13:10:31Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T13:10:31Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T13:10:31Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:10:32Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:10:32Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:10:32Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T13:10:33Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T13:10:33Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:10 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 3 / 16  (13:11:08) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     118s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:10:34Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:10:34Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T13:10:35Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T13:10:35Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:10:36Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:10:36Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:10:36Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:10:36Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T13:10:37Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T13:10:37Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T13:10:37Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:10:38Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:10:38Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:10:38Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:40Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:43Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:45Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:47Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:50Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:52Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:54Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:56Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:59Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:01Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:02Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:11:04Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:06Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:13Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:10 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 4 / 16  (13:11:48) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     2m37s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:10:37Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:10:38Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:10:38Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:10:38Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:40Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:43Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:45Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:47Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:50Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:52Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:54Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:56Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:59Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:01Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:02Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:11:04Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:06Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:13Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:20Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:22Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:27Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:29Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:34Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:36Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:10 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- capturing framebuffer (poll 4) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 5 / 16  (13:12:40) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     3m29s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:10:37Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:10:38Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:10:38Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:10:38Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:40Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:43Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:45Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:47Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:50Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:52Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:54Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:56Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:59Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:01Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:02Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:11:04Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:06Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:13Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:20Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:22Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:27Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:29Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:34Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:36Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:10 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 6 / 16  (13:13:19) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     4m6s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:10:37Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:10:38Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:10:38Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:10:38Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:40Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:43Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:45Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:47Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:50Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:52Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:54Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:56Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:59Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:01Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:02Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:11:04Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:06Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:13Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:20Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:22Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:27Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:29Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:34Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:36Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:10 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 7 / 16  (13:13:57) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     4m45s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:10:38Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:10:38Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:10:38Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:40Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:43Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:45Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:47Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:50Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:52Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:54Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:56Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:59Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:01Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:02Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:11:04Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:06Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:13Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:20Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:22Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:27Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:29Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:34Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:36Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:13:56Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:10 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 8 / 16  (13:14:34) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     5m22s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:10:38Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:10:38Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:10:38Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:40Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:43Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:45Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:47Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:50Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:52Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:54Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:56Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:59Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:01Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:02Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:11:04Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:06Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:13Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:20Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:22Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:27Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:29Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:34Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:36Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:13:56Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:10 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- capturing framebuffer (poll 8) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 9 / 16  (13:15:17) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     6m5s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:10:38Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:10:38Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:40Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:43Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:45Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:47Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:50Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:52Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:54Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:56Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:10:59Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:01Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:02Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:11:04Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:06Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:13Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:20Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:22Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:27Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:29Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:34Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:36Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:13:56Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T13:15:11Z [WARN] MetaTrader exited with code 143

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:10 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 10 / 16  (13:15:54) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     6m42s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:11:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:20Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:22Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:27Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:29Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:34Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:11:36Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:13:56Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T13:15:11Z [WARN] MetaTrader exited with code 143
2026-06-24T13:15:41Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T13:15:41Z [INFO] auto_login: hard-kill watchdog armed (pid=1555, fires at +270s)
2026-06-24T13:15:41Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T13:15:51Z [INFO] auto_login: Login dialog WID=12582936 detected at +10s
2026-06-24T13:15:51Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T13:15:52Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T13:15:53Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T13:15:53Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:15:54Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:15:54Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:15:54Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T13:15:55Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T13:15:55Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:15:56Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:15:56Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:15:56Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T13:15:56Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T13:15:56Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:15 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 11 / 16  (13:16:32) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     7m20s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:15:55Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:15:56Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:15:56Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:15:56Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T13:15:56Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T13:15:56Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:15:58Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:15:58Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:15:58Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-24T13:15:58Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-24T13:15:59Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-24T13:15:59Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T13:15:59Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:16:00Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:16:00Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:16:00Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:02Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:05Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:07Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:14Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:21Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:23Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:28Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:30Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:15 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 12 / 16  (13:17:09) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     7m57s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:15:59Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T13:15:59Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:16:00Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:16:00Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:16:00Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:02Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:05Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:07Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:14Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:21Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:23Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:28Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:30Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:35Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:37Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:39Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:41Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:44Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:46Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:48Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:51Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:53Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:55Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:58Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:15 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- capturing framebuffer (poll 12) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 13 / 16  (13:17:53) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     8m41s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:15:59Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T13:15:59Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:16:00Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:16:00Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:16:00Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:02Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:05Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:07Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:14Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:21Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:23Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:28Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:30Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:35Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:37Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:39Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:41Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:44Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:46Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:48Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:51Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:53Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:55Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:58Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:15 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 14 / 16  (13:18:30) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     9m19s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:15:59Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T13:15:59Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:16:00Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:16:00Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:16:00Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:02Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:05Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:07Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:14Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:21Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:23Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:28Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:30Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:35Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:37Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:39Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:41Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:44Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:46Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:48Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:51Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:53Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:55Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:58Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:15 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 15 / 16  (13:19:08) ============
etradie-mt-f89501e8-e63-0   2/3   Running   0     9m57s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:15:59Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T13:15:59Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:16:00Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:16:00Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:16:00Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:02Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:05Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:07Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:14Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:21Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:23Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:28Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:30Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:35Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:37Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:39Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:41Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:44Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:46Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:48Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:51Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:53Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:55Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:58Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:15 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 16 / 16  (13:19:47) ============
etradie-mt-f89501e8-e63-0   2/3   Terminating   0     10m

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:16:00Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:16:00Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:16:00Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:02Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:05Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:07Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:09Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:11Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:14Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:16Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:18Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:21Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:23Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:25Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:28Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:30Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:32Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:35Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:37Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:39Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:41Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:44Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:46Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:48Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:51Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:53Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:55Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:16:58Z [INFO] auto_login: dismiss follow-up window: '133978149 -   - Netting' (WID=12582913)
2026-06-24T13:19:42Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T13:19:46Z [INFO] Caught shutdown signal, terminating auto-login driver + MetaTrader + fluxbox + Xvfb

--- :5555 socket state ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- accounts.dat presence ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- capturing framebuffer (poll 16) ---

============ FINAL ARTIFACTS ============
222 driver-log-full.txt
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")
mt5-journal.txt: 0 lines
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")
OK: screen-poll-4.png
OK: screen-poll-8.png
OK: screen-poll-12.png
OK: screen-final.png

============ VERDICT ============
NAME                        READY   STATUS        RESTARTS   AGE
etradie-mt-f89501e8-e63-0   2/3     Terminating   0          11m

--- accounts.dat (login completed?) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- MQL5/Logs (EA loaded?) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- :5555 socket ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- MT5 journal (broker response is here) ---
error: Internal error occurred: unable to upgrade connection: container not found ("mt-node")

--- DB row ---
                  id                  | status |                                status_message                                | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+------------+-----------
 f89501e8-e635-49ef-ac3e-270f5b108d8a | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout |            | t
(1 row)


============ DRIVER SENTINELS ============

--- fluxbox readiness ---
2026-06-24T13:09:55Z [INFO] fluxbox ready (pid=212); _NET_ACTIVE_WINDOW available

--- Welcome modal handling ---

--- Phase 2c (Login dialog open) ---
2026-06-24T13:10:30Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +34s

--- Phase 3 strategy + per-field outcome ---
2026-06-24T13:10:31Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:10:32Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:10:32Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:10:32Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T13:10:33Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:10:34Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:10:34Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:10:34Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T13:10:35Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:10:36Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:10:36Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:10:36Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:15:53Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:15:54Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:15:54Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:15:54Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T13:15:55Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:15:56Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:15:56Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:15:56Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T13:15:56Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:15:58Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:15:58Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:15:58Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login

--- Phase 3 stage transitions ---
2026-06-24T13:10:30Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T13:10:31Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T13:10:31Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T13:10:32Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T13:10:33Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T13:10:34Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T13:10:35Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T13:10:36Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:10:36Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T13:10:37Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T13:10:37Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T13:10:38Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:15:51Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T13:15:52Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T13:15:53Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T13:15:54Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T13:15:55Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T13:15:56Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T13:15:56Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T13:15:58Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login

--- Final outcome ---
2026-06-24T13:09:56Z [INFO] auto_login: hard-kill watchdog armed (pid=262, fires at +270s)
2026-06-24T13:13:56Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T13:15:41Z [INFO] auto_login: hard-kill watchdog armed (pid=1555, fires at +270s)
2026-06-24T13:19:42Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting

============ FILES ============
-rw-r--r-- 1 softverse softverse  3674 Jun 24 09:11 /home/softverse/phase2c-diagnostics/after-10down.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 09:11 /home/softverse/phase2c-diagnostics/after-9down.png
-rw-r--r-- 1 softverse softverse 14204 Jun 24 09:52 /home/softverse/phase2c-diagnostics/after-altf-l.png
-rw-r--r-- 1 softverse softverse 13654 Jun 24 09:52 /home/softverse/phase2c-diagnostics/after-altf.png
-rw-r--r-- 1 softverse softverse 24872 Jun 24 08:57 /home/softverse/phase2c-diagnostics/driver-log-full-v2.txt
-rw-r--r-- 1 softverse softverse 19487 Jun 24 14:20 /home/softverse/phase2c-diagnostics/driver-log-full.txt
-rw-r--r-- 1 softverse softverse  1292 Jun 24 08:57 /home/softverse/phase2c-diagnostics/mt5-journal-v2.txt
-rw-r--r-- 1 softverse softverse     0 Jun 24 14:20 /home/softverse/phase2c-diagnostics/mt5-journal.txt
-rw-r--r-- 1 softverse softverse 19633 Jun 24 08:52 /home/softverse/phase2c-diagnostics/pod-state.txt
-rw-r--r-- 1 softverse softverse  7397 Jun 24 09:00 /home/softverse/phase2c-diagnostics/screen-final-now.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 14:20 /home/softverse/phase2c-diagnostics/screen-final.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 08:57 /home/softverse/phase2c-diagnostics/screen-now.png
-rw-r--r-- 1 softverse softverse  3691 Jun 24 14:20 /home/softverse/phase2c-diagnostics/screen-poll-12.png
-rw-r--r-- 1 softverse softverse  3691 Jun 24 14:20 /home/softverse/phase2c-diagnostics/screen-poll-4.png
-rw-r--r-- 1 softverse softverse  3691 Jun 24 14:20 /home/softverse/phase2c-diagnostics/screen-poll-8.png
-rw-r--r-- 1 softverse softverse     0 Jun 24 14:20 /home/softverse/phase2c-diagnostics/windows-final.txt
-rw-r--r-- 1 softverse softverse    41 Jun 24 08:50 /home/softverse/phase2c-diagnostics/windows-poll-1.txt
-rw-r--r-- 1 softverse softverse    41 Jun 24 08:51 /home/softverse/phase2c-diagnostics/windows-poll-2.txt
-rw-r--r-- 1 softverse softverse  2374 Jun 24 08:52 /home/softverse/phase2c-diagnostics/xwininfo-final.txt

Open these screenshots to visually verify:
  explorer.exe ~/phase2c-diagnostics/screen-poll-4.png   (early - Login dialog)
  explorer.exe ~/phase2c-diagnostics/screen-poll-8.png   (mid-Phase-3)
  explorer.exe ~/phase2c-diagnostics/screen-final.png    (end state)
softverse@Softverse:~/phase2c-diagnostics$