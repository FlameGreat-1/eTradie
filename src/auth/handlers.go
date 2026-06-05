package auth

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/rs/zerolog"
)

// writeSessionCookies issues a fresh CSRF token bound to the user and
// writes all three auth cookies on the response. Called from every
// code path that mints or rotates a session (login, register, refresh,
// OAuth sign-in callback). Centralised so a policy change (renamed
// CSRF cookie, tightened SameSite, signed/unsigned toggle) is a
// one-line edit.
//
// CSRF token generation failure does NOT abort the request. The
// rotated session is still valid for read-only calls; the SPA will
// hit GET /auth/me, see the user, and retry the next mutating call
// after a refresh that does mint a CSRF token. Surfacing the failure
// as a 500 here would lock the user out of an account they just
// successfully authenticated against.
func (h *Handler) writeSessionCookies(w http.ResponseWriter, userID, accessToken, refreshToken string) {
	opts := h.cfg.CookieOptions()
	SetAccessCookie(w, opts, accessToken)
	SetRefreshCookie(w, opts, refreshToken)
	if csrf, err := GenerateCSRFToken(h.cfg.JWTSecretBytes(), userID, h.cfg.CSRFSigned); err == nil {
		SetCSRFCookie(w, opts, csrf)
	}
}

// clearSessionCookies expires all auth cookies (prefixed + unprefixed).
func (h *Handler) clearSessionCookies(w http.ResponseWriter) {
	ClearAuthCookies(w, h.cfg.CookieOptions())
}

// maybeTokenPair returns pair when AUTH_RETURN_TOKENS_IN_BODY is true,
// otherwise nil. Used to keep the JSON response shape stable for
// legacy clients while defaulting to cookie-only on the wire.
func (h *Handler) maybeTokenPair(pair *TokenPair) *TokenPair {
	if h.cfg.ReturnTokensInBody {
		return pair
	}
	return nil
}

// CSRFHeader exposes the configured request header name the SPA
// echoes the csrf_token cookie back in (default: "X-CSRF-Token").
// Consumed by the gateway HTTP server to build the CORS Allow-Headers
// list dynamically.
func (h *Handler) CSRFHeader() string {
	return h.cfg.CSRFHeader
}

// AuthConfig returns the underlying auth.Config so the gateway HTTP
// server can build the RequireCSRF middleware with the right (*Config)
// signature without taking a direct dependency on the Handler internals.
func (h *Handler) AuthConfig() *Config {
	return h.cfg
}

// Handler serves the authentication REST API endpoints.
type Handler struct {
	users    *UserStore
	sessions *SessionStore
	tokens   *TokenService
	cfg      *Config

	oauthEnabled    bool
	oauthFlows      *OAuthFlowStore
	oauthIdentities *OAuthIdentityStore
	googleProvider  *GoogleOAuthProvider

	// Password reset (forgot password) dependencies. nil when
	// WithPasswordReset has not been called; in that case the
	// forgot/reset endpoints return 503.
	passwordResets *PasswordResetStore
	mailer         Mailer

	// log is the structured logger used for silent-skip telemetry on
	// the password-reset endpoints (and any future handler that needs
	// observability without changing its wire response). Defaults to a
	// no-op logger when WithLogger has not been called so unit tests
	// do not need to inject one and a half-wired Handler still serves
	// traffic safely.
	log zerolog.Logger

	// attempts is the cluster-wide abuse-control limiter (rate limit +
	// per-account lockout) for the credential-attack surface
	// (login/register/refresh). Injected by the gateway with a
	// Redis-backed implementation (mandatory in prod/staging) via
	// WithAttemptLimiter. When nil, the per-route in-memory limiter
	// applied in RegisterRoutes is the only control — a posture the
	// gateway wiring permits ONLY in dev/test.
	attempts AttemptLimiter

	// breach is the advisory password-breach checker (HIBP). Injected
	// via WithBreachChecker. Applied when a NEW password is stored
	// (register / change / reset). Fail-open: an error never blocks the
	// user. nil disables the check.
	breach BreachChecker
}

// NewHandler creates the auth HTTP handler.
func NewHandler(users *UserStore, sessions *SessionStore, tokens *TokenService, cfg *Config) *Handler {
	return &Handler{
		users:    users,
		sessions: sessions,
		tokens:   tokens,
		cfg:      cfg,
		log:      zerolog.Nop(),
	}
}

