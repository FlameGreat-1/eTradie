
================================================================
RE-PROVISION FROM DASHBOARD NOW.
Press Enter the SECOND you click submit.
================================================================

Release: etradie-mt-89660d92-9e3
POD=etradie-mt-89660d92-9e3-0
[1] mt-node state: {"waiting":{"reason":"PodInitializing"}}
[2] mt-node state: {"waiting":{"reason":"PodInitializing"}}
[3] mt-node state: {"running":{"startedAt":"2026-06-24T17:00:34Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:cd7334257958a5e3d4a0464e6cef5344b385a73e

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

============ poll 1 / 16  (17:00:57) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     41s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

============ poll 2 / 16  (17:01:37) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     81s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:01:05Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T17:01:05Z [INFO] fluxbox ready (pid=228); _NET_ACTIVE_WINDOW available
2026-06-24T17:01:06Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T17:01:06Z [INFO] auto_login: hard-kill watchdog armed (pid=281, fires at +270s)
2026-06-24T17:01:06Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T17:01:37Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T17:01:37Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T17:01:37Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T17:01:38Z [INFO] auto_login: main window is active; modals cleared

--- :5555 socket state ---

--- accounts.dat presence ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat': No such file or directory

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- capturing framebuffer + windows (poll 2) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 3 / 16  (17:02:27) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     2m11s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:01:05Z [INFO] Starting fluxbox window manager (config=/tmp/.fluxbox)
2026-06-24T17:01:05Z [INFO] fluxbox ready (pid=228); _NET_ACTIVE_WINDOW available
2026-06-24T17:01:06Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T17:01:06Z [INFO] auto_login: hard-kill watchdog armed (pid=281, fires at +270s)
2026-06-24T17:01:06Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T17:01:37Z [INFO] auto_login: main UI window WID=12582913 detected at +31s; entering Phase 2c (3-attempt menu invocation)
2026-06-24T17:01:37Z [INFO] auto_login: Phase 2c attempt 1: File menu mnemonic (main WID=12582913, Alt+F then L)
2026-06-24T17:01:37Z [INFO] auto_login: blocking modal detected (WID=12582936, NAME=); attempting dismiss
2026-06-24T17:01:38Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:01:39Z [INFO] auto_login: Login dialog WID=12582938 appeared after mnemonic at +33s
2026-06-24T17:01:39Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582938 name=Login
2026-06-24T17:01:40Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T17:01:41Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T17:01:41Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T17:01:42Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T17:01:42Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T17:01:42Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T17:01:44Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T17:01:44Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T17:01:44Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T17:01:46Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T17:01:46Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T17:01:48Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T17:01:48Z [INFO] auto_login: clipboard scrubbed
2026-06-24T17:01:48Z [INFO] auto_login: phase5: settling 25s for post-login modal + Market Watch population
2026-06-24T17:02:13Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-24T17:02:13Z [INFO] auto_login: blocking modal detected (WID=12582941, NAME=Welcome to LiveUpdate); attempting dismiss
2026-06-24T17:02:14Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:02:14Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 17:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- capturing framebuffer + windows (poll 3) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 4 / 16  (17:03:19) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     3m3s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:01:40Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582938 name=Login
2026-06-24T17:01:41Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582938 name=Login
2026-06-24T17:01:41Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T17:01:42Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T17:01:42Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T17:01:42Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T17:01:44Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T17:01:44Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T17:01:44Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T17:01:46Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T17:01:46Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T17:01:48Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T17:01:48Z [INFO] auto_login: clipboard scrubbed
2026-06-24T17:01:48Z [INFO] auto_login: phase5: settling 25s for post-login modal + Market Watch population
2026-06-24T17:02:13Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-24T17:02:13Z [INFO] auto_login: blocking modal detected (WID=12582941, NAME=Welcome to LiveUpdate); attempting dismiss
2026-06-24T17:02:14Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:02:14Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-24T17:02:37Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-24T17:02:42Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-24T17:02:42Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:02:43Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-24T17:03:07Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-24T17:03:13Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-24T17:03:16Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 17:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- capturing framebuffer + windows (poll 4) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 5 / 16  (17:04:08) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     3m53s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:01:42Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T17:01:42Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T17:01:42Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T17:01:44Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T17:01:44Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T17:01:44Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T17:01:46Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T17:01:46Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T17:01:48Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T17:01:48Z [INFO] auto_login: clipboard scrubbed
2026-06-24T17:01:48Z [INFO] auto_login: phase5: settling 25s for post-login modal + Market Watch population
2026-06-24T17:02:13Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-24T17:02:13Z [INFO] auto_login: blocking modal detected (WID=12582941, NAME=Welcome to LiveUpdate); attempting dismiss
2026-06-24T17:02:14Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:02:14Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-24T17:02:37Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-24T17:02:42Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-24T17:02:42Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:02:43Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-24T17:03:07Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-24T17:03:13Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-24T17:03:16Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-24T17:03:38Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-24T17:03:39Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-24T17:03:39Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 17:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- capturing framebuffer + windows (poll 5) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 6 / 16  (17:04:58) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     4m42s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:01:42Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T17:01:42Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T17:01:42Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T17:01:44Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T17:01:44Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T17:01:44Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T17:01:46Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T17:01:46Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T17:01:48Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T17:01:48Z [INFO] auto_login: clipboard scrubbed
2026-06-24T17:01:48Z [INFO] auto_login: phase5: settling 25s for post-login modal + Market Watch population
2026-06-24T17:02:13Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-24T17:02:13Z [INFO] auto_login: blocking modal detected (WID=12582941, NAME=Welcome to LiveUpdate); attempting dismiss
2026-06-24T17:02:14Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:02:14Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-24T17:02:37Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-24T17:02:42Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-24T17:02:42Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:02:43Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-24T17:03:07Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-24T17:03:13Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-24T17:03:16Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-24T17:03:38Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-24T17:03:39Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-24T17:03:39Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 17:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- capturing framebuffer + windows (poll 6) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 7 / 16  (17:05:54) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     5m38s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:01:42Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T17:01:42Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T17:01:44Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T17:01:44Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T17:01:44Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T17:01:46Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T17:01:46Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T17:01:48Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T17:01:48Z [INFO] auto_login: clipboard scrubbed
2026-06-24T17:01:48Z [INFO] auto_login: phase5: settling 25s for post-login modal + Market Watch population
2026-06-24T17:02:13Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-24T17:02:13Z [INFO] auto_login: blocking modal detected (WID=12582941, NAME=Welcome to LiveUpdate); attempting dismiss
2026-06-24T17:02:14Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:02:14Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-24T17:02:37Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-24T17:02:42Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-24T17:02:42Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:02:43Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-24T17:03:07Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-24T17:03:13Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-24T17:03:16Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-24T17:03:38Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-24T17:03:39Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-24T17:03:39Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-24T17:05:06Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 17:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

============ poll 8 / 16  (17:06:33) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     6m16s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:01:42Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582938 name=Login
2026-06-24T17:01:43Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T17:01:44Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T17:01:44Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T17:01:44Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582938 name=Login
2026-06-24T17:01:45Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T17:01:46Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T17:01:46Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582938 name=Login
2026-06-24T17:01:46Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582938 name=Login
2026-06-24T17:01:47Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T17:01:48Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T17:01:48Z [INFO] auto_login: clipboard scrubbed
2026-06-24T17:01:48Z [INFO] auto_login: phase5: settling 25s for post-login modal + Market Watch population
2026-06-24T17:02:13Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): clearing modals + activating main window
2026-06-24T17:02:13Z [INFO] auto_login: blocking modal detected (WID=12582941, NAME=Welcome to LiveUpdate); attempting dismiss
2026-06-24T17:02:14Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:02:14Z [INFO] auto_login: phase5: attempt 1 (Ctrl+M default action): dispatching keystroke sequence [ctrl+m Tab Home Return]
2026-06-24T17:02:37Z [WARN] auto_login: phase5: attempt 1 (Ctrl+M default action): no chart window appeared within 20s
2026-06-24T17:02:42Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): clearing modals + activating main window
2026-06-24T17:02:42Z [INFO] auto_login: main window is active; modals cleared
2026-06-24T17:02:43Z [INFO] auto_login: phase5: attempt 2 (Ctrl+M context menu): dispatching keystroke sequence [ctrl+m Tab Home Menu Down Return]
2026-06-24T17:03:07Z [WARN] auto_login: phase5: attempt 2 (Ctrl+M context menu): no chart window appeared within 20s
2026-06-24T17:03:13Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): clearing modals + activating main window
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-24T17:03:16Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-24T17:03:38Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-24T17:03:39Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-24T17:03:39Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-24T17:05:06Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T17:06:17Z [WARN] MetaTrader exited with code 143

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 17:01 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- capturing framebuffer + windows (poll 8) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 9 / 16  (17:07:23) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     7m7s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-24T17:03:16Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-24T17:03:38Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-24T17:03:39Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-24T17:03:39Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-24T17:05:06Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T17:06:17Z [WARN] MetaTrader exited with code 143
2026-06-24T17:06:47Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T17:06:47Z [INFO] auto_login: hard-kill watchdog armed (pid=1965, fires at +270s)
2026-06-24T17:06:47Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T17:06:56Z [INFO] auto_login: Login dialog WID=12582936 detected at +9s
2026-06-24T17:06:56Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T17:06:58Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T17:06:58Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T17:06:58Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T17:06:59Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T17:06:59Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T17:07:00Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T17:07:00Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T17:07:00Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T17:07:01Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T17:07:01Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T17:07:02Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T17:07:02Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T17:07:02Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T17:07:04Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T17:07:04Z [INFO] auto_login: clipboard scrubbed
2026-06-24T17:07:04Z [WARN] auto_login: phase5: no main window WID provided; cannot drive menu navigation
2026-06-24T17:07:04Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 17:07 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

