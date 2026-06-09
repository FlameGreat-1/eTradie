package infra

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/rs/zerolog"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/propagation"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/pkg/resilience"
)

// injectTraceContext writes the current context's W3C trace headers
// (traceparent / tracestate) onto the outbound request so the engine's
// FastAPI instrumentation continues the SAME distributed trace instead
// of starting a disconnected root span. Uses the global propagator set
// in observability.InitTracing; a no-op when tracing is disabled or the
// context carries no recording span. Dependency-free (core otel only).
func injectTraceContext(ctx context.Context, req *http.Request) {
	otel.GetTextMapPropagator().Inject(ctx, propagation.HeaderCarrier(req.Header))
}

// internalAuthHeader is the header name the engine's verify_internal_auth
// dependency reads. Mirrors engine/shared/internal_auth.py::INTERNAL_AUTH_HEADER
// and billing/server/http.go::InternalAuthHeader.
const internalAuthHeader = "X-Internal-Auth"

// internalUserIDHeader carries the authenticated user's ID on internal
// calls so the engine can resolve the correct per-user broker connection
// without requiring a full JWT on the internal path.
const (
	internalUserIDHeader       = "X-User-Id"
	internalUserTierHeader     = "X-User-Tier"
	internalUserRoleHeader     = "X-User-Role"
	internalUserUsernameHeader = "X-User-Username"
)

// EngineHTTPClient communicates with the Python engine's internal HTTP endpoints.
type EngineHTTPClient struct {
	baseURL        string
	internalSecret string
	client         *http.Client
	log            zerolog.Logger
}

// NewEngineHTTPClient creates an HTTP client for the Python engine.
//
// internalSecret is the shared secret sent in X-Internal-Auth on every
// call to /internal/* endpoints. It must match ENGINE_INTERNAL_SHARED_SECRET
// on the engine side. Pass an empty string only in tests; production
// deployments must set GATEWAY_ENGINE_INTERNAL_SHARED_SECRET.
//
// The client intentionally has NO http.Client.Timeout. Every phase in
// the orchestrator wraps its ctx with context.WithTimeout using the
// correct phase-level budget (ProcessorTimeoutSeconds, RAGTimeoutSeconds,
// etc.), and http.NewRequestWithContext propagates that deadline all
// the way through connect, write, read, and body-close. A client-wide
// Timeout would silently override those per-call deadlines and cause
// cycles to fail with "context deadline exceeded" long before the
// phase budget is actually spent. The timeoutSeconds parameter is
// preserved for API compatibility with callers but is only used for
// the health-check path below.
func NewEngineHTTPClient(baseURL, internalSecret string, timeoutSeconds int) *EngineHTTPClient {
	log := observability.Logger("engine_http_client")

	client := &http.Client{
		// No Timeout here: see doc comment above. Per-request deadlines
		// come from the caller's context.
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 20,
			IdleConnTimeout:     90 * time.Second,
		},
	}

	log.Info().
		Str("base_url", baseURL).
		Int("health_check_timeout_seconds", timeoutSeconds).
		Msg("engine_http_client_initialized")

	return &EngineHTTPClient{
		baseURL:        baseURL,
		internalSecret: internalSecret,
		client:         client,
		log:            log,
	}
}

// isInternalPath reports whether the given URL path targets an engine
// /internal/* endpoint. These paths require X-Internal-Auth + X-User-Id
// instead of (or in addition to) the user JWT.
func isInternalPath(path string) bool {
	return strings.HasPrefix(path, "/internal/")
}

