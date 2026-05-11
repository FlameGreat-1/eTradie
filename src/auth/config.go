package auth

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/kelseyhightower/envconfig"
)

// Config holds all authentication configuration loaded from environment
// variables with the AUTH_ prefix. Validated at startup; the application
// fails fast on invalid values.
type Config struct {
	// JWT signing secret. Must be at least 32 characters.
	// If not set, a random 64-byte secret is generated (development only).
	JWTSecret string `envconfig:"JWT_SECRET" default:""`

	// Access token lifetime in seconds. Default: 15 minutes.
	AccessTokenTTLSeconds int `envconfig:"ACCESS_TOKEN_TTL_SECONDS" default:"900"`

	// Refresh token lifetime in seconds. Default: 7 days.
	RefreshTokenTTLSeconds int `envconfig:"REFRESH_TOKEN_TTL_SECONDS" default:"604800"`

	// Service token lifetime in seconds. Default: 30 days.
	ServiceTokenTTLSeconds int `envconfig:"SERVICE_TOKEN_TTL_SECONDS" default:"2592000"`

	// Bcrypt cost factor. Default: 12. Range: 10-14.
	BcryptCost int `envconfig:"BCRYPT_COST" default:"12"`

	// Admin seed credentials.
	AdminUsername string `envconfig:"ADMIN_USERNAME" default:"admin"`
	AdminPassword string `envconfig:"ADMIN_PASSWORD" default:""`
	AdminEmail    string `envconfig:"ADMIN_EMAIL" default:"admin@etradie.local"`

	// Maximum active sessions per user.
	MaxSessionsPerUser int `envconfig:"MAX_SESSIONS_PER_USER" default:"5"`

	// Database URL for auth tables.
	DatabaseURL string `envconfig:"DATABASE_URL" default:""`

	// Issuer claim for JWT tokens.
	Issuer string `envconfig:"ISSUER" default:"etradie"`

	// TrustedProxyCIDRs is the list of CIDR blocks whose peer addresses
	// are treated as trusted proxies for client-IP resolution.
	TrustedProxyCIDRs []string `envconfig:"TRUSTED_PROXY_CIDRS"`

	// TrustCloudflare extends the trusted-proxy set with the published
	// Cloudflare IPv4 + IPv6 ranges.
	TrustCloudflare bool `envconfig:"TRUST_CLOUDFLARE" default:"false"`

	// CloudflareRangesDir is an optional directory containing live
	// Cloudflare CIDR files.
	CloudflareRangesDir string `envconfig:"CLOUDFLARE_RANGES_DIR" default:""`

	// ----------------------------------------------------------------
	// Google OAuth 2.0
	// ----------------------------------------------------------------

	GoogleOAuthEnabled         bool     `envconfig:"GOOGLE_OAUTH_ENABLED" default:"false"`
	GoogleClientID             string   `envconfig:"GOOGLE_CLIENT_ID" default:""`
	GoogleClientSecret         string   `envconfig:"GOOGLE_CLIENT_SECRET" default:""`
	GoogleRedirectURI          string   `envconfig:"GOOGLE_REDIRECT_URI" default:""`
	GoogleLinkRedirectURI      string   `envconfig:"GOOGLE_LINK_REDIRECT_URI" default:""`
	GoogleAllowedHostedDomains []string `envconfig:"GOOGLE_ALLOWED_HOSTED_DOMAINS"`
	OAuthFlowTTLSeconds        int      `envconfig:"OAUTH_FLOW_TTL_SECONDS" default:"600"`
	OAuthHTTPTimeoutSeconds    int      `envconfig:"OAUTH_HTTP_TIMEOUT_SECONDS" default:"10"`

	// ----------------------------------------------------------------
	// Cookie auth
	//
	// CookieDomain  -- empty for host-only (default), ".exoper.com" for
	//                  cross-subdomain production.
	// CookieSecure  -- true everywhere except local-HTTP dev. The
	//                  production-mode guard refuses false when
	//                  APP_ENV is production or staging.
	// CookieSameSite-- Strict (default), Lax (legacy escape hatch),
	//                  None (required for cross-subdomain when SPA and
	//                  gateway live on different registrable domains).
	// CSRFHeader    -- request header the SPA echoes the csrf_token
	//                  cookie back in.
	// CSRFSigned    -- true (default) selects signed double-submit
	//                  bound to userID. Setting to false reverts to
	//                  naive double-submit for a staged rollout.
	// ----------------------------------------------------------------

	CookieDomain   string `envconfig:"COOKIE_DOMAIN" default:""`
	CookieSecure   bool   `envconfig:"COOKIE_SECURE" default:"true"`
	CookieSameSite string `envconfig:"COOKIE_SAMESITE" default:"Strict"`
	CSRFHeader     string `envconfig:"CSRF_HEADER" default:"X-CSRF-Token"`
	CSRFSigned     bool   `envconfig:"CSRF_SIGNED" default:"true"`

	// ReturnTokensInBody, when true, causes /auth/login, /auth/register,
	// /auth/refresh, and the OAuth callbacks to echo the issued JWT
	// access and refresh tokens in their JSON response body. The whole
	// point of the cookie-auth migration is to remove the JS-readable
	// token surface that an XSS payload can exfiltrate, so this is
	// false by default in every environment. Legacy non-browser clients
	// that hold tokens explicitly can set it to true during their
	// migration window; production deployments MUST leave it false.
	ReturnTokensInBody bool `envconfig:"RETURN_TOKENS_IN_BODY" default:"false"`

	// AllowSameSiteLaxInProd is an explicit, documented escape hatch.
	// validate() refuses CookieSameSite=Lax in production/staging
	// unless this is true. There is no good reason to set this; it
	// exists only to keep an emergency deploy unblocked while a
	// SameSite=Strict regression is fixed.
	AllowSameSiteLaxInProd bool `envconfig:"ALLOW_SAMESITE_LAX_IN_PROD" default:"false"`

	// cookieSameSite is the parsed http.SameSite derived from
	// CookieSameSite at validate-time.
	cookieSameSite http.SameSite

	// jwtSecretBytes is the parsed secret used for signing.
	jwtSecretBytes []byte

	// ipResolver is the lazily-built ClientIPResolver.
	ipResolverOnce sync.Once
	ipResolver     *ClientIPResolver
}

