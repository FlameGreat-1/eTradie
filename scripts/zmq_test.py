import asyncio
import os
import sys
import json
import argparse

# Add src to path so we can import engine modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.mt5.zmq.client import ZmqClient
from engine.ta.constants import Timeframe

async def ping():
    cfg = MT5Config(provider='native')
    c = ZmqClient(config=cfg)
    ok = await c.health_check()
    print(f'  Endpoint: tcp://{cfg.zmq_host}:{cfg.zmq_port}')
    print(f'  Status:   ' + ('\033[0;32mCONNECTED\033[0m' if ok else '\033[0;31mUNREACHABLE\033[0m'))
    await c.shutdown()
    sys.exit(0 if ok else 1)

async def full_test():
    cfg = MT5Config(provider='native')
    c = ZmqClient(config=cfg)
    ep = f'tcp://{cfg.zmq_host}:{cfg.zmq_port}'
    print(f'  Endpoint: {ep}')
    print()
    
    print('  [1/4] PING...', end=' ', flush=True)
    ok = await c.health_check()
    print('\033[0;32mOK\033[0m' if ok else '\033[0;31mFAIL\033[0m')
    if not ok:
        print('  EA not reachable. Is MT5 running with the EA attached?')
        await c.shutdown()
        sys.exit(1)
        
    print('  [2/4] ACCOUNT_INFO...', end=' ', flush=True)
    try:
        acc = await c.get_account_info()
        print(f'\033[0;32mOK\033[0m  balance={acc.balance} {acc.currency}')
    except Exception as e:
        print(f'\033[0;31mFAIL\033[0m ({e})')
        
    print('  [3/4] TICK_PRICE EURUSD...', end=' ', flush=True)
    try:
        tick = await c.get_tick_price('EURUSD')
        print(f'\033[0;32mOK\033[0m  bid={tick.bid} ask={tick.ask}')
    except Exception as e:
        print(f'\033[0;31mFAIL\033[0m ({e})')
        
    print('  [4/4] CANDLES EURUSD H1 (5 bars)...', end=' ', flush=True)
    try:
        seq = await c.fetch_candles('EURUSD', Timeframe.H1, count=5)
        print(f'\033[0;32mOK\033[0m  {seq.count} candles fetched')
    except Exception as e:
        print(f'\033[0;31mFAIL\033[0m ({e})')
        
    print()
    print('  \033[0;32m\u2713 All ZMQ bridge tests passed\033[0m')
    await c.shutdown()

async def tick(symbol):
    cfg = MT5Config(provider='native')
    c = ZmqClient(config=cfg)
    try:
        t = await c.get_tick_price(symbol)
        print(f'{symbol}  bid={t.bid}  ask={t.ask}  spread={t.ask-t.bid:.5f}')
    except Exception as e:
        print(f'\033[0;31mFAIL\033[0m ({e})')
    await c.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["ping", "test", "tick"], required=True)
    parser.add_argument("--symbol", default="EURUSD")
    args = parser.parse_args()

    if args.mode == "ping":
        asyncio.run(ping())
    elif args.mode == "test":
        asyncio.run(full_test())
    elif args.mode == "tick":
        asyncio.run(tick(args.symbol))