============ poll 10 / 16  (17:08:02) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     7m46s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-24T17:03:16Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-24T17:03:38Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-24T17:03:39Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-24T17:03:39Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-24T17:05:06Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T17:06:17Z [WARN] MetaTrader exited with code 143
2026-06-24T17:06:47Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T17:06:47Z [INFO] auto_login: hard-kill watchdog armed (pid=1965, fires at +270s)
2026-06-24T17:06:47Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T17:06:56Z [INFO] auto_login: Login dialog WID=12582936 detected at +9s
2026-06-24T17:06:56Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T17:06:58Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T17:06:58Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T17:06:58Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T17:06:59Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T17:06:59Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T17:07:00Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T17:07:00Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T17:07:00Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T17:07:01Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T17:07:01Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T17:07:02Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T17:07:02Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T17:07:02Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T17:07:04Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T17:07:04Z [INFO] auto_login: clipboard scrubbed
2026-06-24T17:07:04Z [WARN] auto_login: phase5: no main window WID provided; cannot drive menu navigation
2026-06-24T17:07:04Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 17:07 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- capturing framebuffer + windows (poll 10) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 11 / 16  (17:08:48) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     8m33s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-24T17:03:16Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-24T17:03:38Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-24T17:03:39Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-24T17:03:39Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-24T17:05:06Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T17:06:17Z [WARN] MetaTrader exited with code 143
2026-06-24T17:06:47Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T17:06:47Z [INFO] auto_login: hard-kill watchdog armed (pid=1965, fires at +270s)
2026-06-24T17:06:47Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T17:06:56Z [INFO] auto_login: Login dialog WID=12582936 detected at +9s
2026-06-24T17:06:56Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T17:06:58Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T17:06:58Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T17:06:58Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T17:06:59Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T17:06:59Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T17:07:00Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T17:07:00Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T17:07:00Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T17:07:01Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T17:07:01Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T17:07:02Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T17:07:02Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T17:07:02Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T17:07:04Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T17:07:04Z [INFO] auto_login: clipboard scrubbed
2026-06-24T17:07:04Z [WARN] auto_login: phase5: no main window WID provided; cannot drive menu navigation
2026-06-24T17:07:04Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 17:07 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

