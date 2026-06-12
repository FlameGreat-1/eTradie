import argparse
import asyncio
import os
import sys

# Add src to path so we can import engine modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import contextlib

from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.mt5.zmq.client import ZmqClient
from engine.ta.constants import Timeframe


async def ping():
    cfg = MT5Config(provider="native")
    c = ZmqClient(config=cfg)
    ok = await c.health_check()
    await c.shutdown()
    sys.exit(0 if ok else 1)


async def full_test():
    cfg = MT5Config(provider="native")
    c = ZmqClient(config=cfg)

    ok = await c.health_check()
    if not ok:
        await c.shutdown()
        sys.exit(1)

    with contextlib.suppress(Exception):
        await c.get_account_info()

    # Test all symbols with ALL timeframes distributed
    test_cases = [
        ("EURUSDm", Timeframe.M1, 10, "[3/11] EURUSDm M1 (1-minute)"),
        ("DXYm", Timeframe.M5, 10, "[4/11] DXYm M5 (5-minute)"),
        ("XAUUSDm", Timeframe.M15, 10, "[5/11] XAUUSDm M15 (15-minute)"),
        ("USDCADm", Timeframe.M30, 10, "[6/11] USDCADm M30 (30-minute)"),
        ("NZDUSDm", Timeframe.H1, 10, "[7/11] NZDUSDm H1 (1-hour)"),
        ("USTEC_x100m", Timeframe.H4, 10, "[8/11] USTEC_x100m H4 (4-hour)"),
        ("US30_x10m", Timeframe.D1, 10, "[9/11] US30_x10m D1 (daily)"),
        ("UKOILm", Timeframe.W1, 5, "[10/11] UKOILm W1 (weekly)"),
        ("EURUSDm", Timeframe.MN1, 3, "[11/11] EURUSDm MN1 (monthly)"),
    ]

    for symbol, timeframe, count, _label in test_cases:
        try:
            # Get tick price
            await c.get_tick_price(symbol)

            # Get candles
            await c.fetch_candles(symbol, timeframe, count=count)

        except Exception:
            pass

    await c.shutdown()


async def tick(symbol):
    cfg = MT5Config(provider="native")
    c = ZmqClient(config=cfg)
    with contextlib.suppress(Exception):
        await c.get_tick_price(symbol)
    await c.shutdown()


async def multi_symbol_test():
    """Test all symbols with tick prices"""
    cfg = MT5Config(provider="native")
    c = ZmqClient(config=cfg)

    symbols = ["EURUSDm", "DXYm", "XAUUSDm", "USDCADm", "NZDUSDm", "USTEC_x100m", "US30_x10m", "UKOILm"]

    for symbol in symbols:
        with contextlib.suppress(Exception):
            await c.get_tick_price(symbol)

    await c.shutdown()


async def timeframe_test():
    """Test all timeframes on a single symbol"""
    cfg = MT5Config(provider="native")
    c = ZmqClient(config=cfg)

    symbol = "EURUSDm"
    timeframes = [
        (Timeframe.M1, 10, "1-minute"),
        (Timeframe.M5, 10, "5-minute"),
        (Timeframe.M15, 10, "15-minute"),
        (Timeframe.M30, 10, "30-minute"),
        (Timeframe.H1, 10, "1-hour"),
        (Timeframe.H4, 10, "4-hour"),
        (Timeframe.D1, 10, "daily"),
        (Timeframe.W1, 5, "weekly"),
        (Timeframe.MN1, 3, "monthly"),
    ]

    for tf, count, _label in timeframes:
        with contextlib.suppress(Exception):
            await c.fetch_candles(symbol, tf, count=count)

    await c.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["ping", "test", "tick", "multi", "timeframes"], required=True)
    parser.add_argument("--symbol", default="EURUSDm")
    args = parser.parse_args()

    if args.mode == "ping":
        asyncio.run(ping())
    elif args.mode == "test":
        asyncio.run(full_test())
    elif args.mode == "tick":
        asyncio.run(tick(args.symbol))
    elif args.mode == "multi":
        asyncio.run(multi_symbol_test())
    elif args.mode == "timeframes":
        asyncio.run(timeframe_test())
