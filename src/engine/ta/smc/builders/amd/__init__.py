"""
AMD-specific candidate building.

Builds AMD-related SMC candidates from detected AMD context events.

Pattern 4/9: AMD (Accumulation, Manipulation, Distribution)
- Accumulation: Asian session consolidates and builds a range
- Manipulation: London/NY open manipulates price above/below Asian range to trap traders
- Distribution: Price reverses hard in true direction

Entry during Distribution using:
- Simple RTO to OB
- SH + BMS + RTO
- SMS + BMS + RTO

Requirements (Universal Rule 8):
- Must identify which phase price is in
- Only enter during Distribution phase
- If Manipulation has not completed, do not enter
- Session timing is critical (London/NY opens)
"""

from engine.ta.smc.builders.amd.candidates import AMDCandidateBuilder

__all__ = [
    "AMDCandidateBuilder",
]
