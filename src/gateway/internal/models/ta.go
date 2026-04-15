package models

import "time"

// TASymbolResult holds the TA analysis result for a single symbol.
// The gateway does NOT dictate timeframes; the TA engine owns that.
type TASymbolResult struct {
	Symbol        string                            `json:"symbol"`
	HTFTimeframes []string                          `json:"htf_timeframes"`
	LTFTimeframes []string                          `json:"ltf_timeframes"`
	Status        string                            `json:"status"` // "success" | "insufficient_data" | "error"
	SMCCandidates []map[string]interface{}          `json:"smc_candidates"`
	SnDCandidates []map[string]interface{}          `json:"snd_candidates"`
	Snapshots     map[string]map[string]interface{} `json:"snapshots"`
	Alignment     map[string]map[string]interface{} `json:"alignment"`
	OverallTrend  string                            `json:"overall_trend"`
	Error         string                            `json:"error,omitempty"`
}

// TAResult aggregates TA output across all symbols for a cycle.
type TAResult struct {
	SymbolResults []TASymbolResult `json:"symbol_results"`
	CollectedAt   time.Time        `json:"collected_at"`
	DurationMs    float64          `json:"duration_ms"`
}

// HasCandidates returns true if any successful symbol has SMC or SnD candidates.
func (r *TAResult) HasCandidates() bool {
	for i := range r.SymbolResults {
		sr := &r.SymbolResults[i]
		if sr.Status == "success" && (len(sr.SMCCandidates) > 0 || len(sr.SnDCandidates) > 0) {
			return true
		}
	}
	return false
}

// SuccessfulSymbols returns the list of symbols that were analysed successfully.
func (r *TAResult) SuccessfulSymbols() []string {
	out := make([]string, 0, len(r.SymbolResults))
	for i := range r.SymbolResults {
		if r.SymbolResults[i].Status == "success" {
			out = append(out, r.SymbolResults[i].Symbol)
		}
	}
	return out
}

// TotalSMCCandidates returns the total number of SMC candidates across all symbols.
func (r *TAResult) TotalSMCCandidates() int {
	total := 0
	for i := range r.SymbolResults {
		total += len(r.SymbolResults[i].SMCCandidates)
	}
	return total
}

// TotalSnDCandidates returns the total number of SnD candidates across all symbols.
func (r *TAResult) TotalSnDCandidates() int {
	total := 0
	for i := range r.SymbolResults {
		total += len(r.SymbolResults[i].SnDCandidates)
	}
	return total
}
