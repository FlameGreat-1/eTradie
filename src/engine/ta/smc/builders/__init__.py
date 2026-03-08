"""
SMC candidate builders.

Builds SMC candidates from detected primitives and validated zones:
- Continuation: Builds continuation-style SMC candidates (SH + BMS + RTO)
- Reversal: Builds reversal-style SMC candidates (SMS + BMS + RTO, Turtle Soup)
- AMD: Builds AMD-related SMC candidates (Accumulation, Manipulation, Distribution)

All builders enforce:
- Minimum 3 confluences (Universal Rule 5)
- HTF BMS alignment (Universal Rule 2)
- Premium/Discount filtering (mandatory)
- Session timing (London/NY opens)
- All 7 OB rules satisfied
- All 6 LTF confirmations present

Outputs SMCCandidate models for processor consumption.
"""

from engine.ta.smc.builders.continuation import ContinuationBuilder
from engine.ta.smc.builders.reversal import ReversalBuilder
from engine.ta.smc.builders.amd.candidates import AMDCandidateBuilder

__all__ = [
    "ContinuationBuilder",
    "ReversalBuilder",
    "AMDCandidateBuilder",
]
