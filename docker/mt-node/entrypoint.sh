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
ZMQ_PORT="${ZMQ_PORT:-5555}"
DISPLAY=":99"
export DISPLAY

# Sentinel written by the engine provisioner on first boot, before
# automatic broker symbol resolution has run. When the sentinel is
# present, skip writing the chart template and the Charts section of
# startup.ini so the EA falls back to MT's default chart; resolution
# runs against that default chart's GET_ALL_SYMBOLS reply, then the
# engine patches MT_SYMBOL to the broker-actual name and K8s rolls
# the Pod once. The second boot writes the chart template normally.
MT_SYMBOL_PENDING_SENTINEL="__pending__"

# ── Load Vault-rendered credentials ───────────────────────────────
# The Vault Agent init-container renders broker credentials to
# /vault/secrets/mt-credentials.env via the pod annotation
# vault.hashicorp.com/agent-inject-template-mt-credentials.env. The
# render is gated by agent-init-first=true on the Pod so the file
# always exists by the time this entrypoint runs in a real K8s pod.
#
# Local docker-compose has no injector; the operator can either set
# MT_LOGIN/MT_PASSWORD/MT_ZMQ_AUTH_TOKEN directly in the compose
# file's environment block (skipping the source), or pre-create the
# file at the same path.
VAULT_SECRETS_FILE="${VAULT_SECRETS_FILE:-/vault/secrets/mt-credentials.env}"
if [ -r "${VAULT_SECRETS_FILE}" ]; then
  # shellcheck disable=SC1090
  set -a
  . "${VAULT_SECRETS_FILE}"
  set +a
  if [ -n "${MT_VAULT_RENDERED_AT:-}" ]; then
    log INFO "Loaded Vault-rendered credentials (rendered_at=${MT_VAULT_RENDERED_AT})"
  else
    log INFO "Loaded Vault-rendered credentials from ${VAULT_SECRETS_FILE}"
  fi
else
  log INFO "Vault credentials file not present at ${VAULT_SECRETS_FILE}; relying on env (docker-compose / dev mode)"
fi

# Choose per-tenant token first, else platform default.
EFFECTIVE_AUTH_TOKEN="${MT_ZMQ_AUTH_TOKEN:-${DEFAULT_ZMQ_AUTH_TOKEN:-}}"

# ── Validate required env ─────────────────────────────────────────
for var in MT_LOGIN MT_PASSWORD MT_SERVER MT_SYMBOL; do
  if [ -z "${!var:-}" ]; then
    log FATAL "$var is not set"
    exit 1
  fi
done

if [ "$MT_SYMBOL" = "$MT_SYMBOL_PENDING_SENTINEL" ]; then
  SYMBOL_RESOLVED="false"
else
  SYMBOL_RESOLVED="true"
fi
if [ -z "${EFFECTIVE_AUTH_TOKEN}" ]; then
  log FATAL "Neither MT_ZMQ_AUTH_TOKEN (per-tenant) nor DEFAULT_ZMQ_AUTH_TOKEN (platform) is set"
  exit 1
fi

