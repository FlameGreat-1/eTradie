"""
TA scheduling.

Defines TA-specific job definitions for:
- Candle refresh (real-time updates)
- Backfill (historical data gaps)
- Broker sync (fetch latest data from broker)
- Analysis trigger prep (prepare data for SMC/SnD detection)

All jobs use engine.shared.scheduler infrastructure.
Jobs are registered with the shared scheduler and executed on schedule.

Job execution flow:
1. Scheduler triggers job at scheduled time
2. Job fetches required data (candles, snapshots)
3. Job performs TA-specific operations
4. Job persists results to storage
5. Job logs execution metrics
"""

from engine.ta.scheduler.jobs import (
    CandleRefreshJob,
    BackfillJob,
    BrokerSyncJob,
    AnalysisTriggerJob,
)

__all__ = [
    "CandleRefreshJob",
    "BackfillJob",
    "BrokerSyncJob",
    "AnalysisTriggerJob",
]
