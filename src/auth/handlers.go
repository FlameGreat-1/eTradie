package auth

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

// Handler serves the authentication REST API endpoints.
//
// OAuth dependencies are optional and attached at startup via
// Handler.WithOAuth (see oauth_handlers.go). When oauthEnabled is
// false the OAuth routes return 404 and no Google client is built.
type Handler struct {
	users    *UserStore
	sessions *SessionStore
	tokens   *TokenService
	cfg      *Config

	oauthEnabled    bool
	oauthFlows      *OAuthFlowStore
	oauthIdentities *OAuthIdentityStore
	googleProvider  *GoogleOAuthProvider
}

// NewHandler creates the auth HTTP handler.
func NewHandler(users *UserStore, sessions *SessionStore, tokens *TokenService, cfg *Config) *Handler {
	return &Handler{
		users:    users,
		sessions: sessions,
		tokens:   tokens,
		cfg:      cfg,
	}
}

// RegisterRoutes mounts all auth routes on the given mux.
// Public routes (no auth required): login, register, refresh.
// Protected routes (require valid token): logout, me, password change.
// Admin routes (require admin role): user management.
// Public endpoints are rate-limited per IP to prevent brute-force attacks.
//
// The per-IP rate-limit identity is resolved via h.cfg.IPResolver(),
// which honours forwarding headers only from trusted proxies. This
// prevents an attacker who reaches the origin directly from spoofing
// X-Forwarded-For to impersonate other source IPs.
func (h *Handler) RegisterRoutes(mux *http.ServeMux, ts *TokenService) {
	// Rate limiters for public auth endpoints (per IP).
	loginLimiter := NewRateLimiter(10, 1*time.Minute)        // 10 login attempts/min/IP
	registerLimiter := NewRateLimiter(5, 1*time.Minute)      // 5 registrations/min/IP
	refreshLimiter := NewRateLimiter(20, 1*time.Minute)      // 20 refresh attempts/min/IP
	oauthStartLimiter := NewRateLimiter(20, 1*time.Minute)   // 20 oauth-start/min/IP
	oauthCallbackLimiter := NewRateLimiter(20, 1*time.Minute) // 20 oauth-callback/min/IP

	resolver := h.cfg.IPResolver()

	// Public endpoints (no auth, rate-limited).
	mux.HandleFunc("/auth/login", loginLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleLogin))
	mux.HandleFunc("/auth/register", registerLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleRegister))
	mux.HandleFunc("/auth/refresh", refreshLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleRefresh))

	// OAuth 2.0 sign-in endpoints (public, rate-limited). Mounted
	// unconditionally; when OAuth is not configured the handlers
	// return 404 and the routes are effectively no-ops. This keeps
	// the route table identical across environments for ops
	// simplicity.
	mux.HandleFunc("/auth/oauth/google/start", oauthStartLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleOAuthGoogleStart))
	mux.HandleFunc("/auth/oauth/google/callback", oauthCallbackLimiter.RateLimitMiddlewareWithResolver(resolver, h.handleOAuthGoogleCallback))

	// Protected endpoints (any authenticated user).
	mux.Handle("/auth/logout", RequireAuthFunc(ts, h.handleLogout))
	mux.Handle("/auth/logout-all", RequireAuthFunc(ts, h.handleLogoutAll))
	mux.Handle("/auth/me", RequireAuthFunc(ts, h.handleMe))
	mux.Handle("/auth/me/password", RequireAuthFunc(ts, h.handleChangePassword))

	// OAuth 2.0 account-link endpoints (authenticated). The auth
	// middleware itself is the gate, so no per-IP rate-limiter is
	// added here; an attacker who already holds a valid bearer token
	// is not in the threat model these limiters protect against, and
	// the upstream gateway already throttles per-token traffic.
	mux.Handle("/auth/oauth/google/link/start", RequireAuthFunc(ts, h.handleOAuthGoogleLinkStart))
	mux.Handle("/auth/oauth/google/link/callback", RequireAuthFunc(ts, h.handleOAuthGoogleLinkCallback))
	mux.Handle("/auth/oauth/google/link", RequireAuthFunc(ts, h.handleOAuthGoogleUnlink))

	// Admin endpoints.
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

	// Look up user.
	user, err := h.users.GetUserByUsername(r.Context(), req.Username)
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "internal error")
		return
	}
	if user == nil {
		writeAuthError(w, http.StatusUnauthorized, "invalid username or password")
		return
	}

	// Check account is active.
	if !user.Active {
		writeAuthError(w, http.StatusForbidden, "account is deactivated")
		return
	}

	// Verify password.
	if err := user.CheckPassword(req.Password); err != nil {
		writeAuthError(w, http.StatusUnauthorized, "invalid username or password")
		return
	}

	// Issue token pair.
	pair, rawRefresh, err := h.tokens.IssueTokenPair(user)
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to issue tokens")
		return
	}

	// Enforce max sessions per user.
	count, _ := h.sessions.CountActiveSessions(r.Context(), user.ID)
	if count >= h.cfg.MaxSessionsPerUser {
		_ = h.sessions.RevokeOldestSession(r.Context(), user.ID)
	}

	// Persist refresh session.
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

	// Update last login.
	_ = h.users.UpdateLastLogin(r.Context(), user.ID)

	writeJSON(w, http.StatusOK, pair)
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
		Role:      RoleEtradie, // Self-registration always creates etradie role.
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

	// Auto-login: issue tokens immediately.
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

	writeJSON(w, http.StatusCreated, map[string]interface{}{
		"user":   userPublicView(user),
		"tokens": pair,
	})
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

	var req refreshRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeAuthError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	if req.RefreshToken == "" {
		writeAuthError(w, http.StatusBadRequest, "refresh_token is required")
		return
	}

	// Look up session by refresh token.
	sess, err := h.sessions.GetSessionByToken(r.Context(), req.RefreshToken)
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "internal error")
		return
	}
	if sess == nil {
		writeAuthError(w, http.StatusUnauthorized, "invalid refresh token")
		return
	}

	// Check session is usable.
	if !sess.IsUsable() {
		writeAuthError(w, http.StatusUnauthorized, "refresh token expired or revoked")
		return
	}

	// Look up user.
	user, err := h.users.GetUserByID(r.Context(), sess.UserID)
	if err != nil || user == nil {
		writeAuthError(w, http.StatusUnauthorized, "user not found")
		return
	}
	if !user.Active {
		writeAuthError(w, http.StatusForbidden, "account is deactivated")
		return
	}

	// Revoke the old session (refresh token rotation).
	_ = h.sessions.RevokeSession(r.Context(), sess.ID)

	// Issue new token pair.
	pair, rawRefresh, err := h.tokens.IssueTokenPair(user)
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to issue tokens")
		return
	}

	// Create new session.
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

	writeJSON(w, http.StatusOK, pair)
}

