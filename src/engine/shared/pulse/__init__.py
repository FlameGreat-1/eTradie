"""Pulse — fire-and-forget real-time analysis status broadcasting.

This module provides the ``PulsePublisher`` used to emit granular
technical milestones (e.g. "Fetching H4 Candle Data", "Detecting
BMS on D1") to the user's private SSE channel during an analysis
cycle.

Usage::

    from engine.shared.pulse import PulsePublisher, NoOpPulse

    # In the rerun endpoint (has cache + user_id):
    pulse = PulsePublisher(cache=container.cache, user_id=user.user_id, symbol=symbol)

    # Pass to TA orchestrator:
    await container.ta_orchestrator.analyze(..., pulse=pulse)

    # When pulse is not needed (e.g. unit tests):
    pulse = NoOpPulse()

Safety:
    All publish calls are fire-and-forget. A failed pulse **never**
    blocks, crashes, or delays the analysis pipeline. If the Redis
    cache is unavailable the publisher silently degrades to a no-op.
"""

from engine.shared.pulse.publisher import NoOpPulse, PulsePublisher

__all__ = ["PulsePublisher", "NoOpPulse"]
