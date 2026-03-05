from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from engine.macro.storage.repositories.calendar.event import CalendarRepository
from engine.macro.storage.repositories.central_bank.event import CentralBankRepository
from engine.macro.storage.repositories.cot.report import COTRepository
from engine.macro.storage.repositories.dxy.snapshot import DXYRepository
from engine.macro.storage.repositories.economic.release import EconomicReleaseRepository
from engine.macro.storage.repositories.intermarket.snapshot import IntermarketRepository
from engine.macro.storage.repositories.news.item import NewsRepository

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/health")
async def macro_health() -> dict:
    return {"status": "ok", "module": "macro"}


@router.get("/data/central-bank")
async def get_central_bank_data(
    bank: str | None = None,
    limit: int = 20,
    session: AsyncSession = Depends(),
) -> list[dict]:
    repo = CentralBankRepository(session)
    if bank:
        rows = await repo.get_latest_by_bank(bank, limit=limit)
    else:
        rows = await repo.list_all(limit=limit)
    return [{"id": str(r.id), "bank": r.bank, "event_type": r.event_type,
             "title": r.title, "tone": r.tone, "event_timestamp": r.event_timestamp.isoformat()} for r in rows]


@router.get("/data/cot")
async def get_cot_data(
    currency: str | None = None,
    session: AsyncSession = Depends(),
) -> list[dict]:
    repo = COTRepository(session)
    if currency:
        row = await repo.get_latest_by_currency(currency)
        rows = [row] if row else []
    else:
        rows = await repo.get_latest_all_currencies()
    return [{"id": str(r.id), "currency": r.currency, "non_commercial_net": r.non_commercial_net,
             "open_interest": r.open_interest, "report_date": r.report_date.isoformat()} for r in rows]


@router.get("/data/economic")
async def get_economic_data(
    currency: str | None = None,
    limit: int = 30,
    session: AsyncSession = Depends(),
) -> list[dict]:
    repo = EconomicReleaseRepository(session)
    since = datetime.now(UTC) - timedelta(days=30)
    if currency:
        rows = await repo.get_by_currency(currency, since=since, limit=limit)
    else:
        rows = await repo.get_recent_high_impact(since)
    return [{"id": str(r.id), "currency": r.currency, "indicator": r.indicator,
             "actual": r.actual, "forecast": r.forecast, "surprise_direction": r.surprise_direction,
             "release_time": r.release_time.isoformat()} for r in rows]


@router.get("/data/news")
async def get_news_data(
    limit: int = 50,
    session: AsyncSession = Depends(),
) -> list[dict]:
    repo = NewsRepository(session)
    since = datetime.now(UTC) - timedelta(hours=24)
    rows = await repo.get_recent(since=since, limit=limit)
    return [{"id": str(r.id), "headline": r.headline, "source": r.source,
             "impact": r.impact, "published_at": r.published_at.isoformat()} for r in rows]


@router.get("/data/calendar")
async def get_calendar_data(
    hours_ahead: int = 48,
    session: AsyncSession = Depends(),
) -> list[dict]:
    repo = CalendarRepository(session)
    rows = await repo.get_upcoming(from_time=datetime.now(UTC), hours_ahead=hours_ahead)
    return [{"id": str(r.id), "event_name": r.event_name, "currency": r.currency,
             "impact": r.impact, "event_time": r.event_time.isoformat()} for r in rows]


@router.get("/data/dxy")
async def get_dxy_data(
    session: AsyncSession = Depends(),
) -> dict | None:
    repo = DXYRepository(session)
    row = await repo.get_latest()
    if not row:
        return None
    return {"id": str(row.id), "value": row.value, "bias": row.bias,
            "analyzed_at": row.analyzed_at.isoformat()}


@router.get("/data/intermarket")
async def get_intermarket_data(
    session: AsyncSession = Depends(),
) -> dict | None:
    repo = IntermarketRepository(session)
    row = await repo.get_latest()
    if not row:
        return None
    return {"id": str(row.id), "gold_price": row.gold_price, "oil_price": row.oil_price,
            "us10y_yield": row.us10y_yield, "dxy_value": row.dxy_value,
            "snapshot_at": row.snapshot_at.isoformat()}