// LoadConfig reads configuration from AUTH_ prefixed environment
// variables and validates all constraints.
func LoadConfig() (*Config, error) {
	var cfg Config
	if err := envconfig.Process("AUTH", &cfg); err != nil {
		return nil, fmt.Errorf("auth config: load from env: %w", err)
	}
	if err := cfg.validate(); err != nil {
		return nil, fmt.Errorf("auth config: validation: %w", err)
	}
	return &cfg, nil
}

// appEnv returns the normalised value of APP_ENV (or ENV / ENVIRONMENT
// as fallbacks). "" means unset; treat as development by the caller.
func appEnv() string {
	for _, k := range []string{"APP_ENV", "ENV", "ENVIRONMENT"} {
		if v := strings.ToLower(strings.TrimSpace(os.Getenv(k))); v != "" {
			return v
		}
	}
	return ""
}

// isProdLikeEnv reports whether the runtime environment is one in
// which the cookie-security guards must be enforced.
func isProdLikeEnv() bool {
	switch appEnv() {
	case "production", "prod", "staging":
		return true
	}
	return false
}

func (c *Config) validate() error {
	if c.JWTSecret == "" {
		b := make([]byte, 64)
		if _, err := rand.Read(b); err != nil {
			return fmt.Errorf("failed to generate random JWT secret: %w", err)
		}
		c.JWTSecret = hex.EncodeToString(b)
	}
	if len(c.JWTSecret) < 32 {
		return fmt.Errorf("JWT_SECRET must be at least 32 characters, got %d", len(c.JWTSecret))
	}
	c.jwtSecretBytes = []byte(c.JWTSecret)

	if c.AccessTokenTTLSeconds < 60 || c.AccessTokenTTLSeconds > 86400 {
		return fmt.Errorf("ACCESS_TOKEN_TTL_SECONDS must be 60..86400, got %d", c.AccessTokenTTLSeconds)
	}
	if c.RefreshTokenTTLSeconds < 3600 || c.RefreshTokenTTLSeconds > 2592000 {
		return fmt.Errorf("REFRESH_TOKEN_TTL_SECONDS must be 3600..2592000 (1h..30d), got %d", c.RefreshTokenTTLSeconds)
	}
	if c.ServiceTokenTTLSeconds < 3600 || c.ServiceTokenTTLSeconds > 7776000 {
		return fmt.Errorf("SERVICE_TOKEN_TTL_SECONDS must be 3600..7776000 (1h..90d), got %d", c.ServiceTokenTTLSeconds)
	}

	if c.BcryptCost < 10 || c.BcryptCost > 14 {
		return fmt.Errorf("BCRYPT_COST must be 10..14, got %d", c.BcryptCost)
	}

	c.AdminUsername = strings.TrimSpace(c.AdminUsername)
	if c.AdminUsername == "" {
		return fmt.Errorf("ADMIN_USERNAME must not be empty")
	}
	if len(c.AdminUsername) < 3 || len(c.AdminUsername) > 32 {
		return fmt.Errorf("ADMIN_USERNAME must be 3..32 characters, got %d", len(c.AdminUsername))
	}

	c.AdminEmail = strings.TrimSpace(c.AdminEmail)
	if c.AdminEmail == "" {
		return fmt.Errorf("ADMIN_EMAIL must not be empty")
	}
	if !strings.Contains(c.AdminEmail, "@") {
		return fmt.Errorf("ADMIN_EMAIL must be a valid email address")
	}

	if c.MaxSessionsPerUser < 1 || c.MaxSessionsPerUser > 20 {
		return fmt.Errorf("MAX_SESSIONS_PER_USER must be 1..20, got %d", c.MaxSessionsPerUser)
	}

	if _, bad := ParseTrustedCIDRs(c.TrustedProxyCIDRs); len(bad) > 0 {
		return fmt.Errorf("TRUSTED_PROXY_CIDRS contains malformed entries: %v", bad)
	}

	// Cookie + CSRF validation.
	switch strings.ToLower(strings.TrimSpace(c.CookieSameSite)) {
	case "strict":
		c.cookieSameSite = http.SameSiteStrictMode
	case "lax":
		c.cookieSameSite = http.SameSiteLaxMode
	case "none":
		c.cookieSameSite = http.SameSiteNoneMode
		if !c.CookieSecure {
			return fmt.Errorf("COOKIE_SAMESITE=None requires COOKIE_SECURE=true; browsers reject the combination otherwise")
		}
	default:
		return fmt.Errorf("COOKIE_SAMESITE must be Strict, Lax, or None, got %q", c.CookieSameSite)
	}
	c.CSRFHeader = strings.TrimSpace(c.CSRFHeader)
	if c.CSRFHeader == "" {
		return fmt.Errorf("CSRF_HEADER must not be empty")
	}

	// Production-mode cookie security guards. The host runtime sets
	// APP_ENV (or ENV / ENVIRONMENT); when it indicates a prod-like
	// deployment, refuse insecure cookie postures. These guards do
	// nothing in local dev (APP_ENV=development / unset).
	if isProdLikeEnv() {
		if !c.CookieSecure {
			return fmt.Errorf("COOKIE_SECURE must be true in %s; refusing to start with plain-HTTP cookies", appEnv())
		}
		if c.cookieSameSite == http.SameSiteLaxMode && !c.AllowSameSiteLaxInProd {
			return fmt.Errorf("COOKIE_SAMESITE=Lax is unsafe in %s; set COOKIE_SAMESITE=Strict (single host) or None+Secure=true (cross-subdomain), or set ALLOW_SAMESITE_LAX_IN_PROD=true to override", appEnv())
		}
	}

	if c.GoogleOAuthEnabled {
		c.GoogleClientID = strings.TrimSpace(c.GoogleClientID)
		c.GoogleClientSecret = strings.TrimSpace(c.GoogleClientSecret)
		c.GoogleRedirectURI = strings.TrimSpace(c.GoogleRedirectURI)

		if c.GoogleClientID == "" {
			return fmt.Errorf("GOOGLE_CLIENT_ID must be set when GOOGLE_OAUTH_ENABLED=true")
		}
		if c.GoogleClientSecret == "" {
			return fmt.Errorf("GOOGLE_CLIENT_SECRET must be set when GOOGLE_OAUTH_ENABLED=true")
		}
		if c.GoogleRedirectURI == "" {
			return fmt.Errorf("GOOGLE_REDIRECT_URI must be set when GOOGLE_OAUTH_ENABLED=true")
		}
		u, err := url.Parse(c.GoogleRedirectURI)
		if err != nil || u.Scheme == "" || u.Host == "" || (u.Scheme != "http" && u.Scheme != "https") {
			return fmt.Errorf("GOOGLE_REDIRECT_URI must be an absolute http(s) URL, got %q", c.GoogleRedirectURI)
		}
		c.GoogleLinkRedirectURI = strings.TrimSpace(c.GoogleLinkRedirectURI)
		if c.GoogleLinkRedirectURI == "" {
			return fmt.Errorf("GOOGLE_LINK_REDIRECT_URI must be set when GOOGLE_OAUTH_ENABLED=true")
		}
		lu, err := url.Parse(c.GoogleLinkRedirectURI)
		if err != nil || lu.Scheme == "" || lu.Host == "" || (lu.Scheme != "http" && lu.Scheme != "https") {
			return fmt.Errorf("GOOGLE_LINK_REDIRECT_URI must be an absolute http(s) URL, got %q", c.GoogleLinkRedirectURI)
		}
		if strings.EqualFold(c.GoogleRedirectURI, c.GoogleLinkRedirectURI) {
			return fmt.Errorf("GOOGLE_REDIRECT_URI and GOOGLE_LINK_REDIRECT_URI must differ; register both in Google Cloud Console")
		}
		normalised := make([]string, 0, len(c.GoogleAllowedHostedDomains))
		for _, d := range c.GoogleAllowedHostedDomains {
			d = strings.ToLower(strings.TrimSpace(d))
			if d != "" {
				normalised = append(normalised, d)
			}
		}
		c.GoogleAllowedHostedDomains = normalised

		if c.OAuthFlowTTLSeconds < 60 || c.OAuthFlowTTLSeconds > 1800 {
			return fmt.Errorf("OAUTH_FLOW_TTL_SECONDS must be 60..1800, got %d", c.OAuthFlowTTLSeconds)
		}
		if c.OAuthHTTPTimeoutSeconds < 1 || c.OAuthHTTPTimeoutSeconds > 30 {
			return fmt.Errorf("OAUTH_HTTP_TIMEOUT_SECONDS must be 1..30, got %d", c.OAuthHTTPTimeoutSeconds)
		}
	}

	return nil
}

