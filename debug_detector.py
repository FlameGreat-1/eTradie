import sys
sys.path.insert(0, './src')

import asyncio
import logging

from engine.shared.repositories.market_data import MarketDataRepository
from engine.ta.smc.detector import SMCDetector
from engine.ta.common.timeframes import Timeframe

logging.basicConfig(level=logging.DEBUG)

async def test():
    repo = MarketDataRepository('output/BTCUSDm_20260416T113524Z/history')
    w1 = await repo.load('BTCUSDm', Timeframe.W1, 1500)
    d1 = await repo.load('BTCUSDm', Timeframe.D1, 1500)
    h4 = await repo.load('BTCUSDm', Timeframe.H4, 1500)
    
    det = SMCDetector()
    print("=== W1 / D1 ===")
    candidates = det.detect_patterns(w1, d1)
    print(f"Total returned from detect_patterns(W1, D1): {len(candidates)}")
    for c in candidates:
         print(f"Detected: {c.pattern.value} {c.direction.value} at {c.timestamp}")

    det = SMCDetector()
    print("\n=== D1 / H4 ===")
    candidates = det.detect_patterns(d1, h4)
    print(f"Total returned from detect_patterns(D1, H4): {len(candidates)}")
    for c in candidates:
         print(f"Detected: {c.pattern.value} {c.direction.value} at {c.timestamp}")
         
asyncio.run(test())
