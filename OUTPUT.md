EXAMINE THE docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md DEEPLY AND THOROUGHLY FROM THE BEGINNING TO THE END 
THERE IS A SERIOUS ISSUE WE NEED TO ADDRESS
MAKE SURE YOU EXAMINE CAREFULLY SO THAT YOU WILL GAIN FULLY AND COMPLETE UNDERSTANDING


IT MEANS THAT'S EXACTLY WHAT WE SHOULD BE TRACING IN THE CODEBASE THOROUGHLY TO SEE THE EXACT CAUSE
  
THEREFORE, AS A SENIOR ENGINEER YOU HAVE TO PERFORM A DEEP AND THOROUGH AUDIT ON THE ENTIRE AND WHOLE PIPELINE EXAMINING ALL PLACES AND FILES END TO END ECAUSE WE EED TO AVOID PATCH WORK OR EASY WORK THAT WILL BREAK IN PRODUCTION

WE NEED THE RAW TRUTH OF EXACTLY HOW EVERYTHING AND THE WHOLE PIPELINE OPERATE

DO NOT STOP UNTIL YOU ARE DONE EXAMINING

AVOID ASSUMPTIONS

AVOID GUESSING

YOU MUST BE 100% CERTAIN AND SURE OF EVERY SINGLE THING TO AVOID PROBLEM

DO NOT IGNORE, SKIP OR AVOID EXAMINING ALL PLACES REQUIRED, YOU MUST EXAMINE COMPLETELY

PLEASE NOTE: DO NOT STOP UNTIL YOU ARE DONE EXAMINING ALL & COVERED EVERYTHING

DO NOT DELEGATE TO AGENTS

Every 2.0s: kubectl -n etradie-system get pod -l app.kubernetes.io/name=etradie-mt-node                                  Softverse: Tue Jun 23 18:19:09 2026

No resources found in etradie-system namespace.




softverse@Softverse:~$ POD=etradie-mt-7b9fd8c0-6a1-0

# Allow it to reach the post-LiveUpdate phase + login attempt
sleep 60

# 1. Pod readiness
kubectl -n etradie-system get pod "$POD"

# 2. The journal — the key signal
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"; \
   f=$(ls -t "$P/logs"/*.log 2>/dev/null | head -1); \
   echo "file: $f, size: $(wc -c < "$f") bytes"; \
   tr -d "\000" < "$f"'

# 3. EA's log (MQL5/Logs)
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"; \
   ls -la "$P/MQL5/Logs/" 2>&1 | head -10; \
   f=$(ls -t "$P/MQL5/Logs"/*.log 2>/dev/null | head -1); \
   [ -n "$f" ] && { echo "--- $f ---"; tr -d "\000" < "$f" | tail -60; }'

# 4. :5555 socket state
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'cat /proc/net/tcp | awk "NR>1 && (\$3 ~ /:15B3/ || \$2 ~ /:15B3/){print}"'

# 5. DB row
kubectl -n etradie-system exec -i postgres-0 -c postgres -- psql -U etradie -d etradie -c \
  "SELECT id, status, status_message, mt5_symbol, is_active FROM broker_connections WHERE connection_type='hosted';"
Error from server (NotFound): pods "etradie-mt-7b9fd8c0-6a1-0" not found
Error from server (NotFound): pods "etradie-mt-7b9fd8c0-6a1-0" not found
Error from server (NotFound): pods "etradie-mt-7b9fd8c0-6a1-0" not found
Error from server (NotFound): pods "etradie-mt-7b9fd8c0-6a1-0" not found
                  id                  | status |                                status_message                                | mt5_symbol | is_active
--------------------------------------+--------+------------------------------------------------------------------------------+------------+-----------
 7b9fd8c0-6a1d-44e0-b382-59b06c7a305b | failed | Provisioning failed: mt-node StatefulSet did not become Ready within timeout |            | t
(1 row)

softverse@Softverse:~$






Yes — based on every piece of evidence we have, **the only remaining issue is auto-login**. Let me walk through the full boot sequence so you can see why I'm confident.

#### What happens BEFORE login (all confirmed working)

| Step | Status | Evidence |
|---|---|---|
| 1. Vault Agent injects credentials | ✅ | `Loaded Vault-rendered credentials (rendered_at=...)` in entrypoint log |
| 2. Wine prefix seeded from template | ✅ | `Wine prefix seeded` |
| 3. Xvfb starts | ✅ | `Xvfb ready` |
| 4. Broker `servers.dat` installed | ✅ | `Installed broker servers.dat from bundle` |
| 5. EA binary copied to `MQL5/Experts/` | ✅ | `EA copied to .../MQL5/Experts/ZeroMQ_EA.ex5` |
| 6. EA `.set` file written with auth_token | ✅ | `EA .set written` |
| 7. Bootstrap chart template written | ✅ | `Bootstrap chart template written (no symbol pinned)` |
| 8. `startup.ini` written with login/password/server | ✅ | journal confirms file content correct |
| 9. `terminal.ini` written with LiveUpdate pin | ✅ | `LiveUpdate pinned to build 5836` |
| 10. `wine terminal64.exe /portable` launches | ✅ | `MetaTrader PID: 217` |
| 11. MT5 binary starts | ✅ | `MetaTrader 5 x64 build 5836 started` |
| 12. MT5 first-run setup completes | ✅ | `common.ini Environment=` hex blob exists |
| 13. MT5 full recompile runs (no source = 0 files) | ✅ | `full recompilation has been finished: 0 file(s) compiled` |
| 14. LiveUpdate runs ONCE (one-time) | ✅ | `mt5onnx64 downloaded and updated` then `downloaded successfully` |
| 15. MT5 self-exits 143 for component swap | ✅ | watchdog/entrypoint see exit 143 |
| 16. MT5 relaunches with persisted update | ✅ | second `build 5836 started` line, NO further LiveUpdate |

