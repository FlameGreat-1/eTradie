package auth

import (
	"context"
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"math/big"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/sync/singleflight"
)

// ---------------------------------------------------------------------------
// Google OAuth 2.0 / OpenID Connect provider
//
// Implements:
//
//   - Authorize URL construction (Authorization Code + PKCE S256).
//   - Token exchange against https://oauth2.googleapis.com/token.
//   - ID-token signature verification against Google's JWKS
//     (https://www.googleapis.com/oauth2/v3/certs) with key rotation,
//     concurrency-safe caching, honouring the response Cache-Control
//     max-age, and a bounded floor/ceiling.
//   - Strict claim validation: alg=RS256, iss, aud, exp, iat, nonce,
//     email_verified=true, optional hd allow-list.
//
// ---------------------------------------------------------------------------

// Google OIDC endpoints. Pulled to constants so test doubles and
// air-gapped deployments could swap them via a future config knob.
const (
	googleAuthorizeEndpoint = "https://accounts.google.com/o/oauth2/v2/auth"
	googleTokenEndpoint     = "https://oauth2.googleapis.com/token"
	googleJWKSEndpoint      = "https://www.googleapis.com/oauth2/v3/certs"

	googleIssuerHTTPS = "https://accounts.google.com"
	googleIssuerBare  = "accounts.google.com"

	// JWKS cache bounds. We honour the Cache-Control max-age returned
	// by Google but clamp it so a misconfigured cache header cannot
	// keep a revoked key live for too long, nor force a hot loop on
	// Google's certs endpoint.
	jwksCacheMin = 5 * time.Minute
	jwksCacheMax = 24 * time.Hour
	jwksCacheDef = 1 * time.Hour

	// Small leeway to absorb clock skew between Google and the gateway.
	oidcClockSkew = 60 * time.Second
)

// GoogleOAuthProvider performs the server-side half of the
// Authorization Code + PKCE flow against Google.
//
// Concurrency: every method is safe for use by many goroutines. The
// JWKS cache is guarded internally; refreshes are coalesced through a
// singleflight.Group so that under heavy concurrent verification load
// (or right after Google rotates a key) only one goroutine hits
// Google's JWKS endpoint while the rest wait for that single result.
// This eliminates the thundering-herd risk that the audit flagged.
type GoogleOAuthProvider struct {
	clientID            string
	clientSecret        string
	redirectURI         string
	linkRedirectURI     string
	allowedHostedDomain map[string]struct{}
	http                *http.Client

	jwksMu      sync.RWMutex
	jwksKeys    map[string]*rsa.PublicKey
	jwksFetched time.Time
	jwksTTL     time.Duration
	jwksGroup   singleflight.Group
}

// NewGoogleOAuthProvider constructs a provider from validated config.
// httpTimeout caps every outbound request. Callers are expected to
// pass a Config that has already been validated by Config.validate.
func NewGoogleOAuthProvider(cfg *Config) *GoogleOAuthProvider {
	allowed := make(map[string]struct{}, len(cfg.GoogleAllowedHostedDomains))
	for _, d := range cfg.GoogleAllowedHostedDomains {
		allowed[d] = struct{}{}
	}
	return &GoogleOAuthProvider{
		clientID:            cfg.GoogleClientID,
		clientSecret:        cfg.GoogleClientSecret,
		redirectURI:         cfg.GoogleRedirectURI,
		linkRedirectURI:     cfg.GoogleLinkRedirectURI,
		allowedHostedDomain: allowed,
		http: &http.Client{
			Timeout: time.Duration(cfg.OAuthHTTPTimeoutSeconds) * time.Second,
		},
		jwksKeys: make(map[string]*rsa.PublicKey),
	}
}

// RedirectURI returns the sign-in flow's redirect URI. Used by
// handlers to record the URI in the auth_oauth_flows row so the
// callback can confirm the round-trip is consistent.
func (p *GoogleOAuthProvider) RedirectURI() string {
	return p.redirectURI
}

// LinkRedirectURI returns the link flow's redirect URI. Distinct
// from RedirectURI by design (see Config.GoogleLinkRedirectURI).
func (p *GoogleOAuthProvider) LinkRedirectURI() string {
	return p.linkRedirectURI
}

