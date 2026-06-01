"""CFTC DEA TFF scraper -- Traders in Financial Futures, Futures Only.

Parses the pre-formatted text at:
  https://www.cftc.gov/dea/futures/financial_lf.htm

This is the official DEA "Traders in Financial Futures" (TFF) report on the
same publicly-accessible host the futures-only legacy scraper (cftc_dea.py)
already uses -- no API token, always reachable. It is the source of the
leveraged-funds and asset-manager positioning the legacy futures-only report
does NOT contain. The Socrata API (publicreporting.cftc.gov) that the retired
CFTCProvider used now returns 403 for every request, which is why this scraper
exists.

Each contract block looks like:

  BRITISH POUND - CHICAGO MERCANTILE EXCHANGE   (CONTRACTS OF GBP 62,500)
  CFTC Code #096742                          Open Interest is   282,065
  Positions
   129,679  47,033  24,724  26,687  136,012  5,714  62,625  33,796  4,169  0  0  0  28,467  30,617
  ...

The "Positions" row carries 14 numbers in a fixed column order:
  Dealer        Long Short Spreading
  AssetMgr      Long Short Spreading
  Leveraged     Long Short Spreading
  OtherRept     Long Short Spreading
  Nonreportable Long Short

so Asset Manager Long/Short are indices 3/4 and Leveraged Long/Short are
indices 6/7.
"""

from __future__ import annotations

import re
import time
from datetime import date, datetime

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.macro.models.provider.cot import COTReport, TFFPosition
from engine.macro.providers.cot.base import BaseCOTProvider

logger = get_logger(__name__)

# Contract header keyword -> Currency. Matches the futures-only scraper's set
# (cftc_dea.py) plus MXN/BRL which appear in the TFF report. NZD is not
# published in the CFTC TFF report, so it simply has no TFF row.
_HEADER_CURRENCY_MAP: dict[str, Currency | None] = {
    "CANADIAN DOLLAR": Currency.CAD,
    "SWISS FRANC": Currency.CHF,
    "BRITISH POUND": Currency.GBP,
    "JAPANESE YEN": Currency.JPY,
    "EURO FX": Currency.EUR,
    "AUSTRALIAN DOLLAR": Currency.AUD,
    "NEW ZEALAND DOLLAR": Currency.NZD,
    "MEXICAN PESO": Currency.MXN if hasattr(Currency, "MXN") else None,
}

# "... AS OF May 26, 2026" appears in the report banner.
_DATE_RE = re.compile(r"AS\s+OF\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})")

# Column indices within the 14-number Positions row.
_IDX_ASSET_MGR_LONG = 3
_IDX_ASSET_MGR_SHORT = 4
_IDX_LEVERAGED_LONG = 6
_IDX_LEVERAGED_SHORT = 7
_MIN_POSITION_NUMBERS = 14


def _parse_int(s: str) -> int:
    cleaned = s.replace(",", "").strip()
    if cleaned in ("", ".", "-"):
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return 0


def _parse_report_date(text: str) -> date:
    m = _DATE_RE.search(text)
    if not m:
        return date.today()
    try:
        return datetime.strptime(m.group(1), "%B %d, %Y").date()
    except (ValueError, TypeError):
        return date.today()


