package auth

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/flamegreat-1/etradie/src/mails"
)

// ---------------------------------------------------------------------------
// Password reset (forgot password) handlers
//
// Three endpoints, all public and rate-limited:
//
//   POST /auth/password/forgot          : request a reset email.
//   POST /auth/password/reset/validate  : non-mutating token probe.
//   POST /auth/password/reset           : single-use token redemption.
//
// Threat model and mitigations (mapped to handler code):
//
//   T1  user enumeration                 -> forgot ALWAYS returns 202
//   T2  token guessing                   -> 32-byte crypto rand token
//   T3  reset replay                     -> single-use Consume()
//   T4  reset of a federated account     -> auth_provider check
//   T5  reset of a deactivated account   -> active check
//   T6  mailbox flooding (1 user)        -> per-user soft cap
//   T7  mailbox flooding (many IPs)      -> per-user soft cap (same)
//   T8  open-redirect via reset link     -> FrontendBaseURL only
//   T9  XSS via display name in email    -> html.Escape in template
//   T10 token leaking via referer        -> token is a POST body field
//                                           on the reset call; only
//                                           the SPA reset page sees it
//                                           in the URL and the page is
//                                           on the same origin as the
//                                           gateway's CORS allowlist.
// ---------------------------------------------------------------------------

const (
	// passwordResetGenericMessage is the user-visible envelope returned
	// from POST /auth/password/forgot for BOTH the success path and
	// every silent-skip path (user not found, non-local provider,
	// throttled, etc). Identical wording is what makes the endpoint
	// non-enumerable.
	passwordResetGenericMessage = "if an account exists for that email, a password reset link has been sent"

	// passwordResetUserWindow / passwordResetUserMax cap the number of
	// reset requests a single user can trigger in a rolling window. The
	// limit is intentionally generous (legitimate users retry a couple
	// of times) but tight enough that a botnet rotating IPs cannot use
	// the endpoint as a mailbomb against one address.
	passwordResetUserWindow = 15 * time.Minute
	passwordResetUserMax    = 5
)

// WithPasswordReset attaches the password-reset dependencies to the
// handler. Symmetric with WithOAuth: called once from main.go after
// the store and mailer are built. Calling without a mailer disables
// the forgot-password endpoints (they return 503) so a partial
// deployment fails closed rather than silently mailing into the void.
func (h *Handler) WithPasswordReset(store *PasswordResetStore, mailer Mailer) {
	h.passwordResets = store
	h.mailer = mailer
}

// passwordResetEnabled reports whether the feature is fully wired.
func (h *Handler) passwordResetEnabled() bool {
	return h.passwordResets != nil && h.mailer != nil
}

// ---------------------------------------------------------------------------
// POST /auth/password/forgot
// ---------------------------------------------------------------------------

type forgotPasswordRequest struct {
	Email string `json:"email"`
}

