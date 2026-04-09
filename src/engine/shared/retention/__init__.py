"""
Data retention management.

Provides automated pruning of ephemeral platform data that
accumulates without bounds. Separates retention into two domains:

- **TA data** (user-scoped): candles, snapshots, candidates
- **Macro data** (global): news, calendar, COT, etc.

All pruned data is self-healing — the system re-fetches from
external sources on the next scheduled cycle.
"""

from engine.shared.retention.pruner import RetentionPruner
from engine.shared.retention.scheduler_jobs import register_retention_jobs

__all__ = [
    "RetentionPruner",
    "register_retention_jobs",
]
