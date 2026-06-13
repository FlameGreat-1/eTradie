"""
Automated data retention pruner.

Deletes expired rows from TA, Processor, and Macro tables based on configurable
retention windows. All pruned data is self-healing — external sources
repopulate on the next scheduled collection cycle.

Retention Policy:
    TA (user-scoped):
        candles               → 3 days
        technical_snapshots   → 24 hours
        candidates (inactive) → 3 days
        candidates (active)   → kept indefinitely

    Processor (user-scoped):
        analysis_outputs      → 7 days
        analysis_audit_logs   → 7 days

    Macro (global):
        calendar_events       → 7 days
        central_bank_events   → 7 days
        cot_reports           → 7 days
        dxy_snapshots         → 7 days
        economic_releases     → 7 days
        intermarket_snapshots → 7 days
        sentiment_readings    → 7 days

Design:
    Uses raw SQL DELETE with WHERE created_at < cutoff to avoid
    loading entire ORM objects into memory. This is critical for
    pruning hundreds of thousands of rows without OOM.

    Each table prune is wrapped in its own transaction to prevent
    a failure in one table from blocking others.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete

# Macro schemas
from engine.macro.storage.schemas.calendar import CalendarEventRow
from engine.macro.storage.schemas.central_bank import CentralBankEventRow
from engine.macro.storage.schemas.cot import COTReportRow
from engine.macro.storage.schemas.dxy import DXYSnapshotRow
from engine.macro.storage.schemas.economic import EconomicReleaseRow
from engine.macro.storage.schemas.intermarket import IntermarketSnapshotRow
from engine.macro.storage.schemas.sentiment import SentimentReadingRow

# Processor schemas
from engine.processor.storage.schemas.processor_schema import (
    AnalysisAuditLogRow,
    AnalysisOutputRow,
)
from engine.shared.db import DatabaseManager
from engine.shared.db.migrations._schema_registry import Base
from engine.shared.logging import get_logger
from engine.ta.storage.schemas.candidate import CandidateSchema

# TA schemas
from engine.ta.storage.schemas.candle import CandleSchema
from engine.ta.storage.schemas.snapshot import SnapshotSchema

logger = get_logger(__name__)

# ── Retention windows ────────────────────────────────────────────────
# All values in hours for consistency.

# TA data (user-scoped) — self-heals via broker re-fetch.
RETENTION_CANDLES_HOURS = 72  # 3 days
RETENTION_SNAPSHOTS_HOURS = 24  # 24 hours
RETENTION_CANDIDATES_INACTIVE_HOURS = 72  # 3 days

# Processor data (user-scoped) — heavy JSON reasoning, kept for a week for review
RETENTION_PROCESSOR_HOURS = 168  # 7 days

# Macro data (global) — self-heals via scheduler re-collection.
RETENTION_MACRO_HOURS = 168  # 7 days (all macro tables)


class RetentionPruner:
    """Prunes expired data from TA and Macro tables.

    Each table prune runs in its own session/transaction so that
    a failure in one table does not block pruning of others.

    Usage::

        pruner = RetentionPruner(db)
        await pruner.prune_all()
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def prune_all(self) -> dict[str, int]:
        """Run all pruning operations and return per-table deletion counts.

        Returns:
            Dict mapping table name to number of deleted rows.
        """
        results: dict[str, int] = {}

        logger.info("retention_prune_started")

        # ── TA tables ────────────────────────────────────────────
        results["candles"] = await self._prune_ta_candles()
        results["technical_snapshots"] = await self._prune_ta_snapshots()
        results["candidates_inactive"] = await self._prune_ta_candidates_inactive()

        # ── Processor tables ─────────────────────────────────────
        results["analysis_outputs"] = await self._prune_processor_table(
            AnalysisOutputRow,
            "created_at",
            RETENTION_PROCESSOR_HOURS,
        )
        results["analysis_audit_logs"] = await self._prune_processor_table(
            AnalysisAuditLogRow,
            "created_at",
            RETENTION_PROCESSOR_HOURS,
        )

        # ── Macro tables ─────────────────────────────────────────
        results["calendar_events"] = await self._prune_macro_table(
            CalendarEventRow,
            "created_at",
            RETENTION_MACRO_HOURS,
        )
        results["central_bank_events"] = await self._prune_macro_table(
            CentralBankEventRow,
            "created_at",
            RETENTION_MACRO_HOURS,
        )
        results["cot_reports"] = await self._prune_macro_table(
            COTReportRow,
            "created_at",
            RETENTION_MACRO_HOURS,
        )
        results["dxy_snapshots"] = await self._prune_macro_table(
            DXYSnapshotRow,
            "created_at",
            RETENTION_MACRO_HOURS,
        )
        results["economic_releases"] = await self._prune_macro_table(
            EconomicReleaseRow,
            "created_at",
            RETENTION_MACRO_HOURS,
        )
        results["intermarket_snapshots"] = await self._prune_macro_table(
            IntermarketSnapshotRow,
            "created_at",
            RETENTION_MACRO_HOURS,
        )
        # Sentiment rows are UPSERTED on (currency, source): created_at keeps
        # its original insert time while collected_at advances every cycle.
        # Prune by collected_at so a continuously-updated live row is not
        # deleted just because it was first inserted > 7 days ago.
        results["sentiment_readings"] = await self._prune_macro_table(
            SentimentReadingRow,
            "collected_at",
            RETENTION_MACRO_HOURS,
        )

        total_deleted = sum(results.values())
        logger.info(
            "retention_prune_completed",
            extra={
                "total_deleted": total_deleted,
                "per_table": results,
            },
        )

        return results

    # ── TA pruning ───────────────────────────────────────────────

    async def _prune_ta_candles(self) -> int:
        """Delete candles older than RETENTION_CANDLES_HOURS."""
        cutoff = datetime.now(UTC) - timedelta(hours=RETENTION_CANDLES_HOURS)
        return await self._delete_rows(
            CandleSchema,
            CandleSchema.created_at < cutoff,
            "candles",
        )

    async def _prune_ta_snapshots(self) -> int:
        """Delete technical snapshots older than RETENTION_SNAPSHOTS_HOURS."""
        cutoff = datetime.now(UTC) - timedelta(hours=RETENTION_SNAPSHOTS_HOURS)
        return await self._delete_rows(
            SnapshotSchema,
            SnapshotSchema.created_at < cutoff,
            "technical_snapshots",
        )

    async def _prune_ta_candidates_inactive(self) -> int:
        """Delete inactive candidates older than RETENTION_CANDIDATES_INACTIVE_HOURS.

        Active candidates (is_active=True) are NEVER pruned because they
        represent live trade setups that may be referenced by the
        Execution watcher.
        """
        cutoff = datetime.now(UTC) - timedelta(
            hours=RETENTION_CANDIDATES_INACTIVE_HOURS,
        )
        return await self._delete_rows(
            CandidateSchema,
            and_(
                CandidateSchema.is_active == False,  # noqa: E712
                CandidateSchema.created_at < cutoff,
            ),
            "candidates_inactive",
        )

    # ── Processor pruning ────────────────────────────────────────

    async def _prune_processor_table(
        self,
        schema_class: type[Base],
        timestamp_column: str,
        retention_hours: int,
    ) -> int:
        """Delete processor rows older than retention_hours."""
        cutoff = datetime.now(UTC) - timedelta(hours=retention_hours)
        column = getattr(schema_class, timestamp_column)
        table_name = schema_class.__tablename__
        return await self._delete_rows(
            schema_class,
            column < cutoff,
            table_name,
        )

    # ── Macro pruning ────────────────────────────────────────────

    async def _prune_macro_table(
        self,
        schema_class: type[Base],
        timestamp_column: str,
        retention_hours: int,
    ) -> int:
        """Delete macro rows older than retention_hours.

        Uses getattr to dynamically access the timestamp column
        because macro schemas use different column names (created_at,
        published_at, etc.).
        """
        cutoff = datetime.now(UTC) - timedelta(hours=retention_hours)
        column = getattr(schema_class, timestamp_column)
        table_name = schema_class.__tablename__
        return await self._delete_rows(
            schema_class,
            column < cutoff,
            table_name,
        )

    # ── Core deletion engine ─────────────────────────────────────

    async def _delete_rows(
        self,
        schema_class: type,
        condition,
        label: str,
    ) -> int:
        """Execute a bulk DELETE within its own transaction.

        Each table prune gets its own session so that a failure
        in one table does not block others.

        Args:
            schema_class: The SQLAlchemy ORM model class.
            condition: SQLAlchemy WHERE clause.
            label: Human-readable table label for logging.

        Returns:
            Number of rows deleted.
        """
        try:
            async with self._db.session() as session:
                result = await session.execute(delete(schema_class).where(condition))
                deleted = result.rowcount
                await session.commit()

                if deleted > 0:
                    logger.info(
                        "retention_table_pruned",
                        extra={
                            "table": label,
                            "rows_deleted": deleted,
                        },
                    )
                else:
                    logger.debug(
                        "retention_table_no_expired_rows",
                        extra={"table": label},
                    )

                return deleted

        except Exception as exc:
            logger.error(
                "retention_table_prune_failed",
                extra={
                    "table": label,
                    "error": str(exc),
                },
                exc_info=True,
            )
            return 0
