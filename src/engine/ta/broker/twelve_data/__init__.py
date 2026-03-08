"""
Twelve Data API integration.

Fallback market data source for forex, stocks, and crypto.
Uses REST API with rate limiting and caching.
"""

from engine.ta.broker.twelve_data.client import TwelveDataClient
from engine.ta.broker.twelve_data.config import TwelveDataConfig

__all__ = [
    "TwelveDataClient",
    "TwelveDataConfig",
]
