package infra

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/gateway/internal/observability"
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

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("engine_http: create request for %s: %w", path, err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		c.log.Error().
			Str("path", path).
			Err(err).
			Msg("engine_http_request_failed")
		return nil, fmt.Errorf("engine_http: request %s: %w", path, err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("engine_http: read response from %s: %w", path, err)
	}

	if resp.StatusCode >= 400 {
		c.log.Error().
			Str("path", path).
			Int("status", resp.StatusCode).
			Str("body", string(respBody[:min(len(respBody), 500)])).
			Msg("engine_http_error_response")
		return nil, fmt.Errorf("engine_http: %s returned %d: %s", path, resp.StatusCode, string(respBody[:min(len(respBody), 200)]))
	}

	var result map[string]interface{}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("engine_http: unmarshal response from %s: %w", path, err)
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

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
