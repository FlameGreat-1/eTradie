package pipeline

import (
	"testing"
	"time"

	"github.com/flamegreat-1/etradie/src/gateway/internal/constants"
)

// =============================================================================
// NewCycleTracker
// =============================================================================

func TestNewCycleTracker_GeneratesCycleID(t *testing.T) {
	tracker := NewCycleTracker("trace-123")
	if tracker.CycleID() == "" {
		t.Fatal("CycleID should not be empty")
	}
	// Hex-encoded 16 bytes = 32 characters.
	if len(tracker.CycleID()) != 32 {
		t.Fatalf("CycleID should be 32 hex chars, got %d: %q", len(tracker.CycleID()), tracker.CycleID())
	}
}

func TestNewCycleTracker_UniqueCycleIDs(t *testing.T) {
	a := NewCycleTracker("trace-1")
	b := NewCycleTracker("trace-2")
	if a.CycleID() == b.CycleID() {
		t.Fatal("two trackers should have different CycleIDs")
	}
}

func TestNewCycleTracker_UsesProvidedTraceID(t *testing.T) {
	tracker := NewCycleTracker("my-trace-abc")
	if tracker.TraceID() != "my-trace-abc" {
		t.Fatalf("expected trace ID %q, got %q", "my-trace-abc", tracker.TraceID())
	}
}

func TestNewCycleTracker_AutoGeneratesTraceID_WhenEmpty(t *testing.T) {
	tracker := NewCycleTracker("")
	if tracker.TraceID() == "" {
		t.Fatal("TraceID should be auto-generated when empty string passed")
	}
	if len(tracker.TraceID()) != 32 {
		t.Fatalf("auto-generated TraceID should be 32 hex chars, got %d", len(tracker.TraceID()))
	}
}

func TestNewCycleTracker_InitialState(t *testing.T) {
	tracker := NewCycleTracker("trace-init")

	if tracker.Status() != constants.StatusRunning {
		t.Fatalf("initial status should be RUNNING, got %s", tracker.Status())
	}
	if tracker.Phase() != constants.PhaseInitializing {
		t.Fatalf("initial phase should be INITIALIZING, got %s", tracker.Phase())
	}
	if tracker.Outcome() != "" {
		t.Fatalf("initial outcome should be empty, got %q", tracker.Outcome())
	}
}

func TestNewCycleTracker_ElapsedMs_NonNegative(t *testing.T) {
	tracker := NewCycleTracker("trace-elapsed")
	elapsed := tracker.ElapsedMs()
	if elapsed < 0 {
		t.Fatalf("ElapsedMs should be non-negative, got %f", elapsed)
	}
}

// =============================================================================
// TransitionTo
// =============================================================================

func TestTransitionTo_UpdatesPhase(t *testing.T) {
	tracker := NewCycleTracker("trace-transition")

	tracker.TransitionTo(constants.PhaseCollectParallel)
	if tracker.Phase() != constants.PhaseCollectParallel {
		t.Fatalf("expected phase COLLECTING_PARALLEL, got %s", tracker.Phase())
	}
}

func TestTransitionTo_RecordsPreviousPhaseDuration(t *testing.T) {
	tracker := NewCycleTracker("trace-duration")

	// Sleep briefly so the INITIALIZING phase has measurable duration.
	time.Sleep(5 * time.Millisecond)

	tracker.TransitionTo(constants.PhaseCollectParallel)

	state := tracker.ToState()
	initDuration, exists := state.PhaseDurationsMs[constants.PhaseInitializing.String()]
	if !exists {
		t.Fatal("INITIALIZING phase duration should be recorded after transition")
	}
	if initDuration <= 0 {
		t.Fatalf("INITIALIZING duration should be > 0, got %f", initDuration)
	}
}

