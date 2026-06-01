package models

import "time"

// MacroResult aggregates output from all 7 macro collectors.
type MacroResult struct {
	CentralBank map[string]interface{} `json:"central_bank,omitempty"`
	COT         map[string]interface{} `json:"cot,omitempty"`
	Economic    map[string]interface{} `json:"economic,omitempty"`
	Calendar    map[string]interface{} `json:"calendar,omitempty"`
	DXY         map[string]interface{} `json:"dxy,omitempty"`
	Intermarket map[string]interface{} `json:"intermarket,omitempty"`
	Sentiment   map[string]interface{} `json:"sentiment,omitempty"`
	CollectedAt time.Time              `json:"collected_at"`
	DurationMs  float64                `json:"duration_ms"`
	Errors      map[string]string      `json:"errors"`

	// FromCache is true when served from the Redis cache rather than
	// freshly collected by the engine. Not persisted (json:"-"). The
	// orchestrator reads it to emit a truthful "served from cache"
	// pulse instead of the per-collector CLAUDING feed, which only runs
	// on a cache miss.
	FromCache bool `json:"-"`
}

// datasetNames is the ordered list of macro dataset field names.
var datasetNames = []string{
	"central_bank", "cot", "economic",
	"calendar", "dxy", "intermarket", "sentiment",
}

// AvailableDatasets returns the names of datasets that have non-nil data.
func (r *MacroResult) AvailableDatasets() []string {
	fields := []map[string]interface{}{
		r.CentralBank, r.COT, r.Economic,
		r.Calendar, r.DXY, r.Intermarket, r.Sentiment,
	}
	out := make([]string, 0, 7)
	for i, f := range fields {
		if f != nil {
			out = append(out, datasetNames[i])
		}
	}
	return out
}
