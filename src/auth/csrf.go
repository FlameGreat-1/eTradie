// CSRF defence for cookie-authenticated state-changing requests.
//
// The token is delivered to the browser as a NON-HttpOnly cookie
// (csrf_token) and the SPA echoes it back in a header (default
// X-CSRF-Token). On every state-changing request the server compares
// the cookie value to the header value with constant-time compare.
//
// This is the standard "double-submit" pattern. Its correctness rests
// on three independent invariants, all enforced elsewhere:
//
//  1. Authenticated cookies are SameSite=Strict (or Lax with careful
//     handler design), so a cross-site form POST never carries them.
//     See cookies.go and Config.SameSite.
//
//  2. The session cookies are Secure when behind any real edge, so a
//     network attacker cannot read or set them in plaintext. See
//     cookies.go and Config.Secure.
//
//  3. Cross-origin JS cannot read the csrf_token cookie from a
//     different origin (same-origin policy), so the only way the
//     header AND cookie can match is when the request originates
//     from the legitimate SPA.
//
// Safe methods (GET, HEAD, OPTIONS) bypass the check; mutating
// methods (POST, PUT, PATCH, DELETE) are gated unconditionally. A
// missing or mismatched header returns 403 with a fixed generic
// message so the failure mode cannot leak which side failed.
package auth

import (
	"crypto/rand"
	"crypto/subtle"
	"encoding/hex"
	"net/http"
)

// csrfTokenBytes is the number of random bytes encoded into a CSRF
// token. 32 bytes -> 64 hex chars, identical to the refresh-token
// strength so the same statistical guarantees apply.
const csrfTokenBytes = 32

// csrfRequiredMethods is the set of HTTP methods that REQUIRE a
// matching CSRF cookie + header. Anything not in this set passes
// through unmodified.
var csrfRequiredMethods = map[string]bool{
	http.MethodPost:   true,
	http.MethodPut:    true,
	http.MethodPatch:  true,
	http.MethodDelete: true,
}

// GenerateCSRFToken returns a fresh, hex-encoded random token suitable
// for use as the csrf_token cookie value. Callers should rotate the
// token on every successful login and on every refresh so a stolen
// token's value to an attacker is bounded.
func GenerateCSRFToken() (string, error) {
	b := make([]byte, csrfTokenBytes)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

// VerifyCSRF reads the csrf_token cookie and the configured CSRF
// header from the request and returns true iff both are present,
// non-empty, equal length, and byte-for-byte equal under constant-
// time compare. Any other outcome returns false; callers map this
// to 403.
func VerifyCSRF(r *http.Request, headerName string) bool {
	if headerName == "" {
		return false
	}
	cookie, err := r.Cookie(CSRFCookieName)
	if err != nil || cookie.Value == "" {
		return false
	}
	header := r.Header.Get(headerName)
	if header == "" {
		return false
	}
	a := []byte(cookie.Value)
	b := []byte(header)
	if len(a) != len(b) {
		return false
	}
	return subtle.ConstantTimeCompare(a, b) == 1
}

// RequireCSRF returns HTTP middleware that enforces the double-submit
// CSRF check on state-changing methods. Must run AFTER any auth
// middleware so an unauthenticated request is rejected with 401, not
// 403. In the gateway it is chained as:
//
//	authMiddleware( RequireCSRF(headerName)( handler ) )
func RequireCSRF(headerName string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if !csrfRequiredMethods[r.Method] {
				next.ServeHTTP(w, r)
				return
			}
			if !VerifyCSRF(r, headerName) {
				// Fixed message; do not differentiate between
				// missing cookie / missing header / mismatch so
				// a probe cannot map out which side failed.
				writeAuthError(w, http.StatusForbidden, "csrf token missing or invalid")
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}