# ── Paths ─────────────────────────────────────────────────────────
# WINEPREFIX is a SUBDIRECTORY of the PVC mount point, not the mount
# point itself. The wine-prefix PVC mounts at /home/mt/.wine; on a
# fresh PVC the kubelet sets fsGroup (group=1000 + setgid) but the
# mount-root's OWNER uid stays root (0). Wine refuses a WINEPREFIX not
# owned by the running euid (1000) -> 'wine: '/home/mt/.wine' is not
# owned by you'. The container runs as uid 1000 under the
# etradie-system RESTRICTED PodSecurity Standard, so it can neither
# chown the mount root nor use a root init-container. Creating the
# prefix one level down (mkdir as uid 1000) makes the prefix root
# owned by 1000, which Wine accepts; the PVC still persists it. The
# mount-point parent is captured separately so the corruption-reset
# below clears the SUBDIR contents (it owns them), never the parent.
WINE_PREFIX_MOUNT="/home/mt/.wine"
WINE_PREFIX="${WINE_PREFIX_MOUNT}/prefix"
mkdir -p "$WINE_PREFIX"
# The template is baked into the image at build time by the Dockerfile.
# Holds a fully-initialised Wine prefix plus the MT5 + MT4 install. The
# seed-from-template block below copies it into the (PVC-mounted)
# WINE_PREFIX on first boot, then runs 'wineboot -u' to reconcile
# dosdevices and any absolute-path references in user.reg/system.reg.
WINE_TEMPLATE="${WINE_TEMPLATE:-/opt/wine-template/.wine}"
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
    # $WINE_PREFIX is a subdirectory the entrypoint owns (uid 1000),
    # nested inside the PVC mount point. Clear its CONTENTS (incl.
    # dotfiles); the subdir itself is owned by us so this also works
    # under readOnlyRootFilesystem (the writable PVC backs it). We
    # never touch the mount-point parent ($WINE_PREFIX_MOUNT), which
    # is root-owned and read-only to us.
    rm -rf "${WINE_PREFIX:?}"/* "${WINE_PREFIX:?}"/.[!.]* "${WINE_PREFIX:?}"/..?* 2>/dev/null || true
  fi
fi
# Seed the (PVC-mounted) Wine prefix from the image-baked template on
# first boot, or after a corruption-reset above. The template holds a
# fully-initialised Wine prefix plus the MT5 + MT4 install so we save
# 3-5 minutes per cold-start vs. running 'wineboot --init' from scratch
# (which would also leave the prefix without terminal64.exe, since the
# MT5 installer is baked into the template path, not /home/mt/.wine).
#
# After the copy we must reconcile Wine's path-translation state. Some
# Wine versions write absolute symlinks into dosdevices/* and absolute
# \??\unix\<path> references into user.reg/system.reg pinned to the
# template prefix. Removing dosdevices/* and running 'wineboot -u'
# regenerates them against the destination prefix. wineboot -u runs in
# update mode (~5s) because system.reg exists; it does NOT re-run the
# full init.
if [ ! -d "$WINE_PREFIX/drive_c/windows/system32" ]; then
  if [ -d "$WINE_TEMPLATE/drive_c/windows/system32" ]; then
    log INFO "Wine prefix missing; seeding from template $WINE_TEMPLATE"
    mkdir -p "$WINE_PREFIX"
    # cp -a preserves ownership/permissions/symlinks/timestamps. The
    # trailing '/.' copies the directory CONTENTS (avoids nesting the
    # source dir name inside the destination).
    cp -a "$WINE_TEMPLATE/." "$WINE_PREFIX/"
    # Drop dosdevices so wineboot -u rebuilds them pointing at the
    # destination prefix's drive_c (handles both relative and absolute
    # symlink layouts).
    rm -rf "$WINE_PREFIX/dosdevices"
    # Touch a marker so a future operator/audit can see this prefix
    # was seeded from the template (vs. user-mutated).
    date -u +'%Y-%m-%dT%H:%M:%SZ' > "$WINE_PREFIX/.seeded-from-template"
    log INFO "Reconciling prefix with wineboot -u (update mode)"
    wineboot -u 2>/dev/null || true
    wineserver --wait 2>/dev/null || true
    log INFO "Wine prefix seeded"
  else
    # Fallback for images built without the template (rapid-iteration
    # local builds that skipped the Dockerfile install steps). Logs a
    # loud WARN because the resulting prefix will NOT contain
    # terminal64.exe and the launch loop will fail until an operator
    # manually copies MT5/MT4 into the prefix.
    log WARN "Wine template $WINE_TEMPLATE not present; falling back to wineboot --init (no MT terminal binary will be available)"
    wineboot --init 2>/dev/null || true
    wineserver --wait 2>/dev/null || true
  fi
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

# ── Chart template + startup INI ────────────────────────────────
# When the symbol has not been resolved yet, MT boots into its
# default chart and the EA attaches there; the engine resolves the
# broker-actual symbol via GET_ALL_SYMBOLS and patches MT_SYMBOL,
# triggering a single rolling restart with the real value.
INI_FILE="$MT_DIR/config/startup.ini"
if [ "$SYMBOL_RESOLVED" = "true" ]; then
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
else
  log INFO "MT_SYMBOL is the resolution sentinel; skipping chart template until engine patches the StatefulSet"
  cat > "$INI_FILE" <<EOF
[Common]
Login=${MT_LOGIN}
Password=${MT_PASSWORD}
Server=${MT_SERVER}
AutoConfiguration=true

[Experts]
AllowLive=true
AllowDllImport=true
Enabled=true
Account=${MT_LOGIN}
Profile=default
EOF
fi
log INFO "Startup config written to $INI_FILE"

# ── Disable MT5 LiveUpdate self-restart loop (defect #15) ────────
# MT5 (build 5836) runs LiveUpdate on every cold boot: it detects a
# newer build's data on MetaQuotes' servers, downloads it, and
# self-restarts to apply (exit 143). The supervised loop then
# relaunches, re-seeds, and re-runs the full recompile + LiveUpdate
# from scratch -- an infinite, non-convergent loop in which the EA
# OnInit never runs, MQL5/Logs is never created, and :5555 never
# binds, so the pod never reaches Ready.
#
# LiveUpdate is controlled in terminal.ini (NOT common.ini) under the
# [LiveUpdate] section; LastBuildDataPath tracks the last-known build.
# Pinning it to the baked terminal build makes MT5 treat itself as
# current and skip the update + self-restart. Config only; no EA
# recompile. MT5 path only -- MT4 is not affected by this loop and the
# [LiveUpdate] section is MT5-specific.
if [ "$MT_PLATFORM" = "mt5" ]; then
  # Resolve the baked terminal build so we never pin a stale number.
  # MT5 records the running build in its journal as
  # 'MetaTrader 5 x64 build <N> started'; fall back to the known
  # baked build (5836) if the journal is not yet present (first boot).
  MT5_BUILD=""
  MT5_JOURNAL_DIR="$MT_DIR/logs"
  if [ -d "$MT5_JOURNAL_DIR" ]; then
    MT5_BUILD=$(grep -ahoE 'build [0-9]+ started' "$MT5_JOURNAL_DIR"/*.log 2>/dev/null \
      | grep -oE '[0-9]+' | sort -rn | head -n1 || true)
  fi
  MT5_BUILD="${MT5_BUILD:-5836}"
  TERMINAL_INI="$MT_DIR/config/terminal.ini"
  if [ -f "$TERMINAL_INI" ]; then
    # Preserve any existing terminal.ini content but replace/append the
    # [LiveUpdate] section deterministically.
    if grep -qi '^\[LiveUpdate\]' "$TERMINAL_INI"; then
      # Drop the existing [LiveUpdate] section (from its header up to
      # the next section header or EOF), then append a clean one.
      awk 'BEGIN{skip=0}
           /^\[[Ll]ive[Uu]pdate\]/{skip=1; next}
           /^\[/{skip=0}
           skip==0{print}' "$TERMINAL_INI" > "${TERMINAL_INI}.tmp"
      mv "${TERMINAL_INI}.tmp" "$TERMINAL_INI"
    fi
    printf '\n[LiveUpdate]\nLastBuildDataPath=%s\n' "$MT5_BUILD" >> "$TERMINAL_INI"
  else
    cat > "$TERMINAL_INI" <<EOF
[LiveUpdate]
LastBuildDataPath=${MT5_BUILD}
EOF
  fi
  log INFO "LiveUpdate pinned to build ${MT5_BUILD} in $TERMINAL_INI (defect #15)"
fi

# ── Supervised MT restart loop ───────────────────────────────────
restart_count=0
window_start=$(date +%s)

while :; do
  log INFO "Launching $MT_EXE (platform=$MT_PLATFORM, server=$MT_SERVER, login=$MT_LOGIN, symbol=$MT_SYMBOL, symbol_resolved=$SYMBOL_RESOLVED, zmq_port=$ZMQ_PORT, restart_count=$restart_count)"

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
