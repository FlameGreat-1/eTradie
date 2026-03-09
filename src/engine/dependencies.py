from __future__ import annotations

from engine.config import get_settings
from engine.shared.cache import RedisCache
from engine.shared.db import DatabaseManager
from engine.shared.http import HttpClient
from engine.shared.rss import RSSParser
from engine.shared.scheduler import SchedulerManager

# ══════════════════════════════════════════════════════════════════════════════
# MACRO IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
from engine.macro.collectors.calendar.collector import CalendarCollector
from engine.macro.collectors.central_bank.collector import CentralBankCollector
from engine.macro.collectors.cot.collector import COTCollector
from engine.macro.collectors.dxy.collector import DXYCollector
from engine.macro.collectors.economic_data.collector import EconomicDataCollector
from engine.macro.collectors.intermarket.collector import IntermarketCollector
from engine.macro.collectors.news.collector import NewsCollector
from engine.macro.collectors.sentiment.collector import SentimentCollector
from engine.macro.providers.calendar.trading_economics import TradingEconomicsCalendarProvider
from engine.macro.providers.central_bank.boe_rss import BOERSSProvider
from engine.macro.providers.central_bank.boj_rss import BOJRSSProvider
from engine.macro.providers.central_bank.ecb_rss import ECBRSSProvider
from engine.macro.providers.central_bank.fed_rss import FedRSSProvider
from engine.macro.providers.cot.cftc import CFTCProvider
from engine.macro.providers.economic_data.fred import FREDEconomicProvider
from engine.macro.providers.economic_data.trading_economics import TradingEconomicsEconomicProvider
from engine.macro.providers.market_data.trading_economics import TradingEconomicsMarketDataProvider
from engine.macro.providers.market_data.twelve_data import TwelveDataProvider
from engine.macro.providers.news.bloomberg_rss import BloombergRSSProvider
from engine.macro.providers.news.newsapi import NewsAPIProvider
from engine.macro.providers.news.reuters_rss import ReutersRSSProvider
from engine.macro.providers.registry import ProviderRegistry
from engine.macro.providers.sentiment.trading_economics import TradingEconomicsSentimentProvider

