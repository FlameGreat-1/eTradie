package server

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/gateway/internal/ports"
	"github.com/flamegreat-1/etradie/src/mails"
)

// KillSwitchHandler is the gateway control plane for the execution
// kill switch (CHECKLIST Section 8). It is the SOLE control surface;
// it delegates state + authorization to the execution service via
// ports.ExecutionPort (GetHaltState / SetHaltState).
//
// Chains:
//   - client: authMiddleware -> csrfMiddleware (user-scoped to the JWT)
//   - admin:  authMiddleware -> RequireAdmin -> csrfMiddleware
//
// The handler forwards the caller's JWT (already in the request context
// and propagated by the adapter) so the execution server enforces the
// final authz (global => admin; user => self or admin). RequireAdmin on
// the admin route is the perimeter check; execution is the backstop.
type KillSwitchHandler struct {
	execution ports.ExecutionPort
	users     *auth.UserStore
	mailer    *mails.Sender
	appURL    string
	log       zerolog.Logger
}

// NewKillSwitchHandler builds the handler. execution must not be nil;
// callers gate construction on execution availability. users, mailer,
// and appURL are optional: when all are set, a GLOBAL toggle emails
// every active user. When any is nil the email fan-out is skipped and
// only the realtime notification fires.
func NewKillSwitchHandler(
	execution ports.ExecutionPort,
	users *auth.UserStore,
	mailer *mails.Sender,
	appURL string,
) *KillSwitchHandler {
	if execution == nil {
		panic("kill_switch_handler: execution port must not be nil")
	}
	return &KillSwitchHandler{
		execution: execution,
		users:     users,
		mailer:    mailer,
		appURL:    appURL,
		log:       observability.Logger("kill_switch_handler"),
	}
}

// RegisterRoutes mounts the client and admin kill-switch endpoints.
func (h *KillSwitchHandler) RegisterRoutes(
	mux *http.ServeMux,
	authMiddleware func(http.Handler) http.Handler,
	csrfMiddleware func(http.Handler) http.Handler,
) {
	clientChain := func(handler http.HandlerFunc) http.Handler {
		return authMiddleware(csrfMiddleware(http.HandlerFunc(handler)))
	}
	adminChain := func(handler http.HandlerFunc) http.Handler {
		return authMiddleware(auth.RequireAdmin(csrfMiddleware(http.HandlerFunc(handler))))
	}

	mux.Handle("/api/v1/execution/kill-switch", clientChain(h.handleClient))
	mux.Handle("/api/v1/admin/execution/kill-switch", adminChain(h.handleAdmin))
}

