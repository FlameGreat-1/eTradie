package auth

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"strings"
	"time"

	"golang.org/x/crypto/bcrypt"
)

// ---------------------------------------------------------------------------
// Roles
// ---------------------------------------------------------------------------

// Role defines the permission level of a user.
type Role string

const (
	// RoleAdmin is the platform administrator.
	// Manages users, views all tenants, system config.
	// Also manages their own broker/LLM connections, analyses, trades, journal.
	RoleAdmin Role = "admin"

	// RoleEtradie is a regular user.
	// Creates account, manages their own broker/LLM connections,
	// views their own analyses, trades, journal.
	RoleEtradie Role = "etradie"
)

// ValidRoles is the set of allowed role values.
var ValidRoles = map[Role]bool{
	RoleAdmin:   true,
	RoleEtradie: true,
}

// IsValid checks whether the role is a recognised value.
func (r Role) IsValid() bool {
	return ValidRoles[r]
}

// String returns the role as a lowercase string.
func (r Role) String() string {
	return string(r)
}

// ParseRole normalises and validates a role string.
func ParseRole(s string) (Role, error) {
	r := Role(strings.ToLower(strings.TrimSpace(s)))
	if !r.IsValid() {
		return "", fmt.Errorf("invalid role %q: must be one of admin, etradie", s)
	}
	return r, nil
}

// ---------------------------------------------------------------------------
// User
// ---------------------------------------------------------------------------

// User represents a registered platform user stored in PostgreSQL.
//
// AuthProvider identifies how the account was created and authenticates:
//   - "local": traditional username/password (bcrypt hash in PasswordHash).
//   - "google": federated identity via Google OAuth 2.0. Local password
//     login is disabled for these accounts; PasswordHash is empty and
//     CheckPassword always returns an error so a leaked password reset
//     against a Google-only account cannot create a local credential.
//
// AvatarURL is an optional profile picture URL supplied by the identity
// provider. EmailVerified mirrors the provider's verification claim and
// is required to be true for any account created via Google.
type User struct {
	ID             string     `json:"id"`
	Username       string     `json:"username"`
	Email          string     `json:"email"`
	PasswordHash   string     `json:"-"` // never serialised to JSON
	Role           Role       `json:"role"`
	Tier           string     `json:"tier"`
	Status         string     `json:"status"`
	Active         bool       `json:"active"`
	AuthProvider   string     `json:"auth_provider"`
	AvatarURL      string     `json:"avatar_url,omitempty"`
	EmailVerified  bool       `json:"email_verified"`
	CreatedAt      time.Time  `json:"created_at"`
	UpdatedAt      time.Time  `json:"updated_at"`
	LastLoginAt    *time.Time `json:"last_login_at,omitempty"`
}

// Auth provider identifiers persisted in auth_users.auth_provider.
const (
	AuthProviderLocal  = "local"
	AuthProviderGoogle = "google"
)

// Password length policy. Bcrypt accepts at most 72 bytes; bytes past
// 72 are silently truncated so we refuse them up front. The minimum is
// the lower bound used historically by SetPassword. Exported so the
// public GET /auth/password/policy endpoint and the SPA's reset form
// can mirror the same numbers without copy-pasting magic constants.
const (
	PasswordMinLength = 8
	PasswordMaxLength = 72
)

// SetPassword hashes the plaintext password with bcrypt (cost 12)
// and stores the result in PasswordHash.
func (u *User) SetPassword(plaintext string) error {
	if len(plaintext) < PasswordMinLength {
		return fmt.Errorf("password must be at least %d characters", PasswordMinLength)
	}
	if len(plaintext) > PasswordMaxLength {
		return fmt.Errorf("password must be at most %d characters", PasswordMaxLength)
	}
	hash, err := bcrypt.GenerateFromPassword([]byte(plaintext), 12)
	if err != nil {
		return fmt.Errorf("hash password: %w", err)
	}
	u.PasswordHash = string(hash)
	return nil
}

// CheckPassword compares a plaintext password against the stored hash.
// Returns nil on match, error otherwise.
//
// For accounts whose AuthProvider is not "local" (e.g. "google"),
// password login is disabled by design: PasswordHash is empty and
// any password compare is rejected. This prevents an attacker who
// knows a federated user's email from attempting password guesses.
func (u *User) CheckPassword(plaintext string) error {
	if u.AuthProvider != "" && u.AuthProvider != AuthProviderLocal {
		return fmt.Errorf("password login is disabled for %s accounts", u.AuthProvider)
	}
	if u.PasswordHash == "" {
		return fmt.Errorf("password login is not configured for this account")
	}
	return bcrypt.CompareHashAndPassword([]byte(u.PasswordHash), []byte(plaintext))
}

// IsAdmin returns true if the user has the admin role.
func (u *User) IsAdmin() bool {
	return u.Role == RoleAdmin
}

// ---------------------------------------------------------------------------
// Token Pair (OAuth 2.0 access + refresh)
// ---------------------------------------------------------------------------

// TokenPair holds the access and refresh tokens returned on login
// and token refresh.
type TokenPair struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	TokenType    string `json:"token_type"` // always "Bearer"
	ExpiresIn    int    `json:"expires_in"` // access token TTL in seconds
}

// ---------------------------------------------------------------------------
// JWT Claims
// ---------------------------------------------------------------------------

// Claims is the JWT payload embedded in every access token.
// Kept minimal to reduce token size.
type Claims struct {
	UserID   string `json:"sub"`
	Username string `json:"username"`
	Role     Role   `json:"role"`
	Tier     string `json:"tier"`
	Status   string `json:"status"`
	IssuedAt int64  `json:"iat"`
	Expiry   int64  `json:"exp"`
}

// IsExpired checks whether the token has passed its expiry time.
func (c *Claims) IsExpired() bool {
	return time.Now().UTC().Unix() > c.Expiry
}

// ---------------------------------------------------------------------------
// Refresh Session
// ---------------------------------------------------------------------------

// Session tracks a refresh token in the database so it can be
// revoked individually or as part of a full logout.
type Session struct {
	ID           string    `json:"id"`
	UserID       string    `json:"user_id"`
	RefreshToken string    `json:"-"` // hashed, never exposed
	UserAgent    string    `json:"user_agent,omitempty"`
	ClientIP     string    `json:"client_ip,omitempty"`
	ExpiresAt    time.Time `json:"expires_at"`
	CreatedAt    time.Time `json:"created_at"`
	Revoked      bool      `json:"revoked"`
}

// IsExpired checks whether the session has passed its expiry time.
func (s *Session) IsExpired() bool {
	return time.Now().UTC().After(s.ExpiresAt)
}

// IsUsable returns true if the session is neither revoked nor expired.
func (s *Session) IsUsable() bool {
	return !s.Revoked && !s.IsExpired()
}

// ---------------------------------------------------------------------------
// ID generation helper
// ---------------------------------------------------------------------------

// GenerateID produces a 16-byte (32 hex char) random identifier.
func GenerateID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

// GenerateRefreshToken produces a 32-byte (64 hex char) random token.
func GenerateRefreshToken() string {
	b := make([]byte, 32)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
