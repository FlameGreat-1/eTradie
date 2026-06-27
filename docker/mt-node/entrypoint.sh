#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# etradie-mt-node entrypoint  (CI nudge: 2026-06-26)
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
# Note: 'Open an Account' is deliberately NOT in this regex even though
# the branded MT5 wizard window can carry that title. The Open-an-Account
# wizard is the EXCLUSIVE responsibility of _drv_handle_account_wizard
# (Phase 2a). If this regex matched the wizard, the Phase 2a loop would
# pick the wizard up as a Login dialog the moment the wizard handler
# returned (its Gate 2 short-circuits when the login-dialog regex matches
# the wizard itself), and Phase 3 would type the per-tenant Vault
# credentials into the wizard's focused field. Keep this regex strictly
# anchored to the four real Login-dialog title shapes MT5/MT4 build
# 58xx emit.
AUTO_LOGIN_DIALOG_TITLE_REGEX="${AUTO_LOGIN_DIALOG_TITLE_REGEX:-^(Login|Login to Trade Account|Authorization)}"
# Phase 2c tunables. See the contract docstring above.
#
# AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS: how long Phase 2a polls for a
#   Login-shaped dialog before falling through to Phase 2c. Sized
#   to ~10s main-UI render + ~10s LiveUpdate modal grace + 10s slack;
#   if the dialog has not appeared by then on build 5836 with
#   pre-staged config, MT5 will never prompt and Phase 2c must
#   invoke File -> Login to Trade Account explicitly.
# AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS: per-attempt wait for the
#   Login dialog after a Phase 2c invocation (mnemonic or menu). Used
#   per attempt -- after the Alt+F,L mnemonic and after each Alt+F
#   arrow-navigation fallback. (An earlier design polled after a
#   Ctrl+Shift+L hotkey; that accelerator does not exist on MT5 build
#   5836 and was removed -- see the Phase 2c evidence-basis note below.)
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
# Branded titles add an optional capitalised brand token between
# 'MetaTrader [45]' and ' - <Netting|Hedging>' (e.g.
# 'MetaTrader 5 EXNESS - Netting' on the Exness branded MT5 bundle,
# verified live in commit 3321d2e3 as WID=12582913). The brand token
# is constrained to '[A-Z][A-Za-z0-9]*' (a single capitalised
# alphanumeric word) so the regex cannot accidentally match unrelated
# child windows like 'MetaTrader 5 Help' or 'MetaTrader 5 Settings'.
#
# The login-id-keyed branch covers two distinct post-submit shapes:
#   * Intermediate (post-submit, pre-auth): '<login> -   - Netting'
#     -- empty middle field, broker session slot not yet filled.
#   * Fully logged-in: '<login> - <server> - <broker>' optionally
#     followed by ' - <SYMBOL>,<TIMEFRAME>' when a chart is open.
#     Operator-verified on Exness: '133978149 - Exness-MT5Real9 -
#     Exness Technologies Ltd' / '... - EURUSDm,H1'.
# The two login-id branches are mutually exclusive: the intermediate
# shape uses '<spaces only>' in the middle field (' +'), the
# logged-in shape requires a non-space first character ('[^ ]'). The
# empty-WM_NAME path during init / wizard is handled by
# _drv_find_main_window_by_pid as a fallback after this regex search
# returns nothing.
AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX="${AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX:-^(MetaTrader [45]( [A-Z][A-Za-z0-9]*)? - (Netting|Hedging)|[0-9]+ -  +- (Netting|Hedging)|[0-9]+ - [^ ].* - [^ ].*)}"
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
# AUTO_LOGIN_TOTAL_BUDGET_SECS=420.
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

# _drv_find_main_window_by_pid: find MT5's own window by PROCESS PID,
# independent of WM_NAME. ROOT-CAUSE FIX for the empty-WM_NAME window:
# during the first ~120s of init (and while the embedded 'Open an
# Account' wizard is up) MT5's main window has an EMPTY WM_NAME, so the
# title-regex search in _drv_find_main_window matches nothing. xdotool
# `search --pid` matches by the owning process, which works regardless
# of title.
#
# Selection rule:
#   * Prefer the currently-active window IF it belongs to the MT
#     process -- that is the window the wizard / login UI is painted in
#     (the instrumented 2026-06-26 12:07 capture showed the active
#     WID=12582936 with name='' was exactly this window).
#   * Otherwise pick the largest visible window owned by the MT PID
#     (the MDI frame, not a transient zero-size child).
# Echoes the WID on stdout (empty if the MT process / no window yet).
_drv_find_main_window_by_pid() {
  local _pids _pid _wids _w _awid _geo _area _best _best_area _ww _wh
  if [ "${MT_PLATFORM:-mt5}" = "mt4" ]; then
    _pids=$(pgrep -f 'terminal\.exe' 2>/dev/null || true)
  else
    _pids=$(pgrep -f 'terminal64\.exe' 2>/dev/null || true)
  fi
  [ -n "$_pids" ] || return 1
  # Collect all visible windows owned by any MT pid.
  _wids=""
  for _pid in $_pids; do
    _w=$(DISPLAY=:99 _xdo search --onlyvisible --pid "$_pid" 2>/dev/null || true)
    [ -n "$_w" ] && _wids="$_wids $_w"
  done
  _wids=$(printf '%s\n' $_wids | awk 'NF' | sort -u)
  [ -n "$_wids" ] || return 1
  # Prefer the active window if it is one of the MT-owned windows.
  _awid=$(DISPLAY=:99 _xdo getactivewindow 2>/dev/null || echo "")
  if [ -n "$_awid" ]; then
    for _w in $_wids; do
      if [ "$_w" = "$_awid" ]; then
        printf '%s' "$_awid"
        return 0
      fi
    done
  fi
  # Else pick the largest-area MT-owned window (the MDI frame).
  _best=""; _best_area=0
  for _w in $_wids; do
    _geo=$(DISPLAY=:99 _xdo getwindowgeometry --shell "$_w" 2>/dev/null || true)
    _ww=$(printf '%s\n' "$_geo" | sed -n 's/^WIDTH=//p' | head -1)
    _wh=$(printf '%s\n' "$_geo" | sed -n 's/^HEIGHT=//p' | head -1)
    [ -n "$_ww" ] && [ -n "$_wh" ] || continue
    _area=$(( _ww * _wh ))
    if [ "$_area" -gt "$_best_area" ]; then
      _best_area=$_area; _best=$_w
    fi
  done
  [ -n "$_best" ] && { printf '%s' "$_best"; return 0; }
  # Fallback: first window owned by the MT pid.
  printf '%s' "$(printf '%s\n' $_wids | head -1)"
  return 0
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
    # Action any Welcome-to-LiveUpdate modal that surfaces during the
    # post-login broker-handshake window. MT5's post-login synchronous
    # work (broker access-server handshake, Toolbox panel construction,
    # Experts subsystem boot) frequently surfaces a pending LiveUpdate
    # modal at +20-30s after submit; while it is up, MT5's main message
    # pump is blocked and the journal authorize line is never written,
    # so this loop would time out at AUTO_LOGIN_LOGIN_AUTH_WAIT_SECS
    # (120s) with the credentials accepted but the auth gate failing
    # (NOTE.md 2026-06-26 19:41 staging run captured this exactly).
    # The handler is idempotent: returns 1 (no-op) when no modal is
    # active, returns 0 after clicking Alt+R Restart. On Restart, MT5
    # exits 143; the supervisor's LiveUpdate-self-restart classifier
    # then settles LIVEUPDATE_SETTLE_SECS and relaunches into the
    # post-update prefix, at which point the accounts.dat written by
    # Phase 3's 'Save account information' tick takes over and the
    # next driver's Phase 2a finds :5555 already LISTEN.
    _drv_handle_liveupdate_restart >/dev/null 2>&1 || true
    _title=$(_drv_active_title)
    _drv_log "login-auth wait +${_waited}s: active title='${_title}' (awaiting broker connect/authorize line in journal)"
    sleep 1
    _waited=$(( _waited + 1 ))
  done
  return 1
}

