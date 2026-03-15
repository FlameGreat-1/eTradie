package models

import "github.com/flamegreat/etradie/src/gateway/internal/constants"

// GuardCheckResult holds the result of a single guard rule evaluation.
type GuardCheckResult struct {
	Rule     constants.GuardRule    `json:"rule"`
	Verdict  constants.GuardVerdict `json:"verdict"`
	Reason   string                 `json:"reason"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// GuardEvaluationResult aggregates all guard check results.
type GuardEvaluationResult struct {
	Checks         []GuardCheckResult     `json:"checks"`
	OverallVerdict constants.GuardVerdict  `json:"overall_verdict"`
	BlockingRules  []string               `json:"blocking_rules"`
}

// IsApproved returns true when the overall verdict is PASS.
func (r *GuardEvaluationResult) IsApproved() bool {
	return r.OverallVerdict == constants.VerdictPass
}
