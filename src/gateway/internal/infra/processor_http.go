package infra

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/gateway/internal/models"
)

// HTTPProcessorAdapter implements ports.ProcessorPort by calling
// the Python engine's /internal/processor/process HTTP endpoint.
type HTTPProcessorAdapter struct {
	engine *EngineHTTPClient
}

// NewHTTPProcessorAdapter creates a processor adapter backed by HTTP.
func NewHTTPProcessorAdapter(engine *EngineHTTPClient) *HTTPProcessorAdapter {
	return &HTTPProcessorAdapter{engine: engine}
}

// Process sends the assembled context to the Python Processor LLM
// and returns the trade decision.
func (a *HTTPProcessorAdapter) Process(ctx context.Context, input *models.ProcessorInput) (*models.ProcessorOutput, error) {
	reqBody := map[string]interface{}{
		"processor_input": map[string]interface{}{
			"symbol":              input.Symbol,
			"ta_analysis":         input.TAAnalysis,
			"macro_analysis":      input.MacroAnalysis,
			"retrieved_knowledge": input.RetrievedKnowledge,
			"metadata":            input.Metadata,
		},
	}

	if traceID, ok := input.Metadata["trace_id"]; ok {
		reqBody["trace_id"] = traceID
	}

	// Defense-in-depth: even though EngineHTTPClient also sets the
	// X-User-Id / X-User-Tier / X-User-Role / X-User-Username headers,
	// we mirror the same fields in the JSON body. A misconfigured
	// proxy that strips custom headers would otherwise silently drop
	// the user identity and the engine would 400 us, or worse,
	// silently personalise against the wrong user. With body fallback
	// the engine reconciles header-first, body-second.
	if claims := auth.ClaimsFromContext(ctx); claims != nil {
		if claims.UserID != "" {
			reqBody["user_id"] = claims.UserID
		}
		if claims.Tier != "" {
			reqBody["tier"] = claims.Tier
		}
		if claims.Role != "" {
			reqBody["role"] = string(claims.Role)
		}
		if claims.Username != "" {
			reqBody["username"] = claims.Username
		}
	}

	resp, err := a.engine.PostJSON(ctx, "/internal/processor/process", reqBody)
	if err != nil {
		return nil, fmt.Errorf("processor HTTP call failed: %w", err)
	}

	// Marshal the response map back to JSON, then unmarshal into ProcessorOutput.
	respJSON, err := json.Marshal(resp)
	if err != nil {
		return nil, fmt.Errorf("processor response marshal: %w", err)
	}

	var output models.ProcessorOutput
	if err := json.Unmarshal(respJSON, &output); err != nil {
		return nil, fmt.Errorf("processor response unmarshal: %w", err)
	}

	return &output, nil
}