# _drv_handle_liveupdate_restart: if the CURRENTLY-ACTIVE window is the
# 'Welcome to LiveUpdate' modal ('Updates have been downloaded ... Press
# "Restart" to restart the terminal and install the updates'), click
# RESTART so MT5 applies the update and self-restarts. Returns 0 if it
# actioned the modal, 1 if the modal was not the active window.
#
# Why Restart (not Later/Escape)
# ------------------------------
# MT5 downloaded a LiveUpdate component and will not finish booting into a
# usable Login flow until it restarts to install it. 'Later'/Escape leaves
# a stale build and the modal re-nags, blocking Phase 2a indefinitely
# (observed on the 2026-06-26 staging capture: the modal sat up for the
# whole 120s dialog wait and the Login dialog never appeared). Clicking
# Restart triggers MT5's own exit 143, which the supervisor classifies as a
# LiveUpdate self-restart (settle + relaunch, NOT counted against the
# in-pod restart budget). It is one-shot per fresh PVC: the next boot has
# the update applied and proceeds to login. This therefore cannot loop.
#
# Why Alt+R
# ---------
# 'Restart' is a standard Win32 push button whose mnemonic is the
# underlined 'R' (Alt+R activates it regardless of which button currently
# holds focus). We send Alt+R first (deterministic), then a bare Return as
# a secondary in case this broker build made Restart the default button.
# All xdotool calls are timeout-bounded via _xdo and best-effort.
_drv_handle_liveupdate_restart() {
  local _awid _aname
  _awid=$(DISPLAY=:99 _xdo getactivewindow 2>/dev/null || echo "")
  [ -n "$_awid" ] || { _drv_log "liveupdate-handler: no active window (skip)"; return 1; }
  _aname=$(DISPLAY=:99 _xdo getwindowname "$_awid" 2>/dev/null || echo "")
  # Unconditional observability: log what window is active on EVERY
  # call so the Phase 2a loop's per-iteration state is visible even
  # when this handler is a no-op.
  _drv_log "liveupdate-handler: active WID=${_awid} name='${_aname}'"
  case "$_aname" in
    Welcome\ to\ LiveUpdate*)
      _drv_log "LiveUpdate modal active (WID=${_awid}); clicking Restart (Alt+R) so MT5 installs the update and self-restarts (supervisor handles exit 143)"
      DISPLAY=:99 _xdo windowactivate "$_awid" 2>/dev/null || true
      sleep 0.3
      DISPLAY=:99 _xdo keyup Shift Control Alt Meta 2>/dev/null || true
      DISPLAY=:99 _xdo key --clearmodifiers alt+r 2>/dev/null || true
      sleep 0.4
      DISPLAY=:99 _xdo key --clearmodifiers Return 2>/dev/null || true
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

# _drv_handle_account_wizard: if the CURRENTLY-ACTIVE (or first visible)
# window is MT5's 'Open an Account' first-run wizard ('Select a company to
# open an account with'), click NEXT (Alt+N) to advance it to the Login
# dialog. Returns 0 if it actioned the wizard, 1 otherwise.
#
# Confirmed flow on the branded Exness build (operator, 2026-06-26): MT5
# opens this wizard with the company already selected; pressing 'Next >'
# opens the Login-to-Trade-Account dialog. The driver must click Next or
# it sits on the wizard until the dialog-wait times out (observed: the
# wizard stayed up the whole 120s and 'Login dialog never appeared').
#
# Why this must run BEFORE _drv_find_login_dialog:
# AUTO_LOGIN_DIALOG_TITLE_REGEX matches 'Open an Account', so the wizard
# would otherwise be picked up as the Login dialog and Phase 3 would paste
# credentials into the wizard. Intercepting + advancing it here guarantees
# Phase 3 only ever sees the real Login dialog.
#
# Operator-verified ground truth (2026-06-26 09:36 capture):
#
#   - The "Select a company to open an account with" wizard is NOT a
#     separate X11 top-level window on the branded Exness build. It is
#     drawn by MT5 INSIDE the main MDI window, on top of the Market
#     Watch / Navigator / Journal panels. The full 8-minute capture
#     showed exactly ONE visible top-level window the entire time:
#       WID=12582913 name='MetaTrader 5 EXNESS - Netting'
#     so any handler that searches for a wizard-titled window will
#     never match. The wizard must be driven through the main window.
#   - Once a company is selected in the wizard, pressing Alt+N opens
#     the Login dialog (hard proof: operator's own MT5).
#
# Therefore: 'find' the wizard by finding the main MT5 window, and
# advance it by (a) clicking into the MDI client area at the wizard's
# visual center to put focus on the embedded wizard pane (otherwise
# Market Watch / Navigator hold focus), then (b) sending Alt+N to the
# focused main window. Verification = the real Login dialog appears
# as a separate top-level window (it DOES become one on this build).
# All xdotool calls are timeout-bounded via _xdo and best-effort.
_drv_find_account_wizard() {
  # The wizard is embedded in the main MT5 MDI window; reuse the
  # main-window finder so we drive the wizard through the main window.
  # This intentionally returns the main-window WID, not a separate
  # wizard WID (which does not exist on this build).
  _drv_find_main_window
}

# _drv_account_wizard_advanced: returns 0 (true) if the embedded wizard
# has advanced -- i.e. the real Login dialog has appeared as a separate
# top-level window, OR :5555 is already LISTEN (subsequent-boot fast
# path landed us past the wizard between polls). Used to VERIFY each
# advance attempt instead of firing keystrokes blindly.
_drv_account_wizard_advanced() {
  if _drv_zmq_bound; then
    return 0
  fi
  if [ -n "$(_drv_find_login_dialog)" ]; then
    return 0
  fi
  return 1
}

# _drv_account_wizard_focus_embedded: click into the main MT5 MDI client
# area at the wizard's visual center so the embedded wizard pane (not
# Market Watch / Navigator / Journal) holds focus inside MT5. Without
# this, Alt+N is dispatched to whichever child pane MT5 last focused,
# and the wizard never sees the keystroke.
#
# Geometry math: the wizard renders as a centered modal pane inside
# the MDI client area. The MDI client area sits below MT5's menu bar
# (~50 px) and above MT5's status bar (~30 px) and to the right of
# any docked Navigator panel (~200 px on default layout). The wizard
# itself is roughly centered horizontally and slightly above vertical
# center (the company row sits in the upper-middle of the wizard).
# Clicking at x = left + 55% width, y = top + 45% height lands on the
# wizard's company-list area for the default Xvfb 1024x768 layout AND
# scales with window size if MT5 ever runs at a different resolution.
_drv_account_wizard_focus_embedded() {
  local _wid="$1"
  local _geo _w _h _x _y _cx _cy
  DISPLAY=:99 _xdo windowactivate "$_wid" 2>/dev/null || true
  sleep 0.3
  # Pull window geometry. --shell emits WIDTH=, HEIGHT=, X=, Y= lines.
  # Parse defensively; fall back to the Xvfb default 1024x768 origin.
  _geo=$(DISPLAY=:99 _xdo getwindowgeometry --shell "$_wid" 2>/dev/null || true)
  if printf '%s' "$_geo" | grep -q '^WIDTH='; then
    _w=$(printf '%s\n' "$_geo" | sed -n 's/^WIDTH=//p' | head -1)
    _h=$(printf '%s\n' "$_geo" | sed -n 's/^HEIGHT=//p' | head -1)
    _x=$(printf '%s\n' "$_geo" | sed -n 's/^X=//p' | head -1)
    _y=$(printf '%s\n' "$_geo" | sed -n 's/^Y=//p' | head -1)
  fi
  _w="${_w:-1024}"; _h="${_h:-768}"; _x="${_x:-0}"; _y="${_y:-0}"
  _cx=$(( _x + (_w * 55) / 100 ))
  _cy=$(( _y + (_h * 45) / 100 ))
  _drv_log "account wizard: focusing embedded wizard pane by click at (${_cx},${_cy}) [main win ${_w}x${_h}+${_x}+${_y}]"
  DISPLAY=:99 _xdo mousemove "$_cx" "$_cy" 2>/dev/null || true
  sleep 0.2
  # Single click to focus the embedded wizard pane (do NOT double-click
  # here: a double-click on the highlighted company row could open a
  # nested 'Exness account types' sub-list instead of just focusing).
  DISPLAY=:99 _xdo click 1 2>/dev/null || true
  sleep 0.4
  return 0
}

