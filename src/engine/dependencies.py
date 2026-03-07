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

    def _build_providers(self) -> None:
        s = self.settings
        h = self.http_client
        r = self.rss_parser

        # ── Central Bank RSS (official feeds) ────────
        self.fed_provider = FedRSSProvider(r, feed_url=s.fed_rss_url)
        self.ecb_provider = ECBRSSProvider(r, feed_url=s.ecb_rss_url)
        self.boe_provider = BOERSSProvider(r, feed_url=s.boe_rss_url)
        self.boj_provider = BOJRSSProvider(r, feed_url=s.boj_rss_url)
        for p in (self.fed_provider, self.ecb_provider, self.boe_provider, self.boj_provider):
            self.registry.register(p)

        # ── COT — CFTC (only official source) ───────
        self.cftc_provider = CFTCProvider(h, base_url=s.cftc_api_base_url)
        self.registry.register(self.cftc_provider)

        # ── Economic Data — TradingEconomics (primary) + FRED (US backup) ──
        self.te_econ_provider = TradingEconomicsEconomicProvider(
            h, base_url=s.tradingeconomics_base_url, api_key=s.tradingeconomics_api_key,
        )
        self.fred_provider = FREDEconomicProvider(
            h, base_url=s.fred_base_url, api_key=s.fred_api_key,
        )
        for p in (self.te_econ_provider, self.fred_provider):
            self.registry.register(p)

        # ── Market Data — TwelveData (primary) + TradingEconomics (backup) ──
        self.twelve_data_provider = TwelveDataProvider(
            h, base_url=s.twelvedata_base_url, api_key=s.twelvedata_api_key,
        )
        self.te_market_provider = TradingEconomicsMarketDataProvider(
            h, base_url=s.tradingeconomics_base_url, api_key=s.tradingeconomics_api_key,
        )
        for p in (self.twelve_data_provider, self.te_market_provider):
            self.registry.register(p)

        # ── Calendar — TradingEconomics (single source, institutional-grade) ──
        self.te_cal_provider = TradingEconomicsCalendarProvider(
            h, base_url=s.tradingeconomics_base_url, api_key=s.tradingeconomics_api_key,
        )
        self.registry.register(self.te_cal_provider)

        # ── News — NewsAPI (primary) + Reuters/Bloomberg RSS (backup) ──
        self.newsapi_provider = NewsAPIProvider(h, base_url=s.newsapi_base_url, api_key=s.newsapi_api_key)
        self.reuters_rss_provider = ReutersRSSProvider(r, feed_url=s.reuters_rss_url)
        self.bloomberg_rss_provider = BloombergRSSProvider(r, feed_url=s.bloomberg_rss_url)
        for p in (self.newsapi_provider, self.reuters_rss_provider, self.bloomberg_rss_provider):
            self.registry.register(p)

        # ── Sentiment — TradingEconomics (confidence indicators) ──
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

    async def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
        await self.http_client.close()
        await self.cache.close()
        await self.db.close()
