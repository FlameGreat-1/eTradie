────────────────ee attempts failed' driver-log-full.txt | tail -10 -20ll present' driver-log-full.txt
=== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 18:43:01
=== STAGE 7: race to the pod ===
Release: etradie-mt-10246cb0-213
POD=etradie-mt-10246cb0-213-0
[1] mt-node state: {"running":{"startedAt":"2026-06-26T18:43:00Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:b939755a74c3a8a4c27fefa2dc552f2667c750b7
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:b939755a74c3a8a4c27fefa2dc552f2667c750b7
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

===== poll 1/16  18:43:30 =====
etradie-mt-10246cb0-213-0   2/3   Running   0     47s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 2/16  18:44:26 =====
etradie-mt-10246cb0-213-0   2/3   Running   0     103s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T18:43:35Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T18:43:35Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T18:43:35Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T18:43:35Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T18:43:37Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T18:43:37Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T18:43:38Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T18:43:40Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T18:43:40Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T18:43:40Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T18:43:43Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T18:43:43Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T18:43:43Z [INFO] auto_login: wizard-handler: main window resolved by PID (WID=12582913; WM_NAME empty during init -- title search could not match)
2026-06-26T18:43:43Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:43:43Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:43:44Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (562,360) [main win 1016x734+4+30]
2026-06-26T18:43:49Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:43:49Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:43:49Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:43:54Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:43:54Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:43:55Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:00Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:44:00Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:44:02Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:44:02Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:02Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:02Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:02Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:07Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:44:07Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:07Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:12Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:44:12Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:13Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:17Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:44:17Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:44:19Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:44:19Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:20Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:20Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:20Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:25Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:44:25Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:25Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  18:45:14 =====
etradie-mt-10246cb0-213-0   2/3   Running   0     2m31s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T18:44:19Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:20Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:20Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:20Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:25Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:44:25Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:25Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:30Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:44:30Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:30Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:35Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:44:35Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:44:37Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:44:37Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:37Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:37Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:38Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:43Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:44:43Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:43Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:48Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:44:48Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:53Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:44:53Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:44:55Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T18:44:55Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T18:44:58Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:58Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:59Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:04Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:04Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:04Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:09Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:09Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:09Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:14Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:14Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:16Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:16Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:17Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  18:46:01 =====
etradie-mt-10246cb0-213-0   2/3   Running   0     3m19s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T18:44:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:53Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:44:53Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:44:55Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T18:44:55Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T18:44:58Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:58Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:59Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:04Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:04Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:04Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:09Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:09Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:09Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:14Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:14Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:16Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:16Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:17Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:22Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:22Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:22Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:27Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:27Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:32Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:32Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:34Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:34Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:35Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:40Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:40Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:45Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:45Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:45Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:50Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:50Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:52Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  18:46:48 =====
etradie-mt-10246cb0-213-0   2/3   Running   0     4m3s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T18:44:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:53Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:44:53Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:44:55Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T18:44:55Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T18:44:58Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:58Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:59Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:04Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:04Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:04Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:09Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:09Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:09Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:14Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:14Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:16Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:16Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:17Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:22Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:22Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:22Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:27Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:27Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:32Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:32Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:34Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:34Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:35Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:40Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:40Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:45Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:45Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:45Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:50Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:50Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:52Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  18:47:37 =====
etradie-mt-10246cb0-213-0   2/3   Running   0     4m53s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T18:44:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:53Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:44:53Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:44:55Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T18:44:55Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T18:44:58Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:58Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:59Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:04Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:04Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:04Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:09Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:09Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:09Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:14Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:14Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:16Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:16Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:17Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:22Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:22Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:22Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:27Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:27Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:32Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:32Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:34Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:34Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:35Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:40Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:40Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:45Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:45Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:45Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:50Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:50Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:52Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  18:48:28 =====
etradie-mt-10246cb0-213-0   2/3   Running   0     5m45s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T18:44:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:53Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:44:53Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:44:55Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T18:44:55Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T18:44:58Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:58Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:59Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:04Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:04Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:04Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:09Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:09Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:09Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:14Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:14Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:16Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:16Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:17Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:22Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:22Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:22Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:27Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:27Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:32Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:32Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:34Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:34Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:35Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:40Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:40Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:45Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:45Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:45Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:50Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:50Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:52Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 8/16  18:49:17 =====
etradie-mt-10246cb0-213-0   2/3   Running   0     6m34s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T18:44:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:53Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:44:53Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:44:55Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T18:44:55Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T18:44:58Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:58Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:59Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:04Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:04Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:04Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:09Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:09Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:09Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:14Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:14Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:16Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:16Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:17Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:22Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:22Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:22Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:27Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:27Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:32Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:32Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:34Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:34Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:35Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:40Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:40Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:45Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:45Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:45Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:50Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:50Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:52Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  18:50:26 =====
etradie-mt-10246cb0-213-0   2/3   Running   0     7m44s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T18:44:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:44:53Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:44:53Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:44:55Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T18:44:55Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T18:44:58Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:58Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:59Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:04Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:04Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:04Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:09Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:09Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:09Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:14Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:14Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:16Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:16Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:17Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:22Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:22Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:22Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:27Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:27Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:32Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:32Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:34Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:34Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:35Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:40Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:40Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:45Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:45Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:45Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:50Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:50Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:52Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  18:51:51 =====
etradie-mt-10246cb0-213-0   2/3   Running   0     9m8s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T18:44:53Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:44:53Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:44:55Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T18:44:55Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T18:44:58Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:44:58Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:44:58Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:44:59Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:04Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:04Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:04Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:09Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:09Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:09Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:14Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:14Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:16Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:16Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:16Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:17Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:22Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:22Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:22Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:27Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:27Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:32Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:32Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:34Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:45:34Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:45:34Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:35Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:40Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:45:40Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:45Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:45:45Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:45Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:50Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:50Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:52Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
2026-06-26T18:51:47Z [WARN] MetaTrader exited with code 143
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  18:52:56 =====
etradie-mt-10246cb0-213-0   2/3   Terminating   0     10m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T18:45:45Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:45:45Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:45:50Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:45:50Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:45:52Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
2026-06-26T18:51:47Z [WARN] MetaTrader exited with code 143
2026-06-26T18:52:17Z [INFO] auto_login: start (budget=420s, login=133978149, server=Exness-MT5Real9)
2026-06-26T18:52:17Z [INFO] auto_login: hard-kill watchdog armed (pid=2381, fires at +450s)
2026-06-26T18:52:17Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T18:52:17Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T18:52:17Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T18:52:17Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T18:52:19Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T18:52:19Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T18:52:19Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T18:52:22Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T18:52:22Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T18:52:22Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T18:52:24Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T18:52:24Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T18:52:25Z [INFO] auto_login: wizard-handler: main window resolved by PID (WID=12582913; WM_NAME empty during init -- title search could not match)
2026-06-26T18:52:25Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:52:25Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:52:25Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (562,360) [main win 1016x734+4+30]
2026-06-26T18:52:31Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:52:31Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:52:31Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:52:36Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:52:36Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:52:36Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:52:41Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:52:41Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T18:52:43Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T18:52:43Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T18:52:43Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T18:52:43Z [INFO] auto_login: account wizard advance (attempt 1): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:52:44Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:52:48Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T18:52:48Z [INFO] auto_login: account wizard advance (attempt 2): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:52:49Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:52:54Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T18:52:54Z [INFO] auto_login: account wizard advance (attempt 3): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback
2026-06-26T18:52:54Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T18:52:59Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T18:52:59Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 12/16  18:54:14 =====
Error from server (NotFound): pods "etradie-mt-10246cb0-213-0" not found
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
=== STAGE 13: verdict ===
Error from server (NotFound): pods "etradie-mt-10246cb0-213-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-10246cb0-213-0" not found
--- journal head/tail (broker handshake) ---
(MT_DIR empty; journal/EA log not collected)
...
(MT_DIR empty; journal/EA log not collected)
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 10246cb0-2133-40c3-a13d-adee2d634bb3 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260626T183909Z ===
total 17652
drwxr-xr-x  2 softverse softverse    4096 Jun 26 19:54 .
drwxr-xr-x 17 softverse softverse    4096 Jun 26 19:39 ..
-rw-r--r--  1 softverse softverse     110 Jun 26 19:54 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 26 19:54 driver-log-full.txt
-rw-r--r--  1 softverse softverse      45 Jun 26 19:54 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 26 19:41 engine-env.txt
-rw-r--r--  1 softverse softverse       1 Jun 26 19:43 mt-config-dir.txt
-rw-r--r--  1 softverse softverse       1 Jun 26 19:43 mt-dir.txt
-rw-r--r--  1 softverse softverse      45 Jun 26 19:54 mt5-journal.txt
-rw-r--r--  1 softverse softverse      71 Jun 26 19:43 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse       0 Jun 26 19:43 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 26 19:39 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 26 19:43 release.txt
-rw-r--r--  1 softverse softverse     278 Jun 26 19:54 screen-poll-01.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 19:43 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   63672 Jun 26 19:54 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 19:44 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse   67175 Jun 26 19:54 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 19:45 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse   67196 Jun 26 19:54 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 19:46 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   67196 Jun 26 19:54 screen-poll-05.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 19:47 screen-poll-05.xwd
-rw-r--r--  1 softverse softverse   67175 Jun 26 19:54 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 19:47 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   67196 Jun 26 19:54 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 19:48 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse   67175 Jun 26 19:54 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 19:49 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse   67175 Jun 26 19:54 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 19:51 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse     278 Jun 26 19:54 screen-poll-10.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 19:52 screen-poll-10.xwd
-rw-r--r--  1 softverse softverse   62929 Jun 26 19:54 screen-poll-11.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 19:53 screen-poll-11.xwd
-rw-r--r--  1 softverse softverse      23 Jun 26 19:43 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 26 19:54 windows-final.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 19:43 windows-poll-01.txt
-rw-r--r--  1 softverse softverse      88 Jun 26 19:44 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 19:45 windows-poll-03.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 19:46 windows-poll-04.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 19:47 windows-poll-05.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 19:47 windows-poll-06.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 19:48 windows-poll-07.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 19:49 windows-poll-08.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 19:51 windows-poll-09.txt
-rw-r--r--  1 softverse softverse      31 Jun 26 19:52 windows-poll-10.txt
-rw-r--r--  1 softverse softverse      73 Jun 26 19:53 windows-poll-11.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260626T183909Z
softverse@Softverse:~/hostedmt-diagnostics/20260626T183909Z$