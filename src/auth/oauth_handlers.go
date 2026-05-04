package auth

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"
)

// ---------------------------------------------------------------------------
// OAuth dependency wiring
//
// The OAuth feature is opt-in. When AUTH_GOOGLE_OAUTH_ENABLED=false
// (the default), Handler.oauthEnabled stays false, the start / callback
// routes return 404, and no Google HTTP client is constructed. This
// lets us mount the routes unconditionally without paying any runtime
// cost on deployments that have not configured OAuth.
// ---------------------------------------------------------------------------

// WithOAuth attaches the OAuth dependencies to the handler. Called
// from main.go after the stores and provider are built. Safe to call
// at most once at startup; never called concurrently with route
// serving, so no locking is needed.
func (h *Handler) WithOAuth(
	flows *OAuthFlowStore,
	identities *OAuthIdentityStore,
	google *GoogleOAuthProvider,
) {
	h.oauthFlows = flows
	h.oauthIdentities = identities
	h.googleProvider = google
	h.oauthEnabled = google != nil && flows != nil && identities != nil
}

// ---------------------------------------------------------------------------
// Request / response payloads
// ---------------------------------------------------------------------------

type oauthStartRequest struct {
	ReturnTo string `json:"return_to,omitempty"`
}

type oauthStartResponse struct {
	AuthorizeURL string `json:"authorize_url"`
	State        string `json:"state"`
	ExpiresIn    int    `json:"expires_in"`
}

type oauthCallbackRequest struct {
	Code  string `json:"code"`
	State string `json:"state"`
}

type oauthCallbackResponse struct {
	User      map[string]interface{} `json:"user"`
	Tokens    *TokenPair             `json:"tokens"`
	IsNewUser bool                   `json:"is_new_user"`
	ReturnTo  string                 `json:"return_to"`
}

// ---------------------------------------------------------------------------
// POST /auth/oauth/google/start
// ---------------------------------------------------------------------------

func (h *Handler) handleOAuthGoogleStart(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.oauthEnabled {
		writeAuthError(w, http.StatusNotFound, "google oauth is not enabled")
		return
	}

	var req oauthStartRequest
	if r.ContentLength > 0 {
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeAuthError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
			return
		}
	}
	returnTo := sanitiseReturnTo(req.ReturnTo)

	state, err := GenerateOAuthSecret()
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to generate state")
		return
	}
	nonce, err := GenerateOAuthSecret()
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to generate nonce")
		return
	}
	verifier, err := GenerateOAuthSecret()
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to generate code_verifier")
		return
	}
	flowID, err := GenerateOAuthSecret()
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to generate flow_id")
		return
	}

	now := time.Now().UTC()
	ttl := time.Duration(h.cfg.OAuthFlowTTLSeconds) * time.Second
	flow := &OAuthFlow{
		FlowID:       flowID,
		Provider:     OAuthProviderGoogle,
		State:        state,
		CodeVerifier: verifier,
		Nonce:        nonce,
		RedirectURI:  h.googleProvider.RedirectURI(),
		ReturnTo:     returnTo,
		CreatedAt:    now,
		ExpiresAt:    now.Add(ttl),
	}
	if err := h.oauthFlows.Create(r.Context(), flow); err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to create oauth flow")
		return
	}

	authorizeURL, err := h.googleProvider.BuildAuthorizeURL(state, verifier, nonce)
	if err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to build authorize url")
		return
	}

	writeJSON(w, http.StatusOK, &oauthStartResponse{
		AuthorizeURL: authorizeURL,
		State:        state,
		ExpiresIn:    h.cfg.OAuthFlowTTLSeconds,
	})
}

// ---------------------------------------------------------------------------
// POST /auth/oauth/google/callback
// ---------------------------------------------------------------------------

