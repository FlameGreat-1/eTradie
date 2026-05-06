package auth

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"net/url"
	"strings"
	"sync"

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
	// Used for internal service-to-service authentication (e.g., background
	// trade monitoring, EOD checks, news protection) that must operate
	// autonomously 24/7 without user presence. These tokens carry the
	// user's identity (sub, username, role) so the Python engine resolves
	// the correct broker connection, but are not tied to user sessions.
	ServiceTokenTTLSeconds int `envconfig:"SERVICE_TOKEN_TTL_SECONDS" default:"2592000"`

	// Bcrypt cost factor. Default: 12. Range: 10-14.
	BcryptCost int `envconfig:"BCRYPT_COST" default:"12"`

	// Admin seed credentials. Used to create the initial admin user
	// on first startup if no admin exists in the database.
	AdminUsername string `envconfig:"ADMIN_USERNAME" default:"admin"`
	AdminPassword string `envconfig:"ADMIN_PASSWORD" default:""`
	AdminEmail    string `envconfig:"ADMIN_EMAIL" default:"admin@etradie.local"`

	// Maximum active sessions per user. Oldest session is revoked
	// when this limit is exceeded. Default: 5.
	MaxSessionsPerUser int `envconfig:"MAX_SESSIONS_PER_USER" default:"5"`

	// Database URL for auth tables. Reuses the main PostgreSQL instance.
	// Falls back to the EXECUTION_DATABASE_URL pattern if not set.
	DatabaseURL string `envconfig:"DATABASE_URL" default:""`

	// Issuer claim for JWT tokens.
	Issuer string `envconfig:"ISSUER" default:"etradie"`

	// TrustedProxyCIDRs is the list of CIDR blocks whose peer addresses
	// are treated as trusted proxies for client-IP resolution. When the
	// HTTP request's immediate peer is in one of these ranges, the
	// resolver honours CF-Connecting-IP / X-Forwarded-For / X-Real-IP.
	// Otherwise, those headers are ignored and the peer address is
	// returned as the client IP. This makes header spoofing impossible
	// from outside the trusted edge.
	//
	// Default: empty. With no trusted proxies, the resolver always
	// returns the immediate peer, which is the safe default for any
	// deployment where the edge has not been explicitly configured.
	//
	// Production deployment behind edge-ingress + envoy should list the
	// pod CIDR of edge-ingress (and, if applicable, the envoy pod CIDR
	// when envoy is co-located with gateway). Production deployment
	// behind Cloudflare should additionally set AUTH_TRUST_CLOUDFLARE.
	TrustedProxyCIDRs []string `envconfig:"TRUSTED_PROXY_CIDRS"`

	// TrustCloudflare extends the trusted-proxy set with the published
	// Cloudflare IPv4 + IPv6 ranges. Set to true when Cloudflare is
	// the front door of the deployment. Default: false.
	TrustCloudflare bool `envconfig:"TRUST_CLOUDFLARE" default:"false"`

	// CloudflareRangesDir is an optional directory containing
	// `ipv4.txt` and `ipv6.txt` files with one CIDR per line. When set
	// AND TrustCloudflare is true, the resolver reads the file contents
	// at startup INSTEAD of the in-binary embedded list. This lets the
	// platform pick up live-refreshed Cloudflare ranges (chart-mounted
	// from helm/gateway/files/cloudflare/) without requiring a binary
	// rebuild every time Cloudflare publishes a new range.
	//
	// The chart sets this to /etc/etradie/cloudflare in production via
	// the gateway ConfigMap when trustChain.trustCloudflare is true.
	// On read error or missing dir, the resolver falls back to the
	// embedded list with a single warning to stderr - no panic, no
	// startup failure.
	//
	// Default: empty (use embedded list only).
	CloudflareRangesDir string `envconfig:"CLOUDFLARE_RANGES_DIR" default:""`

	// ----------------------------------------------------------------
	// Google OAuth 2.0
	//
	// Authorization Code with PKCE, server-mediated. The browser never
	// holds the Google client secret or a Google access/ID token; only
	// the gateway exchanges the authorization code at Google's token
	// endpoint and verifies the returned ID token via Google's JWKS.
	//
	// All AUTH_GOOGLE_* fields are optional and ignored unless
	// AUTH_GOOGLE_OAUTH_ENABLED=true. When enabled, ClientID,
	// ClientSecret, and RedirectURI are mandatory and validated at
	// startup so misconfiguration fails fast and never silently.
	// ----------------------------------------------------------------

	// GoogleOAuthEnabled toggles the Google sign-in endpoints.
	// When false (default), no OAuth routes are mounted and no
	// AUTH_GOOGLE_* validation is performed.
	GoogleOAuthEnabled bool `envconfig:"GOOGLE_OAUTH_ENABLED" default:"false"`

	// GoogleClientID is the OAuth 2.0 client ID issued by Google Cloud
	// Console for this application. Used as the `client_id` query
	// parameter on the authorize URL and as the audience claim that
	// Google's ID token must match.
	GoogleClientID string `envconfig:"GOOGLE_CLIENT_ID" default:""`

	// GoogleClientSecret is the OAuth 2.0 client secret. Used only on
	// the server-side token-exchange request to oauth2.googleapis.com
	// /token. Never exposed to the browser.
	GoogleClientSecret string `envconfig:"GOOGLE_CLIENT_SECRET" default:""`

	// GoogleRedirectURI is the absolute URL Google redirects the
	// browser to after consent for the SIGN-IN flow. Must exactly
	// match one of the "Authorized redirect URIs" registered in
	// Google Cloud Console. Convention:
	//   https://<frontend-host>/auth/callback/google.
	GoogleRedirectURI string `envconfig:"GOOGLE_REDIRECT_URI" default:""`

	// GoogleLinkRedirectURI is the absolute URL Google redirects the
	// browser to after consent for the ACCOUNT-LINK flow. Must be
	// distinct from GoogleRedirectURI and registered as a second
	// entry in Google Cloud Console's "Authorized redirect URIs"
	// list. Convention:
	//   https://<frontend-host>/settings/oauth/callback/google.
	//
	// Keeping the link callback on its own URI is the standard
	// defence against cross-flow confusion: even if flow_kind or
	// state leaked between the two paths, a sign-in flow could
	// never complete through the link handler because Google would
	// have redirected the browser to the wrong URL.
	GoogleLinkRedirectURI string `envconfig:"GOOGLE_LINK_REDIRECT_URI" default:""`

	// GoogleAllowedHostedDomains, if non-empty, restricts sign-in to
	// Google Workspace tenants whose `hd` claim matches one of the
	// listed domains (e.g. "exoper.com"). Empty means any Google
	// account is accepted (consumer + workspace). Comparison is
	// case-insensitive.
	GoogleAllowedHostedDomains []string `envconfig:"GOOGLE_ALLOWED_HOSTED_DOMAINS"`

	// OAuthFlowTTLSeconds is how long an authorize-step record is
	// valid before its state/code_verifier/nonce are discarded.
	// Bounds: 60..1800 (1 min..30 min). Default: 600 (10 min).
	OAuthFlowTTLSeconds int `envconfig:"OAUTH_FLOW_TTL_SECONDS" default:"600"`

	// OAuthHTTPTimeoutSeconds caps every outbound HTTP request the
	// gateway makes to Google's token endpoint and JWKS endpoint.
	// Bounds: 1..30. Default: 10.
	OAuthHTTPTimeoutSeconds int `envconfig:"OAUTH_HTTP_TIMEOUT_SECONDS" default:"10"`

	// jwtSecretBytes is the parsed secret used for signing.
	// Not loaded from env; derived from JWTSecret during validation.
	jwtSecretBytes []byte

	// ipResolver is the lazily-built ClientIPResolver. Constructed once
	// after validation and cached for the lifetime of the Config.
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