// WithLogger attaches a structured logger. Symmetric with WithOAuth /
// WithPasswordReset; safe to call exactly once at startup before any
// route serves traffic.
func (h *Handler) WithLogger(log zerolog.Logger) {
	h.log = log
}

// WithAttemptLimiter injects the cluster-wide abuse-control limiter.
// Symmetric with WithOAuth / WithPasswordReset; called once at startup
// before any route serves traffic. The gateway passes a Redis-backed
// implementation (mandatory in prod/staging). When never called, the
// login/register/refresh routes fall back to the per-route in-memory
// limiter wired in RegisterRoutes — a dev/test-only posture.
func (h *Handler) WithAttemptLimiter(a AttemptLimiter) {
	h.attempts = a
}

// WithBreachChecker injects the advisory password-breach checker (HIBP).
// Symmetric with the other With* injectors; call once at startup.
func (h *Handler) WithBreachChecker(b BreachChecker) {
	h.breach = b
}

// checkBreachAllowed enforces the breach policy for a NEW password.
// Returns true when the password may be stored. On a confirmed breach
// it writes a 400 and returns false. On a checker error it fails OPEN
// (logs, returns true) so an HIBP outage never blocks a password set.
// When no checker is injected the feature is disabled and it returns
// true.
func (h *Handler) checkBreachAllowed(w http.ResponseWriter, r *http.Request, plaintext string) bool {
	if h.breach == nil {
		return true
	}
	breached, err := h.breach.IsBreached(r.Context(), plaintext)
	if err != nil {
		h.log.Warn().Err(err).Msg("password_breach_check_failed_failing_open")
		return true
	}
	if breached {
		writeAuthError(w, http.StatusBadRequest,
			"this password has appeared in a known data breach; please choose a different password")
		return false
	}
	return true
}

// rateGate applies the cluster-wide rate limit for the given scope when
// an AttemptLimiter is injected. Returns true when the request may
// proceed. On denial it writes a 429 with Retry-After and returns false
// so the caller early-returns. When no limiter is injected it returns
// true (the per-route in-memory limiter from RegisterRoutes is then the
// active control), so this is safe to call unconditionally.
func (h *Handler) rateGate(w http.ResponseWriter, r *http.Request, scope string) bool {
	if h.attempts == nil {
		return true
	}
	ip := h.cfg.IPResolver().Resolve(r)
	allowed, retryAfter := h.attempts.AllowRequest(r.Context(), scope, ip)
	if allowed {
		return true
	}
	writeRetryAfter(w, retryAfter)
	writeAuthError(w, http.StatusTooManyRequests, "rate limit exceeded, try again later")
	return false
}

// writeRetryAfter sets the Retry-After header (seconds, rounded up, min 1).
func writeRetryAfter(w http.ResponseWriter, d time.Duration) {
	secs := int(d.Seconds())
	if d > 0 && secs < 1 {
		secs = 1
	}
	if secs < 0 {
		secs = 0
	}
	if secs > 0 {
		w.Header().Set("Retry-After", fmt.Sprintf("%d", secs))
	}
}

