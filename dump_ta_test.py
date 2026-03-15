import json
import sys
from datetime import datetime, UTC

sys.path.append(r"\\wsl.localhost\Ubuntu-24.04\home\softverse\eTradie\src")

try:
    from engine.config import get_ta_config
    from engine.ta.constants import Direction
    from engine.ta.models.candidate import SMCCandidate, SMCPattern

    def main():
        config = get_ta_config()
        
        # 1. Grab timeframes straight from your actual live configuration
        htf_tfs = config.htf_timeframes
        ltf_tfs = config.ltf_timeframes

        # Example 1: The highest timeframe pair generated purely from the config index array
        smc1 = SMCCandidate(
            symbol="EURUSD",
            pattern=SMCPattern.BOS,
            status="ACTIVE",
            htf_timeframe=htf_tfs[0],  # the very first HTF in config (e.g. W1)
            ltf_timeframe=htf_tfs[1],  # the second HTF in config (e.g. D1)
            direction=Direction.BULLISH,
            details={"displacement_pips": 120},
            entry_zone={"high": 1.1200, "low": 1.1150},
            detected_at=datetime.now(UTC),
            expires_at=datetime.now(UTC),
            snapshot_id="mock_htf"
        )

        # Output structure that the LLM actually receives in ProcessorInput
        llm_payload_keys = {
            "metadata": {
                "htf_timeframes_configured": [tf.value for tf in htf_tfs],
                "ltf_timeframes_configured": [tf.value for tf in ltf_tfs]
            },
            "snapshots": {tf.value: {"...mock data...": True} for tf in (htf_tfs + ltf_tfs)},
            "smc_candidates": [
                smc1.model_dump(mode="json")
            ]
        }
        
        print(json.dumps(llm_payload_keys, indent=2))

    main()
except Exception as e:
    print(f"Error: {e}")
