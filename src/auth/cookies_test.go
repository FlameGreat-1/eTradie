package auth

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func testOpts() *CookieOptions {
	return &CookieOptions{
		Domain:             "",
		Secure:             true,
		SameSite:           http.SameSiteStrictMode,
		AccessTokenMaxAge:  15 * time.Minute,
		RefreshTokenMaxAge: 7 * 24 * time.Hour,
		CSRFMaxAge:         15 * time.Minute,
	}
}

func findCookie(t *testing.T, h http.Header, name string) *http.Cookie {
	t.Helper()
	resp := http.Response{Header: h}
	for _, c := range resp.Cookies() {
		if c.Name == name {
			return c
		}
	}
	return nil
}

func TestSetAccessCookie_Attributes(t *testing.T) {
	rec := httptest.NewRecorder()
	SetAccessCookie(rec, testOpts(), "abc.def.ghi")

	c := findCookie(t, rec.Header(), AccessTokenCookieName)
	if c == nil {
		t.Fatalf("%s cookie not set", AccessTokenCookieName)
	}
	if c.Value != "abc.def.ghi" {
		t.Errorf("value = %q, want %q", c.Value, "abc.def.ghi")
	}
	if c.Path != "/" {
		t.Errorf("path = %q, want /", c.Path)
	}
	if !c.HttpOnly {
		t.Error("HttpOnly must be true on access cookie")
	}
	if !c.Secure {
		t.Error("Secure must be true with the test policy")
	}
	if c.SameSite != http.SameSiteStrictMode {
		t.Errorf("SameSite = %v, want Strict", c.SameSite)
	}
	if c.MaxAge != int((15 * time.Minute).Seconds()) {
		t.Errorf("MaxAge = %d, want %d", c.MaxAge, int((15*time.Minute).Seconds()))
	}
}

func TestSetRefreshCookie_PathScopedToAuth(t *testing.T) {
	rec := httptest.NewRecorder()
	SetRefreshCookie(rec, testOpts(), "refresh-value")

	c := findCookie(t, rec.Header(), RefreshTokenCookieName)
	if c == nil {
		t.Fatalf("%s cookie not set", RefreshTokenCookieName)
	}
	if c.Path != "/auth" {
		t.Errorf("refresh cookie must be scoped to /auth, got %q", c.Path)
	}
	if !c.HttpOnly {
		t.Error("HttpOnly must be true on refresh cookie")
	}
}

func TestSetCSRFCookie_NotHttpOnly(t *testing.T) {
	rec := httptest.NewRecorder()
	SetCSRFCookie(rec, testOpts(), "csrf-token-value")

	c := findCookie(t, rec.Header(), CSRFCookieName)
	if c == nil {
		t.Fatalf("%s cookie not set", CSRFCookieName)
	}
	if c.HttpOnly {
		t.Error("CSRF cookie must NOT be HttpOnly (double-submit pattern requires JS read)")
	}
	if !c.Secure {
		t.Error("CSRF cookie must inherit Secure=true from policy")
	}
}

func TestClearAuthCookies_ExpiresAllThree(t *testing.T) {
	rec := httptest.NewRecorder()
	ClearAuthCookies(rec, testOpts())

	for _, name := range []string{AccessTokenCookieName, RefreshTokenCookieName, CSRFCookieName} {
		c := findCookie(t, rec.Header(), name)
		if c == nil {
			t.Errorf("%s cookie was not set for clear", name)
			continue
		}
		if c.MaxAge != -1 {
			t.Errorf("%s MaxAge = %d, want -1", name, c.MaxAge)
		}
		if c.Value != "" {
			t.Errorf("%s value should be empty on clear, got %q", name, c.Value)
		}
	}
}

func TestAccessTokenFromCookie_PresentAndAbsent(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/api/x", nil)
	req.AddCookie(&http.Cookie{Name: AccessTokenCookieName, Value: "  jwt-value  "})
	if got := AccessTokenFromCookie(req); got != "jwt-value" {
		t.Errorf("AccessTokenFromCookie = %q, want %q", got, "jwt-value")
	}

	req2 := httptest.NewRequest(http.MethodGet, "/api/x", nil)
	if got := AccessTokenFromCookie(req2); got != "" {
		t.Errorf("AccessTokenFromCookie (absent) = %q, want \"\"", got)
	}
}

func TestRefreshTokenFromCookie_PresentAndAbsent(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/auth/refresh", nil)
	req.AddCookie(&http.Cookie{Name: RefreshTokenCookieName, Value: "refresh-value"})
	if got := RefreshTokenFromCookie(req); got != "refresh-value" {
		t.Errorf("RefreshTokenFromCookie = %q, want %q", got, "refresh-value")
	}

	req2 := httptest.NewRequest(http.MethodPost, "/auth/refresh", nil)
	if got := RefreshTokenFromCookie(req2); got != "" {
		t.Errorf("RefreshTokenFromCookie (absent) = %q, want \"\"", got)
	}
}
