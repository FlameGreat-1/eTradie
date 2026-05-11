package auth

import (
	"encoding/hex"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestGenerateCSRFToken_LengthAndEncoding(t *testing.T) {
	tok, err := GenerateCSRFToken()
	if err != nil {
		t.Fatalf("GenerateCSRFToken: %v", err)
	}
	if len(tok) != csrfTokenBytes*2 {
		t.Errorf("token length = %d, want %d", len(tok), csrfTokenBytes*2)
	}
	if _, err := hex.DecodeString(tok); err != nil {
		t.Errorf("token is not valid hex: %v", err)
	}
	// Two consecutive calls must differ (sanity check on randomness).
	tok2, err := GenerateCSRFToken()
	if err != nil {
		t.Fatalf("GenerateCSRFToken (2): %v", err)
	}
	if tok == tok2 {
		t.Error("two consecutive tokens collided; randomness is broken")
	}
}

func reqWithCSRF(cookieValue, headerName, headerValue string) *http.Request {
	r := httptest.NewRequest(http.MethodPost, "/api/x", nil)
	if cookieValue != "" {
		r.AddCookie(&http.Cookie{Name: CSRFCookieName, Value: cookieValue})
	}
	if headerName != "" && headerValue != "" {
		r.Header.Set(headerName, headerValue)
	}
	return r
}

func TestVerifyCSRF_AcceptsMatching(t *testing.T) {
	tok := "deadbeefcafef00d"
	if !VerifyCSRF(reqWithCSRF(tok, "X-CSRF-Token", tok), "X-CSRF-Token") {
		t.Error("VerifyCSRF must accept matching cookie+header")
	}
}

func TestVerifyCSRF_RejectsMismatches(t *testing.T) {
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
			if VerifyCSRF(reqWithCSRF(tc.cookie, tc.headerN, tc.headerV), tc.lookupHN) {
				t.Error("VerifyCSRF must reject")
			}
		})
	}
}

func TestRequireCSRF_BypassesSafeMethods(t *testing.T) {
	called := false
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		called = true
		w.WriteHeader(http.StatusOK)
	})
	mw := RequireCSRF("X-CSRF-Token")(inner)

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
	called := false
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		called = true
		w.WriteHeader(http.StatusOK)
	})
	mw := RequireCSRF("X-CSRF-Token")(inner)

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

func TestRequireCSRF_AllowsValidPair(t *testing.T) {
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})
	mw := RequireCSRF("X-CSRF-Token")(inner)

	tok := "feedfacecafebabe"
	rec := httptest.NewRecorder()
	mw.ServeHTTP(rec, reqWithCSRF(tok, "X-CSRF-Token", tok))
	if rec.Code != http.StatusNoContent {
		t.Errorf("status = %d, want 204", rec.Code)
	}
}