============ poll 12 / 16  (17:09:29) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     9m12s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-24T17:03:16Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-24T17:03:38Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-24T17:03:39Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-24T17:03:39Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-24T17:05:06Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T17:06:17Z [WARN] MetaTrader exited with code 143
2026-06-24T17:06:47Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T17:06:47Z [INFO] auto_login: hard-kill watchdog armed (pid=1965, fires at +270s)
2026-06-24T17:06:47Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T17:06:56Z [INFO] auto_login: Login dialog WID=12582936 detected at +9s
2026-06-24T17:06:56Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T17:06:58Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T17:06:58Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T17:06:58Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T17:06:59Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T17:06:59Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T17:07:00Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T17:07:00Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T17:07:00Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T17:07:01Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T17:07:01Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T17:07:02Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T17:07:02Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T17:07:02Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T17:07:04Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T17:07:04Z [INFO] auto_login: clipboard scrubbed
2026-06-24T17:07:04Z [WARN] auto_login: phase5: no main window WID provided; cannot drive menu navigation
2026-06-24T17:07:04Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 17:07 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

--- capturing framebuffer + windows (poll 12) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

============ poll 13 / 16  (17:10:14) ============
etradie-mt-89660d92-9e3-0   2/3   Running   0     9m58s

--- driver log (auto_login + paste/type + Phase 5 sentinels) ---
2026-06-24T17:03:13Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:14Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [INFO] auto_login: blocking modal detected (WID=18874369, NAME=logs); attempting dismiss
2026-06-24T17:03:15Z [WARN] auto_login: modal still active after Escape/Return cascade (WID=18874369, NAME=logs); unmapping
2026-06-24T17:03:16Z [INFO] auto_login: phase5: attempt 3 (Alt+F File menu): dispatching keystroke sequence [alt+f Right Right Return]
2026-06-24T17:03:38Z [WARN] auto_login: phase5: attempt 3 (Alt+F File menu): no chart window appeared within 20s
2026-06-24T17:03:39Z [ERROR] auto_login: phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget
2026-06-24T17:03:39Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget
2026-06-24T17:05:06Z [ERROR] auto_login: :5555 never bound within 240s total budget; exiting
2026-06-24T17:06:17Z [WARN] MetaTrader exited with code 143
2026-06-24T17:06:47Z [INFO] auto_login: start (budget=240s, login=133978149, server=Exness-MT5Real9)
2026-06-24T17:06:47Z [INFO] auto_login: hard-kill watchdog armed (pid=1965, fires at +270s)
2026-06-24T17:06:47Z [INFO] auto_login: terminal process detected at +0s
2026-06-24T17:06:56Z [INFO] auto_login: Login dialog WID=12582936 detected at +9s
2026-06-24T17:06:56Z [INFO] auto_login: phase3 stage=pre_activate focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: phase3 stage=post_activate focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: phase3 stage=after_tab_1 focused_wid=12582936 name=Login
2026-06-24T17:06:57Z [INFO] auto_login: deliver login: paste-then-type strategy; paste attempt
2026-06-24T17:06:58Z [INFO] auto_login: paste login: ok (length=9, content not logged)
2026-06-24T17:06:58Z [INFO] auto_login: deliver login: paste succeeded
2026-06-24T17:06:58Z [INFO] auto_login: phase3 stage=after_login_deliver focused_wid=12582936 name=Login
2026-06-24T17:06:59Z [INFO] auto_login: phase3 stage=after_tab_2 focused_wid=12582936 name=Login
2026-06-24T17:06:59Z [INFO] auto_login: deliver password: paste-then-type strategy; paste attempt
2026-06-24T17:07:00Z [INFO] auto_login: paste password: ok (length=13, content not logged)
2026-06-24T17:07:00Z [INFO] auto_login: deliver password: paste succeeded
2026-06-24T17:07:00Z [INFO] auto_login: phase3 stage=after_pwd_deliver focused_wid=12582936 name=Login
2026-06-24T17:07:01Z [INFO] auto_login: phase3 stage=after_tab_3 focused_wid=12582936 name=Login
2026-06-24T17:07:01Z [INFO] auto_login: deliver server: paste-then-type strategy; paste attempt
2026-06-24T17:07:02Z [INFO] auto_login: paste server: ok (length=15, content not logged)
2026-06-24T17:07:02Z [INFO] auto_login: deliver server: paste succeeded
2026-06-24T17:07:02Z [INFO] auto_login: phase3 stage=after_server_deliver focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=after_tab_4 focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=after_space focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: phase3 stage=pre_submit focused_wid=12582936 name=Login
2026-06-24T17:07:03Z [INFO] auto_login: credentials delivered and submitted (server=Exness-MT5Real9, save-account=on, strategy=paste_then_type)
2026-06-24T17:07:04Z [INFO] auto_login: phase3 stage=post_submit_1s focused_wid=12582913 name=133978149 -   - Netting
2026-06-24T17:07:04Z [INFO] auto_login: clipboard scrubbed
2026-06-24T17:07:04Z [WARN] auto_login: phase5: no main window WID provided; cannot drive menu navigation
2026-06-24T17:07:04Z [INFO] auto_login: phase5: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget

