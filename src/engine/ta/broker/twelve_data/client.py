import asyncio
import time as _time
from datetime import UTC, datetime
from typing import Any

from engine.shared.cache.redis_cache import RedisCache
from engine.shared.exceptions import (
    ProviderError,
    ProviderResponseError,
)
from engine.shared.http.client import HttpClient
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    PROVIDER_RESPONSE_SIZE,
    TA_BROKER_ERRORS_TOTAL,
    TA_BROKER_FETCH_DURATION,
)
from engine.ta.broker.base import (
    AccountInfo,
    BrokerBase,
    BrokerCapabilities,
    HistoryDealInfo,
    OrderResult,
    PendingOrderInfo,
    PositionInfo,
    TickPrice,
)
from engine.ta.broker.twelve_data.config import TwelveDataConfig
from engine.ta.broker.validator import BrokerDataValidator
from engine.ta.constants import Timeframe
from engine.ta.models.candle import Candle, CandleSequence

logger = get_logger(__name__)

_TIMEFRAME_MAP: dict[Timeframe, str] = {
    Timeframe.M1: "1min",
    Timeframe.M5: "5min",
    Timeframe.M15: "15min",
    Timeframe.M30: "30min",
    Timeframe.H1: "1h",
    Timeframe.H3: "3h",
    Timeframe.H4: "4h",
    Timeframe.H6: "6h",
    Timeframe.H8: "8h",
    Timeframe.H12: "12h",
    Timeframe.D1: "1day",
    Timeframe.W1: "1week",
    Timeframe.MN1: "1month",
}

_CACHE_KEY_PREFIX = "twelve_data:candles"