func (h *Handler) handleOAuthGoogleCallback(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeAuthError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	if !h.oauthEnabled {
		writeAuthError(w, http.StatusNotFound, "google oauth is not enabled")
		return
	}

	var req oauthCallbackRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeAuthError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	req.Code = strings.TrimSpace(req.Code)
	req.State = strings.TrimSpace(req.State)
	if req.Code == "" || req.State == "" {
		writeAuthError(w, http.StatusBadRequest, "code and state are required")
		return
	}

	flow, err := h.oauthFlows.ConsumeByState(r.Context(), OAuthProviderGoogle, req.State)
	if err != nil {
		writeAuthError(w, http.StatusBadRequest, err.Error())
		return
	}

	claims, err := h.googleProvider.ExchangeCodeAndVerify(r.Context(), req.Code, flow.CodeVerifier, flow.Nonce)
	if err != nil {
		writeAuthError(w, http.StatusUnauthorized, err.Error())
		return
	}

	user, isNewUser, err := h.resolveOrCreateUserForOAuth(r.Context(), claims)
	if err != nil {
		status := http.StatusInternalServerError
		if errors.Is(err, errOAuthEmailConflict) {
			status = http.StatusConflict
		}
		writeAuthError(w, status, err.Error())
		return
	}
	if !user.Active {
		writeAuthError(w, http.StatusForbidden, "account is deactivated")
		return
	}

	if err := h.oauthIdentities.Upsert(r.Context(), &OAuthIdentity{
		ID:              GenerateID(),
		UserID:          user.ID,
		Provider:        OAuthProviderGoogle,
		ProviderSubject: claims.Subject,
		Email:           claims.Email,
		EmailVerified:   claims.EmailVerified,
		Name:            claims.Name,
		Picture:         claims.Picture,
		HostedDomain:    claims.HostedDomain,
	}); err != nil {
		writeAuthError(w, http.StatusInternalServerError, "failed to persist oauth identity")
		return
	}

	// Refresh provider-managed profile fields on every login. Avatar
	// changes upstream become visible without an explicit profile sync.
	if err := h.users.UpdateProfileFromOAuth(r.Context(), user.ID, claims.Picture, true); err == nil {
		user.AvatarURL = claims.Picture
		user.EmailVerified = true
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

	writeJSON(w, http.StatusOK, &oauthCallbackResponse{
		User:      userPublicView(user),
		Tokens:    pair,
		IsNewUser: isNewUser,
		ReturnTo:  flow.ReturnTo,
	})
}

// ---------------------------------------------------------------------------
// User resolution / linking / creation
// ---------------------------------------------------------------------------

var errOAuthEmailConflict = errors.New("an account with this email already exists but is not linked to Google sign-in; please sign in with your password and link Google from settings")

// resolveOrCreateUserForOAuth implements the account-linking policy:
//
//  1. If an OAuthIdentity already exists for (google, sub), use its user.
//  2. Else if a local user exists with the same email AND that local
//     user's auth_provider is already "google", attach by email.
//  3. Else if a local user exists with the same email AND that local
//     user's email is verified AND auth_provider is "local", we refuse
//     to silently merge. Returning ErrOAuthEmailConflict surfaces an
//     actionable 409 to the UI; the user must sign in with their
//     password first and link Google from settings.
//  4. Otherwise create a fresh "etradie" user with auth_provider=google.
func (h *Handler) resolveOrCreateUserForOAuth(ctx context.Context, claims *OAuthClaims) (*User, bool, error) {
	// Step 1: existing identity link.
	if ident, err := h.oauthIdentities.GetByProviderSubject(ctx, OAuthProviderGoogle, claims.Subject); err != nil {
		return nil, false, fmt.Errorf("lookup oauth identity: %w", err)
	} else if ident != nil {
		user, err := h.users.GetUserByID(ctx, ident.UserID)
		if err != nil {
			return nil, false, fmt.Errorf("lookup linked user: %w", err)
		}
		if user == nil {
			return nil, false, fmt.Errorf("linked user not found")
		}
		return user, false, nil
	}

	// Step 2 & 3: existing user with same email.
	existing, err := h.users.GetUserByEmail(ctx, claims.Email)
	if err != nil {
		return nil, false, fmt.Errorf("lookup user by email: %w", err)
	}
	if existing != nil {
		if existing.AuthProvider == AuthProviderGoogle {
			return existing, false, nil
		}
		return nil, false, errOAuthEmailConflict
	}

	// Step 4: brand-new user.
	username, err := h.allocateUsernameFromEmail(ctx, claims.Email)
	if err != nil {
		return nil, false, err
	}

	now := time.Now().UTC()
	u := &User{
		ID:            GenerateID(),
		Username:      username,
		Email:         claims.Email,
		Role:          RoleEtradie,
		Active:        true,
		AuthProvider:  AuthProviderGoogle,
		AvatarURL:     claims.Picture,
		EmailVerified: true,
		CreatedAt:     now,
		UpdatedAt:     now,
	}
	// Federated accounts have no local password. PasswordHash stays empty;
	// CheckPassword refuses to compare anything for non-local providers.
	if err := h.users.CreateUser(ctx, u); err != nil {
		return nil, false, fmt.Errorf("create user: %w", err)
	}
	return u, true, nil
}

// allocateUsernameFromEmail derives a unique username from the email
// local-part. Disallowed characters are stripped, the candidate is
// truncated to 24 chars, and on collision a 6-hex-char random suffix
// is appended (up to 10 attempts) so user creation cannot loop.
func (h *Handler) allocateUsernameFromEmail(ctx context.Context, email string) (string, error) {
	at := strings.IndexByte(email, '@')
	base := email
	if at > 0 {
		base = email[:at]
	}
	cleaned := make([]rune, 0, len(base))
	for _, r := range strings.ToLower(base) {
		switch {
		case r >= 'a' && r <= 'z',
			r >= '0' && r <= '9',
			r == '.', r == '_', r == '-':
			cleaned = append(cleaned, r)
		}
	}
	candidate := string(cleaned)
	if len(candidate) < 3 {
		candidate = "user" + candidate
	}
	if len(candidate) > 24 {
		candidate = candidate[:24]
	}

	if u, err := h.users.GetUserByUsername(ctx, candidate); err != nil {
		return "", fmt.Errorf("check username: %w", err)
	} else if u == nil {
		return candidate, nil
	}

	for i := 0; i < 10; i++ {
		suffix, err := GenerateOAuthSecret()
		if err != nil {
			return "", fmt.Errorf("username suffix: %w", err)
		}
		suffix = strings.ToLower(suffix)
		if len(suffix) > 6 {
			suffix = suffix[:6]
		}
		trim := candidate
		if len(trim) > 25 {
			trim = trim[:25]
		}
		next := trim + "-" + suffix
		if len(next) > 32 {
			next = next[:32]
		}
		u, err := h.users.GetUserByUsername(ctx, next)
		if err != nil {
			return "", fmt.Errorf("check username: %w", err)
		}
		if u == nil {
			return next, nil
		}
	}
	return "", fmt.Errorf("could not allocate a unique username for %s", email)
}

// sanitiseReturnTo guards against open-redirects: only same-origin
// paths are accepted. Anything else is replaced with the safe default
// "/". This is enforced even though the frontend stores return_to in
// sessionStorage, because the field round-trips through the server.
func sanitiseReturnTo(p string) string {
	p = strings.TrimSpace(p)
	if p == "" {
		return "/"
	}
	if !strings.HasPrefix(p, "/") {
		return "/"
	}
	if strings.HasPrefix(p, "//") || strings.HasPrefix(p, "/\\") {
		return "/"
	}
	if len(p) > 512 {
		return "/"
	}
	return p
}

// userPublicView is the canonical JSON shape for AuthUser, shared by
// /auth/me and the OAuth callback so the React types only need one
// definition.
func userPublicView(u *User) map[string]interface{} {
	provider := u.AuthProvider
	if provider == "" {
		provider = AuthProviderLocal
	}
	return map[string]interface{}{
		"id":             u.ID,
		"username":       u.Username,
		"email":          u.Email,
		"role":           string(u.Role),
		"active":         u.Active,
		"auth_provider":  provider,
		"avatar_url":     u.AvatarURL,
		"email_verified": u.EmailVerified,
		"created_at":     u.CreatedAt.Format(time.RFC3339),
		"last_login_at":  formatOptionalTime(u.LastLoginAt),
	}
}
