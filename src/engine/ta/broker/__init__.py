"""
Broker and market data feed integration layer.

Provides:
- Abstract broker contract for market data access
- MT5 adapter for primary real-time data
- Twelve Data adapter for fallback/reference data
- TradingView webhook handler for external alerts
- Broker registry and factory
- Market data validation

All brokers return normalized Candle models.
"""

from engine.ta.broker.base import BrokerBase, BrokerCapabilities
__all__ = [
    "BrokerBase",
    "BrokerCapabilities",
]
