import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, Any

from engine.shared.cache.redis_cache import RedisCache
from engine.shared.exceptions import (
    ProviderError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from engine.shared.http.client import HttpClient
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    TA_BROKER_FETCH_DURATION,
    TA_BROKER_ERRORS_TOTAL,
    PROVIDER_RESPONSE_SIZE,
)
from engine.ta.broker.base import BrokerBase, BrokerCapabilities
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
    Timeframe.H4: "4h",
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
        cache: Optional[RedisCache] = None,
    ) -> None:
        super().__init__(broker_id="twelve_data")
        self.config = config
        self.http_client = http_client
        self.cache = cache
        self.validator = BrokerDataValidator()
        self._rate_limiter = asyncio.Semaphore(self.config.rate_limit_per_minute)

    # ── BrokerBase abstract methods ───────────────────────────────────────

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
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        count: Optional[int] = None,
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

        output_size = min(count or self.config.max_candles_per_request,
                          self.config.max_candles_per_request)

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

        import time as _time
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

    async def get_symbol_info(self, symbol: str) -> dict:
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

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Convert internal symbol format to Twelve Data format.

        Internal:  EURUSD  →  Twelve Data:  EUR/USD
        Metals:    XAUUSD  →  XAU/USD
        """
        raw = symbol.upper().replace("/", "").replace("_", "")

        if len(raw) == 6:
            return f"{raw[:3]}/{raw[3:]}"

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
                timestamp = datetime.strptime(
                    record["datetime"], "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
            except (KeyError, ValueError):
                try:
                    timestamp = datetime.strptime(
                        record["datetime"], "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
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
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        count: Optional[int],
    ) -> str:
        parts = [
            _CACHE_KEY_PREFIX,
            symbol.upper(),
            timeframe.value,
        ]

        if start_time:
            parts.append(f"s:{int(start_time.timestamp())}")
        if end_time:
            parts.append(f"e:{int(end_time.timestamp())}")
        if count:
            parts.append(f"c:{count}")

        return ":".join(parts)

    async def _get_cached(self, key: str) -> Optional[CandleSequence]:
        if self.cache is None:
            return None

        try:
            raw = await self.cache.get(key)
            if raw is None:
                return None

            data = json.loads(raw)
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
                key,
                json.dumps(data),
                ttl=self.config.cache_ttl_seconds,
            )

        except Exception as e:
            logger.warning(
                "twelve_data_cache_write_error",
                extra={"key": key, "error": str(e)},
            )
