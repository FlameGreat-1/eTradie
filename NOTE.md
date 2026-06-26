EXAMINE EVERYTHING THOROUGHLY FROM THE START TO THE END :


ALL THE PNG IMAGES SHOWED THE SAME SCREEN EXCEPT THE FIRST PAGE:


File View
Tools
Help
~
Market Watch
X
IDE (())
Algo Trading
New Order
Symbol
Bid
Ask
Daily Ch...
XAUUSDM
3333.667
3334.638
0.21%
BTCUSDm
115786.40
115923.04
-1.37%
EURUSDM
1.16680
1.16689
-0.32%
USDJPYM
14
Select a company to open an account with
ETHUSDM
43
XAUUSD
333
Symbols
Details
Trading
Navigator
add new company like "CompanyName' or address 'company.com
Find your company
Exness
Accounts
Exness Technologies Ltd
A Indicators
Expert Advisors
Scripts
Services
Exness
Market
Common
Favorites
Time
2026.06.26 08:08:35.233
2026.06.26 08:08:35.263
2026.06.26 08:08:35.263
2026.06.26 08:09:35.462
2026.06.26 08:09:36.563
2026.06.26 08:09:36.565
Too
Next >
Cancel
1Gb memory, 67/192 Gb...
News
Mailbox
Calendar
Alerts |
Articles |
Code Base
Experts
Journal
0000.00.00 00:00
0:000.000
H: 000.000
L: 000.000
C: 000.000
V: 00000
Market (1) Signals VPS Tester
0/0 Kb
For Help, press F1


SO IT'S VERY LIKE THAT AFTER SELECTING THE COMPANY IT DID NOT CLICK THE "Next".
BUT THIS WAS WORKING BEFORE, HOW COME IT IS NOT WORKING AGAIN?

CLICKING Next > IS EXACTLY HOW IT WORKS MANUALLY WHEN I AM USING MT5

ONCE YOU CLICK Next > IT OPENS THE Login dialog 

SO IT'S USUALLY SELECT Exness Technologies Ltd  THEN CLICK Next >   AND THEN Login dialog OPENS


EXAMINE EVERYTHING THOROUGHLY FROM THE BEGINNING TO THE END:


