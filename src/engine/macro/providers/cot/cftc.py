from __future__ import annotations

import time
from datetime import UTC, date, datetime
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.macro.models.provider.cot import COTPosition, COTReport, TFFPosition
from engine.macro.providers.cot.base import BaseCOTProvider

logger = get_logger(__name__)

_CONTRACT_CURRENCY_MAP: dict[str, Currency] = {
    "EURO FX": Currency.EUR,
    "BRITISH POUND": Currency.GBP,
    "JAPANESE YEN": Currency.JPY,
    "SWISS FRANC": Currency.CHF,
    "AUSTRALIAN DOLLAR": Currency.AUD,
    "CANADIAN DOLLAR": Currency.CAD,
    "NEW ZEALAND DOLLAR": Currency.NZD,
    "U.S. DOLLAR INDEX": Currency.USD,
    "GOLD": Currency.XAU,
    "SILVER": Currency.XAG,
}

_CFTC_LEGACY_DATASET_ID = "jun7-fc8e"
_CFTC_TFF_DATASET_ID = "gpe5-46if"


class CFTCProvider(BaseCOTProvider):
    """Fetch COT data from the CFTC Socrata API.

    The CFTC publishes Commitments of Traders reports via a Socrata
    open data portal.  Without an app token, requests are throttled
    to approximately 1 per minute and may be blocked entirely during
    high-traffic periods.  An app token is strongly recommended.

    Register for a free app token at:
    https://publicreporting.cftc.gov/profile/edit/developer_settings

    Set CFTC_APP_TOKEN in .env to enable authenticated access.
    """

    provider_name = "cftc"

    def __init__(
        self,
        http_client: HttpClient,
        *,
        base_url: str,
        app_token: str = "",
    ) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._app_token = app_token

    async def fetch(self) -> COTReport:
        start = time.monotonic()
        try:
            legacy_raw = await self._fetch_dataset(
                _CFTC_LEGACY_DATASET_ID,
                where="market_and_exchange_names LIKE '%CHICAGO MERCANTILE%'",
            )

            if not legacy_raw:
                logger.warning(
                    "cftc_legacy_empty_response",
                    extra={
                        "dataset_id": _CFTC_LEGACY_DATASET_ID,
                        "has_app_token": bool(self._app_token),
                    },
                )

            positions = self._parse_legacy_positions(legacy_raw)

            if not positions:
                logger.warning(
                    "cftc_no_positions_parsed",
                    extra={
                        "raw_rows": len(legacy_raw),
                        "has_app_token": bool(self._app_token),
                    },
                )

            report_date = positions[0].report_date if positions else date.today()

            tff_positions: list[TFFPosition] = []
            try:
                tff_raw = await self._fetch_dataset(
                    _CFTC_TFF_DATASET_ID,
                    where="market_and_exchange_names LIKE '%CHICAGO MERCANTILE%'",
                )
                tff_positions = self._parse_tff_positions(tff_raw)
            except Exception as exc:
                logger.warning("cftc_tff_fetch_skipped", error=str(exc))

            report = COTReport(
                report_date=report_date,
                release_timestamp=datetime.now(UTC),
                positions=positions,
                tff_positions=tff_positions,
            )
            self._record_success(time.monotonic() - start)
            return report
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error(
                "cftc_fetch_failed",
                error=str(exc),
                extra={"has_app_token": bool(self._app_token)},
            )
            raise

    async def _fetch_dataset(
        self, dataset_id: str, *, where: str
    ) -> list[dict[str, Any]]:
        url = f"{self._base_url}/{dataset_id}.json"
        params: dict[str, str] = {
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": "100",
            "$where": where,
        }

        # Socrata app token for authenticated access (higher rate limits).
        # Without this, requests are throttled and may return 403.
        if self._app_token:
            params["$$app_token"] = self._app_token

        raw = await self._http.get(
            url,
            provider_name=self.provider_name,
            category=self.category.value,
            params=params,
        )
        return raw if isinstance(raw, list) else []

    def _parse_legacy_positions(
        self, raw_rows: list[dict[str, Any]]
    ) -> list[COTPosition]:
        positions: list[COTPosition] = []
        currency_counts: dict[str, int] = {}

        for row in raw_rows:
            contract_name = row.get("market_and_exchange_names", "")
            currency = self._map_contract_to_currency(contract_name)
            if currency is None:
                continue

            count = currency_counts.get(currency.value, 0)
            if count >= 4:
                continue
            currency_counts[currency.value] = count + 1

            nc_long = int(row.get("noncomm_positions_long_all", 0))
            nc_short = int(row.get("noncomm_positions_short_all", 0))
            c_long = int(row.get("comm_positions_long_all", 0))
            c_short = int(row.get("comm_positions_short_all", 0))
            oi = int(row.get("open_interest_all", 0))
            report_date_str = row.get("report_date_as_yyyy_mm_dd", "")

            try:
                rd = date.fromisoformat(report_date_str)
            except (ValueError, TypeError):
                rd = date.today()

            positions.append(
                COTPosition(
                    currency=currency,
                    contract_name=contract_name[:100],
                    non_commercial_long=nc_long,
                    non_commercial_short=nc_short,
                    non_commercial_net=nc_long - nc_short,
                    commercial_long=c_long,
                    commercial_short=c_short,
                    commercial_net=c_long - c_short,
                    open_interest=oi,
                    report_date=rd,
                ),
            )
        return positions

    def _parse_tff_positions(self, raw_rows: list[dict[str, Any]]) -> list[TFFPosition]:
        positions: list[TFFPosition] = []
        currency_counts: dict[str, int] = {}

        for row in raw_rows:
            contract_name = row.get("market_and_exchange_names", "")
            currency = self._map_contract_to_currency(contract_name)
            if currency is None:
                continue

            count = currency_counts.get(currency.value, 0)
            if count >= 4:
                continue
            currency_counts[currency.value] = count + 1

            lev_long = int(row.get("lev_money_positions_long_all", 0))
            lev_short = int(row.get("lev_money_positions_short_all", 0))
            am_long = int(row.get("asset_mgr_positions_long_all", 0))
            am_short = int(row.get("asset_mgr_positions_short_all", 0))
            report_date_str = row.get("report_date_as_yyyy_mm_dd", "")

            try:
                rd = date.fromisoformat(report_date_str)
            except (ValueError, TypeError):
                rd = date.today()

            positions.append(
                TFFPosition(
                    currency=currency,
                    contract_name=contract_name[:100],
                    leveraged_long=lev_long,
                    leveraged_short=lev_short,
                    leveraged_net=lev_long - lev_short,
                    asset_manager_long=am_long,
                    asset_manager_short=am_short,
                    asset_manager_net=am_long - am_short,
                    report_date=rd,
                ),
            )
        return positions

    @staticmethod
    def _map_contract_to_currency(contract_name: str) -> Currency | None:
        upper = contract_name.upper()
        for keyword, currency in _CONTRACT_CURRENCY_MAP.items():
            if keyword in upper:
                return currency
        return None
