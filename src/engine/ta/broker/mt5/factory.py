"""MT5 broker factory.

Reads MT5Config.provider and returns the correct BrokerBase
implementation.  This is the single entry point for creating
an MT5-compatible broker client.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.shared.exceptions import ConfigurationError
from engine.shared.logging import get_logger
from engine.ta.broker.base import BrokerBase
from engine.ta.broker.mt5.config import MT5Config

if TYPE_CHECKING:
    from engine.shared.http.client import HttpClient

logger = get_logger(__name__)


def create_mt5_broker(
    config: MT5Config,
    http_client: "HttpClient | None" = None,
) -> BrokerBase:
    """Create the MT5 broker client based on the configured provider.

    Args:
        config: MT5 configuration with provider selection.
        http_client: Shared HTTP client (required for metaapi provider).

    Returns:
        A fully configured BrokerBase implementation.

    Raises:
        ConfigurationError: On invalid provider or missing dependencies.
    """
    if config.provider == "metaapi":
        if http_client is None:
            raise ConfigurationError(
                "HttpClient is required for metaapi provider",
                details={"provider": config.provider},
            )
        from engine.ta.broker.mt5.metaapi.client import MetaApiClient

        client = MetaApiClient(config=config, http_client=http_client)
        logger.info(
            "mt5_broker_created",
            extra={
                "provider": "metaapi",
                "account_id": config.metaapi_account_id[:8] + "...",
            },
        )
        return client

    if config.provider == "native":
        from engine.ta.broker.mt5.zmq.client import ZmqClient

        client = ZmqClient(config=config)
        logger.info(
            "mt5_broker_created",
            extra={
                "provider": "native",
                "endpoint": f"tcp://{config.zmq_host}:{config.zmq_port}",
            },
        )
        return client

    raise ConfigurationError(
        f"Unknown MT5 provider: {config.provider}",
        details={"provider": config.provider, "allowed": ["metaapi", "native"]},
    )