// ---------------------------------------------------------------------------
// Authorize URL
// ---------------------------------------------------------------------------

// BuildAuthorizeURL composes the URL the browser must be redirected to
// in order to start the Google consent step for the SIGN-IN flow.
// Caller supplies state, the PKCE verifier, and a nonce; this method
// derives the S256 challenge from the verifier so the verifier never
// leaves the gateway.
func (p *GoogleOAuthProvider) BuildAuthorizeURL(state, codeVerifier, nonce string) (string, error) {
	return p.buildAuthorizeURL(state, codeVerifier, nonce, p.redirectURI)
}

// BuildLinkAuthorizeURL is the link-flow counterpart of
// BuildAuthorizeURL. It pins the link redirect URI so Google sends
// the browser back to the authenticated callback path, and is
// otherwise identical.
func (p *GoogleOAuthProvider) BuildLinkAuthorizeURL(state, codeVerifier, nonce string) (string, error) {
	return p.buildAuthorizeURL(state, codeVerifier, nonce, p.linkRedirectURI)
}

func (p *GoogleOAuthProvider) buildAuthorizeURL(state, codeVerifier, nonce, redirectURI string) (string, error) {
	if state == "" || codeVerifier == "" || nonce == "" {
		return "", fmt.Errorf("google oauth: state, code_verifier, and nonce are required")
	}
	if redirectURI == "" {
		return "", fmt.Errorf("google oauth: redirect_uri is required")
	}
	q := url.Values{}
	q.Set("client_id", p.clientID)
	q.Set("redirect_uri", redirectURI)
	q.Set("response_type", "code")
	q.Set("scope", "openid email profile")
	q.Set("state", state)
	q.Set("nonce", nonce)
	q.Set("code_challenge", PKCEChallengeS256(codeVerifier))
	q.Set("code_challenge_method", "S256")
	q.Set("access_type", "online")
	q.Set("include_granted_scopes", "true")
	q.Set("prompt", "select_account")
	// When exactly one hosted domain is configured, hint Google to
	// scope the chooser to that domain. The hd claim is still
	// re-verified server-side after token exchange.
	if len(p.allowedHostedDomain) == 1 {
		for d := range p.allowedHostedDomain {
			q.Set("hd", d)
		}
	}
	return googleAuthorizeEndpoint + "?" + q.Encode(), nil
}

// ---------------------------------------------------------------------------
// Token exchange + ID-token verification
// ---------------------------------------------------------------------------

// googleTokenResponse mirrors the JSON returned by /token. We only
// consume id_token; access_token / refresh_token are intentionally
// discarded because we do not call Google APIs on the user's behalf.
type googleTokenResponse struct {
	IDToken          string `json:"id_token"`
	AccessToken      string `json:"access_token"`
	ExpiresIn        int    `json:"expires_in"`
	TokenType        string `json:"token_type"`
	Scope            string `json:"scope"`
	Error            string `json:"error"`
	ErrorDescription string `json:"error_description"`
}

