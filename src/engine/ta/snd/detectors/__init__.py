"""
SnD primitive detectors.

Each detector implements deterministic pattern recognition for specific SnD concepts:
- QM: Quasimodo structure (H → HH → break of H = QML)
- SR Flip: Support becomes Resistance after Marubozu break
- RS Flip: Resistance becomes Support after Marubozu break
- Previous Levels: Clustered highs/lows (minimum 2 touches)
- MPL: Mini Price Level (internal engulfing structure)
- Fakeouts: R1-R4 / S1-S4 tests at SR/RS Flip zones
- Supply/Demand: Zone boundaries between SR/RS Flip and QML

All detectors use shared analyzers and produce domain models.
"""

from engine.ta.snd.detectors.qm import QMDetector
from engine.ta.snd.detectors.sr_flip import SRFlipDetector
from engine.ta.snd.detectors.rs_flip import RSFlipDetector
from engine.ta.snd.detectors.previous_levels import PreviousLevelDetector
from engine.ta.snd.detectors.mpl import MPLDetector
from engine.ta.snd.detectors.fakeouts import FakeoutDetector
from engine.ta.snd.detectors.supply_demand import SupplyDemandDetector

__all__ = [
    "QMDetector",
    "SRFlipDetector",
    "RSFlipDetector",
    "PreviousLevelDetector",
    "MPLDetector",
    "FakeoutDetector",
    "SupplyDemandDetector",
]
