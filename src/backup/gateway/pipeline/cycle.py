"""Analysis cycle state tracker.

Pure state machine that tracks phase transitions, timing, and outcomes.
No I/O - only state management and duration recording.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from gateway.constants import CycleOutcome, CyclePhase, CycleStatus
from gateway.context.models import CycleState


class CycleTracker:
    """Tracks the lifecycle of a single analysis cycle."""

    def __init__(self, trace_id: Optional[str] = None) -> None:
        self._cycle_id = uuid4().hex
        self._trace_id = trace_id or uuid4().hex
        self._status = CycleStatus.RUNNING
        self._phase = CyclePhase.INITIALIZING
        self._outcome: Optional[CycleOutcome] = None
        self._started_at = datetime.now(UTC)
        self._start_mono = time.monotonic()
        self._phase_start_mono = self._start_mono
        self._completed_at: Optional[datetime] = None
        self._error: Optional[str] = None
        self._error_stage: Optional[str] = None
        self._phase_durations: dict[str, float] = {}

    @property
    def cycle_id(self) -> str:
        return self._cycle_id

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def phase(self) -> CyclePhase:
        return self._phase

    @property
    def status(self) -> CycleStatus:
        return self._status

    @property
    def elapsed_ms(self) -> float:
        return (time.monotonic() - self._start_mono) * 1000

    def transition_to(self, phase: CyclePhase) -> None:
        """Record phase transition and duration of the previous phase."""
        now = time.monotonic()
        prev_duration_ms = (now - self._phase_start_mono) * 1000
        self._phase_durations[self._phase.value] = round(prev_duration_ms, 1)
        self._phase = phase
        self._phase_start_mono = now

    def complete(
        self,
        outcome: CycleOutcome,
    ) -> None:
        """Mark cycle as completed with the given outcome."""
        now = time.monotonic()
        prev_duration_ms = (now - self._phase_start_mono) * 1000
        self._phase_durations[self._phase.value] = round(prev_duration_ms, 1)

        self._phase = CyclePhase.COMPLETED
        self._status = CycleStatus.COMPLETED
        self._outcome = outcome
        self._completed_at = datetime.now(UTC)

    def fail(
        self,
        error: str,
        *,
        stage: Optional[str] = None,
        timed_out: bool = False,
    ) -> None:
        """Mark cycle as failed."""
        now = time.monotonic()
        prev_duration_ms = (now - self._phase_start_mono) * 1000
        self._phase_durations[self._phase.value] = round(prev_duration_ms, 1)

        self._phase = CyclePhase.FAILED
        self._status = CycleStatus.TIMED_OUT if timed_out else CycleStatus.FAILED
        self._outcome = CycleOutcome.PIPELINE_ERROR
        self._error = error
        self._error_stage = stage
        self._completed_at = datetime.now(UTC)

    def to_state(self) -> CycleState:
        """Snapshot the current cycle state."""
        return CycleState(
            cycle_id=self._cycle_id,
            trace_id=self._trace_id,
            status=self._status,
            phase=self._phase,
            outcome=self._outcome,
            started_at=self._started_at,
            phase_started_at=datetime.now(UTC),
            completed_at=self._completed_at,
            error=self._error,
            error_stage=self._error_stage,
            phase_durations_ms=dict(self._phase_durations),
        )
