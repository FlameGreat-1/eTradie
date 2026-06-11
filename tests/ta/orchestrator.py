"""Tests for TAOrchestrator (top-down analysis pipeline).

Production module: src/engine/ta/orchestrator.py

The TAOrchestrator requires 9 injected dependencies (broker client,
3 repositories, 2 detectors, snapshot builder, alignment service,
timeframe manager). Full orchestrator tests require mock infrastructure
and are deferred to the integration test phase.
"""


class TestTAOrchestratorImports:
    def test_orchestrator_importable(self):
        from engine.ta.orchestrator import TAOrchestrator
        assert TAOrchestrator is not None

    def test_smc_detector_importable(self):
        from engine.ta.smc.detector import SMCDetector
        assert SMCDetector is not None

    def test_snd_detector_importable(self):
        from engine.ta.snd.detector import SnDDetector
        assert SnDDetector is not None

    def test_snapshot_builder_importable(self):
        from engine.ta.common.services.snapshot.builder import SnapshotBuilder
        assert SnapshotBuilder is not None

    def test_alignment_service_importable(self):
        from engine.ta.common.services.alignment.service import AlignmentService
        assert AlignmentService is not None

    def test_timeframe_manager_importable(self):
        from engine.ta.common.timeframe.manager import TimeframeManager
        assert TimeframeManager is not None



class TestTAConfigForOrchestrator:
    def test_ta_config_has_required_fields(self):
        from engine.config import TAConfig
        cfg = TAConfig()
        assert hasattr(cfg, "htf_timeframes")
        assert hasattr(cfg, "ltf_timeframes")
        assert hasattr(cfg, "primary_broker")
        assert hasattr(cfg, "smc_enabled")
        assert hasattr(cfg, "snd_enabled")