func TestTransitionTo_MultipleTransitions(t *testing.T) {
	tracker := NewCycleTracker("trace-multi")

	time.Sleep(2 * time.Millisecond)
	tracker.TransitionTo(constants.PhaseCollectParallel)

	time.Sleep(2 * time.Millisecond)
	tracker.TransitionTo(constants.PhaseBuildingQuery)

	time.Sleep(2 * time.Millisecond)
	tracker.TransitionTo(constants.PhaseRetrievingRAG)

	state := tracker.ToState()

	// All three previous phases should have recorded durations.
	expectedPhases := []string{
		constants.PhaseInitializing.String(),
		constants.PhaseCollectParallel.String(),
		constants.PhaseBuildingQuery.String(),
	}
	for _, phase := range expectedPhases {
		if _, exists := state.PhaseDurationsMs[phase]; !exists {
			t.Errorf("phase %q duration should be recorded", phase)
		}
	}

	// Current phase should be RETRIEVING_RAG (not yet recorded).
	if tracker.Phase() != constants.PhaseRetrievingRAG {
		t.Fatalf("current phase should be RETRIEVING_RAG, got %s", tracker.Phase())
	}

	// Status should still be RUNNING.
	if tracker.Status() != constants.StatusRunning {
		t.Fatalf("status should still be RUNNING during transitions, got %s", tracker.Status())
	}
}

// =============================================================================
// Complete
// =============================================================================

func TestComplete_TradeApproved(t *testing.T) {
	tracker := NewCycleTracker("trace-complete")
	tracker.TransitionTo(constants.PhaseCollectParallel)
	tracker.Complete(constants.OutcomeTradeApproved)

	if tracker.Status() != constants.StatusCompleted {
		t.Fatalf("expected COMPLETED status, got %s", tracker.Status())
	}
	if tracker.Phase() != constants.PhaseCompleted {
		t.Fatalf("expected COMPLETED phase, got %s", tracker.Phase())
	}
	if tracker.Outcome() != constants.OutcomeTradeApproved {
		t.Fatalf("expected TRADE_APPROVED outcome, got %s", tracker.Outcome())
	}
}

func TestComplete_NoSetup(t *testing.T) {
	tracker := NewCycleTracker("trace-nosetup")
	tracker.Complete(constants.OutcomeNoSetup)

	if tracker.Outcome() != constants.OutcomeNoSetup {
		t.Fatalf("expected NO_SETUP outcome, got %s", tracker.Outcome())
	}
}

func TestComplete_SetsCompletedAt(t *testing.T) {
	tracker := NewCycleTracker("trace-completed-at")
	before := time.Now().UTC()

	tracker.Complete(constants.OutcomeTradeApproved)

	state := tracker.ToState()
	if state.CompletedAt == nil {
		t.Fatal("CompletedAt should be set after Complete()")
	}
	if state.CompletedAt.Before(before) {
		t.Fatal("CompletedAt should be >= the time before Complete() was called")
	}
}

func TestComplete_RecordsFinalPhaseDuration(t *testing.T) {
	tracker := NewCycleTracker("trace-final-dur")
	tracker.TransitionTo(constants.PhaseProcessingLLM)

	time.Sleep(3 * time.Millisecond)
	tracker.Complete(constants.OutcomeTradeApproved)

	state := tracker.ToState()
	procDuration, exists := state.PhaseDurationsMs[constants.PhaseProcessingLLM.String()]
	if !exists {
		t.Fatal("final phase duration should be recorded on Complete")
	}
	if procDuration <= 0 {
		t.Fatalf("final phase duration should be > 0, got %f", procDuration)
	}
}

// =============================================================================
// Fail
// =============================================================================

func TestFail_NotTimedOut(t *testing.T) {
	tracker := NewCycleTracker("trace-fail")
	tracker.TransitionTo(constants.PhaseCollectParallel)

	tracker.Fail("TA collection HTTP error", "ta_collector", false)

	if tracker.Status() != constants.StatusFailed {
		t.Fatalf("expected FAILED status, got %s", tracker.Status())
	}
	if tracker.Phase() != constants.PhaseFailed {
		t.Fatalf("expected FAILED phase, got %s", tracker.Phase())
	}
	if tracker.Outcome() != constants.OutcomePipelineError {
		t.Fatalf("expected PIPELINE_ERROR outcome, got %s", tracker.Outcome())
	}

	state := tracker.ToState()
	if state.Error != "TA collection HTTP error" {
		t.Fatalf("expected error message, got %q", state.Error)
	}
	if state.ErrorStage != "ta_collector" {
		t.Fatalf("expected error stage ta_collector, got %q", state.ErrorStage)
	}
}