# ══════════════════════════════════════════════════════════════════════════════
# TA IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
from engine.ta.broker.mt5.client import MT5Client
from engine.ta.broker.mt5.config import MT5Config
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
from engine.ta.smc.detectors.bms import BMSDetector
from engine.ta.smc.detectors.sms import SMSDetector
from engine.ta.smc.detectors.choch import CHOCHDetector
from engine.ta.smc.detectors.inducement import InducementDetector
from engine.ta.smc.detectors.turtle_soup import TurtleSoupDetector
from engine.ta.smc.detectors.amd import AMDDetector
from engine.ta.smc.zones.order_block import OrderBlockDetector
from engine.ta.smc.zones.fvg import FVGDetector
from engine.ta.smc.zones.breaker import BreakerBlockDetector
from engine.ta.smc.zones.mitigation import MitigationBlockDetector
from engine.ta.smc.validators.zone.validator import ZoneValidator
from engine.ta.smc.validators.ltf.confirmation import LTFConfirmationValidator as SMCLTFValidator
from engine.ta.smc.builders.reversal import ReversalCandidateBuilder
from engine.ta.smc.builders.continuation import ContinuationCandidateBuilder
from engine.ta.smc.builders.amd.candidates import AMDCandidateBuilder
from engine.ta.snd.config import SnDConfig
from engine.ta.snd.detector import SnDDetector
from engine.ta.snd.detectors.qm import QMDetector
from engine.ta.snd.detectors.sr_flip import SRFlipDetector
from engine.ta.snd.detectors.rs_flip import RSFlipDetector
from engine.ta.snd.detectors.previous_levels import PreviousLevelDetector
from engine.ta.snd.detectors.mpl import MPLDetector
from engine.ta.snd.detectors.fakeouts import FakeoutDetector
from engine.ta.snd.detectors.supply_demand import SupplyDemandDetector
from engine.ta.snd.validators.marubozu.validator import MarubozuValidator
from engine.ta.snd.validators.ltf.confirmation import LTFConfirmationValidator as SnDLTFValidator
from engine.ta.snd.builders.candidates.fakeout import FakeoutCandidateBuilder
from engine.ta.snd.builders.candidates.qm import QMCandidateBuilder
from engine.ta.snd.builders.candidates.continuation import ContinuationCandidateBuilder as SnDContinuationBuilder
from engine.ta.storage.repositories.candle import CandleRepository
from engine.ta.storage.repositories.snapshot import SnapshotRepository
from engine.ta.storage.repositories.candidate import CandidateRepository
from engine.ta.orchestrator import TAOrchestrator


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

    def _build_providers(self) -> None:
        s = self.settings
        h = self.http_client
        r = self.rss_parser

        self.fed_provider = FedRSSProvider(r, feed_url=s.fed_rss_url)
        self.ecb_provider = ECBRSSProvider(r, feed_url=s.ecb_rss_url)
        self.boe_provider = BOERSSProvider(r, feed_url=s.boe_rss_url)
        self.boj_provider = BOJRSSProvider(r, feed_url=s.boj_rss_url)
        for p in (self.fed_provider, self.ecb_provider, self.boe_provider, self.boj_provider):
            self.registry.register(p)

        self.cftc_provider = CFTCProvider(h, base_url=s.cftc_api_base_url)
        self.registry.register(self.cftc_provider)

        self.te_econ_provider = TradingEconomicsEconomicProvider(
            h, base_url=s.tradingeconomics_base_url, api_key=s.tradingeconomics_api_key,
        )
        self.fred_provider = FREDEconomicProvider(
            h, base_url=s.fred_base_url, api_key=s.fred_api_key,
        )
        for p in (self.te_econ_provider, self.fred_provider):
            self.registry.register(p)

        self.twelve_data_provider = TwelveDataProvider(
            h, base_url=s.twelvedata_base_url, api_key=s.twelvedata_api_key,
        )
        self.te_market_provider = TradingEconomicsMarketDataProvider(
            h, base_url=s.tradingeconomics_base_url, api_key=s.tradingeconomics_api_key,
        )
        for p in (self.twelve_data_provider, self.te_market_provider):
            self.registry.register(p)

        self.te_cal_provider = TradingEconomicsCalendarProvider(
            h, base_url=s.tradingeconomics_base_url, api_key=s.tradingeconomics_api_key,
        )
        self.registry.register(self.te_cal_provider)

        self.newsapi_provider = NewsAPIProvider(h, base_url=s.newsapi_base_url, api_key=s.newsapi_api_key)
        self.reuters_rss_provider = ReutersRSSProvider(r, feed_url=s.reuters_rss_url)
        self.bloomberg_rss_provider = BloombergRSSProvider(r, feed_url=s.bloomberg_rss_url)
        for p in (self.newsapi_provider, self.reuters_rss_provider, self.bloomberg_rss_provider):
            self.registry.register(p)

        self.te_sentiment_provider = TradingEconomicsSentimentProvider(
            h, base_url=s.tradingeconomics_base_url, api_key=s.tradingeconomics_api_key,
        )
        self.registry.register(self.te_sentiment_provider)

    def _build_collectors(self) -> None:
        s = self.settings
        c = self.cache
        d = self.db

        self.cb_collector = CentralBankCollector(
            [self.fed_provider, self.ecb_provider, self.boe_provider, self.boj_provider], c, d,
        )
        self.cb_collector.cache_ttl = s.cache_ttl_central_bank

        self.cot_collector = COTCollector([self.cftc_provider], c, d)
        self.cot_collector.cache_ttl = s.cache_ttl_cot

        self.economic_collector = EconomicDataCollector(
            [self.te_econ_provider, self.fred_provider], c, d,
        )
        self.economic_collector.cache_ttl = s.cache_ttl_economic_data

        self.news_collector = NewsCollector(
            [self.newsapi_provider, self.reuters_rss_provider, self.bloomberg_rss_provider], c, d,
        )
        self.news_collector.cache_ttl = s.cache_ttl_news

        self.calendar_collector = CalendarCollector([self.te_cal_provider], c, d)
        self.calendar_collector.cache_ttl = s.cache_ttl_calendar

        self.dxy_collector = DXYCollector(
            [self.twelve_data_provider, self.te_market_provider], c, d,
        )
        self.dxy_collector.cache_ttl = s.cache_ttl_dxy

        self.intermarket_collector = IntermarketCollector(
            [self.twelve_data_provider, self.te_market_provider], c, d,
        )
        self.intermarket_collector.cache_ttl = s.cache_ttl_intermarket

        self.sentiment_collector = SentimentCollector([self.te_sentiment_provider], c, d)
        self.sentiment_collector.cache_ttl = s.cache_ttl_sentiment

    def _build_ta_configs(self) -> None:
        from engine.ta.config import TAConfig
        self.ta_config = TAConfig()
        self.smc_config = SMCConfig()
        self.snd_config = SnDConfig()

    def _build_ta_brokers(self) -> None:
        s = self.settings
        
        mt5_config = MT5Config()
        self.mt5_client = MT5Client(mt5_config)
        
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
        self.candle_repository = CandleRepository(self.db)
        self.snapshot_repository = SnapshotRepository(self.db)
        self.candidate_repository = CandidateRepository(self.db)

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
            liquidity_analyzer=self.liquidity_analyzer,
            fibonacci_analyzer=self.fibonacci_analyzer,
        )
        self.alignment_service = AlignmentService(timeframe_manager=self.timeframe_manager)

    def _build_smc_framework(self) -> None:
        self.bms_detector = BMSDetector(self.smc_config)
        self.sms_detector = SMSDetector(self.smc_config)
        self.choch_detector = CHOCHDetector(self.smc_config)
        self.inducement_detector = InducementDetector(self.smc_config)
        self.turtle_soup_detector = TurtleSoupDetector(self.smc_config)
        self.amd_detector = AMDDetector(self.smc_config, self.session_analyzer, self.dealing_range_analyzer)
        
        self.order_block_detector = OrderBlockDetector(self.smc_config)
        self.fvg_detector = FVGDetector(self.smc_config)
        self.breaker_detector = BreakerBlockDetector(self.smc_config)
        self.mitigation_detector = MitigationBlockDetector(self.smc_config)
        
        self.zone_validator = ZoneValidator(self.smc_config, self.fibonacci_analyzer)
        self.smc_ltf_validator = SMCLTFValidator(self.smc_config, self.compression_analyzer, self.fibonacci_analyzer)
        
        self.reversal_builder = ReversalCandidateBuilder(
            self.smc_config, self.zone_validator, self.smc_ltf_validator, self.fibonacci_analyzer,
        )
        self.continuation_builder = ContinuationCandidateBuilder(
            self.smc_config, self.zone_validator, self.smc_ltf_validator, self.fibonacci_analyzer,
        )
        self.amd_builder = AMDCandidateBuilder(
            self.smc_config, self.zone_validator, self.smc_ltf_validator, self.fibonacci_analyzer,
        )
        
        self.smc_detector = SMCDetector(
            config=self.smc_config,
            candle_analyzer=self.candle_analyzer,
            swing_analyzer=self.swing_analyzer,
            bms_detector=self.bms_detector,
            sms_detector=self.sms_detector,
            choch_detector=self.choch_detector,
            inducement_detector=self.inducement_detector,
            turtle_soup_detector=self.turtle_soup_detector,
            amd_detector=self.amd_detector,
            ob_detector=self.order_block_detector,
            fvg_detector=self.fvg_detector,
            breaker_detector=self.breaker_detector,
            mitigation_detector=self.mitigation_detector,
            fibonacci_analyzer=self.fibonacci_analyzer,
            reversal_builder=self.reversal_builder,
            continuation_builder=self.continuation_builder,
            amd_builder=self.amd_builder,
        )

    def _build_snd_framework(self) -> None:
        self.qm_detector = QMDetector(self.snd_config)
        self.sr_flip_detector = SRFlipDetector(self.snd_config, self.marubozu_analyzer)
        self.rs_flip_detector = RSFlipDetector(self.snd_config, self.marubozu_analyzer)
        self.previous_level_detector = PreviousLevelDetector(self.snd_config)
        self.mpl_detector = MPLDetector(self.snd_config)
        self.fakeout_detector = FakeoutDetector(self.snd_config, self.compression_analyzer, self.marubozu_analyzer)
        self.supply_demand_detector = SupplyDemandDetector(self.snd_config)
        
        self.marubozu_validator = MarubozuValidator(self.snd_config, self.marubozu_analyzer)
        self.snd_ltf_validator = SnDLTFValidator(self.snd_config, self.compression_analyzer, self.fibonacci_analyzer)
        
        self.fakeout_builder = FakeoutCandidateBuilder(
            self.snd_config, self.marubozu_validator, self.snd_ltf_validator, self.fibonacci_analyzer,
        )
        self.qm_builder = QMCandidateBuilder(
            self.snd_config, self.marubozu_validator, self.snd_ltf_validator, self.fibonacci_analyzer,
        )
        self.snd_continuation_builder = SnDContinuationBuilder(
            self.snd_config, self.marubozu_validator, self.snd_ltf_validator, self.fibonacci_analyzer,
        )
        
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
            candle_repository=self.candle_repository,
            snapshot_repository=self.snapshot_repository,
            candidate_repository=self.candidate_repository,
            smc_detector=self.smc_detector,
            snd_detector=self.snd_detector,
            snapshot_builder=self.snapshot_builder,
            candle_analyzer=self.candle_analyzer,
            swing_analyzer=self.swing_analyzer,
            fibonacci_analyzer=self.fibonacci_analyzer,
        )

    async def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
        if hasattr(self, 'mt5_client'):
            await self.mt5_client.disconnect()
        await self.http_client.close()
        await self.cache.close()
        await self.db.close()
