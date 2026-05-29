from __future__ import annotations

from typing import Optional

from engine.config import get_settings
from engine.shared.alert_publisher import AlertPublisher
from engine.shared.cache import RedisCache
from engine.shared.concurrency import BackgroundTaskCoordinator
from engine.shared.db import DatabaseManager
from engine.shared.http import HttpClient
from engine.shared.rss import RSSParser
from engine.shared.scheduler import SchedulerManager

from engine.macro.collectors.calendar.collector import CalendarCollector
from engine.macro.collectors.central_bank.collector import CentralBankCollector
from engine.macro.collectors.cot.collector import COTCollector
from engine.macro.collectors.dxy.collector import DXYCollector
from engine.macro.collectors.economic_data.collector import EconomicDataCollector
from engine.macro.collectors.intermarket.collector import IntermarketCollector
from engine.macro.collectors.sentiment.collector import SentimentCollector
from engine.macro.providers.calendar.investing_rss import (
    InvestingRSSCalendarProvider,
)
from engine.macro.providers.central_bank.boc_rss import BOCRSSProvider
from engine.macro.providers.central_bank.boe_rss import BOERSSProvider
from engine.macro.providers.central_bank.boj_rss import BOJRSSProvider
from engine.macro.providers.central_bank.ecb_rss import ECBRSSProvider
from engine.macro.providers.central_bank.fed_rss import FedRSSProvider
from engine.macro.providers.central_bank.rba_rss import RBARSSProvider
from engine.macro.providers.central_bank.rbnz_rss import RBNZRSSProvider
from engine.macro.providers.central_bank.snb_rss import SNBRSSProvider
from engine.macro.providers.cot.cftc_dea import CFTCDEAProvider
from engine.macro.providers.economic_data.fred import FREDEconomicProvider
from engine.macro.providers.economic_data.oecd import OECDEconomicProvider
from engine.macro.providers.market_data.commodity_proxy import CommodityProxyProvider
from engine.macro.providers.market_data.twelve_data import TwelveDataProvider
from engine.macro.providers.registry import ProviderRegistry
from engine.macro.providers.sentiment.cot_derived import COTDerivedSentimentProvider


from engine.ta.broker.twelve_data.client import TwelveDataClient
from engine.ta.broker.twelve_data.config import TwelveDataConfig
from engine.ta.common.analyzers.candles import CandleAnalyzer
from engine.ta.common.analyzers.swings import SwingAnalyzer
from engine.ta.common.analyzers.fibonacci import FibonacciAnalyzer
from engine.ta.common.analyzers.marubozu import MarubozuAnalyzer
from engine.ta.common.analyzers.compression import CompressionAnalyzer
from engine.ta.common.analyzers.liquidity import LiquidityAnalyzer
from engine.ta.common.analyzers.sweeps import SweepAnalyzer
from engine.ta.common.analyzers.session import SessionAnalyzer
from engine.ta.common.analyzers.dealing_range import DealingRangeAnalyzer
from engine.ta.common.services.snapshot.builder import SnapshotBuilder
from engine.ta.common.services.alignment.service import AlignmentService
from engine.ta.common.timeframe.manager import TimeframeManager
from engine.ta.smc.config import SMCConfig
from engine.ta.smc.detector import SMCDetector
from engine.ta.snd.config import SnDConfig
from engine.ta.snd.detector import SnDDetector
from engine.ta.storage.uow import ta_uow_factory, ta_read_uow_factory
from engine.ta.orchestrator import TAOrchestrator

from engine.config import get_rag_config
from engine.rag.embeddings.factory import create_embedding_provider
from engine.rag.embeddings.pipeline import EmbeddingPipeline
from engine.rag.ingest.pipeline import IngestPipeline
from engine.rag.orchestrator import RAGOrchestrator
from engine.rag.retrieval.reranker import Reranker
from engine.rag.retrieval.retriever import Retriever
from engine.rag.scenarios.matcher import ScenarioMatcher
from engine.rag.services.audit import AuditService
from engine.rag.services.bootstrap import BootstrapService
from engine.rag.services.health import HealthService
from engine.rag.services.reembed import ReembedService
from engine.rag.services.sync import SyncService
from engine.rag.services.versioning import VersioningService
from engine.rag.storage.uow import rag_uow_factory
from engine.rag.vectorstore.factory import create_vector_store

from engine.processor.config import ProcessorConfig, get_processor_config
from engine.processor.llm.factory import create_llm_client
from engine.processor.service import AnalysisProcessor
from engine.processor.storage.uow import processor_uow_factory
from engine.processor.storage.repositories.analysis_repository import AnalysisRepository
from engine.processor.storage.repositories.audit_repository import AuditRepository

from engine.shared.logging import get_logger

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Background LLM cache entry
# ---------------------------------------------------------------------------


from dataclasses import dataclass as _dataclass


@_dataclass(frozen=True)
class _BackgroundLLMCacheEntry:
    """One entry in Container._user_background_llm.

    Carries the resolved client and config plus the (role, tier,
    used_platform) tuple the client was built against. On the next
    load_llm_client_for_background() call we compare the requesting
    (role, tier) against this snapshot; a mismatch means the user's
    eligibility changed and the entry must be rebuilt.

    used_platform is an operator-observability flag only — it does
    not affect cache hit/miss because a user who flips between
    personal-key and platform-key always also crosses through an
    invalidate_user_background_llm() call on the connection-mutation
    route, which clears the entry outright.
    """

    client: object  # LLMClient (untyped here to avoid an import cycle)
    config: object  # ProcessorConfig
    role: str
    tier: str
    used_platform: bool


