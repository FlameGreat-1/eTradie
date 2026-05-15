package auth

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

// ---------------------------------------------------------------------------
// Context keys
// ---------------------------------------------------------------------------

type contextKey string

const (
	claimsKey   contextKey = "auth_claims"
	rawTokenKey contextKey = "auth_raw_token"
)

// ClaimsFromContext extracts the JWT claims from the request context.
// Returns nil if no claims are present (unauthenticated request).
func ClaimsFromContext(ctx context.Context) *Claims {
	c, _ := ctx.Value(claimsKey).(*Claims)
	return c
}

// RawTokenFromContext extracts the raw JWT token string from the context.
// Used by EngineHTTPClient to forward the token to the Python engine.
func RawTokenFromContext(ctx context.Context) string {
	s, _ := ctx.Value(rawTokenKey).(string)
	return s
}

// InjectTokenIntoContext creates a new context with the given raw JWT
// token stored under the auth package's context key. Used by background
// goroutines (e.g., Execution watcher) that need to make authenticated
// downstream calls but don't have the original request context.
func InjectTokenIntoContext(ctx context.Context, rawToken string) context.Context {
	if rawToken == "" {
		return ctx
	}
	return context.WithValue(ctx, rawTokenKey, rawToken)
}

// InjectClaimsIntoContext creates a new context with parsed *Claims
// stored under the auth package's context key. Symmetric with
// InjectTokenIntoContext; used by background goroutines that need
// downstream context readers (UserIDFromContext, RoleFromContext,
// ClaimsFromContext) to resolve the identity exactly as they would
// for a request-derived context.
//
// A nil claims argument is a no-op (returns ctx unchanged) so
// callers do not have to branch on the claim-issuance result.
func InjectClaimsIntoContext(ctx context.Context, claims *Claims) context.Context {
	if claims == nil {
		return ctx
	}
	return context.WithValue(ctx, claimsKey, claims)
}

// InjectIdentity is a convenience wrapper around InjectClaimsIntoContext
// for background workers that already know the user fields (because they
// just minted a service token for that user). It builds a minimal
// *Claims and injects it. The userID argument is mandatory; empty
// userID is a no-op so callers don't have to branch on missing data.
//
// This is the canonical helper for any goroutine that:
//   - did not come through RequireAuth middleware, and
//   - needs downstream code (e.g. the engine internal-auth bridge) to
//     resolve who it's acting for via auth.UserIDFromContext(ctx).
//
// Identity flows top-down from the trust boundary; this helper just
// repackages an identity the caller ALREADY has into the shape that
// the rest of the codebase reads from context.
func InjectIdentity(
	ctx context.Context,
	userID, username string,
	role Role,
	tier, status string,
) context.Context {
	if strings.TrimSpace(userID) == "" {
		return ctx
	}
	return InjectClaimsIntoContext(ctx, &Claims{
		UserID:   userID,
		Username: username,
		Role:     role,
		Tier:     tier,
		Status:   status,
	})
}

// UserIDFromContext extracts the user ID from the request context.
// Returns empty string if not authenticated.
func UserIDFromContext(ctx context.Context) string {
	c := ClaimsFromContext(ctx)
	if c == nil {
		return ""
	}
	return c.UserID
}

// RoleFromContext extracts the user role from the request context.
func RoleFromContext(ctx context.Context) Role {
	c := ClaimsFromContext(ctx)
	if c == nil {
		return ""
	}
	return c.Role
}

// IsAdminContext returns true if the authenticated user is an admin.
func IsAdminContext(ctx context.Context) bool {
	return RoleFromContext(ctx) == RoleAdmin
}

// ---------------------------------------------------------------------------
// HTTP Middleware
// ---------------------------------------------------------------------------

// RequireAuth returns HTTP middleware that rejects unauthenticated requests.
// On success, the Claims are injected into the request context.
//
// Both classic Bearer-in-Authorization-header requests and WebSocket
// upgrade requests carrying the token in the Sec-WebSocket-Protocol
// header are accepted. The WS path exists because browsers do not
// allow setting arbitrary HTTP headers on a WebSocket connection;
// the only browser-safe authentication channel for new WebSocket()
// is the subprotocol list. See `extractWebSocketToken` below.
func RequireAuth(ts *TokenService) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			claims, rawToken, err := extractAndVerifyHTTP(r, ts)
			if err != nil {
				writeAuthError(w, http.StatusUnauthorized, "unauthorized: "+err.Error())
				return
			}

			ctx := context.WithValue(r.Context(), claimsKey, claims)
			ctx = context.WithValue(ctx, rawTokenKey, rawToken)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// RequireAdmin returns HTTP middleware that rejects non-admin users.
