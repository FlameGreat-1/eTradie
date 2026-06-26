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

# LiveUpdate self-restart handling (exit 143 from MT5/MT4).
# When MT5 self-exits 143 to apply a downloaded component, the kernel
# needs a brief window to finish the in-flight rename + write-back
# on the (PVC-backed) Wine prefix before we relaunch. SIGKILLing the
# wineserver helpers or relaunching immediately races the rename and
# leaves $WINE_PREFIX/.update-timestamp.lock behind, which is the
# pattern that fed the corruption-reset loop documented in
# docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md.
LIVEUPDATE_SETTLE_SECS="${LIVEUPDATE_SETTLE_SECS:-30}"

MT_PID=""
XVFB_PID=""
DRIVER_PID=""
WM_PID=""

# Window manager wait budget. fluxbox normally registers its EWMH
# atoms on the X root within ~200ms of starting under Xvfb. The 10s
# ceiling here is paranoia for the slow-I/O case (PVC under heavy
# write pressure during the wine seed) and is far below any other
# startup budget in the pod. On timeout we log FATAL and exit so the
# kubelet restarts the container with a clean slate rather than
# launching MT5 against an X server that has no WM (which is exactly
# the failure mode this commit closes; see audit ref in the commit
# message).
WM_READY_TIMEOUT_SECS="${WM_READY_TIMEOUT_SECS:-10}"

log() { printf '%s [%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$1" "$2" >&2; }

# ── Signal handling ─────────────────────────────────────────────
_shutdown() {
  log INFO "Caught shutdown signal, terminating auto-login driver + MetaTrader + fluxbox + Xvfb"
  # Tear down the driver FIRST so it does not race the MT5 SIGTERM
  # below (a driver mid-`xdotool type` would otherwise inject
  # keystrokes into a window that is being closed).
  if [ -n "${DRIVER_PID}" ] && kill -0 "${DRIVER_PID}" 2>/dev/null; then
    kill -TERM "${DRIVER_PID}" 2>/dev/null || true
    pkill -P "${DRIVER_PID}" -TERM 2>/dev/null || true
    for _ in $(seq 1 30); do
      kill -0 "${DRIVER_PID}" 2>/dev/null || break
      sleep 0.1
    done
    kill -KILL "${DRIVER_PID}" 2>/dev/null || true
    pkill -P "${DRIVER_PID}" -KILL 2>/dev/null || true
  fi
  if [ -n "${MT_PID}" ] && kill -0 "${MT_PID}" 2>/dev/null; then
    kill -TERM "${MT_PID}" 2>/dev/null || true
    for _ in $(seq 1 100); do
      kill -0 "${MT_PID}" 2>/dev/null || break
      sleep 0.1
    done
    kill -KILL "${MT_PID}" 2>/dev/null || true
  fi
  # Tear down fluxbox BEFORE Xvfb so it can release its X resources
  # cleanly (managed-window list, root-window properties) rather than
  # crashing on a dead X server. fluxbox normally exits within ~100ms
  # of SIGTERM.
  if [ -n "${WM_PID}" ] && kill -0 "${WM_PID}" 2>/dev/null; then
    kill -TERM "${WM_PID}" 2>/dev/null || true
    for _ in $(seq 1 30); do
      kill -0 "${WM_PID}" 2>/dev/null || break
      sleep 0.1
    done
    kill -KILL "${WM_PID}" 2>/dev/null || true
  fi
  if [ -n "${XVFB_PID}" ]; then
    kill -TERM "${XVFB_PID}" 2>/dev/null || true
  fi
  wineserver -k 2>/dev/null || true
  exit 0
}
trap _shutdown TERM INT

# ── Auto-login driver (xdotool-based GUI automation) ───────────
# MT5 build 5836 ignores /login /password /server flags and the
# startup.ini [Common] block, so the Login dialog is driven via
# xdotool. Phases: 1 wait for terminal; 2a/2b/2c surface or invoke
# the Login dialog (or fast-path on an existing :5555 bind); 3 fill
# + submit credentials; login-auth gate; chart-attach; 4 poll :5555
# + dismiss follow-ups. Best-effort: a driver crash never kills MT5.
# NEVER logs $MT_PASSWORD.
AUTO_LOGIN_CLIPBOARD_TIMEOUT_SECS="${AUTO_LOGIN_CLIPBOARD_TIMEOUT_SECS:-3}"

# Phase 3 per-field input strategy: paste_then_type (default; paste
# first, fall back to xdotool type), paste (paste only), or type
# (type only). Tunable per-pod via `kubectl set env`.
AUTO_LOGIN_INPUT_STRATEGY="${AUTO_LOGIN_INPUT_STRATEGY:-paste_then_type}"

# Overall driver budget. Covers worst-case first boot: Phase 1-2
# (~60s) + Phase 3 (~10s) + login-auth gate (up to 120s; real Exness
# handshake measured at 87s) + Phase 5 settle (up to 60s, early-exits)
# + Phase 5 attempt 1 (chart-window-wait 20s + bind-wait 30s). ~305s
# baseline; 420s gives headroom. Stays under the startupProbe budget
# (620s) and the engine readiness timeout (600s) so the driver always
# completes before those outer gates fire. The hard-kill fires at
# 420 + AUTO_LOGIN_HARD_KILL_GRACE_SECS. Subsequent boots use
# accounts.dat and finish in ~20-30s.
AUTO_LOGIN_TOTAL_BUDGET_SECS="${AUTO_LOGIN_TOTAL_BUDGET_SECS:-420}"
AUTO_LOGIN_DIALOG_WAIT_SECS="${AUTO_LOGIN_DIALOG_WAIT_SECS:-120}"
AUTO_LOGIN_PROCESS_WAIT_SECS="${AUTO_LOGIN_PROCESS_WAIT_SECS:-60}"
AUTO_LOGIN_FOLLOWUP_DISMISS_SECS="${AUTO_LOGIN_FOLLOWUP_DISMISS_SECS:-60}"
AUTO_LOGIN_DIALOG_TITLE_REGEX="${AUTO_LOGIN_DIALOG_TITLE_REGEX:-^(Login|Open an Account|Login to Trade Account|Authorization)}"
# Phase 2c tunables. See the contract docstring above.
#
# AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS: how long Phase 2a polls for a
#   Login-shaped dialog before falling through to Phase 2c. Sized
#   to ~10s main-UI render + ~10s LiveUpdate modal grace + 10s slack;
#   if the dialog has not appeared by then on build 5836 with
#   pre-staged config, MT5 will never prompt and Phase 2c must
#   invoke File -> Login to Trade Account explicitly.
# AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS: per-attempt wait for the
#   Login dialog after a Phase 2c invocation (hotkey or menu). Used
#   twice -- once after Ctrl+Shift+L, once after Alt+F menu fallback.
# AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX: WM_NAME pattern for the MT main
#   UI window. Build 5836 emits TWO distinct shapes that BOTH must be
#   matched by this regex:
#     * PRE-login (Phase 2c entry): 'MetaTrader 5 - Netting' /
#       'MetaTrader 5 - Hedging' / 'MetaTrader 4 - <Account>'. This is
#       what Phase 2c sees when MT5 opens the main UI directly without
#       a Login dialog.
#     * POST-login (Phase 5 entry on the boot-2 / accounts.dat fast
#       path): MT5 rewrites the title to '<login_id> -   - Netting' /
#       '<login_id> -   - Hedging' the instant the broker login
#       succeeds. The runbook captured this exact shape in the
#       post_submit_1s log line: 'name=133978149 -   - Netting'.
#   Phase 5's re-resolve block runs AFTER login, so without the
#   post-login shape in the regex Phase 5 logs 'no main window WID
#   provided; cannot drive menu navigation' and skips chart-attach
#   entirely on every accounts.dat boot. Both shapes are anchored at
#   start-of-string with '^' so log-window titles ('logs', 'Toolbox',
#   ...) and broker-injected modals cannot accidentally match.
#   The state machine additionally gates Phase 2c on MT_PLATFORM=mt5
#   because the MT5-on-Wine path is the only one with empirical
#   evidence of skipping the Login prompt.
AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS="${AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS:-30}"
AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS="${AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS:-15}"
AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX="${AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX:-^(MetaTrader [45] - (Netting|Hedging)|[0-9]+ - +- (Netting|Hedging))}"
# Optional operator override for the journal login-confirmation regex.
# Leave EMPTY (default) to let _drv_login_authenticated() build a
# login-id-keyed pattern at call time (MT_LOGIN is not yet populated
# here - it is loaded from Vault later in the script). Set a non-empty
# value only to force a specific pattern for an unforeseen broker
# journal format; it is then used verbatim.
AUTO_LOGIN_JOURNAL_AUTH_REGEX="${AUTO_LOGIN_JOURNAL_AUTH_REGEX:-}"
# Budget for the post-submit broker-handshake wait. The Login dialog
# closing does NOT mean the broker accepted the credentials; MT5
# probes server pools (often failing on wrong pools first) and only
# then writes the authorize line. The operator's real Exness journal
# showed ~87s between the first failed pool attempt and the successful
# authorize, so 120s gives ~38% headroom while keeping worst-case
# driver time (~60-90s to submit + 120s wait) within
# AUTO_LOGIN_TOTAL_BUDGET_SECS=240.
AUTO_LOGIN_LOGIN_AUTH_WAIT_SECS="${AUTO_LOGIN_LOGIN_AUTH_WAIT_SECS:-120}"
# Wall-clock ceiling on a single xdotool invocation. xdotool's `search
# --onlyvisible --name <re>` and `windowactivate --sync` calls can
# block indefinitely against Wine override-redirect modal windows
# whose WM_NAME atom or _NET_ACTIVE_WINDOW state has not yet stabilised
# (jordansissel/xdotool issues #117 / #126, Wine bug 51924). Without
# a per-call wall-clock cap, a single hung call wedges the entire
# driver and renders AUTO_LOGIN_TOTAL_BUDGET_SECS inoperative — the
# exact failure observed on the 2026-06-24 staging run
# (docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md). The 5s default
# is well above the happy-path latency of any single xdotool primitive
# (~50ms) and well below AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS so
# the per-attempt 15s window can absorb at least two retries if a
# transient call genuinely times out.
AUTO_LOGIN_XDOTOOL_TIMEOUT_SECS="${AUTO_LOGIN_XDOTOOL_TIMEOUT_SECS:-5}"
# Per-character typing delay for Phase 3 credential typing. Industry
# baseline for Wine-translated Win32 keystrokes is 100-200ms/char.
# 50ms (the historical value) was too fast: empirical staging
# evidence (2026-06-24 08:52 post-Phase-3 screenshot) showed
# keystrokes being dropped at the X-event / Wine-message-pump
# boundary: Login field got 0 chars, Password got 3 chars, Server
# lost its trailing character. 150ms is the safe floor under our
# fluxbox+Xvfb+Wine pipeline.
AUTO_LOGIN_TYPE_DELAY_MS="${AUTO_LOGIN_TYPE_DELAY_MS:-150}"
# Settle delay between field-focus transitions in Phase 3. The
# message pump needs time to process the Tab event and fire the
# focus-change handler on the new field before xdotool starts
# typing. 0.5s is the canonical Wine-on-Xvfb value.
AUTO_LOGIN_FIELD_SETTLE_SECS="${AUTO_LOGIN_FIELD_SETTLE_SECS:-0.5}"
# Belt-and-braces hard-kill grace. The driver maintains its own
# wall-clock kill-switch (forked at entry) so that even if a future
# code path introduces a new blocking xdotool surface, the driver
# cannot exceed AUTO_LOGIN_TOTAL_BUDGET_SECS + this grace before
# SIGTERMing itself. The supervisor then reaps it and the MT5 process
# lifecycle continues unaffected (the driver is best-effort by
# contract; its death does NOT kill MT5).
AUTO_LOGIN_HARD_KILL_GRACE_SECS="${AUTO_LOGIN_HARD_KILL_GRACE_SECS:-30}"

_drv_log() { log "INFO" "auto_login: $*"; }
_drv_warn() { log "WARN" "auto_login: $*"; }
_drv_err() { log "ERROR" "auto_login: $*"; }

# Wrap every xdotool call in `timeout` so a wedged X interaction
# (Wine modal whose WM_NAME atom never stabilises) cannot hang the
# driver. Any non-zero exit (including timeout 124) is treated by
# callers as a no-op via their `2>/dev/null || true` postfix.
_xdo() {
  timeout "${AUTO_LOGIN_XDOTOOL_TIMEOUT_SECS}" xdotool "$@"
}

# Deliver a credential to the focused field via X CLIPBOARD + Ctrl+V
# (atomic WM_PASTE; no per-char drops). Caller must have Tab'd to the
# field. $1=label (never logs the value); stdin=the literal bytes.
_drv_paste_into_focused_field() {
  local _label="$1"
  local _bytes_read
  # Step 1: clear field deterministically.
  DISPLAY=:99 _xdo key --clearmodifiers ctrl+a 2>/dev/null || true
  sleep 0.2
  DISPLAY=:99 _xdo key --clearmodifiers Delete 2>/dev/null || true
  sleep 0.2
  # Step 2: read stdin bytes and pipe to xclip atomically. We measure
  # the byte count so we can log a length-only audit signal without
  # ever surfacing the value itself.
  _bytes_read=$(
    LC_ALL=C timeout "$AUTO_LOGIN_CLIPBOARD_TIMEOUT_SECS" sh -c '
      data=$(cat)
      printf "%s" "$data" | xclip -display :99 -selection clipboard -in -loops 1 >/dev/null 2>&1 &
      printf "%s" "${#data}"
    ' 2>/dev/null
  ) || _bytes_read=""
  if [ -z "$_bytes_read" ]; then
    _drv_warn "paste ${_label}: xclip set-clipboard failed or timed out"
    return 1
  fi
  # Brief settle so xclip's selection-owner registration completes
  # before the paste consumer arrives.
  sleep 0.15
  # Step 5: paste.
  DISPLAY=:99 _xdo key --clearmodifiers ctrl+v 2>/dev/null || true
  sleep "$AUTO_LOGIN_FIELD_SETTLE_SECS"
  _drv_log "paste ${_label}: ok (length=${_bytes_read}, content not logged)"
  return 0
}

# _drv_scrub_clipboard: overwrite the X CLIPBOARD selection with the
# empty string so no credential residue lingers in the X selection
# buffer after Phase 3 completes. Called at the end of Phase 3 and on
# any abort path that may have populated the clipboard.
_drv_scrub_clipboard() {
  : | timeout "$AUTO_LOGIN_CLIPBOARD_TIMEOUT_SECS" \
    xclip -display :99 -selection clipboard -in 2>/dev/null || true
  _drv_log "clipboard scrubbed"
}

# Fallback delivery via xdotool type (per-char, 150ms delay tuned for
# Wine-translated Win32 input). $1=value (argv), $2=label. The value
# is briefly visible in xdotool's /proc cmdline (readable only by the
# mt uid); logs the byte length only.
_drv_type_into_focused_field() {
  local _value="$1"
  local _label="$2"
  local _len=${#_value}
  # Step 1: clear field deterministically.
  DISPLAY=:99 _xdo key --clearmodifiers ctrl+a 2>/dev/null || true
  sleep 0.2
  DISPLAY=:99 _xdo key --clearmodifiers Delete 2>/dev/null || true
  sleep 0.2
  # Step 2: type. Wrapped in _xdo so any per-call hang is bounded by
  # AUTO_LOGIN_XDOTOOL_TIMEOUT_SECS. Note: a long password at 150ms/char
  # can exceed the default 5s timeout; the type call's wall-clock is
  # ~ length * delay_ms / 1000 + overhead. For a 24-char password at
  # 150ms = ~3.6s, well under the 5s ceiling. If passwords longer than
  # ~30 chars are expected, raise AUTO_LOGIN_XDOTOOL_TIMEOUT_SECS via
  # env var.
  if ! DISPLAY=:99 _xdo type --clearmodifiers \
       --delay "$AUTO_LOGIN_TYPE_DELAY_MS" -- "$_value" 2>/dev/null; then
    _drv_warn "type ${_label}: xdotool type failed or timed out (length=${_len})"
    return 1
  fi
  sleep "$AUTO_LOGIN_FIELD_SETTLE_SECS"
  _drv_log "type ${_label}: ok (length=${_len}, content not logged)"
  return 0
}

# Deliver a credential to the focused field using
# AUTO_LOGIN_INPUT_STRATEGY. $1=value, $2=label. Returns 0 on
# success, 1 when every configured strategy attempt failed.
_drv_deliver_credential() {
  local _value="$1"
  local _label="$2"
  local _strategy="${AUTO_LOGIN_INPUT_STRATEGY:-paste_then_type}"

  case "$_strategy" in
    paste)
      _drv_log "deliver ${_label}: paste strategy (no fallback)"
      printf '%s' "$_value" | _drv_paste_into_focused_field "$_label"
      return $?
      ;;
    type)
      _drv_log "deliver ${_label}: type strategy (no paste)"
      _drv_type_into_focused_field "$_value" "$_label"
      return $?
      ;;
    paste_then_type)
      _drv_log "deliver ${_label}: paste-then-type strategy; paste attempt"
      if printf '%s' "$_value" | _drv_paste_into_focused_field "$_label"; then
        _drv_log "deliver ${_label}: paste succeeded"
        return 0
      fi
      _drv_warn "deliver ${_label}: paste failed, falling back to type"
      if _drv_type_into_focused_field "$_value" "$_label"; then
        _drv_log "deliver ${_label}: type fallback succeeded after paste failure"
        return 0
      fi
      _drv_err "deliver ${_label}: BOTH paste and type failed"
      return 1
      ;;
    *)
      _drv_warn "deliver ${_label}: unknown strategy '${_strategy}'; defaulting to paste_then_type"
      if printf '%s' "$_value" | _drv_paste_into_focused_field "$_label"; then
        return 0
      fi
      _drv_type_into_focused_field "$_value" "$_label"
      return $?
      ;;
  esac
}

