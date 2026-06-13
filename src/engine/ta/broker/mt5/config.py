import os
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MT5Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MT5_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    enabled: bool = Field(default=True)

    provider: Literal["metaapi", "native"] = Field(
        default="metaapi",
        description="Broker bridge provider: 'metaapi' for cloud REST/WS, 'native' for ZeroMQ EA bridge.",
    )

    # -- MetaAPI Cloud settings ------------------------------------------------
    metaapi_token: str = Field(
        default="",
        description="MetaApi.cloud API token for cloud provider mode.",
    )
    metaapi_account_id: str = Field(
        default="",
        description="MetaApi.cloud provisioned account ID.",
    )
    metaapi_region: str = Field(
        default="new-york",
        description="MetaApi.cloud deployment region (e.g., 'new-york', 'london', 'vint-hill').",
    )
    metaapi_base_url: str = Field(
        default="",
        description="MetaApi.cloud REST API base URL. Auto-constructed from region if empty.",
    )

    # -- ZeroMQ Native settings ------------------------------------------------
    zmq_host: str = Field(
        default="host.docker.internal",
        description="IP/hostname of the Windows PC running the ZeroMQ EA.",
    )
    zmq_port: int = Field(
        default=5555,
        ge=1024,
        le=65535,
        description="ZeroMQ REQ/REP port on the EA bridge.",
    )
    zmq_auth_token: str = Field(
        default="",
        description="Authentication token for ZeroMQ EA.",
    )

    # -- Legacy MT5 terminal settings (native mode only) -----------------------
    terminal_path: str | None = Field(default=None)
    account: int = Field(default=0, ge=0)
    password: str = Field(default="")
    server: str = Field(default="")

    # -- Shared operational settings -------------------------------------------
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_delay_seconds: int = Field(default=2, ge=1, le=30)
    connection_timeout_seconds: int = Field(default=30, ge=5, le=120)
    max_candles_per_request: int = Field(default=5000, ge=100, le=50000)
    enable_tick_data: bool = Field(default=False)
    magic_number: int = Field(default=0, description="MT5 magic number for trade tracking.")

    @model_validator(mode="after")
    def _validate_provider_credentials(self) -> "MT5Config":
        """Ensure the selected provider has its required credentials.

        Only the platform-level metaapi_token is required at startup.
        The metaapi_account_id is dynamically provisioned per-user
        via the MetaAPI Provisioning API and stored in the database.

        The requirement is enforced only in production/staging, where
        real MetaApi credentials must be present. In development and
        testing an empty token is allowed so the engine (and its test
        suite) can boot without cloud broker secrets. This mirrors the
        fail-safe pattern used by Settings and RAGConfig.
        """
        app_env = os.getenv("APP_ENV", "development").lower()
        is_prod_like = app_env in {"production", "prod", "staging"}
        if is_prod_like and self.provider == "metaapi" and not self.metaapi_token:
            raise ValueError("MT5_METAAPI_TOKEN is required when MT5_PROVIDER=metaapi")
        return self
