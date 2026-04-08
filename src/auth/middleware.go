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
func RequireAuth(ts *TokenService) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			claims, err := extractAndVerifyHTTP(r, ts)
			if err != nil {
				writeAuthError(w, http.StatusUnauthorized, "unauthorized: "+err.Error())
				return
			}

			// Store both parsed claims and raw token in context.
			// Raw token is forwarded to Python engine by EngineHTTPClient.
			rawToken := extractBearerToken(r.Header.Get("Authorization"))
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
			claims, _ := extractAndVerifyHTTP(r, ts)
			if claims != nil {
				rawToken := extractBearerToken(r.Header.Get("Authorization"))
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
		// Skip auth for whitelisted methods.
		if skipMethods != nil && skipMethods[info.FullMethod] {
			return handler(ctx, req)
		}

		// Extract token from gRPC metadata.
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

		// Inject both claims and raw token into context.
		newCtx := context.WithValue(ctx, claimsKey, claims)
		newCtx = context.WithValue(newCtx, rawTokenKey, tokenString)
		return handler(newCtx, req)
	}
}

// UnaryAdminInterceptor returns a gRPC unary server interceptor that
// requires the authenticated user to have the admin role.
// Must be chained after UnaryAuthInterceptor.
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

// extractAndVerifyHTTP extracts the Bearer token from the HTTP
// Authorization header and verifies it.
func extractAndVerifyHTTP(r *http.Request, ts *TokenService) (*Claims, error) {
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		return nil, errMissingAuth
	}

	tokenString := extractBearerToken(authHeader)
	if tokenString == "" {
		return nil, errInvalidFormat
	}

	return ts.VerifyAccessToken(tokenString)
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
	errMissingAuth  = &authError{"missing Authorization header"}
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