# Phase 3 stage-by-stage observability. Logs the currently-focused
# window's WID and WM_NAME at the named stage so the operator can
# correlate the credential-typing sequence against the dialog focus
# state. NEVER logs credential values: only window identifiers and
# the stage marker. xdotool calls are timeout-bounded via _xdo.
_drv_phase3_log() {
  local _stage="$1"
  local _wid _name
  _wid=$(DISPLAY=:99 _xdo getactivewindow 2>/dev/null || echo "unknown")
  if [ "$_wid" != "unknown" ] && [ -n "$_wid" ]; then
    _name=$(DISPLAY=:99 _xdo getwindowname "$_wid" 2>/dev/null || echo "unknown")
  else
    _name="unknown"
  fi
  _drv_log "phase3 stage=${_stage} focused_wid=${_wid} name=${_name}"
}

_drv_zmq_bound() {
  # :15B3 = 5555 dec. State 0A = TCP_LISTEN.
  awk 'NR>1 && $4 == "0A" && ($2 ~ /:15B3$/ || $3 ~ /:15B3$/){found=1; exit} END{exit !found}' \
    /proc/net/tcp 2>/dev/null
}

_drv_mt_proc_alive() {
  if [ "${MT_PLATFORM:-mt5}" = "mt4" ]; then
    pgrep -f 'terminal\.exe' >/dev/null 2>&1
  else
    pgrep -f 'terminal64\.exe' >/dev/null 2>&1
  fi
}

# Generic visible-window WM_NAME search. Returns the first matching
# WID on stdout (empty if no match). Single source of truth for the
# xdotool search shape so Phase 2a, Phase 2c, and the Phase 4
# dismiss loop use identical semantics.
#
# The xdotool call is wrapped in `_xdo` (timeout-bounded) because
# `search --onlyvisible --name <re>` performs an XGetWindowProperty
# per visible window to fetch WM_NAME, and a Wine-rendered modal
# whose name atom has not yet been published can hang the property
# fetch indefinitely. On timeout the helper returns the empty string
# (no match) and the caller treats it as 'window absent', which is
# the correct semantic fallback.
_drv_find_window_by_regex() {
  local _re="$1"
  DISPLAY=:99 _xdo search --onlyvisible --name "$_re" 2>/dev/null | head -1 || true
}

_drv_find_login_dialog() {
  _drv_find_window_by_regex "$AUTO_LOGIN_DIALOG_TITLE_REGEX"
}

_drv_find_main_window() {
  _drv_find_window_by_regex "$AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX"
}

# Authoritative login confirmation from the MT5 journal (Tier 2). The
# journal is MT5's own record of the broker handshake, far more
# reliable than the MDI window title. Real Exness journal success
# lines (login-id keyed):
#   '<login>': authorized on <server> through ...
#   '<login>': terminal synchronized with <company> ...
#   '<login>': trading has been enabled - hedging mode
# The failure line "'<login>': authorization on <server> failed
# (Invalid account)" shares none of these tokens, so a rejected login
# is NOT a match. The effective pattern is built at call time keyed to
# MT_LOGIN (now populated from Vault); an explicit
# AUTO_LOGIN_JOURNAL_AUTH_REGEX override, if set, wins verbatim.
# Echoes the matched line on success (return 0).
_drv_login_authenticated() {
  local _journal _match _regex
  if [ -n "${AUTO_LOGIN_JOURNAL_AUTH_REGEX:-}" ]; then
    _regex="$AUTO_LOGIN_JOURNAL_AUTH_REGEX"
  else
    _regex="'${MT_LOGIN}': (authorized on |terminal synchronized with |trading has been enabled)"
  fi
  _journal=$(ls -t "$MT_DIR/logs/"*.log 2>/dev/null | head -n1 || true)
  [ -n "$_journal" ] || return 1
  _match=$(tr -d '\000' < "$_journal" 2>/dev/null \
    | grep -aE "$_regex" \
    | tail -n1 || true)
  if [ -n "$_match" ]; then
    printf '%s' "$_match"
    return 0
  fi
  return 1
}

# Supplementary human-diagnostic only: returns the current active
# window title (e.g. '<login> -   - Netting'). NOT used as a gate.
_drv_active_title() {
  local _w
  _w=$(DISPLAY=:99 _xdo getactivewindow 2>/dev/null || echo "")
  [ -n "$_w" ] && DISPLAY=:99 _xdo getwindowname "$_w" 2>/dev/null || true
}

# Poll the journal for a broker connect/authorize line up to
# AUTO_LOGIN_LOGIN_AUTH_WAIT_SECS. Echoes the matched journal line on
# success (return 0); returns 1 on timeout. Logs the journal tail and
# the live MDI title each second so the exact handshake moment and any
# broker-side rejection are observable in the driver log.
_drv_wait_for_login_auth() {
  local _budget="$1"
  local _waited=0 _line _title
  while [ "$_waited" -lt "$_budget" ]; do
    _line=$(_drv_login_authenticated)
    if [ -n "$_line" ]; then
      _drv_log "login confirmed via journal at +${_waited}s: ${_line}"
      printf '%s' "$_line"
      return 0
    fi
    if ! _drv_mt_proc_alive; then
      _drv_warn "terminal process exited during login-auth wait at +${_waited}s"
      return 1
    fi
    _title=$(_drv_active_title)
    _drv_log "login-auth wait +${_waited}s: active title='${_title}' (awaiting broker connect/authorize line in journal)"
    sleep 1
    _waited=$(( _waited + 1 ))
  done
  return 1
}

# _drv_clear_modals_for_main_window: aggressively dismiss any open modals
# (like the nameless "Open an Account" wizard or the "Welcome to LiveUpdate"
# standalone permissions dialog) that might steal focus from the main UI
# window during Phase 2c menu navigation.
#
# Contract:
#   * $1 = WID of the main UI window.
#
# Dismissal cascade:
#   1. Poll getactivewindow. If the active window is the main UI window,
#      or if there is no active window, we're done.
#   2. If the active window is a blocking modal, attempt to dismiss it.
#   3. If its WM_NAME is 'Welcome to LiveUpdate' (the permissions modal
#      that appears on build 5836), send Return (its default accept action;
#      Escape may be ignored as cancel).
#   4. Otherwise (e.g. the nameless "Open an Account" wizard, which
#      contains an embedded LiveUpdate section asking to Restart),
#      send Escape to trigger its Cancel/Close path. Sending Return here
#      would click the focused "Restart" button, triggering a 143 exit loop.
#   5. Repeat up to 5 times. If a blocking modal is still active, force
#      windowunmap as a last resort.
_drv_clear_modals_for_main_window() {
  local _mwid="$1"
  local _awid _aname _i
  
  for _i in $(seq 1 5); do
    _awid=$(DISPLAY=:99 _xdo getactivewindow 2>/dev/null || echo "unknown")
    if [ "$_awid" = "unknown" ] || [ -z "$_awid" ]; then
      break
    fi
    if [ "$_awid" = "$_mwid" ]; then
      _drv_log "main window is active; modals cleared"
      return 0
    fi
    
    _aname=$(DISPLAY=:99 _xdo getwindowname "$_awid" 2>/dev/null || echo "unknown")
    _drv_log "blocking modal detected (WID=${_awid}, NAME=${_aname}); attempting dismiss"
    
    case "$_aname" in
      Welcome\ to\ LiveUpdate*)
        DISPLAY=:99 _xdo key --clearmodifiers Return 2>/dev/null || true
        ;;
      *)
        DISPLAY=:99 _xdo key --clearmodifiers Escape 2>/dev/null || true
        ;;
    esac
    sleep 0.5
  done
  
  # Final fallback: unmap anything still blocking.
  _awid=$(DISPLAY=:99 _xdo getactivewindow 2>/dev/null || echo "unknown")
  if [ "$_awid" != "unknown" ] && [ -n "$_awid" ] && [ "$_awid" != "$_mwid" ]; then
    _aname=$(DISPLAY=:99 _xdo getwindowname "$_awid" 2>/dev/null || echo "unknown")
    _drv_warn "modal still active after Escape/Return cascade (WID=${_awid}, NAME=${_aname}); unmapping"
    DISPLAY=:99 _xdo windowunmap "$_awid" 2>/dev/null || true
    sleep 0.2
  fi
  return 0
}

# Poll _drv_find_login_dialog up to <budget_secs>. Echoes the WID
# of the matched window on success, returns 0 on success / 1 on
# timeout. Used by Phase 2c after each invocation attempt to wait
# for the Login dialog to appear.
_drv_wait_for_dialog() {
  local _budget="$1"
  local _waited=0 _wid
  while [ "$_waited" -lt "$_budget" ]; do
    _wid=$(_drv_find_login_dialog)
    if [ -n "$_wid" ]; then
      printf '%s' "$_wid"
      return 0
    fi
    sleep 1
    _waited=$(( _waited + 1 ))
  done
  return 1
}

# Phase 2c invocation helpers. Three attempts in sequence; each one
# returns after sending its keystrokes. The caller (auto_login_driver)
# polls for the Login dialog with _drv_wait_for_dialog() after each
# attempt and proceeds to the next on timeout.
#
# Evidence basis for ordering (2026-06-24 research + staging):
#
#   - No keyboard accelerator exists for 'Login to Trade Account' on
#     MT5 build 5836 (verified across 5 independent hotkey reference
#     compilations including MetaQuotes' own). The previous
#     Ctrl+Shift+L attempt was a hypothesis; staging confirmed it does
#     nothing. REMOVED.
#
#   - Win32 menu mnemonics are the most build-stable invocation path
#     because they bind to the displayed letter of a menu item, not
#     to its position. MT5's 'Login to Trade Account' almost certainly
#     uses 'L' as its mnemonic (standard Win32 convention; multiple
#     L-mnemonic items in the menu cycle on repeated keypresses).
#
#   - Down-arrow counting is position-dependent and brittle to menu
#     layout drift across MT5 revisions or broker-injected items.
#     Kept as fallback for cases where the mnemonic is absent or
#     bound to a different item.

