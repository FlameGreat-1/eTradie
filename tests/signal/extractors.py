"""Tests for signal extraction helpers (macro + TA).

Production module: src/engine/signal_extractors.py
"""

from engine.signal_extractors import derive_macro_signals, derive_ta_signals


class TestDeriveMacroSignalsEmpty:
    def test_empty_dict(self):
        signals = derive_macro_signals({})
        assert signals["has_macro_data"] is False
        assert signals["has_cot_data"] is False
        assert signals["has_rate_decision"] is False
        assert signals["has_high_impact_event"] is False
        assert signals["has_dxy_data"] is False
        assert signals["has_qe_qt"] is False
        assert signals["dxy_momentum"] == ""
        assert signals["risk_environment"] == ""
        assert signals["cot_extremes"] == []
        assert signals["fed_tone"] == ""


class TestDeriveMacroSignalsPopulated:
    def test_central_bank_with_rate_decision(self):
        macro = {
            "central_bank": {
                "rate_decisions": [
                    {"bank": "FED", "tone": "HAWKISH", "rate_change_bps": 25}
                ],
            },
        }
        signals = derive_macro_signals(macro)
        assert signals["has_macro_data"] is True
        assert signals["fed_tone"] == "HAWKISH"
        assert signals["has_rate_decision"] is True

    def test_cot_data(self):
        macro = {
            "cot": {
                "latest_positions": [{"currency": "EUR", "net": 50000}],
                "extremes_flagged": ["EUR", "JPY"],
            },
        }
        signals = derive_macro_signals(macro)
        assert signals["has_cot_data"] is True
        assert signals["cot_extremes"] == ["EUR", "JPY"]

    def test_dxy_data(self):
        macro = {
            "dxy": {
                "latest": {"dxy_value": 104.5, "dxy_momentum": "BULLISH"},
            },
        }
        signals = derive_macro_signals(macro)
        assert signals["has_dxy_data"] is True
        assert signals["dxy_momentum"] == "BULLISH"

    def test_sentiment_risk_environment(self):
        macro = {
            "sentiment": {
                "risk_environment": "RISK_OFF",
                "risk_assessment": {
                    "stagflation_detected": True,
                    "safe_haven_demand_elevated": True,
                    "commodity_currencies_weak": False,
                },
            },
        }
        signals = derive_macro_signals(macro)
        assert signals["risk_environment"] == "RISK_OFF"
        assert signals["stagflation_detected"] is True
        assert signals["safe_haven_elevated"] is True
        assert signals["commodity_currencies_weak"] is False


class TestDeriveTASignalsEmpty:
    def test_empty_dict(self):
        signals = derive_ta_signals({})
        assert signals["direction"] == ""
        assert signals["framework"] == ""
        assert signals["setup_families"] == []
        assert signals["patterns"] == []
        assert signals["has_smc"] is False
        assert signals["has_snd"] is False

    def test_error_status_returns_defaults(self):
        signals = derive_ta_signals({"status": "error"})
        assert signals["direction"] == ""
        assert signals["has_smc"] is False


class TestDeriveTASignalsSMCOnly:
    def test_smc_candidates(self):
        ta = {
            "status": "success",
            "smc_candidates": [
                {"direction": "BULLISH", "pattern": "TURTLE_SOUP_LONG"},
            ],
            "snd_candidates": [],
        }
        signals = derive_ta_signals(ta)
        assert signals["direction"] == "long"
        assert signals["framework"] == "smc"
        assert signals["has_smc"] is True
        assert signals["has_snd"] is False
        assert "TURTLE_SOUP_LONG" in signals["patterns"]
        assert "turtle_soup" in signals["setup_families"]


class TestDeriveTASignalsSnDOnly:
    def test_snd_candidates(self):
        ta = {
            "status": "success",
            "smc_candidates": [],
            "snd_candidates": [
                {"direction": "BEARISH", "pattern": "QML_BASELINE", "qml_detected": True},
            ],
        }
        signals = derive_ta_signals(ta)
        assert signals["direction"] == "short"
        assert signals["framework"] == "snd"
        assert signals["has_snd"] is True
        assert "qml" in signals["setup_families"]


class TestDeriveTASignalsMixed:
    def test_both_agree(self):
        ta = {
            "status": "success",
            "smc_candidates": [{"direction": "BULLISH", "pattern": "SH_BMS_RTO_BULLISH"}],
            "snd_candidates": [{"direction": "BULLISH", "pattern": "QMH_BASELINE"}],
        }
        signals = derive_ta_signals(ta)
        assert signals["direction"] == "long"
        assert "smc" in signals["all_frameworks"]
        assert "snd" in signals["all_frameworks"]

    def test_both_disagree(self):
        ta = {
            "status": "success",
            "smc_candidates": [{"direction": "BULLISH", "pattern": "AMD_BULLISH"}],
            "snd_candidates": [{"direction": "BEARISH", "pattern": "QML_BASELINE"}],
        }
        signals = derive_ta_signals(ta)
        assert signals["direction"] == "neutral"
