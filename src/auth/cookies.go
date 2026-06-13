// Cookie service for authenticated session transport.
//
// The platform migrated from localStorage-stored JWTs (read by every
// `fetch` call and therefore exposed to any XSS payload) to HttpOnly
// cookies whose value is never visible to JavaScript. Cookie inventory:
//
//   access_token   - HttpOnly, Secure, Path="/", SameSite=Strict by
//                    default. Sent on every authenticated request to
//                    the gateway. Short-lived (matches access-token
//                    TTL). Never readable by JS.
//
//   refresh_token  - HttpOnly, Secure, scoped to the refresh and
//                    logout endpoints only (Path="/auth") so it is
//                    never sent on regular API calls. Long-lived
//                    (matches refresh-token TTL). Never readable by JS.
//
//   csrf_token     - NOT HttpOnly (deliberately): the SPA must read it
//                    from document.cookie and echo it back in the
//                    AUTH_CSRF_HEADER on every state-changing request.
//                    Double-submit pattern; correctness depends on
//                    SameSite + Secure cookies AND, in signed mode,
//                    an HMAC bound to the authenticated user (see
//                    csrf.go).
//
// All three cookies share the same Domain (if configured), Secure
// flag and SameSite policy so a browser cannot accidentally drop
// one while keeping the others; mismatched policies are the most
// common cause of "sometimes the user is logged out" symptoms.
//
// Cookie name prefix (__Secure-)
//
//   When CookieSecure=true (always in production) every cookie is
//   written under the __Secure- prefix. This is a browser-enforced
//   invariant: a cookie whose name starts with __Secure- is rejected
//   by the browser unless it carries the Secure attribute. Any
//   future regression that downgrades Secure=false will therefore
//   produce a cookie the browser drops on the floor rather than a
//   silent insecure write. We do NOT use __Host- because it forbids
//   the Domain attribute, and production needs Domain=.exoper.com
//   for cross-subdomain SPA -> gateway cookie flow.
//
//   The reader-side helpers (AccessTokenFromCookie etc.) tolerate
//   both the prefixed and unprefixed forms, so an in-flight rollout
//   (rolling pod restart while browsers still hold old cookies) is
//   safe in both directions.
//
//   ClearAuthCookies emits delete cookies for BOTH names on each
//   path/domain so no stale cookie is left in the browser jar.
package auth

import (
	"net/http"
	"strings"
	"time"
)

// secureCookiePrefix is the RFC 6265bis-defined prefix that makes the
// Secure attribute a browser-enforced invariant. See the package
// header comment for why we picked __Secure- over __Host-.
const secureCookiePrefix = "__Secure-"

// Cookie names. Exported so the frontend (cotradee/src/lib/axios.ts)
// and tests reference the same canonical strings. The runtime cookie
// name on the wire is composed of cookieName(opts, name) which
// prepends the secure prefix when opts.Secure is true.
const (
	AccessTokenCookieName  = "access_token"
	RefreshTokenCookieName = "refresh_token"
	CSRFCookieName         = "csrf_token"
)

// Cookie path scopes.
//
//	accessTokenCookiePath  - root; sent on every API request.
//	refreshTokenCookiePath - scoped to /auth (refresh + logout only).
//	csrfCookiePath         - root; the SPA reads it once and attaches
//	                         it to every mutating call.
const (
	accessTokenCookiePath  = "/"
	refreshTokenCookiePath = "/auth"
	csrfCookiePath         = "/"
)

// CookieOptions is the materialised, validated cookie policy used by
// every Set/Clear helper in this file. Built once at startup via
// Config.CookieOptions(); nothing in this struct is mutated after
// construction.
type CookieOptions struct {
	Domain   string
	Secure   bool
	SameSite http.SameSite

	AccessTokenMaxAge  time.Duration
	RefreshTokenMaxAge time.Duration
	CSRFMaxAge         time.Duration
}

// cookieName returns the on-the-wire cookie name for the given base
// name. Adds the __Secure- prefix when opts.Secure is true. Centralised
// so set/clear/read paths cannot drift.
func cookieName(opts *CookieOptions, base string) string {
	if opts != nil && opts.Secure {
		return secureCookiePrefix + base
	}
	return base
}

