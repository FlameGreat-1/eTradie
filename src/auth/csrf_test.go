package auth

import (
	"context"
	"encoding/hex"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

const testHMACSecret = "csrf-test-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

func TestGenerateCSRFTokenRandom_LengthAndEncoding(t *testing.T) {
	tok, err := GenerateCSRFTokenRandom()
	if err != nil {
		t.Fatalf("GenerateCSRFTokenRandom: %v", err)
	}
	if len(tok) != csrfTokenRandomBytes*2 {
		t.Errorf("token length = %d, want %d", len(tok), csrfTokenRandomBytes*2)
	}
	if _, err := hex.DecodeString(tok); err != nil {
		t.Errorf("token is not valid hex: %v", err)
	}
	tok2, err := GenerateCSRFTokenRandom()
	if err != nil {
		t.Fatalf("GenerateCSRFTokenRandom (2): %v", err)
	}
	if tok == tok2 {
		t.Error("two consecutive tokens collided; randomness is broken")
	}
}

func TestGenerateCSRFToken_Signed_FormatAndBinding(t *testing.T) {
	secret := []byte(testHMACSecret)
	tok, err := GenerateCSRFToken(secret, "user-1", true)
	if err != nil {
		t.Fatalf("GenerateCSRFToken signed: %v", err)
	}
	parts := strings.Split(tok, ".")
	if len(parts) != 2 {
		t.Fatalf("signed token must be <random>.<mac>, got %q", tok)
	}
	if len(parts[0]) != csrfTokenRandomBytes*2 {
		t.Errorf("random portion length = %d, want %d", len(parts[0]), csrfTokenRandomBytes*2)
	}
	// MAC must be 64 hex chars (SHA-256 = 32 bytes).
	if len(parts[1]) != 64 {
		t.Errorf("mac length = %d, want 64", len(parts[1]))
	}
	// Recomputing with the same inputs must produce the same MAC.
	check := SignCSRFToken(secret, "user-1", parts[0])
	if check != tok {
		t.Errorf("SignCSRFToken not deterministic: got %q want %q", check, tok)
	}
	// Different user must produce a different MAC for the same random.
	other := SignCSRFToken(secret, "user-2", parts[0])
	if other == tok {
		t.Error("signed token MAC must vary with userID")
	}
}

func TestGenerateCSRFToken_Unsigned_FormatIsPlainRandom(t *testing.T) {
	tok, err := GenerateCSRFToken(nil, "", false)
	if err != nil {
		t.Fatalf("GenerateCSRFToken unsigned: %v", err)
	}
	if strings.Contains(tok, ".") {
		t.Errorf("unsigned token must not contain a dot, got %q", tok)
	}
	if len(tok) != csrfTokenRandomBytes*2 {
		t.Errorf("unsigned token length = %d, want %d", len(tok), csrfTokenRandomBytes*2)
	}
}

// reqWithCSRF builds a request with the cookie + header, optionally
// injecting a userID into the context (for signed-mode tests).
func reqWithCSRF(t *testing.T, cookieValue, headerName, headerValue, userID string) *http.Request {
	t.Helper()
	r := httptest.NewRequest(http.MethodPost, "/api/x", nil)
	if cookieValue != "" {
		r.AddCookie(&http.Cookie{Name: CSRFCookieName, Value: cookieValue})
	}
	if headerName != "" && headerValue != "" {
		r.Header.Set(headerName, headerValue)
	}
	if userID != "" {
		ctx := context.WithValue(r.Context(), claimsKey, &Claims{UserID: userID})
		r = r.WithContext(ctx)
	}
	return r
}

func TestVerifyCSRF_Unsigned_AcceptsMatching(t *testing.T) {
	tok := "deadbeefcafef00ddeadbeefcafef00ddeadbeefcafef00ddeadbeefcafef00d"
	if !VerifyCSRF(reqWithCSRF(t, tok, "X-CSRF-Token", tok, ""), "X-CSRF-Token") {
		t.Error("VerifyCSRF (unsigned) must accept matching cookie+header")
	}
}

func TestVerifyCSRF_Unsigned_RejectsMismatches(t *testing.T) {
	cases := []struct {
		name     string
		cookie   string
		headerN  string
		headerV  string
		lookupHN string
	}{
		{"missing cookie", "", "X-CSRF-Token", "deadbeef", "X-CSRF-Token"},
		{"missing header", "deadbeef", "", "", "X-CSRF-Token"},
		{"empty headerName", "deadbeef", "X-CSRF-Token", "deadbeef", ""},
		{"length mismatch", "deadbeef", "X-CSRF-Token", "deadbeefcafe", "X-CSRF-Token"},
		{"byte mismatch", "deadbeefcafe0001", "X-CSRF-Token", "deadbeefcafe0002", "X-CSRF-Token"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if VerifyCSRF(reqWithCSRF(t, tc.cookie, tc.headerN, tc.headerV, ""), tc.lookupHN) {
				t.Error("VerifyCSRF must reject")
			}
		})
	}
}

// buildSignedCfg returns a Config wired for signed-CSRF middleware tests.
func buildSignedCfg() *Config {
	c := &Config{}
	c.SetTestSecret(testHMACSecret)
	c.CSRFSigned = true
	c.CSRFHeader = "X-CSRF-Token"
	return c
}

func TestRequireCSRF_Signed_AcceptsMatching(t *testing.T) {
	cfg := buildSignedCfg()
	tok, err := GenerateCSRFToken(cfg.JWTSecretBytes(), "user-1", true)
	if err != nil {
		t.Fatalf("GenerateCSRFToken: %v", err)
	}
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})
	mw := RequireCSRF(cfg)(inner)

	rec := httptest.NewRecorder()
	mw.ServeHTTP(rec, reqWithCSRF(t, tok, "X-CSRF-Token", tok, "user-1"))
	if rec.Code != http.StatusNoContent {
		t.Errorf("status = %d, want 204; body=%q", rec.Code, rec.Body.String())
	}
}

