package collectors

import (
	"context"
	"encoding/json"
	"sort"
	"strings"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/config"
	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
	"github.com/flamegreat-1/etradie/src/gateway/internal/infra"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
	"github.com/flamegreat-1/etradie/src/gateway/internal/observability"
)

// TACollector calls the Python TA engine via HTTP for each symbol
// with bounded concurrency, then maps results into gateway models.
// Results are cached in Redis to avoid redundant HTTP calls within
// the configured TTL window.
type TACollector struct {
	engine   *infra.EngineHTTPClient
	redis    *infra.RedisClient
	cfg      *config.Config
	cacheTTL time.Duration
	log      zerolog.Logger
}

// NewTACollector creates a TACollector backed by the engine HTTP client
// with optional Redis caching. If redis is nil or TTL is 0, caching is disabled.
func NewTACollector(engine *infra.EngineHTTPClient, redis *infra.RedisClient, cfg *config.Config) *TACollector {
	return &TACollector{
		engine:   engine,
		redis:    redis,
		cfg:      cfg,
		cacheTTL: time.Duration(cfg.TACacheTTLSeconds) * time.Second,
		log:      observability.Logger("ta_collector"),
	}
}

// taCacheKey builds a deterministic cache key from the user ID and sorted symbol list.
// The userID ensures cache isolation between tenants.
func taCacheKey(userID string, symbols []string) string {
	sorted := make([]string, len(symbols))
	copy(sorted, symbols)
	sort.Strings(sorted)
	if userID != "" {
		return userID + ":" + strings.Join(sorted, ",")
	}
	return strings.Join(sorted, ",")
}

// Collect runs TA analysis for the given symbols via a single HTTP call
// to the Python engine. The Python side processes them in parallel.
func (c *TACollector) Collect(ctx context.Context, symbols []string, traceID string, bypassCache bool) (*models.TAResult, error) {
	if len(symbols) == 0 {
		c.log.Warn().Str("trace_id", traceID).Msg("ta_collect_called_with_empty_symbols")
		return &models.TAResult{
			CollectedAt: time.Now().UTC(),
		}, nil
	}

	// Extract userID for cache key scoping (multi-tenant isolation).
	userID := auth.UserIDFromContext(ctx)

	// Check cache first (unless bypassing).
	if !bypassCache {
		if cached := c.getFromCache(ctx, userID, symbols, traceID); cached != nil {
			return cached, nil
		}
	}

	start := time.Now()

	// Call the Python engine once with all symbols.
	reqBody := map[string]interface{}{
		"symbols":  symbols,
		"trace_id": traceID,
	}

	resp, err := c.engine.PostJSON(ctx, "/internal/ta/analyze", reqBody)

	elapsed := time.Since(start)
	observability.GatewayTACollectDuration.Observe(elapsed.Seconds())

	if err != nil {
		observability.GatewayStageErrors.WithLabelValues(
			constants.StageTACollector.String(), "http_error",
		).Inc()
		c.log.Error().
			Err(err).
			Str("trace_id", traceID).
			Msg("ta_collection_http_failed")
		return nil, err
	}

	// Parse symbol_results from the response.
	results := c.parseSymbolResults(resp, symbols, traceID)

	elapsedMs := float64(elapsed.Milliseconds())
	successCount := 0
	for i := range results {
		if results[i].Status == "success" {
			successCount++
		}
	}

	c.log.Info().
		Strs("symbols_requested", symbols).
		Int("symbols_total", len(symbols)).
		Int("symbols_success", successCount).
		Float64("duration_ms", elapsedMs).
		Str("trace_id", traceID).
		Msg("ta_collection_completed")

	result := &models.TAResult{
		SymbolResults: results,
		CollectedAt:   time.Now().UTC(),
		DurationMs:    elapsedMs,
	}

	// Cache successful result.
	c.storeInCache(ctx, userID, symbols, result, traceID)

	return result, nil
}

func (c *TACollector) getFromCache(ctx context.Context, userID string, symbols []string, traceID string) *models.TAResult {
	if c.redis == nil || c.cacheTTL <= 0 {
		return nil
	}

	key := taCacheKey(userID, symbols)
	raw, err := c.redis.GetRaw(ctx, constants.GatewayCacheNamespace, constants.TAResultCacheKeyPrefix+":"+key)
	if err != nil {
		c.log.Warn().Err(err).Str("trace_id", traceID).Msg("ta_cache_read_error")
		return nil
	}
	if raw == nil {
		return nil
	}

	// Single-pass unmarshal directly into the typed struct.
	var result models.TAResult
	if err := json.Unmarshal(raw, &result); err != nil {
		c.log.Warn().Err(err).Str("trace_id", traceID).Msg("ta_cache_unmarshal_error")
		return nil
	}

	c.log.Info().
		Strs("symbols", symbols).
		Str("trace_id", traceID).
		Msg("ta_result_served_from_cache")
	return &result
}