func (c *Config) validate() error {
	// JWT secret: generate random if empty (dev mode), require 32+ chars in production.
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

	// Token TTL bounds.
	if c.AccessTokenTTLSeconds < 60 || c.AccessTokenTTLSeconds > 86400 {
		return fmt.Errorf("ACCESS_TOKEN_TTL_SECONDS must be 60..86400, got %d", c.AccessTokenTTLSeconds)
	}
	if c.RefreshTokenTTLSeconds < 3600 || c.RefreshTokenTTLSeconds > 2592000 {
		return fmt.Errorf("REFRESH_TOKEN_TTL_SECONDS must be 3600..2592000 (1h..30d), got %d", c.RefreshTokenTTLSeconds)
	}
	if c.ServiceTokenTTLSeconds < 3600 || c.ServiceTokenTTLSeconds > 7776000 {
		return fmt.Errorf("SERVICE_TOKEN_TTL_SECONDS must be 3600..7776000 (1h..90d), got %d", c.ServiceTokenTTLSeconds)
	}

	// Bcrypt cost bounds.
	if c.BcryptCost < 10 || c.BcryptCost > 14 {
		return fmt.Errorf("BCRYPT_COST must be 10..14, got %d", c.BcryptCost)
	}

	// Admin seed validation.
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

	// Max sessions bounds.
	if c.MaxSessionsPerUser < 1 || c.MaxSessionsPerUser > 20 {
		return fmt.Errorf("MAX_SESSIONS_PER_USER must be 1..20, got %d", c.MaxSessionsPerUser)
	}

	// Trusted-proxy CIDR validation: surface bad values at startup.
	if _, bad := ParseTrustedCIDRs(c.TrustedProxyCIDRs); len(bad) > 0 {
		return fmt.Errorf("TRUSTED_PROXY_CIDRS contains malformed entries: %v", bad)
	}

	// Google OAuth: only validate when explicitly enabled. Validation
	// is strict so a half-configured production deployment fails fast.
	// All OAuth-only knobs (TTL, HTTP timeout) are also bounded only
	// when OAuth is enabled, so an operator who never plans to use
	// federated login does not pay startup cost or hit confusing
	// errors about unused fields.
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

// JWTSecretBytes returns the parsed JWT signing key.
func (c *Config) JWTSecretBytes() []byte {
	return c.jwtSecretBytes
}

// IPResolver returns the lazily-initialised ClientIPResolver built from
// TrustedProxyCIDRs, TrustCloudflare, and (when set) the contents of
// CloudflareRangesDir. Safe for concurrent use.
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

// SetTestSecret configures the Config with a known JWT secret for use
// in test harnesses. Sets all required fields to sensible defaults so
// the Config is usable without environment variable loading.
func (c *Config) SetTestSecret(secret string) {
	c.JWTSecret = secret
	c.jwtSecretBytes = []byte(secret)
	if c.AccessTokenTTLSeconds == 0 {
		c.AccessTokenTTLSeconds = 3600 // 1 hour for tests
	}
	if c.RefreshTokenTTLSeconds == 0 {
		c.RefreshTokenTTLSeconds = 86400 // 1 day for tests
	}
	if c.Issuer == "" {
		c.Issuer = "etradie-test"
	}
	if c.ServiceTokenTTLSeconds == 0 {
		c.ServiceTokenTTLSeconds = 2592000 // 30 days for tests
	}
}

// HasAdminSeedPassword returns true if an admin seed password was
// explicitly configured. When false, the admin user is created
// without a password and must be set via the first-login flow.
func (c *Config) HasAdminSeedPassword() bool {
	return strings.TrimSpace(c.AdminPassword) != ""
}