# _drv_account_wizard_advance_attempt: ONE keystroke pass against the
# main MT5 window ($1 = main WID, $2 = log label).
#
# Strategy: PRIMARY is Alt+F, L (the operator-verified MT5 File-menu
# mnemonic that opens 'Login to Trade Account' as a separate top-level
# Login dialog from ANY wizard page). This is the broker-agnostic
# bypass that skips every wizard page -- page 1 (Select a company),
# page 2 (account-type radios: Open a demo / Open a real / Connect
# with an existing trade account), and page 3 (demo-registration
# form with First name / Second name / DOB / Email / Mobile fields
# whose Next > button is disabled until they are filled, as captured
# in the 2026-06-26 17:15 staging run and the operator screenshot).
# SECONDARY is the prior Alt+N action, kept so any future broker
# bundle that exposes a wizard where Alt+F,L is suppressed by a modal
# still has the original select-a-company -> Next advance path.
#
# The focus-click preamble is retained because some wizard pages
# (notably page 1) require focus on the embedded wizard pane before
# ANY menu keystroke is processed -- the click activates the wizard
# pane and the subsequent windowactivate ensures the main window
# receives the mnemonic. Both keystrokes go to the main window; the
# mnemonic is delivered as two consecutive xdotool 'key' calls
# (alt+f then a bare l) to match the operator's manual sequence (Alt
# held, F tapped, L tapped) verbatim, with a 0.4s settle between
# alt+f and l to cover the Wine File-menu paint window.
_drv_account_wizard_advance_attempt() {
  local _wid="$1"
  local _label="$2"
  _drv_log "account wizard advance (${_label}): focusing main window then Alt+F,L mnemonic (operator-verified File->Login to Trade Account bypass); Alt+N retained as fallback"
  _drv_account_wizard_focus_embedded "$_wid"
  # Re-activate before the mnemonic in case the click moved focus
  # into a child control we did not intend; clear any stuck
  # modifiers first so a held key from a prior attempt cannot
  # corrupt the mnemonic delivery.
  DISPLAY=:99 _xdo windowactivate "$_wid" 2>/dev/null || true
  sleep 0.2
  DISPLAY=:99 _xdo keyup Shift Control Alt Meta 2>/dev/null || true
  # PRIMARY: Alt+F, L (operator-verified, 2026-06-26). Opens MT5's
  # File menu via the Win32 mnemonic, then activates 'Login to Trade
  # Account' via its L mnemonic. The Login dialog appears as a
  # separate top-level window which _drv_account_wizard_advanced
  # then verifies via _drv_find_login_dialog (regex tightened in the
  # prior commit so the wizard cannot be mis-matched as the Login
  # dialog -- only the real dialog matches).
  DISPLAY=:99 _xdo key --clearmodifiers alt+f 2>/dev/null || true
  sleep 0.4
  DISPLAY=:99 _xdo key --clearmodifiers l 2>/dev/null || true
  sleep 0.6
  # SECONDARY (defence-in-depth): Alt+N. On the historical select-a-
  # company variant this advances page 1; if the primary mnemonic
  # already opened the Login dialog, this is a no-op against the
  # already-up dialog (Alt+N has no binding on the Login dialog and
  # the dialog has no focus on the main window anyway). On any
  # build where the File menu is modal-suppressed, this preserves
  # the previous advance behaviour.
  DISPLAY=:99 _xdo windowactivate "$_wid" 2>/dev/null || true
  sleep 0.2
  DISPLAY=:99 _xdo keyup Shift Control Alt Meta 2>/dev/null || true
  DISPLAY=:99 _xdo key --clearmodifiers alt+n 2>/dev/null || true
  sleep 0.4
  return 0
}

# Master switch for the in-Phase-2a wizard handler. DEFAULT OFF.
#
# When OFF (default), Phase 2a does NOT run the wizard handler. It
# polls for the Login dialog and after AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS
# (30s default) falls through to Phase 2c which deterministically
# invokes File -> Login to Trade Account via Alt+F,L against the main
# MT5 window (after _drv_clear_modals_for_main_window Escape-dismisses
# any embedded wizard or Open-a-Demo-Account registration form). This
# is the path that was provisioning successfully before the wizard
# handler was added; the operator's 2026-06-26 17:15 staging run
# (NOTE.md) proves that an in-Phase-2a wizard handler returning 0
# every iteration starves Phase 2c and the Login dialog is never
# reached.
#
# When ON, the wizard handler runs at the top of every Phase 2a
# iteration and attempts the focus-click + Alt+F,L + Alt+N cascade
# against the wizard pane directly. Reserved for hypothetical future
# broker bundles where Phase 2c's Alt+F,L proves insufficient.
# Enable via `kubectl -n etradie-system set env statefulset/<release>
# -c mt-node AUTO_LOGIN_WIZARD_HANDLER_ENABLED=1`. No image rebuild
# required.
AUTO_LOGIN_WIZARD_HANDLER_ENABLED="${AUTO_LOGIN_WIZARD_HANDLER_ENABLED:-0}"

# _drv_handle_account_wizard: drive the embedded Open-an-Account wizard
# through the main MT5 window. Gated so it only runs when:
#   - the master switch AUTO_LOGIN_WIZARD_HANDLER_ENABLED is 1, AND
#   - the main MT5 window is visible, AND
#   - no real Login dialog is visible (so we never act after the wizard
#     already advanced), AND
#   - :5555 is NOT bound (so we never disturb a healthy session).
_drv_handle_account_wizard() {
  local _wid _i _ld _aname _aw
  # Gate 0: master switch. Default OFF so Phase 2c (the operator-
  # verified Alt+F,L path with Escape-dismiss-first via
  # _drv_clear_modals_for_main_window) is reachable after the 30s
  # phase2a_deadline. Returning 1 here makes the Phase 2a loop fall
  # through to its Phase 2c gate instead of `continue`ing.
  if [ "${AUTO_LOGIN_WIZARD_HANDLER_ENABLED:-0}" != "1" ]; then
    return 1
  fi
  # Unconditional observability: on EVERY call, log the active window
  # name so the Phase 2a loop's per-iteration state is visible even
  # when this handler is a no-op. This is what the four staging
  # captures were missing (the handler returned 1 through silent gates).
  _aw=$(DISPLAY=:99 _xdo getactivewindow 2>/dev/null || echo "")
  _aname=$([ -n "$_aw" ] && DISPLAY=:99 _xdo getwindowname "$_aw" 2>/dev/null || echo "")
  _drv_log "wizard-handler: active WID=${_aw} name='${_aname}'"
  # Gate 1: never act if :5555 is already bound (accounts.dat fast path
  # or a healthy session). The Phase 2a loop's own :5555 fast-path will
  # return success; we just bail here.
  if _drv_zmq_bound; then
    _drv_log "wizard-handler: gate1 :5555 bound; skip"
    return 1
  fi
  # Gate 2: never act if the real Login dialog is already up. Phase 2a's
  # next iteration will pick it up via _drv_find_login_dialog and Phase
  # 3 will paste credentials. NOTE: AUTO_LOGIN_DIALOG_TITLE_REGEX also
  # matches 'Open an Account', so log the matched WID+name to confirm
  # whether the embedded wizard is being mis-matched as a Login dialog.
  _ld=$(_drv_find_login_dialog)
  if [ -n "$_ld" ]; then
    _drv_log "wizard-handler: gate2 login-dialog match WID=${_ld} name='$(DISPLAY=:99 _xdo getwindowname "$_ld" 2>/dev/null || echo "")'; skip (Phase 2a will drive it)"
    return 1
  fi
  # Gate 3: only act on MT5 (wizard is build-5836 MT5 branded behaviour).
  if [ "${MT_PLATFORM:-mt5}" != "mt5" ]; then
    _drv_log "wizard-handler: gate3 platform=${MT_PLATFORM:-mt5} != mt5; skip"
    return 1
  fi
  # Find the main MT5 MDI window. Try the title-based finder first
  # (post-init / accounts.dat boots where the WM_NAME is set), then
  # fall back to the PID-based finder. ROOT CAUSE: during init and
  # while the embedded wizard is up, MT5's window has an EMPTY WM_NAME
  # (instrumented capture 2026-06-26 12:07: active WID=12582936
  # name=''), so the title search can NEVER match it; the PID finder
  # locates MT5's own window regardless of title.
  _wid=$(_drv_find_main_window)
  if [ -z "$_wid" ]; then
    _wid=$(_drv_find_main_window_by_pid)
    if [ -n "$_wid" ]; then
      _drv_log "wizard-handler: main window resolved by PID (WID=${_wid}; WM_NAME empty during init -- title search could not match)"
    fi
  fi
  [ -n "$_wid" ] || { _drv_log "wizard-handler: gate4 main MT5 window not found by title OR pid yet; defer"; return 1; }
  _drv_log "Open-an-Account wizard handler engaged via main MT5 window (WID=${_wid}); focus + Alt+N to advance to the Login dialog (verified, up to 3 attempts)"
  # Up to 3 VERIFIED attempts. Each focuses the embedded wizard pane
  # then sends Alt+N, and we confirm advance by polling for the real
  # Login dialog (which DOES appear as a separate top-level window on
  # this build) -- instead of the previous fire-once-and-hope.
  for _i in 1 2 3; do
    _drv_account_wizard_advance_attempt "$_wid" "attempt ${_i}"
    # Give the wizard a moment to transition to the Login dialog.
    sleep 2
    if _drv_account_wizard_advanced; then
      _drv_log "account wizard advanced after attempt ${_i} (Login dialog present or :5555 LISTEN)"
      return 0
    fi
    _drv_warn "account wizard still not advanced after attempt ${_i}; retrying focus + Alt+N"
  done
  _drv_warn "account wizard did not advance after 3 attempts; the Phase 2a loop will re-poll and retry next iteration"
  # Return 0 so the caller's Phase 2a loop continues (sleep 2; continue)
  # and re-polls; the next iteration re-enters this handler and retries.
  return 0
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
      *LiveUpdate*|Updates\ have\ been\ downloaded*)
        # Click Restart (Alt+R) so MT5 applies the update and self-
        # restarts; the supervisor handles the resulting exit 143.
        # Bare Return is ambiguous about which button is focused.
        DISPLAY=:99 _xdo key --clearmodifiers alt+r 2>/dev/null || true
        sleep 0.2
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
# The chart window's WM_NAME on the Exness branded build is the
# main window title WITH ' - <SYMBOL>,<TIMEFRAME>' appended (operator-
# verified: '133978149 - Exness-MT5Real9 - Exness Technologies Ltd -
# EURUSDm,H1'). We must match the SYMBOL,TIMEFRAME token wherever it
# appears in the title, not only at start-of-string. The token shape
# itself is unchanged (broker-specific suffix punctuation '.', '#',
# '_', '-', '^', '+', '@', '!' plus alphanumerics, then comma, then
# the timeframe '[A-Za-z][0-9]+'). The leading / trailing character-
# class constraints enforce a word boundary so the token cannot
# accidentally match inside a longer alphanumeric run.
AUTO_LOGIN_PHASE5_CHART_WINDOW_TITLE_REGEX="${AUTO_LOGIN_PHASE5_CHART_WINDOW_TITLE_REGEX:-(^|[^A-Za-z0-9._#@!^+\-])[A-Za-z0-9._#@!^+\-]+,[A-Za-z][0-9]+($|[^0-9])}"
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
    *LiveUpdate*|Updates\ have\ been\ downloaded*) return 0 ;;
    *) return 1 ;;
  esac
}

