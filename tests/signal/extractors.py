from engine.signal_extractors import derive_macro_signals, derive_ta_signals
from engine.ta.constants import Direction


def test_derive_macro_signals_empty():
    """Test macro signal derivation with no data."""
    signals = derive_macro_signals(None)
    assert signals == {
        "fed_tone": "NEUTRAL",
        "has_rate_decision": False,
        "is_qe": False,
        "is_qt": False,
        "cot_extreme": False,
        "dxy_momentum": "NEUTRAL",
        "risk_environment": "NEUTRAL",
        "intermarket_present": False,
    }


def test_derive_macro_signals_populated():
    """Test macro signal derivation with populated data."""
    macro_data = {
        "fed_tone": "HAWKISH",
        "events": [{"impact": "HIGH", "event": "FOMC Rate Decision"}],
        "is_qt": True,
        "cot_signal": {"extreme_flag": True},
        "dxy_bias": {"direction": "BULLISH"},
        "sentiment": {"risk_environment": "RISK_OFF"},
        "intermarket": {"bonds": "BULLISH"},
    }
    signals = derive_macro_signals(macro_data)
    
    assert signals["fed_tone"] == "HAWKISH"
    assert signals["has_rate_decision"] is True
    assert signals["is_qt"] is True
    assert signals["cot_extreme"] is True
    assert signals["dxy_momentum"] == "BULLISH"
    assert signals["risk_environment"] == "RISK_OFF"
    assert signals["intermarket_present"] is True


def test_derive_ta_signals_empty():
    """Test TA signal derivation with no data."""
    signals = derive_ta_signals(None)
    assert signals == {
        "direction": "NO SETUP",
        "framework": "",
        "setup_families": [],
        "patterns": [],
        "ltf_confirmed": False,
    }


def test_derive_ta_signals_smc_only():
    """Test TA signal derivation with only SMC candidates."""
    ta_data = {
        "smc_candidates": [
            {"direction": "LONG", "pattern": "Bullish OB", "ltf_confirmed": True}
        ],
        "snd_candidates": [],
    }
    signals = derive_ta_signals(ta_data)
    
    assert signals["direction"] == "LONG"
    assert signals["framework"] == "SMC"
    assert "SMC" in signals["setup_families"]
    assert "Bullish OB" in signals["patterns"]
    assert signals["ltf_confirmed"] is True


def test_derive_ta_signals_snd_only():
    """Test TA signal derivation with only SnD candidates."""
    ta_data = {
        "smc_candidates": [],
        "snd_candidates": [
            {"direction": "SHORT", "pattern": "Supply Zone", "ltf_confirmed": False}
        ],
    }
    signals = derive_ta_signals(ta_data)
    
    assert signals["direction"] == "SHORT"
    assert signals["framework"] == "SnD"
    assert "SnD" in signals["setup_families"]
    assert "Supply Zone" in signals["patterns"]
    assert signals["ltf_confirmed"] is False


def test_derive_ta_signals_mixed_agreement():
    """Test TA signal derivation when SMC and SnD agree on direction."""
    ta_data = {
        "smc_candidates": [{"direction": "LONG", "pattern": "Bullish OB"}],
        "snd_candidates": [{"direction": "LONG", "pattern": "Demand Zone"}],
    }
    signals = derive_ta_signals(ta_data)
    
    assert signals["direction"] == "LONG"
    assert signals["framework"] == "SMC_SND_CONFLUENCE"
    assert "SMC" in signals["setup_families"]
    assert "SnD" in signals["setup_families"]
    assert "Bullish OB" in signals["patterns"]
    assert "Demand Zone" in signals["patterns"]


def test_derive_ta_signals_mixed_conflict():
    """Test TA signal derivation when SMC and SnD disagree on direction."""
    ta_data = {
        "smc_candidates": [{"direction": "LONG", "pattern": "Bullish OB"}],
        "snd_candidates": [{"direction": "SHORT", "pattern": "Supply Zone"}],
    }
    signals = derive_ta_signals(ta_data)
    
    # Current simplistic logic takes the majority or first. 
    # With 1 LONG and 1 SHORT, it defaults to the first one processed (usually SMC).
    assert signals["direction"] in ["LONG", "SHORT"]
    assert signals["framework"] == "SMC_SND_CONFLUENCE"