// PostJSON sends a POST request with JSON body and returns the decoded response.
func (c *EngineHTTPClient) PostJSON(ctx context.Context, path string, body interface{}) (map[string]interface{}, error) {
	url := c.baseURL + path

	jsonBody, err := json.Marshal(body)
	if err != nil {
		return nil, fmt.Errorf("engine_http: marshal request for %s: %w", path, err)
	}

	// Generate an idempotency key once per logical operation so retries use the same key.
	idempotencyKey := uuid.New().String()

	var result map[string]interface{}

	operation := func() error {
		req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(jsonBody))
		if err != nil {
			return fmt.Errorf("engine_http: create request for %s: %w", path, err)
		}
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("X-Idempotency-Key", idempotencyKey)
		injectTraceContext(ctx, req)

		if isInternalPath(path) {
			// Internal endpoints authenticate via shared secret + user ID.
			// The JWT is NOT sent on these paths: the engine's
			// verify_internal_auth dependency rejects user cookies and
			// only accepts the shared secret.
			if c.internalSecret != "" {
				req.Header.Set(internalAuthHeader, c.internalSecret)
			}
			// Forward the full authenticated identity. The engine's
			// /internal/processor/process handler reads all four to
			// construct an AuthenticatedUser for LLM connection
			// resolution (tier governs whether the platform key
			// fallback is allowed). Empty values are not sent so the
			// engine sees an absent header rather than an empty one.
			if claims := auth.ClaimsFromContext(ctx); claims != nil {
				if claims.UserID != "" {
					req.Header.Set(internalUserIDHeader, claims.UserID)
				}
				if claims.Tier != "" {
					req.Header.Set(internalUserTierHeader, claims.Tier)
				}
				if claims.Role != "" {
					req.Header.Set(internalUserRoleHeader, string(claims.Role))
				}
				if claims.Username != "" {
					req.Header.Set(internalUserUsernameHeader, claims.Username)
				}
			} else if userID := auth.UserIDFromContext(ctx); userID != "" {
				// Defensive fallback: a future caller that injects only
				// user_id (no full claims) still gets the user_id header.
				req.Header.Set(internalUserIDHeader, userID)
			}
		} else {
			// Public / dashboard endpoints: forward the JWT so the engine
			// can identify the authenticated user via get_current_user.
			if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
				req.Header.Set("Authorization", "Bearer "+rawToken)
			}
		}

		resp, err := c.client.Do(req)
		if err != nil {
			c.log.Error().
				Str("path", path).
				Err(err).
				Msg("engine_http_request_failed")
			return fmt.Errorf("engine_http: request %s: %w", path, err)
		}
		defer resp.Body.Close()

		respBody, err := io.ReadAll(resp.Body)
		if err != nil {
			return fmt.Errorf("engine_http: read response from %s: %w", path, err)
		}

		if resp.StatusCode >= 400 {
			safeBody := redactSensitiveJSON(respBody, 500)

			c.log.Error().
				Str("path", path).
				Int("status", resp.StatusCode).
				Str("body", safeBody).
				Msg("engine_http_error_response")

			errorBody := safeBody
			if len(errorBody) > 200 {
				errorBody = errorBody[:200]
			}
			return fmt.Errorf("engine_http: %s returned %d: %s", path, resp.StatusCode, errorBody)
		}

		if err := json.Unmarshal(respBody, &result); err != nil {
			return fmt.Errorf("engine_http: unmarshal response from %s: %w", path, err)
		}

		return nil
	}

	isRetryable := func(err error) bool {
		if strings.Contains(err.Error(), "connection refused") || ctx.Err() != nil {
			return false
		}
		// Only retry on 502/503/504 (proxy/infra errors), NOT 500 (application errors).
		// 500 from the engine usually means an LLM provider failed (e.g. 429 quota)
		// and retrying will just waste more quota.
		if strings.Contains(err.Error(), "returned 502") ||
			strings.Contains(err.Error(), "returned 503") ||
			strings.Contains(err.Error(), "returned 504") {
			return true
		}
		return strings.Contains(err.Error(), "engine_http: request")
	}

	if err := resilience.Retry(ctx, resilience.TransientRetryConfig, isRetryable, operation); err != nil {
		return nil, err
	}

	return result, nil
}

