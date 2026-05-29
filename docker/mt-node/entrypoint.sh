#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# etradie-mt-node entrypoint
#
# Launches a headless MetaTrader 4 or MetaTrader 5 terminal inside
# Wine with a virtual framebuffer (Xvfb). The Exoper ZeroMQ EA is
# pre-loaded so the engine can connect via tcp://<service>:5555.
#
# Environment contract
# --------------------
# Required (from the per-tenant Kubernetes Secret, envFrom in chart):
#   MT_LOGIN              Broker account login number
#   MT_PASSWORD           Broker trading password
# Optional per-tenant override (else falls back to DEFAULT_*):
#   MT_ZMQ_AUTH_TOKEN     EA AUTH_TOKEN; ZmqClient must match
# Required (from the chart env block):
#   MT_PLATFORM           "mt4" or "mt5"
#   MT_SERVER             Broker server (e.g. "Exness-MT5Trial9")
#   MT_SYMBOL             Default chart symbol (broker-correct name)
#   ZMQ_PORT              ZeroMQ REP port (default 5555)
# Required (from the platform Secret):
#   DEFAULT_ZMQ_AUTH_TOKEN  Fallback token when MT_ZMQ_AUTH_TOKEN unset
#
# Lifecycle
# ---------
#  1. Validate env.
#  2. Detect + auto-reset corrupted Wine prefix (boot-loop guard).
#  3. Start Xvfb on :99 and verify ready.
#  4. Copy EA binary into terminal's Experts/ folder.
#  5. Write the EA .set file with AUTH_TOKEN + ZMQ_PORT + MAGIC_NUMBER.
#  6. Render expert.tpl with the per-tenant symbol (NOT hardcoded).
#  7. Render startup.ini with auto-login creds + chart symbol.
#  8. Supervise MT in an in-pod restart loop. Up to MAX_INPOD_RESTARTS
#     consecutive failures within 5min => exit non-zero so the kubelet
#     restarts the whole Pod (the watchdog sidecar's livenessProbe
#     also enforces a cap on watchdog-level wedge).
# ──────────────────────────────────────────────────────────────────
set -euo pipefail

MAX_INPOD_RESTARTS="${MAX_INPOD_RESTARTS:-5}"
INPOD_RESTART_WINDOW_SECS="${INPOD_RESTART_WINDOW_SECS:-300}"

MT_PID=""
XVFB_PID=""

