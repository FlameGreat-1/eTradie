package models

import (
	"time"

	"github.com/flamegreat/etradie/src/gateway/internal/constants"
)

// CycleState tracks the current state of an analysis cycle.
// Used internally by the orchestrator for observability and debugging.
type CycleState struct {
	CycleID          string                    `json:"cycle_id"`
	TraceID          string                    `json:"trace_id"`
	Status           constants.CycleStatus     `json:"status"`
	Phase            constants.CyclePhase      `json:"phase"`
	Outcome          constants.CycleOutcome    `json:"outcome,omitempty"`
	StartedAt        time.Time                 `json:"started_at"`
	PhaseStartedAt   *time.Time                `json:"phase_started_at,omitempty"`
	CompletedAt      *time.Time                `json:"completed_at,omitempty"`
	Error            string                    `json:"error,omitempty"`
	ErrorStage       string                    `json:"error_stage,omitempty"`
	PhaseDurationsMs map[string]float64        `json:"phase_durations_ms"`
}

// GatewayOutput is the complete output of a single analysis cycle.
type GatewayOutput struct {
	CycleStatus     constants.CycleStatus      `json:"cycle_status"`
	CycleOutcome    constants.CycleOutcome     `json:"cycle_outcome"`
	PhaseReached    constants.CyclePhase       `json:"phase_reached"`
	Symbol          string                     `json:"symbol,omitempty"`
	ProcessorOutput *ProcessorOutput           `json:"processor_output,omitempty"`
	GuardResult     *GuardEvaluationResult     `json:"guard_result,omitempty"`
	ExecutionResult map[string]interface{}     `json:"execution_result,omitempty"`
	DurationMs      float64                    `json:"duration_ms"`
	TraceID         string                     `json:"trace_id,omitempty"`
	Error           string                     `json:"error,omitempty"`
	ErrorStage      string                     `json:"error_stage,omitempty"`
}
