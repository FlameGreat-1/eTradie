"""
SnD candidate builders.

Builds SnD candidates from detected primitives and validated zones:
- Fakeout: Builds fakeout-driven SnD candidates (baseline patterns)
- QM: Builds QM/QML/QMH-driven SnD candidates (all QM patterns)
- Continuation: Builds continuation-style SnD candidates (where allowed)

All builders enforce:
- Marubozu is non-negotiable (Universal Rule 1)
- Minimum 2 Previous Highs/Lows (Universal Rule 2)
- Entry is a zone, not a line (Universal Rule 3)
- Top-down timeframe execution (Universal Rule 4)
- Compression adds conviction (Universal Rule 5)
- Diamond Fakeout is exhaustion warning (Universal Rule 6)
- Fakeout broken by Marubozu = entry imminent (Universal Rule 7)
- Multiple fakeout tests = trend strength (Universal Rule 8)
- Fibonacci confluence = 90% probability (Universal Rule 9)

Outputs SnDCandidate models for processor consumption.
"""

from engine.ta.snd.builders.candidates.fakeout import FakeoutCandidateBuilder
from engine.ta.snd.builders.candidates.qm import QMCandidateBuilder
from engine.ta.snd.builders.candidates.continuation import ContinuationCandidateBuilder

__all__ = [
    "FakeoutCandidateBuilder",
    "QMCandidateBuilder",
    "ContinuationCandidateBuilder",
]
