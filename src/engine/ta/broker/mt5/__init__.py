"""
MetaTrader 5 broker integration.

Primary real-time market data source for forex and metals.
Provides tick-level precision and symbol metadata.
"""

from engine.ta.broker.mt5.client import MT5Client
from engine.ta.broker.mt5.config import MT5Config

__all__ = [
    "MT5Client",
    "MT5Config",
]
