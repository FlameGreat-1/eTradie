"""CFTC DEA HTML scraper — COT data from the official CFTC report page.

Parses the pre-formatted text at:
  https://www.cftc.gov/dea/futures/deacmesf.htm

This page is publicly accessible (no API token required) and contains
the latest Commitments of Traders report for CME futures-only positions.

Each currency block looks like:

  BRITISH POUND - CHICAGO MERCANTILE EXCHANGE    Code-096742
  FUTURES ONLY POSITIONS AS OF 04/21/26
  ...
  COMMITMENTS
  63,086 115,125 3,311 172,752 115,913 239,149 234,349 24,374 29,174
  CHANGES FROM 04/14/26 (CHANGE IN OPEN INTEREST: 13,470)
  8,139 5,454 400 5,437 7,846 13,976 13,700 -506 -230
  PERCENT OF OPEN INTEREST ...
  23.9 43.7 1.3 65.6 44.0 90.8 88.9 9.2 11.1
"""

from __future__ import annotations

import re
import time
from datetime import UTC, date, datetime
from typing import Any

from engine.shared.http import HttpClient
from engine.shared.logging import get_logger
from engine.shared.models.currency import Currency
from engine.macro.models.provider.cot import COTPosition, COTReport
from engine.macro.providers.cot.base import BaseCOTProvider

logger = get_logger(__name__)

# Map contract header keywords → Currency enum
_HEADER_CURRENCY_MAP: dict[str, Currency] = {
    "CANADIAN DOLLAR": Currency.CAD,
    "SWISS FRANC": Currency.CHF,
    "BRITISH POUND": Currency.GBP,
    "JAPANESE YEN": Currency.JPY,
    "EURO FX -": Currency.EUR,
    "NZ DOLLAR": Currency.NZD,
    "AUSTRALIAN DOLLAR": Currency.AUD,
    "MEXICAN PESO": Currency.MXN if hasattr(Currency, "MXN") else None,  # type: ignore[arg-type]
}

# Regex to capture the "AS OF MM/DD/YY" date
_DATE_RE = re.compile(r"POSITIONS\s+AS\s+OF\s+(\d{2}/\d{2}/\d{2})")

# Regex to parse a line of 9 numbers (the COMMITMENTS or CHANGES row)
_NUMBERS_RE = re.compile(r"^[\s]*([\d,.-]+(?:\s+[\d,.-]+){8})\s*$")

# Regex to capture the open interest value
_OI_RE = re.compile(r"OPEN\s+INTEREST:\s+([\d,]+)")

# Regex to capture the week-over-week change in open interest
_CHANGE_OI_RE = re.compile(r"CHANGE\s+IN\s+OPEN\s+INTEREST:\s+([\d,.-]+)")


def _parse_int(s: str) -> int:
    """Parse a number string like '115,125' or '-506' into int."""
    return int(s.replace(",", "").replace(".", "").strip() or "0")


def _parse_date(s: str) -> date:
    """Parse 'MM/DD/YY' → date object."""
    try:
        dt = datetime.strptime(s, "%m/%d/%y")
        return dt.date()
    except (ValueError, TypeError):
        return date.today()


