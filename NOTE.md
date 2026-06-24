
================================================================
RE-PROVISION FROM DASHBOARD NOW.
Press Enter the SECOND you click submit.
================================================================

Release: etradie-mt-2cd3d52c-747
POD=etradie-mt-2cd3d52c-747-0
[1] mt-node state: {"running":{"startedAt":"2026-06-24T13:55:17Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:4e1b17cdc5ea74ca50772b7c2791ce5205875489

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

============ poll 1 / 16  (13:55:41) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     41s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:55:45Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T13:55:45Z [INFO] fluxbox ready (pid=210); _NET_ACTIVE_WINDOW available
2026-06-24T13:55:45Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T13:55:45Z [INFO] auto_login: hard-kill watchdog armed (pid=260, fires at +270s)
2026-06-24T13:55:45Z [INFO] auto_login: terminal process detected at +0s

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

============ poll 2 / 16  (13:56:22) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     83s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:55:45Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T13:55:45Z [INFO] fluxbox ready (pid=210); _NET_ACTIVE_WINDOW available
2026-06-24T13:55:45Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T13:55:45Z [INFO] auto_login: hard-kill watchdog armed (pid=260, fires at +270s)
2026-06-24T13:55:45Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T13:56:16Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T13:56:16Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T13:56:16Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T13:56:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T13:56:18Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T13:56:18Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T13:56:19Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:56:21Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:56:21Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:56:21Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:56:23Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:56:23Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:56:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:56:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:56:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:25Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:56 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 3 / 16  (13:57:00) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     2m1s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:55:45Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T13:56:16Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T13:56:16Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T13:56:16Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T13:56:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T13:56:18Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T13:56:18Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T13:56:19Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:56:21Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:56:21Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:56:21Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:56:23Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:56:23Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:56:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:56:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:56:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:25Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:56:27Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:56:27Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:56 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 4 / 16  (13:57:37) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     2m38s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:55:45Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T13:56:16Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T13:56:16Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T13:56:16Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T13:56:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T13:56:18Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T13:56:18Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T13:56:19Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:56:21Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:56:21Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:56:21Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:56:23Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:56:23Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:56:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:56:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:56:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:25Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:56:27Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:56:27Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:56 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- capturing framebuffer (poll 4) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 5 / 16  (13:58:25) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     3m26s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:55:45Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T13:56:16Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T13:56:16Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T13:56:16Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T13:56:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T13:56:18Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T13:56:18Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T13:56:19Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:56:21Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:56:21Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:56:21Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:56:23Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:56:23Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:56:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:56:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:56:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:25Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:56:27Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:56:27Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:56 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 6 / 16  (13:59:04) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     4m4s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:55:45Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T13:56:16Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T13:56:16Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T13:56:16Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T13:56:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T13:56:18Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T13:56:18Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T13:56:19Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:56:21Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:56:21Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:56:21Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:56:23Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:56:23Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:56:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:56:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:56:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:25Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:56:27Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:56:27Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:56 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 7 / 16  (13:59:41) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     4m41s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:55:45Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T13:56:16Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T13:56:16Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T13:56:16Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T13:56:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T13:56:18Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T13:56:18Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T13:56:19Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:56:21Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:56:21Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:56:21Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:56:23Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:56:23Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:56:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:56:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:56:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:25Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:56:27Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:56:27Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:56 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 8 / 16  (14:00:18) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     5m19s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:56:16Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T13:56:16Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T13:56:16Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T13:56:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T13:56:18Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T13:56:18Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T13:56:19Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:56:21Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:56:21Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:56:21Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:56:23Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:56:23Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:56:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:56:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:56:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:25Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:56:27Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:56:27Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:59:45Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:56 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- capturing framebuffer (poll 8) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 9 / 16  (14:01:05) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     6m6s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:56:16Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T13:56:16Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T13:56:16Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T13:56:18Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T13:56:18Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T13:56:19Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T13:56:20Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T13:56:21Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T13:56:21Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T13:56:21Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T13:56:22Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T13:56:23Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T13:56:23Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T13:56:23Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T13:56:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:56:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:56:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:25Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:56:27Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:56:27Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:59:45Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T14:01:00Z [WARN] MetaTrader exited with code 143

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 13:56 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 10 / 16  (14:01:43) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     6m44s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:56:24Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T13:56:24Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T13:56:24Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T13:56:25Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T13:56:26Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T13:56:27Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T13:56:27Z [INFO] auto_login: clipboard scrubbed
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:59:45Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T14:01:00Z [WARN] MetaTrader exited with code 143
2026-06-24T14:01:30Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T14:01:30Z [INFO] auto_login: hard-kill watchdog armed (pid=1418, fires at +270s)
2026-06-24T14:01:30Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T14:01:41Z [INFO] auto_login: Login dialog WID=12582936 detected at +11s
2026-06-24T14:01:41Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T14:01:43Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T14:01:43Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T14:01:45Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T14:01:45Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T14:01:45Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 14:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 11 / 16  (14:02:20) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     7m21s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:59:45Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T14:01:00Z [WARN] MetaTrader exited with code 143
2026-06-24T14:01:30Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T14:01:30Z [INFO] auto_login: hard-kill watchdog armed (pid=1418, fires at +270s)
2026-06-24T14:01:30Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T14:01:41Z [INFO] auto_login: Login dialog WID=12582936 detected at +11s
2026-06-24T14:01:41Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T14:01:43Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T14:01:43Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T14:01:45Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T14:01:45Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T14:01:45Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T14:01:47Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T14:01:47Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T14:01:47Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T14:01:49Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T14:01:49Z [INFO] auto_login: clipboard scrubbed

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 14:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 12 / 16  (14:02:59) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     7m59s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:59:45Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T14:01:00Z [WARN] MetaTrader exited with code 143
2026-06-24T14:01:30Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T14:01:30Z [INFO] auto_login: hard-kill watchdog armed (pid=1418, fires at +270s)
2026-06-24T14:01:30Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T14:01:41Z [INFO] auto_login: Login dialog WID=12582936 detected at +11s
2026-06-24T14:01:41Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T14:01:43Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T14:01:43Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T14:01:45Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T14:01:45Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T14:01:45Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T14:01:47Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T14:01:47Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T14:01:47Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T14:01:49Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T14:01:49Z [INFO] auto_login: clipboard scrubbed

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 14:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- capturing framebuffer (poll 12) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 13 / 16  (14:03:43) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     8m44s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:59:45Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T14:01:00Z [WARN] MetaTrader exited with code 143
2026-06-24T14:01:30Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T14:01:30Z [INFO] auto_login: hard-kill watchdog armed (pid=1418, fires at +270s)
2026-06-24T14:01:30Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T14:01:41Z [INFO] auto_login: Login dialog WID=12582936 detected at +11s
2026-06-24T14:01:41Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T14:01:43Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T14:01:43Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T14:01:45Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T14:01:45Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T14:01:45Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T14:01:47Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T14:01:47Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T14:01:47Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T14:01:49Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T14:01:49Z [INFO] auto_login: clipboard scrubbed

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 14:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 14 / 16  (14:04:21) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     9m23s

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:59:45Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T14:01:00Z [WARN] MetaTrader exited with code 143
2026-06-24T14:01:30Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T14:01:30Z [INFO] auto_login: hard-kill watchdog armed (pid=1418, fires at +270s)
2026-06-24T14:01:30Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T14:01:41Z [INFO] auto_login: Login dialog WID=12582936 detected at +11s
2026-06-24T14:01:41Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T14:01:43Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T14:01:43Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T14:01:45Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T14:01:45Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T14:01:45Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T14:01:47Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T14:01:47Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T14:01:47Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T14:01:49Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T14:01:49Z [INFO] auto_login: clipboard scrubbed

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 14:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 15 / 16  (14:05:02) ============
etradie-mt-2cd3d52c-747-0   2/3   Running   0     10m

--- driver log (auto_login + paste/type sentinels) ---
2026-06-24T13:56:51Z [INFO] auto_login: dismiss follow-up window: 'Welcome to LiveUpdate' (WID=12582941)
2026-06-24T13:59:45Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T14:01:00Z [WARN] MetaTrader exited with code 143
2026-06-24T14:01:30Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T14:01:30Z [INFO] auto_login: hard-kill watchdog armed (pid=1418, fires at +270s)
2026-06-24T14:01:30Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T14:01:41Z [INFO] auto_login: Login dialog WID=12582936 detected at +11s
2026-06-24T14:01:41Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T14:01:42Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T14:01:43Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T14:01:43Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T14:01:44Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T14:01:45Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T14:01:45Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T14:01:45Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T14:01:46Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T14:01:47Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T14:01:47Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T14:01:47Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T14:01:48Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T14:01:49Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T14:01:49Z [INFO] auto_login: clipboard scrubbed

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 14:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

============ poll 16 / 16  (14:05:41) ============
Error from server (NotFound): pods "etradie-mt-2cd3d52c-747-0" not found
POD GONE

============ FINAL ARTIFACTS ============
1 driver-log-full.txt
Error from server (NotFound): pods "etradie-mt-2cd3d52c-747-0" not found
mt5-journal.txt: 0 lines
Error from server (NotFound): pods "etradie-mt-2cd3d52c-747-0" not found
Error from server (NotFound): pods "etradie-mt-2cd3d52c-747-0" not found
OK: screen-poll-4.png
OK: screen-poll-8.png
OK: screen-poll-12.png
OK: screen-final.png

============ VERDICT ============
Error from server (NotFound): pods "etradie-mt-2cd3d52c-747-0" not found

--- accounts.dat (login completed?) ---
Error from server (NotFound): pods "etradie-mt-2cd3d52c-747-0" not found

--- MQL5/Logs (EA loaded?) ---
Error from server (NotFound): pods "etradie-mt-2cd3d52c-747-0" not found

--- :5555 socket ---
Error from server (NotFound): pods "etradie-mt-2cd3d52c-747-0" not found

--- MT5 journal (broker response is here) ---
Error from server (NotFound): pods "etradie-mt-2cd3d52c-747-0" not found

--- DB row ---
                  id                  | status |                                status_message                                | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+------------+-----------
 2cd3d52c-747c-433e-b869-54397f5cf95d | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout |            | t
(1 row)


============ DRIVER SENTINELS ============

--- fluxbox readiness ---

--- Welcome modal handling ---

--- Phase 2c (Login dialog open) ---

--- Phase 3 strategy + per-field outcome ---

--- Phase 3 stage transitions ---

--- Final outcome ---

============ FILES ============
-rw-r--r-- 1 softverse softverse  3674 Jun 24 09:11 /home/softverse/phase2c-diagnostics/after-10down.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 09:11 /home/softverse/phase2c-diagnostics/after-9down.png
-rw-r--r-- 1 softverse softverse 14204 Jun 24 09:52 /home/softverse/phase2c-diagnostics/after-altf-l.png
-rw-r--r-- 1 softverse softverse 13654 Jun 24 09:52 /home/softverse/phase2c-diagnostics/after-altf.png
-rw-r--r-- 1 softverse softverse 24872 Jun 24 08:57 /home/softverse/phase2c-diagnostics/driver-log-full-v2.txt
-rw-r--r-- 1 softverse softverse   110 Jun 24 15:05 /home/softverse/phase2c-diagnostics/driver-log-full.txt
-rw-r--r-- 1 softverse softverse  1292 Jun 24 08:57 /home/softverse/phase2c-diagnostics/mt5-journal-v2.txt
-rw-r--r-- 1 softverse softverse     0 Jun 24 15:05 /home/softverse/phase2c-diagnostics/mt5-journal.txt
-rw-r--r-- 1 softverse softverse 19633 Jun 24 08:52 /home/softverse/phase2c-diagnostics/pod-state.txt
-rw-r--r-- 1 softverse softverse  7397 Jun 24 09:00 /home/softverse/phase2c-diagnostics/screen-final-now.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 15:05 /home/softverse/phase2c-diagnostics/screen-final.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 08:57 /home/softverse/phase2c-diagnostics/screen-now.png
-rw-r--r-- 1 softverse softverse  3691 Jun 24 15:05 /home/softverse/phase2c-diagnostics/screen-poll-12.png
-rw-r--r-- 1 softverse softverse  3691 Jun 24 15:05 /home/softverse/phase2c-diagnostics/screen-poll-4.png
-rw-r--r-- 1 softverse softverse  3691 Jun 24 15:05 /home/softverse/phase2c-diagnostics/screen-poll-8.png
-rw-r--r-- 1 softverse softverse     0 Jun 24 15:05 /home/softverse/phase2c-diagnostics/windows-final.txt
-rw-r--r-- 1 softverse softverse    41 Jun 24 08:50 /home/softverse/phase2c-diagnostics/windows-poll-1.txt
-rw-r--r-- 1 softverse softverse    41 Jun 24 08:51 /home/softverse/phase2c-diagnostics/windows-poll-2.txt
-rw-r--r-- 1 softverse softverse  2374 Jun 24 08:52 /home/softverse/phase2c-diagnostics/xwininfo-final.txt

Open these screenshots to visually verify:
  explorer.exe ~/phase2c-diagnostics/screen-poll-4.png   (early - Login dialog)
  explorer.exe ~/phase2c-diagnostics/screen-poll-8.png   (mid-Phase-3)
  explorer.exe ~/phase2c-diagnostics/screen-final.png    (end state)
softverse@Softverse:~/phase2c-diagnostics$ 