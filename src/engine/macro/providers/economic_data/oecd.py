"""OECD Data Explorer — Non-US Economic Data provider (FREE).

Fetches key economic indicators for non-US countries from the OECD Data
Explorer REST API.  Covers GDP, CPI, Core CPI, unemployment, PMI (via CLI
proxy), retail sales, trade balance, PPI, consumer confidence, and
industrial production.

Covers: EUR (Euro Area), GBP (UK), JPY (Japan), CHF (Switzerland),
        AUD (Australia), CAD (Canada), NZD (New Zealand).

API docs: https://data-explorer.oecd.org/
No API key required. Rate limit: reasonable for hourly polling.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.shared.models.events import EventImpact, EventType, InflationType
from engine.macro.models.provider.economic import EconomicRelease
from engine.macro.providers.economic_data.base import (
    BaseEconomicDataProvider,
    compute_surprise_direction,
)

logger = get_logger(__name__)

_OECD_BASE_URL = "https://sdmx.oecd.org/public/rest/data"

# OECD country codes mapped to Currency enum.
_COUNTRY_CURRENCY_MAP: dict[str, Currency] = {
    "EA20": Currency.EUR,  # Euro Area (20 members)
    "GBR": Currency.GBP,
    "JPN": Currency.JPY,
    "CHE": Currency.CHF,
    "AUS": Currency.AUD,
    "CAN": Currency.CAD,
    "NZL": Currency.NZD,
}

_COUNTRIES_KEY = "+".join(_COUNTRY_CURRENCY_MAP.keys())

# OECD dataset/indicator configurations.
# Each entry defines: dataset_id, filter_key, indicator mapping, impact.
_OECD_INDICATORS: list[dict[str, Any]] = [
    # --- GDP Growth Rate (Quarterly) ---
    {
        "dataset_id": "OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH,1.0",
        "filter": f"{_COUNTRIES_KEY}.Q.G1._T.GY.V",
        "indicator": EventType.GDP,
        "name_template": "GDP Growth Rate ({})",
        "impact": EventImpact.HIGH,
        "inflation_type": None,
    },
    # --- CPI Headline (Monthly) ---
    {
        "dataset_id": "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0",
        "filter": f"{_COUNTRIES_KEY}.M.CPI._T.PA._T.N.GY",
        "indicator": EventType.CPI,
        "name_template": "Consumer Price Index ({})",
        "impact": EventImpact.HIGH,
        "inflation_type": InflationType.HEADLINE,
    },
    # --- Core CPI ex Food & Energy (Monthly) ---
    {
        "dataset_id": "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0",
        "filter": f"{_COUNTRIES_KEY}.M.CPI.FE.PA._T.N.GY",
        "indicator": EventType.CPI,
        "name_template": "Core CPI ex Food & Energy ({})",
        "impact": EventImpact.HIGH,
        "inflation_type": InflationType.CORE,
    },
    # --- Unemployment Rate (Monthly) ---
    {
        "dataset_id": "OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M,1.0",
        "filter": f"{_COUNTRIES_KEY}.M.UNE_LF_M._T._T._T.PA",
        "indicator": EventType.EMPLOYMENT,
        "name_template": "Unemployment Rate ({})",
        "impact": EventImpact.HIGH,
        "inflation_type": None,
    },
    # --- PPI / Producer Prices (Monthly) ---
    {
        "dataset_id": "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0",
        "filter": f"{_COUNTRIES_KEY}.M.PPI._T.PA._T.N.GY",
        "indicator": EventType.PPI,
        "name_template": "Producer Price Index ({})",
        "impact": EventImpact.MEDIUM,
        "inflation_type": InflationType.HEADLINE,
    },
    # --- Composite Leading Indicator (Monthly, PMI proxy) ---
    {
        "dataset_id": "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0",
        "filter": f"{_COUNTRIES_KEY}.M.LI.LOLITOAA.IXOB.AA",
        "indicator": EventType.PMI,
        "name_template": "Composite Leading Indicator ({})",
        "impact": EventImpact.MEDIUM,
        "inflation_type": None,
    },
    # --- Retail Trade Volume (Monthly) ---
    {
        "dataset_id": "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0",
        "filter": f"{_COUNTRIES_KEY}.M.ST.SLRTTO01.IXOB.AA",
        "indicator": EventType.RETAIL_SALES,
        "name_template": "Retail Trade Volume ({})",
        "impact": EventImpact.MEDIUM,
        "inflation_type": None,
    },
    # --- Trade Balance / Goods (Monthly) ---
    {
        "dataset_id": "OECD.SDD.TPS,DSD_BOP@DF_BOP,1.0",
        "filter": f"{_COUNTRIES_KEY}.M.B.G.S._T._T.D.N",
        "indicator": EventType.TRADE_BALANCE,
        "name_template": "Trade Balance - Goods ({})",
        "impact": EventImpact.MEDIUM,
        "inflation_type": None,
    },
    # --- Consumer Confidence (Monthly) ---
    {
        "dataset_id": "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0",
        "filter": f"{_COUNTRIES_KEY}.M.CS.CSCICP03.IXOB.AA",
        "indicator": EventType.CONSUMER_CONFIDENCE,
        "name_template": "Consumer Confidence Index ({})",
        "impact": EventImpact.MEDIUM,
        "inflation_type": None,
    },
    # --- Industrial Production (Monthly) ---
    {
        "dataset_id": "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0",
        "filter": f"{_COUNTRIES_KEY}.M.PR.PRINTO01.IXOB.AA",
        "indicator": EventType.MANUFACTURING,
        "name_template": "Industrial Production Index ({})",
        "impact": EventImpact.MEDIUM,
        "inflation_type": None,
    },
]

# Reverse map for display names.
_COUNTRY_NAMES: dict[str, str] = {
    "EA20": "Euro Area",
    "GBR": "United Kingdom",
    "JPN": "Japan",
    "CHE": "Switzerland",
    "AUS": "Australia",
    "CAN": "Canada",
    "NZL": "New Zealand",
}


class OECDEconomicProvider(BaseEconomicDataProvider):
    """Fetch non-US economic indicators from the OECD Data Explorer API.

    Complements the FRED provider (US-only) to give full coverage of
    all 8 traded currencies. Free, no API key required.
    """

    provider_name = "oecd"

    def __init__(
        self, http_client: HttpClient, *, base_url: str = _OECD_BASE_URL
    ) -> None:
        super().__init__()
        self._http = http_client
        self._base_url = base_url.rstrip("/")

    async def fetch(self) -> list[EconomicRelease]:
        start = time.monotonic()
        try:
            releases: list[EconomicRelease] = []
            for indicator_cfg in _OECD_INDICATORS:
                try:
                    batch = await self._fetch_indicator(indicator_cfg)
                    releases.extend(batch)
                except Exception as exc:
                    logger.warning(
                        "oecd_indicator_skipped",
                        indicator=indicator_cfg["indicator"].value,
                        error=str(exc),
                    )
            self._record_success(time.monotonic() - start)
            return releases
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error("oecd_fetch_failed", error=str(exc))
            raise

    async def _fetch_indicator(self, cfg: dict[str, Any]) -> list[EconomicRelease]:
        """Fetch the latest observations for one OECD indicator across all countries."""
        url = f"{self._base_url}/{cfg['dataset_id']}/{cfg['filter']}"
        raw = await self._http.get(
            url,
            provider_name=self.provider_name,
            category=self.category.value,
            params={
                "format": "jsondata",
                "lastNObservations": "2",
                "dimensionAtObservation": "AllDimensions",
            },
            headers={"Accept": "application/json"},
        )

        return self._parse_sdmx_response(raw, cfg)

    def _parse_sdmx_response(
        self, raw: Any, cfg: dict[str, Any]
    ) -> list[EconomicRelease]:
        """Parse OECD SDMX-JSON response into EconomicRelease objects."""
        releases: list[EconomicRelease] = []

        if not isinstance(raw, dict):
            return releases

        data_sets = raw.get("dataSets", [])
        if not data_sets:
            return releases

        observations = data_sets[0].get("observations", {})
        structure = raw.get("structure", {})
        dimensions = structure.get("dimensions", {}).get("observation", [])

        # Find the country dimension index and time dimension index.
        country_dim_idx: int | None = None
        time_dim_idx: int | None = None
        country_values: list[dict[str, Any]] = []
        time_values: list[dict[str, Any]] = []

        for i, dim in enumerate(dimensions):
            dim_id = dim.get("id", "")
            if dim_id == "REF_AREA":
                country_dim_idx = i
                country_values = dim.get("values", [])
            elif dim_id == "TIME_PERIOD":
                time_dim_idx = i
                time_values = dim.get("values", [])

        if country_dim_idx is None or time_dim_idx is None:
            return releases

        # Group observations by country, take the latest two for actual/previous.
        country_obs: dict[str, list[tuple[str, float]]] = {}

        for obs_key, obs_val in observations.items():
            indices = obs_key.split(":")
            if len(indices) <= max(country_dim_idx, time_dim_idx):
                continue

            country_idx = int(indices[country_dim_idx])
            time_idx = int(indices[time_dim_idx])

            if country_idx >= len(country_values) or time_idx >= len(time_values):
                continue

            country_code = country_values[country_idx].get("id", "")
            time_period = time_values[time_idx].get("id", "")
            value = obs_val[0] if isinstance(obs_val, list) and obs_val else None

            if country_code in _COUNTRY_CURRENCY_MAP and value is not None:
                country_obs.setdefault(country_code, []).append(
                    (time_period, float(value))
                )

        # Build releases: latest = actual, second-latest = previous.
        for country_code, obs_list in country_obs.items():
            obs_list.sort(key=lambda x: x[0], reverse=True)
            if not obs_list:
                continue

            actual = obs_list[0][1]
            previous = obs_list[1][1] if len(obs_list) > 1 else None
            time_period = obs_list[0][0]

            currency = _COUNTRY_CURRENCY_MAP[country_code]
            country_name = _COUNTRY_NAMES.get(country_code, country_code)

            try:
                release_time = datetime.fromisoformat(f"{time_period}-01").replace(
                    tzinfo=UTC
                )
            except (ValueError, TypeError):
                release_time = datetime.now(UTC)

            releases.append(
                EconomicRelease(
                    currency=currency,
                    indicator=cfg["indicator"],
                    indicator_name=cfg["name_template"].format(country_name),
                    actual=actual,
                    forecast=None,
                    previous=previous,
                    surprise=None,
                    surprise_direction=compute_surprise_direction(actual, None),
                    impact=cfg["impact"],
                    inflation_type=cfg["inflation_type"],
                    release_time=release_time,
                    source="oecd",
                )
            )

        return releases
