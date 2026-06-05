package auth

import (
	"context"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// EpochResolver resolves a user's current token epoch. Implemented by
// auth.UserStore (GetTokenEpoch). Injected into TokenService so the
// service-token verification path can reject a token whose 'tv' claim
// is below the user's current epoch, WITHOUT the auth package taking a
// direct database dependency.
type EpochResolver interface {
	GetTokenEpoch(ctx context.Context, userID string) (int, error)
}

// TokenService handles JWT access token creation and verification,
// and refresh token generation. Stateless for access tokens;
// refresh tokens are persisted in the session store.
//
// epochResolver is optional. When set, VerifyAccessToken enforces the
// per-user token epoch on SERVICE tokens only (see WithEpochResolver).
type TokenService struct {
	cfg           *Config
	epochResolver EpochResolver
}

// NewTokenService creates a token service with the given auth config.
func NewTokenService(cfg *Config) *TokenService {
	return &TokenService{cfg: cfg}
}

// WithEpochResolver attaches an epoch resolver so service-token
// verification rejects tokens minted before the user's current epoch
// (i.e. revoked via UserStore.BumpTokenEpoch). Nil is a no-op, leaving
// service tokens un-epoch-checked -- which is the correct default for
// callers that do NOT consume service tokens (e.g. the gateway's
// user-facing HTTP verification) so they pay no per-verify DB lookup.
//
// Returns the receiver for chaining at construction.
func (ts *TokenService) WithEpochResolver(r EpochResolver) *TokenService {
	ts.epochResolver = r
	return ts
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
		"tier":     user.Tier,
		"status":   user.Status,
		"iss":      ts.cfg.Issuer,
		"iat":      now.Unix(),
		"exp":      accessExpiry.Unix(),
		"tv":       user.TokenEpoch,
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

	// Validate the issuer. Tokens are minted with iss = cfg.Issuer;
	// a token whose issuer does not match (e.g. one signed with the
	// same HMAC secret for a different purpose) is rejected. Tier 4
	// "Token issuer validation".
	if iss, ok := mapClaims["iss"].(string); !ok || iss != ts.cfg.Issuer {
		return nil, fmt.Errorf("invalid or missing 'iss' claim")
	}

	// tier is an entitlement floor, not a security gate. Defaulting a
	// missing tier to "free" is fail-SAFE (least privilege), so it is
	// permitted to default.
	if tier, ok := mapClaims["tier"].(string); ok {
		claims.Tier = tier
	} else {
		claims.Tier = "free"
	}

	// status IS a security gate (active / suspended / deactivated).
	// A token missing or carrying a non-string status is rejected
	// rather than coerced to "active" -- fail CLOSED, not open.
	if status, ok := mapClaims["status"].(string); ok && status != "" {
		claims.Status = status
	} else {
		return nil, fmt.Errorf("missing or invalid 'status' claim")
	}

	if iat, ok := mapClaims["iat"].(float64); ok {
		claims.IssuedAt = int64(iat)
	}

	if exp, ok := mapClaims["exp"].(float64); ok {
		claims.Expiry = int64(exp)
	}

	// 'tv' (token epoch / version). Best-effort parse: a token minted
	// before this claim existed parses as 0. Enforced for service
	// tokens below.
	if tv, ok := mapClaims["tv"].(float64); ok {
		claims.TokenEpoch = int(tv)
	}

	// 'token_type'. "svc" marks a long-lived service token.
	if tt, ok := mapClaims["token_type"].(string); ok {
		claims.TokenType = tt
	}

	// Double-check expiry (jwt.Parse already checks, but be explicit).
	if claims.IsExpired() {
		return nil, fmt.Errorf("token expired")
	}

	// Service-token revocation check. Only service tokens are
	// epoch-enforced, and only when a resolver is configured (the
	// services that consume service tokens -- execution + management --
	// wire UserStore as the resolver in their gRPC interceptor; the
	// gateway's user-facing path leaves it nil so access tokens never
	// pay a DB lookup).
	//
	// Fail CLOSED: a money-moving service credential must not pass when
	// its revocation state cannot be confirmed. A resolver error, or a
	// resolved epoch ahead of the token's 'tv' (bumped via
	// BumpTokenEpoch), or epoch 0 (user deleted), all reject.
	if claims.IsServiceToken() && ts.epochResolver != nil {
		current, err := ts.epochResolver.GetTokenEpoch(context.Background(), claims.UserID)
		if err != nil {
			return nil, fmt.Errorf("service token epoch check failed: %w", err)
		}
		if current == 0 {
			return nil, fmt.Errorf("service token rejected: unknown user")
		}
		if claims.TokenEpoch < current {
			return nil, fmt.Errorf("service token revoked (epoch %d < %d)", claims.TokenEpoch, current)
		}
	}

	return claims, nil
}

// IssueServiceToken creates a long-lived JWT for internal service-to-service
// authentication. Used by background operations (trade monitoring, EOD checks,
// news protection, invalidation engines) that must make authenticated broker
// calls on behalf of a user without the user being present.
//
// The token carries the same claims structure (sub, username, role, tier,
// status, iss, iat, exp) as user session tokens so downstream tier checks
// see the user's actual subscription state — not a silent "free" default.
// The "svc" token_type claim distinguishes service tokens from user session
// tokens in audit logs.
//
// Service tokens have a long TTL (default 30 days) because they back
// autonomous 24/7 operations. They are re-issued on service restart for
// each user with active trades, and replaced by fresh user session tokens
// when the user authenticates.
func (ts *TokenService) IssueServiceToken(userID, username string, role Role, tier, statusClaim string, tokenEpoch int) (string, error) {
	if userID == "" {
		return "", fmt.Errorf("issue service token: userID must not be empty")
	}
	if username == "" {
		return "", fmt.Errorf("issue service token: username must not be empty")
	}
	if !role.IsValid() {
		return "", fmt.Errorf("issue service token: invalid role %q", role)
	}
	if tier == "" {
		tier = "free"
	}
	if statusClaim == "" {
		statusClaim = "active"
	}

	now := time.Now().UTC()
	expiry := now.Add(time.Duration(ts.cfg.ServiceTokenTTLSeconds) * time.Second)

	claims := jwt.MapClaims{
		"sub":        userID,
		"username":   username,
		"role":       string(role),
		"tier":       tier,
		"status":     statusClaim,
		"iss":        ts.cfg.Issuer,
		"iat":        now.Unix(),
		"exp":        expiry.Unix(),
		"token_type": "svc",
		"tv":         tokenEpoch,
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := token.SignedString(ts.cfg.JWTSecretBytes())
	if err != nil {
		return "", fmt.Errorf("sign service token: %w", err)
	}

	return signed, nil
}

// RefreshTokenTTL returns the configured refresh token lifetime.
func (ts *TokenService) RefreshTokenTTL() time.Duration {
	return time.Duration(ts.cfg.RefreshTokenTTLSeconds) * time.Second
}

// ServiceTokenTTL returns the configured service token lifetime.
func (ts *TokenService) ServiceTokenTTL() time.Duration {
	return time.Duration(ts.cfg.ServiceTokenTTLSeconds) * time.Second
}