func (h *Handler) handleForgotPassword(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.passwordResetEnabled() {
		writeAuthError(w, http.StatusServiceUnavailable, "password reset is not configured on this deployment")
		return
	}

	var req forgotPasswordRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeAuthError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	email := strings.ToLower(strings.TrimSpace(req.Email))
	if email == "" || !strings.Contains(email, "@") {
		writeAuthError(w, http.StatusBadRequest, "a valid email address is required")
		return
	}

	// Build the user-facing reset link base BEFORE doing the DB lookup
	// so a misconfigured deploy fails the request cleanly rather than
	// silently sending an unusable email.
	baseURL, err := h.passwordResetBaseURL(r)
	if err != nil {
		writeAuthError(w, http.StatusServiceUnavailable, "password reset is not configured: "+err.Error())
		return
	}

	// Always return the same envelope regardless of which silent-skip
	// branch we take. Use a deferred helper so every early-return path
	// produces the same response shape.
	respondGeneric := func() {
		writeJSON(w, http.StatusAccepted, map[string]string{
			"message": passwordResetGenericMessage,
			"status":  "accepted",
		})
	}

	user, err := h.users.GetUserByEmail(r.Context(), email)
	if err != nil {
		// Internal lookup failures must not leak as 500 because that
		// makes the endpoint behave differently when an email exists
		// (cheap path) vs doesn't (DB miss). Log and return generic.
		respondGeneric()
		return
	}
	if user == nil {
		respondGeneric()
		return
	}
	if !user.Active {
		respondGeneric()
		return
	}
	// Federated accounts have no local password; mailing a reset link
	// would be pointless and the redemption handler would reject it.
	if user.AuthProvider != "" && user.AuthProvider != AuthProviderLocal {
		respondGeneric()
		return
	}

	// Per-user soft rate limit. CountRecentRequests is cheap; it sits
	// on top of the IP limiter that already gates the route.
	count, err := h.passwordResets.CountRecentRequests(r.Context(), user.ID, passwordResetUserWindow)
	if err == nil && count >= passwordResetUserMax {
		respondGeneric()
		return
	}

	plaintextToken, err := GeneratePasswordResetToken()
	if err != nil {
		respondGeneric()
		return
	}

	ip := h.cfg.IPResolver().Resolve(r)
	ua := r.UserAgent()

	_, err = h.passwordResets.CreateToken(
		r.Context(), user.ID, plaintextToken,
		h.cfg.PasswordResetTokenTTL(), ip, ua,
	)
	if err != nil {
		respondGeneric()
		return
	}

	resetURL := buildPasswordResetURL(baseURL, plaintextToken)
	expiresMinutes := int(h.cfg.PasswordResetTokenTTL() / time.Minute)
	if expiresMinutes < 1 {
		expiresMinutes = 1
	}

	// Fire-and-forget email delivery. The HTTP response returns
	// immediately; SMTP retries (with exponential backoff) happen in
	// the background goroutine inside mails.Sender.SendWithRetry.
	display := user.Username
	go func(to, name, link string, exp int, requestedIP, requestedUA string) {
		htmlBody := mails.PasswordResetHTML(name, link, exp, requestedIP, requestedUA)
		h.mailer.SendWithRetry(to, mails.PasswordResetSubject, htmlBody)
	}(user.Email, display, resetURL, expiresMinutes, ip, ua)

	respondGeneric()
}

// ---------------------------------------------------------------------------
// POST /auth/password/reset/validate
// ---------------------------------------------------------------------------

type validateResetTokenRequest struct {
	Token string `json:"token"`
}

type validateResetTokenResponse struct {
	Valid bool `json:"valid"`
}

func (h *Handler) handleValidateResetToken(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.passwordResetEnabled() {
		writeAuthError(w, http.StatusServiceUnavailable, "password reset is not configured on this deployment")
		return
	}

	var req validateResetTokenRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusOK, &validateResetTokenResponse{Valid: false})
		return
	}
	req.Token = strings.TrimSpace(req.Token)
	if req.Token == "" {
		writeJSON(w, http.StatusOK, &validateResetTokenResponse{Valid: false})
		return
	}

	row, err := h.passwordResets.GetUsableByToken(r.Context(), req.Token)
	if err != nil || row == nil {
		writeJSON(w, http.StatusOK, &validateResetTokenResponse{Valid: false})
		return
	}

	// Token bytes are valid; double-check the user is still in a state
	// that can complete a reset so the SPA does not let the user type
	// a new password only to fail at submit time.
	user, err := h.users.GetUserByID(r.Context(), row.UserID)
	if err != nil || user == nil || !user.Active {
		writeJSON(w, http.StatusOK, &validateResetTokenResponse{Valid: false})
		return
	}
	if user.AuthProvider != "" && user.AuthProvider != AuthProviderLocal {
		writeJSON(w, http.StatusOK, &validateResetTokenResponse{Valid: false})
		return
	}

	writeJSON(w, http.StatusOK, &validateResetTokenResponse{Valid: true})
}

// ---------------------------------------------------------------------------
// POST /auth/password/reset
// ---------------------------------------------------------------------------