log() { printf '%s [%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$1" "$2" >&2; }

# ── Signal handling ─────────────────────────────────────────────
_shutdown() {
  log INFO "Caught shutdown signal, terminating MetaTrader + Xvfb"
  if [ -n "${MT_PID}" ] && kill -0 "${MT_PID}" 2>/dev/null; then
    kill -TERM "${MT_PID}" 2>/dev/null || true
    for _ in $(seq 1 100); do
      kill -0 "${MT_PID}" 2>/dev/null || break
      sleep 0.1
    done
    kill -KILL "${MT_PID}" 2>/dev/null || true
  fi
  if [ -n "${XVFB_PID}" ]; then
    kill -TERM "${XVFB_PID}" 2>/dev/null || true
  fi
  wineserver -k 2>/dev/null || true
  exit 0
}
trap _shutdown TERM INT

# ── Defaults ──────────────────────────────────────────────────────
MT_PLATFORM="${MT_PLATFORM:-mt5}"
MT_SYMBOL="${MT_SYMBOL:-EURUSD}"
ZMQ_PORT="${ZMQ_PORT:-5555}"
DISPLAY=":99"
export DISPLAY

# Choose per-tenant token first, else platform default.
EFFECTIVE_AUTH_TOKEN="${MT_ZMQ_AUTH_TOKEN:-${DEFAULT_ZMQ_AUTH_TOKEN:-}}"

# ── Validate required env ─────────────────────────────────────────
for var in MT_LOGIN MT_PASSWORD MT_SERVER MT_SYMBOL; do
  if [ -z "${!var:-}" ]; then
    log FATAL "$var is not set"
    exit 1
  fi
done
if [ -z "${EFFECTIVE_AUTH_TOKEN}" ]; then
  log FATAL "Neither MT_ZMQ_AUTH_TOKEN (per-tenant) nor DEFAULT_ZMQ_AUTH_TOKEN (platform) is set"
  exit 1
fi

# ── Paths ─────────────────────────────────────────────────────────
WINE_PREFIX="/home/mt/.wine"
export WINEPREFIX="$WINE_PREFIX"
export WINEDEBUG="-all"

if [ "$MT_PLATFORM" = "mt4" ]; then
  MT_DIR="$WINE_PREFIX/drive_c/Program Files (x86)/MetaTrader 4"
  MT_EXE="terminal.exe"
  EA_SRC="/opt/ea/ZeroMQ_EA.ex4"
  EA_REL_DST="MQL4/Experts/ZeroMQ_EA.ex4"
  SET_REL_DST="MQL4/Profiles/Templates/ZeroMQ_EA.set"
  TPL_REL_DST="templates/expert.tpl"
else
  MT_DIR="$WINE_PREFIX/drive_c/Program Files/MetaTrader 5"
  MT_EXE="terminal64.exe"
  EA_SRC="/opt/ea/ZeroMQ_EA.ex5"
  EA_REL_DST="MQL5/Experts/ZeroMQ_EA.ex5"
  SET_REL_DST="MQL5/Profiles/Templates/ZeroMQ_EA.set"
  TPL_REL_DST="Profiles/Templates/expert.tpl"
fi

# ── Wine prefix corruption auto-reset ─────────────────────────────
# A previous Pod kill mid-write can leave the prefix in an inconsistent
# state where wineserver refuses to start. Detect and reset.
if [ -d "$WINE_PREFIX" ]; then
  if [ ! -d "$WINE_PREFIX/drive_c/windows/system32" ] || \
     [ -f "$WINE_PREFIX/.update-timestamp.lock" ]; then
    log WARN "Wine prefix appears corrupted; resetting"
    rm -rf "$WINE_PREFIX"
  fi
fi
if [ ! -d "$WINE_PREFIX/drive_c/windows/system32" ]; then
  log INFO "Wine prefix missing; initialising"
  wineboot --init 2>/dev/null || true
  wineserver --wait 2>/dev/null || true
fi

# ── Start virtual framebuffer ─────────────────────────────────────
log INFO "Starting Xvfb on $DISPLAY"
Xvfb "$DISPLAY" -screen 0 1024x768x16 -nolisten tcp &
XVFB_PID=$!
for _ in $(seq 1 50); do
  if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then break; fi
  sleep 0.1
done
if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  log FATAL "Xvfb failed to start"
  exit 1
fi
log INFO "Xvfb ready"

# ── Materialise MT directory layout (idempotent) ─────────────────
mkdir -p "$MT_DIR/$(dirname "$EA_REL_DST")" \
         "$MT_DIR/$(dirname "$SET_REL_DST")" \
         "$MT_DIR/$(dirname "$TPL_REL_DST")" \
         "$MT_DIR/config"

# ── Copy EA binary ────────────────────────────────────────────────
if [ -f "$EA_SRC" ]; then
  cp -f "$EA_SRC" "$MT_DIR/$EA_REL_DST"
  log INFO "EA copied to $MT_DIR/$EA_REL_DST"
else
  log WARN "EA binary not found at $EA_SRC (continuing; user-supplied EA may already be in the Wine prefix)"
fi

# ── Write EA .set file (per-tenant AUTH_TOKEN + ZMQ_PORT) ────────
# MT4/5 reads the chart template's <expert>.name then loads inputs
# from the matching .set file. This injects the per-tenant token
# WITHOUT recompiling the EA source.
#
# Risk parameters (MAX_LOT_SIZE, MAX_TOTAL_EXPOSURE, MAX_DRAWDOWN_PCT)
# are intentionally absent. Risk enforcement is the exclusive
# responsibility of the platform's execution and management services.
# The EA is a wire-protocol adapter only.
cat > "$MT_DIR/$SET_REL_DST" <<EOF
ZMQ_PORT=${ZMQ_PORT}
RECV_TIMEOUT_MS=1000
SEND_TIMEOUT_MS=5000
AUTH_TOKEN=${EFFECTIVE_AUTH_TOKEN}
MAGIC_NUMBER=20260321
MAX_SLIPPAGE=10
TIMER_MS=50
ENABLE_DEBUG_LOG=false
LOG_COMMANDS=false
EOF
log INFO "EA .set written to $MT_DIR/$SET_REL_DST"

# ── Chart template (per-tenant symbol, NOT hardcoded EURUSD) ─────
cat > "$MT_DIR/$TPL_REL_DST" <<EOF
<chart>
symbol=${MT_SYMBOL}
period=16385
<expert>
name=ZeroMQ_EA
</expert>
</chart>
EOF
log INFO "Chart template written ($MT_SYMBOL)"

# ── Startup INI (auto-login + auto-attach chart) ─────────────────
INI_FILE="$MT_DIR/config/startup.ini"
cat > "$INI_FILE" <<EOF
[Common]
Login=${MT_LOGIN}
Password=${MT_PASSWORD}
Server=${MT_SERVER}
AutoConfiguration=true

[Charts]
Symbol=${MT_SYMBOL}
Period=H1
Template=expert

[Experts]
AllowLive=true
AllowDllImport=true
Enabled=true
Account=${MT_LOGIN}
Profile=default
EOF
log INFO "Startup config written to $INI_FILE"

# ── Supervised MT restart loop ───────────────────────────────────
restart_count=0
window_start=$(date +%s)

while :; do
  log INFO "Launching $MT_EXE (platform=$MT_PLATFORM, server=$MT_SERVER, login=$MT_LOGIN, symbol=$MT_SYMBOL, zmq_port=$ZMQ_PORT, restart_count=$restart_count)"

  cd "$MT_DIR"
  wine "$MT_EXE" "/config:$INI_FILE" &
  MT_PID=$!
  log INFO "MetaTrader PID: $MT_PID"

  set +e
  wait $MT_PID
  EXIT_CODE=$?
  set -e
  MT_PID=""

  log WARN "MetaTrader exited with code $EXIT_CODE"

  now=$(date +%s)
  elapsed=$(( now - window_start ))
  if [ "$elapsed" -ge "$INPOD_RESTART_WINDOW_SECS" ]; then
    restart_count=0
    window_start=$now
  fi

  restart_count=$(( restart_count + 1 ))

  if [ "$restart_count" -gt "$MAX_INPOD_RESTARTS" ]; then
    log ERROR "In-pod restart budget exhausted ($restart_count > $MAX_INPOD_RESTARTS within ${INPOD_RESTART_WINDOW_SECS}s). Exiting so the kubelet restarts the Pod."
    kill $XVFB_PID 2>/dev/null || true
    wineserver -k 2>/dev/null || true
    # Reap any wine helpers that survived wineserver -k so we do
    # not hand a half-cleaned PID namespace to the next Pod (the
    # containerd cleanup race relies on PID 1 exiting cleanly).
    pkill -9 -f terminal64.exe 2>/dev/null || true
    pkill -9 -f terminal.exe   2>/dev/null || true
    pkill -9 -f wineserver     2>/dev/null || true
    pkill -9 -f wineboot       2>/dev/null || true
    exit $EXIT_CODE
  fi

  log INFO "Sleeping 5s before in-pod restart (attempt $restart_count/$MAX_INPOD_RESTARTS in current ${INPOD_RESTART_WINDOW_SECS}s window)"
  sleep 5
  wineserver -k 2>/dev/null || true
  sleep 1
  # CHECKLIST Section 1: drain zombie wine processes. wineserver -k
  # only sends SIGTERM with a short grace window; helpers spawned by
  # MT (terminal64.exe / terminal.exe / wineboot) frequently survive
  # and collide with the next wine invocation on the wineprefix lock
  # at $WINEPREFIX/.update-timestamp.lock OR the wineserver socket
  # under $XDG_RUNTIME_DIR/wineserver-*. SIGKILL them explicitly.
  # `pkill -f <pat>` matches against the full command line; the
  # calling shell's command line is /bin/bash + entrypoint.sh and
  # does NOT match any of these patterns, so we cannot kill the
  # supervisor by accident. Verified against procps-ng pkill(1).
  pkill -9 -f terminal64.exe 2>/dev/null || true
  pkill -9 -f terminal.exe   2>/dev/null || true
  pkill -9 -f wineserver     2>/dev/null || true
  pkill -9 -f wineboot       2>/dev/null || true
  # Give the kernel 1s to fully reap the SIGKILLed PIDs before the
  # next wine invocation. Without this, MT5 occasionally races on
  # /tmp/.X99-lock and hangs at the splash screen.
  sleep 1
done
