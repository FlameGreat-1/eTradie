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

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
	"github.com/flamegreat-1/etradie/src/pkg/resilience"
)

// EngineHTTPClient communicates with the Python engine's internal HTTP endpoints.
type EngineHTTPClient struct {
	baseURL string
	client  *http.Client
	log     zerolog.Logger
}

// NewEngineHTTPClient creates an HTTP client for the Python engine.
func NewEngineHTTPClient(baseURL string, timeoutSeconds int) *EngineHTTPClient {
	log := observability.Logger("engine_http_client")

	client := &http.Client{
		Timeout: time.Duration(timeoutSeconds) * time.Second,
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 20,
			IdleConnTimeout:     90 * time.Second,
		},
	}

	log.Info().
		Str("base_url", baseURL).
		Int("timeout_seconds", timeoutSeconds).
		Msg("engine_http_client_initialized")

	return &EngineHTTPClient{
		baseURL: baseURL,
		client:  client,
		log:     log,
	}
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

		// Forward the JWT Authorization header from the original request
		// so the Python engine can identify the authenticated user.
		if rawToken := auth.RawTokenFromContext(ctx); rawToken != "" {
			req.Header.Set("Authorization", "Bearer "+rawToken)
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

			// Log error but don't fail immediately, let it retry if applicable
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
		// Retry on network errors or 5xx server errors
		if strings.Contains(err.Error(), "connection refused") || ctx.Err() != nil {
			return false // Context canceled is not retryable
		}
		if strings.Contains(err.Error(), "returned 5") {
			return true // 5xx server errors
		}
		return strings.Contains(err.Error(), "engine_http: request") // Network/timeout errors
	}

	if err := resilience.Retry(ctx, resilience.DefaultRetryConfig, isRetryable, operation); err != nil {
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
// and replaces their values with the redacted placeholder. Returns a
// truncated string safe for logging.
func redactSensitiveJSON(body []byte, maxLen int) string {
	if len(body) == 0 {
		return ""
	}

	// Try to parse as JSON for field-level redaction.
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

	// Fallback: not valid JSON, just truncate.
	if len(body) > maxLen {
		return string(body[:maxLen])
	}
	return string(body)
}

// redactMap recursively redacts sensitive fields in a map.
func redactMap(m map[string]interface{}) {
	for key, val := range m {
		if observability.IsSensitiveField(strings.ToLower(key)) {
			m[key] = observability.RedactedValue
			continue
		}
		// Recurse into nested maps.
		if nested, ok := val.(map[string]interface{}); ok {
			redactMap(nested)
		}
	}
}
