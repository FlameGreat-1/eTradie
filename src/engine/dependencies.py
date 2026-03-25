from __future__ import annotations

from engine.config import get_settings
from engine.shared.cache import RedisCache
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
from engine.macro.collectors.news.collector import NewsCollector
from engine.macro.collectors.sentiment.collector import SentimentCollector
from engine.macro.providers.calendar.trading_economics import (
    TradingEconomicsCalendarProvider,
)
from engine.macro.providers.central_bank.boe_rss import BOERSSProvider
from engine.macro.providers.central_bank.boj_rss import BOJRSSProvider
from engine.macro.providers.central_bank.ecb_rss import ECBRSSProvider
from engine.macro.providers.central_bank.fed_rss import FedRSSProvider
from engine.macro.providers.cot.cftc import CFTCProvider
from engine.macro.providers.economic_data.fred import FREDEconomicProvider
from engine.macro.providers.economic_data.trading_economics import (
    TradingEconomicsEconomicProvider,
)
from engine.macro.providers.market_data.trading_economics import (
    TradingEconomicsMarketDataProvider,
)
from engine.macro.providers.market_data.twelve_data import TwelveDataProvider
from engine.macro.providers.news.bloomberg_rss import BloombergRSSProvider
from engine.macro.providers.news.newsapi import NewsAPIProvider
from engine.macro.providers.news.reuters_rss import ReutersRSSProvider
from engine.macro.providers.registry import ProviderRegistry
from engine.macro.providers.sentiment.trading_economics import (
    TradingEconomicsSentimentProvider,
)

