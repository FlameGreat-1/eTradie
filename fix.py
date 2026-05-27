with open('src/engine/ta/orchestrator.py', 'r') as f:
    data = f.read()

target = """        flag_attrs = (
            "bms_detected", "choch_detected", "sms_detected",
            "liquidity_swept", "inducement_cleared",
        symbol: str,"""

replacement = """        flag_attrs = (
            "bms_detected", "choch_detected", "sms_detected",
            "liquidity_swept", "inducement_cleared", "qml_detected",
            "sr_rs_flip_detected", "mpl_detected", "fakeout_detected",
            "marubozu_detected", "compression_detected", "ltf_confirmation"
        )
        flag_count = sum(bool(getattr(c, attr, False)) for attr in flag_attrs)
        return (confluences, flag_count, getattr(c, "entry_price", 0.0))

    async def _fetch_candles(
        self,
        symbol: str,"""

data = data.replace(target, replacement)

with open('src/engine/ta/orchestrator.py', 'w') as f:
    f.write(data)

print("Fixed orchestrator.py")
