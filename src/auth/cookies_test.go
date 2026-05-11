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

func testOptsInsecure() *CookieOptions {
	o := testOpts()
	o.Secure = false
	return o
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

func TestSetAccessCookie_PrefixedWhenSecure(t *testing.T) {
	rec := httptest.NewRecorder()
	SetAccessCookie(rec, testOpts(), "abc.def.ghi")

	c := findCookie(t, rec.Header(), secureCookiePrefix+AccessTokenCookieName)
	if c == nil {
		t.Fatalf("%s%s cookie not set", secureCookiePrefix, AccessTokenCookieName)
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
	// The unprefixed name must NOT be set.
	if findCookie(t, rec.Header(), AccessTokenCookieName) != nil {
		t.Error("unprefixed access cookie must not be set when Secure=true")
	}
}

func TestSetAccessCookie_UnprefixedWhenInsecure(t *testing.T) {
	rec := httptest.NewRecorder()
	SetAccessCookie(rec, testOptsInsecure(), "abc")

	if findCookie(t, rec.Header(), AccessTokenCookieName) == nil {
		t.Errorf("unprefixed cookie must be used when Secure=false")
	}
	if findCookie(t, rec.Header(), secureCookiePrefix+AccessTokenCookieName) != nil {
		t.Errorf("prefixed cookie must NOT be used when Secure=false (browser would drop it)")
	}
}

func TestSetRefreshCookie_PathScopedToAuth(t *testing.T) {
	rec := httptest.NewRecorder()
	SetRefreshCookie(rec, testOpts(), "refresh-value")

	c := findCookie(t, rec.Header(), secureCookiePrefix+RefreshTokenCookieName)
	if c == nil {
		t.Fatalf("%s%s cookie not set", secureCookiePrefix, RefreshTokenCookieName)
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

	c := findCookie(t, rec.Header(), secureCookiePrefix+CSRFCookieName)
	if c == nil {
		t.Fatalf("%s%s cookie not set", secureCookiePrefix, CSRFCookieName)
	}
	if c.HttpOnly {
		t.Error("CSRF cookie must NOT be HttpOnly (double-submit pattern requires JS read)")
	}
	if !c.Secure {
		t.Error("CSRF cookie must inherit Secure=true from policy")
	}
}

func TestClearAuthCookies_ExpiresBothPrefixedAndUnprefixed(t *testing.T) {
	rec := httptest.NewRecorder()
	ClearAuthCookies(rec, testOpts())

	wantNames := []string{
		secureCookiePrefix + AccessTokenCookieName, AccessTokenCookieName,
		secureCookiePrefix + RefreshTokenCookieName, RefreshTokenCookieName,
		secureCookiePrefix + CSRFCookieName, CSRFCookieName,
	}
	for _, name := range wantNames {
		c := findCookie(t, rec.Header(), name)
		if c == nil {
			t.Errorf("%s cookie not emitted by Clear", name)
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

func TestAccessTokenFromCookie_PrefersPrefixedThenFallsBack(t *testing.T) {
	// Prefixed wins when both are present.
	req := httptest.NewRequest(http.MethodGet, "/api/x", nil)
	req.AddCookie(&http.Cookie{Name: secureCookiePrefix + AccessTokenCookieName, Value: "prefixed"})
	req.AddCookie(&http.Cookie{Name: AccessTokenCookieName, Value: "unprefixed"})
	if got := AccessTokenFromCookie(req); got != "prefixed" {
		t.Errorf("AccessTokenFromCookie = %q, want prefixed", got)
	}

	// Falls back to unprefixed when the prefixed cookie is absent.
	req2 := httptest.NewRequest(http.MethodGet, "/api/x", nil)
	req2.AddCookie(&http.Cookie{Name: AccessTokenCookieName, Value: "  jwt-value  "})
	if got := AccessTokenFromCookie(req2); got != "jwt-value" {
		t.Errorf("AccessTokenFromCookie = %q, want %q", got, "jwt-value")
	}

	// Absent in both -> empty.
	req3 := httptest.NewRequest(http.MethodGet, "/api/x", nil)
	if got := AccessTokenFromCookie(req3); got != "" {
		t.Errorf("AccessTokenFromCookie (absent) = %q, want \"\"", got)
	}
}

func TestRefreshTokenFromCookie_PrefersPrefixedThenFallsBack(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/auth/refresh", nil)
	req.AddCookie(&http.Cookie{Name: secureCookiePrefix + RefreshTokenCookieName, Value: "prefixed"})
	req.AddCookie(&http.Cookie{Name: RefreshTokenCookieName, Value: "unprefixed"})
	if got := RefreshTokenFromCookie(req); got != "prefixed" {
		t.Errorf("RefreshTokenFromCookie = %q, want prefixed", got)
	}

	req2 := httptest.NewRequest(http.MethodPost, "/auth/refresh", nil)
	req2.AddCookie(&http.Cookie{Name: RefreshTokenCookieName, Value: "refresh-value"})
	if got := RefreshTokenFromCookie(req2); got != "refresh-value" {
		t.Errorf("RefreshTokenFromCookie = %q, want %q", got, "refresh-value")
	}

	req3 := httptest.NewRequest(http.MethodPost, "/auth/refresh", nil)
	if got := RefreshTokenFromCookie(req3); got != "" {
		t.Errorf("RefreshTokenFromCookie (absent) = %q, want \"\"", got)
	}
}
