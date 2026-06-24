Let me read this carefully. Three observations:

#### ✅ Confirmed: new image rolled correctly

- `terminal64.exe /portable` (NO credential flags) — confirmed via `ps -ef`
- Image SHA matches the new pin `f1c3d78fa734d8494011bb7e63a90b89a4419278`
- Driver started at `01:09:50Z`, detected terminal process at `+0s`

#### ⚠️ The driver is missing log lines

We should be seeing one of these by now:
- `auto_login: Login dialog WID=... detected at +Ns` (success path)
- `auto_login: :5555 LISTEN at +Ns (no dialog needed; accounts.dat path)` (fast path)
- `auto_login: Login dialog never appeared within 120s...` (timeout)

But the driver log is stuck at `terminal process detected at +0s` — nothing since.

Three possibilities, in order of likelihood:

1. **The driver is polling in Phase 2 right now and just hasn't logged the "dialog detected" line yet** — between `+0s` (terminal detected at 01:09:50) and `01:11:45` we're at +115s into Phase 2's 120s dialog-wait budget. The driver only logs when it DETECTS a dialog, not while it's polling. If MT5 hasn't shown the dialog yet (LiveUpdate just completed at 01:10:54, MT5 has only had ~50s post-LiveUpdate to render UI), the driver could still be polling normally.

2. **MT5 hasn't shown a Login dialog yet on this boot** — after exit-143, MT5 relaunches. The post-LiveUpdate relaunch typically takes 30-60s before any UI is shown. We're currently right at the boundary.

3. **`xdotool search` not matching the window name** — if MT5's dialog has a title we didn't anticipate, the regex `^(Login|Open an Account|Login to Trade Account|Authorization)` won't match.

#### Let me get more diagnostics RIGHT NOW while the pod is still alive

Run this immediately — it'll show us what xdotool sees on the Xvfb display, the full driver log without filtering, and any post-LiveUpdate relaunch in the journal:

```bash
POD=etradie-mt-04514ddd-310-0

echo "=== ALL driver log entries (unfiltered) ==="
kubectl -n etradie-system logs "$POD" -c mt-node --tail=500 | grep -iE 'auto_login|MetaTrader|drv|xdotool'

echo ""
echo "=== Full unfiltered last 50 lines of entrypoint log ==="
kubectl -n etradie-system logs "$POD" -c mt-node --tail=50

echo ""
echo "=== Windows visible on Xvfb right now ==="
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xdotool search --onlyvisible --name ".+" 2>&1 | while read wid; do echo "WID=$wid name=$(DISPLAY=:99 xdotool getwindowname "$wid" 2>/dev/null)"; done'

echo ""
echo "=== All windows on Xvfb (including invisible) via xwininfo ==="
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'DISPLAY=:99 xwininfo -root -children 2>&1 | head -60'

echo ""
echo "=== Is xdotool actually available in the image? ==="
kubectl -n etradie-system exec "$POD" -c mt-node -- which xdotool

echo ""
echo "=== Full MT5 journal (look for second 'build 5836 started' line) ==="
kubectl -n etradie-system exec "$POD" -c mt-node -- sh -c \
  'P="/home/mt/.wine/prefix/drive_c/Program Files/MetaTrader 5"; \
   f=$(ls -t "$P/logs"/*.log 2>/dev/null | head -1); \
   [ -n "$f" ] && tr -d "\000" < "$f"'
```

Paste that output. The window list is the critical signal — if MT5 is showing a dialog with an unexpected title, we'll see it there and can adjust the regex. If there's NO visible window at all, MT5 is still in cold-boot phase and the driver is correctly waiting.








