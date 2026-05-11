// Cookie service for authenticated session transport.
//
// The platform is migrating from localStorage-stored JWTs (read by every
// `fetch` call and therefore exposed to any XSS payload) to HttpOnly
// cookies whose value is never visible to JavaScript. The migration is
// staged across batches 10a (this file + CSRF), 10b (middleware), 10c
// (handler wiring), and 11 (frontend).
//
// Cookie inventory:
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
//                    This is the classic double-submit pattern. The
//                    value itself is random and tied to nothing on the
//                    server side; correctness depends purely on cookie
//                    + header agreeing under SameSite + Secure cookies.
//
// All three cookies share the same Domain (if configured), Secure flag
// and SameSite policy so a browser cannot accidentally drop one while
// keeping the others; mismatched policies are the most common cause
// of "sometimes the user is logged out" symptoms.
package auth

import (
	"net/http"
	"strings"
	"time"
)

// Cookie names. Exported so the frontend (batch 11) and tests can
// reference the same canonical strings.
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
	// Domain is the cookie Domain attribute. Empty means host-only,
	// which is the safest default for single-host deployments. Set
	// (e.g. ".exoper.com") only when the SPA and the API live on
	// different subdomains of the same registrable domain.
	Domain string

	// Secure forces the cookie to be sent only over HTTPS. Must be
	// true behind any real edge. Local development with plain HTTP
	// may disable it; the Config validator pairs Secure=false with
	// the SameSite rule (None requires Secure).
	Secure bool

	// SameSite controls when the browser attaches the cookie to
	// cross-site navigations. Strict is the default; Lax is needed
	// when a third-party site must navigate into an authenticated
	// page; None requires Secure=true.
	SameSite http.SameSite

	// AccessTokenMaxAge / RefreshTokenMaxAge / CSRFMaxAge are the
	// cookie lifetimes derived from the access/refresh TTLs. The
	// CSRF cookie is refreshed alongside the access token.
	AccessTokenMaxAge  time.Duration
	RefreshTokenMaxAge time.Duration
	CSRFMaxAge         time.Duration
}

// SetAccessCookie writes the short-lived HttpOnly access cookie.
func SetAccessCookie(w http.ResponseWriter, opts *CookieOptions, value string) {
	http.SetCookie(w, &http.Cookie{
		Name:     AccessTokenCookieName,
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
	http.SetCookie(w, &http.Cookie{
		Name:     RefreshTokenCookieName,
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
	http.SetCookie(w, &http.Cookie{
		Name:     CSRFCookieName,
		Value:    value,
		Path:     csrfCookiePath,
		Domain:   opts.Domain,
		MaxAge:   int(opts.CSRFMaxAge.Seconds()),
		HttpOnly: false,
		Secure:   opts.Secure,
		SameSite: opts.SameSite,
	})
}

// ClearAuthCookies expires all three cookies with the same domain /
// path / SameSite / Secure attributes used when they were set. Using
// MaxAge=-1 (rather than Value="") is required by RFC 6265 to delete
// a cookie.
func ClearAuthCookies(w http.ResponseWriter, opts *CookieOptions) {
	http.SetCookie(w, &http.Cookie{
		Name:     AccessTokenCookieName,
		Value:    "",
		Path:     accessTokenCookiePath,
		Domain:   opts.Domain,
		MaxAge:   -1,
		HttpOnly: true,
		Secure:   opts.Secure,
		SameSite: opts.SameSite,
	})
	http.SetCookie(w, &http.Cookie{
		Name:     RefreshTokenCookieName,
		Value:    "",
		Path:     refreshTokenCookiePath,
		Domain:   opts.Domain,
		MaxAge:   -1,
		HttpOnly: true,
		Secure:   opts.Secure,
		SameSite: opts.SameSite,
	})
	http.SetCookie(w, &http.Cookie{
		Name:     CSRFCookieName,
		Value:    "",
		Path:     csrfCookiePath,
		Domain:   opts.Domain,
		MaxAge:   -1,
		HttpOnly: false,
		Secure:   opts.Secure,
		SameSite: opts.SameSite,
	})
}

// AccessTokenFromCookie returns the trimmed value of the access_token
// cookie, or "" if absent. Read-side helper consumed by 10b's
// middleware so cookie-name knowledge stays in one place.
func AccessTokenFromCookie(r *http.Request) string {
	c, err := r.Cookie(AccessTokenCookieName)
	if err != nil {
		return ""
	}
	return strings.TrimSpace(c.Value)
}

// RefreshTokenFromCookie returns the trimmed value of the refresh_token
// cookie, or "" if absent. Consumed by /auth/refresh and /auth/logout
// in 10c.
func RefreshTokenFromCookie(r *http.Request) string {
	c, err := r.Cookie(RefreshTokenCookieName)
	if err != nil {
		return ""
	}
	return strings.TrimSpace(c.Value)
}
