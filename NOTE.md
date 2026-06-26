=== STAGE 6: RE-PROVISION FROM DASHBOARD NOW (Exness, Exness-MT5Real9, login 133978149) ===
Press Enter the SECOND you click submit:
Submit (UTC): 17:15:25
=== STAGE 7: race to the pod ===
Release: etradie-mt-70932632-eb3
POD=etradie-mt-70932632-eb3-0
[1] mt-node state: {"waiting":{"reason":"PodInitializing"}}
[2] mt-node state: {"running":{"startedAt":"2026-06-26T17:15:28Z"}}
ghcr.io/flamegreat-1/etradie/mt-node:d83a13678936700d5a91a13f6de2883cc4717f8e
Expect image: ghcr.io/flamegreat-1/etradie/mt-node:d83a13678936700d5a91a13f6de2883cc4717f8e
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

===== poll 1/16  17:15:56 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     44s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 2/16  17:16:43 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     90s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:16:03Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T17:16:03Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T17:16:03Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T17:16:03Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T17:16:05Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T17:16:05Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T17:16:06Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T17:16:08Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T17:16:08Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T17:16:08Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T17:16:11Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T17:16:11Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T17:16:11Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T17:16:13Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T17:16:13Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T17:16:14Z [INFO] auto_login: wizard-handler: main window resolved by PID (WID=12582913; WM_NAME empty during init -- title search could not match)
2026-06-26T17:16:14Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:16:14Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:16:14Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (562,360) [main win 1016x734+4+30]
2026-06-26T17:16:18Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:16:18Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:16:19Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (562,360) [main win 1016x734+4+30]
2026-06-26T17:16:22Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:16:22Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:16:23Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:16:26Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:16:26Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:16:28Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:16:28Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:16:28Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:16:28Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:16:29Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:16:32Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:16:32Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:16:32Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:16:36Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:16:36Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:16:36Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:16:40Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:16:40Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:16:42Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:16:42Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:16:42Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:16:42Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:16:42Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 3/16  17:17:27 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     2m15s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:16:42Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:16:42Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:16:46Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:16:46Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:16:46Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:16:49Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:16:49Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:16:50Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:16:53Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:16:53Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:16:55Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:16:55Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:16:55Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:16:56Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:16:56Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:16:59Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:16:59Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:00Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:03Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:03Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:04Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:07Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:07Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:09Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:09Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:10Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:10Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:10Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:14Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:14Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:14Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:18Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:18Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:18Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:21Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:21Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:23Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T17:17:23Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T17:17:26Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:26Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:30Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:30Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 4/16  17:18:14 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     3m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:17:18Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:21Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:21Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:23Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T17:17:23Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T17:17:26Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:26Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:30Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:30Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:31Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:34Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:34Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:34Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:38Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:38Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:44Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:44Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:44Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:48Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:48Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:52Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:52Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:54Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:58Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:58Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:58Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:02Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:18:02Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:18:02Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:06Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:18:06Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:18:08Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 5/16  17:19:00 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     3m47s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:17:18Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:21Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:21Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:23Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T17:17:23Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T17:17:26Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:26Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:30Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:30Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:31Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:34Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:34Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:34Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:38Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:38Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:44Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:44Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:44Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:48Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:48Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:52Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:52Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:54Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:58Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:58Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:58Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:02Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:18:02Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:18:02Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:06Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:18:06Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:18:08Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 6/16  17:19:53 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     4m40s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:17:18Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:21Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:21Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:23Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T17:17:23Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T17:17:26Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:26Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:30Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:30Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:31Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:34Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:34Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:34Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:38Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:38Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:44Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:44Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:44Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:48Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:48Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:52Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:52Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:54Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:58Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:58Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:58Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:02Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:18:02Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:18:02Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:06Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:18:06Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:18:08Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 7/16  17:20:44 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     5m32s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:17:18Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:21Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:21Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:23Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T17:17:23Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T17:17:26Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:26Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:30Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:30Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:31Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:34Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:34Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:34Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:38Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:38Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:44Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:44Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:44Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:48Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:48Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:52Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:52Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:54Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:58Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:58Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:58Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:02Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:18:02Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:18:02Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:06Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:18:06Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:18:08Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 8/16  17:21:37 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     6m24s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:17:18Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:21Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:21Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:23Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T17:17:23Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T17:17:26Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:26Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:30Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:30Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:31Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:34Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:34Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:34Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:38Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:38Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:44Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:44Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:44Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:48Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:48Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:52Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:52Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:54Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:58Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:58Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:58Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:02Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:18:02Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:18:02Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:06Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:18:06Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:18:08Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 9/16  17:22:21 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     7m9s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:17:18Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:21Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:21Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:23Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T17:17:23Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T17:17:26Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:26Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:30Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:30Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:31Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:34Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:34Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:34Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:38Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:38Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:44Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:44Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:44Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:48Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:48Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:52Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:52Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:54Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:58Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:58Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:58Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:02Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:18:02Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:18:02Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:06Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:18:06Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:18:08Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 10/16  17:23:09 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     7m56s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:17:18Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:21Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:21Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:23Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T17:17:23Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T17:17:26Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:26Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:30Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:30Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:31Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:34Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:34Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:34Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:38Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:38Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:44Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:44Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:44Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:48Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:48Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:52Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:52Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:54Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:58Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:58Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:58Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:02Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:18:02Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:18:02Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:06Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:18:06Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:18:08Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 11/16  17:23:55 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     8m42s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:17:18Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:21Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:21Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:23Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T17:17:23Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T17:17:26Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:26Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:30Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:30Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:31Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:34Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:34Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:34Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:38Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:38Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:44Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:44Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:44Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:48Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:48Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:52Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:52Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:54Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:58Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:58Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:58Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:02Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:18:02Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:18:02Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:06Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:18:06Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:18:08Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 12/16  17:24:39 =====
etradie-mt-70932632-eb3-0   2/3   Running   0     9m27s
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:17:21Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:21Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:23Z [INFO] auto_login: liveupdate-handler: active WID=12582946 name='Welcome to LiveUpdate'
2026-06-26T17:17:23Z [INFO] auto_login: LiveUpdate modal active (WID=12582946); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)
2026-06-26T17:17:26Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:26Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:26Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:27Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:30Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:30Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:31Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:34Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:34Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:34Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:38Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:38Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:40Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:40Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:40Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:44Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:44Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:44Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:48Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:17:48Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:48Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:52Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:17:52Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:17:54Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:17:54Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:54Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:17:58Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:17:58Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:17:58Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:02Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:18:02Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:18:02Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:18:06Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:18:06Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:18:08Z [ERROR] auto_login: Login dialog never appeared within 120s and :5555 not bound; exiting
2026-06-26T17:24:15Z [WARN] MetaTrader exited with code 143
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names