// handleClient serves the user's own kill-switch read + toggle.
//
//	GET  /api/v1/execution/kill-switch
//	PUT  /api/v1/execution/kill-switch   { "halted": bool }
func (h *KillSwitchHandler) handleClient(w http.ResponseWriter, r *http.Request) {
	claims := auth.ClaimsFromContext(r.Context())
	if claims == nil || claims.UserID == "" {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	switch r.Method {
	case http.MethodGet:
		globalHalted, userHalted, err := h.execution.HaltState(r.Context(), "")
		if err != nil {
			h.log.Error().Err(err).Str("user_id", claims.UserID).Msg("kill_switch_get_failed")
			writeJSONError(w, http.StatusBadGateway, "failed to read kill switch state")
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"global_halted": globalHalted,
			"user_halted":   userHalted,
			"effective":     globalHalted || userHalted,
		})

	case http.MethodPut:
		var body struct {
			Halted bool `json:"halted"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeJSONError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
			return
		}
		// scope=user, empty target => execution binds the caller from JWT.
		globalHalted, userHalted, err := h.execution.SetHaltState(r.Context(), "user", "", body.Halted)
		if err != nil {
			h.log.Error().Err(err).Str("user_id", claims.UserID).Bool("halted", body.Halted).Msg("kill_switch_set_user_failed")
			writeJSONError(w, http.StatusBadGateway, "failed to update kill switch")
			return
		}
		h.log.Warn().Str("user_id", claims.UserID).Bool("halted", body.Halted).Msg("kill_switch_user_toggled")
		writeJSON(w, http.StatusOK, map[string]any{
			"scope":         "user",
			"global_halted": globalHalted,
			"user_halted":   userHalted,
		})

	default:
		w.Header().Set("Allow", strings.Join([]string{http.MethodGet, http.MethodPut}, ", "))
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

// handleAdmin serves the admin global / per-user-override toggle.
//
//	PUT /api/v1/admin/execution/kill-switch
//	  { "scope":"global", "halted":bool }
//	  { "scope":"user", "target_user_id":"...", "halted":bool }
func (h *KillSwitchHandler) handleAdmin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		w.Header().Set("Allow", http.MethodPut)
		writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	claims := auth.ClaimsFromContext(r.Context())
	if claims == nil || claims.UserID == "" {
		writeJSONError(w, http.StatusUnauthorized, "unauthorized")
		return
	}

	var body struct {
		Scope        string `json:"scope"`
		TargetUserID string `json:"target_user_id"`
		Halted       bool   `json:"halted"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeJSONError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	scope := strings.ToLower(strings.TrimSpace(body.Scope))
	if scope != "global" && scope != "user" {
		writeJSONError(w, http.StatusBadRequest, "scope must be 'global' or 'user'")
		return
	}
	if scope == "user" && strings.TrimSpace(body.TargetUserID) == "" {
		writeJSONError(w, http.StatusBadRequest, "target_user_id is required for scope=user")
		return
	}

	globalHalted, userHalted, err := h.execution.SetHaltState(r.Context(), scope, strings.TrimSpace(body.TargetUserID), body.Halted)
	if err != nil {
		h.log.Error().Err(err).
			Str("admin_id", claims.UserID).
			Str("scope", scope).
			Str("target_user_id", body.TargetUserID).
			Bool("halted", body.Halted).
			Msg("kill_switch_admin_set_failed")
		writeJSONError(w, http.StatusBadGateway, "failed to update kill switch")
		return
	}

	h.log.Warn().
		Str("admin_id", claims.UserID).
		Str("scope", scope).
		Str("target_user_id", body.TargetUserID).
		Bool("halted", body.Halted).
		Msg("kill_switch_admin_toggled")

	// A global toggle changes trading for every user, so notify them by
	// email in addition to the realtime event. Detached + fire-and-forget
	// so the admin response is not blocked by SMTP.
	if scope == "global" {
		h.emailAllUsersGlobalHalt(body.Halted)
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"scope":         scope,
		"global_halted": globalHalted,
		"user_halted":   userHalted,
	})
}

// emailAllUsersGlobalHalt sends every active user an email describing
// the platform-wide halt state change. No-op unless the user store and
// mailer are wired. Runs in its own goroutine with a bounded context.
func (h *KillSwitchHandler) emailAllUsersGlobalHalt(halted bool) {
	if h.users == nil || h.mailer == nil {
		return
	}

	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		users, err := h.users.ListActiveUsers(ctx)
		if err != nil {
			h.log.Error().Err(err).Msg("kill_switch_global_email_user_list_failed")
			return
		}

		subject, body := globalHaltEmail(halted, h.appURL)
		sent := 0
		for _, u := range users {
			if u == nil || u.Email == "" {
				continue
			}
			// SendWithRetry is itself fire-and-forget with internal
			// retry/backoff; call it directly per recipient.
			h.mailer.SendWithRetry(u.Email, subject, body)
			sent++
		}
		h.log.Info().Bool("halted", halted).Int("recipients", sent).Msg("kill_switch_global_email_dispatched")
	}()
}

// globalHaltEmail returns the subject + HTML body for the platform-wide
// halt notification. Analysis-continues wording matches the product
// semantics: only order placement is paused.
func globalHaltEmail(halted bool, appURL string) (string, string) {
	cta := ""
	if appURL != "" {
		cta = fmt.Sprintf(
			`<p style="margin:24px 0"><a href="%s/dashboard/settings/execution" `+
				`style="background:#000;color:#fff;padding:12px 20px;border-radius:8px;`+
				`text-decoration:none;font-weight:700">Open Execution Settings</a></p>`,
			appURL,
		)
	}
	if halted {
		return "Trading paused: platform-wide kill switch engaged",
			`<div style="font-family:system-ui,sans-serif;max-width:560px;margin:auto">` +
				`<h2>Trading is paused</h2>` +
				`<p>An administrator has engaged the platform-wide execution kill switch. ` +
				`<strong>New trades are not being placed for any account.</strong></p>` +
				`<p>Analysis continues to run as normal, so you can still see what would have traded. ` +
				`Order placement resumes automatically when the kill switch is released.</p>` +
				cta +
				`</div>`
	}
	return "Trading resumed: platform-wide kill switch released",
		`<div style="font-family:system-ui,sans-serif;max-width:560px;margin:auto">` +
			`<h2>Trading has resumed</h2>` +
			`<p>The platform-wide execution kill switch has been released. ` +
			`New trades will be placed again according to your settings.</p>` +
			cta +
			`</div>`
}