# ── Bundle Config-dir case resolver ───────────────────────────────
# The broker bundles are baked on case-INSENSITIVE Windows. On the
# case-SENSITIVE Linux/ext4 PVC the baked config directory may be
# 'Config' (exness mt5), 'config' (exness mt4), or BOTH as two
# distinct directories (deriv mt5). MT5/MT4 on Wine read whichever
# their build opens; our entrypoint must write startup.ini /
# terminal.ini into THAT directory or they are silently ignored.
#
# Resolve a single canonical config dir for $1 (the branded MT root):
#   * If only one case exists, echo it.
#   * If BOTH exist, canonicalize on 'Config' (the case the live MT5
#     builds in these bundles use): migrate any files unique to the
#     lowercase 'config' into 'Config', then remove the lowercase
#     duplicate so MT's read path is deterministic. Echo 'Config'.
#   * If neither exists, create 'Config' and echo it.
# Echoes the ABSOLUTE path on stdout. Idempotent.
_resolve_mt_config_dir() {
  local _root="$1"
  local _cap="$_root/Config"
  local _low="$_root/config"
  if [ -d "$_cap" ] && [ -d "$_low" ]; then
    # Merge lowercase -> Config (do not clobber existing Config files),
    # then drop the duplicate so precedence is unambiguous.
    cp -an "$_low/." "$_cap/" 2>/dev/null || true
    rm -rf "$_low" 2>/dev/null || true
    printf '%s' "$_cap"
    return 0
  fi
  if [ -d "$_low" ]; then
    printf '%s' "$_low"
    return 0
  fi
  # Default (only Config, or neither): use/create Config.
  mkdir -p "$_cap" 2>/dev/null || true
  printf '%s' "$_cap"
}

# ── Bundle overlay normalizer ─────────────────────────────────────
# Neutralizes the baked broker state that blocks deterministic EA
# attach. See the call site (inside the _overlay_needed block) for
# the full rationale (classes A/B/C). $1=branded MT root, $2=platform
# ('mt4'|'mt5'). Idempotent; safe to re-run.
_normalize_overlay() {
  local _root="$1"
  local _plat="$2"
  local _cfg _common _ai

  # (A) Strip the saved chart WORKSPACE so MT cold-boots a fresh
  #     chart that startup.ini Template=expert applies our EA to.
  #     Both the legacy <root>/Profiles/Charts and the live
  #     MQL5/Profiles/Charts copies are removed on MT5; MT4 uses a
  #     lowercase profiles/ tree with per-profile chart dirs +
  #     lastprofile.ini. Templates/ and SymbolSets/ are preserved.
  if [ "$_plat" = "mt4" ]; then
    if [ -d "$_root/profiles" ]; then
      log INFO "overlay-normalize(mt4): stripping baked profiles/* chart workspace (keeping nothing under profiles/; MT4 recreates a default profile on cold boot)"
      # MT4 stores each profile as profiles/<name>/chartNN.chr plus
      # profiles/lastprofile.ini. Remove every profile dir AND
      # lastprofile.ini so no saved workspace is restored.
      find "$_root/profiles" -mindepth 1 -maxdepth 1 \( -type d -o -name 'lastprofile.ini' \) \
        -exec rm -rf {} + 2>/dev/null || true
    fi
  else
    if [ -d "$_root/Profiles/Charts" ]; then
      log INFO "overlay-normalize(mt5): stripping baked Profiles/Charts workspace"
      rm -rf "$_root/Profiles/Charts" 2>/dev/null || true
    fi
    if [ -d "$_root/MQL5/Profiles/Charts" ]; then
      log INFO "overlay-normalize(mt5): stripping baked MQL5/Profiles/Charts workspace"
      rm -rf "$_root/MQL5/Profiles/Charts" 2>/dev/null || true
    fi
  fi

  # Resolve the canonical config dir ONCE (also de-dups Deriv's
  # Config+config). Export it so the later startup.ini / terminal.ini
  # / journal logic uses the same directory MT actually reads.
  _cfg=$(_resolve_mt_config_dir "$_root")
  MT_CONFIG_DIR="$_cfg"
  export MT_CONFIG_DIR
  log INFO "overlay-normalize: canonical config dir resolved to '${MT_CONFIG_DIR}'"

  # (B) MT5 only: DELETE the bundle's baked common.ini. Operationally
  #     verified against PREVIOUS.md (the working entrypoint before
  #     the recent refactoring): the bundle ships a foreign [Common]
  #     Login/Server/Environment that MT5 build 5836 REJECTS on a
  #     fresh Wine prefix because the Environment hash / trusted-
  #     device check fails against the per-tenant machine-id. With
  #     common.ini PRESENT, MT5 surfaces the 'Open a Demo Account'
  #     REGISTRATION FORM (page 3 of the wizard) which holds modal
  #     focus and suppresses the File menu, so Phase 2c's Alt+F,L
  #     cannot open the Login dialog (NOTE.md 2026-06-26 17:15 and
  #     18:43 staging runs both ended with 'Login dialog never
  #     appeared within 120s'). With common.ini DELETED, MT5 falls
  #     into the SHALLOWER 'Select a company' wizard (page 1) which
  #     Phase 2c's _drv_clear_modals_for_main_window Escape-dismisses
  #     before sending Alt+F,L. PREVIOUS.md proves this path works.
  #
  #     The per-tenant credentials reach the broker exclusively via
  #     Phase 3's xdotool paste into the Login dialog; MT5 then
  #     writes a fresh accounts.dat with those credentials when
  #     Phase 3 ticks 'Save account information', and every
  #     subsequent boot uses that file for silent auto-login.
  #
  #     Earlier history: commit 4c5fafe7 had this delete logic
  #     (working); bc1b96566 preserved it (still working);
  #     4b371085 reverted to PRESERVE on an incorrect theory which
  #     this commit now reverses based on operational evidence.
  if [ "$_plat" != "mt4" ]; then
    _common="$MT_CONFIG_DIR/common.ini"
    if [ -f "$_common" ]; then
      log INFO "overlay-normalize(mt5): deleting baked common.ini (foreign [Common] account context blocked by trusted-device check on fresh Wine prefix -- surfaces demo-registration wizard; MT5 recreates the file after Phase 3's per-tenant login)"
      rm -f "$_common" 2>/dev/null || true
    fi
  fi

  # (C) DELETE the baked saved-account cache for the same reason.
  #     MT5 -> accounts.dat ; MT4 -> accounts.ini. The bundle ships
  #     a saved-account record for the bundle builder's own foreign
  #     account; MT5 cannot auto-restore it on a per-tenant Wine
  #     prefix and the rejection contributes to the wizard-state
  #     drift documented above. MT5 recreates accounts.dat itself
  #     after Phase 3's first successful per-tenant login (Phase 3
  #     ticks 'Save account information'), and the PVC persists it
  #     so the subsequent-boot fast path is intact.
  if [ "$_plat" = "mt4" ]; then
    _ai="$MT_CONFIG_DIR/accounts.ini"
    if [ -f "$_ai" ]; then
      log INFO "overlay-normalize(mt4): deleting baked accounts.ini (foreign account; MT4 recreates after Phase 3's per-tenant login)"
      rm -f "$_ai" 2>/dev/null || true
    fi
  else
    if [ -f "$MT_CONFIG_DIR/accounts.dat" ]; then
      log INFO "overlay-normalize(mt5): deleting baked accounts.dat (foreign account; MT5 recreates after Phase 3's per-tenant auto-login)"
      rm -f "$MT_CONFIG_DIR/accounts.dat" 2>/dev/null || true
    fi
  fi

  # Deterministic success status. entrypoint.sh runs under `set -e`
  # and this function is invoked as a bare statement; without an
  # explicit return, a trailing `[ -f ... ]` test that evaluates
  # false (e.g. no baked accounts cache) would return non-zero and
  # abort the entrypoint. All cleanup above is best-effort by design.
  return 0
}

