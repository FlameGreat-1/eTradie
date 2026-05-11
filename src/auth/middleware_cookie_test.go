package auth

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

// buildTestTokenService returns a TokenService and a freshly-issued
// signed access token for a synthetic user. Used by the cookie-auth
// middleware tests so they exercise the real verify path, not a
// mocked one.
func buildTestTokenService(t *testing.T) (*TokenService, string) {
	t.Helper()
	cfg := &Config{}
	cfg.SetTestSecret("middleware-cookie-test-secret-aaaaaaaaaaaaaaaaaa")
	ts := NewTokenService(cfg)

	u := &User{
		ID:       "user-1",
		Username: "alice",
		Role:     RoleEtradie,
		Tier:     "free",
		Status:   "active",
	}
	pair, _, err := ts.IssueTokenPair(u)
	if err != nil {
		t.Fatalf("IssueTokenPair: %v", err)
	}
	return ts, pair.AccessToken
}

// protectedHandler is the inner handler we wrap with RequireAuth to
// observe whether the request was accepted. It writes the resolved
// UserID so tests can verify the claims actually round-tripped.
func protectedHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(UserIDFromContext(r.Context())))
}

func TestRequireAuth_AcceptsAccessTokenCookie(t *testing.T) {
	ts, token := buildTestTokenService(t)
	handler := RequireAuth(ts)(http.HandlerFunc(protectedHandler))

	req := httptest.NewRequest(http.MethodGet, "/api/x", nil)
	req.AddCookie(&http.Cookie{Name: AccessTokenCookieName, Value: token})
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body=%q", rec.Code, rec.Body.String())
	}
	if got := rec.Body.String(); got != "user-1" {
		t.Errorf("user id from context = %q, want user-1", got)
	}
}

func TestRequireAuth_HeaderWinsOverCookie(t *testing.T) {
	// Issue two distinct tokens (different subjects) so we can tell
	// which one the middleware honoured by inspecting the body.
	ts := NewTokenService(func() *Config {
		c := &Config{}
		c.SetTestSecret("middleware-cookie-test-secret-bbbbbbbbbbbbbbbbbbbb")
		return c
	}())
	pairHeader, _, err := ts.IssueTokenPair(&User{ID: "hdr-user", Username: "u1", Role: RoleEtradie})
	if err != nil {
		t.Fatalf("issue header token: %v", err)
	}
	pairCookie, _, err := ts.IssueTokenPair(&User{ID: "ck-user", Username: "u2", Role: RoleEtradie})
	if err != nil {
		t.Fatalf("issue cookie token: %v", err)
	}

	handler := RequireAuth(ts)(http.HandlerFunc(protectedHandler))
	req := httptest.NewRequest(http.MethodGet, "/api/x", nil)
	req.Header.Set("Authorization", "Bearer "+pairHeader.AccessToken)
	req.AddCookie(&http.Cookie{Name: AccessTokenCookieName, Value: pairCookie.AccessToken})
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := rec.Body.String(); got != "hdr-user" {
		t.Errorf("header must take precedence; got user id %q, want hdr-user", got)
	}
}

func TestRequireAuth_InvalidCookieReturns401(t *testing.T) {
	ts, _ := buildTestTokenService(t)
	handler := RequireAuth(ts)(http.HandlerFunc(protectedHandler))

	req := httptest.NewRequest(http.MethodGet, "/api/x", nil)
	req.AddCookie(&http.Cookie{Name: AccessTokenCookieName, Value: "not-a-real-jwt"})
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Errorf("status = %d, want 401", rec.Code)
	}
}

func TestRequireAuth_NoCredentialsReturns401(t *testing.T) {
	ts, _ := buildTestTokenService(t)
	handler := RequireAuth(ts)(http.HandlerFunc(protectedHandler))

	req := httptest.NewRequest(http.MethodGet, "/api/x", nil)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Errorf("status = %d, want 401", rec.Code)
	}
}

func TestRequireAuth_WSUpgradeNoSubprotocolStillRejectedEvenWithCookie(t *testing.T) {
	// Regression guard: a WS handshake must never silently accept
	// the access_token cookie. The WS channel is single-source
	// (subprotocol only) for diagnostic clarity.
	ts, token := buildTestTokenService(t)
	handler := RequireAuth(ts)(http.HandlerFunc(protectedHandler))

	req := httptest.NewRequest(http.MethodGet, "/ws/notifications", nil)
	req.Header.Set("Upgrade", "websocket")
	req.Header.Set("Connection", "Upgrade")
	req.AddCookie(&http.Cookie{Name: AccessTokenCookieName, Value: token})
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Errorf("WS upgrade must NOT fall back to cookie; status = %d, want 401", rec.Code)
	}
}

func TestOptionalAuth_PassesThroughOnNoCookie(t *testing.T) {
	ts, _ := buildTestTokenService(t)
	called := false
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
		// claims should be nil since no creds supplied
		if c := ClaimsFromContext(r.Context()); c != nil {
			t.Errorf("OptionalAuth should leave context unauthenticated when no credentials; got %+v", c)
		}
		w.WriteHeader(http.StatusOK)
	})
	handler := OptionalAuth(ts)(inner)

	req := httptest.NewRequest(http.MethodGet, "/optional", nil)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if !called {
		t.Fatal("OptionalAuth must call inner handler when no credentials are present")
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want 200", rec.Code)
	}
}

func TestOptionalAuth_AcceptsCookie(t *testing.T) {
	ts, token := buildTestTokenService(t)
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if UserIDFromContext(r.Context()) != "user-1" {
			t.Errorf("OptionalAuth must populate claims when valid cookie is present")
		}
		w.WriteHeader(http.StatusOK)
	})
	handler := OptionalAuth(ts)(inner)

	req := httptest.NewRequest(http.MethodGet, "/optional", nil)
	req.AddCookie(&http.Cookie{Name: AccessTokenCookieName, Value: token})
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want 200", rec.Code)
	}
}