// Must be chained after RequireAuth.
func RequireAdmin(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		claims := ClaimsFromContext(r.Context())
		if claims == nil {
			writeAuthError(w, http.StatusUnauthorized, "unauthorized: no claims in context")
			return
		}
		if claims.Role != RoleAdmin {
			writeAuthError(w, http.StatusForbidden, "forbidden: admin access required")
			return
		}
		next.ServeHTTP(w, r)
	})
}

// OptionalAuth returns HTTP middleware that sets claims in context if
// a valid token is present, but does NOT reject unauthenticated requests.
// Useful for endpoints that behave differently for authenticated users.
// Both claims and raw token are stored (consistent with RequireAuth)
// so downstream calls to RawTokenFromContext work correctly.
func OptionalAuth(ts *TokenService) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			claims, rawToken, err := extractAndVerifyHTTP(r, ts)
			if err == nil && claims != nil {
				ctx := context.WithValue(r.Context(), claimsKey, claims)
				ctx = context.WithValue(ctx, rawTokenKey, rawToken)
				next.ServeHTTP(w, r.WithContext(ctx))
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

// RequireAuthFunc is a convenience wrapper for http.HandlerFunc.
func RequireAuthFunc(ts *TokenService, handler http.HandlerFunc) http.Handler {
	return RequireAuth(ts)(http.HandlerFunc(handler))
}

// RequireAdminFunc is a convenience wrapper that chains RequireAuth + RequireAdmin.
func RequireAdminFunc(ts *TokenService, handler http.HandlerFunc) http.Handler {
	return RequireAuth(ts)(RequireAdmin(http.HandlerFunc(handler)))
}

// ---------------------------------------------------------------------------
// gRPC Interceptor
// ---------------------------------------------------------------------------

// UnaryAuthInterceptor returns a gRPC unary server interceptor that
// extracts the Bearer token from the "authorization" metadata key,
// verifies it, and injects Claims into the context.
//
// skipMethods is a set of full gRPC method names that should bypass
// authentication (e.g., health checks).
func UnaryAuthInterceptor(ts *TokenService, skipMethods map[string]bool) grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req interface{},
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (interface{}, error) {
		if skipMethods != nil && skipMethods[info.FullMethod] {
			return handler(ctx, req)
		}

		md, ok := metadata.FromIncomingContext(ctx)
		if !ok {
			return nil, status.Errorf(codes.Unauthenticated, "missing metadata")
		}

		vals := md.Get("authorization")
		if len(vals) == 0 {
			return nil, status.Errorf(codes.Unauthenticated, "missing authorization header")
		}

		tokenString := extractBearerToken(vals[0])
		if tokenString == "" {
			return nil, status.Errorf(codes.Unauthenticated, "invalid authorization format")
		}

		claims, err := ts.VerifyAccessToken(tokenString)
		if err != nil {
			return nil, status.Errorf(codes.Unauthenticated, "invalid token: %v", err)
		}

		newCtx := context.WithValue(ctx, claimsKey, claims)
		newCtx = context.WithValue(newCtx, rawTokenKey, tokenString)
		return handler(newCtx, req)
	}
}