class TwelveDataClient(BrokerBase):
    """
    Twelve Data REST API adapter for fallback/reference market data.

    Uses the shared HttpClient (circuit breaker, retries, metrics)
    and optional RedisCache to avoid redundant API calls within
    the configured TTL.
    """

    def __init__(
        self,
        config: TwelveDataConfig,
        http_client: HttpClient,
        cache: RedisCache | None = None,
    ) -> None:
        super().__init__(broker_id="twelve_data")
        self.config = config
        self.http_client = http_client
        self.cache = cache
        self.validator = BrokerDataValidator()
        self._rate_limiter = asyncio.Semaphore(self.config.rate_limit_per_minute)

    # -- Identity --------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "twelve_data"

    @property
    def account_id(self) -> str:
        # Twelve Data is a keyed reference-data service with no per-account
        # concept; the broker_id is the stable identifier used for metrics
        # and logging labels.
        return self.broker_id

    # -- BrokerBase abstract methods -------------------------------------------

    async def get_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_realtime=False,
            supports_historical=True,
            supports_tick_data=False,
            supports_symbol_info=True,
            max_candles_per_request=self.config.max_candles_per_request,
            rate_limit_per_minute=self.config.rate_limit_per_minute,
            requires_authentication=True,
        )

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        count: int | None = None,
    ) -> CandleSequence:
        if start_time and end_time:
            self.validator.validate_time_range(start_time, end_time)

        td_interval = _TIMEFRAME_MAP.get(timeframe)
        if td_interval is None:
            raise ProviderError(
                f"Unsupported timeframe: {timeframe}",
                details={"timeframe": timeframe},
            )

        cache_key = self._build_cache_key(symbol, timeframe, start_time, end_time, count)
        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached

        output_size = min(
            count or self.config.max_candles_per_request,
            self.config.max_candles_per_request,
        )

        params: dict[str, Any] = {
            "symbol": self._normalize_symbol(symbol),
            "interval": td_interval,
            "outputsize": output_size,
            "apikey": self.config.api_key,
            "format": "JSON",
            "order": "ASC",
        }

        if start_time:
            params["start_date"] = start_time.strftime("%Y-%m-%d %H:%M:%S")
        if end_time:
            params["end_date"] = end_time.strftime("%Y-%m-%d %H:%M:%S")

        start_timer = _time.monotonic()

        try:
            async with self._rate_limiter:
                response = await self.http_client.get(
                    f"{self.config.base_url}/time_series",
                    provider_name="twelve_data",
                    category="candles",
                    params=params,
                    timeout_override=self.config.timeout_seconds,
                )

            duration = _time.monotonic() - start_timer

            TA_BROKER_FETCH_DURATION.labels(
                broker="twelve_data",
                symbol=symbol,
                timeframe=timeframe.value,
            ).observe(duration)

            if not isinstance(response, dict):
                TA_BROKER_ERRORS_TOTAL.labels(
                    broker="twelve_data",
                    error_type="invalid_response_type",
                ).inc()
                raise ProviderResponseError(
                    "Unexpected response type from Twelve Data",
                    details={"response_type": type(response).__name__},
                )

            if "code" in response and response.get("status") == "error":
                TA_BROKER_ERRORS_TOTAL.labels(
                    broker="twelve_data",
                    error_type="api_error",
                ).inc()
                raise ProviderResponseError(
                    f"Twelve Data API error: {response.get('message', 'unknown')}",
                    details={
                        "code": response.get("code"),
                        "message": response.get("message"),
                    },
                )

            values = response.get("values")
            if not values:
                TA_BROKER_ERRORS_TOTAL.labels(
                    broker="twelve_data",
                    error_type="no_data",
                ).inc()
                raise ProviderResponseError(
                    "No candle data returned from Twelve Data",
                    details={"symbol": symbol, "timeframe": timeframe},
                )

            candles = self._parse_candles(values, symbol, timeframe)

            sequence = CandleSequence(
                symbol=symbol,
                timeframe=timeframe,
                candles=candles,
            )

            self.validator.validate_sequence(sequence)

            PROVIDER_RESPONSE_SIZE.labels(
                provider="twelve_data",
                category="candles",
            ).observe(len(candles))

            await self._set_cached(cache_key, sequence)

            logger.info(
                "twelve_data_candles_fetched",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "count": len(candles),
                    "duration_seconds": round(duration, 3),
                },
            )

            return sequence

        except ProviderError:
            raise
        except Exception as e:
            TA_BROKER_ERRORS_TOTAL.labels(
                broker="twelve_data",
                error_type=type(e).__name__,
            ).inc()

            logger.error(
                "twelve_data_fetch_candles_failed",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e),
                },
                exc_info=True,
            )

            raise ProviderError(
                f"Twelve Data fetch candles failed: {e}",
                details={"symbol": symbol, "timeframe": timeframe, "error": str(e)},
            ) from e

    async def fetch_latest_candle(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> Candle:
        sequence = await self.fetch_candles(
            symbol=symbol,
            timeframe=timeframe,
            count=1,
        )

        if sequence.count == 0:
            raise ProviderResponseError(
                "No candles returned",
                details={"symbol": symbol, "timeframe": timeframe},
            )

        return sequence.candles[-1]

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        normalized = self._normalize_symbol(symbol)

        try:
            response = await self.http_client.get(
                f"{self.config.base_url}/symbol_search",
                provider_name="twelve_data",
                category="symbol_info",
                params={
                    "symbol": normalized,
                    "apikey": self.config.api_key,
                },
                timeout_override=self.config.timeout_seconds,
            )

            if not isinstance(response, dict):
                raise ProviderResponseError(
                    "Unexpected response type",
                    details={"response_type": type(response).__name__},
                )

            data = response.get("data", [])
            if not data:
                raise ProviderResponseError(
                    f"Symbol not found: {symbol}",
                    details={"symbol": symbol},
                )

            info = data[0]
            return {
                "symbol": info.get("symbol", ""),
                "instrument_name": info.get("instrument_name", ""),
                "exchange": info.get("exchange", ""),
                "instrument_type": info.get("instrument_type", ""),
                "country": info.get("country", ""),
                "currency": info.get("currency", ""),
            }

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"Twelve Data symbol info failed: {e}",
                details={"symbol": symbol, "error": str(e)},
            ) from e

    async def validate_symbol(self, symbol: str) -> bool:
        try:
            await self.get_symbol_info(symbol)
            return True
        except ProviderError:
            return False

    async def health_check(self) -> bool:
        try:
            response = await self.http_client.get(
                f"{self.config.base_url}/api_usage",
                provider_name="twelve_data",
                category="health",
                params={"apikey": self.config.api_key},
                timeout_override=10,
            )

            if isinstance(response, dict) and "timestamp" in response:
                logger.debug("twelve_data_health_ok")
                return True

            return False

        except Exception as e:
            logger.error(
                "twelve_data_health_check_failed",
                extra={"error": str(e)},
            )
            return False

    async def shutdown(self) -> None:
        logger.info("twelve_data_shutdown_complete")

    # -- Symbol catalog (not provided by Twelve Data) --------------------------
    #
    # Twelve Data is used only as a candle-data fallback. It is not the
    # symbol catalog source of truth (that is the active MT5 broker), so
    # the catalog operations fail loudly rather than returning empty data
    # that would mislead the SymbolResolver / BrokerSyncService.
    # --------------------------------------------------------------------------

    _CATALOG_NOT_SUPPORTED = (
        "Twelve Data is a candle-data fallback provider and does not expose a "
        "symbol catalog. Use the active MT5 broker for symbol enumeration."
    )

    async def get_all_symbol_names(self) -> list[str]:
        raise ProviderError(
            self._CATALOG_NOT_SUPPORTED,
            details={"provider": "twelve_data", "operation": "get_all_symbol_names"},
        )

    async def get_all_symbols(self) -> list[dict[str, Any]]:
        raise ProviderError(
            self._CATALOG_NOT_SUPPORTED,
            details={"provider": "twelve_data", "operation": "get_all_symbols"},
        )

    # -- Trading methods (not supported by Twelve Data) ------------------------
    #
    # Twelve Data is a market-data-only REST API.  It does not provide
    # trading endpoints.  All order/position/account methods raise
    # ProviderError so the execution layer never accidentally routes
    # real money through a data-only provider.
    # --------------------------------------------------------------------------

    _TRADING_NOT_SUPPORTED = (
        "Twelve Data is a market-data-only provider.  Trading operations require the MT5 broker (MetaApi or ZeroMQ)."
    )

    async def get_account_info(self) -> AccountInfo:
        raise ProviderError(
            self._TRADING_NOT_SUPPORTED,
            details={"provider": "twelve_data", "operation": "get_account_info"},
        )

    async def get_positions(self) -> list[PositionInfo]:
        raise ProviderError(
            self._TRADING_NOT_SUPPORTED,
            details={"provider": "twelve_data", "operation": "get_positions"},
        )

    async def get_history(self, days: int = 30) -> list[HistoryDealInfo]:
        raise ProviderError(
            self._TRADING_NOT_SUPPORTED,
            details={"provider": "twelve_data", "operation": "get_history", "days": days},
        )

    async def get_position(self, ticket: str) -> PositionInfo:
        raise ProviderError(
            self._TRADING_NOT_SUPPORTED,
            details={
                "provider": "twelve_data",
                "operation": "get_position",
                "ticket": ticket,
            },
        )

    async def get_pending_orders(self) -> list[PendingOrderInfo]:
        raise ProviderError(
            self._TRADING_NOT_SUPPORTED,
            details={"provider": "twelve_data", "operation": "get_pending_orders"},
        )

    async def get_tick_price(self, symbol: str) -> TickPrice:
        raise ProviderError(
            self._TRADING_NOT_SUPPORTED,
            details={
                "provider": "twelve_data",
                "operation": "get_tick_price",
                "symbol": symbol,
            },
        )

    async def place_order(
        self,
        *,
        symbol: str,
        direction: str,
        order_type: str,
        price: float,
        stop_loss: float,
        take_profit: float,
        lot_size: float,
        comment: str = "",
    ) -> OrderResult:
        raise ProviderError(
            self._TRADING_NOT_SUPPORTED,
            details={
                "provider": "twelve_data",
                "operation": "place_order",
                "symbol": symbol,
                "direction": direction,
                "lot_size": lot_size,
            },
        )

    async def cancel_order(self, order_id: str) -> bool:
        raise ProviderError(
            self._TRADING_NOT_SUPPORTED,
            details={
                "provider": "twelve_data",
                "operation": "cancel_order",
                "order_id": order_id,
            },
        )

    async def modify_position(
        self,
        *,
        ticket: str,
        stop_loss: float,
        take_profit: float,
    ) -> bool:
        raise ProviderError(
            self._TRADING_NOT_SUPPORTED,
            details={
                "provider": "twelve_data",
                "operation": "modify_position",
                "ticket": ticket,
            },
        )

    async def close_partial(
        self,
        *,
        ticket: str,
        volume: float,
    ) -> dict[str, Any]:
        raise ProviderError(
            self._TRADING_NOT_SUPPORTED,
            details={
                "provider": "twelve_data",
                "operation": "close_partial",
                "ticket": ticket,
                "volume": volume,
            },
        )

    async def close_position(self, ticket: str) -> dict[str, Any]:
        raise ProviderError(
            self._TRADING_NOT_SUPPORTED,
            details={
                "provider": "twelve_data",
                "operation": "close_position",
                "ticket": ticket,
            },
        )

    # -- Private helpers -------------------------------------------------------

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Convert broker-specific symbol to Twelve Data format.

        MT5 brokers append proprietary suffixes to standard symbols:
          Exness:   XAUUSDm, EURUSDm   (micro account)
          Others:   GBPJPYpro, USDCADc  (cent/pro/raw accounts)
          Dots:     EURUSD.i, XAUUSD.raw

        Twelve Data expects standard format:  XAU/USD, EUR/USD
        """
        raw = symbol.upper().replace("/", "").replace("_", "")

        # Clean pair - standard 6-char forex/metals symbol
        if len(raw) == 6 and raw.isalpha():
            return f"{raw[:3]}/{raw[3:]}"

        # Broker-suffixed symbol - the base pair is always the first
        # 6 alphabetic characters (e.g. XAUUSDm -> XAUUSD, EURUSDpro -> EURUSD)
        if len(raw) > 6:
            base = raw[:6]
            if base.isalpha():
                return f"{base[:3]}/{base[3:]}"

        return raw

    @staticmethod
    def _parse_candles(
        values: list[dict[str, Any]],
        symbol: str,
        timeframe: Timeframe,
    ) -> list[Candle]:
        candles: list[Candle] = []

        for record in values:
            try:
                timestamp = datetime.strptime(record["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            except (KeyError, ValueError):
                try:
                    timestamp = datetime.strptime(record["datetime"], "%Y-%m-%d").replace(tzinfo=UTC)
                except (KeyError, ValueError):
                    logger.warning(
                        "twelve_data_parse_skip",
                        extra={"record": record},
                    )
                    continue

            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                open=float(record["open"]),
                high=float(record["high"]),
                low=float(record["low"]),
                close=float(record["close"]),
                volume=float(record.get("volume", 0)),
            )

            candles.append(candle)

        return candles

    def _build_cache_key(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime | None,
        end_time: datetime | None,
        count: int | None,
    ) -> str:
        parts = [
            _CACHE_KEY_PREFIX,
            symbol,
            timeframe.value,
        ]

        if start_time:
            parts.append(f"s:{int(start_time.timestamp())}")
        if end_time:
            parts.append(f"e:{int(end_time.timestamp())}")
        if count:
            parts.append(f"c:{count}")

        return ":".join(parts)

    async def _get_cached(self, key: str) -> CandleSequence | None:
        if self.cache is None:
            return None

        try:
            data = await self.cache.get("twelve_data", key)
            if data is None:
                return None
            candles = [
                Candle(
                    symbol=data["symbol"],
                    timeframe=Timeframe(data["timeframe"]),
                    timestamp=datetime.fromisoformat(c["timestamp"]),
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                    volume=c.get("volume", 0),
                )
                for c in data["candles"]
            ]

            return CandleSequence(
                symbol=data["symbol"],
                timeframe=Timeframe(data["timeframe"]),
                candles=candles,
            )

        except Exception as e:
            logger.warning(
                "twelve_data_cache_read_error",
                extra={"key": key, "error": str(e)},
            )
            return None

    async def _set_cached(self, key: str, sequence: CandleSequence) -> None:
        if self.cache is None:
            return

        try:
            data = {
                "symbol": sequence.symbol,
                "timeframe": sequence.timeframe.value,
                "candles": [
                    {
                        "timestamp": c.timestamp.isoformat(),
                        "open": c.open,
                        "high": c.high,
                        "low": c.low,
                        "close": c.close,
                        "volume": c.volume,
                    }
                    for c in sequence.candles
                ],
            }

            await self.cache.set(
                "twelve_data",
                key,
                data,
                self.config.cache_ttl_seconds,
            )

        except Exception as e:
            logger.warning(
                "twelve_data_cache_write_error",
                extra={"key": key, "error": str(e)},
            )