// ---------------------------------------------------------------------------
// POST /auth/logout
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

	// If refresh token provided, revoke that specific session.
	if req.RefreshToken != "" {
		sess, _ := h.sessions.GetSessionByToken(r.Context(), req.RefreshToken)
		if sess != nil {
			_ = h.sessions.RevokeSession(r.Context(), sess.ID)
		}
	}

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

	// Federated accounts have no local password to change. Surface a
	// clear 400 instead of letting CheckPassword return a generic error.
	if user.AuthProvider != "" && user.AuthProvider != AuthProviderLocal {
		writeAuthError(w, http.StatusBadRequest, "this account signs in with "+user.AuthProvider+"; password change is not applicable")
		return
	}

	// Verify current password.
	if err := user.CheckPassword(req.CurrentPassword); err != nil {
		writeAuthError(w, http.StatusUnauthorized, "current password is incorrect")
		return
	}

	// Set new password.
	if err := user.SetPassword(req.NewPassword); err != nil {
		writeAuthError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := h.users.UpdatePassword(r.Context(), userID, user.PasswordHash); err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to update password")
		return
	}

	// Revoke all sessions to force re-login with new password.
	_ = h.sessions.RevokeAllUserSessions(r.Context(), userID)

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
	// Parse path: /auth/admin/users/{id}/{action}
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
		// Revoke all sessions for deactivated user.
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

// clientIP() was removed in favour of the trust-aware ClientIPResolver
// in clientip.go, exposed via Config.IPResolver(). The legacy helper
// trusted X-Forwarded-For from any peer and was therefore vulnerable
// to header spoofing once an attacker reached the origin directly.

func formatOptionalTime(t *time.Time) interface{} {
	if t == nil {
		return nil
	}
	return t.Format(time.RFC3339)
}