class CFTCDEATFFProvider(BaseCOTProvider):
    """Scrape the CFTC DEA Traders-in-Financial-Futures report.

    Returns a COTReport carrying ONLY tff_positions (positions=[]). It is
    consumed by the COTCollector as a dedicated, best-effort TFF source that
    enriches the legacy futures-only data; a failure here never degrades the
    core COT signal.
    """

    provider_name = "cftc_dea_tff"

    def __init__(self, http_client: HttpClient, *, url: str) -> None:
        super().__init__()
        self._http = http_client
        self._url = url

    async def fetch(self) -> COTReport:
        start = time.monotonic()
        try:
            raw_text = await self._http.get(
                self._url,
                provider_name=self.provider_name,
                category=self.category.value,
            )
            if not isinstance(raw_text, str):
                raise ValueError(
                    f"Expected text from CFTC DEA TFF page, got {type(raw_text).__name__}"
                )

            report_date = _parse_report_date(raw_text)
            tff_positions = self._parse(raw_text, report_date)

            if not tff_positions:
                logger.warning(
                    "cftc_dea_tff_no_positions_parsed",
                    extra={"text_length": len(raw_text)},
                )

            report = COTReport(
                report_date=report_date,
                release_timestamp=datetime.now(datetime.now().astimezone().tzinfo),
                positions=[],
                tff_positions=tff_positions,
            )
            self._record_success(time.monotonic() - start)
            return report
        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error(
                "cftc_dea_tff_fetch_failed",
                error=str(exc),
                extra={"url": self._url},
            )
            raise

    def _parse(self, text: str, report_date: date) -> list[TFFPosition]:
        positions: list[TFFPosition] = []
        seen: set[str] = set()

        for currency, block in self._split_into_blocks(text):
            if currency.value in seen:
                # First (current) block per currency wins; later duplicates
                # (e.g. combined report concatenations) are ignored.
                continue
            try:
                pos = self._parse_block(currency, block, report_date)
            except Exception as exc:
                logger.debug(
                    "cftc_dea_tff_block_parse_error",
                    extra={"currency": currency.value, "error": str(exc)},
                )
                continue
            if pos is not None:
                positions.append(pos)
                seen.add(currency.value)
        return positions

    def _split_into_blocks(self, text: str) -> list[tuple[Currency, str]]:
        """Find currency blocks, skipping cross-rate (XRATE) contracts.

        A naive substring search for "EURO FX" would also match
        "EURO FX/BRITISH POUND XRATE"; we exclude any header line containing
        "XRATE" so the cross-rate contracts never mis-map to a single
        currency.
        """
        header_re = re.compile(
            r"^([A-Z][A-Z .,/]+?)\s+-\s+CHICAGO MERCANTILE EXCHANGE.*$",
            re.MULTILINE,
        )
        matches = list(header_re.finditer(text))

        results: list[tuple[Currency, str]] = []
        for i, m in enumerate(matches):
            header = m.group(0).upper()
            if "XRATE" in header:
                continue
            currency = self._map_header_to_currency(header)
            if currency is None:
                continue
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            results.append((currency, text[start:end]))
        return results

    @staticmethod
    def _map_header_to_currency(header: str) -> Currency | None:
        for keyword, currency in _HEADER_CURRENCY_MAP.items():
            if currency is None:
                continue
            if keyword in header:
                return currency
        return None

    def _parse_block(
        self, currency: Currency, block: str, report_date: date
    ) -> TFFPosition | None:
        # The numbers row is the first line AFTER the "Positions" marker that
        # carries at least 14 numeric tokens. The "Changes from" and percent
        # rows come later and must not be picked.
        pos_idx = block.find("Positions")
        if pos_idx == -1:
            return None
        after = block[pos_idx + len("Positions"):]

        nums: list[int] | None = None
        for line in after.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("Changes"):
                # Stop scanning once we reach the Changes row without having
                # found a positions row -- the block is malformed.
                if stripped.startswith("Changes"):
                    break
                continue
            tokens = re.findall(r"-?[\d,]+", stripped)
            if len(tokens) >= _MIN_POSITION_NUMBERS:
                nums = [_parse_int(t) for t in tokens[:_MIN_POSITION_NUMBERS]]
                break

        if nums is None or len(nums) < _MIN_POSITION_NUMBERS:
            return None

        am_long = nums[_IDX_ASSET_MGR_LONG]
        am_short = nums[_IDX_ASSET_MGR_SHORT]
        lev_long = nums[_IDX_LEVERAGED_LONG]
        lev_short = nums[_IDX_LEVERAGED_SHORT]

        first_line = block.split("\n", 1)[0].strip()[:100]
        return TFFPosition(
            currency=currency,
            contract_name=first_line,
            leveraged_long=lev_long,
            leveraged_short=lev_short,
            leveraged_net=lev_long - lev_short,
            asset_manager_long=am_long,
            asset_manager_short=am_short,
            asset_manager_net=am_long - am_short,
            report_date=report_date,
        )
