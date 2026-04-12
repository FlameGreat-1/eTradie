package collectors

import (
	"context"
	"encoding/json"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
)

// MacroCollector calls the Python engine to collect all 8 macro datasets
// via a single HTTP call (the Python side runs them in parallel).
// Results are cached in Redis to avoid redundant HTTP calls within
// the configured TTL window.
type MacroCollector struct {
	engine   *infra.EngineHTTPClient
	redis    *infra.RedisClient
	cacheTTL time.Duration
	log      zerolog.Logger
}

// NewMacroCollector creates a MacroCollector backed by the engine HTTP client
// with optional Redis caching. If redis is nil or TTL is 0, caching is disabled.
func NewMacroCollector(engine *infra.EngineHTTPClient, redis *infra.RedisClient, cacheTTLSeconds int) *MacroCollector {
	return &MacroCollector{
		engine:   engine,
		redis:    redis,
		cacheTTL: time.Duration(cacheTTLSeconds) * time.Second,
		log:      observability.Logger("macro_collector"),
	}
}

// Collect runs all 8 macro collectors via the Python engine and returns a MacroResult.
func (c *MacroCollector) Collect(ctx context.Context, traceID string) (*models.MacroResult, error) {
	// Check global cache first.
	if cached := c.getFromCache(ctx, traceID); cached != nil {
		return cached, nil
	}

	start := time.Now()

	reqBody := map[string]interface{}{
		"trace_id": traceID,
	}

	resp, err := c.engine.PostJSON(ctx, "/internal/macro/collect", reqBody)

	elapsedMs := float64(time.Since(start).Milliseconds())
	observability.GatewayMacroCollectDuration.Observe(time.Since(start).Seconds())

	if err != nil {
		observability.GatewayStageErrors.WithLabelValues(
			constants.StageMacroCollector.String(), "http_error",
		).Inc()
		c.log.Error().
			Err(err).
			Str("trace_id", traceID).
			Msg("macro_collection_http_failed")
		return nil, err
	}

	result := &models.MacroResult{
		CentralBank: getDatasetMap(resp, "central_bank"),
		COT:         getDatasetMap(resp, "cot"),
		Economic:    getDatasetMap(resp, "economic"),
		News:        getDatasetMap(resp, "news"),
		Calendar:    getDatasetMap(resp, "calendar"),
		DXY:         getDatasetMap(resp, "dxy"),
		Intermarket: getDatasetMap(resp, "intermarket"),
		Sentiment:   getDatasetMap(resp, "sentiment"),
		CollectedAt: time.Now().UTC(),
		DurationMs:  elapsedMs,
		Errors:      getErrorsMap(resp),
	}

	available := result.AvailableDatasets()
	failed := make([]string, 0, len(result.Errors))
	for k := range result.Errors {
		failed = append(failed, k)
	}

	c.log.Info().
		Strs("datasets_available", available).
		Strs("datasets_failed", failed).
		Float64("duration_ms", elapsedMs).
		Str("trace_id", traceID).
		Msg("macro_collection_completed")

	// Cache successful result globally.
	c.storeInCache(ctx, result, traceID)

	return result, nil
}

// macroCacheKey returns the global cache key for macro results.
func macroCacheKey() string {
	return "latest"
}

func (c *MacroCollector) getFromCache(ctx context.Context, traceID string) *models.MacroResult {
	if c.redis == nil || c.cacheTTL <= 0 {
		return nil
	}

	raw, err := c.redis.GetRaw(ctx, constants.GatewayCacheNamespace, constants.MacroResultCacheKeyPrefix+":"+macroCacheKey())
	if err != nil {
		c.log.Warn().Err(err).Str("trace_id", traceID).Msg("macro_cache_read_error")
		return nil
	}
	if raw == nil {
		return nil
	}

	// Single-pass unmarshal directly into the typed struct.
	var result models.MacroResult
	if err := json.Unmarshal(raw, &result); err != nil {
		c.log.Warn().Err(err).Str("trace_id", traceID).Msg("macro_cache_unmarshal_error")
		return nil
	}

	c.log.Info().
		Str("trace_id", traceID).
		Msg("macro_result_served_from_cache")
	return &result
}

func (c *MacroCollector) storeInCache(ctx context.Context, result *models.MacroResult, traceID string) {
	if c.redis == nil || c.cacheTTL <= 0 {
		return
	}

	if err := c.redis.Set(ctx, constants.GatewayCacheNamespace, constants.MacroResultCacheKeyPrefix+":"+macroCacheKey(), result, c.cacheTTL); err != nil {
		c.log.Warn().Err(err).Str("trace_id", traceID).Msg("macro_cache_write_error")
	}
}

func getDatasetMap(resp map[string]interface{}, key string) map[string]interface{} {
	v, ok := resp[key]
	if !ok || v == nil {
		return nil
	}
	m, ok := v.(map[string]interface{})
	if !ok {
		return nil
	}
	return m
}

func getErrorsMap(resp map[string]interface{}) map[string]string {
	v, ok := resp["errors"]
	if !ok || v == nil {
		return make(map[string]string)
	}
	raw, ok := v.(map[string]interface{})
	if !ok {
		return make(map[string]string)
	}
	out := make(map[string]string, len(raw))
	for k, val := range raw {
		if s, ok := val.(string); ok {
			out[k] = s
		}
	}
	return out
}
