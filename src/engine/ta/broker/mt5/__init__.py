"""
MetaTrader 5 broker integration (Hybrid Architecture).

Supports two network-based providers:
- metaapi: Cloud REST/WS via MetaApi.cloud (Linux, macOS, Windows)
- native:  ZeroMQ REQ/REP bridge to a Windows MT5 terminal

The provider is selected via the MT5_PROVIDER environment variable.
No local MetaTrader5 library is required on any platform.
"""

from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.mt5.factory import create_mt5_broker

__all__ = [
    "MT5Config",
    "create_mt5_broker",
]