// RegisterRoutes mounts all auth routes on the given mux.
//
// /auth/logout is mounted with OptionalAuth so a user whose access
// cookie has expired but who still holds a refresh cookie can clear
// the browser jar without first refreshing. The handler reads the
// refresh-token body field (or refresh cookie) to revoke the session
// when possible; cookie clearing happens regardless.
func (h *Handler) RegisterRoutes(mux *http.ServeMux, ts *TokenService) {
	loginLimiter := NewRateLimiter(10, 1*time.Minute)
	registerLimiter := NewRateLimiter(5, 1*time.Minute)
	refreshLimiter := NewRateLimiter(20, 1*time.Minute)
	oauthStartLimiter := NewRateLimiter(20, 1*time.Minute)
	oauthCallbackLimiter := NewRateLimiter(20, 1*time.Minute)
	logoutLimiter := NewRateLimiter(60, 1*time.Minute)
	forgotPasswordLimiter := NewRateLimiter(5, 1*time.Minute)
	resetValidateLimiter := NewRateLimiter(30, 1*time.Minute)
	resetPasswordLimiter := NewRateLimiter(10, 1*time.Minute)
	passwordPolicyLimiter := NewRateLimiter(60, 1*time.Minute)

	resolver := h.cfg.IPResolver()

	// Public endpoints (no auth, rate-limited).
	mux.HandleFunc("/auth/login", loginLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleLogin))
	mux.HandleFunc("/auth/register", registerLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleRegister))
	mux.HandleFunc("/auth/refresh", refreshLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleRefresh))

	// OAuth 2.0 sign-in endpoints (public, rate-limited).
	mux.HandleFunc("/auth/oauth/google/start", oauthStartLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleOAuthGoogleStart))
	mux.HandleFunc("/auth/oauth/google/callback", oauthCallbackLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleOAuthGoogleCallback))

	// Forgot / reset password endpoints (public, rate-limited).
	// The three routes are independent so the SPA can validate a
	// token without mutating it (UX: render the form vs the "link
	// expired" screen) and then redeem it with a separate POST.
	mux.HandleFunc("/auth/password/forgot", forgotPasswordLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleForgotPassword))
	mux.HandleFunc("/auth/password/reset/validate", resetValidateLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleValidateResetToken))
	mux.HandleFunc("/auth/password/reset", resetPasswordLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleResetPassword))
	mux.HandleFunc("/auth/password/policy", passwordPolicyLimiter.RateLimitMiddlewareWithResolver(resolver, h.handlePasswordPolicy))

	// Logout: OptionalAuth + rate-limited. Even an unauthenticated
	// request reaches the handler so the cookie jar can be cleared.
	mux.Handle("/auth/logout", OptionalAuth(ts)(http.HandlerFunc(
		logoutLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleLogout),
	)))

	// Protected endpoints (any authenticated user).
	mux.Handle("/auth/logout-all", RequireAuthFunc(ts, h.handleLogoutAll))
	mux.Handle("/auth/me", RequireAuthFunc(ts, h.handleMe))
	mux.Handle("/auth/me/password", RequireAuthFunc(ts, h.handleChangePassword))

	mux.Handle("/auth/oauth/google/link/start", RequireAuthFunc(ts, h.handleOAuthGoogleLinkStart))
	mux.Handle("/auth/oauth/google/link/callback", RequireAuthFunc(ts, h.handleOAuthGoogleLinkCallback))
	mux.Handle("/auth/oauth/google/link", RequireAuthFunc(ts, h.handleOAuthGoogleUnlink))

	mux.Handle("/auth/admin/users", RequireAdminFunc(ts, h.handleAdminUsers))
	mux.Handle("/auth/admin/users/", RequireAdminFunc(ts, h.handleAdminUserAction))
}

// ---------------------------------------------------------------------------
// POST /auth/login
// ---------------------------------------------------------------------------

type loginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

