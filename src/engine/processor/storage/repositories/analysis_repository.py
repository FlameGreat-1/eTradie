"""Repository for persisting analysis outputs.

Extends BaseRepository with processor-specific queries.
Idempotent upsert on analysis_id to handle retries safely.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.db.repositories.base_repository import BaseRepository
from engine.shared.logging import get_logger
from engine.processor.storage.schemas.processor_schema import AnalysisOutputRow

logger = get_logger(__name__)


class AnalysisRepository(BaseRepository[AnalysisOutputRow]):
    """Persists and queries analysis outputs."""

    model = AnalysisOutputRow
    _repo_name = "analysis_output"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def save_analysis(
        self,
        *,
        user_id: str,
        analysis_id: str,
        pair: str,
        direction: str,
        setup_grade: str,
        confluence_score: float,
        confidence: str,
        proceed_to_module_b: str,
        rr_ratio: Optional[float] = None,
        entry_price_low: Optional[float] = None,
        entry_price_high: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        tp1_price: Optional[float] = None,
        tp2_price: Optional[float] = None,
        tp3_price: Optional[float] = None,
        trading_style: str = "",
        session: str = "",
        llm_provider: str = "",
        llm_model: str = "",
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: float = 0.0,
        trace_id: Optional[str] = None,
        raw_output: Optional[dict] = None,
    ) -> None:
        """Idempotent upsert of an analysis output, scoped to user."""
        await self.upsert(
            values={
                "user_id": user_id,
                "analysis_id": analysis_id,
                "pair": pair,
                "direction": direction,
                "setup_grade": setup_grade,
                "confluence_score": confluence_score,
                "confidence": confidence,
                "proceed_to_module_b": proceed_to_module_b,
                "rr_ratio": rr_ratio,
                "entry_price_low": entry_price_low,
                "entry_price_high": entry_price_high,
                "stop_loss_price": stop_loss_price,
                "tp1_price": tp1_price,
                "tp2_price": tp2_price,
                "tp3_price": tp3_price,
                "trading_style": trading_style,
                "session": session,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "status": status,
                "error_message": error_message,
                "duration_ms": duration_ms,
                "trace_id": trace_id,
                "raw_output": raw_output or {},
            },
            index_elements=["analysis_id"],
            update_fields=[
                "direction",
                "setup_grade",
                "confluence_score",
                "confidence",
                "proceed_to_module_b",
                "status",
                "error_message",
                "duration_ms",
                "raw_output",
            ],
        )

    async def get_latest_by_pair(
        self,
        pair: str,
        user_id: str,
        *,
        limit: int = 10,
    ) -> Sequence[AnalysisOutputRow]:
        """Retrieve the most recent analyses for a pair, scoped to user."""
        stmt = (
            select(AnalysisOutputRow)
            .where(
                AnalysisOutputRow.user_id == user_id,
                AnalysisOutputRow.pair == pair,
            )
            .order_by(AnalysisOutputRow.created_at.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def get_by_analysis_id(
        self,
        analysis_id: str,
        user_id: str,
    ) -> Optional[AnalysisOutputRow]:
        """Retrieve a single analysis by its unique analysis_id, scoped to user."""
        stmt = select(AnalysisOutputRow).where(
            AnalysisOutputRow.user_id == user_id,
            AnalysisOutputRow.analysis_id == analysis_id,
        )
        results = await self.execute_query(stmt)
        return results[0] if results else None

    async def list_recent_all(
        self,
        user_id: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[AnalysisOutputRow]:
        """List most recent analyses across all pairs for this user."""
        offset, limit = self._validate_pagination(offset, limit)
        stmt = (
            select(AnalysisOutputRow)
            .where(AnalysisOutputRow.user_id == user_id)
            .order_by(AnalysisOutputRow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def list_filtered(
        self,
        user_id: str,
        *,
        pair: Optional[str] = None,
        status: Optional[str] = None,
        grade: Optional[str] = None,
        provider: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[AnalysisOutputRow], int]:
        """List analyses with filters and return (rows, total_count).

        All filter parameters are optional. When omitted, no filter
        is applied for that dimension. Returns a tuple of the page
        rows and the total count matching the filters (for pagination).
        """
        offset, limit = self._validate_pagination(offset, limit)

        base = select(AnalysisOutputRow).where(AnalysisOutputRow.user_id == user_id)
        base = self._apply_filters(
            base,
            pair=pair,
            status=status,
            grade=grade,
            provider=provider,
            since=since,
            until=until,
        )

        total = await self.count(base)

        page_stmt = (
            base.order_by(AnalysisOutputRow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = await self.execute_query(page_stmt)

        return rows, total

    async def get_stats(
        self,
        user_id: str,
        *,
        pair: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Compute aggregate statistics for the dashboard.

        Returns a dict with:
          total, success_count, no_setup_count, error_count,
          success_rate, avg_confluence_score, avg_duration_ms,
          grade_distribution, provider_distribution, pair_distribution
        """
        T = AnalysisOutputRow  # noqa: N806 – alias for readability

        # -- Scalar aggregates ------------------------------------------------
        scalar_stmt = select(
            func.count(T.id).label("total"),
            func.count(case((T.status == "success", 1))).label("success_count"),
            func.count(case((T.status == "no_setup", 1))).label("no_setup_count"),
            func.count(
                case(
                    (T.status.notin_(["success", "no_setup"]), 1),
                )
            ).label("error_count"),
            func.avg(T.confluence_score).label("avg_confluence_score"),
            func.avg(T.duration_ms).label("avg_duration_ms"),
        ).where(T.user_id == user_id)
        scalar_stmt = self._apply_scalar_filters(
            scalar_stmt,
            pair=pair,
            since=since,
            until=until,
        )

        result = await self._session.execute(scalar_stmt)
        row = result.one()

        total = row.total or 0
        success_count = row.success_count or 0
        success_rate = round(success_count / total, 4) if total > 0 else 0.0

        # -- Grade distribution -----------------------------------------------
        grade_stmt = (
            select(
                T.setup_grade,
                func.count(T.id).label("cnt"),
            )
            .where(T.user_id == user_id)
            .group_by(T.setup_grade)
        )
        grade_stmt = self._apply_scalar_filters(
            grade_stmt,
            pair=pair,
            since=since,
            until=until,
        )
        grade_rows = await self._session.execute(grade_stmt)
        grade_distribution = {g: c for g, c in grade_rows.all()}

        # -- Provider distribution --------------------------------------------
        provider_stmt = (
            select(
                T.llm_provider,
                func.count(T.id).label("cnt"),
            )
            .where(T.user_id == user_id, T.llm_provider != "")
            .group_by(T.llm_provider)
        )
        provider_stmt = self._apply_scalar_filters(
            provider_stmt,
            pair=pair,
            since=since,
            until=until,
        )
        provider_rows = await self._session.execute(provider_stmt)
        provider_distribution = {p: c for p, c in provider_rows.all()}

        # -- Pair distribution ------------------------------------------------
        pair_stmt = (
            select(
                T.pair,
                func.count(T.id).label("cnt"),
            )
            .where(T.user_id == user_id)
            .group_by(T.pair)
        )
        pair_stmt = self._apply_scalar_filters(
            pair_stmt,
            pair=pair,
            since=since,
            until=until,
        )
        pair_rows = await self._session.execute(pair_stmt)
        pair_distribution = {p: c for p, c in pair_rows.all()}

        return {
            "total": total,
            "success_count": success_count,
            "no_setup_count": row.no_setup_count or 0,
            "error_count": row.error_count or 0,
            "success_rate": success_rate,
            "avg_confluence_score": round(row.avg_confluence_score or 0.0, 2),
            "avg_duration_ms": round(row.avg_duration_ms or 0.0, 1),
            "grade_distribution": grade_distribution,
            "provider_distribution": provider_distribution,
            "pair_distribution": pair_distribution,
        }

    # -- Private filter helpers -----------------------------------------------

    @staticmethod
    def _apply_filters(
        stmt: Any,
        *,
        pair: Optional[str],
        status: Optional[str],
        grade: Optional[str],
        provider: Optional[str],
        since: Optional[datetime],
        until: Optional[datetime],
    ) -> Any:
        """Apply WHERE clauses to a SELECT(AnalysisOutputRow) statement."""
        T = AnalysisOutputRow  # noqa: N806
        if pair:
            stmt = stmt.where(T.pair == pair.upper())
        if status:
            stmt = stmt.where(T.status == status)
        if grade:
            stmt = stmt.where(T.setup_grade == grade)
        if provider:
            stmt = stmt.where(T.llm_provider == provider)
        if since:
            stmt = stmt.where(T.created_at >= since)
        if until:
            stmt = stmt.where(T.created_at <= until)
        return stmt

    @staticmethod
    def _apply_scalar_filters(
        stmt: Any,
        *,
        pair: Optional[str],
        since: Optional[datetime],
        until: Optional[datetime],
    ) -> Any:
        """Apply WHERE clauses to aggregate (non-row) statements."""
        T = AnalysisOutputRow  # noqa: N806
        if pair:
            stmt = stmt.where(T.pair == pair.upper())
        if since:
            stmt = stmt.where(T.created_at >= since)
        if until:
            stmt = stmt.where(T.created_at <= until)
        return stmt