===== poll 13/16  17:25:23 =====
etradie-mt-70932632-eb3-0   2/3   Terminating   0     10m
--- driver log (auto_login / wizard / deterministic / phase5 / overlay) ---
2026-06-26T17:24:45Z [INFO] auto_login: terminal process detected at +0s
2026-06-26T17:24:45Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T17:24:45Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T17:24:45Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T17:24:47Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T17:24:47Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T17:24:48Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T17:24:50Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T17:24:50Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T17:24:50Z [INFO] auto_login: wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer
2026-06-26T17:24:52Z [INFO] auto_login: liveupdate-handler: no active window (skip)
2026-06-26T17:24:53Z [INFO] auto_login: wizard-handler: active WID= name=''
2026-06-26T17:24:53Z [INFO] auto_login: wizard-handler: main window resolved by PID (WID=12582913; WM_NAME empty during init -- title search could not match)
2026-06-26T17:24:53Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:24:53Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:24:54Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (562,360) [main win 1016x734+4+30]
2026-06-26T17:24:57Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:24:57Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:24:58Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:25:01Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:25:01Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:25:02Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:25:05Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:25:05Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:25:07Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:25:07Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:25:08Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:25:08Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:25:08Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:25:12Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:25:12Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:25:12Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:25:15Z [WARN] auto_login: account wizard still not advanced after attempt 2; retrying focus + Alt+N
2026-06-26T17:25:15Z [INFO] auto_login: account wizard advance (attempt 3): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:25:16Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:25:19Z [WARN] auto_login: account wizard still not advanced after attempt 3; retrying focus + Alt+N
2026-06-26T17:25:19Z [WARN] auto_login: account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration
2026-06-26T17:25:21Z [INFO] auto_login: liveupdate-handler: active WID=12582936 name=''
2026-06-26T17:25:21Z [INFO] auto_login: wizard-handler: active WID=12582936 name=''
2026-06-26T17:25:21Z [INFO] auto_login: Open-an-Account wizard handler engaged via main MT5 window (WID=12582913); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)
2026-06-26T17:25:21Z [INFO] auto_login: account wizard advance (attempt 1): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:25:22Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
2026-06-26T17:25:25Z [WARN] auto_login: account wizard still not advanced after attempt 1; retrying focus + Alt+N
2026-06-26T17:25:25Z [INFO] auto_login: account wizard advance (attempt 2): focusing embedded wizard then Alt+N (operator-verified)
2026-06-26T17:25:26Z [INFO] auto_login: account wizard: focusing embedded wizard pane by click at (563,345) [main win 1024x768+0+0]
--- :5555 LISTEN state (0A) ---
1573739 /tmp/screen.xwd
tar: Removing leading `/' from member names

===== poll 14/16  17:26:09 =====
Error from server (NotFound): pods "etradie-mt-70932632-eb3-0" not found
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
Error from server (NotFound): pods "etradie-mt-70932632-eb3-0" not found
--- :5555 LISTEN (the goal) ---
Error from server (NotFound): pods "etradie-mt-70932632-eb3-0" not found
--- journal head/tail (broker handshake) ---
(MT_DIR empty; journal/EA log not collected)
...
(MT_DIR empty; journal/EA log not collected)
--- DB row ---
                  id                  | status |                                status_message                                | broker_id |    broker_entity_id     | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+-----------+-------------------------+------------+-----------
 70932632-eb39-4a62-a467-54a0430e8e27 | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout | exness    | exness_technologies_ltd |            | t
(1 row)

=== STAGE 14: driver sentinels ===
--- overlay normalizer ---
--- Open-an-Account wizard (NEW: select-company + Alt+N + verify) ---
--- deterministic attach decision (evidence-based) ---
--- chart+EA presence gating ---
--- phase5 fallback (should be RARE / skipped) ---
--- final outcome ---
=== STAGE 15: artifacts in /home/softverse/hostedmt-diagnostics/20260626T170850Z ===
total 20872
drwxr-xr-x  2 softverse softverse    4096 Jun 26 18:26 .
drwxr-xr-x 16 softverse softverse    4096 Jun 26 18:08 ..
-rw-r--r--  1 softverse softverse     110 Jun 26 18:26 broker-bundle-init.log
-rw-r--r--  1 softverse softverse     110 Jun 26 18:26 driver-log-full.txt
-rw-r--r--  1 softverse softverse      45 Jun 26 18:26 ea-log.txt
-rw-r--r--  1 softverse softverse      92 Jun 26 18:09 engine-env.txt
-rw-r--r--  1 softverse softverse       1 Jun 26 18:15 mt-config-dir.txt
-rw-r--r--  1 softverse softverse       1 Jun 26 18:15 mt-dir.txt
-rw-r--r--  1 softverse softverse      45 Jun 26 18:26 mt5-journal.txt
-rw-r--r--  1 softverse softverse      71 Jun 26 18:15 on-disk-asserts.txt
-rw-r--r--  1 softverse softverse       0 Jun 26 18:15 overlay-normalize.log
-rw-r--r--  1 softverse softverse      41 Jun 26 18:08 pinned-sha.txt
-rw-r--r--  1 softverse softverse      58 Jun 26 18:15 release.txt
-rw-r--r--  1 softverse softverse     278 Jun 26 18:26 screen-poll-01.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:16 screen-poll-01.xwd
-rw-r--r--  1 softverse softverse   65220 Jun 26 18:26 screen-poll-02.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:16 screen-poll-02.xwd
-rw-r--r--  1 softverse softverse   69521 Jun 26 18:26 screen-poll-03.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:17 screen-poll-03.xwd
-rw-r--r--  1 softverse softverse   69521 Jun 26 18:26 screen-poll-04.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:18 screen-poll-04.xwd
-rw-r--r--  1 softverse softverse   69521 Jun 26 18:26 screen-poll-05.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:19 screen-poll-05.xwd
-rw-r--r--  1 softverse softverse   69540 Jun 26 18:26 screen-poll-06.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:20 screen-poll-06.xwd
-rw-r--r--  1 softverse softverse   69540 Jun 26 18:26 screen-poll-07.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:21 screen-poll-07.xwd
-rw-r--r--  1 softverse softverse   69540 Jun 26 18:26 screen-poll-08.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:21 screen-poll-08.xwd
-rw-r--r--  1 softverse softverse   69521 Jun 26 18:26 screen-poll-09.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:22 screen-poll-09.xwd
-rw-r--r--  1 softverse softverse   69521 Jun 26 18:26 screen-poll-10.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:23 screen-poll-10.xwd
-rw-r--r--  1 softverse softverse   69521 Jun 26 18:26 screen-poll-11.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:24 screen-poll-11.xwd
-rw-r--r--  1 softverse softverse     278 Jun 26 18:26 screen-poll-12.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:24 screen-poll-12.xwd
-rw-r--r--  1 softverse softverse   62069 Jun 26 18:26 screen-poll-13.png
-rw-r--r--  1 softverse softverse 1573739 Jun 26 18:25 screen-poll-13.xwd
-rw-r--r--  1 softverse softverse      23 Jun 26 18:15 submit-timestamp.txt
-rw-r--r--  1 softverse softverse      73 Jun 26 18:26 windows-final.txt
-rw-r--r--  1 softverse softverse       0 Jun 26 18:16 windows-poll-01.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 18:16 windows-poll-02.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 18:17 windows-poll-03.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 18:18 windows-poll-04.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 18:19 windows-poll-05.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 18:20 windows-poll-06.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 18:21 windows-poll-07.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 18:21 windows-poll-08.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 18:22 windows-poll-09.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 18:23 windows-poll-10.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 18:24 windows-poll-11.txt
-rw-r--r--  1 softverse softverse      31 Jun 26 18:24 windows-poll-12.txt
-rw-r--r--  1 softverse softverse      48 Jun 26 18:25 windows-poll-13.txt
DONE. Diagnostic dir: /home/softverse/hostedmt-diagnostics/20260626T170850Z
softverse@Softverse:~/hostedmt-diagnostics/20260626T170850Z$
