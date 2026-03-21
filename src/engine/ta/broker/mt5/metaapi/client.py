"""MetaApi.cloud REST client implementing BrokerBase.

Communicates with MetaApi cloud servers to fetch candle data,
symbol info, and health status.  Uses the shared HttpClient
for all HTTP calls (inheriting circuit breaker, retries, metrics).

No local MT5 terminal or Windows dependency required.
"""

from __future__ import annotations

import asyncio
import time as _time
from datetime import datetime, timezone
from typing import Any, Optional

from engine.shared.exceptions import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from engine.shared.http.client import HttpClient
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    PROVIDER_RESPONSE_SIZE,
    TA_BROKER_ERRORS_TOTAL,
    TA_BROKER_FETCH_DURATION,
)
from engine.ta.broker.base import BrokerBase, BrokerCapabilities
from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.validator import BrokerDataValidator
from engine.ta.constants import Timeframe
from engine.ta.models.candle import Candle, CandleSequence

logger = get_logger(__name__)

# MetaApi uses standard timeframe strings.
_METAAPI_TIMEFRAME_MAP: dict[Timeframe, str] = {
    Timeframe.M1: "1m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.M30: "30m",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1d",
    Timeframe.W1: "1w",
    Timeframe.MN1: "1mn",
}


class MetaApiClient(BrokerBase):
    """Cloud-based MT5 data provider via MetaApi.cloud REST API."""

    _BASE_URL = "https://mt-client-api-v1.agiliumtrade.agiliumtrade.ai"

    def __init__(
        self,
        config: MT5Config,
        http_client: HttpClient,
    ) -> None:
        super().__init__(broker_id="mt5")
        self.config = config
        self._http = http_client
        self.validator = BrokerDataValidator()
        self._account_id = config.metaapi_account_id
        self._auth_headers = {
            "auth-token": config.metaapi_token,
        }

    # -- Helpers ---------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._BASE_URL}/users/current/accounts/{self._account_id}{path}"

    async def _api_get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        category: str = "candles",
    ) -> Any:
        """Execute authenticated GET against MetaApi."""
        return await self._http.get(
            self._url(path),
            provider_name="metaapi",
            category=category,
            headers=self._auth_headers,
            params=params,
            timeout_override=self.config.timeout_seconds,
        )

    # -- BrokerBase implementation ---------------------------------------------

    async def get_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_realtime=True,
            supports_historical=True,
            supports_tick_data=self.config.enable_tick_data,
            supports_symbol_info=True,
            max_candles_per_request=self.config.max_candles_per_request,
            rate_limit_per_minute=60,
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

        ma_tf = _METAAPI_TIMEFRAME_MAP.get(timeframe)
        if ma_tf is None:
            raise ProviderError(
                f"Unsupported timeframe: {timeframe}",
                details={"timeframe": timeframe},
            )

        start_timer = _time.monotonic()

        try:
            params: dict[str, Any] = {}
            if start_time:
                params["startTime"] = start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            if count:
                params["limit"] = min(count, self.config.max_candles_per_request)
            else:
                params["limit"] = 500

            path = f"/historical-market-data/symbols/{symbol}/timeframes/{ma_tf}/candles"
            raw = await self._api_get(path, params=params, category="candles")

            duration = _time.monotonic() - start_timer

            TA_BROKER_FETCH_DURATION.labels(
                broker="mt5",
                symbol=symbol,
                timeframe=timeframe.value,
            ).observe(duration)

            if not raw or not isinstance(raw, list) or len(raw) == 0:
                TA_BROKER_ERRORS_TOTAL.labels(
                    broker="mt5",
                    error_type="no_data",
                ).inc()
                raise ProviderResponseError(
                    "No data returned from MetaApi",
                    details={"symbol": symbol, "timeframe": timeframe},
                )

            candles = self._parse_candles(raw, symbol, timeframe)

            # Apply time range filter if both bounds provided.
            if start_time and end_time:
                candles = [
                    c for c in candles
                    if start_time <= c.timestamp <= end_time
                ]

            if not candles:
                raise ProviderResponseError(
                    "No candles within requested time range",
                    details={
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "start_time": start_time.isoformat() if start_time else None,
                        "end_time": end_time.isoformat() if end_time else None,
                    },
                )

            sequence = CandleSequence(
                symbol=symbol,
                timeframe=timeframe,
                candles=candles,
            )

            self.validator.validate_sequence(sequence)

            PROVIDER_RESPONSE_SIZE.labels(
                provider="mt5",
                category="candles",
            ).observe(len(candles))

            logger.info(
                "metaapi_candles_fetched",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "count": len(candles),
                    "duration_seconds": duration,
                },
            )

            return sequence

        except ProviderError:
            raise
        except Exception as e:
            TA_BROKER_ERRORS_TOTAL.labels(
                broker="mt5",
                error_type=type(e).__name__,
            ).inc()

            logger.error(
                "metaapi_fetch_candles_failed",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "error": str(e),
                },
                exc_info=True,
            )

            raise ProviderError(
                f"MetaApi fetch candles failed: {e}",
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
        path = f"/symbols/{symbol}/specification"
        try:
            info = await self._api_get(path, category="symbol_info")
        except Exception as e:
            raise ProviderResponseError(
                f"Symbol info not found: {e}",
                details={"symbol": symbol, "error": str(e)},
            ) from e

        if not info or not isinstance(info, dict):
            raise ProviderResponseError(
                "Empty symbol info from MetaApi",
                details={"symbol": symbol},
            )

        return {
            "symbol": info.get("symbol", symbol),
            "description": info.get("description", ""),
            "point": info.get("point", 0.0),
            "digits": info.get("digits", 5),
            "spread": info.get("spread", 0),
            "trade_contract_size": info.get("contractSize", 100000),
            "volume_min": info.get("minVolume", 0.01),
            "volume_max": info.get("maxVolume", 100.0),
            "volume_step": info.get("volumeStep", 0.01),
        }

    async def validate_symbol(self, symbol: str) -> bool:
        try:
            await self.get_symbol_info(symbol)
            return True
        except ProviderResponseError:
            return False

    async def health_check(self) -> bool:
        try:
            info = await self._http.get(
                f"{self._BASE_URL}/users/current/accounts/{self._account_id}",
                provider_name="metaapi",
                category="health",
                headers=self._auth_headers,
                timeout_override=10,
            )
            if not isinstance(info, dict):
                return False
            state = info.get("state", "")
            connection_status = info.get("connectionStatus", "")
            return state == "DEPLOYED" and connection_status == "CONNECTED"
        except Exception as e:
            logger.error(
                "metaapi_health_check_failed",
                extra={"error": str(e)},
            )
            return False

    async def shutdown(self) -> None:
        logger.info("metaapi_shutdown_complete")

    # -- Parsing ---------------------------------------------------------------

    @staticmethod
    def _parse_candles(
        raw: list[dict[str, Any]],
        symbol: str,
        timeframe: Timeframe,
    ) -> list[Candle]:
        """Convert MetaApi candle dicts to domain Candle models.

        MetaApi returns candles as:
        {
            "time": "2024-01-15T10:00:00.000Z",
            "brokerTime": "2024-01-15 12:00:00.000",
            "open": 1.09500,
            "high": 1.09600,
            "low": 1.09400,
            "close": 1.09550,
            "tickVolume": 1234
        }
        """
        candles: list[Candle] = []
        for bar in raw:
            time_str = bar.get("time", "")
            if not time_str:
                continue

            # Parse ISO timestamp from MetaApi.
            ts = datetime.fromisoformat(time_str.replace("Z", "+00:00"))

            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=ts,
                open=float(bar["open"]),
                high=float(bar["high"]),
                low=float(bar["low"]),
                close=float(bar["close"]),
                volume=float(bar.get("tickVolume", 0)),
            )
            candles.append(candle)

        return candles