// PostJSONNoRetry sends a POST request without any HTTP-level retries.
// Use this for high-cost, idempotency-sensitive operations like the LLM
// processor, where a failure should bubble up immediately.
func (c *EngineHTTPClient) PostJSONNoRetry(ctx context.Context, path string, body interface{}) (map[string]interface{}, error) {
	url := c.baseURL + path

	jsonBody, err := json.Marshal(body)
	if err != nil {
		return nil, fmt.Errorf("engine_http: marshal request for %s: %w", path, err)
	}

	idempotencyKey := uuid.New().String()
	var result map[string]interface{}

	operation := func() error {
		req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(jsonBody))
		if err != nil {
			return fmt.Errorf("engine_http: create request for %s: %w", path, err)
		}
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("X-Idempotency-Key", idempotencyKey)
		injectTraceContext(ctx, req)

		if isInternalPath(path) {
			if c.internalSecret != "" {
				req.Header.Set(internalAuthHeader, c.internalSecret)
			}
			if claims := auth.ClaimsFromContext(ctx); claims != nil {
				if claims.UserID != "" {
					req.Header.Set(internalUserIDHeader, claims.UserID)
				}
				if claims.Tier != "" {
					req.Header.Set(internalUserTierHeader, claims.Tier)
				}
				if claims.Role != "" {
					req.Header.Set(internalUserRoleHeader, string(claims.Role))
				}
				if claims.Username != "" {
					req.Header.Set(internalUserUsernameHeader, claims.Username)
				}
			} else if userID := auth.UserIDFromContext(ctx); userID != "" {
				req.Header.Set(internalUserIDHeader, userID)
			}
		} else {
			if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
				req.Header.Set("Authorization", "Bearer "+rawToken)
			}
		}

		resp, err := c.client.Do(req)
		if err != nil {
			c.log.Error().
				Str("path", path).
				Err(err).
				Msg("engine_http_request_failed")
			return fmt.Errorf("engine_http: request %s: %w", path, err)
		}
		defer resp.Body.Close()

		respBody, err := io.ReadAll(resp.Body)
		if err != nil {
			return fmt.Errorf("engine_http: read response from %s: %w", path, err)
		}

		if resp.StatusCode >= 400 {
			safeBody := redactSensitiveJSON(respBody, 500)
			c.log.Error().
				Str("path", path).
				Int("status", resp.StatusCode).
				Str("body", safeBody).
				Msg("engine_http_error_response")
			errorBody := safeBody
			if len(errorBody) > 200 {
				errorBody = errorBody[:200]
			}
			return fmt.Errorf("engine_http: %s returned %d: %s", path, resp.StatusCode, errorBody)
		}

		if err := json.Unmarshal(respBody, &result); err != nil {
			return fmt.Errorf("engine_http: unmarshal response from %s: %w", path, err)
		}

		return nil
	}

	// Always false to disable retries.
	isRetryable := func(err error) bool { return false }

	if err := resilience.Retry(ctx, resilience.NoRetryConfig, isRetryable, operation); err != nil {
		return nil, err
	}

	return result, nil
}

