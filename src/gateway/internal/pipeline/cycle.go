package pipeline

import (
	"time"

	"github.com/flamegreat/etradie/src/gateway/internal/constants"
	"github.com/flamegreat/etradie/src/gateway/internal/models"

	"crypto/rand"
	"encoding/hex"
)

// CycleTracker tracks the lifecycle of a single analysis cycle.
type CycleTracker struct {
	cycleID        string
	traceID        string
	status         constants.CycleStatus
	phase          constants.CyclePhase
	outcome        constants.CycleOutcome
	startedAt      time.Time
	startMono      time.Time
	phaseStartMono time.Time
	completedAt    *time.Time
	err            string
	errStage       string
	phaseDurations map[string]float64
}

// NewCycleTracker creates a tracker for a new analysis cycle.
func NewCycleTracker(traceID string) *CycleTracker {
	if traceID == "" {
		traceID = generateID()
	}
	now := time.Now()
	return &CycleTracker{
		cycleID:        generateID(),
		traceID:        traceID,
		status:         constants.StatusRunning,
		phase:          constants.PhaseInitializing,
		startedAt:      now.UTC(),
		startMono:      now,
		phaseStartMono: now,
		phaseDurations: make(map[string]float64),
	}
}

// CycleID returns the unique cycle identifier.
func (t *CycleTracker) CycleID() string { return t.cycleID }

// TraceID returns the distributed trace identifier.
func (t *CycleTracker) TraceID() string { return t.traceID }

// Phase returns the current pipeline phase.
func (t *CycleTracker) Phase() constants.CyclePhase { return t.phase }

// Status returns the current cycle status.
func (t *CycleTracker) Status() constants.CycleStatus { return t.status }

// ElapsedMs returns milliseconds since cycle start.
func (t *CycleTracker) ElapsedMs() float64 {
	return float64(time.Since(t.startMono).Milliseconds())
}

// TransitionTo records a phase transition and the duration of the previous phase.
func (t *CycleTracker) TransitionTo(phase constants.CyclePhase) {
	now := time.Now()
	prevDurationMs := float64(now.Sub(t.phaseStartMono).Milliseconds())
	t.phaseDurations[t.phase.String()] = prevDurationMs
	t.phase = phase
	t.phaseStartMono = now
}

// Complete marks the cycle as completed with the given outcome.
func (t *CycleTracker) Complete(outcome constants.CycleOutcome) {
	now := time.Now()
	prevDurationMs := float64(now.Sub(t.phaseStartMono).Milliseconds())
	t.phaseDurations[t.phase.String()] = prevDurationMs

	t.phase = constants.PhaseCompleted
	t.status = constants.StatusCompleted
	t.outcome = outcome
	nowUTC := now.UTC()
	t.completedAt = &nowUTC
}

// Fail marks the cycle as failed.
func (t *CycleTracker) Fail(errMsg string, stage string, timedOut bool) {
	now := time.Now()
	prevDurationMs := float64(now.Sub(t.phaseStartMono).Milliseconds())
	t.phaseDurations[t.phase.String()] = prevDurationMs

	t.phase = constants.PhaseFailed
	if timedOut {
		t.status = constants.StatusTimedOut
	} else {
		t.status = constants.StatusFailed
	}
	t.outcome = constants.OutcomePipelineError
	t.err = errMsg
	t.errStage = stage
	nowUTC := now.UTC()
	t.completedAt = &nowUTC
}

// ToState returns a snapshot of the current cycle state.
func (t *CycleTracker) ToState() *models.CycleState {
	nowUTC := time.Now().UTC()
	durations := make(map[string]float64, len(t.phaseDurations))
	for k, v := range t.phaseDurations {
		durations[k] = v
	}
	return &models.CycleState{
		CycleID:          t.cycleID,
		TraceID:          t.traceID,
		Status:           t.status,
		Phase:            t.phase,
		Outcome:          t.outcome,
		StartedAt:        t.startedAt,
		PhaseStartedAt:   &nowUTC,
		CompletedAt:      t.completedAt,
		Error:            t.err,
		ErrorStage:       t.errStage,
		PhaseDurationsMs: durations,
	}
}

func generateID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
