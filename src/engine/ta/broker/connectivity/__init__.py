"""Broker connectivity primitives shared by ZmqClient and MetaApiClient.

This package is the single source of truth for:
  - exponential-backoff reconnect (reconnect.py)
  - per-connection heartbeat task (heartbeat.py)
  - tick freshness validation (freshness.py)
  - logical -> broker symbol resolution (symbol_resolver.py)

Client code MUST consume these primitives instead of rolling its own.
Audit ref: CHECKLIST Section 2.
"""

from engine.ta.broker.connectivity.freshness import TickFreshnessGuard
from engine.ta.broker.connectivity.heartbeat import (
    BrokerHeartbeatService,
    HeartbeatProbeFn,
    HeartbeatResult,
    HeartbeatState,
)
from engine.ta.broker.connectivity.outbound_limiter import OutboundRateLimiter
from engine.ta.broker.connectivity.reconnect import ReconnectPolicy
from engine.ta.broker.connectivity.symbol_resolver import SymbolResolver

__all__ = [
    "BrokerHeartbeatService",
    "HeartbeatProbeFn",
    "HeartbeatResult",
    "HeartbeatState",
    "OutboundRateLimiter",
    "ReconnectPolicy",
    "SymbolResolver",
    "TickFreshnessGuard",
]