--- :5555 socket state ---

--- accounts.dat presence ---
-rw-r--r-- 1 mt mt 4635 Jun 24 17:07 /home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/config/accounts.dat

--- MQL5/Logs (EA OnInit ran?) ---
ls: cannot access '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5/MQL5/Logs/': No such file or directory

============ poll 14 / 16  (17:10:54) ============
Error from server (NotFound): pods "etradie-mt-89660d92-9e3-0" not found
POD GONE

============ FINAL ARTIFACTS ============
1 driver-log-full.txt
Error from server (NotFound): pods "etradie-mt-89660d92-9e3-0" not found
mt5-journal.txt: 0 lines
Error from server (NotFound): pods "etradie-mt-89660d92-9e3-0" not found
ea-log.txt: 0 lines (>0 means EA OnInit ran)
Error from server (NotFound): pods "etradie-mt-89660d92-9e3-0" not found
Error from server (NotFound): pods "etradie-mt-89660d92-9e3-0" not found
OK: screen-poll-2.png
OK: screen-poll-3.png
OK: screen-poll-4.png
OK: screen-poll-5.png
OK: screen-poll-6.png
OK: screen-poll-8.png
OK: screen-poll-10.png
OK: screen-poll-12.png
OK: screen-final.png

============ VERDICT ============
Error from server (NotFound): pods "etradie-mt-89660d92-9e3-0" not found