class Container:
    def __init__(self) -> None:
        self.settings = get_settings()
        s = self.settings

        self.db = DatabaseManager(
            url=s.async_database_url,
            pool_size=s.db_pool_size,
            max_overflow=s.db_max_overflow,
            pool_timeout=s.db_pool_timeout,
            pool_recycle=s.db_pool_recycle,
            echo=s.db_echo,
        )
        self.cache = RedisCache(
            url=str(s.redis_url),
            max_connections=s.redis_max_connections,
            socket_timeout=s.redis_socket_timeout,
            socket_connect_timeout=s.redis_socket_connect_timeout,
        )
        # Engine -> gateway alert event bridge over Redis pub/sub. One
        # instance per Container; injected into AnalysisProcessor at every
        # construction site so the BYOK retry-exhausted branch can publish
        # LLM_PROVIDER_QUOTA_EXCEEDED. Stateless beyond self.cache; no
        # explicit close needed (the underlying RedisCache.close in
        # Container.shutdown releases the transport). Audit ref:
        # ADMIN-QUOTA-9.
        self.alert_publisher = AlertPublisher(self.cache)
        self.http_client = HttpClient(
            timeout_seconds=s.http_timeout_seconds,
            max_retries=s.http_max_retries,
            backoff_base=s.http_retry_backoff_base,
            backoff_max=s.http_retry_backoff_max,
            cb_failure_threshold=s.circuit_breaker_failure_threshold,
            cb_recovery_timeout=s.circuit_breaker_recovery_timeout,
            cb_half_open_max=s.circuit_breaker_half_open_max_calls,
            ssl_ca_bundle_path=s.ssl_ca_bundle_path,
            ssl_verify=s.ssl_verify,
        )
        self.rss_parser = RSSParser(self.http_client)
        self.scheduler = SchedulerManager()

        # Coordinator for opaque background work owned by the engine
        # (chart pre-warm, stale-while-revalidate refreshes). Centralised
        # so the FastAPI lifespan can cancel every spawned task on
        # shutdown without each call site having to track its own task
        # references. See engine.shared.concurrency for the contract.
        self.background_tasks = BackgroundTaskCoordinator()

        self.registry = ProviderRegistry()
        self._build_providers()
        self._build_collectors()

        self._build_ta_configs()
        self._build_ta_repositories()
        self._build_ta_analyzers()
        self._build_ta_services()
        self._build_smc_framework()
        self._build_snd_framework()
        self._build_ta_orchestrator()

        self.rag_config = get_rag_config()

        # Per-user LLM processor cache. Keyed by user_id.
        # Invalidated when user changes their LLM connection.
        self._user_processors: dict[str, AnalysisProcessor] = {}

        # Per-user LLM client cache for BACKGROUND generators
        # (trading-plan + performance-review). Keyed by user_id;
        # each value is a _BackgroundLLMCacheEntry tuple recording
        # the role+tier the client was resolved against so a stale
        # entry built when the user had a different tier is
        # transparently replaced on the next request. Generators
        # MUST NOT close the returned client — the cache owns the
        # lifecycle and Container.shutdown() closes every entry on
        # process exit. Mirrors the existing _user_processors
        # pattern so the analysis and background paths share the
        # same ownership semantics.
        self._user_background_llm: dict[str, _BackgroundLLMCacheEntry] = {}

        # Per-user broker client cache. Keyed by user_id.
        # Invalidated when user changes their broker connection.
        # Section 5 (CHECKLIST): backed by BrokerClientPool which adds
        # per-key construction lock + idle eviction + metrics. The
        # dict above is kept only as a (user_id -> (provider, account_id))
        # index so invalidate_user_broker can translate user_id to
        # pool key without re-reading the database.
        from engine.ta.broker.mt5.client_pool import BrokerClientPool

        import os as _os
        _pool_idle = float(_os.environ.get("ENGINE_BROKER_POOL_IDLE_TIMEOUT_SECS", "600") or 600)
        _pool_sweep = float(_os.environ.get("ENGINE_BROKER_POOL_SWEEP_INTERVAL_SECS", "60") or 60)
        self.broker_client_pool = BrokerClientPool(
            idle_timeout_secs=_pool_idle if _pool_idle > 0 else 600.0,
            sweep_interval_secs=_pool_sweep if _pool_sweep > 0 else 60.0,
        )
        # Tracks user_id -> (provider, account_id) so we know which
        # pool entry to evict when invalidate_user_broker is called.
        # NOT a client cache - the pool is the source of truth.
        self._user_broker_keys: dict[str, tuple[str, str]] = {}
        # Retained ONLY for backwards-compat with code paths that
        # historically read this dict directly. New code MUST go
        # through broker_client_pool. Removed in the next MR after a
        # full audit confirms no external reads remain.
        self._user_brokers: dict[str, BrokerBase] = {}

    def _build_providers(self) -> None:
        s = self.settings
        h = self.http_client
        r = self.rss_parser

        self.fed_provider = FedRSSProvider(r, feed_url=s.fed_rss_url)
        self.ecb_provider = ECBRSSProvider(r, feed_url=s.ecb_rss_url)
        self.boe_provider = BOERSSProvider(r, feed_url=s.boe_rss_url)
        self.boj_provider = BOJRSSProvider(r, feed_url=s.boj_rss_url)
        self.rba_provider = RBARSSProvider(r, feed_url=s.rba_rss_url)
        self.boc_provider = BOCRSSProvider(r, feed_url=s.boc_rss_url)
        self.rbnz_provider = RBNZRSSProvider(r, feed_url=s.rbnz_rss_url)
        self.snb_provider = SNBRSSProvider(r, feed_url=s.snb_rss_url)
        for p in (
            self.fed_provider,
            self.ecb_provider,
            self.boe_provider,
            self.boj_provider,
            self.rba_provider,
            self.boc_provider,
            self.rbnz_provider,
            self.snb_provider,
        ):
            self.registry.register(p)

        self.cftc_dea_provider = CFTCDEAProvider(
            h,
            url=s.cftc_dea_url,
        )
        self.registry.register(self.cftc_dea_provider)

        self.fred_provider = FREDEconomicProvider(
            h,
            base_url=s.fred_base_url,
            api_key=s.fred_api_key,
        )
        self.oecd_provider = OECDEconomicProvider(
            h,
            base_url=s.oecd_api_base_url,
        )
        for p in (self.fred_provider, self.oecd_provider):
            self.registry.register(p)

        self.twelve_data_provider = TwelveDataProvider(
            h,
            base_url=s.twelvedata_base_url,
            api_key=s.twelvedata_api_key,
        )
        self.commodity_proxy_provider = CommodityProxyProvider(
            h,
            iron_ore_url=s.iron_ore_price_url,
            dairy_gdt_url=s.dairy_gdt_price_url,
        )
        for p in (self.twelve_data_provider, self.commodity_proxy_provider):
            self.registry.register(p)

        self.investing_cal_provider = InvestingRSSCalendarProvider(
            r,
            feed_url=s.investing_calendar_rss_url,
        )
        self.registry.register(self.investing_cal_provider)

    def _build_collectors(self) -> None:
        s = self.settings
        c = self.cache
        d = self.db

        self.cb_collector = CentralBankCollector(
            [
                self.fed_provider,
                self.ecb_provider,
                self.boe_provider,
                self.boj_provider,
                self.rba_provider,
                self.boc_provider,
                self.rbnz_provider,
                self.snb_provider,
            ],
            c,
            d,
        )
        self.cb_collector.cache_ttl = s.cache_ttl_central_bank

        self.cot_collector = COTCollector([self.cftc_dea_provider], c, d)
        self.cot_collector.cache_ttl = s.cache_ttl_cot

        self.economic_collector = EconomicDataCollector(
            [self.fred_provider, self.oecd_provider],
            c,
            d,
        )
        self.economic_collector.cache_ttl = s.cache_ttl_economic_data

        self.calendar_collector = CalendarCollector([self.investing_cal_provider], c, d)
        self.calendar_collector.cache_ttl = s.cache_ttl_calendar

        self.dxy_collector = DXYCollector(
            [self.twelve_data_provider],
            c,
            d,
        )
        self.dxy_collector.cache_ttl = s.cache_ttl_dxy

        self.intermarket_collector = IntermarketCollector(
            [self.twelve_data_provider, self.commodity_proxy_provider],
            c,
            d,
        )
        self.intermarket_collector.cache_ttl = s.cache_ttl_intermarket

        self.cot_sentiment_provider = COTDerivedSentimentProvider(c)
        self.registry.register(self.cot_sentiment_provider)

        self.sentiment_collector = SentimentCollector(
            [self.cot_sentiment_provider],
            c,
            d,
        )
        self.sentiment_collector.cache_ttl = s.cache_ttl_sentiment

    def _build_ta_configs(self) -> None:
        from engine.config import TAConfig
        from engine.ta.broker.mt5.config import MT5Config

        self.ta_config = TAConfig()
        self.mt5_config = MT5Config()
        self.smc_config = SMCConfig()
        self.snd_config = SnDConfig()

        # Twelve Data fallback is always available for market data
        # (public API, not user-specific). Used as a data fallback
        # when the user's primary broker fails to return candles.
        s = self.settings
        self.twelve_data_client = None
        try:
            twelve_config = TwelveDataConfig(
                api_key=s.twelvedata_api_key,
                base_url=s.twelvedata_base_url,
            )
            self.twelve_data_client = TwelveDataClient(
                config=twelve_config,
                http_client=self.http_client,
                cache=self.cache,
            )
        except Exception as exc:
            _logger.warning(
                "twelve_data_client_creation_failed",
                extra={"error": str(exc)},
            )



    def _build_ta_repositories(self) -> None:
        self.ta_uow_factory = ta_uow_factory(self.db)
        self.ta_read_uow_factory = ta_read_uow_factory(self.db)

    def _build_ta_analyzers(self) -> None:
        self.candle_analyzer = CandleAnalyzer()
        self.swing_analyzer = SwingAnalyzer()
        self.fibonacci_analyzer = FibonacciAnalyzer()
        # Wire SnD config values into MarubozuAnalyzer so .env
        # settings (SND_MARUBOZU_BODY_PERCENTAGE_THRESHOLD,
        # SND_MARUBOZU_MAX_WICK_PERCENTAGE) are respected.
        self.marubozu_analyzer = MarubozuAnalyzer(
            min_body_percentage=self.snd_config.marubozu_body_percentage_threshold,
            max_wick_percentage=self.snd_config.marubozu_max_wick_percentage,
        )
        self.compression_analyzer = CompressionAnalyzer()
        self.liquidity_analyzer = LiquidityAnalyzer()
        self.sweep_analyzer = SweepAnalyzer()
        self.session_analyzer = SessionAnalyzer()
        self.dealing_range_analyzer = DealingRangeAnalyzer()

    def _build_ta_services(self) -> None:
        self.timeframe_manager = TimeframeManager()
        self.snapshot_builder = SnapshotBuilder(
            swing_analyzer=self.swing_analyzer,
            session_analyzer=self.session_analyzer,
            liquidity_analyzer=self.liquidity_analyzer,
            sweep_analyzer=self.sweep_analyzer,
            fibonacci_analyzer=self.fibonacci_analyzer,
            dealing_range_analyzer=self.dealing_range_analyzer,
        )
        self.alignment_service = AlignmentService(
            require_trend_alignment=True,
            require_zone_nesting=False,
        )

    def _build_smc_framework(self) -> None:
        self.smc_detector = SMCDetector(
            config=self.smc_config,
            candle_analyzer=self.candle_analyzer,
            swing_analyzer=self.swing_analyzer,
            session_analyzer=self.session_analyzer,
            liquidity_analyzer=self.liquidity_analyzer,
            sweep_analyzer=self.sweep_analyzer,
            fibonacci_analyzer=self.fibonacci_analyzer,
            dealing_range_analyzer=self.dealing_range_analyzer,
        )

    def _build_snd_framework(self) -> None:
        self.snd_detector = SnDDetector(
            config=self.snd_config,
            candle_analyzer=self.candle_analyzer,
            swing_analyzer=self.swing_analyzer,
            marubozu_analyzer=self.marubozu_analyzer,
            compression_analyzer=self.compression_analyzer,
            fibonacci_analyzer=self.fibonacci_analyzer,
        )

    def _build_ta_orchestrator(self) -> None:
        """Build the TA orchestrator.

        broker_client is None because in multi-tenant mode, the broker
        is resolved per-request from the user's DB connection. The
        orchestrator's analyze() method requires broker_client as a
        keyword argument from the caller. The instance-level
        broker_client is never used at runtime.
        """
        self.ta_orchestrator = TAOrchestrator(
            broker_client=None,
            ta_uow_factory=self.ta_uow_factory,
            ta_read_uow_factory=self.ta_read_uow_factory,
            smc_detector=self.smc_detector,
            snd_detector=self.snd_detector,
            snapshot_builder=self.snapshot_builder,
            alignment_service=self.alignment_service,
            timeframe_manager=self.timeframe_manager,
            ta_config=self.ta_config,
            fallback_client=self.twelve_data_client,
        )

    # -- Broker connection management (async, requires DB) ---------------------

    async def build_broker(self) -> None:
        """Initialize broker infrastructure.

        Called from the FastAPI lifespan after the database is ready.
        In multi-tenant mode, every user (including admin) configures
        their own broker connection via the dashboard. There is no
        platform-level broker. Per-user broker connections are resolved
        at request time via load_user_broker(user_id).
        """
        _logger.info(
            "broker_startup",
            extra={
                "mode": "multi_tenant",
                "action": "Per-user broker connections resolved at request time.",
            },
        )

    async def load_user_broker(self, user_id: str):
        """Load the active broker connection for a specific user.

        Section 5 (CHECKLIST): routed through BrokerClientPool so
        concurrent first-touches for the same user collapse into ONE
        client (the previous implementation built a new client per
        concurrent caller, racing on the EA's single REP socket).

        Returns a BrokerBase instance or None.
        """
        # Pre-resolve the active connection metadata so we can key the
        # pool by (provider, account_id). This MUST happen before
        # pool.get() because the pool needs a deterministic key.
        cached_key = self._user_broker_keys.get(user_id)
        if cached_key is not None:
            provider, account_id = cached_key
            # Fast path: pool already has it.
            existing = self.broker_client_pool._entries.get((provider, account_id))
            if existing is not None:
                return existing.client
            # Pool evicted (idle); drop the stale key and fall through.
            self._user_broker_keys.pop(user_id, None)

        # Resolve the row first so we know the pool key. This single
        # DB hit replaces the unbounded per-user dict.
        row_meta = await self._resolve_broker_row_meta(user_id)
        if row_meta is None:
            return None
        provider, account_id = row_meta

        async def _factory():
            client = await self._load_active_broker_connection(user_id)
            if client is None:
                raise RuntimeError(
                    f"broker connection vanished between metadata fetch and construction for user_id={user_id}"
                )
            return client

        client = await self.broker_client_pool.get(provider, account_id, _factory)
        self._user_broker_keys[user_id] = (provider, account_id)
        return client

    async def _resolve_broker_row_meta(self, user_id: str) -> Optional[tuple[str, str]]:
        """Read the active broker_connections row JUST to get the pool
        key (provider, account_id). Cheap; one indexed lookup.
        """
        try:
            from engine.processor.storage.repositories.broker_connection_repository import (
                BrokerConnectionRepository,
            )

            async with self.db.read_session() as session:
                repo = BrokerConnectionRepository(session)
                row = await repo.get_active(user_id=user_id)
            if row is None:
                return None
            if row.connection_type == "ea":
                return ("zmq-ea", f"{row.ea_host}:{row.ea_port}")
            if row.connection_type == "hosted":
                return ("zmq-hosted", row.hosted_container_id or "unknown")
            if row.connection_type == "metaapi":
                return ("metaapi", row.metaapi_account_id or "unknown")
            return None
        except Exception as exc:
            _logger.warning(
                "failed_to_resolve_broker_row_meta",
                extra={"error": str(exc), "user_id": user_id},
            )
            return None

    async def invalidate_user_broker(self, user_id: str) -> None:
        """Invalidate the cached broker connection for a user.

        Section 5 (CHECKLIST): routes through BrokerClientPool.evict
        so the cached client is closed AND the pool size metric is
        updated atomically.
        """
        # Drop the legacy dict entry too so any straggler reader sees
        # consistent state.
        self._user_brokers.pop(user_id, None)
        key = self._user_broker_keys.pop(user_id, None)
        if key is not None:
            provider, account_id = key
            await self.broker_client_pool.evict(
                provider, account_id, reason="explicit"
            )
            _logger.info(
                "user_broker_invalidated",
                extra={"user_id": user_id, "provider": provider},
            )

    async def _load_active_broker_connection(self, user_id: str):
        """Load the active broker connection from the database.

        Returns a BrokerBase instance built from the saved connection,
        or None if no active connection exists.

        For MetaAPI connections, uses the platform-level token from
        the MT5_METAAPI_TOKEN env var (NOT a per-row encrypted token).
        For EA connections, decrypts the EA auth token from the DB row.
        """
        try:
            from engine.processor.storage.repositories.broker_connection_repository import (
                BrokerConnectionRepository,
                decrypt_credential,
            )
            from engine.ta.broker.mt5.factory import create_mt5_broker_from_connection

            async with self.db.read_session() as session:
                repo = BrokerConnectionRepository(session)
                row = await repo.get_active(user_id=user_id)

            if row is None:
                _logger.debug("no_active_broker_connection_in_db", extra={"user_id": user_id})
                return None

            # Decrypt EA auth token if applicable.
            ea_auth_token = ""
            if row.connection_type == "ea" and row.ea_auth_token_encrypted:
                ea_auth_token = decrypt_credential(row.ea_auth_token_encrypted)

            # Platform-level MetaAPI token from env (never from DB).
            platform_token = ""
            if row.connection_type == "metaapi":
                import os
                platform_token = os.environ.get("MT5_METAAPI_TOKEN", "")

            client = create_mt5_broker_from_connection(
                row=row,
                http_client=self.http_client,
                ea_auth_token=ea_auth_token,
                platform_token=platform_token,
            )

            _logger.info(
                "loaded_active_broker_connection_from_db",
                extra={
                    "connection_id": str(row.id),
                    "type": row.connection_type,
                    "name": row.name,
                },
            )
            return client

        except Exception as exc:
            _logger.warning(
                "failed_to_load_broker_connection_from_db",
                extra={"error": str(exc)},
            )
            return None

    # -- RAG -------------------------------------------------------------------

    async def build_rag(self) -> None:
        rc = self.rag_config

        uow_factory = rag_uow_factory(self.db)

        self.rag_vector_store = create_vector_store(config=rc)

        self.rag_embedding_provider = create_embedding_provider(
            config=rc,
            http_client=self.http_client,
        )

        self.rag_embedding_pipeline = EmbeddingPipeline(
            config=rc,
            provider=self.rag_embedding_provider,
            uow_factory=uow_factory,
        )

        self.rag_ingest_pipeline = IngestPipeline(
            config=rc,
            uow_factory=uow_factory,
        )

        self.rag_retriever = Retriever(
            config=rc,
            vector_store=self.rag_vector_store,
            embedding_provider=self.rag_embedding_provider,
        )

        self.rag_reranker = Reranker(config=rc)

        self.rag_scenario_matcher = ScenarioMatcher(
            uow_factory=uow_factory,
        )

        self.rag_audit_service = AuditService(
            uow_factory=uow_factory,
        )

        self.rag_versioning_service = VersioningService(
            uow_factory=uow_factory,
        )

        self.rag_reembed_service = ReembedService(
            uow_factory=uow_factory,
            embedding_pipeline=self.rag_embedding_pipeline,
            vector_store=self.rag_vector_store,
            collection=rc.collection_documents,
        )

        self.rag_sync_service = SyncService(
            uow_factory=uow_factory,
            vector_store=self.rag_vector_store,
            collection=rc.collection_documents,
        )

        self.rag_bootstrap_service = BootstrapService(
            config=rc,
            uow_factory=uow_factory,
            vector_store=self.rag_vector_store,
            ingest_pipeline=self.rag_ingest_pipeline,
            reembed_service=self.rag_reembed_service,
            versioning_service=self.rag_versioning_service,
        )

        self.rag_health_service = HealthService(
            config=rc,
            vector_store=self.rag_vector_store,
            db=self.db,
            embedding_provider=self.rag_embedding_provider,
        )

        self.rag_orchestrator = RAGOrchestrator(
            config=rc,
            retriever=self.rag_retriever,
            reranker=self.rag_reranker,
            scenario_matcher=self.rag_scenario_matcher,
            audit_service=self.rag_audit_service,
            uow_factory=uow_factory,
        )

    # -- Processor (LLM) ------------------------------------------------------

    async def build_processor(self) -> None:
        """Build the Processor LLM service from environment variables.

        Called at startup. Uses env-var configuration as the system
        default. Per-user LLM connections are resolved at request time
        via load_user_llm_config(user_id).

        Supports Anthropic, OpenAI, Gemini, and any OpenAI-compatible
        self-hosted endpoint. Must be called after build_rag() since
        the processor persists audit data to the same database.
        """
        self.processor_uow_factory = processor_uow_factory(self.db)

        # At startup, use env-var configuration only. The startup
        # processor is only ever used as the platform-key baseline
        # (admin / pro_managed fallback when no personal row exists),
        # so the platform-key flag is True here. Per-user processors
        # built later via resolve_user_processor() get the correct
        # platform/BYOK flag from _processor_config_from_row().
        startup_cfg = get_processor_config()
        self.processor_config = startup_cfg.model_copy(
            update={"uses_platform_key": True}
        )

        self.processor_llm_client = create_llm_client(
            config=self.processor_config,
        )

        self.processor = AnalysisProcessor(
            config=self.processor_config,
            llm_client=self.processor_llm_client,
            uow_factory=self.processor_uow_factory,
            cache=self.cache,
            alert_publisher=self.alert_publisher,
        )

    async def resolve_user_processor(self, user: "AuthenticatedUser") -> "AnalysisProcessor":
        """Resolve the authenticated user's LLM processor.

        Uses a per-user cache to avoid rebuilding the LLM client on
        every request. The cache is invalidated when the user changes
        their LLM connection via the dashboard.

        Resolution order:
          1. Cached processor for this user -> return immediately
          2. Active LLM connection from DB -> build, cache, return
          3. If user is pro_managed and no DB connection, use platform env-var fallback.
          4. No connection configured (and not pro_managed) -> raise.

        Every user MUST configure their own LLM connection unless they
        are subscribed to the pro_managed tier.
        """
        # Check cache first.
        cached = self._user_processors.get(user.user_id)
        if cached is not None:
            return cached

        # Build from DB.
        user_config = await self._load_active_llm_connection(user)
        if user_config is None:
            # Tier-aware message so pro_byok users see why their request
            # was rejected; everyone else gets the generic guidance.
            if user.tier == "pro_byok":
                raise ValueError(
                    "Pro BYOK requires your own LLM API key. "
                    "Please add a connection on the LLM Settings page, "
                    "or upgrade to Pro Managed to use the platform key."
                )
            raise ValueError(
                "No LLM connection configured. "
                "Please set up an LLM connection via the dashboard."
            )

        user_llm_client = create_llm_client(user_config)
        user_processor = AnalysisProcessor(
            config=user_config,
            llm_client=user_llm_client,
            uow_factory=self.processor_uow_factory,
            cache=self.cache,
            alert_publisher=self.alert_publisher,
        )

        self._user_processors[user.user_id] = user_processor

        _logger.info(
            "user_processor_cached",
            extra={
                "user_id": user.user_id,
                "provider": user_config.llm_provider,
                "model": user_config.model_name,
            },
        )
        return user_processor

    async def invalidate_user_processor(self, user_id: str) -> None:
        """Invalidate the cached processor for a user.

        Called when the user activates, updates, deactivates, or deletes
        their LLM connection. The next call to resolve_user_processor()
        will rebuild from the DB.
        """
        old_processor = self._user_processors.pop(user_id, None)
        if old_processor is not None:
            try:
                await old_processor._llm.close()
            except Exception:
                pass
            _logger.info(
                "user_processor_invalidated",
                extra={"user_id": user_id},
            )

    async def load_user_llm_config(self, user: "AuthenticatedUser") -> "ProcessorConfig | None":
        """Load the active LLM connection for a specific user.

        Called at request time. Returns a ProcessorConfig built from
        the user's saved connection, or None.
        """
        return await self._load_active_llm_connection(user)

    # -- LLM connection -> ProcessorConfig (shared helpers) -----------------

    @staticmethod
    def _processor_config_from_row(row, *, is_platform: bool) -> "ProcessorConfig":
        """Build a ProcessorConfig from a saved llm_connections row.

        Used by both the analysis-path resolver and the background
        generators. The connection fields (provider, model, key,
        temperature, max_output_tokens, base_url) come from the row;
        every operational field (timeouts, retry policy, validation,
        audit flags) is carried forward from the env-var config so
        per-row tweaks cannot accidentally weaken the platform's
        operational guarantees.

        is_platform is logged for observability so a platform-row
        load is distinguishable from a personal-row load. The two
        branches build the SAME ProcessorConfig shape — a missing
        per-provider API key on the env baseline is overridden by
        the row's decrypted key for the row's provider.
        """
        from engine.processor.storage.repositories.llm_connection_repository import (
            decrypt_api_key,
        )
        from pydantic import SecretStr

        api_key = decrypt_api_key(row.api_key_encrypted)
        env_cfg = get_processor_config()

        overrides: dict = {
            "llm_provider": row.provider,
            "model_name": row.model_name,
            "temperature": row.temperature,
            "max_output_tokens": row.max_output_tokens,
            # Carry forward operational settings from env.
            "llm_timeout_seconds": env_cfg.llm_timeout_seconds,
            "total_timeout_seconds": env_cfg.total_timeout_seconds,
            "max_retries": env_cfg.max_retries,
            "retry_backoff_base_seconds": env_cfg.retry_backoff_base_seconds,
            "retry_backoff_max_seconds": env_cfg.retry_backoff_max_seconds,
            "strict_schema_validation": env_cfg.strict_schema_validation,
            "require_citations": env_cfg.require_citations,
            "persist_audit_logs": env_cfg.persist_audit_logs,
            "log_raw_llm_response": env_cfg.log_raw_llm_response,
            # Default all provider keys to env values so a different
            # provider's key remains intact for inert validation.
            "anthropic_api_key": env_cfg.anthropic_api_key,
            "openai_api_key": env_cfg.openai_api_key,
            "gemini_api_key": env_cfg.gemini_api_key,
            "self_hosted_api_key": env_cfg.self_hosted_api_key,
            "api_base_url": row.base_url or env_cfg.api_base_url,
        }

        key_field = f"{row.provider}_api_key"
        if key_field in overrides:
            overrides[key_field] = SecretStr(api_key)

        # Carry the platform/BYOK origin down to service.py so it can
        # decide whether to call the gateway's metering layer. Personal
        # rows (is_platform=False) bypass metering entirely because the
        # user pays their own provider bill.
        overrides["uses_platform_key"] = is_platform

        cfg = ProcessorConfig(**overrides)
        _logger.info(
            "processor_config_built_from_row",
            extra={
                "is_platform": is_platform,
                "provider": row.provider,
                "model": row.model_name,
                "connection_id": str(row.id),
            },
        )
        return cfg

    async def _load_platform_processor_config(self) -> "ProcessorConfig":
        """Return the platform LLM ProcessorConfig.

        Resolution order (single source of truth for every caller
        that wants the platform key):

          1. The active platform row in llm_connections
             (is_platform=true). Hot-reloadable: an admin can
             rotate the platform key from the dashboard without
             a container restart.
          2. Env-var configuration. Static fallback used when no
             platform row exists (fresh install, or admin
             explicitly deleted the row).
        """
        from engine.processor.storage.repositories.llm_connection_repository import (
            LLMConnectionRepository,
        )

        async with self.db.read_session() as session:
            repo = LLMConnectionRepository(session)
            platform_row = await repo.get_platform()

        if platform_row is not None:
            return self._processor_config_from_row(
                platform_row, is_platform=True
            )
        _logger.info("using_platform_llm_from_env")
        # Env-var fallback IS the platform key by definition (this branch
        # is only reached for admin / pro_managed users with no saved
        # connection). Mark the config accordingly so service.py keeps
        # metering enabled for it.
        env_cfg = get_processor_config()
        return env_cfg.model_copy(update={"uses_platform_key": True})

    @staticmethod
    def _is_eligible_for_platform_fallback(role: str, tier: str) -> bool:
        """Tier policy for platform-key fallback.

        Centralised so every caller (analysis path, trading-plan
        background, performance-review background) uses the SAME
        rule. Currently:

          - role == 'admin'           -> always eligible
          - tier == 'pro_managed'     -> eligible (the managed tier
                                         is what users pay for in
                                         exchange for the platform
                                         covering LLM costs)
          - everyone else             -> not eligible; must BYOK
        """
        if (role or "").strip().lower() == "admin":
            return True
        if (tier or "").strip().lower() == "pro_managed":
            return True
        return False

    # -- Analysis-path resolver (request-scoped, has AuthenticatedUser) ----

    async def _load_active_llm_connection(self, user: "AuthenticatedUser") -> "ProcessorConfig | None":
        """Load the active LLM connection from the database for a user.

        Tier policy (defense-in-depth):
          - admin or pro_managed with NO saved connection -> platform key
            (DB row first, env-var fallback).
          - pro_byok or any other tier with no saved connection -> None,
            the caller raises a tier-aware 503 telling the user to add
            their own key in the dashboard.
          - any user with a saved connection -> use the saved key,
            regardless of tier.
        """
        try:
            from engine.processor.storage.repositories.llm_connection_repository import (
                LLMConnectionRepository,
            )

            async with self.db.read_session() as session:
                repo = LLMConnectionRepository(session)
                row = await repo.get_active(user_id=user.user_id)

            if row is not None:
                return self._processor_config_from_row(row, is_platform=False)

            if self._is_eligible_for_platform_fallback(user.role, user.tier):
                _logger.info(
                    "falling_back_to_platform_llm",
                    extra={"user_id": user.user_id, "tier": user.tier},
                )
                return await self._load_platform_processor_config()

            _logger.info(
                "no_active_llm_connection_in_db_for_byok",
                extra={"user_id": user.user_id, "tier": user.tier},
            )
            return None

        except Exception as exc:
            _logger.warning(
                "failed_to_load_llm_connection_from_db",
                extra={"error": str(exc), "user_id": user.user_id},
            )
            return None

    # -- Background-path resolver (no AuthenticatedUser; role+tier strings) -

    async def load_llm_client_for_background(
        self,
        user_id: str,
        *,
        role: str,
        tier: str,
        allow_platform_fallback: bool,
    ) -> tuple[Optional["LLMClient"], Optional["ProcessorConfig"]]:
        """Resolve (and cache) the LLM client for a background generator.

        This is the single entry point for both the trading-plan and
        performance-review generators. It honors the same tier policy
        as the analysis path but takes role + tier as plain strings
        (forwarded by the gateway in the dispatch body) so the engine
        does not need an AuthenticatedUser.

        Resolution + caching:

          1. Cache hit  (entry exists for user_id AND its (role, tier)
             match the request) -> return the cached client without
             any DB read. The cache value lives until either
             invalidate_user_background_llm(user_id) fires (on every
             LLM-connection mutation route) or the user's role/tier
             changes (a subsequent call with different role/tier
             will fall through to the build path and replace the
             stale entry).
          2. Personal LLM connection on llm_connections for user_id
             -> build a client from the saved key (regardless of tier).
          3. No personal connection AND allow_platform_fallback is
             True AND the (role, tier) pair is eligible (admin or
             pro_managed) -> build a client from the platform row
             (or env-var processor config when no platform row
             exists).
          4. Anything else -> (None, None) so the generator can
             surface the right tier-aware CTA.

        allow_platform_fallback is a per-feature switch so the
        performance-review generator can still hold the strict
        BYOK-or-managed line (no platform fallback for free /
        pro_byok tiers) without duplicating the policy.

        Ownership: the cache owns the returned client. Callers MUST
        NOT close it. Container.shutdown() closes every cached entry
        on process exit; invalidate_user_background_llm() closes the
        specific entry on every connection-mutation route.
        """
        # -- 1. Cache hit fast path --------------------------------------
        cached = self._user_background_llm.get(user_id)
        if cached is not None and cached.role == role and cached.tier == tier:
            return cached.client, cached.config  # type: ignore[return-value]

        # If we have a stale entry (same user_id, different role/tier),
        # close it before rebuilding so we never leak an HTTP pool.
        if cached is not None:
            try:
                await cached.client.close()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._user_background_llm.pop(user_id, None)
            _logger.info(
                "background_llm_client_evicted_stale",
                extra={
                    "user_id": user_id,
                    "old_role": cached.role,
                    "old_tier": cached.tier,
                    "new_role": role,
                    "new_tier": tier,
                },
            )

        try:
            from engine.processor.storage.repositories.llm_connection_repository import (
                LLMConnectionRepository,
            )

            async with self.db.read_session() as session:
                repo = LLMConnectionRepository(session)
                row = await repo.get_active(user_id=user_id)

            if row is not None:
                cfg = self._processor_config_from_row(row, is_platform=False)
                client = create_llm_client(config=cfg)
                self._user_background_llm[user_id] = _BackgroundLLMCacheEntry(
                    client=client,
                    config=cfg,
                    role=role,
                    tier=tier,
                    used_platform=False,
                )
                _logger.info(
                    "background_llm_client_built_personal",
                    extra={
                        "user_id": user_id,
                        "provider": row.provider,
                        "model": row.model_name,
                        "role": role,
                        "tier": tier,
                    },
                )
                return client, cfg

            if not allow_platform_fallback:
                _logger.info(
                    "background_llm_client_personal_required",
                    extra={
                        "user_id": user_id,
                        "role": role,
                        "tier": tier,
                    },
                )
                return None, None

            if not self._is_eligible_for_platform_fallback(role, tier):
                _logger.info(
                    "background_llm_client_not_eligible_for_platform",
                    extra={
                        "user_id": user_id,
                        "role": role,
                        "tier": tier,
                    },
                )
                return None, None

            cfg = await self._load_platform_processor_config()
            client = create_llm_client(config=cfg)
            self._user_background_llm[user_id] = _BackgroundLLMCacheEntry(
                client=client,
                config=cfg,
                role=role,
                tier=tier,
                used_platform=True,
            )
            _logger.info(
                "background_llm_client_built_platform",
                extra={
                    "user_id": user_id,
                    "provider": cfg.llm_provider,
                    "model": cfg.model_name,
                    "role": role,
                    "tier": tier,
                },
            )
            return client, cfg

        except Exception as exc:
            _logger.warning(
                "failed_to_build_background_llm_client",
                extra={
                    "error": str(exc),
                    "user_id": user_id,
                    "role": role,
                    "tier": tier,
                },
            )
            return None, None

    async def invalidate_user_background_llm(self, user_id: str) -> None:
        """Invalidate the cached background LLM client for a user.

        Called when the user activates, updates, deactivates, or
        deletes their LLM connection. Symmetric with
        invalidate_user_processor() which already drives the same
        invariant on the analysis-path cache.

        Best-effort close: a client whose underlying transport has
        already faulted may raise on close(); we swallow because the
        entry is being discarded anyway.
        """
        entry = self._user_background_llm.pop(user_id, None)
        if entry is not None:
            try:
                await entry.client.close()  # type: ignore[attr-defined]
            except Exception:
                pass
            _logger.info(
                "background_llm_client_invalidated",
                extra={"user_id": user_id},
            )

    async def invalidate_all_background_llm(self) -> None:
        """Invalidate every cached background LLM client.

        Called from the platform-key rotation routes (POST/DELETE
        /api/llm/platform/connection) where every user that was
        using the platform key needs to rebuild against the new
        config. Mirrors the existing container._user_processors.clear()
        pattern from the analysis path but also closes each client
        properly so we never leak an HTTP connection pool on a
        platform-key rotation.
        """
        users = list(self._user_background_llm.keys())
        for user_id in users:
            entry = self._user_background_llm.pop(user_id, None)
            if entry is not None:
                try:
                    await entry.client.close()  # type: ignore[attr-defined]
                except Exception:
                    pass
        if users:
            _logger.info(
                "background_llm_clients_invalidated_all",
                extra={"count": len(users)},
            )

    async def load_user_llm_client_by_id(
        self, user_id: str
    ) -> tuple[Optional["LLMClient"], Optional["ProcessorConfig"]]:
        """Personal-key-only background loader (compatibility shim).

        Equivalent to load_llm_client_for_background with
        allow_platform_fallback=False. Kept as a one-liner so any
        future caller that genuinely wants the strict 'no platform
        key, ever' behaviour does not have to repeat the flag.
        """
        return await self.load_llm_client_for_background(
            user_id,
            role="",
            tier="",
            allow_platform_fallback=False,
        )

    # -- Shutdown --------------------------------------------------------------


    async def shutdown(self) -> None:
        # Cancel pending background work BEFORE we tear down the resources
        # those tasks may be holding (broker clients, http client, redis).
        # The coordinator drains with a short bounded timeout so a wedged
        # background task cannot stall process exit.
        await self.background_tasks.shutdown(drain_timeout_s=2.0)
        self.scheduler.shutdown(wait=False)
        if hasattr(self, "rag_vector_store"):
            await self.rag_vector_store.close()
        if hasattr(self, "rag_embedding_provider"):
            await self.rag_embedding_provider.close()
        # Close per-user cached processor LLM clients.
        #
        # Iterate over a snapshot list (NOT the live dict) so a
        # concurrent invalidate_user_processor call cannot mutate the
        # dict mid-iteration and raise RuntimeError. The dict is
        # cleared after the loop. Audit ref: ADMIN-QUOTA-AUDIT-V2-8.
        for user_id, proc in list(self._user_processors.items()):
            try:
                await proc._llm.close()
            except Exception:
                pass
        self._user_processors.clear()

        # Close per-user cached background LLM clients (trading-plan +
        # performance-review). Same snapshot pattern as above.
        for user_id, entry in list(self._user_background_llm.items()):
            try:
                await entry.client.close()  # type: ignore[attr-defined]
            except Exception:
                pass
        self._user_background_llm.clear()

        # Close per-user cached broker clients via the pool. The pool's
        # stop() closes every cached client and cancels the sweeper.
        try:
            await self.broker_client_pool.stop()
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "broker_client_pool_shutdown_failed",
                extra={"error": str(exc)},
            )
        self._user_broker_keys.clear()
        self._user_brokers.clear()
        
        # Close the global system-level processor LLM client.
        if hasattr(self, "processor_llm_client"):
            await self.processor_llm_client.close()

        await self.http_client.close()
        await self.cache.close()
        await self.db.close()