// GetJSON sends a GET request and returns the decoded JSON response.
//
// Mirrors PostJSON's auth header logic (internal-secret + user-id for
// /internal/* paths, JWT for public paths), error redaction, retry
// policy, and logging. The trading-plan balance lookup is a GET-only
// engine endpoint, so this helper is required; future callers should
// prefer it over building a raw http.Request.
func (c *EngineHTTPClient) GetJSON(ctx context.Context, path string) (map[string]interface{}, error) {
	url := c.baseURL + path

	var result map[string]interface{}

	operation := func() error {
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
		if err != nil {
			return fmt.Errorf("engine_http: create request for %s: %w", path, err)
		}
		injectTraceContext(ctx, req)

		if isInternalPath(path) {
			if c.internalSecret != "" {
				req.Header.Set(internalAuthHeader, c.internalSecret)
			}
			if claims := auth.ClaimsFromContext(ctx); claims != nil {
				if claims.UserID != "" {
					req.Header.Set(internalUserIDHeader, claims.UserID)
				}
				if claims.Tier != "" {
					req.Header.Set(internalUserTierHeader, claims.Tier)
				}
				if claims.Role != "" {
					req.Header.Set(internalUserRoleHeader, string(claims.Role))
				}
				if claims.Username != "" {
					req.Header.Set(internalUserUsernameHeader, claims.Username)
				}
			} else if userID := auth.UserIDFromContext(ctx); userID != "" {
				req.Header.Set(internalUserIDHeader, userID)
			}
		} else {
			if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
				req.Header.Set("Authorization", "Bearer "+rawToken)
			}
		}

		resp, err := c.client.Do(req)
		if err != nil {
			c.log.Error().
				Str("path", path).
				Err(err).
				Msg("engine_http_get_failed")
			return fmt.Errorf("engine_http: request %s: %w", path, err)
		}
		defer resp.Body.Close()

		respBody, err := io.ReadAll(resp.Body)
		if err != nil {
			return fmt.Errorf("engine_http: read response from %s: %w", path, err)
		}

		if resp.StatusCode >= 400 {
			safeBody := redactSensitiveJSON(respBody, 500)
			c.log.Error().
				Str("path", path).
				Int("status", resp.StatusCode).
				Str("body", safeBody).
				Msg("engine_http_get_error_response")
			if len(safeBody) > 200 {
				safeBody = safeBody[:200]
			}
			return fmt.Errorf("engine_http: %s returned %d: %s", path, resp.StatusCode, safeBody)
		}

		if err := json.Unmarshal(respBody, &result); err != nil {
			return fmt.Errorf("engine_http: unmarshal response from %s: %w", path, err)
		}
		return nil
	}

	isRetryable := func(err error) bool {
		if strings.Contains(err.Error(), "connection refused") || ctx.Err() != nil {
			return false
		}
		if strings.Contains(err.Error(), "returned 502") ||
			strings.Contains(err.Error(), "returned 503") ||
			strings.Contains(err.Error(), "returned 504") {
			return true
		}
		return strings.Contains(err.Error(), "engine_http: request")
	}

	if err := resilience.Retry(ctx, resilience.TransientRetryConfig, isRetryable, operation); err != nil {
		return nil, err
	}

	return result, nil
}

// HealthCheck checks the Python engine's health endpoint.
func (c *EngineHTTPClient) HealthCheck(ctx context.Context) bool {
	checkCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(checkCtx, http.MethodGet, c.baseURL+"/health", nil)
	if err != nil {
		c.log.Error().Err(err).Msg("engine_health_check_request_failed")
		return false
	}

	resp, err := c.client.Do(req)
	if err != nil {
		c.log.Error().Err(err).Msg("engine_health_check_failed")
		return false
	}
	defer resp.Body.Close()

	return resp.StatusCode == http.StatusOK
}

// Close releases HTTP client resources.
func (c *EngineHTTPClient) Close() {
	c.client.CloseIdleConnections()
	c.log.Info().Msg("engine_http_client_closed")
}

// redactSensitiveJSON scans a JSON response body for sensitive field names
// and replaces their values with the redacted placeholder.
func redactSensitiveJSON(body []byte, maxLen int) string {
	if len(body) == 0 {
		return ""
	}

	var parsed map[string]interface{}
	if err := json.Unmarshal(body, &parsed); err == nil {
		redactMap(parsed)
		redacted, err := json.Marshal(parsed)
		if err == nil {
			if len(redacted) > maxLen {
				return string(redacted[:maxLen])
			}
			return string(redacted)
		}
	}

	if len(body) > maxLen {
		return string(body[:maxLen])
	}
	return string(body)
}

func redactMap(m map[string]interface{}) {
	for key, val := range m {
		if observability.IsSensitiveField(strings.ToLower(key)) {
			m[key] = observability.RedactedValue
			continue
		}
		if nested, ok := val.(map[string]interface{}); ok {
			redactMap(nested)
		}
	}
}