func TestRequireCSRF_Signed_RejectsMissingUserContext(t *testing.T) {
	cfg := buildSignedCfg()
	tok, err := GenerateCSRFToken(cfg.JWTSecretBytes(), "user-1", true)
	if err != nil {
		t.Fatalf("GenerateCSRFToken: %v", err)
	}
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		t.Fatal("inner must not run when userID is absent in signed mode")
	})
	mw := RequireCSRF(cfg)(inner)

	rec := httptest.NewRecorder()
	mw.ServeHTTP(rec, reqWithCSRF(t, tok, "X-CSRF-Token", tok, "")) // no userID
	if rec.Code != http.StatusForbidden {
		t.Errorf("status = %d, want 403", rec.Code)
	}
}

func TestRequireCSRF_Signed_RejectsForgedMACForDifferentUser(t *testing.T) {
	cfg := buildSignedCfg()
	// Attacker (sibling subdomain) reads alice's cookie and replays it,
	// but their session is bob's. The MAC was bound to alice's id; the
	// middleware recomputes against bob and must reject.
	tok, err := GenerateCSRFToken(cfg.JWTSecretBytes(), "alice", true)
	if err != nil {
		t.Fatalf("GenerateCSRFToken: %v", err)
	}
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		t.Fatal("inner must not run for forged MAC")
	})
	mw := RequireCSRF(cfg)(inner)

	rec := httptest.NewRecorder()
	mw.ServeHTTP(rec, reqWithCSRF(t, tok, "X-CSRF-Token", tok, "bob"))
	if rec.Code != http.StatusForbidden {
		t.Errorf("status = %d, want 403", rec.Code)
	}
}

func TestRequireCSRF_Signed_RejectsHeaderRandomMismatch(t *testing.T) {
	cfg := buildSignedCfg()
	cookie, err := GenerateCSRFToken(cfg.JWTSecretBytes(), "user-1", true)
	if err != nil {
		t.Fatalf("GenerateCSRFToken: %v", err)
	}
	// Header has a different random portion but same MAC suffix -
	// double-submit invariant must fail.
	parts := strings.Split(cookie, ".")
	forged := strings.Repeat("f", len(parts[0])) + "." + parts[1]
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		t.Fatal("inner must not run on random mismatch")
	})
	mw := RequireCSRF(cfg)(inner)

	rec := httptest.NewRecorder()
	mw.ServeHTTP(rec, reqWithCSRF(t, cookie, "X-CSRF-Token", forged, "user-1"))
	if rec.Code != http.StatusForbidden {
		t.Errorf("status = %d, want 403", rec.Code)
	}
}

func TestRequireCSRF_Unsigned_StillWorks(t *testing.T) {
	cfg := &Config{}
	cfg.SetTestSecret(testHMACSecret)
	cfg.CSRFSigned = false
	cfg.CSRFHeader = "X-CSRF-Token"
	tok, err := GenerateCSRFToken(cfg.JWTSecretBytes(), "user-1", false)
	if err != nil {
		t.Fatalf("GenerateCSRFToken: %v", err)
	}
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})
	mw := RequireCSRF(cfg)(inner)

	rec := httptest.NewRecorder()
	mw.ServeHTTP(rec, reqWithCSRF(t, tok, "X-CSRF-Token", tok, ""))
	if rec.Code != http.StatusNoContent {
		t.Errorf("status = %d, want 204", rec.Code)
	}
}

func TestRequireCSRF_BypassesSafeMethods(t *testing.T) {
	cfg := buildSignedCfg()
	called := false
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		called = true
		w.WriteHeader(http.StatusOK)
	})
	mw := RequireCSRF(cfg)(inner)

	for _, m := range []string{http.MethodGet, http.MethodHead, http.MethodOptions} {
		called = false
		rec := httptest.NewRecorder()
		mw.ServeHTTP(rec, httptest.NewRequest(m, "/api/x", nil))
		if !called {
			t.Errorf("%s: inner handler not called", m)
		}
		if rec.Code != http.StatusOK {
			t.Errorf("%s: status = %d, want 200", m, rec.Code)
		}
	}
}

func TestRequireCSRF_BlocksUnsafeMethodsWithoutPair(t *testing.T) {
	cfg := buildSignedCfg()
	called := false
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		called = true
		w.WriteHeader(http.StatusOK)
	})
	mw := RequireCSRF(cfg)(inner)

	for _, m := range []string{http.MethodPost, http.MethodPut, http.MethodPatch, http.MethodDelete} {
		called = false
		rec := httptest.NewRecorder()
		mw.ServeHTTP(rec, httptest.NewRequest(m, "/api/x", nil))
		if called {
			t.Errorf("%s: inner handler must NOT be called without CSRF pair", m)
		}
		if rec.Code != http.StatusForbidden {
			t.Errorf("%s: status = %d, want 403", m, rec.Code)
		}
	}
}

func TestSplitSignedCSRFToken_Edges(t *testing.T) {
	cases := []struct {
		in string
		ok bool
	}{
		{"abc.def", true},
		{".def", false},
		{"abc.", false},
		{"nodot", false},
		{"", false},
	}
	for _, tc := range cases {
		_, _, ok := splitSignedCSRFToken(tc.in)
		if ok != tc.ok {
			t.Errorf("splitSignedCSRFToken(%q) ok=%v, want %v", tc.in, ok, tc.ok)
		}
	}
}
