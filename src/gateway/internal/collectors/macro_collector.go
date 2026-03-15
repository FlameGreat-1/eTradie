package collectors

import (
	"context"
	"encoding/json"
	"time"

	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/gateway/internal/constants"
	"github.com/flamegreat/etradie/src/gateway/internal/infra"
	"github.com/flamegreat/etradie/src/gateway/internal/models"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"

	enginev1 "github.com/flamegreat/etradie/proto/engine/v1"
)

// MacroCollector calls the Python engine to collect all 8 macro datasets
// in a single gRPC call (the Python side runs them in parallel).
type MacroCollector struct {
	engine enginev1.EngineServiceClient
	log    zerolog.Logger
}

// NewMacroCollector creates a MacroCollector backed by the engine gRPC client.
func NewMacroCollector(engineConn *infra.EngineClient) *MacroCollector {
	return &MacroCollector{
		engine: enginev1.NewEngineServiceClient(engineConn.Conn),
		log:    observability.Logger("macro_collector"),
	}
}

// Collect runs all 8 macro collectors via the Python engine and returns a MacroResult.
func (c *MacroCollector) Collect(ctx context.Context, traceID string) (*models.MacroResult, error) {
	start := time.Now()

	resp, err := c.engine.CollectMacro(ctx, &enginev1.CollectMacroRequest{
		TraceId: traceID,
	})

	elapsedMs := float64(time.Since(start).Milliseconds())
	observability.GatewayMacroCollectDuration.Observe(time.Since(start).Seconds())

	if err != nil {
		observability.GatewayStageErrors.WithLabelValues(
			constants.StageMacroCollector.String(), "grpc_error",
		).Inc()
		c.log.Error().
			Err(err).
			Str("trace_id", traceID).
			Msg("macro_collection_grpc_failed")
		return nil, err
	}

	result := &models.MacroResult{
		CentralBank: unmarshalDataset(resp.GetCentralBankJson()),
		COT:         unmarshalDataset(resp.GetCotJson()),
		Economic:    unmarshalDataset(resp.GetEconomicJson()),
		News:        unmarshalDataset(resp.GetNewsJson()),
		Calendar:    unmarshalDataset(resp.GetCalendarJson()),
		DXY:         unmarshalDataset(resp.GetDxyJson()),
		Intermarket: unmarshalDataset(resp.GetIntermarketJson()),
		Sentiment:   unmarshalDataset(resp.GetSentimentJson()),
		CollectedAt: time.Now().UTC(),
		DurationMs:  elapsedMs,
		Errors:      resp.GetErrors(),
	}

	if result.Errors == nil {
		result.Errors = make(map[string]string)
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

	return result, nil
}

func unmarshalDataset(data []byte) map[string]interface{} {
	if len(data) == 0 {
		return nil
	}
	var out map[string]interface{}
	if err := json.Unmarshal(data, &out); err != nil {
		return nil
	}
	return out
}