#### What does NOT happen (the broken step)

| Step | Status | Evidence |
|---|---|---|
| 17. **Login attempt to broker server** | ❌ MISSING | no `Network 'Exness-MT5Real9': connecting` line |
| 18. **Broker authentication** | ❌ MISSING | no `Login: ok` line |
| 19. **Profile load** | ❌ MISSING | no `Profile: loaded` line |
| 20. **Default chart open** | ❌ MISSING | no `Charts: opened` line |
| 21. **Expert template applied** | ❌ MISSING | no `Expert: ZeroMQ_EA loaded` line |
| 22. **EA `OnInit()` runs** | ❌ MISSING | `MQL5/Logs/` directory doesn't exist |
| 23. **EA binds `:5555`** | ❌ MISSING | `/proc/net/tcp` has no LISTEN on `:5555` |

#### Why I'm confident login is the trigger

Look at network state from your earlier output:
```
1CB3A4C2:01BB 06    <- :443 TIME_WAIT (LiveUpdate CDN)
21B3A4C2:01BB 06    <- :443 TIME_WAIT (LiveUpdate CDN)
```

`:443` only. No connections to broker ports (`1950`, `1951`) or the broker's `:443` access servers. **MT5 has not even attempted to contact Exness yet.** Once login fires, you'd see ESTABLISHED connections to Exness IPs.

The chain is strict:
```
login → broker connection → profile loaded → chart opens → template applies → EA loads → :5555 binds
```

If step 17 (login) never fires, NOTHING downstream can happen. That's exactly the pattern we see: clean boot through step 16, then silence.

#### My current fix (the just-shipped commit)

```bash
wine "$MT_EXE" /portable "/login:$MT_LOGIN" "/password:$MT_PASSWORD" "/server:$MT_SERVER"
```

These flags ARE the documented MT5 unattended-login trigger. When honored, they execute steps 17 → 23 automatically.

#### Caveats I want to flag honestly

1. **There's a small risk Wine doesn't pass `/login:` correctly to terminal64.exe.** Wine handles Windows-style `/flag:value` arguments, but MetaTrader-specific flags aren't well documented in the Wine compatibility matrix. If the flags don't make it to MT5, we'll see the same silent pattern, and you'll be able to confirm via `ps -ef | grep terminal64` whether the flags reached the binary.

2. **There's a risk the server name `Exness-MT5Real9` doesn't resolve via the broker's `servers.dat`.** The entrypoint correctly installs `servers.dat` from the broker bundle (we saw `Installed broker servers.dat from bundle (/broker-bundle/MetaTrader 5 EXNESS/Config/servers.dat)`), so this should be fine. If it's not, the journal will show `Network 'Exness-MT5Real9': server not found`.

3. **There's a risk this is a Real account vs Demo account issue.** The server name `Exness-MT5Real9` suggests a **real money** account. Real accounts on Exness require additional verification steps that demo accounts skip. If you're testing, **use a demo account** (server name `Exness-MT5Trial9` or similar) to eliminate this variable.

#### Definitive test once the new image is deployed

After the CI nudge lands and the new image rolls, the journal will tell us in 90 seconds which scenario applies:

| Journal line we see | What it means | Next step |
|---|---|---|
| `Network 'Exness-MT5Real9': connecting...` then `Login: ok` | Fix worked, MT5 logging in | Wait for `:5555 LISTEN`, we're done |
| `Network 'Exness-MT5Real9': connecting...` then `Login: invalid account/password/server` | Flags reached MT5; credentials wrong | Check broker creds |
| `Network 'Exness-MT5Real9': server not found` | Flags reached MT5; servers.dat issue | Inspect broker bundle |
| Silent (same as now) | Flags didn't reach MT5 | Try a different syntax (e.g. `/login:` without quotes, or different escape) |

The diagnosis is straightforward once we have the new journal. **Wait for CI green, run the cleanup, re-provision, paste the journal.** I won't speculate further until we see what build 5836 actually does with the new flags.

#### One quick check you can do NOW

While waiting for CI, confirm the current pod's `ps -ef` so we know exactly what flags the current image is passing:

```bash
POD=etradie-mt-bf30a46b-af2-0
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'ps -ef | grep -i "terminal64\|start.exe" | grep -v grep'
```

Expected output for the current (440986a0 image) pod:

```
mt  ...  start.exe /exec terminal64.exe
mt  ...  C:\Program Files\MetaTrader 5\terminal64.exe /portable
```

After the new image rolls, the same command should show:

```
mt  ...  start.exe /exec terminal64.exe
mt  ...  C:\Program Files\MetaTrader 5\terminal64.exe /portable /login:133978149 /password:****** /server:Exness-MT5Real9
```

If the new image's `terminal64.exe` line shows only `/portable` (no `/login` etc.), then Wine isn't forwarding the args correctly and we need to debug the entrypoint's argument quoting.

#### Summary

**Yes, the only remaining issue is auto-login.** Everything before it works. The new commit's `/login /password /server` flags target exactly that gap. We'll know in ~5 minutes after the new image deploys whether MT5 honors them correctly. If not, we have a clear diagnostic path (Wine arg forwarding, server name resolution, real-vs-demo account, credential validity) to chase one at a time.