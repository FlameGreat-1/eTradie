package collectors

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/gateway/internal/config"
	"github.com/flamegreat/etradie/src/gateway/internal/constants"
	"github.com/flamegreat/etradie/src/gateway/internal/infra"
	"github.com/flamegreat/etradie/src/gateway/internal/models"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"

	enginev1 "github.com/flamegreat/etradie/proto/engine/v1"
)

// TACollector calls the Python TA engine via gRPC for each symbol
// with bounded concurrency, then maps results into gateway models.
type TACollector struct {
	engine enginev1.EngineServiceClient
	cfg    *config.Config
	log    zerolog.Logger
}

// NewTACollector creates a TACollector backed by the engine gRPC client.
func NewTACollector(engineConn *infra.EngineClient, cfg *config.Config) *TACollector {
	return &TACollector{
		engine: enginev1.NewEngineServiceClient(engineConn.Conn),
		cfg:    cfg,
		log:    observability.Logger("ta_collector"),
	}
}

// Collect runs TA analysis for the given symbols with bounded concurrency.
func (c *TACollector) Collect(ctx context.Context, symbols []string, traceID string) (*models.TAResult, error) {
	if len(symbols) == 0 {
		c.log.Warn().Str("trace_id", traceID).Msg("ta_collect_called_with_empty_symbols")
		return &models.TAResult{
			CollectedAt: time.Now().UTC(),
		}, nil
	}

	start := time.Now()
	sem := make(chan struct{}, c.cfg.MaxConcurrentSymbols)

	type indexedResult struct {
		index  int
		result models.TASymbolResult
	}

	results := make([]models.TASymbolResult, len(symbols))
	var mu sync.Mutex
	var wg sync.WaitGroup

	for i, symbol := range symbols {
		wg.Add(1)
		go func(idx int, sym string) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			sr := c.analyzeSingle(ctx, sym, traceID)
			mu.Lock()
			results[idx] = sr
			mu.Unlock()
		}(i, symbol)
	}

	wg.Wait()

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

func (c *TACollector) analyzeSingle(ctx context.Context, symbol, traceID string) models.TASymbolResult {
	start := time.Now()

	resp, err := c.engine.AnalyzeTA(ctx, &enginev1.AnalyzeTARequest{
		Symbols: []string{symbol},
		TraceId: traceID,
	})

	elapsed := time.Since(start).Seconds()
	observability.GatewayTACollectDuration.WithLabelValues(symbol).Observe(elapsed)

	if err != nil {
		observability.GatewayStageErrors.WithLabelValues(
			constants.StageTACollector.String(), "grpc_error",
		).Inc()
		c.log.Error().
			Str("symbol", symbol).
			Err(err).
			Str("trace_id", traceID).
			Msg("ta_single_symbol_failed")
		return models.TASymbolResult{
			Symbol: symbol,
			Status: "error",
			Error:  err.Error(),
		}
	}

	if len(resp.GetSymbolResults()) == 0 {
		return models.TASymbolResult{
			Symbol:       symbol,
			Status:       "insufficient_data",
			OverallTrend: "NEUTRAL",
		}
	}

	sr := resp.GetSymbolResults()[0]
	result := models.TASymbolResult{
		Symbol:        sr.GetSymbol(),
		HTFTimeframes: sr.GetHtfTimeframes(),
		LTFTimeframes: sr.GetLtfTimeframes(),
		Status:        sr.GetStatus(),
		OverallTrend:  sr.GetOverallTrend(),
		Error:         sr.GetError(),
	}

	if result.OverallTrend == "" {
		result.OverallTrend = "NEUTRAL"
	}

	// Unmarshal JSON-encoded fields.
	result.SMCCandidates = unmarshalCandidates(sr.GetSmcCandidatesJson())
	result.SnDCandidates = unmarshalCandidates(sr.GetSndCandidatesJson())
	result.Snapshots = unmarshalNestedMap(sr.GetSnapshotsJson())
	result.Alignment = unmarshalNestedMap(sr.GetAlignmentJson())

	if result.Status == "success" {
		observability.GatewayTACandidatesPerCycle.WithLabelValues("smc").Observe(float64(len(result.SMCCandidates)))
		observability.GatewayTACandidatesPerCycle.WithLabelValues("snd").Observe(float64(len(result.SnDCandidates)))
	}

	return result
}

func unmarshalCandidates(data []byte) []map[string]interface{} {
	if len(data) == 0 {
		return nil
	}
	var out []map[string]interface{}
	if err := json.Unmarshal(data, &out); err != nil {
		return nil
	}
	return out
}

func unmarshalNestedMap(data []byte) map[string]map[string]interface{} {
	if len(data) == 0 {
		return nil
	}
	var out map[string]map[string]interface{}
	if err := json.Unmarshal(data, &out); err != nil {
		return nil
	}
	return out
}

// Ensure proto import is used.
var _ = fmt.Sprintf