--- accounts.dat (login completed?) ---
Error from server (NotFound): pods "etradie-mt-89660d92-9e3-0" not found

--- MQL5/Logs (EA loaded?) ---
Error from server (NotFound): pods "etradie-mt-89660d92-9e3-0" not found

--- :5555 socket ---
Error from server (NotFound): pods "etradie-mt-89660d92-9e3-0" not found

--- MT5 journal (broker response is here) ---
Error from server (NotFound): pods "etradie-mt-89660d92-9e3-0" not found

--- DB row ---
                  id                  | status |                                status_message                                | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+------------+-----------
 89660d92-9e35-42c3-8d89-a3d93fc87846 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout |            | t
(1 row)


============ DRIVER SENTINELS ============

--- fluxbox readiness ---

--- Welcome modal handling ---

--- Phase 2a precedence guard (subsequent-boot health) ---

--- Phase 2c (Login dialog open) ---

--- Phase 3 strategy + per-field outcome ---

--- Phase 3 stage transitions ---

--- Phase 5 chart-attach (Ctrl+M Market Watch cascade) ---

--- Phase 5 attempt outcomes ---

--- Final outcome ---

============ FILES ============
-rw-r--r-- 1 softverse softverse  3674 Jun 24 09:11 /home/softverse/phase2c-diagnostics/after-10down.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 09:11 /home/softverse/phase2c-diagnostics/after-9down.png
-rw-r--r-- 1 softverse softverse 14204 Jun 24 09:52 /home/softverse/phase2c-diagnostics/after-altf-l.png
-rw-r--r-- 1 softverse softverse 13654 Jun 24 09:52 /home/softverse/phase2c-diagnostics/after-altf.png
-rw-r--r-- 1 softverse softverse 24872 Jun 24 08:57 /home/softverse/phase2c-diagnostics/driver-log-full-v2.txt
-rw-r--r-- 1 softverse softverse   110 Jun 24 18:10 /home/softverse/phase2c-diagnostics/driver-log-full.txt
-rw-r--r-- 1 softverse softverse     0 Jun 24 18:10 /home/softverse/phase2c-diagnostics/ea-log.txt
-rw-r--r-- 1 softverse softverse  1292 Jun 24 08:57 /home/softverse/phase2c-diagnostics/mt5-journal-v2.txt
-rw-r--r-- 1 softverse softverse     0 Jun 24 18:10 /home/softverse/phase2c-diagnostics/mt5-journal.txt
-rw-r--r-- 1 softverse softverse 19633 Jun 24 08:52 /home/softverse/phase2c-diagnostics/pod-state.txt
-rw-r--r-- 1 softverse softverse  7397 Jun 24 09:00 /home/softverse/phase2c-diagnostics/screen-final-now.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 18:11 /home/softverse/phase2c-diagnostics/screen-final.png
-rw-r--r-- 1 softverse softverse  7397 Jun 24 08:57 /home/softverse/phase2c-diagnostics/screen-now.png
-rw-r--r-- 1 softverse softverse  3691 Jun 24 18:11 /home/softverse/phase2c-diagnostics/screen-poll-10.png
-rw-r--r-- 1 softverse softverse  3691 Jun 24 18:11 /home/softverse/phase2c-diagnostics/screen-poll-12.png
-rw-r--r-- 1 softverse softverse 13956 Jun 24 18:11 /home/softverse/phase2c-diagnostics/screen-poll-2.png
-rw-r--r-- 1 softverse softverse  3745 Jun 24 18:11 /home/softverse/phase2c-diagnostics/screen-poll-3.png
-rw-r--r-- 1 softverse softverse  3691 Jun 24 18:11 /home/softverse/phase2c-diagnostics/screen-poll-4.png
-rw-r--r-- 1 softverse softverse  3691 Jun 24 18:11 /home/softverse/phase2c-diagnostics/screen-poll-5.png
-rw-r--r-- 1 softverse softverse  3691 Jun 24 18:11 /home/softverse/phase2c-diagnostics/screen-poll-6.png
-rw-r--r-- 1 softverse softverse   278 Jun 24 18:11 /home/softverse/phase2c-diagnostics/screen-poll-8.png
-rw-r--r-- 1 softverse softverse     0 Jun 24 18:10 /home/softverse/phase2c-diagnostics/windows-final.txt
-rw-r--r-- 1 softverse softverse    41 Jun 24 08:50 /home/softverse/phase2c-diagnostics/windows-poll-1.txt
-rw-r--r-- 1 softverse softverse    42 Jun 24 18:08 /home/softverse/phase2c-diagnostics/windows-poll-10.txt
-rw-r--r-- 1 softverse softverse    42 Jun 24 18:09 /home/softverse/phase2c-diagnostics/windows-poll-12.txt
-rw-r--r-- 1 softverse softverse    42 Jun 24 18:01 /home/softverse/phase2c-diagnostics/windows-poll-2.txt
-rw-r--r-- 1 softverse softverse    65 Jun 24 18:02 /home/softverse/phase2c-diagnostics/windows-poll-3.txt
-rw-r--r-- 1 softverse softverse    42 Jun 24 18:03 /home/softverse/phase2c-diagnostics/windows-poll-4.txt
-rw-r--r-- 1 softverse softverse    42 Jun 24 18:04 /home/softverse/phase2c-diagnostics/windows-poll-5.txt
-rw-r--r-- 1 softverse softverse    42 Jun 24 18:05 /home/softverse/phase2c-diagnostics/windows-poll-6.txt
-rw-r--r-- 1 softverse softverse    31 Jun 24 18:06 /home/softverse/phase2c-diagnostics/windows-poll-8.txt
-rw-r--r-- 1 softverse softverse  2374 Jun 24 08:52 /home/softverse/phase2c-diagnostics/xwininfo-final.txt

