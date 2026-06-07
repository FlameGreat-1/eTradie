package auth

import (
	"context"
	"errors"
	"testing"
)

// fakeEpochResolver is an in-memory EpochResolver for tests.
type fakeEpochResolver struct {
	epoch int
	err   error
}

func (f fakeEpochResolver) GetTokenEpoch(_ context.Context, _ string) (int, error) {
	return f.epoch, f.err
}

func testTokenConfig() *Config {
	return &Config{
		JWTSecret:              "this-is-a-test-secret-of-sufficient-length-0123456789",
		AccessTokenTTLSeconds:  900,
		RefreshTokenTTLSeconds: 604800,
		ServiceTokenTTLSeconds: 2592000,
		Issuer:                 "etradie",
	}
}

func testUser() *User {
	return &User{
		ID:         "u1",
		Username:   "alice",
		Role:       RoleEtradie,
		Tier:       "free",
		Status:     "active",
		TokenEpoch: 3,
	}
}

func TestServiceToken_EpochAllowsCurrentRejectsStale(t *testing.T) {
	ts := NewTokenService(testTokenConfig()).WithEpochResolver(fakeEpochResolver{epoch: 3})
	u := testUser()

	tok, err := ts.IssueServiceToken(u.ID, u.Username, u.Role, u.Tier, u.Status, u.TokenEpoch)
	if err != nil {
		t.Fatalf("IssueServiceToken: %v", err)
	}
	claims, err := ts.VerifyAccessToken(tok)
	if err != nil {
		t.Fatalf("service token with current epoch should verify: %v", err)
	}
	if !claims.IsServiceToken() {
		t.Fatalf("expected token_type svc")
	}

	// Bump the user's epoch beyond the token: revoked.
	ts2 := NewTokenService(testTokenConfig()).WithEpochResolver(fakeEpochResolver{epoch: 4})
	if _, err := ts2.VerifyAccessToken(tok); err == nil {
		t.Fatalf("stale-epoch service token must be rejected (revocation)")
	}
}

func TestServiceToken_FailClosedOnResolverError(t *testing.T) {
	ts := NewTokenService(testTokenConfig()).WithEpochResolver(fakeEpochResolver{epoch: 3})
	u := testUser()
	tok, _ := ts.IssueServiceToken(u.ID, u.Username, u.Role, u.Tier, u.Status, u.TokenEpoch)

	boom := NewTokenService(testTokenConfig()).WithEpochResolver(fakeEpochResolver{err: errors.New("db down")})
	if _, err := boom.VerifyAccessToken(tok); err == nil {
		t.Fatalf("resolver error must FAIL CLOSED for a service token")
	}
}

func TestServiceToken_RejectsUnknownUser(t *testing.T) {
	ts := NewTokenService(testTokenConfig()).WithEpochResolver(fakeEpochResolver{epoch: 3})
	u := testUser()
	tok, _ := ts.IssueServiceToken(u.ID, u.Username, u.Role, u.Tier, u.Status, u.TokenEpoch)

	gone := NewTokenService(testTokenConfig()).WithEpochResolver(fakeEpochResolver{epoch: 0})
	if _, err := gone.VerifyAccessToken(tok); err == nil {
		t.Fatalf("epoch 0 (unknown/deleted user) must reject the service token")
	}
}

func TestAccessToken_NotEpochChecked(t *testing.T) {
	// Even with a resolver whose epoch is far ahead, a normal access
	// token is not epoch-enforced (only token_type==svc is).
	ts := NewTokenService(testTokenConfig()).WithEpochResolver(fakeEpochResolver{epoch: 999})
	u := testUser()
	pair, _, err := ts.IssueTokenPair(u)
	if err != nil {
		t.Fatalf("IssueTokenPair: %v", err)
	}
	if _, err := ts.VerifyAccessToken(pair.AccessToken); err != nil {
		t.Fatalf("access token must verify regardless of epoch resolver: %v", err)
	}
}

func TestServiceToken_NoResolverSkipsEpochCheck(t *testing.T) {
	// Gateway posture: no resolver attached -> service token is not
	// epoch-checked (and access tokens stay stateless).
	ts := NewTokenService(testTokenConfig())
	u := testUser()
	tok, _ := ts.IssueServiceToken(u.ID, u.Username, u.Role, u.Tier, u.Status, u.TokenEpoch)
	if _, err := ts.VerifyAccessToken(tok); err != nil {
		t.Fatalf("with no resolver the service token should verify: %v", err)
	}
}

func TestVerify_RejectsWrongIssuer(t *testing.T) {
	issuer := NewTokenService(testTokenConfig())
	u := testUser()
	pair, _, _ := issuer.IssueTokenPair(u)

	other := testTokenConfig()
	other.Issuer = "someone-else"
	verifier := NewTokenService(other)
	if _, err := verifier.VerifyAccessToken(pair.AccessToken); err == nil {
		t.Fatalf("token with mismatched issuer must be rejected")
	}
}

func TestVerify_RejectsWrongAudience(t *testing.T) {
	issCfg := testTokenConfig()
	issCfg.Audience = "etradie-api"
	issuer := NewTokenService(issCfg)
	u := testUser()
	pair, _, _ := issuer.IssueTokenPair(u)

	other := testTokenConfig()
	other.Audience = "some-other-audience"
	verifier := NewTokenService(other)
	if _, err := verifier.VerifyAccessToken(pair.AccessToken); err == nil {
		t.Fatalf("token with mismatched audience must be rejected")
	}
}

func TestVerify_AcceptsMatchingAudience(t *testing.T) {
	cfg := testTokenConfig()
	cfg.Audience = "etradie-api"
	ts := NewTokenService(cfg)
	u := testUser()
	pair, _, _ := ts.IssueTokenPair(u)
	claims, err := ts.VerifyAccessToken(pair.AccessToken)
	if err != nil {
		t.Fatalf("token with matching audience must verify: %v", err)
	}
	if claims.Audience != "etradie-api" {
		t.Fatalf("expected aud=etradie-api, got %q", claims.Audience)
	}
}

func TestVerify_AudienceTolerantWindow(t *testing.T) {
	// A token minted with NO aud (pre-rollout) must still verify while
	// RequireAudience is false, but must be rejected once it is true.
	cfg := testTokenConfig()
	cfg.Audience = "etradie-api"
	cfg.RequireAudience = false

	// Mint a token WITHOUT aud by issuing from a service whose Audience
	// is empty (simulating a pre-rollout token).
	noAudCfg := testTokenConfig()
	noAudCfg.Audience = ""
	noAudIssuer := NewTokenService(noAudCfg)
	u := testUser()
	pair, _, _ := noAudIssuer.IssueTokenPair(u)

	tolerant := NewTokenService(cfg)
	if _, err := tolerant.VerifyAccessToken(pair.AccessToken); err != nil {
		t.Fatalf("tolerant window must accept a token with no aud: %v", err)
	}

	strictCfg := testTokenConfig()
	strictCfg.Audience = "etradie-api"
	strictCfg.RequireAudience = true
	strict := NewTokenService(strictCfg)
	if _, err := strict.VerifyAccessToken(pair.AccessToken); err == nil {
		t.Fatalf("with RequireAudience=true a token without aud must be rejected")
	}
}
