"""
MetaApi.cloud broker integration.

Cloud-based REST provider for MT5 market data.
Runs on any OS (macOS, Linux, Windows) without a local MT5 terminal.
"""

from engine.ta.broker.mt5.metaapi.client import MetaApiClient
from engine.ta.broker.mt5.metaapi.provisioner import MetaApiProvisioner

__all__ = ["MetaApiClient", "MetaApiProvisioner"]