Open these screenshots to visually verify each Phase 5 stage:
  explorer.exe ~/phase2c-diagnostics/screen-poll-2.png    (Phase 2c menu navigation)
  explorer.exe ~/phase2c-diagnostics/screen-poll-3.png    (Phase 3 paste mid-flight)
  explorer.exe ~/phase2c-diagnostics/screen-poll-4.png    (Phase 5 settle starting)
  explorer.exe ~/phase2c-diagnostics/screen-poll-5.png    (Phase 5 Ctrl+M Market Watch)
  explorer.exe ~/phase2c-diagnostics/screen-poll-6.png    (Phase 5 chart open or attempt 2)
  explorer.exe ~/phase2c-diagnostics/screen-poll-8.png    (Phase 5 mid/end or Phase 4)
  explorer.exe ~/phase2c-diagnostics/screen-poll-10.png   (Phase 4 polling)
  explorer.exe ~/phase2c-diagnostics/screen-poll-12.png   (Ready or pre-teardown)
  explorer.exe ~/phase2c-diagnostics/screen-poll-16.png   (final state)
  explorer.exe ~/phase2c-diagnostics/screen-final.png     (end-of-run snapshot)

Window-tree snapshots for cross-correlation with screenshots:
  cat ~/phase2c-diagnostics/windows-poll-{2,3,4,5,6,8,10,12,16}.txt
softverse@Softverse:~/phase2c-diagnostics$