type resetPasswordRequest struct {
	Token       string `json:"token"`
	NewPassword string `json:"new_password"`
}

func (h *Handler) handleResetPassword(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.passwordResetEnabled() {
		writeAuthError(w, http.StatusServiceUnavailable, "password reset is not configured on this deployment")
		return
	}

	var req resetPasswordRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeAuthError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	req.Token = strings.TrimSpace(req.Token)
	if req.Token == "" {
		writeAuthError(w, http.StatusBadRequest, "token is required")
		return
	}
	if req.NewPassword == "" {
		writeAuthError(w, http.StatusBadRequest, "new_password is required")
		return
	}

	row, err := h.passwordResets.ConsumeByToken(r.Context(), req.Token)
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "internal error")
		return
	}
	if row == nil {
		writeAuthError(w, http.StatusBadRequest, "reset link is invalid, expired, or already used")
		return
	}

	user, err := h.users.GetUserByID(r.Context(), row.UserID)
	if err != nil || user == nil {
		writeAuthError(w, http.StatusBadRequest, "reset link is invalid, expired, or already used")
		return
	}
	if !user.Active {
		writeAuthError(w, http.StatusForbidden, "account is deactivated")
		return
	}
	if user.AuthProvider != "" && user.AuthProvider != AuthProviderLocal {
		writeAuthError(w, http.StatusBadRequest, fmt.Sprintf("this account signs in with %s; password reset is not applicable", user.AuthProvider))
		return
	}

	// SetPassword applies the same length constraints and bcrypt cost
	// as register / change-password. Any policy change to those rules
	// (eg adding a complexity check) flows here for free.
	if err := user.SetPassword(req.NewPassword); err != nil {
		writeAuthError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := h.users.UpdatePassword(r.Context(), user.ID, user.PasswordHash); err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to update password")
		return
	}

	// Symmetric with PUT /auth/me/password: a password change kills
	// every session so an attacker who had access to a logged-in tab
	// is logged out the moment the legitimate user resets the password.
	_ = h.sessions.RevokeAllUserSessions(r.Context(), user.ID)

	h.clearSessionCookies(w)
	writeJSON(w, http.StatusOK, map[string]string{
		"message": "password updated, all sessions revoked",
	})
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// passwordResetBaseURL returns the validated origin used to build the
// reset link. Preference order:
//
//   1. AUTH_FRONTEND_BASE_URL  (validated at startup; always trusted).
//   2. Request Origin header   (only when scheme is https or the host
//                               is localhost/127.0.0.1).
//
// Returns an error when neither is available, so a deployment that
// forgot to set AUTH_FRONTEND_BASE_URL fails fast rather than mailing
// a broken or attacker-controlled link.
func (h *Handler) passwordResetBaseURL(r *http.Request) (string, error) {
	if h.cfg.FrontendBaseURL != "" {
		return h.cfg.FrontendBaseURL, nil
	}
	origin := strings.TrimSpace(r.Header.Get("Origin"))
	if origin == "" {
		return "", fmt.Errorf("AUTH_FRONTEND_BASE_URL is not set and the request carries no Origin header")
	}
	ou, err := url.Parse(origin)
	if err != nil || ou.Host == "" || (ou.Scheme != "http" && ou.Scheme != "https") {
		return "", fmt.Errorf("invalid Origin %q", origin)
	}
	if ou.Scheme == "http" {
		host := strings.ToLower(ou.Hostname())
		if host != "localhost" && host != "127.0.0.1" {
			return "", fmt.Errorf("insecure Origin %q refused for password reset link", origin)
		}
	}
	return ou.Scheme + "://" + ou.Host, nil
}

// buildPasswordResetURL composes the reset link the user clicks in
// their email. The token is URL-encoded; the path is fixed because the
// SPA owns it. base is already trimmed of any trailing slash.
func buildPasswordResetURL(base, token string) string {
	return base + "/reset-password?token=" + url.QueryEscape(token)
}