func (h *Handler) handleLogin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	var req loginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeAuthError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	req.Username = strings.TrimSpace(req.Username)
	if req.Username == "" || req.Password == "" {
		writeAuthError(w, http.StatusBadRequest, "username and password are required")
		return
	}

	// Cluster-wide IP rate gate (defeats per-pod-limit bypass at scale).
	if !h.rateGate(w, r, ScopeLogin) {
		return
	}

	// Per-account lockout key. Normalised so the counter is stable
	// across case/whitespace variants of the same username.
	accountKey := strings.ToLower(req.Username)

	// Pre-check the lock BEFORE any DB read or password compute so a
	// locked account costs no work and a generic 429 is returned.
	if h.attempts != nil {
		if locked, retryAfter := h.attempts.IsLocked(r.Context(), accountKey); locked {
			writeRetryAfter(w, retryAfter)
			writeAuthError(w, http.StatusTooManyRequests, "too many failed attempts; account temporarily locked, try again later")
			return
		}
	}

	user, err := h.users.GetUserByUsername(r.Context(), req.Username)
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "internal error")
		return
	}
	if user == nil {
		writeAuthError(w, http.StatusUnauthorized, "invalid username or password")
		return
	}
	if !user.Active {
		writeAuthError(w, http.StatusForbidden, "account is deactivated")
		return
	}
	if err := user.CheckPassword(req.Password); err != nil {
		// Record the failure against the account and, if it crosses the
		// lockout threshold, surface a 429 + Retry-After so the client
		// learns to back off. The wording is intentionally close to the
		// rate-limit message and never confirms whether the username
		// exists.
		if h.attempts != nil {
			if locked, retryAfter := h.attempts.RegisterFailure(r.Context(), accountKey); locked {
				writeRetryAfter(w, retryAfter)
				writeAuthError(w, http.StatusTooManyRequests, "too many failed attempts; account temporarily locked, try again later")
				return
			}
		}
		writeAuthError(w, http.StatusUnauthorized, "invalid username or password")
		return
	}

	// Successful credential check: clear the failed-attempt counter.
	if h.attempts != nil {
		h.attempts.ResetFailures(r.Context(), accountKey)
	}

	// Transparent hash upgrade: if the stored hash is legacy bcrypt (or
	// weaker-parameter Argon2id), re-hash the just-verified plaintext
	// with current Argon2id parameters and persist it. Non-fatal: a
	// failure here must never block an otherwise-valid login, so the
	// error is logged and the login proceeds (the upgrade retries on
	// the next sign-in).
	if user.NeedsPasswordRehash() {
		if err := user.SetPassword(req.Password); err == nil {
			if err := h.users.UpdatePassword(r.Context(), user.ID, user.PasswordHash); err != nil {
				h.log.Warn().Err(err).Str("user_id", user.ID).Msg("password_rehash_persist_failed")
			} else {
				h.log.Info().Str("user_id", user.ID).Msg("password_hash_upgraded_to_argon2id")
			}
		} else {
			h.log.Warn().Err(err).Str("user_id", user.ID).Msg("password_rehash_compute_failed")
		}
	}

	pair, rawRefresh, err := h.tokens.IssueTokenPair(user)
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to issue tokens")
		return
	}

	count, _ := h.sessions.CountActiveSessions(r.Context(), user.ID)
	if count >= h.cfg.MaxSessionsPerUser {
		_ = h.sessions.RevokeOldestSession(r.Context(), user.ID)
	}

	now := time.Now().UTC()
	sess := &Session{
		ID:           GenerateID(),
		UserID:       user.ID,
		RefreshToken: rawRefresh,
		UserAgent:    r.UserAgent(),
		ClientIP:     h.cfg.IPResolver().Resolve(r),
		ExpiresAt:    now.Add(h.tokens.RefreshTokenTTL()),
		CreatedAt:    now,
		Revoked:      false,
	}
	if err := h.sessions.CreateSession(r.Context(), sess); err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to create session")
		return
	}

	_ = h.users.UpdateLastLogin(r.Context(), user.ID)

	h.writeSessionCookies(w, user.ID, pair.AccessToken, rawRefresh)
	writeJSON(w, http.StatusOK, h.loginResponseBody(user, pair))
}

// loginResponseBody composes the legacy-shaped JSON response. Tokens
// are omitted unless AUTH_RETURN_TOKENS_IN_BODY is true so a default
// cookie-auth deployment does not re-introduce the JS-readable token
// surface.
func (h *Handler) loginResponseBody(user *User, pair *TokenPair) map[string]interface{} {
	body := map[string]interface{}{
		"user":       userPublicView(user),
		"token_type": pair.TokenType,
		"expires_in": pair.ExpiresIn,
	}
	if tp := h.maybeTokenPair(pair); tp != nil {
		body["access_token"] = tp.AccessToken
		body["refresh_token"] = tp.RefreshToken
	}
	return body
}

// ---------------------------------------------------------------------------
// POST /auth/register
// ---------------------------------------------------------------------------

type registerRequest struct {
	Username string `json:"username"`
	Email    string `json:"email"`
	Password string `json:"password"`
}