// ExchangeCodeAndVerify performs the full backend half of the flow:
// exchanges the authorization code for an id_token, verifies it
// against Google's JWKS, and returns the trusted claims.
//
// redirectURI MUST be the same URI that was sent to Google's
// /authorize endpoint at the start of the flow; Google's /token
// endpoint compares the two byte-for-byte and refuses the exchange
// otherwise. Callers supply the URI explicitly (rather than the
// provider picking it) so the link path and the sign-in path cannot
// accidentally use each other's URI.
//
// expectedNonce is the nonce that was sent to Google during the
// authorize step; the ID token's nonce claim must match it exactly.
func (p *GoogleOAuthProvider) ExchangeCodeAndVerify(
	ctx context.Context,
	code string,
	codeVerifier string,
	expectedNonce string,
	redirectURI string,
) (*OAuthClaims, error) {
	if code == "" || codeVerifier == "" || expectedNonce == "" {
		return nil, fmt.Errorf("google oauth: code, code_verifier, and expected nonce are required")
	}
	if redirectURI == "" {
		return nil, fmt.Errorf("google oauth: redirect_uri is required")
	}

	form := url.Values{}
	form.Set("grant_type", "authorization_code")
	form.Set("code", code)
	form.Set("client_id", p.clientID)
	form.Set("client_secret", p.clientSecret)
	form.Set("redirect_uri", redirectURI)
	form.Set("code_verifier", codeVerifier)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, googleTokenEndpoint,
		strings.NewReader(form.Encode()))
	if err != nil {
		return nil, fmt.Errorf("google oauth: build token request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("Accept", "application/json")

	resp, err := p.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("google oauth: token request transport: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return nil, fmt.Errorf("google oauth: read token response: %w", err)
	}

	var tok googleTokenResponse
	if err := json.Unmarshal(body, &tok); err != nil {
		return nil, fmt.Errorf("google oauth: decode token response: %w", err)
	}
	if resp.StatusCode != http.StatusOK || tok.Error != "" {
		return nil, fmt.Errorf("google oauth: token exchange failed: status=%d error=%s description=%s",
			resp.StatusCode, tok.Error, tok.ErrorDescription)
	}
	if tok.IDToken == "" {
		return nil, fmt.Errorf("google oauth: token response missing id_token")
	}

	claims, err := p.VerifyIDToken(ctx, tok.IDToken, expectedNonce)
	if err != nil {
		return nil, err
	}

	if len(p.allowedHostedDomain) > 0 {
		if _, ok := p.allowedHostedDomain[strings.ToLower(claims.HostedDomain)]; !ok {
			return nil, fmt.Errorf("google oauth: hosted domain %q is not permitted", claims.HostedDomain)
		}
	}

	return claims, nil
}

// VerifyIDToken parses and validates an ID token, returning the
// trusted claims. Public so callers (and tests) can verify a token
// independently from the token-exchange path.
func (p *GoogleOAuthProvider) VerifyIDToken(ctx context.Context, idToken, expectedNonce string) (*OAuthClaims, error) {
	parser := jwt.NewParser(
		jwt.WithValidMethods([]string{"RS256"}),
		jwt.WithIssuedAt(),
		jwt.WithLeeway(oidcClockSkew),
	)

	parsed, err := parser.Parse(idToken, func(t *jwt.Token) (interface{}, error) {
		kid, _ := t.Header["kid"].(string)
		if kid == "" {
			return nil, fmt.Errorf("id token missing kid header")
		}
		return p.publicKeyForKID(ctx, kid)
	})
	if err != nil {
		return nil, fmt.Errorf("google oauth: verify id token: %w", err)
	}
	if !parsed.Valid {
		return nil, fmt.Errorf("google oauth: id token is invalid")
	}

	mc, ok := parsed.Claims.(jwt.MapClaims)
	if !ok {
		return nil, fmt.Errorf("google oauth: id token claims have unexpected type")
	}

	iss, _ := mc["iss"].(string)
	if iss != googleIssuerHTTPS && iss != googleIssuerBare {
		return nil, fmt.Errorf("google oauth: id token issuer %q is not Google", iss)
	}

	// `aud` may legitimately be a string OR a JSON array of strings
	// (RFC 7519 §4.1.3, OIDC Core §3.1.3.7). Accept either form, but
	// when it's an array also require the OIDC `azp` (Authorized
	// Party) claim to equal our client_id, per OIDC §3.1.3.7
	//   "If the ID Token contains multiple audiences, the Client SHOULD
	//    verify that an azp Claim is present."
	aud, audArray, audIsArray := extractAudClaim(mc)
	if !audIsArray {
		if aud != p.clientID {
			return nil, fmt.Errorf("google oauth: id token audience does not match configured client_id")
		}
	} else {
		matched := false
		for _, a := range audArray {
			if a == p.clientID {
				matched = true
				break
			}
		}
		if !matched {
			return nil, fmt.Errorf("google oauth: id token audience array does not contain configured client_id")
		}
		azp, _ := mc["azp"].(string)
		if azp != p.clientID {
			return nil, fmt.Errorf("google oauth: id token has multiple audiences and azp does not match client_id")
		}
		aud = p.clientID
	}

	now := time.Now().UTC()
	exp, err := claimToTime(mc, "exp")
	if err != nil {
		return nil, fmt.Errorf("google oauth: id token exp: %w", err)
	}
	if now.After(exp.Add(oidcClockSkew)) {
		return nil, fmt.Errorf("google oauth: id token expired at %s", exp.Format(time.RFC3339))
	}
	iat, err := claimToTime(mc, "iat")
	if err != nil {
		return nil, fmt.Errorf("google oauth: id token iat: %w", err)
	}
	if iat.After(now.Add(oidcClockSkew)) {
		return nil, fmt.Errorf("google oauth: id token issued in the future")
	}

	nonce, _ := mc["nonce"].(string)
	if nonce == "" || nonce != expectedNonce {
		return nil, fmt.Errorf("google oauth: id token nonce mismatch")
	}

	sub, _ := mc["sub"].(string)
	if sub == "" {
		return nil, fmt.Errorf("google oauth: id token missing subject")
	}

	email, _ := mc["email"].(string)
	if email == "" {
		return nil, fmt.Errorf("google oauth: id token missing email")
	}
	emailVerified := claimAsBool(mc["email_verified"])
	if !emailVerified {
		return nil, fmt.Errorf("google oauth: email %q is not verified by Google", email)
	}

	name, _ := mc["name"].(string)
	picture, _ := mc["picture"].(string)
	hd, _ := mc["hd"].(string)

	return &OAuthClaims{
		Subject:       sub,
		Email:         strings.ToLower(strings.TrimSpace(email)),
		EmailVerified: true,
		Name:          strings.TrimSpace(name),
		Picture:       strings.TrimSpace(picture),
		HostedDomain:  strings.ToLower(strings.TrimSpace(hd)),
		Issuer:        iss,
		Audience:      aud,
		IssuedAt:      iat,
		Expiry:        exp,
	}, nil
}

// ---------------------------------------------------------------------------
// JWKS cache
// ---------------------------------------------------------------------------

type jwksKey struct {
	Kid string `json:"kid"`
	Kty string `json:"kty"`
	Alg string `json:"alg"`
	Use string `json:"use"`
	N   string `json:"n"`
	E   string `json:"e"`
}

type jwksDocument struct {
	Keys []jwksKey `json:"keys"`
}

// publicKeyForKID returns the cached RSA public key for kid, refreshing
// the JWKS document on cache miss or expiry. A second miss after a
// successful refresh is a hard error: it means Google rotated to a key
// we still can't see.
//
// Concurrent refreshes are coalesced via singleflight under the static
// key "jwks": only one HTTP call to Google's certs endpoint runs at a
// time, and any other goroutines waiting on a refresh share its result.
func (p *GoogleOAuthProvider) publicKeyForKID(ctx context.Context, kid string) (*rsa.PublicKey, error) {
	if key := p.cachedKey(kid); key != nil {
		return key, nil
	}
	if _, err, _ := p.jwksGroup.Do("jwks", func() (interface{}, error) {
		return nil, p.refreshJWKS(ctx)
	}); err != nil {
		return nil, err
	}
	if key := p.cachedKey(kid); key != nil {
		return key, nil
	}
	return nil, fmt.Errorf("google oauth: signing key %q not found in JWKS", kid)
}

func (p *GoogleOAuthProvider) cachedKey(kid string) *rsa.PublicKey {
	p.jwksMu.RLock()
	defer p.jwksMu.RUnlock()
	if p.jwksTTL > 0 && time.Since(p.jwksFetched) > p.jwksTTL {
		return nil
	}
	return p.jwksKeys[kid]
}

func (p *GoogleOAuthProvider) refreshJWKS(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, googleJWKSEndpoint, nil)
	if err != nil {
		return fmt.Errorf("google oauth: build jwks request: %w", err)
	}
	req.Header.Set("Accept", "application/json")

	resp, err := p.http.Do(req)
	if err != nil {
		return fmt.Errorf("google oauth: jwks transport: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("google oauth: jwks status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return fmt.Errorf("google oauth: read jwks: %w", err)
	}

	var doc jwksDocument
	if err := json.Unmarshal(body, &doc); err != nil {
		return fmt.Errorf("google oauth: decode jwks: %w", err)
	}

	next := make(map[string]*rsa.PublicKey, len(doc.Keys))
	for _, k := range doc.Keys {
		if k.Kty != "RSA" || k.Alg != "" && k.Alg != "RS256" {
			continue
		}
		if k.Kid == "" || k.N == "" || k.E == "" {
			continue
		}
		pub, err := jwksRSAFromNE(k.N, k.E)
		if err != nil {
			continue
		}
		next[k.Kid] = pub
	}
	if len(next) == 0 {
		return fmt.Errorf("google oauth: jwks contained no usable RSA keys")
	}

	ttl := jwksTTLFromCacheControl(resp.Header.Get("Cache-Control"))

	p.jwksMu.Lock()
	p.jwksKeys = next
	p.jwksFetched = time.Now()
	p.jwksTTL = ttl
	p.jwksMu.Unlock()
	return nil
}

// jwksRSAFromNE rebuilds an *rsa.PublicKey from the base64url-encoded
// modulus and exponent fields in a JWK.
func jwksRSAFromNE(n, e string) (*rsa.PublicKey, error) {
	nBytes, err := base64.RawURLEncoding.DecodeString(n)
	if err != nil {
		return nil, fmt.Errorf("decode n: %w", err)
	}
	eBytes, err := base64.RawURLEncoding.DecodeString(e)
	if err != nil {
		return nil, fmt.Errorf("decode e: %w", err)
	}
	if len(nBytes) == 0 || len(eBytes) == 0 {
		return nil, fmt.Errorf("empty modulus or exponent")
	}
	eInt := 0
	for _, b := range eBytes {
		eInt = eInt<<8 | int(b)
	}
	if eInt <= 0 {
		return nil, fmt.Errorf("non-positive exponent")
	}
	return &rsa.PublicKey{
		N: new(big.Int).SetBytes(nBytes),
		E: eInt,
	}, nil
}

// jwksTTLFromCacheControl extracts max-age from a Cache-Control header
// and clamps it to [jwksCacheMin, jwksCacheMax]. Falls back to the
// default TTL when the header is missing or malformed.
func jwksTTLFromCacheControl(cc string) time.Duration {
	if cc == "" {
		return jwksCacheDef
	}
	for _, part := range strings.Split(cc, ",") {
		part = strings.TrimSpace(strings.ToLower(part))
		if !strings.HasPrefix(part, "max-age=") {
			continue
		}
		n, err := strconv.Atoi(strings.TrimPrefix(part, "max-age="))
		if err != nil || n <= 0 {
			return jwksCacheDef
		}
		d := time.Duration(n) * time.Second
		if d < jwksCacheMin {
			return jwksCacheMin
		}
		if d > jwksCacheMax {
			return jwksCacheMax
		}
		return d
	}
	return jwksCacheDef
}

// ---------------------------------------------------------------------------
// Claim helpers
// ---------------------------------------------------------------------------

func claimToTime(mc jwt.MapClaims, key string) (time.Time, error) {
	switch v := mc[key].(type) {
	case float64:
		return time.Unix(int64(v), 0).UTC(), nil
	case int64:
		return time.Unix(v, 0).UTC(), nil
	case json.Number:
		n, err := v.Int64()
		if err != nil {
			return time.Time{}, fmt.Errorf("%s not an integer: %w", key, err)
		}
		return time.Unix(n, 0).UTC(), nil
	default:
		return time.Time{}, fmt.Errorf("%s missing or wrong type", key)
	}
}

func claimAsBool(v interface{}) bool {
	switch t := v.(type) {
	case bool:
		return t
	case string:
		b, err := strconv.ParseBool(t)
		return err == nil && b
	default:
		return false
	}
}

// extractAudClaim normalises the `aud` claim into either a single
// string or a slice of strings, per RFC 7519 §4.1.3. Returns:
//   - (single, nil, false) when `aud` is a string
//   - ("", arr,  true)     when `aud` is an array (possibly empty)
//   - ("", nil,  false)    when `aud` is missing or has an unexpected
//                          type — callers treat this as a mismatch
func extractAudClaim(mc jwt.MapClaims) (single string, arr []string, isArray bool) {
	switch v := mc["aud"].(type) {
	case string:
		return v, nil, false
	case []interface{}:
		out := make([]string, 0, len(v))
		for _, item := range v {
			if s, ok := item.(string); ok && s != "" {
				out = append(out, s)
			}
		}
		return "", out, true
	case []string:
		return "", append([]string(nil), v...), true
	default:
		return "", nil, false
	}
}
