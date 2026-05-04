package auth

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"time"
)

// OAuth provider identifiers persisted in auth_oauth_identities.provider.
const (
	OAuthProviderGoogle = "google"
)

// OAuthFlow is the server-side record created at the authorize step
// and consumed at the callback step. It binds the browser's redirect
// to the gateway-issued state, PKCE verifier, and OIDC nonce.
type OAuthFlow struct {
	FlowID       string
	Provider     string
	State        string
	CodeVerifier string
	Nonce        string
	RedirectURI  string
	ReturnTo     string
	CreatedAt    time.Time
	ExpiresAt    time.Time
	Consumed     bool
}

// IsUsable reports whether a flow record can still be consumed.
func (f *OAuthFlow) IsUsable(now time.Time) bool {
	return !f.Consumed && now.Before(f.ExpiresAt)
}

// OAuthIdentity is the persistent link between a platform User and an
// external identity provider account. The (Provider, ProviderSubject)
// pair is unique and is what the callback handler keys on.
type OAuthIdentity struct {
	ID              string
	UserID          string
	Provider        string
	ProviderSubject string
	Email           string
	EmailVerified   bool
	Name            string
	Picture         string
	HostedDomain    string
	CreatedAt       time.Time
	UpdatedAt       time.Time
	LastLoginAt     *time.Time
}

// OAuthClaims is the verified subset of an ID token that callers act on.
// Only fields we explicitly trust after JWKS verification end up here.
type OAuthClaims struct {
	Subject       string
	Email         string
	EmailVerified bool
	Name          string
	Picture       string
	HostedDomain  string
	Issuer        string
	Audience      string
	IssuedAt      time.Time
	Expiry        time.Time
}

// GenerateOAuthSecret produces a URL-safe random string with at least
// 256 bits of entropy. Used for state, nonce, flow_id, and the PKCE
// code verifier (which RFC 7636 requires to be 43..128 unreserved
// chars; 32 random bytes base64url-encoded yields 43 chars).
func GenerateOAuthSecret() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", fmt.Errorf("oauth: read random bytes: %w", err)
	}
	return base64.RawURLEncoding.EncodeToString(b), nil
}

// PKCEChallengeS256 derives the S256 code_challenge for a verifier
// per RFC 7636 §4.2: BASE64URL(SHA256(ASCII(verifier))).
func PKCEChallengeS256(verifier string) string {
	sum := sha256.Sum256([]byte(verifier))
	return base64.RawURLEncoding.EncodeToString(sum[:])
}
