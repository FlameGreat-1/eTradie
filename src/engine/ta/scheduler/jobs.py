from datetime import datetime, timedelta
from typing import Optional

from engine.shared.logging import get_logger
from engine.shared.scheduler.base import BaseJob
from engine.ta.constants import Timeframe

logger = get_logger(__name__)


class CandleRefreshJob(BaseJob):
    """
    Candle refresh job - real-time updates.
    
    Fetches latest candles from broker and updates storage.
    Runs on schedule based on timeframe:
    - M1: Every 1 minute
    - M5: Every 5 minutes
    - M15: Every 15 minutes
    - M30: Every 30 minutes
    - H1: Every 1 hour
    - H4: Every 4 hours
    - D1: Every 1 day
    
    Job responsibilities:
    1. Fetch latest candle from broker
    2. Check if candle already exists in storage
    3. Insert new candle if not exists
    4. Trigger analysis if candle is complete
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: Timeframe,
        broker_client: object,
        candle_repository: object,
    ) -> None:
        super().__init__(
            name=f"candle_refresh_{symbol}_{timeframe.value}",
            description=f"Refresh {timeframe.value} candles for {symbol}",
        )
        self.symbol = symbol
        self.timeframe = timeframe
        self.broker_client = broker_client
        self.candle_repository = candle_repository
        self._logger = get_logger(__name__)
    
    async def execute(self) -> dict:
        """Execute candle refresh job."""
        self._logger.info(
            "candle_refresh_job_started",
            extra={
                "symbol": self.symbol,
                "timeframe": self.timeframe.value,
            },
        )
        
        try:
            latest_candle = await self.broker_client.fetch_latest_candle(
                self.symbol,
                self.timeframe.value,
            )
            
            if not latest_candle:
                self._logger.warning(
                    "candle_refresh_no_data",
                    extra={
                        "symbol": self.symbol,
                        "timeframe": self.timeframe.value,
                    },
                )
                return {"status": "no_data", "candles_added": 0}
            
            existing = await self.candle_repository.find_by_symbol_timeframe_timestamp(
                self.symbol,
                self.timeframe.value,
                latest_candle.timestamp,
            )
            
            if existing:
                self._logger.debug(
                    "candle_refresh_already_exists",
                    extra={
                        "symbol": self.symbol,
                        "timeframe": self.timeframe.value,
                        "timestamp": latest_candle.timestamp.isoformat(),
                    },
                )
                return {"status": "already_exists", "candles_added": 0}
            
            await self.candle_repository.create(latest_candle)
            
            self._logger.info(
                "candle_refresh_job_completed",
                extra={
                    "symbol": self.symbol,
                    "timeframe": self.timeframe.value,
                    "candles_added": 1,
                },
            )
            
            return {"status": "success", "candles_added": 1}
        
        except Exception as e:
            self._logger.error(
                "candle_refresh_job_failed",
                extra={
                    "symbol": self.symbol,
                    "timeframe": self.timeframe.value,
                    "error": str(e),
                },
                exc_info=True,
            )
            return {"status": "error", "error": str(e)}


class BackfillJob(BaseJob):
    """
    Backfill job - historical data gaps.
    
    Fetches historical candles to fill gaps in storage.
    Runs on-demand or scheduled for specific time ranges.
    
    Job responsibilities:
    1. Identify missing candles in time range
    2. Fetch missing candles from broker
    3. Batch insert candles into storage
    4. Verify backfill completeness
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
        broker_client: object,
        candle_repository: object,
    ) -> None:
        super().__init__(
            name=f"backfill_{symbol}_{timeframe.value}",
            description=f"Backfill {timeframe.value} candles for {symbol}",
        )
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_time = start_time
        self.end_time = end_time
        self.broker_client = broker_client
        self.candle_repository = candle_repository
        self._logger = get_logger(__name__)
    
    async def execute(self) -> dict:
        """Execute backfill job."""
        self._logger.info(
            "backfill_job_started",
            extra={
                "symbol": self.symbol,
                "timeframe": self.timeframe.value,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
            },
        )
        
        try:
            historical_candles = await self.broker_client.fetch_historical_candles(
                self.symbol,
                self.timeframe.value,
                self.start_time,
                self.end_time,
            )
            
            if not historical_candles:
                self._logger.warning(
                    "backfill_no_data",
                    extra={
                        "symbol": self.symbol,
                        "timeframe": self.timeframe.value,
                    },
                )
                return {"status": "no_data", "candles_added": 0}
            
            new_candles = []
            for candle in historical_candles:
                existing = await self.candle_repository.find_by_symbol_timeframe_timestamp(
                    self.symbol,
                    self.timeframe.value,
                    candle.timestamp,
                )
                
                if not existing:
                    new_candles.append(candle)
            
            if new_candles:
                await self.candle_repository.bulk_create(new_candles)
            
            self._logger.info(
                "backfill_job_completed",
                extra={
                    "symbol": self.symbol,
                    "timeframe": self.timeframe.value,
                    "candles_added": len(new_candles),
                    "total_fetched": len(historical_candles),
                },
            )
            
            return {
                "status": "success",
                "candles_added": len(new_candles),
                "total_fetched": len(historical_candles),
            }
        
        except Exception as e:
            self._logger.error(
                "backfill_job_failed",
                extra={
                    "symbol": self.symbol,
                    "timeframe": self.timeframe.value,
                    "error": str(e),
                },
                exc_info=True,
            )
            return {"status": "error", "error": str(e)}


