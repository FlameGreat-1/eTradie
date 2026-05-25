from __future__ import annotations

from datetime import datetime

from engine.shared.models.base import TimestampedModel


class EconomicRelease(TimestampedModel):
    """An economic data release as consumed by the LLM.

    Only the fields the LLM actually reasons over are kept:
      - indicator_name: human-readable label including the country
        tag (e.g. "Core CPI ex Food & Energy (US)"). Carries both
        the indicator and the currency information.
      - actual / previous: the numeric values the LLM compares.
      - release_time: the timestamp.

    Provenance fields (source, currency enum, indicator enum) were
    removed in 2026-05. They had no live downstream consumer; the
    Go gateway extractor that referenced them was reading fields the
    providers never populated. See the cleanup MR for the audit.
    """

    indicator_name: str
    actual: float | None = None
    previous: float | None = None
    release_time: datetime
