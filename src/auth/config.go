package auth

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"strings"

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

	// jwtSecretBytes is the parsed secret used for signing.
	// Not loaded from env; derived from JWTSecret during validation.
	jwtSecretBytes []byte
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

	return nil
}

// JWTSecretBytes returns the parsed JWT signing key.
func (c *Config) JWTSecretBytes() []byte {
	return c.jwtSecretBytes
}

// HasAdminSeedPassword returns true if an admin seed password was
// explicitly configured. When false, the admin user is created
// without a password and must be set via the first-login flow.
func (c *Config) HasAdminSeedPassword() bool {
	return strings.TrimSpace(c.AdminPassword) != ""
}
