// CSRF defence for cookie-authenticated state-changing requests.
//
// The token is delivered to the browser as a NON-HttpOnly cookie
// (csrf_token) and the SPA echoes it back in a header (default
// X-CSRF-Token). On every state-changing request the server compares
// the cookie value to the header value with constant-time compare.
//
// Two modes are supported, selected by Config.CSRFSigned:
//
//   Signed double-submit (default, AUTH_CSRF_SIGNED=true):
//     cookie / header value = "<random_hex>.<hmac_sha256_hex>" where
//     the HMAC is keyed on the JWT secret and computed over
//     random_hex || user_id. VerifyCSRF recomputes the HMAC against
//     the user_id from the authenticated request context and rejects
//     any mismatch in constant time. A sibling-subdomain XSS that
//     reads the cookie cannot replay it against a different user's
//     session because the HMAC is bound to the user.
//
//   Naive double-submit (legacy, AUTH_CSRF_SIGNED=false):
//     cookie value = random hex; header echoes it verbatim. Kept for
//     a staged rollout when the SPA is being updated in lockstep.
//
// In both modes:
//   - Safe methods (GET, HEAD, OPTIONS) bypass the check.
//   - Mutating methods (POST, PUT, PATCH, DELETE) are gated.
//   - Failures return 403 with a fixed generic message so a probe
//     cannot map out which side failed.
//   - The cookie/header are compared with constant-time primitives.
package auth

import (
	"context"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"net/http"
	"strings"
)

// csrfTokenRandomBytes is the number of random bytes encoded into the
// "random" portion of a CSRF token. 32 bytes -> 64 hex chars, identical
// to the refresh-token strength so the same statistical guarantees apply.
const csrfTokenRandomBytes = 32

// csrfHMACSeparator separates the random portion from the HMAC portion
// in a signed CSRF token. A dot is unambiguous (hex never contains it)
// and matches the separator JWT uses for the same purpose.
const csrfHMACSeparator = "."

// csrfRequiredMethods is the set of HTTP methods that REQUIRE a
// matching CSRF cookie + header. Anything not in this set passes
// through unmodified.
var csrfRequiredMethods = map[string]bool{
	http.MethodPost:   true,
	http.MethodPut:    true,
	http.MethodPatch:  true,
	http.MethodDelete: true,
}

