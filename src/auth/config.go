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

	// ----------------------------------------------------------------
	// Password reset (forgot password)
	//
	// PasswordResetTokenTTLSeconds -- lifetime of the bearer token
	//   carried in the emailed reset link. Default 1 hour. Bounded
	//   at startup to [5 minutes .. 24 hours] so an operator cannot
	//   accidentally configure a permanent reset link.
	// FrontendBaseURL -- origin used to construct the user-facing
	//   reset URL ("<base>/reset-password?token=...") that the email
	//   template includes. Validated to be absolute http(s).
	// ----------------------------------------------------------------
	PasswordResetTokenTTLSeconds int    `envconfig:"PASSWORD_RESET_TOKEN_TTL_SECONDS" default:"3600"`
	FrontendBaseURL              string `envconfig:"FRONTEND_BASE_URL" default:""`

	// ----------------------------------------------------------------
	// LLM quota policy (Pro Managed / admin tier metering)
	//
	// The per-tier token caps, soft-cap percent, max-per-call ceiling,
	// allowed-models list, and reservation TTL previously lived here
	// as envconfig fields. They have moved to the tier_quota_policies
	// DB table (migration 0028) and are now mutable at runtime from
	// the admin dashboard. The gateway reads them via
	// billing/store.QuotaPolicyStore.GetPolicy(tier) with a 30 s cache
	// and explicit invalidation on UpsertPolicy.
	//
	// The HTTP-rate-limit knobs below (TierFree/ProByok/ProManaged
	// CycleRPM/Burst) are a DIFFERENT policy -- per-user anti-abuse
	// caps on POST /api/v1/cycle/run, enforced by an in-memory token
	// bucket. They are correctly env-driven (no per-user editing) and
	// stay here.
	// ----------------------------------------------------------------

	// Per-user rate limit on POST /api/v1/cycle/run. Tiered so
	// managed users (who burn the platform key) are tighter than
	// BYOK users (who pay their own bill).
	TierFreeCycleRPM                 int `envconfig:"TIER_FREE_CYCLE_RPM" default:"2"`
	TierFreeCycleBurst               int `envconfig:"TIER_FREE_CYCLE_BURST" default:"3"`
	TierProByokCycleRPM              int `envconfig:"TIER_PRO_BYOK_CYCLE_RPM" default:"30"`
	TierProByokCycleBurst            int `envconfig:"TIER_PRO_BYOK_CYCLE_BURST" default:"60"`
	TierProManagedCycleRPM           int `envconfig:"TIER_PRO_MANAGED_CYCLE_RPM" default:"10"`
	TierProManagedCycleBurst         int `envconfig:"TIER_PRO_MANAGED_CYCLE_BURST" default:"20"`

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
	// Production-mode JWT secret guard. A random secret invalidates
	// every JWT on pod restart; in production that means every user
	// is logged out on every rollout. Refuse to start. In development
	// / testing an unset secret is replaced with a fresh random value
	// so the local stack can boot without operator setup.
	// Audit ref: FV-H3.
	if c.JWTSecret == "" {
		if isProdLikeEnv() {
			return fmt.Errorf("AUTH_JWT_SECRET must be set in %s; refusing to generate a random secret because every pod restart would invalidate all JWTs", appEnv())
		}
		b := make([]byte, 64)
		if _, err := rand.Read(b); err != nil {
			return fmt.Errorf("failed to generate random JWT secret: %w", err)
		}
		c.JWTSecret = hex.EncodeToString(b)
	}
	if len(c.JWTSecret) < 32 {
		return fmt.Errorf("AUTH_JWT_SECRET must be at least 32 characters, got %d", len(c.JWTSecret))
	}
	c.jwtSecretBytes = []byte(c.JWTSecret)

	// Production-mode database URL guard. The auth store cannot operate
	// against an empty DSN. Without this, the service boots and then
	// crashes at the first SQL call with an opaque pgx error. Audit ref:
	// FV-H1.
	if strings.TrimSpace(c.DatabaseURL) == "" && isProdLikeEnv() {
		return fmt.Errorf("AUTH_DATABASE_URL must be set in %s; the auth store cannot start without a valid DSN", appEnv())
	}

	// Production-mode admin seed password guard. In production we
	// require an explicit ADMIN_PASSWORD so the first-boot seed path
	// either creates a usable admin or refuses to start. Audit ref:
	// FV-H2.
	if !c.HasAdminSeedPassword() && isProdLikeEnv() {
		return fmt.Errorf("AUTH_ADMIN_PASSWORD must be set in %s; refusing to seed the initial admin user with an empty password", appEnv())
	}

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

	if c.PasswordResetTokenTTLSeconds < 300 || c.PasswordResetTokenTTLSeconds > 86400 {
		return fmt.Errorf("PASSWORD_RESET_TOKEN_TTL_SECONDS must be 300..86400 (5m..24h), got %d", c.PasswordResetTokenTTLSeconds)
	}

	// LLM quota bounds. Token caps cannot be negative; per-call cap
	// must be > 0 so the engine has a deterministic ceiling on the
	// largest legitimate request. Soft-cap percent is informational
	// only (the SPA renders an amber banner above it) so we accept
	// 0..100.
	if c.TierProManagedDailyInputTokens < 0 ||
		c.TierProManagedDailyOutputTokens < 0 ||
		c.TierProManagedMonthlyInputTokens < 0 ||
		c.TierProManagedMonthlyOutputTokens < 0 {
		return fmt.Errorf("TIER_PRO_MANAGED_*_TOKENS must be non-negative")
	}
	if c.TierProManagedMaxInputPerCall <= 0 {
		return fmt.Errorf("TIER_PRO_MANAGED_MAX_INPUT_PER_CALL must be positive, got %d", c.TierProManagedMaxInputPerCall)
	}
	if c.TierProManagedSoftCapPercent < 0 || c.TierProManagedSoftCapPercent > 100 {
		return fmt.Errorf("TIER_PRO_MANAGED_SOFT_CAP_PERCENT must be 0..100, got %d", c.TierProManagedSoftCapPercent)
	}
	if c.LLMReservationTTLSeconds < 30 || c.LLMReservationTTLSeconds > 3600 {
		return fmt.Errorf("LLM_RESERVATION_TTL_SECONDS must be 30..3600, got %d", c.LLMReservationTTLSeconds)
	}

	// Cycle RPM tiers. RPM > 0 so a misconfigured zero does not
	// silently lock everyone out; burst >= RPM so the token bucket
	// can actually serve the steady-state rate.
	for _, p := range []struct {
		name  string
		rpm   int
		burst int
	}{
		{"FREE", c.TierFreeCycleRPM, c.TierFreeCycleBurst},
		{"PRO_BYOK", c.TierProByokCycleRPM, c.TierProByokCycleBurst},
		{"PRO_MANAGED", c.TierProManagedCycleRPM, c.TierProManagedCycleBurst},
	} {
		if p.rpm <= 0 || p.rpm > 600 {
			return fmt.Errorf("TIER_%s_CYCLE_RPM must be 1..600, got %d", p.name, p.rpm)
		}
		if p.burst < p.rpm || p.burst > 1200 {
			return fmt.Errorf("TIER_%s_CYCLE_BURST must be %d..1200, got %d", p.name, p.rpm, p.burst)
		}
	}

	// Normalise the model allow-list to lowercase, trimmed, non-empty
	// entries. An empty list means "any model the provider supports";
	// the engine still constrains by the active provider's allow-list
	// upstream when set.
	normalisedModels := make([]string, 0, len(c.TierProManagedAllowedModels))
	for _, m := range c.TierProManagedAllowedModels {
		m = strings.ToLower(strings.TrimSpace(m))
		if m != "" {
			normalisedModels = append(normalisedModels, m)
		}
	}
	c.TierProManagedAllowedModels = normalisedModels

	c.FrontendBaseURL = strings.TrimRight(strings.TrimSpace(c.FrontendBaseURL), "/")
	if c.FrontendBaseURL != "" {
		fu, err := url.Parse(c.FrontendBaseURL)
		if err != nil || fu.Scheme == "" || fu.Host == "" || (fu.Scheme != "http" && fu.Scheme != "https") {
			return fmt.Errorf("FRONTEND_BASE_URL must be an absolute http(s) URL, got %q", c.FrontendBaseURL)
		}
		if fu.Path != "" || fu.RawQuery != "" || fu.Fragment != "" {
			return fmt.Errorf("FRONTEND_BASE_URL must not contain a path, query, or fragment, got %q", c.FrontendBaseURL)
		}
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

// PasswordResetTokenTTL returns the configured reset-token lifetime.
func (c *Config) PasswordResetTokenTTL() time.Duration {
	return time.Duration(c.PasswordResetTokenTTLSeconds) * time.Second
}

// LLMReservationTTL returns the wall-clock window inside which a Commit
// or Refund must arrive before the janitor reaps a held reservation.
func (c *Config) LLMReservationTTL() time.Duration {
	return time.Duration(c.LLMReservationTTLSeconds) * time.Second
}

// LLMQuotaPolicy is a tier-agnostic snapshot of the policy fields the
// store needs. Mirror of billing/store.LLMQuotaPolicy with no time-
// duration dependency on the store package so auth can stay free of
// any billing import (the gateway-side metering handler converts to
// the store type at the boundary).
type LLMQuotaPolicy struct {
	DailyInputTokens      int64
	DailyOutputTokens     int64
	MonthlyInputTokens    int64
	MonthlyOutputTokens   int64
	MaxInputTokensPerCall int64
	SoftCapPercent        int
	AllowedModels         []string
	ReservationTTL        time.Duration
}

// LLMQuotaPolicyForTier returns the policy snapshot for the given tier
// string. Unknown tiers and BYOK both return a zero-access policy so
// the metering handler refuses any request that should not have hit it
// (the BYOK user already has their own key; metering is irrelevant).
//
// admin and pro_managed share the managed-tier numbers because admins
// already use the platform LLM key per _load_active_llm_connection.
func (c *Config) LLMQuotaPolicyForTier(tier string) LLMQuotaPolicy {
	switch strings.ToLower(strings.TrimSpace(tier)) {
	case "pro_managed", "admin":
		models := make([]string, len(c.TierProManagedAllowedModels))
		copy(models, c.TierProManagedAllowedModels)
		return LLMQuotaPolicy{
			DailyInputTokens:      c.TierProManagedDailyInputTokens,
			DailyOutputTokens:     c.TierProManagedDailyOutputTokens,
			MonthlyInputTokens:    c.TierProManagedMonthlyInputTokens,
			MonthlyOutputTokens:   c.TierProManagedMonthlyOutputTokens,
			MaxInputTokensPerCall: c.TierProManagedMaxInputPerCall,
			SoftCapPercent:        c.TierProManagedSoftCapPercent,
			AllowedModels:         models,
			ReservationTTL:        c.LLMReservationTTL(),
		}
	default:
		return LLMQuotaPolicy{ReservationTTL: c.LLMReservationTTL()}
	}
}

// CycleRateLimitForTier returns the per-user (RPM, burst) pair that the
// gateway's /api/v1/cycle/run handler should apply to this user. Unknown
// tiers fall back to the free tier so a misconfigured JWT cannot grant a
// looser limit.
func (c *Config) CycleRateLimitForTier(tier string) (int, int) {
	switch strings.ToLower(strings.TrimSpace(tier)) {
	case "pro_managed", "admin":
		return c.TierProManagedCycleRPM, c.TierProManagedCycleBurst
	case "pro_byok":
		return c.TierProByokCycleRPM, c.TierProByokCycleBurst
	default:
		return c.TierFreeCycleRPM, c.TierFreeCycleBurst
	}
}

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