from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.mt5.factory import create_mt5_broker
from engine.ta.broker.twelve_data.client import TwelveDataClient
from engine.ta.broker.twelve_data.config import TwelveDataConfig
from engine.ta.broker.registry import BrokerRegistry
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
        self.http_client = HttpClient(
            timeout_seconds=s.http_timeout_seconds,
            max_retries=s.http_max_retries,
            backoff_base=s.http_retry_backoff_base,
            backoff_max=s.http_retry_backoff_max,
            cb_failure_threshold=s.circuit_breaker_failure_threshold,
            cb_recovery_timeout=s.circuit_breaker_recovery_timeout,
            cb_half_open_max=s.circuit_breaker_half_open_max_calls,
        )
        self.rss_parser = RSSParser(self.http_client)
        self.scheduler = SchedulerManager()

        self.registry = ProviderRegistry()
        self._build_providers()
        self._build_collectors()

        self._build_ta_configs()
        self._build_ta_brokers()
        self._build_ta_repositories()
        self._build_ta_analyzers()
        self._build_ta_services()
        self._build_smc_framework()
        self._build_snd_framework()
        self._build_ta_orchestrator()

        self.rag_config = get_rag_config()

    def _build_providers(self) -> None:
        s = self.settings
        h = self.http_client
        r = self.rss_parser

        self.fed_provider = FedRSSProvider(r, feed_url=s.fed_rss_url)
        self.ecb_provider = ECBRSSProvider(r, feed_url=s.ecb_rss_url)
        self.boe_provider = BOERSSProvider(r, feed_url=s.boe_rss_url)
        self.boj_provider = BOJRSSProvider(r, feed_url=s.boj_rss_url)
        for p in (
            self.fed_provider,
            self.ecb_provider,
            self.boe_provider,
            self.boj_provider,
        ):
            self.registry.register(p)

        self.cftc_provider = CFTCProvider(h, base_url=s.cftc_api_base_url)
        self.registry.register(self.cftc_provider)

        self.te_econ_provider = TradingEconomicsEconomicProvider(
            h,
            base_url=s.tradingeconomics_base_url,
            api_key=s.tradingeconomics_api_key,
        )
        self.fred_provider = FREDEconomicProvider(
            h,
            base_url=s.fred_base_url,
            api_key=s.fred_api_key,
        )
        for p in (self.te_econ_provider, self.fred_provider):
            self.registry.register(p)

        self.twelve_data_provider = TwelveDataProvider(
            h,
            base_url=s.twelvedata_base_url,
            api_key=s.twelvedata_api_key,
        )
        self.te_market_provider = TradingEconomicsMarketDataProvider(
            h,
            base_url=s.tradingeconomics_base_url,
            api_key=s.tradingeconomics_api_key,
        )
        for p in (self.twelve_data_provider, self.te_market_provider):
            self.registry.register(p)

        self.te_cal_provider = TradingEconomicsCalendarProvider(
            h,
            base_url=s.tradingeconomics_base_url,
            api_key=s.tradingeconomics_api_key,
        )
        self.registry.register(self.te_cal_provider)

        self.newsapi_provider = NewsAPIProvider(
            h, base_url=s.newsapi_base_url, api_key=s.newsapi_api_key
        )
        self.reuters_rss_provider = ReutersRSSProvider(r, feed_url=s.reuters_rss_url)
        self.bloomberg_rss_provider = BloombergRSSProvider(
            r, feed_url=s.bloomberg_rss_url
        )
        for p in (
            self.newsapi_provider,
            self.reuters_rss_provider,
            self.bloomberg_rss_provider,
        ):
            self.registry.register(p)

        self.te_sentiment_provider = TradingEconomicsSentimentProvider(
            h,
            base_url=s.tradingeconomics_base_url,
            api_key=s.tradingeconomics_api_key,
        )
        self.registry.register(self.te_sentiment_provider)

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
            ],
            c,
            d,
        )
        self.cb_collector.cache_ttl = s.cache_ttl_central_bank

        self.cot_collector = COTCollector([self.cftc_provider], c, d)
        self.cot_collector.cache_ttl = s.cache_ttl_cot

        self.economic_collector = EconomicDataCollector(
            [self.te_econ_provider, self.fred_provider],
            c,
            d,
        )
        self.economic_collector.cache_ttl = s.cache_ttl_economic_data

        self.news_collector = NewsCollector(
            [
                self.newsapi_provider,
                self.reuters_rss_provider,
                self.bloomberg_rss_provider,
            ],
            c,
            d,
        )
        self.news_collector.cache_ttl = s.cache_ttl_news

        self.calendar_collector = CalendarCollector([self.te_cal_provider], c, d)
        self.calendar_collector.cache_ttl = s.cache_ttl_calendar

        self.dxy_collector = DXYCollector(
            [self.twelve_data_provider, self.te_market_provider],
            c,
            d,
        )
        self.dxy_collector.cache_ttl = s.cache_ttl_dxy

        self.intermarket_collector = IntermarketCollector(
            [self.twelve_data_provider, self.te_market_provider],
            c,
            d,
        )
        self.intermarket_collector.cache_ttl = s.cache_ttl_intermarket

        self.sentiment_collector = SentimentCollector(
            [self.te_sentiment_provider], c, d
        )
        self.sentiment_collector.cache_ttl = s.cache_ttl_sentiment

    def _build_ta_configs(self) -> None:
        from engine.config import TAConfig

        self.ta_config = TAConfig()
        self.smc_config = SMCConfig()
        self.snd_config = SnDConfig()

    def _build_ta_brokers(self) -> None:
        s = self.settings

        mt5_config = MT5Config()
        self.mt5_client = create_mt5_broker(
            config=mt5_config,
            http_client=self.http_client,
        )

        twelve_config = TwelveDataConfig(
            api_key=s.twelvedata_api_key,
            base_url=s.twelvedata_base_url,
        )
        self.twelve_data_client = TwelveDataClient(
            config=twelve_config,
            http_client=self.http_client,
            cache=self.cache,
        )

        self.broker_registry = BrokerRegistry(
            ta_config=self.ta_config,
            http_client=self.http_client,
            cache=self.cache,
        )

    def _build_ta_repositories(self) -> None:
        self.ta_uow_factory = ta_uow_factory(self.db)
        self.ta_read_uow_factory = ta_read_uow_factory(self.db)

    def _build_ta_analyzers(self) -> None:
        self.candle_analyzer = CandleAnalyzer()
        self.swing_analyzer = SwingAnalyzer()
        self.fibonacci_analyzer = FibonacciAnalyzer()
        self.marubozu_analyzer = MarubozuAnalyzer()
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
        self.ta_orchestrator = TAOrchestrator(
            broker_client=self.mt5_client,
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

    def build_processor(self) -> None:
        """Build the Processor LLM service.

        On startup, checks the database for an active LLM connection
        saved by the user via the dashboard. If found, uses that
        connection's provider, model, and decrypted API key.

        If no active connection exists, falls back to environment
        variables (PROCESSOR_LLM_PROVIDER, PROCESSOR_ANTHROPIC_API_KEY, etc.).

        Supports Anthropic, OpenAI, Gemini, and any OpenAI-compatible
        self-hosted endpoint. Must be called after build_rag() since
        the processor persists audit data to the same database.
        """
        self.processor_uow_factory = processor_uow_factory(self.db)

        # Try to load active connection from database.
        db_config = self._load_active_llm_connection()
        if db_config is not None:
            self.processor_config = db_config
        else:
            self.processor_config = get_processor_config()

        self.processor_llm_client = create_llm_client(
            config=self.processor_config,
        )

        self.processor = AnalysisProcessor(
            config=self.processor_config,
            llm_client=self.processor_llm_client,
            uow_factory=self.processor_uow_factory,
        )

    def _load_active_llm_connection(self) -> "ProcessorConfig | None":
        """Load the active LLM connection from the database.

        Returns a ProcessorConfig built from the saved connection,
        or None if no active connection exists. Runs synchronously
        at startup using asyncio.run() since the event loop is not
        yet running when build_processor() is called from lifespan.
        """
        import asyncio
        from engine.shared.logging import get_logger

        _logger = get_logger(__name__)

        async def _fetch() -> "ProcessorConfig | None":
            try:
                from engine.processor.storage.repositories.llm_connection_repository import (
                    LLMConnectionRepository,
                    decrypt_api_key,
                )
                from pydantic import SecretStr

                async with self.db.read_session() as session:
                    repo = LLMConnectionRepository(session)
                    row = await repo.get_active()

                if row is None:
                    _logger.info("no_active_llm_connection_in_db_using_env_vars")
                    return None

                api_key = decrypt_api_key(row.api_key_encrypted)

                # Build a ProcessorConfig from the saved connection.
                # Start with env var defaults for non-connection fields,
                # then override provider/model/key from the DB row.
                env_cfg = get_processor_config()

                overrides = {
                    "llm_provider": row.provider,
                    "model_name": row.model_name,
                    "temperature": row.temperature,
                    "max_output_tokens": row.max_output_tokens,
                    # Carry forward non-connection settings from env.
                    "llm_timeout_seconds": env_cfg.llm_timeout_seconds,
                    "total_timeout_seconds": env_cfg.total_timeout_seconds,
                    "max_retries": env_cfg.max_retries,
                    "retry_backoff_base_seconds": env_cfg.retry_backoff_base_seconds,
                    "retry_backoff_max_seconds": env_cfg.retry_backoff_max_seconds,
                    "strict_schema_validation": env_cfg.strict_schema_validation,
                    "require_citations": env_cfg.require_citations,
                    "persist_audit_logs": env_cfg.persist_audit_logs,
                    "log_raw_llm_response": env_cfg.log_raw_llm_response,
                    # Default all provider keys to env values.
                    "anthropic_api_key": env_cfg.anthropic_api_key,
                    "openai_api_key": env_cfg.openai_api_key,
                    "gemini_api_key": env_cfg.gemini_api_key,
                    "self_hosted_api_key": env_cfg.self_hosted_api_key,
                    "api_base_url": row.base_url or env_cfg.api_base_url,
                }

                # Set the API key for the active provider from the DB.
                key_field = f"{row.provider}_api_key"
                if key_field in overrides:
                    overrides[key_field] = SecretStr(api_key)

                cfg = ProcessorConfig(**overrides)

                _logger.info(
                    "loaded_active_llm_connection_from_db",
                    extra={
                        "provider": row.provider,
                        "model": row.model_name,
                        "connection_id": str(row.id),
                    },
                )
                return cfg

            except Exception as exc:
                _logger.warning(
                    "failed_to_load_llm_connection_from_db_falling_back_to_env",
                    extra={"error": str(exc)},
                )
                return None

        try:
            loop = asyncio.get_running_loop()
            # If we're inside an async context (lifespan), create a task.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return loop.run_in_executor(pool, lambda: asyncio.run(_fetch())).__await__().__next__()
        except RuntimeError:
            # No running loop (called outside async context).
            return asyncio.run(_fetch())

    async def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
        if hasattr(self, "mt5_client"):
            await self.mt5_client.shutdown()
        if hasattr(self, "rag_vector_store"):
            await self.rag_vector_store.close()
        if hasattr(self, "rag_embedding_provider"):
            await self.rag_embedding_provider.close()
        if hasattr(self, "processor_llm_client"):
            await self.processor_llm_client.close()
        await self.http_client.close()
        await self.cache.close()
        await self.db.close()