func (h *Handler) handleRegister(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	if !h.rateGate(w, r, ScopeRegister) {
		return
	}

	var req registerRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeAuthError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	req.Username = strings.TrimSpace(req.Username)
	req.Email = strings.TrimSpace(strings.ToLower(req.Email))

	if req.Username == "" || req.Email == "" || req.Password == "" {
		writeAuthError(w, http.StatusBadRequest, "username, email, and password are required")
		return
	}
	if len(req.Username) < 3 || len(req.Username) > 32 {
		writeAuthError(w, http.StatusBadRequest, "username must be 3-32 characters")
		return
	}
	if !strings.Contains(req.Email, "@") {
		writeAuthError(w, http.StatusBadRequest, "invalid email address")
		return
	}

	now := time.Now().UTC()
	user := &User{
		ID:        GenerateID(),
		Username:  req.Username,
		Email:     req.Email,
		Role:      RoleEtradie,
		Active:    true,
		CreatedAt: now,
		UpdatedAt: now,
	}

	// Complexity first (cheap, offline), then the advisory breach check
	// (network, fail-open) only once the password is otherwise valid.
	if err := ValidatePasswordComplexity(req.Password, req.Username, req.Email); err != nil {
		writeAuthError(w, http.StatusBadRequest, err.Error())
		return
	}
	if !h.checkBreachAllowed(w, r, req.Password) {
		return
	}

	if err := user.SetPassword(req.Password); err != nil {
		writeAuthError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := h.users.CreateUser(r.Context(), user); err != nil {
		if strings.Contains(err.Error(), "already exists") {
			writeAuthError(w, http.StatusConflict, err.Error())
			return
		}
		writeAuthError(w, http.StatusInternalServerError, "failed to create user")
		return
	}

	pair, rawRefresh, err := h.tokens.IssueTokenPair(user)
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "user created but failed to issue tokens")
		return
	}

	sess := &Session{
		ID:           GenerateID(),
		UserID:       user.ID,
		RefreshToken: rawRefresh,
		UserAgent:    r.UserAgent(),
		ClientIP:     h.cfg.IPResolver().Resolve(r),
		ExpiresAt:    now.Add(h.tokens.RefreshTokenTTL()),
		CreatedAt:    now,
		Revoked:      false,
	}
	_ = h.sessions.CreateSession(r.Context(), sess)

	h.writeSessionCookies(w, user.ID, pair.AccessToken, rawRefresh)
	writeJSON(w, http.StatusCreated, h.loginResponseBody(user, pair))
}

// ---------------------------------------------------------------------------
// POST /auth/refresh
// ---------------------------------------------------------------------------

type refreshRequest struct {
	RefreshToken string `json:"refresh_token"`
}

func (h *Handler) handleRefresh(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	if !h.rateGate(w, r, ScopeRefresh) {
		return
	}

	var req refreshRequest
	if r.Body != nil && r.ContentLength != 0 {
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeAuthError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
			return
		}
	}
	if req.RefreshToken == "" {
		req.RefreshToken = RefreshTokenFromCookie(r)
	}
	if req.RefreshToken == "" {
		writeAuthError(w, http.StatusBadRequest, "refresh_token is required")
		return
	}

	sess, err := h.sessions.GetSessionByToken(r.Context(), req.RefreshToken)
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "internal error")
		return
	}
	if sess == nil {
		writeAuthError(w, http.StatusUnauthorized, "invalid refresh token")
		return
	}

	// Refresh-token reuse detection. A token that maps to a session
	// which is REVOKED but NOT yet expired has already been rotated
	// once: presenting it again means either the legitimate client
	// replayed an old token OR the token was stolen and the thief (or
	// victim) is racing the rotation. Either way it is a theft signal.
	// Contain it by revoking the user's ENTIRE session family so the
	// token held by BOTH parties is dead and a fresh login is required.
	if sess.Revoked && !sess.IsExpired() {
		_ = h.sessions.RevokeAllUserSessions(r.Context(), sess.UserID)
		h.clearSessionCookies(w)
		h.log.Warn().
			Str("event", "refresh_token_reuse_detected").
			Str("user_id", sess.UserID).
			Str("session_id", sess.ID).
			Str("client_ip", h.cfg.IPResolver().Resolve(r)).
			Msg("refresh_token_reuse_detected_all_sessions_revoked")
		writeAuthError(w, http.StatusUnauthorized, "refresh token reuse detected; all sessions revoked, please sign in again")
		return
	}
	if !sess.IsUsable() {
		writeAuthError(w, http.StatusUnauthorized, "refresh token expired or revoked")
		return
	}

	user, err := h.users.GetUserByID(r.Context(), sess.UserID)
	if err != nil || user == nil {
		writeAuthError(w, http.StatusUnauthorized, "user not found")
		return
	}
	if !user.Active {
		writeAuthError(w, http.StatusForbidden, "account is deactivated")
		return
	}

	_ = h.sessions.RevokeSession(r.Context(), sess.ID)

	pair, rawRefresh, err := h.tokens.IssueTokenPair(user)
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to issue tokens")
		return
	}

	now := time.Now().UTC()
	newSess := &Session{
		ID:           GenerateID(),
		UserID:       user.ID,
		RefreshToken: rawRefresh,
		UserAgent:    r.UserAgent(),
		ClientIP:     h.cfg.IPResolver().Resolve(r),
		ExpiresAt:    now.Add(h.tokens.RefreshTokenTTL()),
		CreatedAt:    now,
		Revoked:      false,
	}
	_ = h.sessions.CreateSession(r.Context(), newSess)

	h.writeSessionCookies(w, user.ID, pair.AccessToken, rawRefresh)
	writeJSON(w, http.StatusOK, h.loginResponseBody(user, pair))
}

