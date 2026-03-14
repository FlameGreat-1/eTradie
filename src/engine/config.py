"""Engine configuration — Pydantic Settings.

All configuration is loaded from environment variables and validated at startup.
The application fails fast if any required variable is missing or malformed.
This is the single source of truth for every tuneable parameter in the system.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Self

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from engine.ta.constants import Timeframe


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


class TAConfig(BaseSettings):
    """Technical Analysis configuration.

    All TA parameters are loaded from env vars prefixed with ``TA_``.
    Includes symbols, timeframes, broker selection, and analysis tuning.
    """

    model_config = SettingsConfigDict(
        env_prefix="TA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    enabled: bool = Field(default=True)

    smc_enabled: bool = Field(default=True)
    snd_enabled: bool = Field(default=True)

    primary_broker: str = Field(default="mt5")
    fallback_broker: str = Field(default="twelve_data")

    default_symbols: list[str] = Field(
        default_factory=lambda: [
            "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
            "AUDUSD", "NZDUSD", "USDCAD", "XAUUSD",
        ]
    )

    htf_timeframes: list[Timeframe] = Field(
        default_factory=lambda: [Timeframe.D1, Timeframe.H4, Timeframe.H1]
    )

    ltf_timeframes: list[Timeframe] = Field(
        default_factory=lambda: [Timeframe.M30, Timeframe.M15, Timeframe.M5, Timeframe.M1]
    )

    candle_lookback_periods: int = Field(default=500, ge=100, le=5000)

    snapshot_cache_ttl_seconds: int = Field(default=300, ge=60, le=3600)

    candidate_cache_ttl_seconds: int = Field(default=600, ge=60, le=3600)

    analysis_interval_seconds: int = Field(default=60, ge=30, le=300)

    backfill_on_startup: bool = Field(default=True)

    max_concurrent_symbol_analysis: int = Field(default=4, ge=1, le=10)

    @field_validator("primary_broker", "fallback_broker")
    @classmethod
    def validate_broker(cls, v: str) -> str:
        allowed = {"mt5", "twelve_data", "tradingview"}
        if v not in allowed:
            raise ValueError(f"Broker must be one of {allowed}")
        return v

    @field_validator("default_symbols")
    @classmethod
    def validate_symbols(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one symbol must be configured")
        return [s.upper() for s in v]


class RAGConfig(BaseSettings):
    """RAG Intelligence Engine configuration.

    All RAG parameters are loaded from env vars prefixed with ``RAG_``.
    Covers embedding providers, vector store, chunking strategy,
    retrieval tuning, reranking, knowledge base governance, and
    ingest pipeline settings.
    """

    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Master switch for the RAG subsystem")

    # ── Embedding Provider ──────────────────────────────────────────
    embedding_provider: str = Field(
        default="openai",
        description="Active embedding provider: openai, nomic, sentence_transformers",
    )
    embedding_model: str = Field(
        default="text-embedding-3-large",
        description="Model identifier for the active embedding provider",
    )
    embedding_dimensions: int = Field(
        default=3072, ge=64, le=4096,
        description="Output vector dimensionality",
    )
    embedding_batch_size: int = Field(
        default=64, ge=1, le=512,
        description="Chunks per embedding API call",
    )
    embedding_max_retries: int = Field(
        default=3, ge=1, le=10,
        description="Max retries per embedding batch request",
    )
    embedding_timeout_seconds: int = Field(
        default=30, ge=5, le=120,
        description="Timeout per embedding API call",
    )

    # ── Embedding API Keys ──────────────────────────────────────────
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for text-embedding-3-large",
    )
    openai_embedding_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL",
    )

    # ── Vector Store ────────────────────────────────────────────────
    vectorstore_provider: str = Field(
        default="chroma",
        description="Active vector store backend: chroma",
    )
    chroma_host: str = Field(
        default="localhost",
        description="ChromaDB server host",
    )
    chroma_port: int = Field(
        default=8000, ge=1, le=65535,
        description="ChromaDB server port",
    )
    chroma_auth_token: str = Field(
        default="",
        description="ChromaDB authentication token (empty for no auth)",
    )
    chroma_ssl: bool = Field(
        default=False,
        description="Use TLS for ChromaDB connection",
    )
    collection_documents: str = Field(
        default="etradie_documents",
        description="ChromaDB collection name for rulebook/guide chunks",
    )
    collection_scenarios: str = Field(
        default="etradie_scenarios",
        description="ChromaDB collection name for chart scenario chunks",
    )

    # ── Chunking ────────────────────────────────────────────────────
    chunk_size: int = Field(
        default=1024, ge=128, le=4096,
        description="Target chunk size in tokens",
    )
    chunk_overlap: int = Field(
        default=128, ge=0, le=512,
        description="Overlap between consecutive chunks in tokens",
    )
    chunk_min_size: int = Field(
        default=64, ge=16, le=512,
        description="Minimum chunk size; smaller chunks are merged with neighbors",
    )
    chunk_max_size: int = Field(
        default=2048, ge=256, le=8192,
        description="Maximum chunk size; larger chunks are force-split",
    )

    # ── Retrieval ───────────────────────────────────────────────────
    retrieval_top_k: int = Field(
        default=40, ge=1, le=200,
        description="Number of candidate chunks to retrieve from vector store per bucket",
    )
    retrieval_score_threshold: float = Field(
        default=0.20, ge=0.0, le=1.0,
        description="Minimum similarity score to include a chunk in results",
    )
    retrieval_default_strategy: str = Field(
        default="hybrid",
        description="Default retrieval strategy: rule_first, scenario_first, macro_bias, hybrid",
    )

    # ── Reranking ───────────────────────────────────────────────────
    rerank_enabled: bool = Field(
        default=True,
        description="Enable reranking stage after initial retrieval",
    )
    rerank_top_k: int = Field(
        default=25, ge=1, le=100,
        description="Number of chunks to keep after reranking",
    )
    rerank_model: str = Field(
        default="rule_weighted",
        description="Reranking method: rule_weighted (built-in rule-based scoring)",
    )

    # ── Coverage & Conflict ─────────────────────────────────────────
    coverage_min_rule_chunks: int = Field(
        default=4, ge=1, le=20,
        description="Minimum rulebook chunks required for sufficient coverage",
    )
    coverage_min_framework_chunks: int = Field(
        default=3, ge=1, le=20,
        description="Minimum framework-specific chunks required",
    )
    conflict_auto_reject: bool = Field(
        default=True,
        description="Auto-reject (NO SETUP) when conflicting rules are retrieved",
    )

    # ── Knowledge Base Paths ────────────────────────────────────────
    knowledge_base_dir: str = Field(
        default="knowledge",
        description="Root directory containing knowledge base source documents",
    )
    scenario_assets_dir: str = Field(
        default="knowledge/scenarios",
        description="Directory containing chart scenario assets",
    )

    # ── Ingest Pipeline ─────────────────────────────────────────────
    ingest_on_startup: bool = Field(
        default=True,
        description="Run bootstrap ingest check on application startup",
    )
    ingest_max_concurrent: int = Field(
        default=4, ge=1, le=16,
        description="Max concurrent document ingest operations",
    )
    ingest_retry_max: int = Field(
        default=3, ge=1, le=10,
        description="Max retries for failed ingest jobs",
    )

    # ── Cache TTL ───────────────────────────────────────────────────
    cache_ttl_retrieval: int = Field(
        default=300, ge=60, le=3600,
        description="Cache TTL for retrieval results in seconds",
    )
    cache_ttl_embedding: int = Field(
        default=86400, ge=3600, le=604800,
        description="Cache TTL for embedding hashes in seconds",
    )

    @field_validator("embedding_provider")
    @classmethod
    def validate_embedding_provider(cls, v: str) -> str:
        allowed = {"openai", "nomic", "sentence_transformers"}
        if v not in allowed:
            raise ValueError(f"Embedding provider must be one of {allowed}")
        return v

    @field_validator("vectorstore_provider")
    @classmethod
    def validate_vectorstore_provider(cls, v: str) -> str:
        allowed = {"chroma"}
        if v not in allowed:
            raise ValueError(f"Vector store provider must be one of {allowed}")
        return v

    @field_validator("retrieval_default_strategy")
    @classmethod
    def validate_retrieval_strategy(cls, v: str) -> str:
        allowed = {"rule_first", "scenario_first", "macro_bias", "hybrid"}
        if v not in allowed:
            raise ValueError(f"Retrieval strategy must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def _validate_chunk_bounds(self) -> Self:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be less than "
                f"chunk_size ({self.chunk_size})"
            )
        if self.chunk_min_size >= self.chunk_size:
            raise ValueError(
                f"chunk_min_size ({self.chunk_min_size}) must be less than "
                f"chunk_size ({self.chunk_size})"
            )
        # rerank_top_k can be less than retrieval_top_k (that is the point)
        # but should not exceed a reasonable upper bound
        if self.rerank_top_k > 100:
            raise ValueError(
                f"rerank_top_k ({self.rerank_top_k}) must not exceed 100"
            )
        return self

    @model_validator(mode="after")
    def _validate_production_embedding_key(self) -> Self:
        if self.embedding_provider == "openai" and not self.openai_api_key:
            import os
            env = os.getenv("APP_ENV", "development")
            if env in {"production", "staging"}:
                raise ValueError(
                    "RAG_OPENAI_API_KEY is required when embedding_provider "
                    "is 'openai' in production/staging"
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton settings instance, cached after first load."""
    return Settings()


@lru_cache(maxsize=1)
def get_ta_config() -> TAConfig:
    """Return the singleton TA config instance, cached after first load."""
    return TAConfig()


@lru_cache(maxsize=1)
def get_rag_config() -> RAGConfig:
    """Return the singleton RAG config instance, cached after first load."""
    return RAGConfig()
