"""
SnD candidate composition.

Builds all 14 SnD pattern candidates:
1. QML + SR Flip + Fakeout (baseline)
2. QML + MPL + SR Flip + Fakeout
3. QML + Previous Highs + MPL + SR Flip + Fakeout (Type 1 - 90% Killer Setup)
4. QML + Previous Highs + MPL + SR Flip + Fakeout (Type 2 - 90% Killer Setup)
5. QML + Triple Fakeout (highest confluence)
6. Fakeout King (multiple fakeout tests)
7. Previous Highs + Supply Zone + Fakeout (S.O.P)
8. QMH + RS Flip + Fakeout (baseline)
9. QMH + MPL + RS Flip + Fakeout
10. QMH + Previous Lows + MPL + RS Flip + Fakeout (Type 1 - 90% Killer Setup)
11. QMH + Previous Lows + MPL + RS Flip + Fakeout (Type 2 - 90% Killer Setup)
12. QMH + Triple Fakeout (highest confluence)
13. Fakeout King (multiple fakeout tests)
14. Previous Lows + Demand Zone + Fakeout (S.O.P)

Each builder validates all requirements before generating candidates.
"""

from engine.ta.snd.builders.candidates.fakeout import FakeoutCandidateBuilder
from engine.ta.snd.builders.candidates.qm import QMCandidateBuilder
from engine.ta.snd.builders.candidates.continuation import ContinuationCandidateBuilder

__all__ = [
    "FakeoutCandidateBuilder",
    "QMCandidateBuilder",
    "ContinuationCandidateBuilder",
]
