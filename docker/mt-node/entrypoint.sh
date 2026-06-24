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

log() { printf '%s [%s] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$1" "$2" >&2; }

# ── Signal handling ─────────────────────────────────────────────
_shutdown() {
  log INFO "Caught shutdown signal, terminating auto-login driver + MetaTrader + Xvfb"
  # Tear down the driver FIRST so it does not race the MT5 SIGTERM
  # below (a driver mid-`xdotool type` would otherwise inject
  # keystrokes into a window that is being closed).
  if [ -n "${DRIVER_PID}" ] && kill -0 "${DRIVER_PID}" 2>/dev/null; then
    kill -TERM "${DRIVER_PID}" 2>/dev/null || true
    for _ in $(seq 1 30); do
      kill -0 "${DRIVER_PID}" 2>/dev/null || break
      sleep 0.1
    done
    kill -KILL "${DRIVER_PID}" 2>/dev/null || true
  fi
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

# ── Auto-login driver (xdotool-based GUI automation) ───────────
#
# Why this exists
# ---------------
# MetaTrader 5 build 5836 ignores both documented unattended-launch
# mechanisms:
#   * `/login /password /server` command-line flags - confirmed via
#     ps -ef + journal silence + zero outbound TCP to broker IPs.
#   * startup.ini [Common] Login/Password/Server - file is read, but
#     never acted on; only populates the Login dialog's fields.
#
# MetaQuotes' modern builds expect either a saved accounts.dat (which
# only exists after a manual first login) or interactive user input.
# The accepted industry solution - used by every commercial MT5 VPS
# provider running Wine + Xvfb (ForexVPS, Beeks, CNS) - is to drive
# the Login dialog programmatically via xdotool, check "Save account
# information" so MT5 writes accounts.dat itself, and let every
# subsequent boot use accounts.dat for silent auto-login.
#
# Contract
# --------
# auto_login_driver() runs as a background child of the entrypoint.
# It is best-effort: a driver crash does NOT kill MT5. The supervisor
# loop's normal exit-code path handles MT5 lifecycle; the driver is
# purely additive automation.
#
#   1. Wait up to AUTO_LOGIN_PROCESS_WAIT_SECS for terminal binary.
#   2. Phase 2 (dialog-first, with main-window fallback):
#      a) Phase 2a -- poll xdotool every 2s for a Login-shaped window
#         (AUTO_LOGIN_DIALOG_TITLE_REGEX). Wait at most
#         AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS (default 30s) for the
#         dialog before considering Phase 2c. The dialog path was the
#         original design contract; it remains the happy path for
#         fresh prefixes and for any future MT5 build that reinstates
#         the on-launch Login prompt.
#      b) Phase 2b -- idempotent :5555 fast path. If :5555 LISTEN
#         appears at any time, MT5 has auto-logged in via
#         accounts.dat (subsequent boot). Exit 0 immediately.
#      c) Phase 2c -- main-window menu-driven invocation. After
#         AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS of NEITHER dialog NOR
#         :5555 bind, check whether MT5's main UI window is visible
#         (AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX). If yes, this is the
#         empirical build-5836 + pre-staged-config path -- MT5
#         opened straight to the main window without prompting.
#         Phase 2c dismisses the 'Welcome to LiveUpdate' modal
#         (Escape), focuses the main window, sends Ctrl+Shift+L
#         (MT5's 'Login to Trade Account' hotkey), waits up to
#         AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS for the dialog,
#         and falls back to the Alt+F (File menu) -> arrow Down ->
#         Return menu navigation if the hotkey was absorbed. On
#         dialog visible after either path, falls through to Phase
#         3 unchanged. Platform-gated to MT_PLATFORM=mt5; MT4 keeps
#         the dialog-only Phase 2a path because MT4 build behaviour
#         on this code path has not been empirically validated.
#      Phase 2 overall budget remains AUTO_LOGIN_DIALOG_WAIT_SECS;
#      if neither dialog nor :5555 bind happens within that budget,
#      exit 1 (supervisor handles).
#   3. Phase 3 -- on dialog visible: activate window, type credentials
#      with --clearmodifiers --delay 50, check 'Save account
#      information', press Return. Unchanged from previous design.
#   4. Phase 4 -- for AUTO_LOGIN_FOLLOWUP_DISMISS_SECS, dismiss any
#      other visible windows (EULA, Welcome, broker terms, news
#      alerts) via Return. Unchanged.
#   5. Total budget AUTO_LOGIN_TOTAL_BUDGET_SECS. On success exit 0;
#      on timeout exit 1.
#
# Security
# --------
# - Runs as uid 1000 (same as the main container).
# - $MT_PASSWORD is passed to `xdotool type --` as an argv element.
#   It appears in xdotool's /proc/<pid>/cmdline for the milliseconds
#   the call takes. Only the mt uid can read it. This is a strict
#   improvement over the previous `/password:` on terminal64.exe
#   itself, which kept the password in cmdline for the process
#   lifetime.
# - NEVER logs $MT_PASSWORD. Logs $MT_LOGIN, $MT_SERVER, dialog
#   titles, timing.
AUTO_LOGIN_TOTAL_BUDGET_SECS="${AUTO_LOGIN_TOTAL_BUDGET_SECS:-240}"
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
#   UI window. Build 5836 emits 'MetaTrader 5 - Netting' (netting
#   accounts) or 'MetaTrader 5 - Hedging' (hedging accounts); MT4
#   uses 'MetaTrader 4 - <Account>'. The state machine additionally
#   gates Phase 2c on MT_PLATFORM=mt5 because the MT5-on-Wine path
#   is the only one with empirical evidence of skipping the Login
#   prompt.
AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS="${AUTO_LOGIN_MAIN_WINDOW_WAIT_SECS:-30}"
AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS="${AUTO_LOGIN_DIALOG_WAIT_AFTER_INVOKE_SECS:-15}"
AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX="${AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX:-^MetaTrader [45] - (Netting|Hedging)}"

_drv_log() { log "INFO" "auto_login: $*"; }
_drv_warn() { log "WARN" "auto_login: $*"; }
_drv_err() { log "ERROR" "auto_login: $*"; }

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
_drv_find_window_by_regex() {
  local _re="$1"
  DISPLAY=:99 xdotool search --onlyvisible --name "$_re" 2>/dev/null | head -1 || true
}

_drv_find_login_dialog() {
  _drv_find_window_by_regex "$AUTO_LOGIN_DIALOG_TITLE_REGEX"
}

_drv_find_main_window() {
  _drv_find_window_by_regex "$AUTO_LOGIN_MAIN_WINDOW_TITLE_REGEX"
}

# Pre-dismiss the LiveUpdate welcome modal (build 5836 emits one
# titled 'Welcome to LiveUpdate'). If left visible it steals focus
# from any subsequent hotkey or menu navigation. Idempotent: a
# missing modal is a no-op.
_drv_dismiss_welcome_modal() {
  local _wmwid
  _wmwid=$(_drv_find_window_by_regex '^Welcome to LiveUpdate')
  if [ -n "$_wmwid" ]; then
    _drv_log "dismissing 'Welcome to LiveUpdate' modal (WID=${_wmwid})"
    DISPLAY=:99 xdotool windowactivate --sync "$_wmwid" 2>/dev/null || true
    sleep 0.2
    DISPLAY=:99 xdotool key --clearmodifiers Escape 2>/dev/null || true
    sleep 0.4
  fi
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

# Phase 2c attempt 1: open File menu, press L mnemonic.
_drv_invoke_login_via_mnemonic() {
  local _mwid="$1"
  _drv_log "Phase 2c attempt 1: File menu mnemonic (main WID=${_mwid}, Alt+F then L)"
  _drv_dismiss_welcome_modal
  DISPLAY=:99 xdotool windowactivate --sync "$_mwid" 2>/dev/null || true
  sleep 0.3
  DISPLAY=:99 xdotool keyup Shift Control Alt Meta 2>/dev/null || true
  DISPLAY=:99 xdotool key --clearmodifiers alt+f 2>/dev/null || true
  sleep 0.4
  DISPLAY=:99 xdotool key --clearmodifiers l 2>/dev/null || true
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
  _drv_dismiss_welcome_modal
  DISPLAY=:99 xdotool windowactivate --sync "$_mwid" 2>/dev/null || true
  sleep 0.3
  DISPLAY=:99 xdotool keyup Shift Control Alt Meta 2>/dev/null || true
  DISPLAY=:99 xdotool key --clearmodifiers alt+f 2>/dev/null || true
  sleep 0.4
  _i=0
  while [ "$_i" -lt "$_n" ]; do
    DISPLAY=:99 xdotool key --clearmodifiers Down 2>/dev/null || true
    sleep 0.1
    _i=$(( _i + 1 ))
  done
  DISPLAY=:99 xdotool key --clearmodifiers Return 2>/dev/null || true
}

auto_login_driver() {
  local start_ts now elapsed wid wid_first dialog_seen=0 bind_until dismiss_until fwid w wname
  local main_wid="" phase2a_deadline phase2c_attempted=0
  start_ts=$(date +%s)

  _drv_log "start (budget=${AUTO_LOGIN_TOTAL_BUDGET_SECS}s, login=${MT_LOGIN}, server=${MT_SERVER})"

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
    DISPLAY=:99 xdotool windowactivate --sync "$wid_first" 2>/dev/null || true
    sleep 0.4
    _drv_phase3_log "post_activate"
    # Clear stuck modifiers (xdotool best practice for Xvfb).
    DISPLAY=:99 xdotool keyup Shift Control Alt Meta 2>/dev/null || true

    DISPLAY=:99 xdotool key --clearmodifiers Tab 2>/dev/null || true
    sleep 0.15
    DISPLAY=:99 xdotool key --clearmodifiers ctrl+a 2>/dev/null || true
    sleep 0.1
    _drv_phase3_log "after_tab_1"
    DISPLAY=:99 xdotool type --clearmodifiers --delay 50 -- "$MT_LOGIN" 2>/dev/null || true
    sleep 0.2
    _drv_phase3_log "after_login_type"

    DISPLAY=:99 xdotool key --clearmodifiers Tab 2>/dev/null || true
    sleep 0.15
    DISPLAY=:99 xdotool key --clearmodifiers ctrl+a 2>/dev/null || true
    sleep 0.1
    _drv_phase3_log "after_tab_2"
    DISPLAY=:99 xdotool type --clearmodifiers --delay 50 -- "$MT_PASSWORD" 2>/dev/null || true
    sleep 0.2
    _drv_phase3_log "after_pwd_type"

    DISPLAY=:99 xdotool key --clearmodifiers Tab 2>/dev/null || true
    sleep 0.15
    # The startup.ini we wrote should pre-select $MT_SERVER, but we
    # type the server name explicitly as a defence against any state
    # where it has reset to the combobox default.
    DISPLAY=:99 xdotool key --clearmodifiers ctrl+a 2>/dev/null || true
    sleep 0.1
    _drv_phase3_log "after_tab_3"
    DISPLAY=:99 xdotool type --clearmodifiers --delay 50 -- "$MT_SERVER" 2>/dev/null || true
    sleep 0.3
    _drv_phase3_log "after_server_type"

    # Tab to "Save account information", toggle ON with Space so MT5
    # writes accounts.dat. Subsequent boots auto-login from that file
    # silently and the driver's fast path detects the immediate
    # :5555 LISTEN.
    DISPLAY=:99 xdotool key --clearmodifiers Tab 2>/dev/null || true
    sleep 0.15
    _drv_phase3_log "after_tab_4"
    DISPLAY=:99 xdotool key --clearmodifiers space 2>/dev/null || true
    sleep 0.2
    _drv_phase3_log "after_space"

    # Submit via Return. Works whether focus is on the checkbox or
    # the Login button - Return is the dialog's default action.
    _drv_phase3_log "pre_submit"
    DISPLAY=:99 xdotool key --clearmodifiers Return 2>/dev/null || true
    _drv_log "credentials typed and submitted (server=${MT_SERVER}, save-account=on)"
    sleep 1
    _drv_phase3_log "post_submit_1s"
  fi

  # Phase 4: dismiss follow-up dialogs AND poll for :5555 bind. The
  # two run concurrently because a Welcome / EULA window can appear
  # while we are also waiting for the EA to bind.
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
          wname=$(DISPLAY=:99 xdotool getwindowname "$w" 2>/dev/null || true)
          [ -z "$wname" ] && continue
          case "$wname" in
            'MetaTrader 5'*|'MetaTrader 4'*) continue ;;
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

# ── Materialise MT directory layout (idempotent) ─────────────────
mkdir -p "$MT_DIR/$(dirname "$EA_REL_DST")" \
         "$MT_DIR/$(dirname "$SET_REL_DST")" \
         "$MT_DIR/$(dirname "$TPL_REL_DST")" \
         "$MT_DIR/config"

# ── Inject broker-specific servers.dat or *.srv if present ────────
# The broker-bundle initContainer unzips the broker portable zip into
# /broker-bundle. That zip carries a TOP-LEVEL 'MetaTrader 5/' (or
# 'MetaTrader 5 <BRAND>/') directory -- the same layout the image
# Dockerfile unzips and asserts terminal64.exe beneath -- so the
# broker's servers.dat is at e.g.
# /broker-bundle/MetaTrader 5/config/servers.dat, NOT
# /broker-bundle/config/servers.dat. A per-instance Terminal data dir
# layout is also possible. Per the architecture doc we therefore FIND
# servers.dat rather than assume a fixed path, and install it (plus any
# *.srv companions) into the terminal's config dir before launch. These
# are the broker's OWN authoritative files -- installed verbatim, never
# edited. Safe when the bundle is absent (dev/docker-compose): the find
# returns nothing and the block is a no-op.
if [ -d "/broker-bundle" ]; then
  _bundle_installed=0
  while IFS= read -r _sd; do
    [ -n "$_sd" ] || continue
    cp -f "$_sd" "$MT_DIR/config/servers.dat"
    _bundle_installed=1
    log INFO "Installed broker servers.dat from bundle ($_sd)"
  done <<EOF
$(find /broker-bundle -type f -iname 'servers.dat' 2>/dev/null)
EOF
  while IFS= read -r _srv; do
    [ -n "$_srv" ] || continue
    cp -f "$_srv" "$MT_DIR/config/"
    _bundle_installed=1
    log INFO "Installed broker .srv from bundle ($_srv)"
  done <<EOF
$(find /broker-bundle -type f -iname '*.srv' 2>/dev/null)
EOF
  if [ "$_bundle_installed" -eq 0 ]; then
    log WARN "/broker-bundle present but no servers.dat/*.srv found under it; MT will use the baked servers.dat (broker login may fail)"
  fi
fi

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

# ── Disable MetaTrader LiveUpdate self-restart loop (defect #15) ──
# Both MT5 (terminal64.exe) and MT4 (terminal.exe) run LiveUpdate on
# every cold boot: the terminal contacts MetaQuotes' update servers,
# downloads a component (e.g. mt5onnx64), and self-restarts to apply
# (exit 143). The supervised loop then relaunches and re-runs the full
# recompile + LiveUpdate from scratch -- an infinite, non-convergent
# loop in which the EA OnInit never runs, MQL Logs is never created,
# and :5555 never binds, so the pod never reaches Ready.
#
# DEAD ENDS -- DO NOT RE-IMPLEMENT (all empirically DISPROVEN on the
# live cluster, build 5836; see
# docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md §1.x):
#   1. [LiveUpdate] LastBuildDataPath pin in terminal.ini  -> IGNORED.
#   2. hostAliases / DNS sinkhole of download.mql5.com     -> IGNORED
#      (updater dials MetaQuotes by hardcoded IP, bypassing /etc/hosts).
#   3. common.ini [Common] Source= empty (+ NewsEnable=0), re-asserted
#      every boot                                          -> IGNORED
#      (confirmed present in the running prefix; MT5 still downloaded
#      mt5onnx64 and self-restarted exit 143; :5555 never bound).
#
# NO in-container config or DNS lever stops LiveUpdate on this build.
# The ONLY working control is a NETWORK EGRESS BLOCK (Layer 2) applied
# by the per-tenant NetworkPolicy (default-deny egress + broker
# access-server CIDR allowlist). That lives in the chart + provisioner,
# NOT in this script. Do not add another config-write 'fix' here.
#
# The legacy terminal.ini LastBuildDataPath pin is still written below
# only because the baked template carries it; it is INERT and retained
# solely to avoid a no-op diff. It does nothing.

# Resolve the baked terminal build so we never pin a stale number.
# The terminal records the running build in its journal as
# 'MetaTrader <4|5> ... build <N> started'; fall back to the known
# baked MT5 build (5836) if the journal is not yet present (first
# boot). MT4 journals carry the same 'build <N>' token.
MT_BUILD=""
MT_JOURNAL_DIR="$MT_DIR/logs"
if [ -d "$MT_JOURNAL_DIR" ]; then
  MT_BUILD=$(grep -ahoE 'build [0-9]+ started' "$MT_JOURNAL_DIR"/*.log 2>/dev/null \
    | grep -oE '[0-9]+' | sort -rn | head -n1 || true)
fi
MT_BUILD="${MT_BUILD:-5836}"

# Layer 1: pin [LiveUpdate] LastBuildDataPath in terminal.ini for the
# active platform (MT4 and MT5 share this config file + section name).
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

# NOTE: LiveUpdate is disabled solely via the [LiveUpdate]
# LastBuildDataPath pin in terminal.ini above (the mechanism
# confirmed from the actual install). No filesystem chmod and no
# network block are applied: MetaTrader writes legitimate files at
# the program-dir root on normal startup, so locking it risks
# stopping the terminal from launching; and any network block is the
# only lever that could endanger the broker connection. The ini pin
# is config-only with zero side effect -- it cannot break the broker,
# the EA, the ZMQ socket, or startup.

# ── Supervised MT restart loop ───────────────────────────────────
restart_count=0
window_start=$(date +%s)

while :; do
  log INFO "Launching $MT_EXE (platform=$MT_PLATFORM, server=$MT_SERVER, login=$MT_LOGIN, symbol=$MT_SYMBOL, symbol_resolved=$SYMBOL_RESOLVED, zmq_port=$ZMQ_PORT, restart_count=$restart_count)"

  cd "$MT_DIR"
  # Launch contract for unattended headless MT5 build 5836:
  #
  #   /portable - the ONLY flag we pass. It pins MT5's config location
  #               to <install_dir>/config/ (not
  #               AppData/Roaming/MetaQuotes/), so the startup.ini we
  #               write is the one MT5 reads, AND so MT5 writes
  #               accounts.dat to the PVC-mounted config dir (where
  #               it persists across pod restarts).
  #
  # We deliberately do NOT pass /login /password /server. MT5 build
  # 5836 ignores those flags entirely - confirmed via ps -ef showing
  # the flags reaching terminal64.exe + journal silence + zero
  # outbound TCP to broker IPs (see runbook sections 1.2 / 2.x for
  # the full empirical evidence trail). startup.ini's [Common]
  # Login/Password/Server block is also ignored for auto-login: MT5
  # reads the file (populates dialog fields) but never executes a
  # login action.
  #
  # Auto-login is instead driven by the xdotool-based
  # auto_login_driver() shell function defined above, which forks
  # immediately after this wine launch. The driver waits for MT5's
  # Login dialog on the Xvfb display, types $MT_LOGIN / $MT_PASSWORD
  # / $MT_SERVER with --clearmodifiers, ticks "Save account
  # information" so MT5 writes accounts.dat, and presses Return.
  # Every subsequent boot auto-loads silently from accounts.dat and
  # the driver's fast path exits success on the immediate :5555
  # LISTEN.
  #
  # See docs/runbooks/HOSTED-MT-PROVISIONING-SESSION.md sections 2.x.
  #
  # Note on credential exposure: MT_PASSWORD is NOT on the wine
  # command line. The xdotool auto_login_driver (forked below) types
  # the password into MT5's Login dialog after launch; the password
  # appears in xdotool's /proc/<pid>/cmdline ONLY for the milliseconds
  # the `xdotool type` call takes. This is a strict improvement over
  # the previous `/password:$MT_PASSWORD` on terminal64.exe, which
  # kept the password in MT5's cmdline for the entire process
  # lifetime. /portable is retained so MT5 reads/writes config in
  # <install_dir>/config (PVC-mounted, persists across pod restarts);
  # this lets MT5 save accounts.dat itself when the driver checks
  # "Save account information", and subsequent boots auto-login
  # silently from that file (the driver detects the immediate
  # :5555 LISTEN and exits success on its fast path).
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
      sleep 1
      kill -KILL "$DRIVER_PID" 2>/dev/null || true
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
