package auth

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
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

	// passwordResetGenericRedemptionFailure is the single user-facing
	// message returned for every failure path of POST /auth/password/reset
	// EXCEPT internal-server faults. Sharing one string across the
	// not-found / expired / consumed / inactive-user / federated-user
	// branches means a presented token cannot be used as an oracle for
	// the account's lifecycle state.
	passwordResetGenericRedemptionFailure = "reset link is invalid, expired, or already used"

	// passwordResetUserWindow / passwordResetUserMax cap the number of
	// reset requests a single user can trigger in a rolling window. The
	// limit is intentionally generous (legitimate users retry a couple
	// of times) but tight enough that a botnet rotating IPs cannot use
	// the endpoint as a mailbomb against one address.
	passwordResetUserWindow = 15 * time.Minute
	passwordResetUserMax    = 5

	// passwordResetMaxBodyBytes caps the JSON body each public reset
	// endpoint will read. The largest legitimate body is the redemption
	// request: {"token":"<64 hex chars>","new_password":"<<=72 chars>"}
	// which fits in well under 256 bytes. 4 KiB is far above any
	// legitimate payload and small enough that an attacker cannot make
	// the gateway buffer a multi-MB blob just to have it rejected.
	passwordResetMaxBodyBytes int64 = 4 << 10

	// Skip-reason codes used by the silent-skip telemetry on /forgot.
	// Stable strings so dashboards / alerts can match on them.
	skipReasonUserNotFound       = "user_not_found"
	skipReasonUserInactive       = "user_inactive"
	skipReasonUserFederated      = "user_federated"
	skipReasonPerUserRateLimited = "per_user_rate_limited"
	skipReasonLookupFailed       = "lookup_failed"
	skipReasonTokenGenFailed     = "token_generation_failed"
	skipReasonPersistFailed      = "persist_failed"
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
	if err := decodeResetJSON(w, r, &req); err != nil {
		return // decodeResetJSON already wrote the error response
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

	ip := h.cfg.IPResolver().Resolve(r)
	ua := r.UserAgent()
	emailFP := emailFingerprint(email)

	user, err := h.users.GetUserByEmail(r.Context(), email)
	if err != nil {
		// Internal lookup failures must not leak as 500 because that
		// makes the endpoint behave differently when an email exists
		// (cheap path) vs doesn't (DB miss). Log and return generic.
		h.logForgotSkip(skipReasonLookupFailed, emailFP, ip, "")
		respondGeneric()
		return
	}
	if user == nil {
		h.logForgotSkip(skipReasonUserNotFound, emailFP, ip, "")
		respondGeneric()
		return
	}
	if !user.Active {
		h.logForgotSkip(skipReasonUserInactive, emailFP, ip, user.ID)
		respondGeneric()
		return
	}
	// Federated accounts have no local password; mailing a reset link
	// would be pointless and the redemption handler would reject it.
	if user.AuthProvider != "" && user.AuthProvider != AuthProviderLocal {
		h.logForgotSkip(skipReasonUserFederated, emailFP, ip, user.ID)
		respondGeneric()
		return
	}

	// Per-user soft rate limit. CountRecentRequests is cheap; it sits
	// on top of the IP limiter that already gates the route.
	count, err := h.passwordResets.CountRecentRequests(r.Context(), user.ID, passwordResetUserWindow)
	if err == nil && count >= passwordResetUserMax {
		h.logForgotSkip(skipReasonPerUserRateLimited, emailFP, ip, user.ID)
		respondGeneric()
		return
	}

	plaintextToken, err := GeneratePasswordResetToken()
	if err != nil {
		h.logForgotSkip(skipReasonTokenGenFailed, emailFP, ip, user.ID)
		respondGeneric()
		return
	}

	_, err = h.passwordResets.CreateToken(
		r.Context(), user.ID, plaintextToken,
		h.cfg.PasswordResetTokenTTL(), ip, ua,
	)
	if err != nil {
		h.logForgotSkip(skipReasonPersistFailed, emailFP, ip, user.ID)
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

	// Recovery-attempt monitoring: the success path. Audit ref: B4.
	PasswordResetRequestsTotal.WithLabelValues(recoveryRequestDispatched).Inc()

	h.log.Info().
		Str("event", "password_reset_email_dispatched").
		Str("user_id", user.ID).
		Str("email_fp", emailFP).
		Str("client_ip", ip).
		Int("expires_minutes", expiresMinutes).
		Msg("password_reset_requested")

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
	if err := decodeResetJSONSilent(r, &req); err != nil {
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
	if err := decodeResetJSON(w, r, &req); err != nil {
		return // decodeResetJSON already wrote the error response
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
		PasswordResetRedemptionsTotal.WithLabelValues(recoveryRedeemInternalError).Inc()
		writeAuthError(w, http.StatusInternalServerError, "internal error")
		return
	}
	if row == nil {
		PasswordResetRedemptionsTotal.WithLabelValues(recoveryRedeemInvalidExpired).Inc()
		writeAuthError(w, http.StatusBadRequest, passwordResetGenericRedemptionFailure)
		return
	}

	user, err := h.users.GetUserByID(r.Context(), row.UserID)
	if err != nil || user == nil {
		PasswordResetRedemptionsTotal.WithLabelValues(recoveryRedeemInvalidExpired).Inc()
		writeAuthError(w, http.StatusBadRequest, passwordResetGenericRedemptionFailure)
		return
	}
	if !user.Active {
		// Deliberately collapsed into the generic redemption-failure
		// message so the response is indistinguishable from
		// not-found / expired / consumed. A separate 403 here would
		// leak the existence of a deactivated account that an
		// attacker holds a stale token for.
		PasswordResetRedemptionsTotal.WithLabelValues(recoveryRedeemInvalidExpired).Inc()
		writeAuthError(w, http.StatusBadRequest, passwordResetGenericRedemptionFailure)
		return
	}
	if user.AuthProvider != "" && user.AuthProvider != AuthProviderLocal {
		// M4: collapse the federated branch into the generic message
		// so a presented token does not leak the provider name. The
		// scenario is essentially unreachable (/forgot never mails
		// federated accounts) but defence in depth.
		PasswordResetRedemptionsTotal.WithLabelValues(recoveryRedeemInvalidExpired).Inc()
		writeAuthError(w, http.StatusBadRequest, passwordResetGenericRedemptionFailure)
		return
	}

	// Enforce the same NEW-password policy as register / change-
	// password: complexity (offline) then the advisory breach check
	// (network, fail-open). SetPassword re-validates complexity as a
	// backstop.
	if err := ValidatePasswordComplexity(req.NewPassword, user.Username, user.Email); err != nil {
		PasswordResetRedemptionsTotal.WithLabelValues(recoveryRedeemComplexity).Inc()
		writeAuthError(w, http.StatusBadRequest, err.Error())
		return
	}
	if !h.rejectReusedPassword(w, r, user.ID, req.NewPassword) {
		PasswordResetRedemptionsTotal.WithLabelValues(recoveryRedeemReused).Inc()
		return
	}
	if !h.checkBreachAllowed(w, r, req.NewPassword) {
		PasswordResetRedemptionsTotal.WithLabelValues(recoveryRedeemBreached).Inc()
		return
	}

	if err := user.SetPassword(req.NewPassword); err != nil {
		PasswordResetRedemptionsTotal.WithLabelValues(recoveryRedeemComplexity).Inc()
		writeAuthError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := h.users.UpdatePassword(r.Context(), user.ID, user.PasswordHash); err != nil {
		PasswordResetRedemptionsTotal.WithLabelValues(recoveryRedeemPersistFailed).Inc()
		writeAuthError(w, http.StatusInternalServerError, "failed to update password")
		return
	}

	h.recordPasswordHistory(r, user.ID, user.PasswordHash)

	// Symmetric with PUT /auth/me/password: a password change kills
	// every session so an attacker who had access to a logged-in tab
	// is logged out the moment the legitimate user resets the password.
	_ = h.sessions.RevokeAllUserSessions(r.Context(), user.ID)

	// And the long-lived service tokens, which are outside the session
	// store. A reset is an account-recovery action, so any service
	// token minted under the old credential must die too. Best-effort.
	if _, err := h.users.BumpTokenEpoch(r.Context(), user.ID); err != nil {
		h.log.Warn().Err(err).Str("user_id", user.ID).Msg("token_epoch_bump_failed_on_password_reset")
	}

	// Anti-ATO: confirm the reset out-of-band. Symmetric with
	// PUT /auth/me/password.
	h.notifyPasswordChanged(r, user)

	h.clearSessionCookies(w)

	// Recovery-attempt monitoring: the success path. Audit ref: B4.
	PasswordResetRedemptionsTotal.WithLabelValues(recoveryRedeemed).Inc()

	h.log.Info().
		Str("event", "password_reset_completed").
		Str("user_id", user.ID).
		Str("client_ip", h.cfg.IPResolver().Resolve(r)).
		Msg("password_reset_redeemed")

	writeJSON(w, http.StatusOK, map[string]string{
		"message": "password updated, all sessions revoked",
	})
}

// ---------------------------------------------------------------------------
// GET /auth/password/policy
//
// Public, read-only, no DB access. The SPA hits this once on the
// forgot-password screen to display the real expiry minutes (instead
// of a hard-coded literal that would drift the moment an operator
// overrides AUTH_PASSWORD_RESET_TOKEN_TTL_SECONDS) and the real
// min/max password length used by the reset form's client-side
// validation. ResetEnabled mirrors h.passwordResetEnabled() so the
// SPA can render a graceful 'feature unavailable' card on a deployment
// where the operator wired no mailer.
// ---------------------------------------------------------------------------

type passwordPolicyResponse struct {
	ResetEnabled         bool `json:"reset_enabled"`
	TokenExpiresMinutes  int  `json:"token_expires_minutes"`
	PasswordMinLength    int  `json:"password_min_length"`
	PasswordMaxLength    int  `json:"password_max_length"`
}

func (h *Handler) handlePasswordPolicy(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	expiresMinutes := int(h.cfg.PasswordResetTokenTTL() / time.Minute)
	if expiresMinutes < 1 {
		expiresMinutes = 1
	}

	writeJSON(w, http.StatusOK, &passwordPolicyResponse{
		ResetEnabled:        h.passwordResetEnabled(),
		TokenExpiresMinutes: expiresMinutes,
		PasswordMinLength:   PasswordMinLength,
		PasswordMaxLength:   PasswordMaxLength,
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

// ---------------------------------------------------------------------------
// JSON body helpers + observability
// ---------------------------------------------------------------------------

// decodeResetJSON wraps r.Body in an http.MaxBytesReader (4 KiB) and
// decodes into out. On any failure it writes a 400 (or 413, for the
// size cap) and returns the error so the caller can early-return
// without writing a second response.
func decodeResetJSON(w http.ResponseWriter, r *http.Request, out interface{}) error {
	r.Body = http.MaxBytesReader(w, r.Body, passwordResetMaxBodyBytes)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(out); err != nil {
		var maxBytesErr *http.MaxBytesError
		if errors.As(err, &maxBytesErr) {
			writeAuthError(w, http.StatusRequestEntityTooLarge, "request body too large")
			return err
		}
		writeAuthError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return err
	}
	return nil
}

// decodeResetJSONSilent is the variant used by /reset/validate, where
// every failure mode (including oversize, malformed JSON, empty body)
// is mapped to the same {valid:false} response by the caller. The
// caller writes the response; we just bound the read.
func decodeResetJSONSilent(r *http.Request, out interface{}) error {
	// Use a discard ResponseWriter-ish bound: MaxBytesReader needs an
	// http.ResponseWriter only to set the connection-close hint on
	// oversize; we pass nil to suppress that side-effect and let the
	// caller decide how to respond. Inspect via errors.As below.
	r.Body = http.MaxBytesReader(nil, r.Body, passwordResetMaxBodyBytes)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	return dec.Decode(out)
}

// logForgotSkip emits a debug-level structured event on every silent-
// skip branch of POST /auth/password/forgot. Reasons are stable string
// constants so dashboards can match on them. The email is never logged
// in plaintext; emailFingerprint() returns a short SHA-256 prefix that
// stays stable across requests for safe correlation without exposing
// PII to the log stream.
func (h *Handler) logForgotSkip(reason, emailFP, clientIP, userID string) {
	// Recovery-attempt monitoring (CHECKLIST Tier 1): mirror every
	// silent-skip branch onto the metrics rail with the SAME reason
	// string the log carries, so an operator can alert on
	// enumeration / mailbomb / ATO-probe spikes without log-scraping.
	// The wire response is unchanged (generic 202). Audit ref: B4.
	PasswordResetRequestsTotal.WithLabelValues(reason).Inc()

	ev := h.log.Debug().
		Str("event", "password_reset_forgot_skipped").
		Str("reason", reason).
		Str("email_fp", emailFP).
		Str("client_ip", clientIP)
	if userID != "" {
		ev = ev.Str("user_id", userID)
	}
	ev.Msg("password_reset_forgot_skipped")
}

// emailFingerprint returns a stable 16-hex-char prefix of SHA-256 of
// the lowercased trimmed email. Used in logs so operators can correlate
// repeated reset requests for the same address without ever writing
// the address itself to disk.
func emailFingerprint(email string) string {
	sum := sha256.Sum256([]byte(strings.ToLower(strings.TrimSpace(email))))
	return hex.EncodeToString(sum[:])[:16]
}


