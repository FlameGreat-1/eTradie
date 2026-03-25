"""MT5 broker factory.

Reads MT5Config.provider and returns the correct BrokerBase
implementation.  This is the single entry point for creating
an MT5-compatible broker client.

Two creation paths:
  1. create_mt5_broker(config) - from MT5Config (env vars)
  2. create_mt5_broker_from_connection(row, http_client) - from DB row
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.shared.exceptions import ConfigurationError
from engine.shared.logging import get_logger
from engine.ta.broker.base import BrokerBase
from engine.ta.broker.mt5.config import MT5Config

if TYPE_CHECKING:
    from engine.processor.storage.schemas.broker_connection_schema import (
        BrokerConnectionRow,
    )
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


def create_mt5_broker_from_connection(
    row: "BrokerConnectionRow",
    http_client: "HttpClient",
    *,
    ea_auth_token: str = "",
    metaapi_token: str = "",
) -> BrokerBase:
    """Create an MT5 broker client from a database connection row.

    Builds an MT5Config programmatically from the decrypted credentials
    stored in the broker_connections table, then delegates to the
    appropriate client constructor.

    Args:
        row: BrokerConnectionRow with connection details.
        http_client: Shared HTTP client (required for metaapi).
        ea_auth_token: Decrypted EA auth token (for EA connections).
        metaapi_token: Decrypted MetaAPI token (for MetaAPI connections).

    Returns:
        A fully configured BrokerBase implementation.

    Raises:
        ConfigurationError: On invalid connection type or missing data.
    """
    if row.connection_type == "ea":
        if not row.ea_host or row.ea_port is None:
            raise ConfigurationError(
                "EA connection requires host and port",
                details={"connection_id": str(row.id)},
            )

        # Build MT5Config for ZeroMQ native provider.
        config = MT5Config.model_construct(
            enabled=True,
            provider="native",
            metaapi_token="",
            metaapi_account_id="",
            zmq_host=row.ea_host,
            zmq_port=row.ea_port,
            terminal_path=None,
            account=0,
            password="",
            server=row.mt5_server or "",
            timeout_seconds=60,
            max_retries=3,
            retry_delay_seconds=2,
            connection_timeout_seconds=30,
            max_candles_per_request=5000,
            enable_tick_data=False,
        )

        from engine.ta.broker.mt5.zmq.client import ZmqClient

        client = ZmqClient(config=config)
        logger.info(
            "mt5_broker_created_from_db",
            extra={
                "provider": "native",
                "connection_id": str(row.id),
                "name": row.name,
                "endpoint": f"tcp://{row.ea_host}:{row.ea_port}",
            },
        )
        return client

    if row.connection_type == "metaapi":
        if not metaapi_token or not row.metaapi_account_id:
            raise ConfigurationError(
                "MetaAPI connection requires token and account_id",
                details={"connection_id": str(row.id)},
            )

        # Build MT5Config for MetaAPI cloud provider.
        config = MT5Config.model_construct(
            enabled=True,
            provider="metaapi",
            metaapi_token=metaapi_token,
            metaapi_account_id=row.metaapi_account_id,
            zmq_host="",
            zmq_port=5555,
            terminal_path=None,
            account=0,
            password="",
            server=row.mt5_server or "",
            timeout_seconds=60,
            max_retries=3,
            retry_delay_seconds=2,
            connection_timeout_seconds=30,
            max_candles_per_request=5000,
            enable_tick_data=False,
        )

        from engine.ta.broker.mt5.metaapi.client import MetaApiClient

        client = MetaApiClient(config=config, http_client=http_client)
        logger.info(
            "mt5_broker_created_from_db",
            extra={
                "provider": "metaapi",
                "connection_id": str(row.id),
                "name": row.name,
                "account_id": row.metaapi_account_id[:8] + "...",
            },
        )
        return client

    raise ConfigurationError(
        f"Unknown connection type: {row.connection_type}",
        details={
            "connection_id": str(row.id),
            "connection_type": row.connection_type,
            "allowed": ["ea", "metaapi"],
        },
    )
