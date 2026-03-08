"""
SMC primitive detectors.

Each detector implements deterministic pattern recognition for specific SMC concepts:
- BMS: Break in Market Structure
- CHOCH: Change of Character
- SMS: Shift in Market Structure
- Inducement: Liquidity bait before intended move
- Turtle Soup: Liquidity sweep with reversal
- AMD: Accumulation, Manipulation, Distribution phases

All detectors use shared analyzers and produce domain models.
"""

from engine.ta.smc.detectors.bms import BMSDetector
from engine.ta.smc.detectors.choch import CHOCHDetector
from engine.ta.smc.detectors.sms import SMSDetector
from engine.ta.smc.detectors.inducement import InducementDetector
from engine.ta.smc.detectors.turtle_soup import TurtleSoupDetector
from engine.ta.smc.detectors.amd import AMDDetector

__all__ = [
    "BMSDetector",
    "CHOCHDetector",
    "SMSDetector",
    "InducementDetector",
    "TurtleSoupDetector",
    "AMDDetector",
]
