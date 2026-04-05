package auth

import (
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// TokenService handles JWT access token creation and verification,
// and refresh token generation. Stateless for access tokens;
// refresh tokens are persisted in the session store.
type TokenService struct {
	cfg *Config
}

// NewTokenService creates a token service with the given auth config.
func NewTokenService(cfg *Config) *TokenService {
	return &TokenService{cfg: cfg}
}

// IssueTokenPair creates a new access + refresh token pair for the
// given user. The access token is a signed JWT; the refresh token
// is a random hex string that must be stored (hashed) in the DB.
func (ts *TokenService) IssueTokenPair(user *User) (*TokenPair, string, error) {
	now := time.Now().UTC()

	// Build JWT claims.
	accessExpiry := now.Add(time.Duration(ts.cfg.AccessTokenTTLSeconds) * time.Second)

	claims := jwt.MapClaims{
		"sub":      user.ID,
		"username": user.Username,
		"role":     string(user.Role),
		"iss":      ts.cfg.Issuer,
		"iat":      now.Unix(),
		"exp":      accessExpiry.Unix(),
	}

	// Sign the access token with HMAC-SHA256.
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	accessToken, err := token.SignedString(ts.cfg.JWTSecretBytes())
	if err != nil {
		return nil, "", fmt.Errorf("sign access token: %w", err)
	}

	// Generate a random refresh token.
	refreshToken := GenerateRefreshToken()

	pair := &TokenPair{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		TokenType:    "Bearer",
		ExpiresIn:    ts.cfg.AccessTokenTTLSeconds,
	}

	return pair, refreshToken, nil
}

// VerifyAccessToken parses and validates a JWT access token string.
// Returns the embedded claims on success, or an error if the token
// is malformed, expired, or has an invalid signature.
func (ts *TokenService) VerifyAccessToken(tokenString string) (*Claims, error) {
	parsed, err := jwt.Parse(tokenString, func(t *jwt.Token) (interface{}, error) {
		// Ensure the signing method is HMAC.
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
		}
		return ts.cfg.JWTSecretBytes(), nil
	})
	if err != nil {
		return nil, fmt.Errorf("parse token: %w", err)
	}

	mapClaims, ok := parsed.Claims.(jwt.MapClaims)
	if !ok || !parsed.Valid {
		return nil, fmt.Errorf("invalid token claims")
	}

	// Extract claims into our struct.
	claims := &Claims{}

	if sub, ok := mapClaims["sub"].(string); ok {
		claims.UserID = sub
	} else {
		return nil, fmt.Errorf("missing or invalid 'sub' claim")
	}

	if username, ok := mapClaims["username"].(string); ok {
		claims.Username = username
	} else {
		return nil, fmt.Errorf("missing or invalid 'username' claim")
	}

	if role, ok := mapClaims["role"].(string); ok {
		parsedRole, err := ParseRole(role)
		if err != nil {
			return nil, fmt.Errorf("invalid 'role' claim: %w", err)
		}
		claims.Role = parsedRole
	} else {
		return nil, fmt.Errorf("missing or invalid 'role' claim")
	}

	if iat, ok := mapClaims["iat"].(float64); ok {
		claims.IssuedAt = int64(iat)
	}

	if exp, ok := mapClaims["exp"].(float64); ok {
		claims.Expiry = int64(exp)
	}

	// Double-check expiry (jwt.Parse already checks, but be explicit).
	if claims.IsExpired() {
		return nil, fmt.Errorf("token expired")
	}

	return claims, nil
}

// RefreshTokenTTL returns the configured refresh token lifetime.
func (ts *TokenService) RefreshTokenTTL() time.Duration {
	return time.Duration(ts.cfg.RefreshTokenTTLSeconds) * time.Second
}
