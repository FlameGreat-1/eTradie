package collectors

import (
	"context"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/gateway/internal/config"
	"github.com/flamegreat/etradie/src/gateway/internal/constants"
	"github.com/flamegreat/etradie/src/gateway/internal/infra"
	"github.com/flamegreat/etradie/src/gateway/internal/models"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
)

// TACollector calls the Python TA engine via HTTP for each symbol
// with bounded concurrency, then maps results into gateway models.
type TACollector struct {
	engine *infra.EngineHTTPClient
	cfg    *config.Config
	log    zerolog.Logger
}

// NewTACollector creates a TACollector backed by the engine HTTP client.
func NewTACollector(engine *infra.EngineHTTPClient, cfg *config.Config) *TACollector {
	return &TACollector{
		engine: engine,
		cfg:    cfg,
		log:    observability.Logger("ta_collector"),
	}
}

// Collect runs TA analysis for the given symbols via a single HTTP call
// to the Python engine. The Python side processes them in parallel.
func (c *TACollector) Collect(ctx context.Context, symbols []string, traceID string) (*models.TAResult, error) {
	if len(symbols) == 0 {
		c.log.Warn().Str("trace_id", traceID).Msg("ta_collect_called_with_empty_symbols")
		return &models.TAResult{
			CollectedAt: time.Now().UTC(),
		}, nil
	}

	start := time.Now()

	// Call the Python engine once with all symbols.
	reqBody := map[string]interface{}{
		"symbols":  symbols,
		"trace_id": traceID,
	}

	resp, err := c.engine.PostJSON(ctx, "/internal/ta/analyze", reqBody)
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

	elapsedMs := float64(time.Since(start).Milliseconds())
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

	return &models.TAResult{
		SymbolResults: results,
		CollectedAt:   time.Now().UTC(),
		DurationMs:    elapsedMs,
	}, nil
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