// GenerateCSRFTokenRandom returns a fresh, hex-encoded random token of
// csrfTokenRandomBytes*2 chars. This is the "random" portion of a
// signed token, and is also the full token in legacy unsigned mode.
func GenerateCSRFTokenRandom() (string, error) {
	b := make([]byte, csrfTokenRandomBytes)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

// SignCSRFToken returns the signed double-submit token for the given
// user. Format: "<random_hex>.<hmac_sha256_hex>" where the HMAC is
// keyed on `secret` (the JWT signing secret) and computed over
// random_hex || ":" || userID. The colon separator prevents an
// attacker who controls one of the inputs from constructing a
// collision against a different (random, userID) pair.
func SignCSRFToken(secret []byte, userID, randomHex string) string {
	mac := hmac.New(sha256.New, secret)
	_, _ = mac.Write([]byte(randomHex))
	_, _ = mac.Write([]byte(":"))
	_, _ = mac.Write([]byte(userID))
	return randomHex + csrfHMACSeparator + hex.EncodeToString(mac.Sum(nil))
}

// GenerateCSRFToken returns a fresh CSRF cookie value for the given
// user. When signed=true the token is signed double-submit bound to
// userID; otherwise it is naive double-submit (random only).
//
// secret is the HMAC key (the JWT signing secret). userID is the
// authenticated user's ID (sub claim). Both are required in signed
// mode; userID may be empty in unsigned mode but must still be
// passed by the caller to keep the call site uniform.
func GenerateCSRFToken(secret []byte, userID string, signed bool) (string, error) {
	randomHex, err := GenerateCSRFTokenRandom()
	if err != nil {
		return "", err
	}
	if !signed {
		return randomHex, nil
	}
	return SignCSRFToken(secret, userID, randomHex), nil
}

// csrfVerifyConfig captures everything VerifyCSRF needs to make its
// decision. Constructed once per request by RequireCSRF; not exported.
type csrfVerifyConfig struct {
	HeaderName string
	Signed     bool
	Secret     []byte
}

// verifyCSRFAgainstContext reads the csrf_token cookie and the
// configured CSRF header from the request and returns true iff:
//   - both are present and non-empty,
//   - in unsigned mode: they are equal length and byte-for-byte equal
//     under constant-time compare;
//   - in signed mode: both parse as <random>.<hmac>, the random
//     portions match in constant time, the cookie's HMAC matches a
//     freshly-recomputed HMAC over (random, userID) in constant time,
//     AND the userID is present in the request context (RequireAuth
//     must have run first).
//
// Any other outcome returns false. Callers map this to 403.
func verifyCSRFAgainstContext(ctx context.Context, r *http.Request, vc *csrfVerifyConfig) bool {
	if vc == nil || vc.HeaderName == "" {
		return false
	}
	cookie, err := r.Cookie(CSRFCookieName)
	if err != nil || cookie.Value == "" {
		// Backwards-compat: also try the __Secure- prefixed name when
		// the unprefixed cookie is absent. The cookies.go writer side
		// chooses the name based on Secure flag; this reader tolerates
		// either so an in-flight rollout where the writer was updated
		// but the browser still holds the old name keeps working.
		cookie, err = r.Cookie(secureCookiePrefix + CSRFCookieName)
		if err != nil || cookie.Value == "" {
			return false
		}
	}
	header := r.Header.Get(vc.HeaderName)
	if header == "" {
		return false
	}

	if !vc.Signed {
		return constantTimeEqualString(cookie.Value, header)
	}

	// Signed mode: require the authenticated user from context. The
	// middleware chain is RequireAuth -> RequireCSRF, so by the time
	// we get here the claims have already been verified. A missing
	// user is a wiring bug, surfaced as a 403 rather than panicking.
	userID := UserIDFromContext(ctx)
	if userID == "" {
		return false
	}

	cookieRandom, cookieMAC, ok := splitSignedCSRFToken(cookie.Value)
	if !ok {
		return false
	}
	headerRandom, headerMAC, ok := splitSignedCSRFToken(header)
	if !ok {
		return false
	}

	// The random portions must match between cookie and header (the
	// double-submit invariant) AND the HMAC in the cookie must match
	// a freshly-recomputed HMAC over (random, userID). We also check
	// the header's HMAC equals the cookie's HMAC to refuse any client
	// that echoed an outdated header.
	if !constantTimeEqualString(cookieRandom, headerRandom) {
		return false
	}
	if !constantTimeEqualString(cookieMAC, headerMAC) {
		return false
	}
	expected := SignCSRFToken(vc.Secret, userID, cookieRandom)
	_, expectedMAC, ok := splitSignedCSRFToken(expected)
	if !ok {
		return false
	}
	return constantTimeEqualString(cookieMAC, expectedMAC)
}

// splitSignedCSRFToken splits a signed token into its random and MAC
// parts. Returns ok=false if the format is wrong or either side is
// empty. Both sides must be valid hex; length is not enforced here
// because constant-time comparison handles unequal lengths safely.
func splitSignedCSRFToken(s string) (random, mac string, ok bool) {
	i := strings.IndexByte(s, '.')
	if i <= 0 || i >= len(s)-1 {
		return "", "", false
	}
	return s[:i], s[i+1:], true
}

// constantTimeEqualString wraps subtle.ConstantTimeCompare with the
// up-front length check so unequal lengths return false without
// short-circuiting on the comparator.
func constantTimeEqualString(a, b string) bool {
	ab := []byte(a)
	bb := []byte(b)
	if len(ab) != len(bb) {
		return false
	}
	return subtle.ConstantTimeCompare(ab, bb) == 1
}

// VerifyCSRF retains the legacy unsigned signature for callers that
// have not yet been updated to pass a verify config. It is wired only
// to the unsigned path; the signed path is reachable exclusively via
// the RequireCSRF middleware which constructs its own csrfVerifyConfig
// at startup.
//
// Deprecated: prefer RequireCSRF for new code. Kept for backward
// compatibility with external test harnesses that called VerifyCSRF
// directly. Will be removed once those harnesses migrate.
func VerifyCSRF(r *http.Request, headerName string) bool {
	return verifyCSRFAgainstContext(r.Context(), r, &csrfVerifyConfig{
		HeaderName: headerName,
		Signed:     false,
	})
}

// RequireCSRF returns HTTP middleware that enforces the double-submit
// CSRF check on state-changing methods. Must run AFTER any auth
// middleware so an unauthenticated request is rejected with 401, not
// 403, AND so the user_id is in context for signed-mode verification.
//
// Chain order in production:
//
//	authMiddleware( RequireCSRF(cfg)( handler ) )
//
// cfg.CSRFHeader is the header name the SPA echoes the cookie in.
// cfg.CSRFSigned selects signed vs naive double-submit.
// cfg.JWTSecretBytes() is the HMAC key in signed mode.
func RequireCSRF(cfg *Config) func(http.Handler) http.Handler {
	vc := &csrfVerifyConfig{
		HeaderName: cfg.CSRFHeader,
		Signed:     cfg.CSRFSigned,
		Secret:     cfg.JWTSecretBytes(),
	}
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if !csrfRequiredMethods[r.Method] {
				next.ServeHTTP(w, r)
				return
			}
			if !verifyCSRFAgainstContext(r.Context(), r, vc) {
				writeAuthError(w, http.StatusForbidden, "csrf token missing or invalid")
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

// RequireCSRFHeader returns the legacy header-only middleware factory.
// Maintained for callers that explicitly want unsigned naive double-
// submit without building a full Config. New code MUST use RequireCSRF.
//
// Deprecated: prefer RequireCSRF.
func RequireCSRFHeader(headerName string) func(http.Handler) http.Handler {
	vc := &csrfVerifyConfig{
		HeaderName: headerName,
		Signed:     false,
	}
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if !csrfRequiredMethods[r.Method] {
				next.ServeHTTP(w, r)
				return
			}
			if !verifyCSRFAgainstContext(r.Context(), r, vc) {
				writeAuthError(w, http.StatusForbidden, "csrf token missing or invalid")
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}