class CFTCDEAProvider(BaseCOTProvider):
    """Fetch COT data by scraping the CFTC DEA futures report HTML page.

    This provider is the primary/fallback for COT data. It does NOT
    require an API token and is always accessible.
    """

    provider_name = "cftc_dea"

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
                    f"Expected text response from CFTC DEA page, got {type(raw_text).__name__}"
                )

            positions = self._parse_html(raw_text)

            if not positions:
                logger.warning(
                    "cftc_dea_no_positions_parsed",
                    extra={"text_length": len(raw_text)},
                )

            report_date = positions[0].report_date if positions else date.today()

            report = COTReport(
                report_date=report_date,
                release_timestamp=datetime.now(UTC),
                positions=positions,
                tff_positions=[],
            )
            self._record_success(time.monotonic() - start)
            return report

        except Exception as exc:
            self._record_failure(time.monotonic() - start, type(exc).__name__)
            logger.error(
                "cftc_dea_fetch_failed",
                error=str(exc),
                extra={"url": self._url},
            )
            raise

    def _parse_html(self, text: str) -> list[COTPosition]:
        """Parse the raw pre-formatted text into COTPosition objects.

        The page is structured as consecutive blocks, one per contract.
        We split on contract headers we recognize and extract data from each.
        """
        positions: list[COTPosition] = []

        # Split the giant text into blocks by looking for currency keywords.
        # Each block starts with e.g. "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE"
        blocks = self._split_into_blocks(text)

        for currency, block_text in blocks:
            try:
                pos = self._parse_block(currency, block_text)
                if pos is not None:
                    positions.append(pos)
            except Exception as exc:
                logger.debug(
                    "cftc_dea_block_parse_error",
                    extra={"currency": currency.value, "error": str(exc)},
                )

        return positions

    def _split_into_blocks(self, text: str) -> list[tuple[Currency, str]]:
        """Find all currency blocks in the text."""
        results: list[tuple[Currency, str, int]] = []

        for keyword, currency in _HEADER_CURRENCY_MAP.items():
            if currency is None:
                continue
            # Find all occurrences of this keyword in the text
            idx = text.find(keyword)
            if idx != -1:
                results.append((currency, text, idx))

        # Sort by position in text so we can slice between them
        results.sort(key=lambda x: x[2])

        blocks: list[tuple[Currency, str]] = []
        for i, (currency, _, start_idx) in enumerate(results):
            if i + 1 < len(results):
                end_idx = results[i + 1][2]
            else:
                end_idx = len(text)
            block_text = text[start_idx:end_idx]
            blocks.append((currency, block_text))

        return blocks

    def _parse_block(self, currency: Currency, block: str) -> COTPosition | None:
        """Parse a single contract block into a COTPosition."""
        # Extract report date
        date_match = _DATE_RE.search(block)
        report_date = _parse_date(date_match.group(1)) if date_match else date.today()

        # Extract open interest
        oi_match = _OI_RE.search(block)
        open_interest = _parse_int(oi_match.group(1)) if oi_match else 0

        # Find "COMMITMENTS" line and extract the 9 numbers after it
        commitments_idx = block.find("COMMITMENTS")
        if commitments_idx == -1:
            return None

        # Get the text after COMMITMENTS
        after_commitments = block[commitments_idx + len("COMMITMENTS"):]

        # Extract the contract name from the first line
        first_line = block.split("\n")[0] if "\n" in block else block[:100]
        contract_name = first_line.strip()[:100]

        # Parse commitment numbers: find the first line with 9+ numbers
        commitment_nums = self._extract_numbers(after_commitments)
        if not commitment_nums or len(commitment_nums) < 9:
            return None

        # Layout:
        # NC_LONG  NC_SHORT  NC_SPREADS  C_LONG  C_SHORT  T_LONG  T_SHORT  NR_LONG  NR_SHORT
        nc_long = commitment_nums[0]
        nc_short = commitment_nums[1]
        # nc_spreads = commitment_nums[2]
        c_long = commitment_nums[3]
        c_short = commitment_nums[4]

        return COTPosition(
            currency=currency,
            contract_name=contract_name,
            non_commercial_long=nc_long,
            non_commercial_short=nc_short,
            non_commercial_net=nc_long - nc_short,
            commercial_long=c_long,
            commercial_short=c_short,
            commercial_net=c_long - c_short,
            open_interest=open_interest,
            report_date=report_date,
        )

    @staticmethod
    def _extract_numbers(text: str) -> list[int]:
        """Extract the first line of 9 whitespace-separated numbers from text.

        Numbers may contain commas (e.g. '115,125') and minus signs.
        """
        # Look through lines for one that has at least 9 number tokens
        for line in text.split("\n"):
            line = line.strip()
            if not line or line.startswith("(") or line.startswith("-"):
                continue
            # Try to find number-like tokens
            tokens = re.findall(r"-?[\d,]+", line)
            if len(tokens) >= 9:
                return [_parse_int(t) for t in tokens[:9]]
        return []
