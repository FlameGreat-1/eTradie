import hashlib
import hmac
import ipaddress
from typing import Optional, Any

from pydantic import Field, field_validator

from engine.shared.exceptions import (
    ProviderAuthenticationError,
    ProviderValidationError,
    ProviderError,
)
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    PROVIDER_REQUEST_DURATION,
    PROVIDER_REQUEST_ERRORS,
)

from engine.shared.models.base import FrozenModel
from engine.ta.broker.tradingview.config import TradingViewConfig
from engine.ta.constants import Timeframe, Direction

logger = get_logger(__name__)


class TradingViewAlert(FrozenModel):
    
    symbol: str = Field(min_length=6, max_length=10)
    timeframe: Optional[Timeframe] = None
    direction: Optional[Direction] = None
    price: Optional[float] = Field(default=None, gt=0)
    message: str = Field(default="")
    timestamp: Optional[str] = None
    raw_payload: dict = Field(default_factory=dict)
    
    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        return v.upper().replace("/", "").replace("_", "")


class TradingViewWebhookHandler:
    
    def __init__(self, config: TradingViewConfig) -> None:
        self.config = config
        self._logger = get_logger(__name__)
    
    def validate_ip(self, client_ip: str) -> bool:
        if not self.config.allowed_ips:
            return True
        
        try:
            client_addr = ipaddress.ip_address(client_ip)
            
            for allowed in self.config.allowed_ips:
                try:
                    if "/" in allowed:
                        network = ipaddress.ip_network(allowed)
                        if client_addr in network:
                            return True
                    else:
                        allowed_addr = ipaddress.ip_address(allowed)
                        if client_addr == allowed_addr:
                            return True
                except ValueError:
                    continue
            
            return False
            
        except ValueError:
            self._logger.warning(
                "tradingview_invalid_client_ip",
                extra={"client_ip": client_ip},
            )
            return False
    
    def validate_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        if not self.config.validate_signature:
            return True
        
        if not signature:
            raise ProviderAuthenticationError(
                "Missing signature header",
                details={"header": self.config.signature_header},
            )
        
        expected_signature = hmac.new(
            key=self.config.webhook_secret.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()
        
        is_valid = hmac.compare_digest(signature, expected_signature)
        
        if not is_valid:
            PROVIDER_REQUEST_ERRORS.labels(
                provider="tradingview",
                operation="webhook",
                error_type="invalid_signature",
            ).inc()
            
            raise ProviderAuthenticationError(
                "Invalid webhook signature",
                details={"provided_signature": signature[:16] + "..."},
            )
        
        return True
    
    def validate_payload_size(self, payload: bytes) -> None:
        size = len(payload)
        
        if size > self.config.max_payload_size_bytes:
            PROVIDER_REQUEST_ERRORS.labels(
                provider="tradingview",
                operation="webhook",
                error_type="payload_too_large",
            ).inc()
            
            raise ProviderValidationError(
                "Payload too large",
                details={
                    "size_bytes": size,
                    "max_bytes": self.config.max_payload_size_bytes,
                },
            )
    
    def parse_alert(self, payload: dict) -> TradingViewAlert:
        try:
            symbol = payload.get("ticker") or payload.get("symbol")
            if not symbol:
                raise ProviderValidationError(
                    "Missing symbol in payload",
                    details={"payload": payload},
                )
            
            timeframe_str = payload.get("interval") or payload.get("timeframe")
            timeframe = None
            if timeframe_str:
                timeframe = self._parse_timeframe(timeframe_str)
            
            direction_str = payload.get("strategy.order.action") or payload.get("direction")
            direction = None
            if direction_str:
                direction = self._parse_direction(direction_str)
            
            price = payload.get("close") or payload.get("price")
            if price:
                price = float(price)
            
            message = payload.get("message", "")
            timestamp = payload.get("time") or payload.get("timestamp")
            
            alert = TradingViewAlert(
                symbol=symbol,
                timeframe=timeframe,
                direction=direction,
                price=price,
                message=message,
                timestamp=timestamp,
                raw_payload=payload,
            )
            
            self._logger.info(
                "tradingview_alert_parsed",
                extra={
                    "symbol": alert.symbol,
                    "timeframe": alert.timeframe,
                    "direction": alert.direction,
                    "price": alert.price,
                },
            )
            
            return alert
            
        except (KeyError, ValueError, TypeError) as e:
            PROVIDER_REQUEST_ERRORS.labels(
                provider="tradingview",
                operation="webhook",
                error_type="parse_error",
            ).inc()
            
            raise ProviderValidationError(
                f"Failed to parse alert payload: {e}",
                details={"payload": payload, "error": str(e)},
            ) from e
    
    def _parse_timeframe(self, timeframe_str: str) -> Optional[Timeframe]:
        timeframe_map = {
            "1": Timeframe.M1,
            "1m": Timeframe.M1,
            "5": Timeframe.M5,
            "5m": Timeframe.M5,
            "15": Timeframe.M15,
            "15m": Timeframe.M15,
            "30": Timeframe.M30,
            "30m": Timeframe.M30,
            "60": Timeframe.H1,
            "1h": Timeframe.H1,
            "240": Timeframe.H4,
            "4h": Timeframe.H4,
            "D": Timeframe.D1,
            "1D": Timeframe.D1,
            "W": Timeframe.W1,
            "1W": Timeframe.W1,
            "M": Timeframe.MN1,
            "1M": Timeframe.MN1,
        }
        
        return timeframe_map.get(timeframe_str.upper())
    
    def _parse_direction(self, direction_str: str) -> Optional[Direction]:
        direction_str_upper = direction_str.upper()
        
        if direction_str_upper in ("BUY", "LONG", "BULLISH"):
            return Direction.BULLISH
        elif direction_str_upper in ("SELL", "SHORT", "BEARISH"):
            return Direction.BEARISH
        
        return None
    
    async def handle_webhook(
        self,
        payload: bytes,
        signature: Optional[str],
        client_ip: str,
    ) -> TradingViewAlert:
        import time
        start_time = time.time()
        
        try:
            if not self.validate_ip(client_ip):
                PROVIDER_REQUEST_ERRORS.labels(
                    provider="tradingview",
                    operation="webhook",
                    error_type="ip_blocked",
                ).inc()
                
                raise ProviderAuthenticationError(
                    "IP address not allowed",
                    details={"client_ip": client_ip},
                )
            
            self.validate_payload_size(payload)
            
            if self.config.validate_signature:
                self.validate_signature(payload, signature or "")
            
            import json
            payload_dict = json.loads(payload.decode("utf-8"))
            
            alert = self.parse_alert(payload_dict)
            
            duration = time.time() - start_time
            PROVIDER_REQUEST_DURATION.labels(
                provider="tradingview",
                operation="webhook",
            ).observe(duration)
            
            return alert
            
        except (ProviderAuthenticationError, ProviderValidationError):
            raise
        except Exception as e:
            PROVIDER_REQUEST_ERRORS.labels(
                provider="tradingview",
                operation="webhook",
                error_type=type(e).__name__,
            ).inc()
            
            self._logger.error(
                "tradingview_webhook_failed",
                extra={
                    "client_ip": client_ip,
                    "error": str(e),
                },
                exc_info=True,
            )
            
            raise ProviderError(
                f"Webhook handling failed: {e}",
                details={"error": str(e)},
            ) from e