# ── Chart-attach evidence helpers (MQL5/Logs grep) ────────────────
# EA bind happens ONLY after chart-open -> EA-attach -> OnInit ->
# g_socket.bind(). These helpers read the EA's own Experts-tab log
# (MQL5/Logs/<date>.log for MT5, MQL4/Logs/<date>.log for MT4) so the
# keystroke-fallback decision branches on the ACTUAL chart/EA state,
# not on the coarse 'is :5555 LISTEN?' symptom. A missing bind can
# mean (a) no chart/EA yet [keystrokes help], (b) chart+EA attached
# but OnInit still running [keep waiting], or (c) chart+EA attached
# but bind FAILED [keystrokes are harmful: the EA's duplicate-instance
# guard would reject a second attach]. Only (a) is a keystroke case.
#
# The grep patterns are anchored to the EA's literal Print() strings
# from src/engine/ta/broker/mt5/zmq/ZeroMQ_EA.mq5 and the terminal's
# own Experts-tab line, both verified against a real MT5 build 5833
# journal capture:
#   S1 attach:      'expert ZeroMQ_EA (EURUSDm,H1) loaded successfully'
#   S2 bind ok:     '... [ZMQ_EA] ... === eTradie ZeroMQ Bridge Started ==='
#   S2 bind fail:   '... [ZMQ_EA] ... FATAL: Failed to bind to tcp://*:5555'
#                   '... [ZMQ_EA] ... Duplicate EA instance on port 5555 ...'
# All reads strip the UTF-16 NUL bytes the MT5 log writer emits.
_drv_mql5_logs_dir() {
  if [ "${MT_PLATFORM:-mt5}" = "mt4" ]; then
    printf '%s' "$MT_DIR/MQL4/Logs"
  else
    printf '%s' "$MT_DIR/MQL5/Logs"
  fi
}