echo "Discovered MT_DIR: '$MT_DIR'"
echo "$MT_DIR" > mt-dir.txt
echo "DONE. Diagnostic dir: $DIAG_DIR"_DIR ==="────────────────────────ee attempts failed' driver-log-full.txt | tail -10 -20l getwindowname "$w" 2>/dev/nul
=== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 08:08:06
=== STAGE 7: race to the pod ===
Release: etradie-mt-d16ae820-6a1
POD=etradie-mt-d16ae820-6a1-0
[1] mt-node state: {"running":{"startedAt":"2026-06-26T08:08:04Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:f2581eb5fe9f7c70062368c718b851d4db045125
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:f2581eb5fe9f7c70062368c718b851d4db045125
=== STAGE 8: broker-bundle initContainer log ===
Downloading https://pub-5bdcacdedad6458298e8b8d5435f301a.r2.dev/broker-bundles/exness-portable.zip...
/broker-bundle/bundle.zip: OK
Bundle extracted successfully.
Expect: 'Downloading ...exness-portable.zip', 'eadee9c7... OK', 'Bundle extracted successfully.'
=== STAGE 8b: discover MT_DIR (branded root) + MT_CONFIG_DIR ===
Discovered MT_DIR: ''
FATAL: could not discover branded MT root (terminal*.exe not found).
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
--- Profiles/Charts (MUST be absent or empty) ---
ls: cannot access '/Profiles/Charts': No such file or directory
ls: cannot access '/MQL5/Profiles/Charts': No such file or directory
--- common.ini (MUST be absent until MT5 recreates it) ---
ls: cannot access '/common.ini': No such file or directory
--- stray lowercase config dir (MUST be absent on Deriv after de-dup) ---
ls: cannot access '/config': No such file or directory
--- expert.tpl co-located with the .set (BOTH MUST exist) ---
ls: cannot access '/MQL5/Profiles/Templates/expert.tpl': No such file or directory
ls: cannot access '/MQL5/Profiles/Templates/ZeroMQ_EA.set': No such file or directory
--- expert.tpl legacy mirror ---
ls: cannot access '/Profiles/Templates/expert.tpl': No such file or directory
--- our startup.ini in the resolved config dir ---
ls: cannot access '/startup.ini': No such file or directory
--- servers.dat present (broker server list) ---
ls: cannot access '/servers.dat': No such file or directory
command terminated with exit code 2
=== STAGE 11: poll loop ===

===== poll 1/16  08:08:32 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     45s
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
3148907 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 2/16  08:09:20 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     94s
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  08:10:05 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     2m19s
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T08:09:37Z [INFO] auto_login: LiveUpdate modal active (WID=12582937); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  08:10:50 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     3m4s
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T08:09:37Z [INFO] auto_login: LiveUpdate modal active (WID=12582937); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T08:10:33Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  08:11:35 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     3m49s
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T08:09:37Z [INFO] auto_login: LiveUpdate modal active (WID=12582937); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T08:10:33Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  08:12:27 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     4m41s
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T08:09:37Z [INFO] auto_login: LiveUpdate modal active (WID=12582937); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T08:10:33Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  08:13:15 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     5m29s
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T08:09:37Z [INFO] auto_login: LiveUpdate modal active (WID=12582937); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T08:10:33Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 8/16  08:14:02 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     6m16s
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T08:09:37Z [INFO] auto_login: LiveUpdate modal active (WID=12582937); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T08:10:33Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  08:14:46 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     7m
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T08:09:37Z [INFO] auto_login: LiveUpdate modal active (WID=12582937); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T08:10:33Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  08:15:34 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     7m48s
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T08:09:37Z [INFO] auto_login: LiveUpdate modal active (WID=12582937); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T08:10:33Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  08:16:18 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     8m32s
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T08:09:37Z [INFO] auto_login: LiveUpdate modal active (WID=12582937); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T08:10:33Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 12/16  08:17:12 =====
etradie-mt-d16ae820-6a1-0   2/3   Running   0     9m27s
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T08:09:37Z [INFO] auto_login: LiveUpdate modal active (WID=12582937); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T08:10:33Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
2026-06-26T08:16:37Z [WARN] MetaTrader exited with code 143
2026-06-26T08:17:07Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:17:07Z [INFO] auto_login: hard-kill watchdog armed (pid=2280, fires at +450s)
2026-06-26T08:17:07Z [INFO] auto_login: terminal process detected at +0s
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 13/16  08:17:58 =====
etradie-mt-d16ae820-6a1-0   2/3   Terminating   0     10m
--- driver log (auto_login / deterministic / phase5 / overlay) ---
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace
2026-06-26T08:08:31Z [INFO] overlay-normalize: canonical config dir resolved to '/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5 EXNESS/Config'
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked common.ini (foreign account [Common] Login/Server/Environment + ProfileLast/PreloadCharts; MT5 recreates it after first login)
2026-06-26T08:08:31Z [INFO] overlay-normalize(mt5): removing baked accounts.dat (foreign account; MT5 recreates after auto-login)
2026-06-26T08:08:32Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:08:32Z [INFO] auto_login: hard-kill watchdog armed (pid=338, fires at +450s)
2026-06-26T08:08:32Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T08:09:37Z [INFO] auto_login: LiveUpdate modal active (WID=12582937); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T08:10:33Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
2026-06-26T08:16:37Z [WARN] MetaTrader exited with code 143
2026-06-26T08:17:07Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T08:17:07Z [INFO] auto_login: hard-kill watchdog armed (pid=2280, fires at +450s)
2026-06-26T08:17:07Z [INFO] auto_login: terminal process detected at +0s
--- :5555 LISTEN state (0A) ---
--- EA Experts log (chart+EA attach + bind banner) ---
(no MQL5/Logs yet)
--- accounts.dat (recreated after first login?) ---
ls: cannot access '/accounts.dat': No such file or directory
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 14/16  08:18:49 =====
Error from server (NotFound): pods "etradie-mt-d16ae820-6a1-0" not found
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
=== STAGE 13: verdict ===
Error from server (NotFound): pods "etradie-mt-d16ae820-6a1-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-d16ae820-6a1-0" not found
--- journal head/tail (broker handshake) ---
Error from server (NotFound): pods "etradie-mt-d16ae820-6a1-0" not found
...
Error from server (NotFound): pods "etradie-mt-d16ae820-6a1-0" not found
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 d16ae820-6a1b-446f-9614-fc5f9646e9df | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260626T075903Z ===
total 22388