func (c *Config) JWTSecretBytes() []byte { return c.jwtSecretBytes }

// CookieOptions returns the materialised cookie policy used by the
// Set/Clear helpers. The CSRF cookie shares the access token's
// MaxAge so both are rotated together; mismatched lifetimes would
// produce a 403 on the next mutating call after the CSRF cookie
// expired but before the access cookie did.
func (c *Config) CookieOptions() *CookieOptions {
	return &CookieOptions{
		Domain:             c.CookieDomain,
		Secure:             c.CookieSecure,
		SameSite:           c.cookieSameSite,
		AccessTokenMaxAge:  time.Duration(c.AccessTokenTTLSeconds) * time.Second,
		RefreshTokenMaxAge: time.Duration(c.RefreshTokenTTLSeconds) * time.Second,
		CSRFMaxAge:         time.Duration(c.AccessTokenTTLSeconds) * time.Second,
	}
}

// IPResolver returns the lazily-initialised ClientIPResolver.
func (c *Config) IPResolver() *ClientIPResolver {
	c.ipResolverOnce.Do(func() {
		c.ipResolver = NewClientIPResolverWithRangesDir(
			c.TrustedProxyCIDRs,
			c.TrustCloudflare,
			c.CloudflareRangesDir,
		)
	})
	return c.ipResolver
}

// SetTestSecret configures the Config with a known JWT secret for test
// harnesses. Sets all required fields to sensible defaults so the
// Config is usable without environment variable loading.
func (c *Config) SetTestSecret(secret string) {
	c.JWTSecret = secret
	c.jwtSecretBytes = []byte(secret)
	if c.AccessTokenTTLSeconds == 0 {
		c.AccessTokenTTLSeconds = 3600
	}
	if c.RefreshTokenTTLSeconds == 0 {
		c.RefreshTokenTTLSeconds = 86400
	}
	if c.Issuer == "" {
		c.Issuer = "etradie-test"
	}
	if c.ServiceTokenTTLSeconds == 0 {
		c.ServiceTokenTTLSeconds = 2592000
	}
	if c.cookieSameSite == 0 {
		c.cookieSameSite = http.SameSiteStrictMode
	}
	if c.CSRFHeader == "" {
		c.CSRFHeader = "X-CSRF-Token"
	}
}

func (c *Config) HasAdminSeedPassword() bool {
	return strings.TrimSpace(c.AdminPassword) != ""
}
