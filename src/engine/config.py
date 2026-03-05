"""Engine configuration — Pydantic Settings.

All configuration is loaded from environment variables and validated at startup.
The application fails fast if any required variable is missing or malformed.
This is the single source of truth for every tuneable parameter in the system.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Self

from pydantic import Field, PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Centralised configuration loaded exclusively from environment variables.

    Every external API key, URL, polling interval, and operational parameter
    is defined here with validation.  Missing required values cause an
    immediate startup failure — no silent defaults for secrets.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = "etradie-engine"
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_debug: bool = False
    app_log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # ── PostgreSQL ───────────────────────────────────────────
    database_url: PostgresDsn
    db_pool_size: int = Field(default=10, ge=2, le=50, description="SQLAlchemy connection pool size")
    db_max_overflow: int = Field(default=20, ge=0, le=100, description="Max connections above pool_size")
    db_pool_timeout: int = Field(default=30, ge=5, le=120, description="Seconds to wait for a connection from pool")
    db_pool_recycle: int = Field(default=1800, ge=300, le=7200, description="Seconds before a connection is recycled")
    db_echo: bool = Field(default=False, description="Echo SQL statements to log (dev only)")

    # ── Redis ────────────────────────────────────────────────
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")
    redis_max_connections: int = Field(default=20, ge=5, le=100, description="Redis connection pool max")
    redis_socket_timeout: float = Field(default=5.0, ge=1.0, le=30.0)
    redis_socket_connect_timeout: float = Field(default=5.0, ge=1.0, le=30.0)

    # ── API Keys — Data Providers ────────────────────────────
    # CFTC (no key required — public API)
    cftc_api_base_url: str = "https://publicreporting.cftc.gov/resource"

    # NewsAPI
    newsapi_api_key: str = Field(default="", description="NewsAPI.org API key")
    newsapi_base_url: str = "https://newsapi.org/v2"

    # Twelve Data
    twelvedata_api_key: str = Field(default="", description="TwelveData API key")
    twelvedata_base_url: str = "https://api.twelvedata.com"

    # TradingEconomics.com — institutional-grade economic data
    tradingeconomics_api_key: str = Field(default="", description="TradingEconomics.com API key")
    tradingeconomics_base_url: str = "https://api.tradingeconomics.com"

    # FRED (Federal Reserve Economic Data) — US-only backup
    fred_api_key: str = Field(default="", description="FRED (St. Louis Fed) API key")
    fred_base_url: str = "https://api.stlouisfed.org/fred"

    # ── RSS Feed URLs — Central Banks ────────────────────────
    fed_rss_url: str = "https://www.federalreserve.gov/feeds/press_all.xml"
    ecb_rss_url: str = "https://www.ecb.europa.eu/rss/press.html"
    boe_rss_url: str = "https://www.bankofengland.co.uk/rss/news"
    boj_rss_url: str = "https://www.boj.or.jp/en/rss/whatsnew.xml"

    # ── RSS Feed URLs — News ─────────────────────────────────
    reuters_rss_url: str = "https://www.reutersagency.com/feed"
    bloomberg_rss_url: str = "https://feeds.bloomberg.com/markets/news.rss"

    # ── Polling Intervals (seconds) ──────────────────────────
    poll_interval_central_bank_rss: int = Field(default=600, ge=60, description="CB RSS poll: 10 min default")
    poll_interval_news: int = Field(default=900, ge=60, description="News poll: 15 min default")
    poll_interval_calendar: int = Field(default=1800, ge=60, description="Calendar poll: 30 min default")
    poll_interval_cot: int = Field(default=604800, ge=3600, description="COT poll: weekly default")
    poll_interval_dxy: int = Field(default=14400, ge=300, description="DXY poll: 4H default")
    poll_interval_intermarket: int = Field(default=86400, ge=3600, description="Intermarket poll: daily default")
    poll_interval_sentiment: int = Field(default=604800, ge=3600, description="Sentiment poll: weekly default")
    poll_interval_economic_data: int = Field(default=3600, ge=300, description="Economic data poll: 1H default")
    analysis_cycle_interval: int = Field(default=14400, ge=300, description="Analysis cycle: 4H default")

    # ── HTTP Client ──────────────────────────────────────────
    http_timeout_seconds: int = Field(default=30, ge=5, le=120)
    http_max_retries: int = Field(default=3, ge=1, le=10)
    http_retry_backoff_base: float = Field(default=1.0, ge=0.1, le=10.0)
    http_retry_backoff_max: float = Field(default=60.0, ge=5.0, le=300.0)

    # ── Rate Limiting ────────────────────────────────────────
    rate_limit_requests_per_minute: int = Field(default=60, ge=1)
    rate_limit_burst_size: int = Field(default=10, ge=1)

    # ── Circuit Breaker ──────────────────────────────────────
    circuit_breaker_failure_threshold: int = Field(default=5, ge=2, le=20)
    circuit_breaker_recovery_timeout: int = Field(default=60, ge=10, le=600, description="Seconds before half-open")
    circuit_breaker_half_open_max_calls: int = Field(default=3, ge=1, le=10)

    # ── Observability ────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "etradie-engine"
    prometheus_metrics_port: int = Field(default=9090, ge=1024, le=65535)

    # ── Cache TTL (seconds) ──────────────────────────────────
    cache_ttl_central_bank: int = Field(default=600, ge=60)
    cache_ttl_news: int = Field(default=300, ge=60)
    cache_ttl_calendar: int = Field(default=900, ge=60)
    cache_ttl_cot: int = Field(default=86400, ge=3600)
    cache_ttl_dxy: int = Field(default=14400, ge=300)
    cache_ttl_intermarket: int = Field(default=43200, ge=3600)
    cache_ttl_sentiment: int = Field(default=86400, ge=3600)
    cache_ttl_economic_data: int = Field(default=1800, ge=300)

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> Self:
        """In production and staging, all critical API keys must be set."""
        if self.app_env in {AppEnvironment.PRODUCTION, AppEnvironment.STAGING}:
            required_keys = {
                "newsapi_api_key": self.newsapi_api_key,
                "twelvedata_api_key": self.twelvedata_api_key,
                "tradingeconomics_api_key": self.tradingeconomics_api_key,
            }
            missing = [k for k, v in required_keys.items() if not v]
            if missing:
                msg = f"Production/staging requires API keys: {', '.join(missing)}"
                raise ValueError(msg)
        if self.app_env == AppEnvironment.PRODUCTION and self.app_debug:
            raise ValueError("app_debug must be False in production")
        if self.app_env == AppEnvironment.PRODUCTION and self.db_echo:
            raise ValueError("db_echo must be False in production")
        return self

    @property
    def async_database_url(self) -> str:
        """Database URL with asyncpg driver for SQLAlchemy async engine."""
        return str(self.database_url)

    @property
    def sync_database_url(self) -> str:
        """Database URL with psycopg2 driver for Alembic migrations."""
        return str(self.database_url).replace("+asyncpg", "")

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnvironment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.app_env == AppEnvironment.TESTING

    @property
    def json_logs(self) -> bool:
        """Use JSON log output in non-development environments."""
        return self.app_env != AppEnvironment.DEVELOPMENT


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton settings instance, cached after first load."""
    return Settings()