// UnaryAdminInterceptor returns a gRPC unary server interceptor that
// requires the authenticated user to have the admin role.
func UnaryAdminInterceptor() grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req interface{},
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (interface{}, error) {
		claims := ClaimsFromContext(ctx)
		if claims == nil {
			return nil, status.Errorf(codes.Unauthenticated, "no claims in context")
		}
		if claims.Role != RoleAdmin {
			return nil, status.Errorf(codes.PermissionDenied, "admin access required")
		}
		return handler(ctx, req)
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// extractAndVerifyHTTP returns the validated claims and the raw token
// string for the request. It tries, in order:
//
//  1. the standard `Authorization: Bearer <token>` HTTP header
//     (server-to-server and CLI tooling);
//  2. for WebSocket upgrade requests, the `Sec-WebSocket-Protocol`
//     header in the form `Bearer, <token>` (non-browser WS clients
//     that explicitly hold a token);
//  3. the `access_token` cookie set by the cookie-auth migration
//     (see src/auth/cookies.go). This branch is tried for BOTH
//     non-WS HTTP requests AND WebSocket upgrade requests: a
//     cookie-auth browser cannot read its HttpOnly access cookie
//     to copy it into Sec-WebSocket-Protocol, so the only browser-
//     safe WS auth channel is the cookie itself. The browser
//     attaches the cookie to the WS handshake automatically.
//
// Returns errMissingAuth / errInvalidFormat / a token verification
// error when none of the channels yields a valid token. A non-empty
// channel with an invalid token is reported as an auth failure (not
// a fallthrough to the next channel) so an expired cookie cannot
// silently be treated as "unauthenticated".
func extractAndVerifyHTTP(r *http.Request, ts *TokenService) (*Claims, string, error) {
	// 1. Authorization header.
	if authHeader := r.Header.Get("Authorization"); authHeader != "" {
		tokenString := extractBearerToken(authHeader)
		if tokenString == "" {
			return nil, "", errInvalidFormat
		}
		claims, err := ts.VerifyAccessToken(tokenString)
		if err != nil {
			return nil, "", err
		}
		return claims, tokenString, nil
	}

	// 2. WebSocket subprotocol channel. Non-browser WS clients (CLI
	// tooling, server-to-server tests) still use this path. A
	// non-empty subprotocol token is authoritative: if it is
	// invalid we surface the verification error rather than
	// silently falling through to the cookie, because a deliberate
	// subprotocol declaration with a bad value is a bug, not an
	// unauthenticated request.
	if isWebSocketUpgrade(r) {
		if tokenString := extractWebSocketToken(r); tokenString != "" {
			claims, err := ts.VerifyAccessToken(tokenString)
			if err != nil {
				return nil, "", err
			}
			return claims, tokenString, nil
		}
		// No subprotocol token — fall through to the cookie branch
		// below. Browsers cannot read HttpOnly cookies from JS so
		// they cannot put the token into the subprotocol channel;
		// the cookie attached automatically by the browser to the
		// WS handshake is the only browser-safe WS auth signal.
	}

	// 3. access_token cookie. Centralised in cookies.go.
	// AccessTokenFromCookie returns "" when the cookie is absent
	// so this branch is a no-op for non-browser clients that
	// already declared no Authorization header and no subprotocol
	// token.
	if tokenString := AccessTokenFromCookie(r); tokenString != "" {
		claims, err := ts.VerifyAccessToken(tokenString)
		if err != nil {
			return nil, "", err
		}
		return claims, tokenString, nil
	}

	return nil, "", errMissingAuth
}

// isWebSocketUpgrade reports whether the request is a WebSocket
// handshake. Per RFC 6455 the HTTP request must carry
// `Connection: Upgrade` and `Upgrade: websocket`. Header values are
// case-insensitive and `Connection` may contain a comma-separated list.
func isWebSocketUpgrade(r *http.Request) bool {
	if !strings.EqualFold(r.Header.Get("Upgrade"), "websocket") {
		return false
	}
	for _, v := range strings.Split(r.Header.Get("Connection"), ",") {
		if strings.EqualFold(strings.TrimSpace(v), "upgrade") {
			return true
		}
	}
	return false
}

// extractWebSocketToken parses the Sec-WebSocket-Protocol header used
// by browser WebSocket clients to smuggle a Bearer token through the
// handshake. The agreed format is:
//
//     Sec-WebSocket-Protocol: Bearer, <jwt>
//
// Multiple Sec-WebSocket-Protocol header lines are also supported
// (RFC 6455 §4.1). The function returns the first token after the
// "Bearer" marker, or "" if none is present / malformed.
func extractWebSocketToken(r *http.Request) string {
	headers := r.Header.Values("Sec-WebSocket-Protocol")
	if len(headers) == 0 {
		return ""
	}

	// Flatten all values from all header lines into a single ordered
	// list of trimmed protocol items.
	items := make([]string, 0, 4)
	for _, line := range headers {
		for _, part := range strings.Split(line, ",") {
			if p := strings.TrimSpace(part); p != "" {
				items = append(items, p)
			}
		}
	}

	// Find the Bearer marker and return the next non-empty item.
	for i, item := range items {
		if strings.EqualFold(item, "Bearer") {
			if i+1 < len(items) {
				return items[i+1]
			}
			return ""
		}
	}

	return ""
}

// extractBearerToken strips the "Bearer " prefix from an auth header value.
func extractBearerToken(header string) string {
	const prefix = "Bearer "
	if len(header) > len(prefix) && strings.EqualFold(header[:len(prefix)], prefix) {
		return strings.TrimSpace(header[len(prefix):])
	}
	return ""
}

var (
	errMissingAuth   = &authError{"missing Authorization header"}
	errInvalidFormat = &authError{"invalid Authorization format, expected: Bearer <token>"}
)

type authError struct {
	msg string
}

func (e *authError) Error() string {
	return e.msg
}

func writeAuthError(w http.ResponseWriter, statusCode int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": message})
}