# Phase 5 (chart-attach) tunables. See the Phase 5 contract in the
# auto_login_driver() docstring above.
#
# AUTO_LOGIN_PHASE5_ENABLED: master switch. Default on. Set to 0 to
#   disable Phase 5 entirely (e.g. when investigating an unrelated
#   Phase 3/4 regression on staging without rebuilding the image).
# AUTO_LOGIN_PHASE5_POST_LOGIN_SETTLE_SECS: how long to wait after
#   the Phase 3 submit for MT5's post-login synchronous work to
#   settle (broker access-server handshake, Market Watch symbol-
#   catalogue download, Welcome-to-LiveUpdate modal materialisation).
#   The 2026-06-24 15:14 staging diagnostic showed the Welcome modal
#   appearing ~25s after submit; this window must be long enough for
#   the modal to appear AND be dismissed by Phase 5's pre-keystroke
#   sweep before menu navigation starts.
# AUTO_LOGIN_PHASE5_CHART_WINDOW_WAIT_SECS: per-attempt budget for
#   a chart window to appear after menu navigation. MT5 opens the
#   chart synchronously when the symbol-picker submenu's Return
#   accelerator fires; the chart window's WM_NAME is published
#   within ~500ms. 20s covers slow-I/O cases and broker symbol-
#   catalogue lookups.
# AUTO_LOGIN_PHASE5_CHART_WINDOW_TITLE_REGEX: WM_NAME pattern for an
#   open MT5 chart window. The MT5 chart title format is
#   '<SYMBOL>,<TIMEFRAME>' (e.g. 'EURUSD,H1' or 'XAUUSD.m,H1').
#   Symbol characters include broker-specific suffix punctuation
#   ('.', '#', '_', '-', '^', '+', '@', '!'), plus alphanumerics; the
#   regex is intentionally permissive so brokers with EURUSD.m /
#   EURUSD-cd / XAUUSD# / BTCUSD@ all match.
# AUTO_LOGIN_PHASE5_BIND_WAIT_SECS: how long to poll :5555 after
#   the chart opens before falling through to Phase 4. Sized to the
#   EA's typical OnInit -> bind latency (~1-3s under fluxbox+Xvfb+
#   Wine pipeline); 30s gives headroom without burning much of the
#   total budget.
# AUTO_LOGIN_PHASE5_INTER_ATTEMPT_SECS: settle between attempts so a
#   half-opened menu has time to close before the next Alt+F.
#
# Phase 5 default is OFF.
#
# Phase 5 was a 3-attempt keystroke cascade (Ctrl+M Market Watch /
# File menu fallback) designed to force MT5 to open a chart after
# Phase 3 submitted credentials. It was authored against the GENERIC
# MetaQuotes terminal64.exe (which does NOT auto-open charts), back
# when the image baked the generic install. That image no longer
# exists: every Pod now receives the BRANDED terminal64.exe at
# runtime via the broker-bundle overlay. Branded MT (Exness, Deriv,
# ...) auto-opens its own default charts after login - confirmed on
# the operator workstation for both Exness and Deriv (Wine + real X
# display) and documented in docs/runbooks/HOSTED-MT-PROVISIONING-
# SESSION.md Section A.2.
#
# On the failed 2026-06-25 staging run, Phase 5 attempt 3 actively
# UNMAPPED MT5's own Toolbox/Journal panel ('WID=18874369 NAME=logs')
# during its modal-clear cascade. That is destructive to MT5's UI
# assembly. With the branded binary now running there is no scenario
# in which Phase 5 helps: either MT5 auto-opens charts (Phase 5 races
# MT5's own work) or it does not (the branded binary's chart-attach
# is broker-side, not keystroke-driven).
#
# The Phase 5 code is RETAINED below so an operator can opt-in for a
# specific Pod via
#   kubectl -n etradie-system set env statefulset/<release> -c mt-node \
#     AUTO_LOGIN_PHASE5_ENABLED=1
# without an image rebuild. The default is 0.
# Chart-attach is REQUIRED for the EA to load: the ZeroMQ_EA binds
# tcp://*:5555 in OnInit(), and OnInit runs only when the EA is
# attached to a chart. Branded MT5 auto-opens its OWN bundled
# workspace charts after login, but those use the broker's per-chart
# templates, not Profiles/Templates/expert.tpl, so our EA is never
# attached by that path. This cascade opens a chart and lets MT5
# apply expert.tpl (which names ZeroMQ_EA). It runs ONLY after the
# login-success gate confirmed the broker handshake, so it can no
# longer race a still-initialising terminal. Set to 0 only to
# diagnose an unrelated regression without an image rebuild.
AUTO_LOGIN_PHASE5_ENABLED="${AUTO_LOGIN_PHASE5_ENABLED:-1}"
# Upper bound only: the settle loop early-exits the instant a
# deterministic readiness signal fires (see
# _drv_phase5_mql5_logs_present / _drv_phase5_welcome_modal_seen below).
# Raised from 25 -> 60 because the 2026-06-24 18:11 staging run proved
# 25s was racing the broker symbol-catalogue download on this Exness
# account, with all three Phase 5 keystroke attempts then dispatched
# against a still-initialising main window. The early-exit gate keeps
# healthy boots fast (the gate typically fires within 5-15s) while
# giving slow brokers and slow disks enough headroom not to race.
AUTO_LOGIN_PHASE5_POST_LOGIN_SETTLE_SECS="${AUTO_LOGIN_PHASE5_POST_LOGIN_SETTLE_SECS:-60}"
AUTO_LOGIN_PHASE5_CHART_WINDOW_WAIT_SECS="${AUTO_LOGIN_PHASE5_CHART_WINDOW_WAIT_SECS:-20}"
AUTO_LOGIN_PHASE5_CHART_WINDOW_TITLE_REGEX="${AUTO_LOGIN_PHASE5_CHART_WINDOW_TITLE_REGEX:-^[A-Za-z0-9._#@!^+\-]+,[A-Za-z][0-9]+}"
AUTO_LOGIN_PHASE5_BIND_WAIT_SECS="${AUTO_LOGIN_PHASE5_BIND_WAIT_SECS:-30}"
AUTO_LOGIN_PHASE5_INTER_ATTEMPT_SECS="${AUTO_LOGIN_PHASE5_INTER_ATTEMPT_SECS:-5}"
# Deterministic-attach wait. After login is confirmed and the bundle's
# Profiles/Default workspace has been stripped on overlay, MT5 should
# cold-boot a fresh chart from startup.ini [Charts] Template=expert and
# the EA should bind :5555 on its own with NO keystrokes. Poll :5555
# for this long before falling back to the Phase 5 keystroke cascade.
# 60s covers MT5's post-login chart open + EA OnInit on a fresh prefix.
AUTO_LOGIN_DETERMINISTIC_BIND_WAIT_SECS="${AUTO_LOGIN_DETERMINISTIC_BIND_WAIT_SECS:-60}"
# Budget guard: how much of the AUTO_LOGIN_TOTAL_BUDGET_SECS must be
# reserved for Phase 4's poll-for-remainder loop. When the total
# budget is about to be exhausted, Phase 5 skips remaining attempts
# and falls through so Phase 4 can observe a late :5555 LISTEN that
# occurs after Phase 5's chart-open keystrokes (chart open is fast
# but the EA's OnInit + bind can lag a few seconds on a slow
# wineprefix). 30s default leaves comfortable margin without
# starving Phase 5 of attempt budget.
AUTO_LOGIN_PHASE5_BUDGET_GUARD_SECS="${AUTO_LOGIN_PHASE5_BUDGET_GUARD_SECS:-30}"

# _drv_find_chart_window: search Xvfb for an open MT5 chart window.
# Returns the WID or empty. The MT5 chart title format is
# '<SYMBOL>,<TIMEFRAME>' which is unambiguous against the main UI
# window title ('MetaTrader 5 - Netting' or '<login> -   - Netting'),
# the Login dialog ('Login'), the Welcome modal ('Welcome to
# LiveUpdate'), the symbol-picker submenu (transient, no WM_NAME
# under fluxbox), and Phase 4's follow-up windows.
_drv_find_chart_window() {
  _drv_find_window_by_regex "$AUTO_LOGIN_PHASE5_CHART_WINDOW_TITLE_REGEX"
}