// ---------------------------------------------------------------------------
// POST /auth/logout
//
// Mounted under OptionalAuth (see RegisterRoutes). The handler
// unconditionally clears the browser cookie jar so a user whose
// access cookie expired between the dashboard load and the logout
// click still ends up signed out. The refresh-token body field (or
// refresh cookie) is consumed when present to revoke the session
// server-side too.
// ---------------------------------------------------------------------------

func (h *Handler) handleLogout(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	var req refreshRequest
	if r.Body != nil && r.ContentLength > 0 {
		_ = json.NewDecoder(r.Body).Decode(&req)
	}
	if req.RefreshToken == "" {
		req.RefreshToken = RefreshTokenFromCookie(r)
	}

	if req.RefreshToken != "" {
		sess, _ := h.sessions.GetSessionByToken(r.Context(), req.RefreshToken)
		if sess != nil {
			_ = h.sessions.RevokeSession(r.Context(), sess.ID)
		}
	}

	h.clearSessionCookies(w)
	writeJSON(w, http.StatusOK, map[string]string{"message": "logged out"})
}

// ---------------------------------------------------------------------------
// POST /auth/logout-all
// ---------------------------------------------------------------------------

func (h *Handler) handleLogoutAll(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	userID := UserIDFromContext(r.Context())
	if userID == "" {
		writeAuthError(w, http.StatusUnauthorized, "not authenticated")
		return
	}

	_ = h.sessions.RevokeAllUserSessions(r.Context(), userID)

	h.clearSessionCookies(w)
	writeJSON(w, http.StatusOK, map[string]string{"message": "all sessions revoked"})
}

// ---------------------------------------------------------------------------
// GET /auth/me
// ---------------------------------------------------------------------------

func (h *Handler) handleMe(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	userID := UserIDFromContext(r.Context())
	user, err := h.users.GetUserByID(r.Context(), userID)
	if err != nil || user == nil {
		writeAuthError(w, http.StatusNotFound, "user not found")
		return
	}

	writeJSON(w, http.StatusOK, userPublicView(user))
}

// ---------------------------------------------------------------------------
// PUT /auth/me/password
// ---------------------------------------------------------------------------

type changePasswordRequest struct {
	CurrentPassword string `json:"current_password"`
	NewPassword     string `json:"new_password"`
}

func (h *Handler) handleChangePassword(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	var req changePasswordRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeAuthError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	if req.CurrentPassword == "" || req.NewPassword == "" {
		writeAuthError(w, http.StatusBadRequest, "current_password and new_password are required")
		return
	}

	userID := UserIDFromContext(r.Context())
	user, err := h.users.GetUserByID(r.Context(), userID)
	if err != nil || user == nil {
		writeAuthError(w, http.StatusNotFound, "user not found")
		return
	}

	if user.AuthProvider != "" && user.AuthProvider != AuthProviderLocal {
		writeAuthError(w, http.StatusBadRequest, "this account signs in with "+user.AuthProvider+"; password change is not applicable")
		return
	}

	if err := user.CheckPassword(req.CurrentPassword); err != nil {
		writeAuthError(w, http.StatusUnauthorized, "current password is incorrect")
		return
	}

	if err := ValidatePasswordComplexity(req.NewPassword, user.Username, user.Email); err != nil {
		writeAuthError(w, http.StatusBadRequest, err.Error())
		return
	}
	if !h.checkBreachAllowed(w, r, req.NewPassword) {
		return
	}

	if err := user.SetPassword(req.NewPassword); err != nil {
		writeAuthError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := h.users.UpdatePassword(r.Context(), userID, user.PasswordHash); err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to update password")
		return
	}

	_ = h.sessions.RevokeAllUserSessions(r.Context(), userID)

	h.clearSessionCookies(w)
	writeJSON(w, http.StatusOK, map[string]string{"message": "password updated, all sessions revoked"})
}