class BrokerSyncJob(BaseJob):
    """
    Broker sync job - fetch latest data from broker.
    
    Ensures storage is synchronized with broker data.
    Runs periodically to catch any missed updates.
    
    Job responsibilities:
    1. Fetch latest N candles from broker
    2. Compare with storage
    3. Insert missing candles
    4. Update incomplete candles
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: Timeframe,
        lookback_periods: int,
        broker_client: object,
        candle_repository: object,
    ) -> None:
        super().__init__(
            name=f"broker_sync_{symbol}_{timeframe.value}",
            description=f"Sync {timeframe.value} candles for {symbol} with broker",
        )
        self.symbol = symbol
        self.timeframe = timeframe
        self.lookback_periods = lookback_periods
        self.broker_client = broker_client
        self.candle_repository = candle_repository
        self._logger = get_logger(__name__)
    
    async def execute(self) -> dict:
        """Execute broker sync job."""
        self._logger.info(
            "broker_sync_job_started",
            extra={
                "symbol": self.symbol,
                "timeframe": self.timeframe.value,
                "lookback_periods": self.lookback_periods,
            },
        )
        
        try:
            end_time = datetime.utcnow()
            start_time = self._calculate_start_time(end_time)
            
            broker_candles = await self.broker_client.fetch_historical_candles(
                self.symbol,
                self.timeframe.value,
                start_time,
                end_time,
            )
            
            if not broker_candles:
                self._logger.warning(
                    "broker_sync_no_data",
                    extra={
                        "symbol": self.symbol,
                        "timeframe": self.timeframe.value,
                    },
                )
                return {"status": "no_data", "candles_synced": 0}
            
            new_candles = []
            for candle in broker_candles:
                existing = await self.candle_repository.find_by_symbol_timeframe_timestamp(
                    self.symbol,
                    self.timeframe.value,
                    candle.timestamp,
                )
                
                if not existing:
                    new_candles.append(candle)
            
            if new_candles:
                await self.candle_repository.bulk_create(new_candles)
            
            self._logger.info(
                "broker_sync_job_completed",
                extra={
                    "symbol": self.symbol,
                    "timeframe": self.timeframe.value,
                    "candles_synced": len(new_candles),
                },
            )
            
            return {"status": "success", "candles_synced": len(new_candles)}
        
        except Exception as e:
            self._logger.error(
                "broker_sync_job_failed",
                extra={
                    "symbol": self.symbol,
                    "timeframe": self.timeframe.value,
                    "error": str(e),
                },
                exc_info=True,
            )
            return {"status": "error", "error": str(e)}
    
    def _calculate_start_time(self, end_time: datetime) -> datetime:
        """Calculate start time based on timeframe and lookback periods."""
        if self.timeframe == Timeframe.M1:
            return end_time - timedelta(minutes=self.lookback_periods)
        elif self.timeframe == Timeframe.M5:
            return end_time - timedelta(minutes=5 * self.lookback_periods)
        elif self.timeframe == Timeframe.M15:
            return end_time - timedelta(minutes=15 * self.lookback_periods)
        elif self.timeframe == Timeframe.M30:
            return end_time - timedelta(minutes=30 * self.lookback_periods)
        elif self.timeframe == Timeframe.H1:
            return end_time - timedelta(hours=self.lookback_periods)
        elif self.timeframe == Timeframe.H4:
            return end_time - timedelta(hours=4 * self.lookback_periods)
        elif self.timeframe == Timeframe.D1:
            return end_time - timedelta(days=self.lookback_periods)
        else:
            return end_time - timedelta(hours=self.lookback_periods)


class AnalysisTriggerJob(BaseJob):
    """
    Analysis trigger prep job - prepare data for SMC/SnD detection.
    
    Runs after candle updates to trigger technical analysis.
    Prepares candle sequences and triggers orchestrator.
    
    Job responsibilities:
    1. Fetch required candles for HTF and LTF
    2. Build CandleSequence models
    3. Trigger orchestrator for analysis
    4. Handle analysis results
    """
    
    def __init__(
        self,
        symbol: str,
        htf_timeframe: Timeframe,
        ltf_timeframe: Timeframe,
        candle_repository: object,
        orchestrator: object,
    ) -> None:
        super().__init__(
            name=f"analysis_trigger_{symbol}_{htf_timeframe.value}_{ltf_timeframe.value}",
            description=f"Trigger analysis for {symbol} ({htf_timeframe.value}/{ltf_timeframe.value})",
        )
        self.symbol = symbol
        self.htf_timeframe = htf_timeframe
        self.ltf_timeframe = ltf_timeframe
        self.candle_repository = candle_repository
        self.orchestrator = orchestrator
        self._logger = get_logger(__name__)
    
    async def execute(self) -> dict:
        """Execute analysis trigger job."""
        self._logger.info(
            "analysis_trigger_job_started",
            extra={
                "symbol": self.symbol,
                "htf_timeframe": self.htf_timeframe.value,
                "ltf_timeframe": self.ltf_timeframe.value,
            },
        )
        
        try:
            result = await self.orchestrator.analyze(
                self.symbol,
                self.htf_timeframe,
                self.ltf_timeframe,
            )
            
            self._logger.info(
                "analysis_trigger_job_completed",
                extra={
                    "symbol": self.symbol,
                    "htf_timeframe": self.htf_timeframe.value,
                    "ltf_timeframe": self.ltf_timeframe.value,
                    "candidates_generated": result.get("candidates_generated", 0),
                },
            )
            
            return result
        
        except Exception as e:
            self._logger.error(
                "analysis_trigger_job_failed",
                extra={
                    "symbol": self.symbol,
                    "htf_timeframe": self.htf_timeframe.value,
                    "ltf_timeframe": self.ltf_timeframe.value,
                    "error": str(e),
                },
                exc_info=True,
            )
            return {"status": "error", "error": str(e)}