# _drv_grep_mql5_logs: grep -aE the given ERE across the newest MQL5/
# MQL4 log file (NUL-stripped). Returns 0 on a match. Newest file
# only: the EA rewrites a fresh daily log per boot, and matching the
# newest avoids a stale match from a previous PVC boot's log.
_drv_grep_mql5_logs() {
  local _re="$1"
  local _dir _log
  _dir=$(_drv_mql5_logs_dir)
  _log=$(ls -t "$_dir"/*.log 2>/dev/null | head -n1 || true)
  [ -n "$_log" ] || return 1
  tr -d '\000' < "$_log" 2>/dev/null | grep -aqE "$_re"
}

# S1: a chart was opened AND the EA was attached to it. The terminal
# writes this Experts-tab line the instant the EA loads onto a chart,
# BEFORE OnInit's bind result is known.
_drv_chart_ea_attached() {
  _drv_grep_mql5_logs 'expert[[:space:]]+ZeroMQ_EA[[:space:]]*\(.*\)[[:space:]]+loaded successfully'
}

# S2: OnInit ran and g_socket.bind() SUCCEEDED (the EA prints the
# startup banner only on the bind-success path). Redundant safety
# signal alongside the authoritative _drv_zmq_bound port check.
_drv_ea_bind_succeeded() {
  _drv_grep_mql5_logs '\[ZMQ_EA\].*(=== eTradie ZeroMQ Bridge Started ===|Endpoint: tcp://\*:)'
}

# S2-fail: OnInit ran but g_socket.bind() FAILED, or the duplicate-
# instance guard rejected the attach. Either way a fresh chart-open
# via keystrokes cannot fix it and would stack a second EA into the
# same guard. The operator-facing remedy is DLL/AutoTrading config or
# a clean restart, not another chart.
_drv_ea_bind_failed() {
  _drv_grep_mql5_logs '\[ZMQ_EA\].*(FATAL: Failed to bind|Duplicate EA instance on port)'
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
    # Longer settle for Ctrl+M (Market Watch panel materialisation),
    # Menu (context menu unfurl), and Right (submenu render in File →
    # New Chart navigation under Wine); shorter for arrow keys / Return.
    case "$_tok" in
      ctrl+m|Menu) sleep 1.0 ;;
      alt+f|Right) sleep 0.5 ;;
      *)           sleep 0.3 ;;
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
#    Attempt 1 (recently-used path): Alt+F → New Chart → Return.
#      alt+f Right Return
#      - Alt+F opens the File menu. "New Chart" is the first item.
#      - Right enters the "New Chart" submenu. If recently-used
#        symbols exist (e.g. EURUSD at the top), they appear before
#        the category folders. Return opens a chart for the first one.
#      - On a fresh install with no recently-used symbols, Return
#        lands on the first category (which has a ► submenu arrow)
#        and enters it rather than opening a chart. Attempt 2 covers
#        this case.
#      Operator-verified on real MT5 build 5836 (2026-06-27).
#
#    Attempt 2 (first category path): Alt+F → New Chart → category → Return.
#      alt+f Right Right Return
#      - Same Alt+F + Right as Attempt 1 to enter the New Chart submenu.
#      - Second Right enters the first category's submenu (e.g.
#        "Forex Major ►" on Exness). The submenu lists individual
#        symbols (EURUSD, GBPUSD, etc.).
#      - Return opens a chart for the first symbol in that category.
#      - This is the primary path on fresh installs where no recently-
#        used symbols exist.
#      Operator-verified on real MT5 build 5836 (2026-06-27).
#
#    Attempt 3 (second category path): Alt+F → New Chart → Down → category → Return.
#      alt+f Right Down Right Return
#      - Same as Attempt 2 but Down skips to the second category row
#        before Right enters its submenu. Defence-in-depth for brokers
#        whose first category is empty or has no submenu.
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
    # Higher-priority than the readiness signal below: if a chart+EA is
    # ALREADY attached (S1) we must NOT keystroke, because opening a
    # second chart would attach a second EA that the EA's own
    # duplicate-instance guard rejects with INIT_FAILED. The bind is
    # either still in progress (OnInit) or has failed; either way the
    # correct action is to yield to the Phase 4 poll, which keeps
    # watching :5555 for the remaining budget. Returning 1 (not 0)
    # signals 'chart-attach not completed here' so the caller's Phase 4
    # loop owns the final bind verdict.
    if _drv_chart_ea_attached; then
      _drv_warn "phase5: chart+EA already attached at +${_waited}s during settle (no :5555 yet); NOT keystroking (would double-attach into the EA duplicate-instance guard); yielding to Phase 4 poll"
      return 1
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

  # Attempt 1: File → New Chart → first recently-used symbol (operator-verified).
  # alt+f opens File menu. Right enters "New Chart" submenu (first item).
  # If recently-used symbols exist at the top, Return opens a chart for
  # the first one. If only categories (with ►) are present, Return enters
  # the category submenu without opening a chart -- attempt 2 handles that.
  if _drv_phase5_attempt "$_mwid" "attempt 1 (Alt+F New Chart → recently-used)" "alt+f Right Return"; then
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

  # Attempt 2: File → New Chart → first category → first symbol (operator-verified).
  # The second Right enters the first category's submenu (e.g. "Forex Major ►").
  # Return opens a chart for the first symbol in that category.
  # On a fresh install with no recently-used symbols, this is the primary path.
  if _drv_phase5_attempt "$_mwid" "attempt 2 (Alt+F New Chart → first category)" "alt+f Right Right Return"; then
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

  # Attempt 3: File → New Chart → second category → first symbol (defence-in-depth).
  # Down skips the first category row and highlights the second. Right enters
  # its submenu. Return opens the first symbol. Covers edge cases where the
  # first category is empty or has no submenu on a particular broker.
  if _drv_phase5_attempt "$_mwid" "attempt 3 (Alt+F New Chart → second category)" "alt+f Right Down Right Return"; then
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
  local _det_waited=0
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
    # LiveUpdate gate. On a fresh prefix MT5 downloads a LiveUpdate
    # component and raises a 'Welcome to LiveUpdate ... Press Restart'
    # modal that BLOCKS the Login flow until actioned. Sweep for it on
    # every Phase 2a iteration and click Restart so MT5 installs the
    # update and self-restarts (supervisor handles exit 143, one-shot
    # per fresh PVC). Without this the modal sits up for the whole
    # AUTO_LOGIN_DIALOG_WAIT_SECS window and the Login dialog never
    # appears (2026-06-26 staging capture). After actioning, continue
    # the loop; MT5 will exit 143 and the next boot proceeds to login.
    if _drv_handle_liveupdate_restart; then
      sleep 2
      continue
    fi
    # Open-an-Account wizard gate. MT5's branded first-run flow opens an
    # 'Open an Account / Select a company' wizard that gates the Login
    # dialog: the operator-confirmed flow is select-company -> Next ->
    # Login dialog. Advance it with Alt+N here, BEFORE the login-dialog
    # detection below (the dialog regex also matches 'Open an Account',
    # so without this the wizard would be mistaken for the Login dialog
    # and Phase 3 would paste into it). After clicking Next, continue
    # the loop so the next iteration detects the real Login dialog.
    if _drv_handle_account_wizard; then
      sleep 2
      continue
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
      # Resolve the main MT5 window. Try title-based finder first
      # (post-init / accounts.dat boots where WM_NAME is set), then
      # fall back to PID-based finder. The Exness branded MT5 build
      # 5836 leaves WM_NAME EMPTY during the first ~60s of init AND
      # while the embedded Open-an-Account wizard is visible, so the
      # title regex cannot match (NOTE.md 2026-06-26 captures show
      # active WID=12582913 / 12582936 name=''). Without this PID
      # fallback, Phase 2c was never entered on the wizard-state
      # boot and the Login dialog never appeared.
      main_wid=$(_drv_find_main_window)
      if [ -z "$main_wid" ]; then
        main_wid=$(_drv_find_main_window_by_pid)
        if [ -n "$main_wid" ]; then
          _drv_log "main UI window resolved by PID (WID=${main_wid}; WM_NAME empty during init -- title regex could not match)"
        fi
      fi
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

    # ── Field 3: Save account information (checkbox) ─────────────
    # The 'Save password' checkbox is physically to the right of the Password
    # field, so the Windows Tab order hits it BEFORE the Server field.
    # We toggle it ON so MT5 writes accounts.dat.
    DISPLAY=:99 _xdo key --clearmodifiers Tab 2>/dev/null || true
    sleep "$AUTO_LOGIN_FIELD_SETTLE_SECS"
    _drv_phase3_log "after_tab_3"
    DISPLAY=:99 _xdo key --clearmodifiers space 2>/dev/null || true
    sleep "$AUTO_LOGIN_FIELD_SETTLE_SECS"
    _drv_phase3_log "after_space"

    # ── Field 4: Server (paste-then-type; combobox edit portion) ─────
    # MT5's Server field is an editable combobox (Win32 CBS_DROPDOWN
    # style) located below the Password/Checkbox row.
    DISPLAY=:99 _xdo key --clearmodifiers Tab 2>/dev/null || true
    sleep "$AUTO_LOGIN_FIELD_SETTLE_SECS"
    _drv_phase3_log "after_tab_4"
    _drv_deliver_credential "$MT_SERVER" "server"
    _drv_phase3_log "after_server_deliver"

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
    # ZeroMQ_EA, and OnInit binds :5555 with no keystrokes.
    #
    # The fallback decision is EVIDENCE-BASED, not a bare port-bind
    # timeout. EA bind happens only after chart-open -> EA-attach ->
    # OnInit -> g_socket.bind(), so a missing :5555 within the wait can
    # mean three different things, only one of which keystrokes fix:
    #   (a) no chart/EA attached yet          -> keystrokes help
    #   (b) chart+EA attached, OnInit running  -> keep waiting
    #   (c) chart+EA attached, bind FAILED     -> keystrokes HARMFUL
    #       (the EA's duplicate-instance guard rejects a 2nd attach)
    # Each poll classifies the state from the EA's own MQL5/Logs lines
    # and the /proc/net/tcp LISTEN check, and only escalates to the
    # keystroke fallback when there is genuinely no chart+EA AND no
    # bind by the end of the wait.
    _det_waited=0
    while [ "$_det_waited" -lt "$AUTO_LOGIN_DETERMINISTIC_BIND_WAIT_SECS" ]; do
      # Authoritative success: the EA's REP socket is LISTENing. The
      # bind-success log line is a redundant confirmation for slow
      # /proc visibility windows.
      if _drv_zmq_bound; then
        _drv_log "deterministic attach: :5555 LISTEN at +${_det_waited}s (startup.ini Template=expert applied to fresh chart); exit success"
        return 0
      fi
      if _drv_ea_bind_succeeded && _drv_zmq_bound; then
        _drv_log "deterministic attach: EA reported bind success at +${_det_waited}s and :5555 LISTEN; exit success"
        return 0
      fi
      # State (c): chart+EA attached but OnInit's bind FAILED. A second
      # chart-open would stack a second EA into the same duplicate-
      # instance guard (INIT_FAILED). Do NOT keystroke; surface the
      # real cause and let the supervisor respawn cleanly.
      if _drv_ea_bind_failed; then
        _drv_err "deterministic attach: EA attached to a chart but OnInit bind FAILED at +${_det_waited}s (MQL5/Logs shows 'FATAL: Failed to bind' or 'Duplicate EA instance on port'). A keystroke chart-open would stack a SECOND EA into the same duplicate-instance guard, so the keystroke fallback is intentionally skipped. Likely cause: a prior EA still holds :5555, DLL imports / automated trading disabled, or libzmq.dll failed to load. Exiting so the supervisor respawns MT5 with a clean prefix."
        return 1
      fi
      if ! _drv_mt_proc_alive; then
        _drv_warn "deterministic attach: terminal exited at +${_det_waited}s; exiting (supervisor will respawn)"
        return 1
      fi
      # State (b): chart+EA attached, OnInit still running. Observed
      # ~10s between the 'loaded successfully' line and the EA's bind
      # banner on a real MT5 build 5833 capture, so this is the
      # expected healthy-but-slow path. Keep waiting; do NOT escalate.
      if _drv_chart_ea_attached; then
        _drv_log "deterministic attach: chart+EA attached at +${_det_waited}s, OnInit still binding (no :5555 yet); waiting (NOT escalating to keystrokes)"
      fi
      sleep 2
      _det_waited=$(( _det_waited + 2 ))
    done

    # Wait elapsed without a bind. Classify ONE more time to decide
    # whether the keystroke fallback is appropriate.
    if _drv_ea_bind_failed; then
      _drv_err "deterministic attach: bind FAILED (see MQL5/Logs); skipping keystroke fallback to avoid a duplicate-instance double-attach; exiting for a clean respawn"
      return 1
    fi
    if _drv_chart_ea_attached; then
      _drv_warn "deterministic attach: chart+EA attached but :5555 not bound within ${AUTO_LOGIN_DETERMINISTIC_BIND_WAIT_SECS}s and no explicit bind-failure line. The chart-open keystroke fallback cannot help (a chart+EA already exists); yielding to the Phase 4 poll for the remaining budget in case OnInit binds late."
    else
      _drv_warn "deterministic attach: NO chart+EA attached and :5555 not bound within ${AUTO_LOGIN_DETERMINISTIC_BIND_WAIT_SECS}s; engaging keystroke chart-attach fallback (genuine no-chart state)"
      # FALLBACK chart-attach (xdotool keystroke cascade). Only reached
      # when there is genuinely no chart+EA attached. Re-resolve
      # main_wid for the Phase 2a path. Title finder first, then the
      # PID-based finder (MT5's window may still have an empty WM_NAME).
      if [ -z "${main_wid:-}" ]; then
        main_wid=$(_drv_find_main_window) || true
        [ -n "${main_wid:-}" ] || main_wid=$(_drv_find_main_window_by_pid) || true
      fi
      # Final guard against a race: a chart+EA may have attached in the
      # interval between the check above and here. Re-check so the
      # cascade never double-attaches.
      if _drv_chart_ea_attached; then
        _drv_log "phase5 fallback: chart+EA attached just before cascade dispatch; skipping keystrokes and yielding to Phase 4 poll"
      elif _drv_phase5_chart_attach "$main_wid" "$start_ts"; then
        _drv_log "phase5 fallback: chart-attach succeeded; :5555 bound; exit success"
        return 0
      else
        _drv_log "phase5 fallback: chart-attach did not bind :5555; continuing to Phase 4 follow-up poll for remaining budget"
      fi
    fi
  fi

  # Phase 4: dismiss follow-up dialogs AND poll for :5555 bind. The
  # two run concurrently because a Welcome / EULA window can appear
  # while we are also waiting for the EA to bind.
  #
  # Ensure main_wid is populated so we can skip it below. In the
  # Phase 2a path (dialog detected without Phase 2c), main_wid is
  # still empty; grab it now. Title finder first, then the PID-based
  # finder (MT5's window may still have an empty WM_NAME post-login).
  if [ -z "${main_wid:-}" ]; then
    main_wid=$(_drv_find_main_window) || true
    [ -n "${main_wid:-}" ] || main_wid=$(_drv_find_main_window_by_pid) || true
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
      # dialog, the MetaTrader main window, or the Open-an-Account
      # wizard (the wizard has its own dedicated handler in Phase 2a).
      # Press Return on each (default "OK/Accept" action for EULA /
      # news / broker terms). All xdotool calls are timeout-bounded
      # via _xdo (Wine override-redirect modals can hang raw xdotool
      # property reads -- jordansissel/xdotool #117/#126; bounding
      # them keeps Phase 4 from wedging the driver). windowactivate
      # is async (no --sync) for the same reason every other driver
      # site is async against Wine.
      fwid=$(DISPLAY=:99 _xdo search --onlyvisible --name '.+' 2>/dev/null | head -5 || true)
      if [ -n "$fwid" ]; then
        for w in $fwid; do
          [ "$w" = "$wid_first" ] && continue
          # Skip the main MT window by WID. After login the title
          # changes from 'MetaTrader 5 - Netting' to
          # '<account> - - Netting', so name-only matching is not
          # sufficient.
          [ -n "${main_wid:-}" ] && [ "$w" = "$main_wid" ] && continue
          wname=$(DISPLAY=:99 _xdo getwindowname "$w" 2>/dev/null || true)
          [ -z "$wname" ] && continue
          case "$wname" in
            'MetaTrader 5'*|'MetaTrader 4'*|*'- Netting'*|*'- Hedging'*) continue ;;
            'Open an Account'*|*'Select a company'*) continue ;;
          esac
          _drv_log "dismiss follow-up window: '${wname}' (WID=${w})"
          DISPLAY=:99 _xdo windowactivate "$w" 2>/dev/null || true
          sleep 0.2
          DISPLAY=:99 _xdo key --clearmodifiers Return 2>/dev/null || true
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
  # Defensive guard: an empty _self_pid would degenerate the case
  # glob to '*', firing the regression WARN on every boot regardless
  # of password content (false positive). $$ is the entrypoint's own
  # PID and is essentially never empty in bash, but skipping the
  # match when it IS empty keeps the guard from ever turning into a
  # log-pollution source.
  if [ -n "$_self_pid" ]; then
    case "${MT_PASSWORD:-}" in
      "${_self_pid}"*)
        log WARN "MT_PASSWORD appears to start with this shell's PID (${_self_pid}). This is the historical signature of bash-source corruption of /vault/secrets/. If the broker rejects the login as 'invalid password', someone has reintroduced a shell-source pattern upstream of this entrypoint. See docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md."
        ;;
    esac
  fi
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
  # Primary template path: co-located with ZeroMQ_EA.set so MT4 loads
  # the <expert> inputs from the same directory. TPL_REL_DST_ALT is
  # the legacy root-level location, written as a mirror so whichever
  # tree the build reads, expert.tpl is present.
  TPL_REL_DST="MQL4/Profiles/Templates/expert.tpl"
  TPL_REL_DST_ALT="templates/expert.tpl"
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
  # Primary template path: co-located with ZeroMQ_EA.set so MT5 loads
  # the <expert> inputs from the same directory (the authoritative
  # read path on build 58xx). TPL_REL_DST_ALT is the legacy root-level
  # tree the bundles also ship; written as a mirror so whichever tree
  # the build reads, expert.tpl is present.
  TPL_REL_DST="MQL5/Profiles/Templates/expert.tpl"
  TPL_REL_DST_ALT="Profiles/Templates/expert.tpl"
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

# Legacy-PVC self-heal. PVCs that were overlay-installed by the
# deletion-era normalizer (commits e16b70bf / c85b5d7e / bc1b96566)
# have the sentinel + MT_EXE present, but the bundle's shipped
# Config/common.ini + Config/accounts.dat (MT5) or Config/accounts.ini
# (MT4) were DELETED at overlay time. On those PVCs the sentinel-gated
# skip above would leave the prefix permanently in the deletion state
# and every boot would land on the Open-an-Account wizard (the wizard
# handler in Phase 2a is the safety net, but the supportable steady
# state is 'common.ini present; MT5 boots straight to the Login
# dialog'). Detect this state and bust the sentinel so the overlay
# re-runs and the preserving normalizer restores the files from the
# bundle. Idempotent: only fires when a real mismatch is observed.
if [ "$_overlay_needed" -eq 0 ]; then
  _legacy_cfg=$(_resolve_mt_config_dir "$MT_DIR")
  _bundle_cfg="${_bundle_root}/Config"
  if [ ! -d "$_bundle_cfg" ]; then
    # Some MT4 bundles ship 'config' (lowercase). The bundle Config-dir
    # resolution itself is the normalizer's job, but for the heal-check
    # we just look at whichever case the bundle ships.
    _bundle_cfg="${_bundle_root}/config"
  fi
  _legacy_state_detected=0
  _legacy_missing=""
  if [ "$MT_PLATFORM" = "mt4" ]; then
    if [ -f "${_bundle_cfg}/accounts.ini" ] && [ ! -f "${_legacy_cfg}/accounts.ini" ]; then
      _legacy_state_detected=1
      _legacy_missing="accounts.ini"
    fi
  else
    if [ -f "${_bundle_cfg}/common.ini" ] && [ ! -f "${_legacy_cfg}/common.ini" ]; then
      _legacy_state_detected=1
      _legacy_missing="common.ini"
    fi
    if [ -f "${_bundle_cfg}/accounts.dat" ] && [ ! -f "${_legacy_cfg}/accounts.dat" ]; then
      _legacy_state_detected=1
      if [ -n "$_legacy_missing" ]; then
        _legacy_missing="${_legacy_missing}+accounts.dat"
      else
        _legacy_missing="accounts.dat"
      fi
    fi
  fi
  if [ "$_legacy_state_detected" -eq 1 ]; then
    log WARN "broker-bundle overlay: legacy-PVC state detected (sentinel present, ${MT_EXE} on disk, but bundle-shipped ${_legacy_missing} missing under '${_legacy_cfg}'). This PVC was overlay-installed by a deletion-era normalizer (commits e16b70bf/c85b5d7e/bc1b96566). Busting the sentinel so the overlay re-runs and the preserving normalizer (commit 4b371085) restores the missing file(s) from the bundle. One-shot per affected PVC; idempotent on subsequent boots."
    _overlay_needed=1
  fi
  unset _legacy_cfg _bundle_cfg _legacy_state_detected _legacy_missing
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

  # ── Overlay normalizer (deterministic chart-attach prerequisites) ──
  #
  # The pre-baked broker bundles are built on case-INSENSITIVE Windows
  # and ship state that actively BLOCKS our deterministic EA attach on
  # case-SENSITIVE Linux/Wine. Verified against the three sha-matched
  # catalog bundles (exness mt5, deriv mt5, exness mt4). Three classes
  # of baked state must be neutralized, ONCE, on (re-)overlay only
  # (sentinel-gated), so MT5's OWN saved profile + accounts cache on
  # subsequent boots over the same PVC are preserved:
  #
  #   (A) Saved chart WORKSPACE. The bundles do NOT ship Profiles/
  #       Default; the real workspace is Profiles/Charts/* AND
  #       MQL5/Profiles/Charts/* (MT5) or profiles/* + lastprofile.ini
  #       (MT4). While a saved profile exists, MT5 restores it and
  #       IGNORES startup.ini [Charts] Template=expert, so our EA never
  #       attaches. Removing the chart workspace forces MT5 to cold-
  #       boot a fresh chart that Template=expert applies expert.tpl
  #       to (naming ZeroMQ_EA), OnInit runs, :5555 binds -- no GUI
  #       automation. Templates/ + SymbolSets/ are KEPT.
  #
  #   (B) common.ini profile-restore + FOREIGN account (MT5 only).
  #       Both MT5 bundles ship [Charts] ProfileLast=Default +
  #       PreloadCharts=1 (forces profile restore) and a third-party
  #       [Common] Login=/Server=/Environment= (the bundle builder's
  #       own account). Left in place MT5 would auto-restore a foreign
  #       session and race our Vault-sourced auto-login. We blank
  #       ProfileLast, set PreloadCharts=0, and strip the foreign
  #       Login/Server/Environment.
  #
  #   (C) Saved-account cache. MT5 ships Config/accounts.dat; MT4
  #       ships the encrypted Config/accounts.ini. Both carry the
  #       foreign account. We DELETE them so the only login path is
  #       auto_login_driver() with the per-tenant Vault creds. MT5
  #       re-creates accounts.dat itself after the first successful
  #       login (the driver ticks 'Save account information') and the
  #       PVC persists it, so the subsequent-boot fast path is intact.
  #
  # MT_CONFIG_DIR (resolved below, BEFORE this block uses it) is the
  # single canonical Config directory; on Deriv (which ships BOTH
  # 'Config' and 'config') it is de-duplicated so MT5's read path is
  # deterministic.
  _normalize_overlay "$MT_DIR" "$MT_PLATFORM"
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

# Ensure MT_CONFIG_DIR is set on EVERY boot path. The normalizer sets
# + exports it on the overlay path; on the overlay-SKIPPED subsequent-
# boot path (sentinel matched) it is still unset here, so resolve it
# now against the existing on-disk layout (also de-dups a stray
# Config/config pair if a prior boot left one). All later config /
# journal writes derive from this so they land in the directory MT
# actually reads (case-correct on Linux/Wine).
if [ -z "${MT_CONFIG_DIR:-}" ]; then
  MT_CONFIG_DIR=$(_resolve_mt_config_dir "$MT_DIR")
  export MT_CONFIG_DIR
  log INFO "config dir resolved (overlay-skipped path) to '${MT_CONFIG_DIR}'"
fi

# ── Materialise MT directory layout under the branded root ────────
mkdir -p "$MT_DIR/$(dirname "$EA_REL_DST")" \
         "$MT_DIR/$(dirname "$SET_REL_DST")" \
         "$MT_DIR/$(dirname "$TPL_REL_DST")" \
         "$MT_DIR/$(dirname "$TPL_REL_DST_ALT")" \
         "$MT_DIR/$(dirname "$EA_DEPS_LIBZMQ_DST_REL")" \
         "$MT_DIR/$EA_DEPS_INCLUDE_DST_REL" \
         "$MT_CONFIG_DIR"

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
INI_FILE="$MT_CONFIG_DIR/startup.ini"
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
  # Mirror to the legacy template tree so whichever Profiles/Templates
  # location the build reads, expert.tpl is present and byte-identical.
  cp -f "$MT_DIR/$TPL_REL_DST" "$MT_DIR/$TPL_REL_DST_ALT" 2>/dev/null || true
  # ALSO mirror to default.tpl so interactive Phase 5 chart-opens apply it.
  cp -f "$MT_DIR/$TPL_REL_DST" "$MT_DIR/$(dirname "$TPL_REL_DST")/default.tpl" 2>/dev/null || true
  cp -f "$MT_DIR/$TPL_REL_DST" "$MT_DIR/$(dirname "$TPL_REL_DST_ALT")/default.tpl" 2>/dev/null || true
  log INFO "Chart template written to '$TPL_REL_DST' (+ mirror '$TPL_REL_DST_ALT' + default.tpl) symbol=$MT_SYMBOL"

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
  # Mirror to the legacy template tree (see symbol-resolved branch).
  cp -f "$MT_DIR/$TPL_REL_DST" "$MT_DIR/$TPL_REL_DST_ALT" 2>/dev/null || true
  # ALSO mirror to default.tpl so that any chart opened interactively by
  # Phase 5 keystrokes automatically loads the ZeroMQ_EA.
  cp -f "$MT_DIR/$TPL_REL_DST" "$MT_DIR/$(dirname "$TPL_REL_DST")/default.tpl" 2>/dev/null || true
  cp -f "$MT_DIR/$TPL_REL_DST" "$MT_DIR/$(dirname "$TPL_REL_DST_ALT")/default.tpl" 2>/dev/null || true
  log INFO "Bootstrap chart template written to '$TPL_REL_DST' (+ mirror '$TPL_REL_DST_ALT' + default.tpl), no symbol pinned"

  cat > "$INI_FILE" <<EOF
[Common]
Login=${MT_LOGIN}
Password=${MT_PASSWORD}
Server=${MT_SERVER}
AutoConfiguration=true

[Charts]
Symbol=UNKNOWN
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
# and harmless.
#
# Build resolution is JOURNAL-FIRST and authoritative: the running
# build is read from the broker-bundle terminal's own journal
# ('Terminal ... build NNNN started'). The image no longer bakes any
# MetaTrader install -- the branded terminal arrives at runtime via
# the broker bundle -- so there is NO single 'baked build' to assume
# as a fallback (real captures span build 5833 on Deriv, 5830 on the
# Exness access server, etc.). When the journal does not yet exist
# (cold first boot, before MT5 has written it), the build is UNKNOWN
# unless an operator pins MT_BUILD_FALLBACK explicitly. In the unknown
# case we SKIP writing the [LiveUpdate] pin rather than fabricate a
# build number: a wrong LastBuildDataPath is at best inert and at
# worst misleading to an operator reading terminal.ini, and the pin
# is not the mechanism that actually gates LiveUpdate (the egress
# NetworkPolicy is).
MT_BUILD_FALLBACK="${MT_BUILD_FALLBACK:-}"
MT_BUILD=""
# MT5/MT4 write the journal to <root>/logs (lowercase) at runtime;
# this is created by MT itself, not baked, so it is case-stable.
MT_JOURNAL_DIR="$MT_DIR/logs"
if [ -d "$MT_JOURNAL_DIR" ]; then
  # MT5/MT4 build 58xx writes the journal as UTF-16LE (ASCII bytes
  # interleaved with 0x00 NUL). Strip the NULs before grepping or
  # the ASCII regex literally never matches. Same posture every
  # other journal reader in this script uses
  # (_drv_login_authenticated, _drv_grep_mql5_logs, the LiveUpdate
  # self-restart classifier in the supervisor loop).
  MT_BUILD=$(cat "$MT_JOURNAL_DIR"/*.log 2>/dev/null \
    | tr -d '\000' \
    | grep -ahoE 'build [0-9]+ started' \
    | grep -oE '[0-9]+' | sort -rn | head -n1 || true)
fi
MT_BUILD="${MT_BUILD:-$MT_BUILD_FALLBACK}"

TERMINAL_INI="$MT_CONFIG_DIR/terminal.ini"
if [ -z "$MT_BUILD" ]; then
  log INFO "LiveUpdate build pin SKIPPED: running build not yet resolvable from the journal ($MT_JOURNAL_DIR) and MT_BUILD_FALLBACK is unset. The journal-derived build will be pinned on a subsequent boot; LiveUpdate is gated by the NetworkPolicy egress block regardless, so this is non-fatal ($MT_PLATFORM)."
elif [ -f "$TERMINAL_INI" ]; then
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
  log INFO "LiveUpdate pinned to build ${MT_BUILD} in $TERMINAL_INI ($MT_PLATFORM)"
else
  cat > "$TERMINAL_INI" <<EOF
[LiveUpdate]
LastBuildDataPath=${MT_BUILD}
EOF
  log INFO "LiveUpdate pinned to build ${MT_BUILD} in $TERMINAL_INI ($MT_PLATFORM)"
fi

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