# _drv_phase5_mql5_logs_present: returns 0 (true) if any *.log file
# exists under the MT data directory's MQL5/Logs (or MQL4/Logs for
# MT4) subdirectory.
#
# Why this is a deterministic readiness signal
# --------------------------------------------
# MT5 creates MQL5/Logs/<YYYYMMDD>.log the first time ANY MQL5
# program (EA, indicator, script) writes a Print()/Comment()/Alert
# line, OR when the terminal itself writes the daily Experts-tab log
# header. Both happen ONLY after MT5 has finished its post-login
# internal setup (broker handshake, Toolbox panel construction,
# Experts subsystem boot). If MQL5/Logs/ has at least one file, MT5
# has either:
#   * already loaded an EA on a default chart MT5 opened on its own
#     (in which case :5555 is seconds away and Phase 5 is
#     unnecessary), or
#   * finished initialising to the point where it CAN load an EA the
#     moment a chart is opened (in which case Phase 5 keystrokes
#     will actually be processed productively).
#
# This is observable via the same PVC-backed MT data directory the
# entrypoint already populates ($MT_DIR is in scope inside
# auto_login_driver because the entrypoint resolves it before forking
# the driver). No xdotool involved; pure filesystem check.
_drv_phase5_mql5_logs_present() {
  local _logs_dir
  if [ "${MT_PLATFORM:-mt5}" = "mt4" ]; then
    _logs_dir="$MT_DIR/MQL4/Logs"
  else
    _logs_dir="$MT_DIR/MQL5/Logs"
  fi
  # ls -1 inside a non-existent directory returns 2 and prints to
  # stderr; we suppress both. The wildcard expands ONLY when the
  # directory exists AND contains at least one .log file, in which
  # case ls prints the names and exits 0.
  ls -1 "$_logs_dir"/*.log >/dev/null 2>&1
}

# _drv_phase5_welcome_modal_seen: returns 0 (true) if the currently-
# active window is the 'Welcome to LiveUpdate' post-login modal.
#
# Why this is a deterministic readiness signal
# --------------------------------------------
# MT5 build 5836 surfaces the 'Welcome to LiveUpdate' modal at the
# tail of its post-login synchronous work (broker access-server
# handshake complete, account profile loaded, Toolbox panel
# constructed). The exact moment this modal appears is the moment
# MT5 is ready to process keystroke-driven menu / hotkey commands.
# The 2026-06-24 18:11 staging run captured this modal at WID=12582941
# inside the Phase 5 settle loop -- proving the signal exists; we
# just were not gating on it.
#
# This helper is intended to be polled from the settle loop. The
# caller turns the observation into a sticky flag: once true, exit
# the settle (the modal-clear helper inside each attempt will
# dismiss the modal a moment later). Same getactivewindow +
# getwindowname path the modal-clear helper uses, so the two never
# disagree on whether the modal is present.
_drv_phase5_welcome_modal_seen() {
  local _awid _aname
  _awid=$(DISPLAY=:99 _xdo getactivewindow 2>/dev/null || echo "")
  if [ -z "$_awid" ]; then
    return 1
  fi
  _aname=$(DISPLAY=:99 _xdo getwindowname "$_awid" 2>/dev/null || echo "")
  case "$_aname" in
    Welcome\ to\ LiveUpdate*) return 0 ;;
    *) return 1 ;;
  esac
}

# _drv_wait_for_chart_window: poll _drv_find_chart_window until
# visible or budget exhausted. Echoes WID on success, returns 0;
# returns 1 on timeout. Same shape as _drv_wait_for_dialog so Phase 5
# is symmetric with Phase 2c.
_drv_wait_for_chart_window() {
  local _budget="$1"
  local _waited=0 _wid
  while [ "$_waited" -lt "$_budget" ]; do
    _wid=$(_drv_find_chart_window)
    if [ -n "$_wid" ]; then
      printf '%s' "$_wid"
      return 0
    fi
    sleep 1
    _waited=$(( _waited + 1 ))
  done
  return 1
}

# _drv_phase5_attempt: drive ONE keystroke sequence to open a chart
# and wait for the chart window to appear. Helper used by
# _drv_phase5_chart_attach below for the 3-attempt cascade.
#
# Contract:
#   * $1 = main UI window WID (focus target).
#   * $2 = attempt label (for logging).
#   * $3 = keystroke sequence as a space-separated list of xdotool
#          key tokens (e.g. 'ctrl+m Tab Home Return'). Each token is
#          dispatched in sequence with a small inter-keystroke settle.
#          Tokens containing '+' are xdotool key chords; bare tokens
#          are single keys.
#   Returns 0 if a chart window appears within the budget; 1 if not.
_drv_phase5_attempt() {
  local _mwid="$1"
  local _label="$2"
  local _seq="$3"
  local _tok _chart_wid

  _drv_log "phase5: ${_label}: clearing modals + activating main window"
  _drv_clear_modals_for_main_window "$_mwid"
  DISPLAY=:99 _xdo windowactivate "$_mwid" 2>/dev/null || true
  sleep 0.4
  DISPLAY=:99 _xdo keyup Shift Control Alt Meta 2>/dev/null || true

  _drv_log "phase5: ${_label}: dispatching keystroke sequence [${_seq}]"
  for _tok in $_seq; do
    DISPLAY=:99 _xdo key --clearmodifiers "$_tok" 2>/dev/null || true
    # Longer settle for Ctrl+M (Market Watch panel materialisation)
    # and Menu (context menu unfurl); shorter for arrow keys.
    case "$_tok" in
      ctrl+m|Menu) sleep 1.0 ;;
      alt+f)        sleep 0.5 ;;
      *)            sleep 0.3 ;;
    esac
  done

  _chart_wid=$(_drv_wait_for_chart_window "$AUTO_LOGIN_PHASE5_CHART_WINDOW_WAIT_SECS")
  if [ -n "$_chart_wid" ]; then
    _drv_log "phase5: ${_label}: chart window WID=${_chart_wid} visible after keystroke sequence"
    return 0
  fi
  _drv_warn "phase5: ${_label}: no chart window appeared within ${AUTO_LOGIN_PHASE5_CHART_WINDOW_WAIT_SECS}s"
  # Close any half-opened menu/panel before the next attempt so a
  # stuck UI state does not absorb the next keystroke. Escape closes
  # context menus; a second Escape closes the File menu if open.
  DISPLAY=:99 _xdo key --clearmodifiers Escape 2>/dev/null || true
  sleep 0.3
  DISPLAY=:99 _xdo key --clearmodifiers Escape 2>/dev/null || true
  sleep 0.3
  return 1
}

# _drv_phase5_chart_attach: open a chart on the broker-default Market
# Watch symbol via menu-driven File -> New Chart navigation so MT5's
# startup.ini-pinned 'Template=expert' directive auto-applies the EA
# template, the EA's OnInit runs, and the EA binds tcp://*:5555.
#
# Why this exists
# ---------------
# On build 5836 + /portable + a fresh Wine prefix, MT5 does NOT open
# a chart on its own after login. The empirical signature is the
# window title '<login> -   - Netting' (account window with the
# symbol slot blank), no MQL5/Logs directory, and :5555 never
# LISTENing past the 240s auto-login budget.
#
# Why Ctrl+M Market Watch (not Ctrl+N, not Alt+F primary)
# -------------------------------------------------------
# Ctrl+N is the Navigator panel toggle in MT5 (the EA/Indicator tree
# docked widget), NOT a New Chart hotkey. The 2026-06-24 15:14 staging
# diagnostic confirmed Ctrl+N does nothing useful for chart-attach.
#
# Ctrl+M opens the Market Watch panel -- empirically verified by the
# operator on real MT5 build 5836 (2026-06-24 16:45). Market Watch
# is a flat list of broker symbols. Pressing Return on a focused
# Market Watch row triggers MT5's default action, which ships as
# 'Chart Window' (opens a new chart) on every fresh MT5 install per
# MetaQuotes documentation. This is broker-agnostic: whatever symbol
# the broker put first in Market Watch is what the chart opens on.
#
# Alt+F + File menu navigation is the secondary mechanism. It was
# the v2 primary but relied on Win32 menu-position assumptions that
# were never empirically verified against build 5836. Retained as
# the last-resort attempt because it costs nothing.
#
# How it works
# ------------
# 1. Wait AUTO_LOGIN_PHASE5_POST_LOGIN_SETTLE_SECS for MT5's post-
#    login synchronous work to complete (broker access-server
#    handshake, Market Watch symbol-catalogue download, Welcome-to-
#    LiveUpdate modal materialisation). During this window the
#    modal-clear helper sweeps any blocking modal.
# 2. Re-check :5555. On the subsequent-boot accounts.dat path the
#    EA may already be bound; we exit success without keystroking
#    so a healthy session is never disturbed.
# 3. Three-attempt cascade, ordered by empirical certainty. Each
#    attempt:
#    - Re-clears modals + re-activates main window.
#    - Dispatches a keystroke sequence.
#    - Waits AUTO_LOGIN_PHASE5_CHART_WINDOW_WAIT_SECS for a chart
#      window matching '<SYMBOL>,<TIMEFRAME>' to appear.
#    - On timeout: sends Escape twice to close any half-opened
#      menu/panel then proceeds to the next attempt.
#
#    Attempt 1 (highest certainty): Ctrl+M + default action.
#      ctrl+m Tab Home Return
#      - Ctrl+M opens Market Watch panel (verified working).
#      - Tab moves focus into the Market Watch list.
#      - Home selects the first row (deterministic; no positional
#        guessing).
#      - Return triggers MT5's default Market Watch action which is
#        'Chart Window' out of the box (per MetaQuotes docs).
#
#    Attempt 2 (high certainty): Ctrl+M + keyboard context menu.
#      ctrl+m Tab Home Menu Down Return
#      - Same Ctrl+M + Tab + Home as Attempt 1 to focus the first
#        Market Watch row.
#      - Menu key (XKB keysym, dedicated context-menu key on PC
#        keyboards) opens the right-click context menu in place.
#      - Down moves from 'New Order' (position 1) to 'Chart Window'
#        (position 2) per MetaQuotes default menu order.
#      - Return activates Chart Window.
#      This is the keyboard-equivalent of the operator's manual
#      verification workflow ('right-click symbol -> Chart Window').
#
#    Attempt 3 (last resort): Alt+F + File menu navigation.
#      alt+f Right Right Return
#      - Retained from v2 verbatim as a defence-in-depth fallback
#        for the rare case where both Ctrl+M paths fail (e.g.
#        Market Watch panel is empty post-login because the broker
#        symbol-catalogue download has not yet completed).
#
# 4. MT5 auto-applies startup.ini [Charts] Template=expert to the
#    newly-opened chart -- per MetaQuotes the directive applies to
#    charts opened both at startup AND interactively post-startup.
#    The pre-staged expert.tpl loads ZeroMQ_EA, OnInit runs, and the
#    EA binds tcp://*:5555.
# 5. Poll :5555 LISTEN for AUTO_LOGIN_PHASE5_BIND_WAIT_SECS. On bind
#    we exit success; on timeout we fall through to Phase 4 which
#    keeps polling the remaining budget.
#
# Contract
# --------
#   * $1 = main UI window WID (used only for focus clearing).
#   * Best-effort: every failure logs WARN and returns 1; the caller
#     (auto_login_driver) MUST treat a non-zero return as 'try harder
#     in Phase 4', never as fatal.
#   * Idempotent: re-running on an already-:5555-LISTEN pod is a
#     no-op (early return at step 2).
#   * Never logs credentials. Logs only WIDs, names, attempt labels,
#     keystroke sequences, and durations.
# _drv_phase5_budget_exhausted: returns 0 (true) if the remaining
# total auto-login budget is below AUTO_LOGIN_PHASE5_BUDGET_GUARD_SECS,
# 1 (false) otherwise. Used as a gate before each Phase 5 attempt
# and inside each :5555 poll loop so Phase 5 never consumes the
# budget reserved for Phase 4's final poll-for-remainder.
#
# Contract:
#   * $1 = auto_login_driver's start_ts (UNIX seconds).
_drv_phase5_budget_exhausted() {
  local _start_ts="$1"
  local _now _elapsed _remaining
  _now=$(date +%s)
  _elapsed=$(( _now - _start_ts ))
  _remaining=$(( AUTO_LOGIN_TOTAL_BUDGET_SECS - _elapsed ))
  if [ "$_remaining" -le "$AUTO_LOGIN_PHASE5_BUDGET_GUARD_SECS" ]; then
    return 0
  fi
  return 1
}

# _drv_phase5_poll_bind: poll :5555 LISTEN for up to either
# AUTO_LOGIN_PHASE5_BIND_WAIT_SECS OR until the budget guard fires,
# whichever is shorter. Returns 0 on LISTEN observed, 1 on timeout.
# Used by each Phase 5 attempt instead of an inline while loop.
#
# Contract:
#   * $1 = start_ts (UNIX seconds) for budget guard.
#   * $2 = attempt label for logging.
_drv_phase5_poll_bind() {
  local _start_ts="$1"
  local _label="$2"
  local _waited=0
  while [ "$_waited" -lt "$AUTO_LOGIN_PHASE5_BIND_WAIT_SECS" ]; do
    if _drv_zmq_bound; then
      _drv_log "phase5: :5555 LISTEN at +${_waited}s after ${_label}; EA OnInit succeeded"
      return 0
    fi
    if _drv_phase5_budget_exhausted "$_start_ts"; then
      _drv_warn "phase5: ${_label}: budget guard fired (remaining < ${AUTO_LOGIN_PHASE5_BUDGET_GUARD_SECS}s); yielding to Phase 4"
      return 1
    fi
    sleep 1
    _waited=$(( _waited + 1 ))
  done
  return 1
}

_drv_phase5_chart_attach() {
  local _mwid="$1"
  local _start_ts="$2"
  local _waited=0

  if [ "${AUTO_LOGIN_PHASE5_ENABLED}" != "1" ]; then
    _drv_log "phase5: disabled via AUTO_LOGIN_PHASE5_ENABLED=${AUTO_LOGIN_PHASE5_ENABLED}"
    return 1
  fi

  if [ -z "$_mwid" ]; then
    _drv_warn "phase5: no main window WID provided; cannot drive menu navigation"
    return 1
  fi

  if [ -z "$_start_ts" ]; then
    _drv_warn "phase5: no start_ts provided; budget guard disabled"
    _start_ts=$(date +%s)
  fi

  # Subsequent-boot short-circuit BEFORE the long settle so the
  # accounts.dat fast path is not delayed.
  if _drv_zmq_bound; then
    _drv_log "phase5: :5555 already LISTEN (accounts.dat fast path); skipping chart-attach"
    return 0
  fi

  _drv_log "phase5: settling up to ${AUTO_LOGIN_PHASE5_POST_LOGIN_SETTLE_SECS}s (early-exit on :5555 LISTEN | MQL5/Logs present | Welcome modal observed)"
  # Settle in 1s chunks so we can early-exit on the first
  # deterministic readiness signal AND log progress to an operator-
  # readable cadence. Budget-guarded so the settle cannot consume the
  # Phase 4 reservation.
  #
  # Three early-exit signals, polled every second:
  #
  #   (1) :5555 LISTEN -- EA already bound (accounts.dat fast path or
  #       a broker that auto-opened a chart). Phase 5 is unnecessary;
  #       return 0 immediately so Phase 4 short-circuits to success.
  #
  #   (2) MQL5/Logs/<date>.log exists -- MT5 has finished post-login
  #       internal setup (broker handshake, Toolbox panel, Experts
  #       subsystem) and either already ran an EA OnInit on a chart
  #       it opened itself, or is now capable of running one. Exit
  #       the settle EARLY (do not return) so the keystroke cascade
  #       runs against an actually-ready MT5.
  #
  #   (3) 'Welcome to LiveUpdate' modal observed -- broker handshake
  #       completed enough to surface the post-login modal. Sticky:
  #       once seen, the loop breaks (the dismissal happens inside
  #       _drv_phase5_attempt's modal-clear helper). Exit the settle
  #       EARLY so the cascade runs while the main UI is reachable.
  #
  # When NO signal fires within the upper-bound budget, the cascade
  # still runs (preserving the previous best-effort posture) but the
  # operator gets a clear log line explaining that no readiness
  # signal was observed.
  local _welcome_seen=0
  local _exit_reason=""
  while [ "$_waited" -lt "$AUTO_LOGIN_PHASE5_POST_LOGIN_SETTLE_SECS" ]; do
    if _drv_zmq_bound; then
      _drv_log "phase5: :5555 LISTEN at +${_waited}s during post-login settle; skipping chart-attach"
      return 0
    fi
    if _drv_phase5_mql5_logs_present; then
      _exit_reason="MQL5/Logs present"
      break
    fi
    if [ "$_welcome_seen" -eq 0 ] && _drv_phase5_welcome_modal_seen; then
      _welcome_seen=1
      _exit_reason="Welcome modal observed"
      break
    fi
    if _drv_phase5_budget_exhausted "$_start_ts"; then
      _drv_warn "phase5: budget guard fired during settle (remaining < ${AUTO_LOGIN_PHASE5_BUDGET_GUARD_SECS}s); yielding to Phase 4"
      return 1
    fi
    sleep 1
    _waited=$(( _waited + 1 ))
  done
  if [ -n "$_exit_reason" ]; then
    _drv_log "phase5: settle early-exit at +${_waited}s (${_exit_reason}); proceeding to keystroke cascade"
  else
    _drv_warn "phase5: settle upper bound (${AUTO_LOGIN_PHASE5_POST_LOGIN_SETTLE_SECS}s) reached without any readiness signal; proceeding to keystroke cascade anyway (best-effort)"
  fi

  # Attempt 1: Ctrl+M Market Watch + default action (highest certainty).
  if _drv_phase5_attempt "$_mwid" "attempt 1 (Ctrl+M default action)" "ctrl+m Tab Home Return"; then
    if _drv_phase5_poll_bind "$_start_ts" "attempt 1"; then
      return 0
    fi
    _drv_warn "phase5: attempt 1: chart opened but :5555 not bound within budget; falling through to next attempt"
  fi

  if _drv_phase5_budget_exhausted "$_start_ts"; then
    _drv_warn "phase5: budget guard fired before attempt 2 (remaining < ${AUTO_LOGIN_PHASE5_BUDGET_GUARD_SECS}s); yielding to Phase 4"
    return 1
  fi
  sleep "$AUTO_LOGIN_PHASE5_INTER_ATTEMPT_SECS"

  # Attempt 2: Ctrl+M Market Watch + keyboard context menu (high certainty).
  if _drv_phase5_attempt "$_mwid" "attempt 2 (Ctrl+M context menu)" "ctrl+m Tab Home Menu Down Return"; then
    if _drv_phase5_poll_bind "$_start_ts" "attempt 2"; then
      return 0
    fi
    _drv_warn "phase5: attempt 2: chart opened but :5555 not bound within budget; falling through to next attempt"
  fi

  if _drv_phase5_budget_exhausted "$_start_ts"; then
    _drv_warn "phase5: budget guard fired before attempt 3 (remaining < ${AUTO_LOGIN_PHASE5_BUDGET_GUARD_SECS}s); yielding to Phase 4"
    return 1
  fi
  sleep "$AUTO_LOGIN_PHASE5_INTER_ATTEMPT_SECS"

  # Attempt 3: Alt+F File menu navigation (last resort, defence-in-depth).
  if _drv_phase5_attempt "$_mwid" "attempt 3 (Alt+F File menu)" "alt+f Right Right Return"; then
    if _drv_phase5_poll_bind "$_start_ts" "attempt 3"; then
      return 0
    fi
    _drv_warn "phase5: attempt 3: chart opened but :5555 not bound within budget"
  fi

  _drv_err "phase5: all three attempts failed to open a chart that binds :5555; falling through to Phase 4 poll for remaining budget"
  return 1
}

# Phase 2c attempt 1: open File menu, press L mnemonic.
# Every xdotool call is timeout-bounded via _xdo; `windowactivate` is
# async (no --sync) to avoid Wine WM hangs on transient_for modals.
_drv_invoke_login_via_mnemonic() {
  local _mwid="$1"
  _drv_log "Phase 2c attempt 1: File menu mnemonic (main WID=${_mwid}, Alt+F then L)"
  _drv_clear_modals_for_main_window "$_mwid"
  DISPLAY=:99 _xdo windowactivate "$_mwid" 2>/dev/null || true
  sleep 0.3
  DISPLAY=:99 _xdo keyup Shift Control Alt Meta 2>/dev/null || true
  DISPLAY=:99 _xdo key --clearmodifiers alt+f 2>/dev/null || true
  sleep 0.4
  DISPLAY=:99 _xdo key --clearmodifiers l 2>/dev/null || true
}

# Phase 2c attempts 2 + 3: open File menu, press Down N times, Return.
# Parameter is the Down-press count. 9 is the position-stable guess
# for MT5 build 5836 (File menu items: New Chart, Open Offline, Open
# Deleted, Save As, Save As Picture, [sep], Open an Account, Open a
# Demo Account, Login to Trade Account = position 9 if Win32 skips
# separators on Down navigation, which it does by default). 10 covers
# the over-by-one case in case separator counting drifts or a
# broker-injected menu item shifts the position.
_drv_invoke_login_via_menu_n() {
  local _mwid="$1"
  local _n="$2"
  local _i
  _drv_log "Phase 2c attempt: File menu arrow navigation (main WID=${_mwid}, Alt+F then ${_n}x Down then Return)"
  _drv_clear_modals_for_main_window "$_mwid"
  DISPLAY=:99 _xdo windowactivate "$_mwid" 2>/dev/null || true
  sleep 0.3
  DISPLAY=:99 _xdo keyup Shift Control Alt Meta 2>/dev/null || true
  DISPLAY=:99 _xdo key --clearmodifiers alt+f 2>/dev/null || true
  sleep 0.4
  _i=0
  while [ "$_i" -lt "$_n" ]; do
    DISPLAY=:99 _xdo key --clearmodifiers Down 2>/dev/null || true
    sleep 0.1
    _i=$(( _i + 1 ))
  done
  DISPLAY=:99 _xdo key --clearmodifiers Return 2>/dev/null || true
}

auto_login_driver() {
  local start_ts now elapsed wid wid_first dialog_seen=0 bind_until dismiss_until fwid w wname
  local main_wid="" phase2a_deadline phase2c_attempted=0
  local hard_kill_pid="" hard_kill_budget driver_pid
  start_ts=$(date +%s)

  _drv_log "start (budget=${AUTO_LOGIN_TOTAL_BUDGET_SECS}s, login=${MT_LOGIN}, server=${MT_SERVER})"

  # Hard wall-clock kill-switch. Forked sleeper that SIGTERMs THIS
  # driver process at AUTO_LOGIN_TOTAL_BUDGET_SECS +
  # AUTO_LOGIN_HARD_KILL_GRACE_SECS. Belt-and-braces against any future
  # xdotool hang surface that escapes the per-call _xdo timeout (e.g.
  # a new code path that forgets to use _xdo, or a libX11 hang inside
  # timeout(1) itself). The supervisor reaps the driver normally; MT5
  # is unaffected.
  #
  # `$$` inside a function in bash is the parent shell PID, which IS
  # the driver subshell PID because auto_login_driver is invoked as
  # `auto_login_driver &` (a background subshell). `kill -TERM $$`
  # from the sleeper therefore targets the driver, not the entrypoint
  # supervisor.
  driver_pid=$$
  hard_kill_budget=$(( AUTO_LOGIN_TOTAL_BUDGET_SECS + AUTO_LOGIN_HARD_KILL_GRACE_SECS ))
  ( sleep "$hard_kill_budget"; kill -TERM "$driver_pid" 2>/dev/null || true ) &
  hard_kill_pid=$!
  # On any driver exit (success, timeout, internal error), reap the
  # sleeper so it does not outlive the driver. The trap also handles
  # the SIGTERM-from-self case from the sleeper itself.
  trap 'if [ -n "${hard_kill_pid:-}" ] && kill -0 "$hard_kill_pid" 2>/dev/null; then kill -KILL "$hard_kill_pid" 2>/dev/null || true; fi' EXIT TERM
  _drv_log "hard-kill watchdog armed (pid=${hard_kill_pid}, fires at +${hard_kill_budget}s)"

  # Phase 1: wait for terminal64.exe to be running.
  while :; do
    now=$(date +%s); elapsed=$(( now - start_ts ))
    if [ "$elapsed" -ge "$AUTO_LOGIN_PROCESS_WAIT_SECS" ]; then
      _drv_err "terminal binary never appeared within ${AUTO_LOGIN_PROCESS_WAIT_SECS}s; exiting"
      return 1
    fi
    if _drv_mt_proc_alive; then break; fi
    sleep 1
  done
  _drv_log "terminal process detected at +${elapsed}s"

  # Phase 2: dialog-first poll with main-window fallback.
  # ----------------------------------------------------
  # Phase 2a (dialog-first): poll up to AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS
  # for a Login-shaped dialog. This was the original design contract
  # and remains the happy path for fresh prefixes / any future MT5
  # build that restores the on-launch Login prompt.
  # Phase 2b (idempotent :5555 fast-path): exit 0 immediately on bind.
  # Phase 2c (main-window menu invocation): build-5836 + pre-staged
  # config opens the main UI directly; trigger File -> Login to Trade
  # Account via hotkey, with Alt+F menu navigation as fallback.
  # Phase 2-final: if neither yielded a dialog and the main UI is
  # also absent, keep polling until AUTO_LOGIN_DIALOG_WAIT_SECS so MT4
  # and any slow-render variant still has the original budget.
  wid_first=""
  phase2a_deadline=$(( start_ts + AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS ))
  while :; do
    now=$(date +%s); elapsed=$(( now - start_ts ))
    if [ "$elapsed" -ge "$AUTO_LOGIN_DIALOG_WAIT_SECS" ]; then
      if _drv_zmq_bound; then
        _drv_log ":5555 already LISTEN at +${elapsed}s (subsequent-boot via accounts.dat); exit success"
        return 0
      fi
      _drv_err "Login dialog never appeared within ${AUTO_LOGIN_DIALOG_WAIT_SECS}s and :5555 not bound; exiting"
      return 1
    fi
    # Subsequent-boot fast path: accounts.dat means MT5 logs in silently.
    if _drv_zmq_bound; then
      _drv_log ":5555 LISTEN at +${elapsed}s (no dialog needed; accounts.dat path); exit success"
      return 0
    fi
    # Phase 2a: look for a Login-shaped window. `xdotool search
    # --name <re>` matches the regex against window WM_NAME. We
    # restrict to visible windows so the dock / hidden helpers do
    # not match.
    wid=$(_drv_find_login_dialog)
    if [ -n "$wid" ]; then
      # Phase 2a precedence guard. On the subsequent-boot accounts.dat
      # path MT5 may briefly raise a residual Login dialog after a
      # LiveUpdate-induced restart even though the EA from boot 1 has
      # already bound :5555. Without this check the driver would
      # re-paste credentials on top of a healthy session, briefly
      # closing then re-opening the broker connection. Re-check
      # :5555 the instant we observe the dialog; if already LISTEN,
      # exit success and let Phase 4's dismiss cascade handle the
      # residual dialog (Return is its default action).
      if _drv_zmq_bound; then
        _drv_log "Login dialog WID=${wid} observed at +${elapsed}s BUT :5555 already LISTEN; treating as residual post-restart dialog (skipping Phase 3 to avoid double-paste); exit success"
        return 0
      fi
      wid_first="$wid"
      dialog_seen=1
      _drv_log "Login dialog WID=${wid} detected at +${elapsed}s"
      break
    fi
    # Phase 2c entry. Only fires once, only on MT5, and only after
    # the Phase 2a budget has elapsed without a dialog. Build 5836 is
    # the empirically-known platform that skips the prompt; MT4 stays
    # on the dialog-only path.
    if [ "$phase2c_attempted" -eq 0 ] \
       && [ "$now" -ge "$phase2a_deadline" ] \
       && [ "${MT_PLATFORM:-mt5}" = "mt5" ]; then
      main_wid=$(_drv_find_main_window)
      if [ -n "$main_wid" ]; then
        phase2c_attempted=1
        _drv_log "main UI window WID=${main_wid} detected at +${elapsed}s; entering Phase 2c (3-attempt menu invocation)"
        # Attempt 1: Alt+F then L (Win32 mnemonic).
        _drv_invoke_login_via_mnemonic "$main_wid"
        wid=$(_drv_wait_for_dialog "$AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS")
        if [ -n "$wid" ]; then
          wid_first="$wid"
          dialog_seen=1
          _drv_log "Login dialog WID=${wid} appeared after mnemonic at +$(( $(date +%s) - start_ts ))s"
          break
        fi
        _drv_warn "mnemonic Alt+F,L did not surface the Login dialog within ${AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS}s; trying 9-down menu navigation"
        # Attempt 2: Alt+F then 9x Down then Return.
        _drv_invoke_login_via_menu_n "$main_wid" 9
        wid=$(_drv_wait_for_dialog "$AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS")
        if [ -n "$wid" ]; then
          wid_first="$wid"
          dialog_seen=1
          _drv_log "Login dialog WID=${wid} appeared after 9-down menu at +$(( $(date +%s) - start_ts ))s"
          break
        fi
        _drv_warn "9-down menu navigation did not surface the Login dialog within ${AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS}s; trying 10-down menu navigation"
        # Attempt 3: Alt+F then 10x Down then Return (over-by-one defence).
        _drv_invoke_login_via_menu_n "$main_wid" 10
        wid=$(_drv_wait_for_dialog "$AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS")
        if [ -n "$wid" ]; then
          wid_first="$wid"
          dialog_seen=1
          _drv_log "Login dialog WID=${wid} appeared after 10-down menu at +$(( $(date +%s) - start_ts ))s"
          break
        fi
        _drv_err "all three Phase 2c attempts (mnemonic, 9-down menu, 10-down menu) failed to surface Login dialog; exiting (supervisor will respawn)"
        return 1
      fi
    fi
    sleep 2
  done

  # Phase 3: drive the dialog.
  # Strategy: focus the window, send Tab/Ctrl+A/type sequences through
  # the standard MT5 Login-to-Trade-Account dialog field order:
  #   1. Login (text)
  #   2. Password (text)
  #   3. Server (combobox, auto-populated from servers.dat / startup.ini)
  #   4. "Save account information" (checkbox, default OFF)
  #   5. "Login" button (Return activates)
  # We do NOT assume initial cursor focus is on the Login field;
  # Ctrl+A in whatever field is focused selects-all, and typing
  # overwrites with the value. Tab moves focus deterministically.
  #
  # Stage-by-stage focused-window logging is added at each transition.
  # If MT5 build 5836's dialog Tab order differs from our assumption,
  # the log will show the active WID name diverging from the dialog's
  # WID and an operator can read the log to pinpoint exactly which Tab
  # went wrong. Never logs $MT_PASSWORD.
  if [ "$dialog_seen" -eq 1 ]; then
    _drv_phase3_log "pre_activate"
    # Async activate (no --sync). --sync against a freshly-rendered
    # Wine dialog can hang indefinitely because Wine's WM emulation
    # does not always advance _NET_ACTIVE_WINDOW promptly on dialog
    # creation. _xdo bounds the call by AUTO_LOGIN_XDOTOOL_TIMEOUT_SECS.
    DISPLAY=:99 _xdo windowactivate "$wid_first" 2>/dev/null || true
    # Extended settle for dialog activation: Wine's Win32 dialog
    # initialization (focus assignment, control creation, default-text
    # population) needs ~1s to complete on a fresh dialog. 0.4s was
    # empirically too short under our fluxbox+Xvfb+Wine pipeline.
    sleep 1.0
    _drv_phase3_log "post_activate"
    # Clear stuck modifiers (xdotool best practice for Xvfb).
    DISPLAY=:99 _xdo keyup Shift Control Alt Meta 2>/dev/null || true

    # ── Field 1: Login (paste-then-type) ─────────────────────────────
    # The dialog opens with the Login field already focused. We do NOT tab here.
    sleep "$AUTO_LOGIN_FIELD_SETTLE_SECS"
    _drv_phase3_log "after_tab_1"
    _drv_deliver_credential "$MT_LOGIN" "login"
    _drv_phase3_log "after_login_deliver"

    # ── Field 2: Password (paste-then-type) ──────────────────────────
    # Password is piped via stdin to the paste helper (never as argv);
    # if paste fails, the typing fallback exposes it briefly in
    # xdotool's cmdline (security-strict deployments can opt out via
    # AUTO_LOGIN_INPUT_STRATEGY=paste).
    DISPLAY=:99 _xdo key --clearmodifiers Tab 2>/dev/null || true
    sleep "$AUTO_LOGIN_FIELD_SETTLE_SECS"
    _drv_phase3_log "after_tab_2"
    _drv_deliver_credential "$MT_PASSWORD" "password"
    _drv_phase3_log "after_pwd_deliver"

    # ── Field 3: Server (paste-then-type; combobox edit portion) ─────
    # MT5's Server field is an editable combobox (Win32 CBS_DROPDOWN
    # style). The edit portion accepts WM_PASTE exactly like a plain
    # edit control; MT5 reads the entry-portion text on dialog submit
    # rather than the dropdown highlight.
    DISPLAY=:99 _xdo key --clearmodifiers Tab 2>/dev/null || true
    sleep "$AUTO_LOGIN_FIELD_SETTLE_SECS"
    _drv_phase3_log "after_tab_3"
    _drv_deliver_credential "$MT_SERVER" "server"
    _drv_phase3_log "after_server_deliver"

    # ── Field 4: Save account information (checkbox) ─────────────
    # Tab to checkbox, Space to toggle ON so MT5 writes accounts.dat.
    DISPLAY=:99 _xdo key --clearmodifiers Tab 2>/dev/null || true
    sleep "$AUTO_LOGIN_FIELD_SETTLE_SECS"
    _drv_phase3_log "after_tab_4"
    DISPLAY=:99 _xdo key --clearmodifiers space 2>/dev/null || true
    sleep "$AUTO_LOGIN_FIELD_SETTLE_SECS"
    _drv_phase3_log "after_space"

    # ── Submit ───────────────────────────────────────────────────
    # Return activates the dialog's default button (the OK / Login
    # button on MT5's Login dialog).
    _drv_phase3_log "pre_submit"
    DISPLAY=:99 _xdo key --clearmodifiers Return 2>/dev/null || true
    _drv_log "credentials delivered and submitted (server=${MT_SERVER}, save-account=on, strategy=${AUTO_LOGIN_INPUT_STRATEGY})"
    sleep 1
    _drv_phase3_log "post_submit_1s"
    # Scrub the X CLIPBOARD selection so no credential residue
    # lingers in the buffer after Phase 3.
    _drv_scrub_clipboard

    # Login-success gate. Submitting the dialog does NOT mean the
    # broker authenticated the session. Confirm via the MT5 journal's
    # broker authorize/connect line before proceeding. The
    # accounts.dat fast path (:5555 already bound) short-circuits it.
    if _drv_zmq_bound; then
      _drv_log "login gate: :5555 already LISTEN (accounts.dat fast path); skipping journal wait"
    elif _drv_wait_for_login_auth "$AUTO_LOGIN_LOGIN_AUTH_WAIT_SECS" >/dev/null; then
      _drv_log "login gate: broker authentication confirmed; proceeding to chart-attach"
    else
      _drv_err "login gate: broker authentication NOT confirmed within ${AUTO_LOGIN_LOGIN_AUTH_WAIT_SECS}s (no broker connect/authorize line in the MT5 journal). Credentials may be wrong, the server name may not resolve against servers.dat, or the access-server handshake failed. Exiting so the supervisor respawns."
      return 1
    fi

    # PRIMARY chart-attach (deterministic, GUI-free). With the bundle's
    # Profiles/Default workspace stripped on overlay, MT5 cold-boots a
    # fresh chart from startup.ini [Charts] Template=expert, attaches
    # ZeroMQ_EA, and OnInit binds :5555 with no keystrokes. Poll for
    # that bind before resorting to the keystroke fallback.
    _det_waited=0
    while [ "$_det_waited" -lt "$AUTO_LOGIN_DETERMINISTIC_BIND_WAIT_SECS" ]; do
      if _drv_zmq_bound; then
        _drv_log "deterministic attach: :5555 LISTEN at +${_det_waited}s (startup.ini Template=expert applied to fresh chart); exit success"
        return 0
      fi
      if ! _drv_mt_proc_alive; then
        _drv_warn "deterministic attach: terminal exited at +${_det_waited}s; exiting (supervisor will respawn)"
        return 1
      fi
      sleep 2
      _det_waited=$(( _det_waited + 2 ))
    done
    _drv_warn "deterministic attach: :5555 not bound within ${AUTO_LOGIN_DETERMINISTIC_BIND_WAIT_SECS}s; falling back to keystroke chart-attach"

    # FALLBACK chart-attach (xdotool keystroke cascade). Only reached
    # when the deterministic path did not bind. Re-resolve main_wid
    # for the Phase 2a path.
    if [ -z "${main_wid:-}" ]; then
      main_wid=$(_drv_find_main_window) || true
    fi
    if _drv_phase5_chart_attach "$main_wid" "$start_ts"; then
      _drv_log "phase5 fallback: chart-attach succeeded; :5555 bound; exit success"
      return 0
    else
      _drv_log "phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget"
    fi
  fi

  # Phase 4: dismiss follow-up dialogs AND poll for :5555 bind. The
  # two run concurrently because a Welcome / EULA window can appear
  # while we are also waiting for the EA to bind.
  #
  # Ensure main_wid is populated so we can skip it below. In the
  # Phase 2a path (dialog detected without Phase 2c), main_wid is
  # still empty; grab it now.
  if [ -z "${main_wid:-}" ]; then
    main_wid=$(_drv_find_main_window) || true
  fi
  dismiss_until=$(( $(date +%s) + AUTO_LOGIN_FOLLOWUP_DISMISS_SECS ))
  bind_until=$(( start_ts + AUTO_LOGIN_TOTAL_BUDGET_SECS ))
  while :; do
    now=$(date +%s)
    if _drv_zmq_bound; then
      _drv_log ":5555 LISTEN at +$(( now - start_ts ))s; exit success"
      return 0
    fi
    if [ "$now" -ge "$bind_until" ]; then
      _drv_err ":5555 never bound within ${AUTO_LOGIN_TOTAL_BUDGET_SECS}s total budget; exiting"
      return 1
    fi
    if ! _drv_mt_proc_alive; then
      _drv_warn "terminal process exited while waiting for :5555 bind; exiting (supervisor will respawn)"
      return 1
    fi
    if [ "$now" -lt "$dismiss_until" ]; then
      # Look for follow-up windows that are NOT the original Login
      # dialog or the MetaTrader main window. Press Return on each
      # (default "OK/Accept" action for EULA / news / broker terms).
      fwid=$(DISPLAY=:99 xdotool search --onlyvisible --name '.+' 2>/dev/null | head -5 || true)
      if [ -n "$fwid" ]; then
        for w in $fwid; do
          [ "$w" = "$wid_first" ] && continue
          # Skip the main MT window by WID. After login the title
          # changes from 'MetaTrader 5 - Netting' to
          # '<account> - - Netting', so name-only matching is not
          # sufficient.
          [ -n "${main_wid:-}" ] && [ "$w" = "$main_wid" ] && continue
          wname=$(DISPLAY=:99 xdotool getwindowname "$w" 2>/dev/null || true)
          [ -z "$wname" ] && continue
          case "$wname" in
            'MetaTrader 5'*|'MetaTrader 4'*|*'- Netting'*|*'- Hedging'*) continue ;;
          esac
          _drv_log "dismiss follow-up window: '${wname}' (WID=${w})"
          DISPLAY=:99 xdotool windowactivate --sync "$w" 2>/dev/null || true
          sleep 0.2
          DISPLAY=:99 xdotool key --clearmodifiers Return 2>/dev/null || true
        done
      fi
    fi
    sleep 2
  done
}

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
# file's environment block (skipping the parse), or pre-create the
# file at the same path.
#
# CRITICAL: we MUST NOT bash-source this file. The Vault Agent renders
# each line as `export KEY=VALUE` with the value substituted verbatim.
# User passwords can contain $, `, $(, \, !, ${ - all of which bash
# would expand or execute on `. "$FILE"`. A password starting with $$
# (a literal double dollar) would otherwise expand to the shell's PID
# and the broker would receive a wrong password; a password containing
# `cmd` or $(cmd) would execute that command inside the pod as uid 1000
# with access to the per-tenant Vault credentials and the projected
# aud=vault SA token. Both classes are closed by parsing the file as
# pure text and never letting the shell re-evaluate the right-hand side.
#
# This parser mirrors watchdog.py::_load_vault_secrets_file exactly so
# the two consumers of the Vault-rendered file agree on its semantics.
# See docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md ("Vault credential
# shell-expansion bug") for the diagnosis and the full audit trail.
VAULT_SECRETS_FILE="${VAULT_SECRETS_FILE:-/vault/secrets/mt-credentials.env}"
if [ -r "${VAULT_SECRETS_FILE}" ]; then
  _vault_rendered_at=""
  _vault_loaded_count=0
  # Read each line as a literal string. `IFS=` + `-r` prevents word
  # splitting and backslash interpretation by `read` itself. The
  # `|| [ -n "$_line" ]` keeps the loop reading the final line when
  # the file does not end with a newline.
  while IFS= read -r _line || [ -n "$_line" ]; do
    # Strip leading whitespace.
    _line="${_line#"${_line%%[![:space:]]*}"}"
    # Skip blank lines and comments.
    case "$_line" in
      ''|\#*) continue ;;
    esac
    # Drop a single leading `export ` (the Vault template emits it).
    case "$_line" in
      'export '*)
        _line="${_line#export }"
        _line="${_line#"${_line%%[![:space:]]*}"}"
        ;;
    esac
    # Split on the FIRST '=' only.
    case "$_line" in
      *=*)
        _key="${_line%%=*}"
        _val="${_line#*=}"
        ;;
      *) continue ;;
    esac
    # Trim trailing carriage return then trailing whitespace on the value.
    _val="${_val%$'\r'}"
    _val="${_val%"${_val##*[![:space:]]}"}"
    # Strip matching single- or double-quote wrappers if present.
    case "$_val" in
      \"*\") _val="${_val#\"}"; _val="${_val%\"}" ;;
      \'*\') _val="${_val#\'}"; _val="${_val%\'}" ;;
    esac
    # Whitelist the keys we expect. Anything else is ignored so a
    # future template typo cannot pollute the engine env or leak
    # arbitrary attacker-influenced values into the process
    # environment.
    case "$_key" in
      MT_LOGIN|MT_PASSWORD|MT_ZMQ_AUTH_TOKEN|MT_VAULT_RENDERED_AT)
        # `export NAME=VALUE` with the value in a variable is NOT
        # re-parsed by bash (parameter expansion is not recursive
        # once the value is in $_val). $_val is treated as a literal
        # byte string.
        export "$_key=$_val"
        _vault_loaded_count=$(( _vault_loaded_count + 1 ))
        if [ "$_key" = "MT_VAULT_RENDERED_AT" ]; then
          _vault_rendered_at="$_val"
        fi
        ;;
    esac
  done < "${VAULT_SECRETS_FILE}"

  # Regression guard. If MT_PASSWORD starts with the entrypoint's own
  # PID, the file was sourced by something upstream (not us) and bash
  # re-expanded `$$`. Log loudly so the symptom (broker reports invalid
  # password) is never re-diagnosed at the MT5 layer again. We do not
  # modify the value here - we cannot reverse the corruption - but a
  # clear log entry plus a journal-grep is enough for an operator to
  # escalate.
  _self_pid=$$
  case "${MT_PASSWORD:-}" in
    "${_self_pid}"*)
      log WARN "MT_PASSWORD appears to start with this shell's PID (${_self_pid}). This is the historical signature of bash-source corruption of /vault/secrets/. If the broker rejects the login as 'invalid password', someone has reintroduced a shell-source pattern upstream of this entrypoint. See docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md."
      ;;
  esac
  unset _self_pid _line _key _val

  if [ -n "$_vault_rendered_at" ]; then
    log INFO "Loaded ${_vault_loaded_count} Vault-rendered credential entries (rendered_at=${_vault_rendered_at})"
  else
    log INFO "Loaded ${_vault_loaded_count} Vault-rendered credential entries from ${VAULT_SECRETS_FILE}"
  fi
  unset _vault_rendered_at _vault_loaded_count
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

# Platform-specific runtime layout. MT_DIR is resolved IN TWO STAGES:
#
#   (a) Pre-overlay default below: the generic Program Files path.
#       Used only so the Wine-prefix corruption-detect block can run
#       its 'is drive_c/windows/system32 present?' test against a
#       stable path before the broker-bundle overlay runs.
#   (b) Post-overlay actual: the BRANDED MT root (e.g. 'MetaTrader 5
#       EXNESS', 'MetaTrader 5') is resolved from /broker-bundle/ by
#       the bundle-install block further down. After the overlay
#       copies the branded tree to that branded path INSIDE the Wine
#       prefix, MT_DIR is REASSIGNED to that branded path and every
#       later step (EA copy, .set write, chart template, startup.ini,
#       MT_EXE launch) uses the branded path.
#
# MT_EXE is the binary FILENAME within MT_DIR; the same filename
# works for every broker's branded build (terminal64.exe for MT5,
# terminal.exe for MT4). What differs across brokers is the BYTES of
# that file, which is what the bundle overlay delivers.
if [ "$MT_PLATFORM" = "mt4" ]; then
  MT_DIR="$WINE_PREFIX/drive_c/Program Files (x86)/MetaTrader 4"
  MT_EXE="terminal.exe"
  EA_SRC="/opt/ea/ZeroMQ_EA.ex4"
  EA_REL_DST="MQL4/Experts/ZeroMQ_EA.ex4"
  EA_DEPS_LIBZMQ_SRC="/opt/ea/deps/mt4/libzmq.dll"
  EA_DEPS_LIBZMQ_DST_REL="MQL4/Libraries/libzmq.dll"
  EA_DEPS_INCLUDE_DST_REL="MQL4/Include"
  SET_REL_DST="MQL4/Profiles/Templates/ZeroMQ_EA.set"
  TPL_REL_DST="templates/expert.tpl"
  MT_PROGRAM_FILES_PARENT="$WINE_PREFIX/drive_c/Program Files (x86)"
else
  MT_DIR="$WINE_PREFIX/drive_c/Program Files/MetaTrader 5"
  MT_EXE="terminal64.exe"
  EA_SRC="/opt/ea/ZeroMQ_EA.ex5"
  EA_REL_DST="MQL5/Experts/ZeroMQ_EA.ex5"
  EA_DEPS_LIBZMQ_SRC="/opt/ea/deps/mt5/libzmq.dll"
  EA_DEPS_LIBZMQ_DST_REL="MQL5/Libraries/libzmq.dll"
  EA_DEPS_INCLUDE_DST_REL="MQL5/Include"
  SET_REL_DST="MQL5/Profiles/Templates/ZeroMQ_EA.set"
  TPL_REL_DST="Profiles/Templates/expert.tpl"
  MT_PROGRAM_FILES_PARENT="$WINE_PREFIX/drive_c/Program Files"
fi

# ── Wine prefix corruption auto-reset ─────────────────────────────
# A previous Pod kill mid-write can leave the prefix in an inconsistent
# state where wineserver refuses to start. Detect and reset.
#
# CRITICAL: the ONLY real corruption signal is a missing
# drive_c/windows/system32. .update-timestamp.lock is NOT a corruption
# signal: Wine writes it during normal wineboot -u and it legitimately
# survives any abrupt pod kill (SIGKILL, kubelet eviction, node
# reboot). Wiping the whole prefix on a stale lock destroys the
# LiveUpdate-applied mt5onnx64 (and the broker's trusted-device
# profile, the EA's compiled state, and the chart-template files),
# forcing MT5 to re-download LiveUpdate on the next boot and producing
# the exit-143 self-restart loop documented in
# docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md.
#
# Correct behaviour on a stale lock: delete the SINGLE lock file and
# let wineboot -u (run by the seed block below when needed, or our own
# wineserver --wait + lock removal here) reconcile the prefix. NO
# prefix wipe.
if [ -d "$WINE_PREFIX" ]; then
  if [ ! -d "$WINE_PREFIX/drive_c/windows/system32" ]; then
    log WARN "Wine prefix is missing drive_c/windows/system32; resetting (true corruption signal)"
    # $WINE_PREFIX is a subdirectory the entrypoint owns (uid 1000),
    # nested inside the PVC mount point. Clear its CONTENTS (incl.
    # dotfiles); the subdir itself is owned by us so this also works
    # under readOnlyRootFilesystem (the writable PVC backs it). We
    # never touch the mount-point parent ($WINE_PREFIX_MOUNT), which
    # is root-owned and read-only to us.
    rm -rf "${WINE_PREFIX:?}"/* "${WINE_PREFIX:?}"/.[!.]* "${WINE_PREFIX:?}"/..?* 2>/dev/null || true
  elif [ -f "$WINE_PREFIX/.update-timestamp.lock" ]; then
    log WARN "Stale wineboot lock detected at $WINE_PREFIX/.update-timestamp.lock; removing single file and reconciling (NOT wiping prefix)"
    rm -f "$WINE_PREFIX/.update-timestamp.lock" 2>/dev/null || true
    # Best-effort reconcile against the surviving prefix. -u runs in
    # update mode (~5s) and rebuilds dosdevices/* against the live
    # drive_c. If wineserver is already stopped this is a no-op.
    wineserver --wait 2>/dev/null || true
    WINEPREFIX="$WINE_PREFIX" wineboot -u 2>/dev/null || true
    WINEPREFIX="$WINE_PREFIX" wineserver --wait 2>/dev/null || true
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

# ── Start window manager (fluxbox) ────────────────────────────────
#
# Why this exists
# ---------------
# Xvfb by itself is a bare X server with no window manager. xdotool's
# windowactivate, focus tracking, and key-event delivery rely on the
# EWMH spec (the _NET_ACTIVE_WINDOW root-window property and friends)
# published by a window manager. Without a WM:
#
#   * `xdotool windowactivate <wid>` returns:
#       "Your windowmanager claims not to support _NET_ACTIVE_WINDOW,
#        so the attempt to activate the window was aborted."
#     and the window never gets keyboard focus.
#   * keystrokes sent via `xdotool key` go to whichever window holds
#     raw XSetInputFocus (usually the X root), NOT the intended
#     application window. MT5's Win32 menu system never sees Alt+F
#     because there is no focused MT5 window from X's perspective.
#
# This is the empirical failure observed on the 2026-06-24 staging
# diagnostic at 08:09 UTC: every keystroke the driver sent went into
# the void, and the Phase 2c File-menu invocation could not work
# regardless of which keystroke sequence we tried.
#
# Industry context: every commercial Wine+Xvfb MT5 VPS provider runs
# a lightweight EWMH-compliant WM under Xvfb for exactly this reason.
# fluxbox is the most common pick (ForexVPS, several MetaTrader CDN
# automation guides). It registers _NET_ACTIVE_WINDOW + _NET_SUPPORTED
# + the rest of the EWMH atom set within ~200ms of starting.
#
# Configuration
# -------------
# Headless-safe profile:
#   * No screen, no toolbar, no slit (these would render decorations
#     onto Xvfb that MT5 does not expect).
#   * No menu (Wine apps never invoke fluxbox's right-click menu).
#   * No window decorations on application windows (MT5 draws its own
#     title bar; an additional fluxbox decoration would shift the
#     content area and break xdotool coordinate math if we ever use
#     it for click automation).
#   * Focus model: ClickToFocus. We do not want sloppy/follow-mouse
#     focus because the driver-issued windowactivate is the source of
#     truth, not random mouse-positioned events from Xvfb.
#
# The config lives under $HOME/.fluxbox (uid 1000 / home is on the
# PVC under $WINE_PREFIX_MOUNT but $HOME itself is /home/mt which is
# the image-baked layer; we use /tmp/.fluxbox at runtime to satisfy
# readOnlyRootFilesystem). /tmp is the emptyDir-backed writable mount
# from the chart (helm/mt-node/templates/statefulset.yaml volumes).
FLUXBOX_CONFIG_DIR="/tmp/.fluxbox"
mkdir -p "$FLUXBOX_CONFIG_DIR"
cat > "$FLUXBOX_CONFIG_DIR/init" <<'EOF'
session.screen0.toolbar.visible: false
session.screen0.slit.autoHide: true
session.screen0.slit.maxOver: false
session.screen0.slit.placement: BottomRight
session.screen0.tab.placement: TopLeft
session.screen0.tab.width: 64
session.screen0.workspaces: 1
session.screen0.workspaceNames: Default,
session.screen0.windowPlacement: RowSmartPlacement
session.screen0.rowPlacementDirection: LeftToRight
session.screen0.colPlacementDirection: TopToBottom
session.screen0.fullMaximization: true
session.screen0.focusModel: ClickToFocus
session.screen0.followModel: Ignore
session.screen0.autoRaise: false
session.screen0.clickRaises: true
session.screen0.opaqueMove: true
session.screen0.defaultDeco: NONE
session.screen0.tab.placement: TopLeft
session.screen0.allowRemoteActions: false
session.screen0.iconbar.iconWidth: 0
session.styleFile: /usr/share/fluxbox/styles/Squared_blue
session.menuFile: /dev/null
EOF
# Empty keys file so no fluxbox keybinding can ever intercept a
# keystroke that the driver intends to deliver to MT5. The driver's
# xdotool key calls go straight through to the focused window.
: > "$FLUXBOX_CONFIG_DIR/keys"
# Empty apps file so fluxbox does not apply per-app overrides.
: > "$FLUXBOX_CONFIG_DIR/apps"
log INFO "Starting fluxbox window manager (config=$FLUXBOX_CONFIG_DIR)"
fluxbox -display "$DISPLAY" -rc "$FLUXBOX_CONFIG_DIR/init" -no-slit -no-toolbar >/dev/null 2>&1 &
WM_PID=$!
# Wait for fluxbox to publish _NET_SUPPORTED on the root window.
# xprop returns the property when the WM has finished registering its
# EWMH atoms; that is the signal xdotool needs.
_wm_ready=0
for _i in $(seq 1 "$(( WM_READY_TIMEOUT_SECS * 10 ))"); do
  if xprop -display "$DISPLAY" -root _NET_SUPPORTED 2>/dev/null \
     | grep -q '_NET_ACTIVE_WINDOW'; then
    _wm_ready=1
    break
  fi
  # Surface a clean error if fluxbox crashed during startup so the
  # operator does not have to grep through the kubelet event log.
  if ! kill -0 "$WM_PID" 2>/dev/null; then
    log FATAL "fluxbox exited during startup (pid=${WM_PID} no longer alive)"
    exit 1
  fi
  sleep 0.1
done
if [ "$_wm_ready" -ne 1 ]; then
  log FATAL "fluxbox did not publish _NET_SUPPORTED within ${WM_READY_TIMEOUT_SECS}s"
  exit 1
fi
unset _wm_ready _i
log INFO "fluxbox ready (pid=${WM_PID}); _NET_ACTIVE_WINDOW available"

# ── Broker-bundle overlay (REQUIRED; installs branded MetaTrader) ─
#
# The mt-node image no longer carries any MetaTrader install. Every
# per-tenant Pod receives the broker's BRANDED MetaTrader at runtime
# via the broker-bundle initContainer, which:
#
#   1. wgets the per-broker portable zip from R2 (pin in the broker
#      catalog, infrastructure/broker-catalog/<brand>.json).
#   2. verifies sha256 against the pin.
#   3. unpacks into the /broker-bundle emptyDir volume.
#
# This block then:
#
#   1. Finds the BRANDED MT root inside /broker-bundle/ by locating
#      the single subdirectory containing terminal64.exe (MT5) or
#      terminal.exe (MT4). The root name varies per broker:
#        - Generic MetaTrader from MetaQuotes: 'MetaTrader 5'
#        - Exness branded: 'MetaTrader 5 EXNESS'
#        - Deriv branded: 'MetaTrader 5'  (some brokers reuse the
#          generic name; only the BYTES differ)
#      We do NOT assume the root name. We discover it.
#
#   2. Resolves the destination MT_DIR to
#      <MT_PROGRAM_FILES_PARENT>/<root_basename> so the branded
#      directory name is preserved inside the Wine prefix. The launch
#      line (wine "$MT_EXE" /portable from MT_DIR) then runs the
#      BRANDED terminal64.exe / terminal.exe.
#
#   3. Idempotent overlay via sentinel '.bundle-installed-from-<sha>':
#      the overlay runs only when the sentinel is absent or carries a
#      different sha. On subsequent boots over the same PVC the
#      overlay is a no-op (the branded MT install is already in
#      place, including all per-MT5 mutations like accounts.dat and
#      the LiveUpdate-applied components).
#
#   4. After the overlay, installs the EA + libzmq.dll + Include
#      headers + EA .set into the BRANDED MT root's MQL5/Experts,
#      MQL5/Libraries, and MQL5/Include subtrees. Order matters: the
#      bundle may carry empty MQL5/* subtrees, so EA install runs
#      LAST (after the overlay copies the bundle's empty subtrees
#      in, we copy the EA on top).
#
# This block FAILS LOUDLY if /broker-bundle/ is missing or carries no
# terminal binary: the only mode in which that happens is a
# misconfigured Pod (no initContainer, or initContainer failed
# silently). The image has no MT install to fall back to, so we exit
# FATAL rather than launching a binary that does not exist.
#
# Local docker-compose / dev: the operator can mount a pre-baked
# branded MT tree at /broker-bundle/<root>/ (or skip the broker-bundle
# entirely and bake the MT install into a derived dev image).
#
# Observability: every step logs structured detail so an operator
# can deterministically diagnose a failed install from the mt-node
# container log alone, without a debug pod against the preserved PVC.
if [ ! -d "/broker-bundle" ]; then
  log FATAL "/broker-bundle volume is not present. The mt-node image no longer carries any MetaTrader install; every Pod MUST receive the branded MT at runtime via the broker-bundle initContainer. Check that the StatefulSet/Pod spec includes the broker-bundle initContainer + emptyDir + volumeMount (see helm/mt-node/templates/statefulset.yaml and src/engine/ta/broker/mt5/hosted/provisioner.py::_upsert_statefulset)."
  exit 1
fi

# Step 1: report the top-level listing of the bundle volume so the
# operator can verify the initContainer actually extracted something.
# If the initContainer wget / sha256 / unzip silently dropped to an
# empty bundle, this listing surfaces that immediately.
_bundle_top_level=$(ls -la /broker-bundle 2>&1 | tr '\n' '|' | sed 's/|$//')
log INFO "broker-bundle volume present at /broker-bundle; top-level listing: ${_bundle_top_level}"

# Step 2: locate the branded MT root inside the bundle. The bundle's
# top-level directory holds the branded MT install; its name varies
# per broker ('MetaTrader 5 EXNESS', 'MetaTrader 5', etc.). We
# discover it by finding the single subdirectory that contains the
# platform's terminal binary.
if [ "$MT_PLATFORM" = "mt4" ]; then
  _bundle_exe_name="terminal.exe"
else
  _bundle_exe_name="terminal64.exe"
fi

# find ... -maxdepth 4 covers the common 'MetaTrader 5 EXNESS/
# terminal64.exe' layout AND a hypothetical broker that nests one
# level deeper. -iname is case-insensitive because some installer
# zips capitalise the .exe.
_bundle_exe_finds=$(find /broker-bundle -maxdepth 4 -type f -iname "${_bundle_exe_name}" 2>/dev/null || true)
if [ -z "$_bundle_exe_finds" ]; then
  log FATAL "broker-bundle: no ${_bundle_exe_name} found under /broker-bundle (the initContainer extracted nothing, or the bundle layout is wrong). Re-bake the broker bundle per docs/MT5_Multi_Broker_Provisioning_Architecture.md §6 and republish the R2 zip with a fresh sha256."
  exit 1
fi
_bundle_exe_count=$(printf '%s\n' "$_bundle_exe_finds" | wc -l)
log INFO "broker-bundle: ${_bundle_exe_name} matches=${_bundle_exe_count}"
printf '%s\n' "$_bundle_exe_finds" | while IFS= read -r _line; do
  [ -n "$_line" ] || continue
  log INFO "  - ${_line}"
done
if [ "$_bundle_exe_count" -gt 1 ]; then
  log FATAL "broker-bundle: multiple ${_bundle_exe_name} candidates inside /broker-bundle (count=${_bundle_exe_count}). A healthy bundle contains exactly one branded MT install. Re-bake."
  exit 1
fi
_bundle_exe=$(printf '%s\n' "$_bundle_exe_finds" | head -n1)
_bundle_root=$(dirname "$_bundle_exe")
_bundle_root_name=$(basename "$_bundle_root")
log INFO "broker-bundle: detected branded MT root at '${_bundle_root}' (platform=${MT_PLATFORM}, root_name='${_bundle_root_name}')"

# Step 3: resolve the runtime MT_DIR to <Program Files parent>/<branded
# root name> so the branded directory layout is preserved on the Wine
# prefix. From this point onward MT_DIR points at the branded path.
MT_DIR="${MT_PROGRAM_FILES_PARENT}/${_bundle_root_name}"
log INFO "broker-bundle: post-overlay MT_DIR='${MT_DIR}'"

# Step 4: idempotent overlay via sentinel. The sentinel records the
# BUNDLE_SHA256 that produced this install; on subsequent boots over
# the same PVC the overlay is skipped when the sha matches. A catalog
# bump (new bundle for the same connection) will mismatch the
# sentinel and re-overlay, which is intentional: a fresh bundle MUST
# land on the PVC.
_sentinel_dir="$MT_DIR"
_sentinel_file="${_sentinel_dir}/.bundle-installed-from-${BUNDLE_SHA256:-unknown}"
_overlay_needed=1
if [ -f "$_sentinel_file" ] && [ -f "$MT_DIR/$MT_EXE" ]; then
  _overlay_needed=0
  log INFO "broker-bundle overlay: sentinel '${_sentinel_file}' present and ${MT_EXE} on disk; skipping overlay (idempotent)"
fi

if [ "$_overlay_needed" -eq 1 ]; then
  # Clean any stale sentinel files from a previous bundle version on
  # this PVC so 'ls .bundle-installed-from-*' is always unambiguous.
  rm -f "${_sentinel_dir}"/.bundle-installed-from-* 2>/dev/null || true
  mkdir -p "$MT_DIR"
  # cp -a preserves ownership/permissions/symlinks/timestamps. The
  # trailing '/.' copies the CONTENTS of the bundle root (so the
  # branded files land directly inside MT_DIR, not nested one level
  # deeper inside MT_DIR/<root_name>/).
  log INFO "broker-bundle overlay: cp -a '${_bundle_root}/.' -> '${MT_DIR}/'"
  if ! cp -a "${_bundle_root}/." "${MT_DIR}/"; then
    log FATAL "broker-bundle overlay: cp -a failed (src='${_bundle_root}', dst='${MT_DIR}'). The Wine prefix PVC may be full or unwritable."
    exit 1
  fi
  printf '%s\n' "${BUNDLE_SHA256:-unknown}" > "$_sentinel_file" 2>/dev/null || true
  log INFO "broker-bundle overlay: complete; sentinel written at '${_sentinel_file}'"

  # Primary deterministic chart-attach: remove the bundle's pre-baked
  # default chart workspace. MT5 restores Profiles/Default on boot
  # using the BROKER's per-chart templates and ignores our
  # startup.ini [Charts] Template=expert when a profile exists, so our
  # EA would never attach. With Profiles/Default gone, MT5 cold-boots
  # a fresh chart and applies expert.tpl (which names ZeroMQ_EA),
  # OnInit runs, and the EA binds :5555 - no GUI automation needed.
  # Runs only on (re-)overlay (sentinel-gated), so MT5's OWN saved
  # profile on subsequent boots is preserved. Profiles/Templates/
  # (expert.tpl + broker templates) and config/ are untouched.
  if [ -d "$MT_DIR/Profiles/Default" ]; then
    log INFO "broker-bundle overlay: removing bundled Profiles/Default workspace so MT5 cold-boots a fresh chart via startup.ini Template=expert (deterministic EA attach)"
    rm -rf "$MT_DIR/Profiles/Default" 2>/dev/null || true
  fi
fi

# Step 5: assert the branded terminal is now in place and grab its
# sha256 + size for the audit log. A mismatch between the bundle pin
# and the installed bytes would point at a PVC-corruption event.
if [ ! -f "$MT_DIR/$MT_EXE" ]; then
  log FATAL "broker-bundle overlay: ${MT_EXE} not present at '${MT_DIR}/${MT_EXE}' after overlay. Aborting."
  exit 1
fi
_terminal_size=$(wc -c < "$MT_DIR/$MT_EXE" 2>/dev/null || echo "?")
_terminal_sha=$(sha256sum "$MT_DIR/$MT_EXE" 2>/dev/null | awk '{print $1}')
log INFO "broker-bundle overlay summary: branded_terminal='${MT_DIR}/${MT_EXE}', size=${_terminal_size}, sha256=${_terminal_sha}, bundle_sha256=${BUNDLE_SHA256:-unset}"

unset _bundle_top_level _bundle_exe_name _bundle_exe_finds _bundle_exe_count _bundle_exe _bundle_root _bundle_root_name _sentinel_dir _sentinel_file _overlay_needed _terminal_size _terminal_sha _line

# ── Materialise MT directory layout under the branded root ────────
mkdir -p "$MT_DIR/$(dirname "$EA_REL_DST")" \
         "$MT_DIR/$(dirname "$SET_REL_DST")" \
         "$MT_DIR/$(dirname "$TPL_REL_DST")" \
         "$MT_DIR/$(dirname "$EA_DEPS_LIBZMQ_DST_REL")" \
         "$MT_DIR/$EA_DEPS_INCLUDE_DST_REL" \
         "$MT_DIR/config"

# ── Copy EA binary + dependencies (AFTER bundle overlay) ──────────
# The bundle may have shipped empty MQL{4,5}/Experts and MQL{4,5}/
# Libraries subtrees; the overlay above placed those empty trees
# into MT_DIR. We now install our EA + libzmq.dll + Include headers
# ON TOP of the overlaid tree so the branded MT loads our EA, not
# whatever happened to be in the bundle's MQL{4,5}/Experts (which is
# normally empty).
if [ -f "$EA_SRC" ]; then
  cp -f "$EA_SRC" "$MT_DIR/$EA_REL_DST"
  log INFO "EA installed: ${MT_DIR}/${EA_REL_DST}"
else
  log FATAL "EA binary not found at $EA_SRC. The image is missing /opt/ea/ZeroMQ_EA.ex{4,5}; rebuild the mt-node image."
  exit 1
fi

if [ -f "$EA_DEPS_LIBZMQ_SRC" ]; then
  cp -f "$EA_DEPS_LIBZMQ_SRC" "$MT_DIR/$EA_DEPS_LIBZMQ_DST_REL"
  log INFO "EA dep installed: libzmq.dll -> ${MT_DIR}/${EA_DEPS_LIBZMQ_DST_REL}"
else
  log FATAL "EA dep missing at $EA_DEPS_LIBZMQ_SRC; rebuild the mt-node image."
  exit 1
fi
if [ -d "/opt/ea/deps/Include/Zmq" ]; then
  cp -a "/opt/ea/deps/Include/Zmq" "$MT_DIR/$EA_DEPS_INCLUDE_DST_REL/"
  log INFO "EA dep installed: Include/Zmq -> ${MT_DIR}/${EA_DEPS_INCLUDE_DST_REL}/Zmq"
else
  log FATAL "EA dep dir missing at /opt/ea/deps/Include/Zmq; rebuild the mt-node image."
  exit 1
fi
if [ -f "/opt/ea/deps/Include/JAson.mqh" ]; then
  cp -f "/opt/ea/deps/Include/JAson.mqh" "$MT_DIR/$EA_DEPS_INCLUDE_DST_REL/JAson.mqh"
  log INFO "EA dep installed: Include/JAson.mqh -> ${MT_DIR}/${EA_DEPS_INCLUDE_DST_REL}/JAson.mqh"
else
  log FATAL "EA dep missing at /opt/ea/deps/Include/JAson.mqh; rebuild the mt-node image."
  exit 1
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
  # Pending-symbol (sentinel) boot. We must STILL attach the EA so it
  # binds :5555 -- otherwise the startupProbe on :5555 kills the pod
  # AND the engine can never resolve the real symbol (GET_ALL_SYMBOLS
  # travels over the EA's ZMQ socket, which requires the EA loaded).
  #
  # The EA is a wire-protocol adapter: its header says "Attach to any
  # chart (symbol doesn't matter)" and OnInit binds tcp://*:5555 with
  # no reference to the chart symbol. So we attach the EA WITHOUT
  # specifying any symbol -- the platform is broker-agnostic and a
  # hardcoded/placeholder symbol would fail for the ~70% of users on
  # brokers with different symbol formats. MT5 opens a chart on the
  # broker's OWN default Market Watch symbol and applies the expert
  # template, loading the EA. The engine then resolves the real
  # per-tenant symbol via GET_ALL_SYMBOLS and patches MT_SYMBOL
  # (normal two-boot).
  log INFO "MT_SYMBOL is the resolution sentinel; attaching EA on the broker's default chart (no symbol pinned) so :5555 binds"

  # Bootstrap chart template: load the EA, do NOT pin a symbol. MT5
  # applies this template to whatever default chart it opens.
  cat > "$MT_DIR/$TPL_REL_DST" <<EOF
<chart>
period=16385
<expert>
name=ZeroMQ_EA
</expert>
</chart>
EOF
  log INFO "Bootstrap chart template written (no symbol pinned)"

  cat > "$INI_FILE" <<EOF
[Common]
Login=${MT_LOGIN}
Password=${MT_PASSWORD}
Server=${MT_SERVER}
AutoConfiguration=true

[Charts]
Period=H1
Template=expert

[Experts]
AllowLive=true
AllowDllImport=true
Enabled=true
Account=${MT_LOGIN}
Profile=default
EOF
fi
log INFO "Startup config written to $INI_FILE"

# ── LiveUpdate build pin (terminal.ini) ───────────────────────────
# The only effective LiveUpdate control is the per-tenant
# NetworkPolicy egress block (chart + provisioner), NOT a config
# write. The terminal.ini LastBuildDataPath pin below is config-only
# and harmless. Resolve the running build from the journal, falling
# back to the baked MT5 build 5836 on first boot.
MT_BUILD=""
MT_JOURNAL_DIR="$MT_DIR/logs"
if [ -d "$MT_JOURNAL_DIR" ]; then
  MT_BUILD=$(grep -ahoE 'build [0-9]+ started' "$MT_JOURNAL_DIR"/*.log 2>/dev/null \
    | grep -oE '[0-9]+' | sort -rn | head -n1 || true)
fi
MT_BUILD="${MT_BUILD:-5836}"

TERMINAL_INI="$MT_DIR/config/terminal.ini"
if [ -f "$TERMINAL_INI" ]; then
  # Preserve any existing terminal.ini content but replace/append the
  # [LiveUpdate] section deterministically.
  if grep -qi '^\[LiveUpdate\]' "$TERMINAL_INI"; then
    # Drop the existing [LiveUpdate] section (from its header up to the
    # next section header or EOF), then append a clean one.
    awk 'BEGIN{skip=0}
         /^\[[Ll]ive[Uu]pdate\]/{skip=1; next}
         /^\[/{skip=0}
         skip==0{print}' "$TERMINAL_INI" > "${TERMINAL_INI}.tmp"
    mv "${TERMINAL_INI}.tmp" "$TERMINAL_INI"
  fi
  printf '\n[LiveUpdate]\nLastBuildDataPath=%s\n' "$MT_BUILD" >> "$TERMINAL_INI"
else
  cat > "$TERMINAL_INI" <<EOF
[LiveUpdate]
LastBuildDataPath=${MT_BUILD}
EOF
fi
log INFO "LiveUpdate pinned to build ${MT_BUILD} in $TERMINAL_INI ($MT_PLATFORM)"

# ── Supervised MT restart loop ───────────────────────────────────
restart_count=0
window_start=$(date +%s)

while :; do
  log INFO "Launching $MT_EXE (platform=$MT_PLATFORM, server=$MT_SERVER, login=$MT_LOGIN, symbol=$MT_SYMBOL, symbol_resolved=$SYMBOL_RESOLVED, zmq_port=$ZMQ_PORT, restart_count=$restart_count)"

  cd "$MT_DIR"
  # /portable is the only flag: it pins config to <install_dir>/config
  # (PVC-backed) so our startup.ini is read and MT5 persists
  # accounts.dat across restarts. /login /password /server are NOT
  # passed (ignored by build 5836); auto-login is driven by
  # auto_login_driver(), keeping MT_PASSWORD off the wine cmdline.
  wine "$MT_EXE" /portable &
  MT_PID=$!
  log INFO "MetaTrader PID: $MT_PID"

  # Fork the auto-login driver. Best-effort: a driver crash does NOT
  # kill MT5. The driver's return code is logged but does not affect
  # the supervisor loop; the supervisor reacts only to MT5's own exit.
  # If MT5 dies before the driver finishes, the driver detects this
  # via _drv_mt_proc_alive and exits cleanly within ~2s.
  auto_login_driver &
  DRIVER_PID=$!
  log INFO "auto-login driver PID: $DRIVER_PID"

  set +e
  wait $MT_PID
  EXIT_CODE=$?
  set -e
  MT_PID=""

  # Reap the driver. If MT5 exited before the driver finished its
  # AUTO_LOGIN_TOTAL_BUDGET_SECS budget, give it a short grace to
  # detect the dead terminal and exit on its own; SIGTERM+SIGKILL if
  # it does not. This prevents orphaned drivers from accumulating
  # across restart cycles.
  if [ -n "$DRIVER_PID" ] && kill -0 "$DRIVER_PID" 2>/dev/null; then
    log INFO "reaping auto-login driver PID=$DRIVER_PID (MT exited; driver still running)"
    for _ in $(seq 1 30); do
      kill -0 "$DRIVER_PID" 2>/dev/null || break
      sleep 0.2
    done
    if kill -0 "$DRIVER_PID" 2>/dev/null; then
      kill -TERM "$DRIVER_PID" 2>/dev/null || true
      pkill -P "$DRIVER_PID" -TERM 2>/dev/null || true
      sleep 1
      kill -KILL "$DRIVER_PID" 2>/dev/null || true
      pkill -P "$DRIVER_PID" -KILL 2>/dev/null || true
    fi
  fi
  set +e
  wait "$DRIVER_PID" 2>/dev/null
  set -e
  DRIVER_PID=""

  log WARN "MetaTrader exited with code $EXIT_CODE"

  # Layer 4 (operability): detect the LiveUpdate self-restart pattern
  # and surface it LOUDLY so this symptom is never again misdiagnosed
  # as a slow boot / login failure. exit 143 = SIGTERM (MT's own
  # self-restart to apply a LiveUpdate; also matches external SIGTERM
  # from the watchdog sidecar or kubelet preStop, which is why the
  # classifier MUST also check whether MT5 has already run past the
  # most recent LiveUpdate event before treating exit-143 as a
  # self-restart).
  #
  # Issue #3 of the 2026-06-24 staging diagnostic: the original
  # grep matched on ANY persisted 'LiveUpdate ... downloaded' line
  # in the (PVC-backed) journal. Once boot 1 ran LiveUpdate, every
  # later exit-143 (watchdog SIGTERM, kubelet preStop, ...) got
  # mis-classified as a LiveUpdate self-restart, and the supervisor
  # never incremented restart_count, never exhausted the in-pod
  # restart budget, and never let the kubelet recover the pod.
  #
  # Correct discriminator: is the LAST 'Terminal ... build NNNN
  # started' line in the journal AFTER the LAST 'LiveUpdate ...
  # downloaded successfully' line?
  #   YES -> MT5 has already booted past that LiveUpdate. Exit-143
  #          must be external. Classify as NOT LiveUpdate.
  #   NO  -> MT5 has not yet booted past the most recent LiveUpdate.
  #          Exit-143 is plausibly that LiveUpdate firing. Classify
  #          as LiveUpdate self-restart.
  IS_LIVEUPDATE_RESTART=0
  if [ "$EXIT_CODE" = "143" ]; then
    # Pick the most recent journal file. MT5 writes one .log per
    # day so this is normally only one file, but the find/sort
    # covers historical PVCs with multiple files.
    _journal_file=$(ls -t "$MT_DIR/logs/"*.log 2>/dev/null | head -n1 || true)
    if [ -n "$_journal_file" ]; then
      # tr -d '\000' strips the UTF-16 NUL bytes the MT5 journal
      # writes. grep -n prefixes each match with its line number;
      # we parse the line number with cut to compare positions.
      _last_lu_line=$(tr -d '\000' < "$_journal_file" 2>/dev/null \
        | grep -nE 'LiveUpdate.*downloaded successfully' \
        | tail -n1 | cut -d: -f1 || true)
      _last_build_line=$(tr -d '\000' < "$_journal_file" 2>/dev/null \
        | grep -nE 'Terminal[[:space:]]+MetaTrader [45].*build [0-9]+ started' \
        | tail -n1 | cut -d: -f1 || true)
      # Whether to classify as LiveUpdate self-restart:
      #   - No LiveUpdate line in journal yet -> NOT a self-restart.
      #   - LiveUpdate line exists but no later 'build started'
      #     line -> IS a self-restart (current MT5 boot has not yet
      #     run past that LiveUpdate event).
      #   - LiveUpdate line exists AND a later 'build started' line
      #     exists -> NOT a self-restart (current boot has already
      #     run past that LiveUpdate event; this exit must be
      #     external).
      if [ -n "$_last_lu_line" ]; then
        if [ -z "$_last_build_line" ] || [ "$_last_build_line" -le "$_last_lu_line" ]; then
          IS_LIVEUPDATE_RESTART=1
          log INFO "LiveUpdate self-restart detected (exit 143; LiveUpdate line ${_last_lu_line}, last build-started line ${_last_build_line:-none}). This is MetaQuotes' designed behaviour: the terminal swaps its own binary atomically and re-execs. Letting the kernel finalize the on-disk rename and relaunching cleanly. This should occur AT MOST ONCE per fresh PVC; if it loops, see docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md."
        else
          log INFO "exit 143 classified as external SIGTERM (LiveUpdate line ${_last_lu_line} predates last build-started line ${_last_build_line}; MT5 already ran past that LiveUpdate). Likely watchdog SIGTERM or kubelet preStop. Counting against in-pod restart budget."
        fi
      else
        log INFO "exit 143 classified as external SIGTERM (no LiveUpdate event in journal yet). Counting against in-pod restart budget."
      fi
    fi
  fi

  # On a genuine LiveUpdate self-restart we MUST NOT race the
  # on-disk rename: no wineserver -k, no pkill -9, no
  # restart_count increment. We just sleep the settle window and
  # relaunch into the post-update prefix on the next iteration.
  # The MT process has already exited cleanly so its wineserver +
  # helpers either drained themselves or are about to; the
  # 5-second "sleep before in-pod restart" below is replaced by
  # the LIVEUPDATE_SETTLE_SECS window. Counting this against the
  # in-pod restart budget would exhaust the budget on the very
  # FIRST boot of a fresh prefix.
  if [ "$IS_LIVEUPDATE_RESTART" = "1" ]; then
    log INFO "Waiting ${LIVEUPDATE_SETTLE_SECS}s for LiveUpdate on-disk finalize before relaunch (restart_count NOT incremented)"
    sleep "$LIVEUPDATE_SETTLE_SECS"
    continue
  fi

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