func TestFail_TimedOut(t *testing.T) {
	tracker := NewCycleTracker("trace-timeout")
	tracker.TransitionTo(constants.PhaseRetrievingRAG)

	tracker.Fail("Cycle timed out after 300s", "cycle_timeout", true)

	if tracker.Status() != constants.StatusTimedOut {
		t.Fatalf("expected TIMED_OUT status, got %s", tracker.Status())
	}
	if tracker.Phase() != constants.PhaseFailed {
		t.Fatalf("expected FAILED phase, got %s", tracker.Phase())
	}
}

func TestFail_SetsCompletedAt(t *testing.T) {
	tracker := NewCycleTracker("trace-fail-at")
	tracker.Fail("error", "stage", false)

	state := tracker.ToState()
	if state.CompletedAt == nil {
		t.Fatal("CompletedAt should be set after Fail()")
	}
}

func TestFail_RecordsPhaseDuration(t *testing.T) {
	tracker := NewCycleTracker("trace-fail-dur")
	tracker.TransitionTo(constants.PhaseCollectParallel)

	time.Sleep(3 * time.Millisecond)
	tracker.Fail("error", "stage", false)

	state := tracker.ToState()
	if _, exists := state.PhaseDurationsMs[constants.PhaseCollectParallel.String()]; !exists {
		t.Fatal("phase duration should be recorded on Fail")
	}
}

// =============================================================================
// ToState
// =============================================================================

func TestToState_MatchesTrackerFields(t *testing.T) {
	tracker := NewCycleTracker("trace-state")
	tracker.TransitionTo(constants.PhaseCollectParallel)
	tracker.Complete(constants.OutcomeTradeApproved)

	state := tracker.ToState()

	if state.CycleID != tracker.CycleID() {
		t.Fatalf("CycleID mismatch: state=%q tracker=%q", state.CycleID, tracker.CycleID())
	}
	if state.TraceID != tracker.TraceID() {
		t.Fatalf("TraceID mismatch: state=%q tracker=%q", state.TraceID, tracker.TraceID())
	}
	if state.Status != constants.StatusCompleted {
		t.Fatalf("expected COMPLETED status in state, got %s", state.Status)
	}
	if state.Phase != constants.PhaseCompleted {
		t.Fatalf("expected COMPLETED phase in state, got %s", state.Phase)
	}
	if state.Outcome != constants.OutcomeTradeApproved {
		t.Fatalf("expected TRADE_APPROVED outcome in state, got %s", state.Outcome)
	}
}

func TestToState_DurationsMapIsCopy(t *testing.T) {
	tracker := NewCycleTracker("trace-copy")
	tracker.TransitionTo(constants.PhaseCollectParallel)
	tracker.Complete(constants.OutcomeNoSetup)

	state := tracker.ToState()

	// Mutate the returned map.
	state.PhaseDurationsMs["injected"] = 999.0

	// Get a fresh state and verify the injected key is not present.
	state2 := tracker.ToState()
	if _, exists := state2.PhaseDurationsMs["injected"]; exists {
		t.Fatal("ToState should return a copy of durations, not a shared reference")
	}
}

func TestToState_RunningCycle_NoCompletedAt(t *testing.T) {
	tracker := NewCycleTracker("trace-running")

	state := tracker.ToState()
	if state.CompletedAt != nil {
		t.Fatal("running cycle should have nil CompletedAt")
	}
	if state.Error != "" {
		t.Fatalf("running cycle should have empty error, got %q", state.Error)
	}
}

func TestToState_FailedCycle_HasErrorFields(t *testing.T) {
	tracker := NewCycleTracker("trace-err-fields")
	tracker.Fail("connection refused", "macro_collector", false)

	state := tracker.ToState()
	if state.Error != "connection refused" {
		t.Fatalf("expected error message, got %q", state.Error)
	}
	if state.ErrorStage != "macro_collector" {
		t.Fatalf("expected error stage, got %q", state.ErrorStage)
	}
	if state.CompletedAt == nil {
		t.Fatal("failed cycle should have CompletedAt set")
	}
}
