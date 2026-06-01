from __future__ import annotations

from datetime import UTC, datetime

from engine.shared.logging import get_logger
from engine.shared.models.events import COTSignalStrength
from engine.macro.collectors.base import BaseCollector
from engine.macro.models.collector.cot import COTDataSet
from engine.macro.models.provider.cot import COTPosition, COTPositionEnriched
from engine.macro.storage.repositories.cot.report import COTRepository

logger = get_logger(__name__)

_EXTREME_HIGH_PERCENTILE = 90.0
_EXTREME_LOW_PERCENTILE = 10.0


def _compute_percentile(value: int, min_val: int, max_val: int) -> float:
    if max_val == min_val:
        return 50.0
    return round(((value - min_val) / (max_val - min_val)) * 100.0, 2)


def _classify_signal(percentile: float, net: int) -> COTSignalStrength:
    if percentile >= 90:
        return (
            COTSignalStrength.EXTREME_LONG
            if net > 0
            else COTSignalStrength.EXTREME_SHORT
        )
    if percentile >= 75:
        return (
            COTSignalStrength.STRONG_LONG if net > 0 else COTSignalStrength.STRONG_SHORT
        )
    if percentile >= 60:
        return (
            COTSignalStrength.MODERATE_LONG
            if net > 0
            else COTSignalStrength.MODERATE_SHORT
        )
    if percentile <= 10:
        return (
            COTSignalStrength.EXTREME_SHORT
            if net < 0
            else COTSignalStrength.EXTREME_LONG
        )
    if percentile <= 25:
        return (
            COTSignalStrength.STRONG_SHORT if net < 0 else COTSignalStrength.STRONG_LONG
        )
    if percentile <= 40:
        return (
            COTSignalStrength.MODERATE_SHORT
            if net < 0
            else COTSignalStrength.MODERATE_LONG
        )
    return COTSignalStrength.NEUTRAL


def _detect_divergence(commercial_net: int, non_commercial_net: int) -> bool:
    if commercial_net == 0 or non_commercial_net == 0:
        return False
    return (commercial_net > 0) != (non_commercial_net > 0)


class COTCollector(BaseCollector):
    collector_name = "cot"
    cache_namespace = "cot"
    cache_model = COTDataSet

    async def _do_collect(self) -> COTDataSet:
        report = await self._fetch_with_failover(self._providers)
        positions = report.positions if report else []
        tff_positions = report.tff_positions if report else []

        enriched: list[COTPositionEnriched] = []
        previous_positions: list[COTPosition] = []
        wow_shifts: dict[str, int] = {}
        extremes_flagged: list[str] = []

        async with self._db.session() as session:
            repo = COTRepository(session)

            for p in positions:
                prev_net = await repo.get_previous_net(
                    p.currency.value, p.report_date,
                )
                wow = (p.non_commercial_net - prev_net) if prev_net is not None else 0

                min_net, max_net = await repo.get_52_week_net_range(
                    p.currency.value,
                )
                percentile = _compute_percentile(p.non_commercial_net, min_net, max_net)
                extreme = (
                    percentile >= _EXTREME_HIGH_PERCENTILE
                    or percentile <= _EXTREME_LOW_PERCENTILE
                )
                signal = _classify_signal(percentile, p.non_commercial_net)
                divergence = _detect_divergence(p.commercial_net, p.non_commercial_net)

                enriched_pos = COTPositionEnriched(
                    currency=p.currency,
                    contract_name=p.contract_name,
                    non_commercial_long=p.non_commercial_long,
                    non_commercial_short=p.non_commercial_short,
                    non_commercial_net=p.non_commercial_net,
                    commercial_long=p.commercial_long,
                    commercial_short=p.commercial_short,
                    commercial_net=p.commercial_net,
                    open_interest=p.open_interest,
                    report_date=p.report_date,
                    wow_change=wow,
                    percentile_rank=percentile,
                    extreme_flag=extreme,
                    signal_strength=signal,
                    commercial_vs_speculator_divergence=divergence,
                )
                enriched.append(enriched_pos)
                wow_shifts[p.currency.value] = wow
                if extreme:
                    extremes_flagged.append(p.currency.value)

                # Find TFF data for this currency
                tff_match = next(
                    (t for t in tff_positions if t.currency == p.currency), None
                )

                row_data = {
                    "currency": p.currency.value,
                    "contract_name": p.contract_name,
                    "non_commercial_long": p.non_commercial_long,
                    "non_commercial_short": p.non_commercial_short,
                    "non_commercial_net": p.non_commercial_net,
                    "commercial_long": p.commercial_long,
                    "commercial_short": p.commercial_short,
                    "commercial_net": p.commercial_net,
                    "open_interest": p.open_interest,
                    "leveraged_long": tff_match.leveraged_long if tff_match else 0,
                    "leveraged_short": tff_match.leveraged_short if tff_match else 0,
                    "leveraged_net": tff_match.leveraged_net if tff_match else 0,
                    "asset_manager_long": (
                        tff_match.asset_manager_long if tff_match else 0
                    ),
                    "asset_manager_short": (
                        tff_match.asset_manager_short if tff_match else 0
                    ),
                    "asset_manager_net": (
                        tff_match.asset_manager_net if tff_match else 0
                    ),
                    "wow_change": wow,
                    "percentile_rank": percentile,
                    "extreme_flag": extreme,
                    "signal_strength": signal.value,
                    "divergence_flag": divergence,
                    "report_date": p.report_date,
                }
                await repo.bulk_upsert(
                    [row_data],
                    index_elements=["currency", "report_date"],
                    update_fields=[
                        "non_commercial_long",
                        "non_commercial_short",
                        "non_commercial_net",
                        "commercial_long",
                        "commercial_short",
                        "commercial_net",
                        "open_interest",
                        "leveraged_long",
                        "leveraged_short",
                        "leveraged_net",
                        "asset_manager_long",
                        "asset_manager_short",
                        "asset_manager_net",
                        "wow_change",
                        "percentile_rank",
                        "extreme_flag",
                        "signal_strength",
                        "divergence_flag",
                    ],
                )

        dataset = COTDataSet(
            latest_positions=enriched,
            previous_positions=positions,
            tff_positions=tff_positions,
            report_date=report.report_date if report else None,
            wow_shifts=wow_shifts,
            extremes_flagged=extremes_flagged,
            has_tff_data=len(tff_positions) > 0,
            collected_at=datetime.now(UTC),
        )
        await self._cache.set(
            self.cache_namespace,
            self._cache_key(),
            dataset.model_dump(mode="json"),
            self.cache_ttl,
        )
        self._record_items_stored(len(enriched))
        return dataset


    def _empty_dataset(self) -> COTDataSet:
        return COTDataSet(collected_at=datetime.now(UTC))