// ---------------------------------------------------------------------------
// Admin: GET/POST /auth/admin/users
// ---------------------------------------------------------------------------

type adminCreateUserRequest struct {
	Username string `json:"username"`
	Email    string `json:"email"`
	Password string `json:"password"`
	Role     string `json:"role"`
}

func (h *Handler) handleAdminUsers(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.adminListUsers(w, r)
	case http.MethodPost:
		h.adminCreateUser(w, r)
	default:
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (h *Handler) adminListUsers(w http.ResponseWriter, r *http.Request) {
	users, err := h.users.ListUsers(r.Context())
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to list users")
		return
	}

	result := make([]map[string]interface{}, 0, len(users))
	for _, u := range users {
		result = append(result, map[string]interface{}{
			"id":            u.ID,
			"username":      u.Username,
			"email":         u.Email,
			"role":          string(u.Role),
			"active":        u.Active,
			"created_at":    u.CreatedAt.Format(time.RFC3339),
			"last_login_at": formatOptionalTime(u.LastLoginAt),
		})
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{"users": result, "count": len(result)})
}

func (h *Handler) adminCreateUser(w http.ResponseWriter, r *http.Request) {
	var req adminCreateUserRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeAuthError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	req.Username = strings.TrimSpace(req.Username)
	req.Email = strings.TrimSpace(strings.ToLower(req.Email))

	if req.Username == "" || req.Email == "" || req.Password == "" || req.Role == "" {
		writeAuthError(w, http.StatusBadRequest, "username, email, password, and role are required")
		return
	}

	role, err := ParseRole(req.Role)
	if err != nil {
		writeAuthError(w, http.StatusBadRequest, err.Error())
		return
	}

	now := time.Now().UTC()
	user := &User{
		ID:        GenerateID(),
		Username:  req.Username,
		Email:     req.Email,
		Role:      role,
		Active:    true,
		CreatedAt: now,
		UpdatedAt: now,
	}

	if err := user.SetPassword(req.Password); err != nil {
		writeAuthError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := h.users.CreateUser(r.Context(), user); err != nil {
		if strings.Contains(err.Error(), "already exists") {
			writeAuthError(w, http.StatusConflict, err.Error())
			return
		}
		writeAuthError(w, http.StatusInternalServerError, "failed to create user")
		return
	}

	writeJSON(w, http.StatusCreated, map[string]interface{}{
		"id":       user.ID,
		"username": user.Username,
		"email":    user.Email,
		"role":     string(user.Role),
		"active":   user.Active,
		"message":  "user created",
	})
}

// ---------------------------------------------------------------------------
// Admin: /auth/admin/users/{id}/{action}
// ---------------------------------------------------------------------------

func (h *Handler) handleAdminUserAction(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/auth/admin/users/")
	parts := strings.SplitN(path, "/", 2)

	if len(parts) < 2 {
		writeAuthError(w, http.StatusBadRequest, "expected /auth/admin/users/{id}/{action}")
		return
	}

	userID := parts[0]
	action := parts[1]

	if r.Method != http.MethodPut {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}

	switch action {
	case "deactivate":
		if err := h.users.DeactivateUser(r.Context(), userID); err != nil {
			writeAuthError(w, http.StatusInternalServerError, "failed to deactivate user")
			return
		}
		_ = h.sessions.RevokeAllUserSessions(r.Context(), userID)
		writeJSON(w, http.StatusOK, map[string]string{"message": "user deactivated", "id": userID})

	case "activate":
		if err := h.users.ActivateUser(r.Context(), userID); err != nil {
			writeAuthError(w, http.StatusInternalServerError, "failed to activate user")
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"message": "user activated", "id": userID})

	default:
		writeAuthError(w, http.StatusBadRequest, fmt.Sprintf("unknown action %q, expected deactivate or activate", action))
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func formatOptionalTime(t *time.Time) interface{} {
	if t == nil {
		return nil
	}
	return t.Format(time.RFC3339)
}
