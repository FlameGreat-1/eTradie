#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# etradie-mt-node entrypoint
#
# Launches a headless MetaTrader 4 or MetaTrader 5 terminal inside
# Wine with a virtual framebuffer (Xvfb).  The Exoper ZeroMQ EA is
# pre-loaded so the Engine can connect via tcp://<container>:5555.
#
# Required environment variables (injected by the Engine at runtime):
#   MT_PLATFORM   - "mt4" or "mt5"
#   MT_LOGIN      - Broker account login
#   MT_PASSWORD   - Broker trading password
#   MT_SERVER     - Broker server name (e.g. "Exness-MT5Trial9")
#   ZMQ_PORT      - ZeroMQ REP port (default 5555)
#
# The script is designed to be resilient:
#   - Xvfb is started first and verified before Wine launches.
#   - Wine prefix is pre-initialized to avoid first-run GUI popups.
#   - The terminal is monitored; if it crashes, the container exits
#     so Docker's restart policy can reboot it instantly.
# ──────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Signal handling ─────────────────────────────────────────────
# Trap SIGTERM and SIGINT so `docker stop` does a clean shutdown of
# the MetaTrader binary AND the Xvfb display server. Without this,
# the container kills MT mid-write and wineserver may keep the
# prefix locked across restart, which prevents the next boot.
# Audit ref: DMT-M2.
MT_PID=""
XVFB_PID=""
_shutdown() {
  echo "[INFO] Caught shutdown signal, terminating MetaTrader + Xvfb..." >&2
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
ZMQ_PORT="${ZMQ_PORT:-5555}"
DISPLAY=":99"
export DISPLAY

# ── Validate required env ─────────────────────────────────────────
for var in MT_LOGIN MT_PASSWORD MT_SERVER; do
  if [ -z "${!var:-}" ]; then
    echo "[FATAL] $var is not set. Exiting." >&2
    exit 1
  fi
done

# ── Paths ─────────────────────────────────────────────────────────
WINE_PREFIX="/home/mt/.wine"
export WINEPREFIX="$WINE_PREFIX"
export WINEDEBUG="-all"

if [ "$MT_PLATFORM" = "mt4" ]; then
  MT_DIR="$WINE_PREFIX/drive_c/Program Files (x86)/MetaTrader 4"
  MT_EXE="terminal.exe"
  EA_SRC="/opt/ea/ZeroMQ_EA.ex4"
  EA_DST="$MT_DIR/MQL4/Experts/ZeroMQ_EA.ex4"
else
  MT_DIR="$WINE_PREFIX/drive_c/Program Files/MetaTrader 5"
  MT_EXE="terminal64.exe"
  EA_SRC="/opt/ea/ZeroMQ_EA.ex5"
  EA_DST="$MT_DIR/MQL5/Experts/ZeroMQ_EA.ex5"
fi

# ── Start virtual framebuffer ─────────────────────────────────────
echo "[INFO] Starting Xvfb on $DISPLAY"
Xvfb "$DISPLAY" -screen 0 1024x768x16 -nolisten tcp &
XVFB_PID=$!

# Wait for Xvfb to be ready (up to 5 seconds).
for i in $(seq 1 50); do
  if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  echo "[FATAL] Xvfb failed to start." >&2
  exit 1
fi
echo "[INFO] Xvfb ready."

# ── Copy EA into the terminal's Experts directory ─────────────────
if [ -f "$EA_SRC" ]; then
  mkdir -p "$(dirname "$EA_DST")"
  cp -f "$EA_SRC" "$EA_DST"
  echo "[INFO] EA copied to $EA_DST"
else
  echo "[WARN] EA binary not found at $EA_SRC — manual installation required."
fi

# ── Generate MT Template to Auto-Attach EA ────────────────────────
# MetaTrader will NOT run an EA just because it's in the Experts folder.
# We must build a chart template (.tpl) and tell the INI file to load it.
if [ "$MT_PLATFORM" = "mt4" ]; then
  TPL_DIR="$MT_DIR/templates"
else
  TPL_DIR="$MT_DIR/Profiles/Templates"
fi
mkdir -p "$TPL_DIR"

cat > "$TPL_DIR/expert.tpl" <<EOF
<chart>
symbol=EURUSD
period=16385
<expert>
name=ZeroMQ_EA
</expert>
</chart>
EOF

echo "[INFO] EA Template written to $TPL_DIR/expert.tpl"

# ── Generate MT startup config ────────────────────────────────────
# MetaTrader reads a .ini file on startup to auto-login AND open the chart.
INI_FILE="$MT_DIR/config/startup.ini"
mkdir -p "$(dirname "$INI_FILE")"

cat > "$INI_FILE" <<EOF
[Common]
Login=$MT_LOGIN
Password=$MT_PASSWORD
Server=$MT_SERVER
AutoConfiguration=true

[Charts]
Symbol=EURUSD
Period=H1
Template=expert

[Experts]
AllowLive=true
AllowDllImport=true
Enabled=true
Account=$MT_LOGIN
Profile=default
EOF

echo "[INFO] Startup config written to $INI_FILE"

# ── Launch MetaTrader under Wine ──────────────────────────────────
echo "[INFO] Launching $MT_EXE (platform=$MT_PLATFORM, server=$MT_SERVER, login=$MT_LOGIN, zmq_port=$ZMQ_PORT)"

cd "$MT_DIR"
wine "$MT_EXE" "/config:$INI_FILE" &
MT_PID=$!

echo "[INFO] MetaTrader PID: $MT_PID"

# ── Monitor the terminal process ──────────────────────────────────
# If the terminal exits for any reason, we exit the container so
# Docker's restart policy (restart: unless-stopped) reboots it.
# This provides automatic self-healing.
wait $MT_PID
EXIT_CODE=$?

echo "[WARN] MetaTrader exited with code $EXIT_CODE. Container will restart."
kill $XVFB_PID 2>/dev/null || true
exit $EXIT_CODE
