package context

import (
	"github.com/rs/zerolog"

	"github.com/flamegreat/etradie/src/gateway/internal/models"
	"github.com/flamegreat/etradie/src/gateway/internal/observability"
)

// Assembler builds the final ProcessorInput payload by combining
// TA output, Macro output, and RAG-retrieved knowledge.
type Assembler struct {
	log zerolog.Logger
}

// NewAssembler creates a ContextAssembler.
func NewAssembler() *Assembler {
	return &Assembler{log: observability.Logger("context_assembler")}
}

// Assemble builds ProcessorInput from all pipeline outputs.
// ragBundle is the raw JSON-decoded context bundle from the Python RAG service.
func (a *Assembler) Assemble(
	symbol string,
	taResult *models.TASymbolResult,
	macroResult *models.MacroResult,
	ragBundle map[string]interface{},
	traceID string,
) *models.ProcessorInput {
	taAnalysis := buildTASection(taResult)
	macroAnalysis := buildMacroSection(macroResult)

	metadata := map[string]interface{}{
		"symbol":                   symbol,
		"htf_timeframes":           taResult.HTFTimeframes,
		"ltf_timeframes":           taResult.LTFTimeframes,
		"overall_trend":            taResult.OverallTrend,
		"macro_datasets_available": macroResult.AvailableDatasets(),
		"trace_id":                 traceID,
	}

	// Propagate RAG metadata if present in the bundle.
	for _, key := range []string{"strategy_used", "coverage_result", "conflict_result", "total_chunks_returned", "coverage_gaps", "conflict_details"} {
		if v, ok := ragBundle[key]; ok {
			metadata["rag_"+key] = v
		}
	}

	payload := &models.ProcessorInput{
		Symbol:             symbol,
		TAAnalysis:         taAnalysis,
		MacroAnalysis:      macroAnalysis,
		RetrievedKnowledge: ragBundle,
		Metadata:           metadata,
	}

	a.log.Debug().
		Str("symbol", symbol).
		Int("ta_smc_count", len(taResult.SMCCandidates)).
		Int("ta_snd_count", len(taResult.SnDCandidates)).
		Int("macro_datasets", len(macroResult.AvailableDatasets())).
		Str("trace_id", traceID).
		Msg("context_assembled")

	return payload
}

func buildTASection(ta *models.TASymbolResult) map[string]interface{} {
	return map[string]interface{}{
		"symbol":         ta.Symbol,
		"htf_timeframes": ta.HTFTimeframes,
		"ltf_timeframes": ta.LTFTimeframes,
		"status":         ta.Status,
		"smc_candidates": ta.SMCCandidates,
		"snd_candidates": ta.SnDCandidates,
		"snapshots":      ta.Snapshots,
		"alignment":      ta.Alignment,
		"overall_trend":  ta.OverallTrend,
	}
}

func buildMacroSection(macro *models.MacroResult) map[string]interface{} {
	return map[string]interface{}{
		"central_bank":       macro.CentralBank,
		"cot":                macro.COT,
		"economic":           macro.Economic,
		"news":               macro.News,
		"calendar":           macro.Calendar,
		"dxy":                macro.DXY,
		"intermarket":        macro.Intermarket,
		"sentiment":          macro.Sentiment,
		"datasets_available": macro.AvailableDatasets(),
		"collection_errors":  macro.Errors,
	}
}