// SetAccessCookie writes the short-lived HttpOnly access cookie.
func SetAccessCookie(w http.ResponseWriter, opts *CookieOptions, value string) {
	http.SetCookie(w, &http.Cookie{ // #nosec G124
		Name:     cookieName(opts, AccessTokenCookieName),
		Value:    value,
		Path:     accessTokenCookiePath,
		Domain:   opts.Domain,
		MaxAge:   int(opts.AccessTokenMaxAge.Seconds()),
		HttpOnly: true,
		Secure:   opts.Secure,
		SameSite: opts.SameSite,
	})
}

// SetRefreshCookie writes the long-lived HttpOnly refresh cookie. The
// path is deliberately scoped to /auth so the cookie does not ride
// along on regular API traffic.
func SetRefreshCookie(w http.ResponseWriter, opts *CookieOptions, value string) {
	http.SetCookie(w, &http.Cookie{ // #nosec G124
		Name:     cookieName(opts, RefreshTokenCookieName),
		Value:    value,
		Path:     refreshTokenCookiePath,
		Domain:   opts.Domain,
		MaxAge:   int(opts.RefreshTokenMaxAge.Seconds()),
		HttpOnly: true,
		Secure:   opts.Secure,
		SameSite: opts.SameSite,
	})
}

// SetCSRFCookie writes the readable CSRF cookie consumed by the SPA's
// double-submit logic. NOT HttpOnly by design.
func SetCSRFCookie(w http.ResponseWriter, opts *CookieOptions, value string) {
	http.SetCookie(w, &http.Cookie{ // #nosec G124
		Name:     cookieName(opts, CSRFCookieName),
		Value:    value,
		Path:     csrfCookiePath,
		Domain:   opts.Domain,
		MaxAge:   int(opts.CSRFMaxAge.Seconds()),
		HttpOnly: false,
		Secure:   opts.Secure,
		SameSite: opts.SameSite,
	})
}

// ClearAuthCookies expires all six cookie variants (three names *
// {prefixed, unprefixed}) with the same domain / path / SameSite /
// Secure attributes used when they were set. Using MaxAge=-1 is
// required by RFC 6265 to delete a cookie.
//
// We emit the delete for BOTH prefixed and unprefixed names so a
// rollout that flips Secure (and therefore the prefix) does not
// leave a stale cookie of the old name in the browser jar. Browsers
// silently accept a delete for a name they do not currently hold,
// so the extra Set-Cookie headers are harmless.
func ClearAuthCookies(w http.ResponseWriter, opts *CookieOptions) {
	type clearSpec struct {
		name     string
		path     string
		httpOnly bool
	}
	specs := []clearSpec{
		{AccessTokenCookieName, accessTokenCookiePath, true},
		{RefreshTokenCookieName, refreshTokenCookiePath, true},
		{CSRFCookieName, csrfCookiePath, false},
	}
	for _, s := range specs {
		for _, n := range []string{cookieName(opts, s.name), s.name} {
			http.SetCookie(w, &http.Cookie{ // #nosec G124
				Name:     n,
				Value:    "",
				Path:     s.path,
				Domain:   opts.Domain,
				MaxAge:   -1,
				HttpOnly: s.httpOnly,
				Secure:   opts.Secure,
				SameSite: opts.SameSite,
			})
		}
	}
}

// readCookieValue returns the trimmed value of the prefixed cookie
// name, falling back to the unprefixed name when the prefixed form is
// absent. Returns "" when neither exists.
func readCookieValue(r *http.Request, base string) string {
	if c, err := r.Cookie(secureCookiePrefix + base); err == nil {
		if v := strings.TrimSpace(c.Value); v != "" {
			return v
		}
	}
	if c, err := r.Cookie(base); err == nil {
		return strings.TrimSpace(c.Value)
	}
	return ""
}

// AccessTokenFromCookie returns the trimmed value of the access_token
// cookie (prefixed or unprefixed), or "" if absent.
func AccessTokenFromCookie(r *http.Request) string {
	return readCookieValue(r, AccessTokenCookieName)
}

// RefreshTokenFromCookie returns the trimmed value of the refresh_token
// cookie (prefixed or unprefixed), or "" if absent.
func RefreshTokenFromCookie(r *http.Request) string {
	return readCookieValue(r, RefreshTokenCookieName)
}
