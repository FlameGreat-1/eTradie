"""Shared exception hierarchy for the eTradie engine.

Every custom exception derives from ``ETradieBaseError`` so that top-level
handlers can catch the entire tree with a single ``except`` clause while
still allowing granular handling per category.

Exceptions carry structured context (``details`` dict) that is safe to log
but never exposed to external callers without sanitisation.
"""

from __future__ import annotations

from typing import Any


class ETradieBaseError(Exception):
    """Root exception for all eTradie engine errors."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}

    def __repr__(self) -> str:
        cls = type(self).__name__
        return f"{cls}(message={self.message!r}, details={self.details!r})"


# ── Configuration ────────────────────────────────────────────


class ConfigurationError(ETradieBaseError):
    """Invalid or missing configuration."""


# ── Provider layer ───────────────────────────────────────────


class ProviderError(ETradieBaseError):
    """Base class for all provider (external API) errors."""


class ProviderTimeoutError(ProviderError):
    """An external API call exceeded its timeout deadline."""


class ProviderRateLimitError(ProviderError):
    """An external API returned a rate-limit (HTTP 429) response."""


class ProviderAuthenticationError(ProviderError):
    """An external API rejected the supplied credentials."""


class ProviderUnavailableError(ProviderError):
    """An external API is unreachable or returns 5xx errors."""


class ProviderResponseError(ProviderError):
    """An external API returned a parseable but semantically invalid response."""


# ── Collector layer ──────────────────────────────────────────


class CollectorError(ETradieBaseError):
    """Base class for data collection errors."""


class CollectorAllProvidersFailedError(CollectorError):
    """Every provider in a collector's pool returned an error."""


# ── Processor layer ──────────────────────────────────────────


class ProcessorError(ETradieBaseError):
    """Base class for data processing / analysis errors."""


class ProcessorInsufficientDataError(ProcessorError):
    """Not enough data available to produce a meaningful analysis."""


# ── Storage layer ────────────────────────────────────────────


class StorageError(ETradieBaseError):
    """Base class for database / cache persistence errors."""


class StorageConnectionError(StorageError):
    """Could not connect to the backing store."""


class StorageIntegrityError(StorageError):
    """A write violated a database constraint (unique, FK, etc.)."""


# ── Pipeline layer ───────────────────────────────────────────


class PipelineError(ETradieBaseError):
    """An error during pipeline orchestration."""