func (c *TACollector) storeInCache(ctx context.Context, userID string, symbols []string, result *models.TAResult, traceID string) {
	if c.redis == nil || c.cacheTTL <= 0 {
		return
	}

	key := taCacheKey(userID, symbols)
	if err := c.redis.Set(ctx, constants.GatewayCacheNamespace, constants.TAResultCacheKeyPrefix+":"+key, result, c.cacheTTL); err != nil {
		c.log.Warn().Err(err).Str("trace_id", traceID).Msg("ta_cache_write_error")
	}
}

func (c *TACollector) parseSymbolResults(
	resp map[string]interface{},
	symbols []string,
	traceID string,
) []models.TASymbolResult {
	rawResults, ok := resp["symbol_results"]
	if !ok {
		c.log.Warn().Str("trace_id", traceID).Msg("ta_response_missing_symbol_results")
		var results []models.TASymbolResult
		for _, sym := range symbols {
			results = append(results, models.TASymbolResult{
				Symbol:       sym,
				Status:       "error",
				Error:        "missing symbol_results in response",
				OverallTrend: "NEUTRAL",
			})
		}
		return results
	}

	resultSlice, ok := rawResults.([]interface{})
	if !ok {
		c.log.Warn().Str("trace_id", traceID).Msg("ta_response_symbol_results_not_array")
		return nil
	}

	var results []models.TASymbolResult
	for _, raw := range resultSlice {
		resultMap, ok := raw.(map[string]interface{})
		if !ok {
			continue
		}

		sr := models.TASymbolResult{
			Symbol:        getStringField(resultMap, "symbol"),
			Status:        getStringField(resultMap, "status"),
			OverallTrend:  getStringFieldDefault(resultMap, "overall_trend", "NEUTRAL"),
			Error:         getStringField(resultMap, "error"),
			HTFTimeframes: getStringSlice(resultMap, "htf_timeframes"),
			LTFTimeframes: getStringSlice(resultMap, "ltf_timeframes"),
		}

		sr.SMCCandidates = getMapSlice(resultMap, "smc_candidates")
		sr.SnDCandidates = getMapSlice(resultMap, "snd_candidates")
		sr.Snapshots = getNestedMapMap(resultMap, "snapshots")
		sr.Alignment = getNestedMapMap(resultMap, "alignment")

		if sr.Status == "success" {
			observability.GatewayTACandidatesPerCycle.WithLabelValues("smc").Observe(float64(len(sr.SMCCandidates)))
			observability.GatewayTACandidatesPerCycle.WithLabelValues("snd").Observe(float64(len(sr.SnDCandidates)))
		}

		results = append(results, sr)
	}

	return results
}

// JSON response field helpers.

func getStringField(m map[string]interface{}, key string) string {
	v, ok := m[key]
	if !ok || v == nil {
		return ""
	}
	s, ok := v.(string)
	if !ok {
		return ""
	}
	return s
}

func getStringFieldDefault(m map[string]interface{}, key, def string) string {
	s := getStringField(m, key)
	if s == "" {
		return def
	}
	return s
}

func getStringSlice(m map[string]interface{}, key string) []string {
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	slice, ok := v.([]interface{})
	if !ok {
		return nil
	}
	out := make([]string, 0, len(slice))
	for _, item := range slice {
		if s, ok := item.(string); ok {
			out = append(out, s)
		}
	}
	return out
}

func getMapSlice(m map[string]interface{}, key string) []map[string]interface{} {
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	slice, ok := v.([]interface{})
	if !ok {
		return nil
	}
	out := make([]map[string]interface{}, 0, len(slice))
	for _, item := range slice {
		if mp, ok := item.(map[string]interface{}); ok {
			out = append(out, mp)
		}
	}
	return out
}

func getNestedMapMap(m map[string]interface{}, key string) map[string]map[string]interface{} {
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	outer, ok := v.(map[string]interface{})
	if !ok {
		return nil
	}
	out := make(map[string]map[string]interface{}, len(outer))
	for k, val := range outer {
		if inner, ok := val.(map[string]interface{}); ok {
			out[k] = inner
		}
	}
	return out
}
