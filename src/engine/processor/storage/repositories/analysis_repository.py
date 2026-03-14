"""Repository for persisting analysis outputs.

Extends BaseRepository with processor-specific queries.
Idempotent upsert on analysis_id to handle retries safely.
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
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
        """Idempotent upsert of an analysis output."""
        await self.upsert(
            values={
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
                "direction", "setup_grade", "confluence_score",
                "confidence", "proceed_to_module_b", "status",
                "error_message", "duration_ms", "raw_output",
            ],
        )

    async def get_latest_by_pair(
        self,
        pair: str,
        *,
        limit: int = 10,
    ) -> Sequence[AnalysisOutputRow]:
        """Retrieve the most recent analyses for a pair."""
        stmt = (
            select(AnalysisOutputRow)
            .where(AnalysisOutputRow.pair == pair)
            .order_by(AnalysisOutputRow.created_at.desc())
            .limit(limit)
        )
        return await self.execute_query(stmt)

    async def get_by_analysis_id(
        self,
        analysis_id: str,
    ) -> Optional[AnalysisOutputRow]:
        """Retrieve a single analysis by its unique analysis_id."""
        stmt = select(AnalysisOutputRow).where(
            AnalysisOutputRow.analysis_id == analysis_id,
        )
        results = await self.execute_query(stmt)
        return results[0] if results else None
