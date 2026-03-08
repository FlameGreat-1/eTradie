from typing import Optional, Dict

from engine.shared.cache.redis_cache import RedisCache
from engine.shared.exceptions import ConfigurationError
from engine.shared.http.client import HttpClient
from engine.shared.logging import get_logger
from engine.ta.broker.base import BrokerBase
from engine.ta.broker.mt5.client import MT5Client
from engine.ta.broker.mt5.config import MT5Config
from engine.ta.broker.twelve_data.client import TwelveDataClient
from engine.ta.broker.twelve_data.config import TwelveDataConfig
from engine.ta.config import TAConfig

logger = get_logger(__name__)


class BrokerRegistry:
    
    def __init__(
        self,
        ta_config: TAConfig,
        http_client: HttpClient,
        cache: Optional[RedisCache] = None,
    ) -> None:
        self.ta_config = ta_config
        self.http_client = http_client
        self.cache = cache
        self._brokers: Dict[str, BrokerBase] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        if self._initialized:
            return
        
        try:
            if self.ta_config.primary_broker == "mt5":
                mt5_config = MT5Config()
                if mt5_config.enabled:
                    mt5_client = MT5Client(config=mt5_config)
                    self._brokers["mt5"] = mt5_client
                    logger.info("broker_registered", extra={"broker": "mt5"})
            
            if self.ta_config.fallback_broker == "twelve_data" or self.ta_config.primary_broker == "twelve_data":
                twelve_data_config = TwelveDataConfig()
                if twelve_data_config.enabled:
                    twelve_data_client = TwelveDataClient(
                        config=twelve_data_config,
                        http_client=self.http_client,
                        cache=self.cache,
                    )
                    self._brokers["twelve_data"] = twelve_data_client
                    logger.info("broker_registered", extra={"broker": "twelve_data"})
            
            if not self._brokers:
                raise ConfigurationError(
                    "No brokers configured",
                    details={
                        "primary_broker": self.ta_config.primary_broker,
                        "fallback_broker": self.ta_config.fallback_broker,
                    },
                )
            
            self._initialized = True
            
            logger.info(
                "broker_registry_initialized",
                extra={
                    "brokers": list(self._brokers.keys()),
                    "primary": self.ta_config.primary_broker,
                    "fallback": self.ta_config.fallback_broker,
                },
            )
            
        except Exception as e:
            logger.error(
                "broker_registry_initialization_failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise
    
    def get_broker(self, broker_id: Optional[str] = None) -> BrokerBase:
        if not self._initialized:
            raise ConfigurationError(
                "Broker registry not initialized",
                details={"call_initialize_first": True},
            )
        
        if broker_id is None:
            broker_id = self.ta_config.primary_broker
        
        broker = self._brokers.get(broker_id)
        
        if broker is None:
            raise ConfigurationError(
                f"Broker not found: {broker_id}",
                details={
                    "broker_id": broker_id,
                    "available_brokers": list(self._brokers.keys()),
                },
            )
        
        return broker
    
    def get_primary_broker(self) -> BrokerBase:
        return self.get_broker(self.ta_config.primary_broker)
    
    def get_fallback_broker(self) -> BrokerBase:
        return self.get_broker(self.ta_config.fallback_broker)
    
    async def health_check_all(self) -> Dict[str, bool]:
        results = {}
        
        for broker_id, broker in self._brokers.items():
            try:
                is_healthy = await broker.health_check()
                results[broker_id] = is_healthy
                
                logger.info(
                    "broker_health_check",
                    extra={
                        "broker": broker_id,
                        "healthy": is_healthy,
                    },
                )
                
            except Exception as e:
                results[broker_id] = False
                
                logger.error(
                    "broker_health_check_failed",
                    extra={
                        "broker": broker_id,
                        "error": str(e),
                    },
                )
        
        return results
    
    async def shutdown(self) -> None:
        for broker_id, broker in self._brokers.items():
            try:
                if hasattr(broker, "shutdown"):
                    await broker.shutdown()
                
                logger.info(
                    "broker_shutdown",
                    extra={"broker": broker_id},
                )
                
            except Exception as e:
                logger.error(
                    "broker_shutdown_failed",
                    extra={
                        "broker": broker_id,
                        "error": str(e),
                    },
                )
        
        self._brokers.clear()
        self._initialized = False


_registry: Optional[BrokerRegistry] = None


async def get_broker_registry(
    ta_config: TAConfig,
    http_client: HttpClient,
    cache: Optional[RedisCache] = None,
) -> BrokerRegistry:
    global _registry
    
    if _registry is None:
        _registry = BrokerRegistry(
            ta_config=ta_config,
            http_client=http_client,
            cache=cache,
        )
        await _registry.initialize()
    
    return _registry


def get_broker(broker_id: Optional[str] = None) -> BrokerBase:
    if _registry is None:
        raise ConfigurationError(
            "Broker registry not initialized",
            details={"call_get_broker_registry_first": True},
        )
    
    return _registry.get_broker(broker_id)
